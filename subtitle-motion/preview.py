# -*- coding: utf-8 -*-
"""风格预览：同一句歌词、同一时刻，把多种风格并排拼图或拼成对比片。

同一段画面、同一个时刻，只换字幕风格，一眼就能挑出合适的那个。

拼图（出 PNG，快，几秒）：
    python preview.py --video 片子.mp4 --lrc 歌词.lrc --at 40.2 --styles all
    python preview.py --video 片子.mp4 --lrc 歌词.lrc --at 40.2 --styles neon,huge --cols 2

对比片（出 MP4，带声音，慢一些）：
    python preview.py --video 片子.mp4 --lrc 歌词.lrc --at 40.2 \
        --styles neon,slam,cine --seconds 4 --mode video

--at 一律按「原曲时间」填；如果视频是从原曲中途剪出来的片段，
再用 --offset 声明「视频第 0 秒＝原曲第几秒」。
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import karaoke  # noqa: E402

LABEL = {
    "neon": "逐字扫色", "slam": "砸入回弹", "cine": "电影大字",
    "fadeup": "逐字浮起", "ink": "墨色细字", "huge": "全屏巨字",
    "vtext": "竖排古风", "type": "打字机", "blur": "模糊聚焦",
    "mirror": "倒影",
}


def run(cmd, cwd=None, what="ffmpeg"):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit("%s 失败:\n%s" % (what, (r.stderr or "")[-900:]))
    return r


def pick_styles(arg):
    if arg in (None, "", "all"):
        return list(karaoke.STYLES)
    names = [x.strip() for x in arg.replace("，", ",").split(",") if x.strip()]
    for n in names:
        if n not in karaoke.STYLES:
            raise SystemExit("没有这个风格: %s（可用: %s）"
                             % (n, ", ".join(karaoke.STYLES)))
    return names


def align(at, lrc, delay):
    """把取帧时刻挪进某句歌词的「稳定期」。

    直接截在歌词刚开始那一帧，会正撞上淡入（alpha 还是 255），
    截出来是空的——不是渲染失败，是时候不对。这里自动往后推 delay 秒。
    """
    if delay <= 0:
        return at
    lines = karaoke.parse_lrc(lrc)
    if not lines:
        return at
    before = [t for t, _ in lines if t <= at + 0.05]
    if not before:
        return at                                    # 第一句之前，照原样
    st = before[-1]
    nxt = next((t for t, _ in lines if t > st), st + 60)
    cap = max(at, st + delay)
    cap = min(cap, nxt - 0.15)                       # 别越过下一句
    return max(cap, st + 0.08)


def make_ass(style, lrc, seg_start, seg_end, kws):
    """生成从 seg_start 起算（时间为 0）的 ASS，放进临时目录"""
    tmp = tempfile.mkdtemp(prefix="prev_", dir=HERE)
    out = os.path.join(tmp, "p.ass")
    karaoke.build(style, lrc, seg_start, seg_end, seg_start, out=out,
                  keywords=kws)
    return tmp, out


def line_start(at, lrc):
    """at 这一刻正在唱的那句歌词，是从什么时候开始的。

    从「at 往前 1.2 秒」开始建 ASS 是错的：如果那句歌词在更早的时候
    就开始了，它会被 t_from 过滤掉，截出来就没有字幕。
    """
    lines = karaoke.parse_lrc(lrc)
    before = [t for t, _ in lines if t <= at + 0.02]
    return before[-1] if before else max(0.0, at - 1.2)


def capture(video, style, lrc, at, offset, kws, out_png, seg_start):
    """截 at 那一帧（原曲时间），烧好该风格字幕"""
    hold = 6.0                                   # 字幕窗口开多宽
    seg_end = at + hold
    tmp, ass = make_ass(style, lrc, seg_start, seg_end, kws)
    try:
        seek_in = max(0.0, seg_start - offset)   # 视频内位置
        seek_out = at - seg_start
        cmd = ["ffmpeg", "-y", "-v", "error"]
        if seek_in > 0:
            cmd += ["-ss", "%.3f" % seek_in]
        cmd += ["-i", os.path.abspath(video), "-vf", "ass=filename=p.ass"]
        if seek_out > 0:
            cmd += ["-ss", "%.3f" % seek_out]
        cmd += ["-frames:v", "1", "-update", "1", os.path.abspath(out_png)]
        run(cmd, cwd=tmp, what="截图（%s）" % style)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not os.path.isfile(out_png):
        raise SystemExit("截图失败：%s 这个时刻没有画面（视频可能比 --at 短）" % at)
    return out_png


def build_grid(frames, names, cols, out_png):
    """把若干帧拼成网格，左下角标风格名"""
    n = len(frames)
    rows = (n + cols - 1) // cols
    cw = (karaoke.W // cols) // 2 * 2      # 偶数，x264/scale 更友好
    ch = (karaoke.H // cols) // 2 * 2
    gw, gh = cw * cols, ch * rows

    args, fc = [], ""
    for i, f in enumerate(frames):
        args += ["-i", f]
        fc += "[%d]scale=%d:%d,setsar=1[s%d];" % (i, cw, ch, i)
    fc += "".join("[s%d]" % i for i in range(n))
    layout = "|".join("%d_%d" % ((i % cols) * cw, (i // cols) * ch)
                      for i in range(n))
    fc += "xstack=inputs=%d:layout=%s" % (n, layout)

    tmp = tempfile.mkdtemp(prefix="grid_", dir=HERE)
    try:
        raw = os.path.join(tmp, "raw.png")
        run(["ffmpeg", "-y", "-v", "error"] + args +
            ["-filter_complex", fc, "-frames:v", "1", raw], what="拼图")

        # 标签用 ASS 烧，比 drawtext 稳（不依赖系统 fontconfig）
        fs = max(15, int(cw * 0.042))
        ev = []
        for i, nm in enumerate(names):
            x = (i % cols) * cw + int(cw * 0.03)
            y = (i // cols) * ch + ch - int(ch * 0.07)
            ev.append("Dialogue: 0,0:00:00.00,0:00:10.00,L,,0,0,0,,"
                      "{\\an7\\pos(%d,%d)\\fs%d\\c&H00FFFFFF&\\bord2.4"
                      "\\3c&H00000000&}%d  %s  %s"
                      % (x, y, fs, i + 1, nm, LABEL.get(nm, "")))
        ass = "\n".join([
            "[Script Info]", "ScriptType: v4.00+",
            "PlayResX: %d" % gw, "PlayResY: %d" % gh,
            "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,"
            " OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut,"
            " ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow,"
            " Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: L,Microsoft YaHei,32,&H00FFFFFF,&H00FFFFFF,&H00000000,"
            "&H00000000,-1,0,0,0,100,100,0,0,1,2.4,0,7,0,0,0,1", "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR,"
            " MarginV, Effect, Text",
        ]) + "\n" + "\n".join(ev) + "\n"
        lab = os.path.join(tmp, "label.ass")
        open(lab, "w", encoding="utf-8-sig").write(ass)

        run(["ffmpeg", "-y", "-v", "error", "-i", raw,
             "-vf", "ass=filename=label.ass", "-frames:v", "1",
             os.path.abspath(out_png)], cwd=tmp, what="烧标签")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("拼图:", out_png)


def label_font():
    """drawtext 要一个能读到的字体文件；本机 fontconfig 坏了也能用"""
    for p in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
              "/System/Library/Fonts/PingFang.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        if os.path.isfile(p):
            return "fontfile='%s'" % p.replace(":", "\\:")
    return "font=sans"


def build_video(video, names, lrc, at, offset, kws, seconds, out_mp4, crf,
                seg_start):
    """每种风格切一段，标签后首尾相接成对比片"""
    tmp = tempfile.mkdtemp(prefix="cmp_", dir=HERE)
    font = label_font()
    segs = []
    dur = max(0.5, at - seg_start) + seconds      # 从这句歌词的起点开始
    try:
        for nm in names:
            tmp_ass, ass = make_ass(nm, lrc, seg_start, seg_start + dur + 1, kws)
            seek_in = max(0.0, seg_start - offset)
            raw = os.path.join(tmp, "s_%s.mp4" % nm)
            cmd = ["ffmpeg", "-y", "-v", "error"]
            if seek_in > 0:
                cmd += ["-ss", "%.3f" % seek_in]
            cmd += ["-i", os.path.abspath(video), "-t", "%.3f" % dur,
                    "-vf", "ass=filename=p.ass",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", raw]
            run(cmd, cwd=tmp_ass, what="切片（%s）" % nm)
            shutil.rmtree(tmp_ass, ignore_errors=True)

            lab = os.path.join(tmp, "l_%s.mp4" % nm)
            txt = ("%s  %s" % (nm, LABEL.get(nm, ""))).replace(":", r"\:")
            r = subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", raw, "-vf",
                 "drawtext=%s:text='%s':x=40:y=40:fontsize=%d:"
                 "fontcolor=white@0.92:box=1:boxcolor=black@0.42:boxborderw=14"
                 % (font, txt, max(18, int(karaoke.W * 0.032))),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
                 "-pix_fmt", "yuv420p", "-c:a", "copy", lab],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace")
            segs.append(lab if r.returncode == 0 else raw)
            if r.returncode:
                print("  标注失败，仍用原片:", nm, (r.stderr or "")[-160:])
            else:
                print("  OK", nm)

        lst = os.path.join(tmp, "concat.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for p in segs:
                f.write("file '%s'\n" % p.replace("\\", "/"))
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", lst, "-c", "copy", "-movflags", "+faststart",
             os.path.abspath(out_mp4)], what="拼接")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("对比片:", out_mp4, "%.1f MB" % (os.path.getsize(out_mp4) / 1e6))


def main():
    ap = argparse.ArgumentParser(description="多风格字幕预览（拼图 / 对比片）")
    ap.add_argument("--video", required=True, help="源视频")
    ap.add_argument("--lrc", required=True, help="歌词 LRC")
    ap.add_argument("--at", type=float, required=True,
                    help="截图/起片时刻（原曲秒数）")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="视频第 0 秒＝原曲第几秒，整片填 0")
    ap.add_argument("--styles", default="all",
                    help="all 或逗号分隔的风格名列表")
    ap.add_argument("--keywords", help="cine 点亮的关键词，逗号分隔")
    ap.add_argument("--cols", type=int, default=3, help="拼图列数，默认 3")
    ap.add_argument("--seconds", type=float, default=4.0,
                    help="对比片每段时长，默认 4 秒")
    ap.add_argument("--crf", type=int, default=20, help="对比片画质")
    ap.add_argument("--delay", type=float, default=0.9,
                    help="自动把取帧时刻推后到歌词开始后这么多秒，"
                         "避开淡入那一下（0＝完全按 --at 截）")
    ap.add_argument("--mode", choices=["grid", "video"], default="grid")
    ap.add_argument("--out", help="输出文件；默认即时间命名")
    a = ap.parse_args()

    for p in (a.video, a.lrc):
        if not os.path.isfile(p):
            raise SystemExit("找不到文件: %s" % p)

    w, h = karaoke.probe_size(a.video)
    karaoke.set_canvas(w, h)
    names = pick_styles(a.styles)
    kws = [x.strip() for x in (a.keywords or "").replace("，", ",").split(",")
           if x.strip()]
    at = align(a.at, a.lrc, a.delay)
    print("画面 %dx%d · %d 种风格 · 取 %.2f 秒处%s"
          % (w, h, len(names), at,
             "" if abs(at - a.at) < 0.01 else "（已从 %.2f 对齐到歌词稳定处）"
             % a.at))

    if a.mode == "grid":
        out = a.out or os.path.join(HERE, "preview_grid.png")
        tmp = tempfile.mkdtemp(prefix="cap_", dir=HERE)
        try:
            seg_start = line_start(at, a.lrc)
            frames = []
            for nm in names:
                frames.append(capture(a.video, nm, a.lrc, at, a.offset, kws,
                                      os.path.join(tmp, "c_%s.png" % nm),
                                      seg_start))
            build_grid(frames, names, a.cols, out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        out = a.out or os.path.join(HERE, "preview_compare.mp4")
        build_video(a.video, names, a.lrc, at, a.offset, kws, a.seconds,
                    out, a.crf, line_start(at, a.lrc))


if __name__ == "__main__":
    main()

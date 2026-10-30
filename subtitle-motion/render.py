# -*- coding: utf-8 -*-
"""一条命令出片：视频 + LRC + 风格 -> 带字幕的成片。

自动读取视频分辨率并按比例适配字幕（不写死 1080x1920），
不需要手动拼 ffmpeg 命令，也不会踩 Windows 路径冒号转义的坑。

用法：
    python render.py --video a.mp4 --lrc a.lrc --style neon --out a_sub.mp4
    python render.py --video a.mp4 --lrc a.lrc --style ink --from 40 --to 60
    python render.py --video a.mp4 --lrc a.lrc --style neon --dim 0.07      # 加轻微压暗
    python render.py --video a.mp4 --lrc a.lrc --style neon --preview 2.4   # 只出一帧干净图
    python render.py --video a.mp4 --lrc a.lrc --style cine --keywords "离开,再见"
    python render.py --video 片段.mp4 --lrc a.lrc --style ink --offset 40   # 视频从原曲40秒起
"""

import argparse
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import karaoke  # noqa: E402


def run(cmd, cwd=None, quiet=True):
    """跑一条命令，失败时把 stderr 尾部抛出来"""
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        tail = (r.stderr or "")[-1200:]
        raise SystemExit("命令失败（%s）:\n%s" % (os.path.basename(cmd[0]), tail))
    if not quiet and r.stderr.strip():
        print(r.stderr.strip()[-600:])
    return r


def duration(video):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", video])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def cleanup(work, ass_path, keep):
    """删除临时目录；--keep-ass 时把 ASS 挪回工作目录"""
    try:
        if keep and os.path.isfile(ass_path):
            os.replace(ass_path, os.path.join(HERE, os.path.basename(keep)))
            print("ASS 保留:", os.path.join(HERE, os.path.basename(keep)))
    except OSError:
        pass
    try:
        for f in os.listdir(work):
            if not f.endswith(".ass") or not keep:
                os.remove(os.path.join(work, f))
        os.rmdir(work)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(
        description="视频 + LRC + 风格 -> 带卡拉OK字幕的成片（自动适配任意分辨率）")
    ap.add_argument("--video", required=True, help="源视频")
    ap.add_argument("--lrc", required=True, help="歌词 LRC")
    ap.add_argument("--style", default="neon", help="风格名，默认 neon")
    ap.add_argument("--out", help="输出视频，默认 <源名>_<风格>.mp4")
    ap.add_argument("--from", dest="t_from", type=float,
                    help="起始秒（按原曲/歌词时间）")
    ap.add_argument("--to", dest="t_to", type=float,
                    help="结束秒（按原曲/歌词时间）")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="视频第 0 秒对应原曲第几秒。整片=0（默认）；"
                         "若视频是从原曲中途剪出的片段，填那个切点，"
                         "例如 40 表示「视频开头＝原曲 40 秒」")
    ap.add_argument("--dim", type=float, default=0.0,
                    help="压暗幅度 0-1，如 0.07（亮画面加字幕时用）")
    ap.add_argument("--sat", type=float, default=1.0, help="饱和度倍数，如 1.14")
    ap.add_argument("--crf", type=int, default=19, help="画质，默认 19")
    ap.add_argument("--preset", default="medium", help="编码速度，默认 medium")
    ap.add_argument("--keep-ass", action="store_true", help="保留生成的 ASS")
    ap.add_argument("--keywords",
                    help="cine 风格要点亮的关键词，逗号分隔，如 \"离开,再见\"")
    ap.add_argument("--preview", type=float, help="只截某一秒的一帧 PNG，不编码视频")
    a = ap.parse_args()

    if not os.path.isfile(a.video):
        raise SystemExit("找不到视频: %s" % a.video)
    if not os.path.isfile(a.lrc):
        raise SystemExit("找不到 LRC: %s" % a.lrc)

    # 1) 按视频真实分辨率设画布
    w, h = karaoke.probe_size(a.video)
    karaoke.set_canvas(w, h)
    print("画面 %dx%d · 缩放系数 %.3f · 风格 %s" % (w, h, h / 1920.0, a.style))

    # 2) 生成 ASS 到临时目录（放同目录，避免路径冒号）
    #    --from/--to/--preview 一律按「原曲时间」理解；
    #    --offset 声明视频第 0 秒对应原曲第几秒（整片=0，切片=切点）
    offset = a.offset
    work = tempfile.mkdtemp(prefix="sub_", dir=HERE)
    ass_name = "sub.ass"
    ass_path = os.path.join(work, ass_name)
    kws = [x.strip() for x in (a.keywords or "").replace("，", ",").split(",")
           if x.strip()]
    # ASS 的时间从 s0 起算为 0；s0 = 要开始的那一秒（原曲时间）
    s0 = a.t_from if a.t_from is not None else offset
    karaoke.build(a.style, a.lrc, s0, a.t_to, s0, out=ass_path, keywords=kws)

    # 3) 组装滤镜：可选压暗/饱和 + 字幕（cwd 下用相对文件名，绕开路径转义）
    vf = []
    if a.dim or a.sat != 1.0:
        vf.append("eq=brightness=-%.4f:saturation=%.3f" % (a.dim, a.sat))
    vf.append("ass=filename=%s" % ass_name)

    keep_name = (os.path.basename(a.out) + ".ass") if a.keep_ass else None
    if a.keep_ass and not a.out:
        keep_name = "sub_%s.ass" % a.style

    if a.preview is not None:
        out_png = a.out or os.path.join(HERE, "preview.png")
        # 视频内起点 = s0 - offset；输入先 seek 到这里（流 pts 归 0），
        # 再在过滤器后 seek「preview - s0」拿到目标帧。
        # 只用一个输出端 seek 会跳错位置，两个配合才对得上字幕时间轴。
        seek_in = max(0.0, s0 - offset)
        seek = a.preview - s0
        if seek < 0:
            raise SystemExit("--preview %.2f 早于起点 %.2f（--from/--offset）"
                             % (a.preview, s0))
        cmd = ["ffmpeg", "-y", "-v", "error"]
        if seek_in > 0:
            cmd += ["-ss", "%.3f" % seek_in]
        cmd += ["-i", os.path.abspath(a.video), "-vf", ",".join(vf)]
        if seek > 0:
            cmd += ["-ss", "%.3f" % seek]
        cmd += ["-frames:v", "1", "-update", "1", os.path.abspath(out_png)]
        run(cmd, cwd=work)
        print("已出图:", out_png)
        cleanup(work, ass_path, keep_name)
        return

    out = a.out or os.path.splitext(a.video)[0] + "_" + a.style + ".mp4"
    out = os.path.abspath(out)

    # 视频内起点 = 原曲起点 s0 减偏移；时长按 s0 起算
    seek_v = max(0.0, s0 - offset)
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if seek_v > 0:
        cmd += ["-ss", "%.3f" % seek_v]
    cmd += ["-i", os.path.abspath(a.video)]
    if a.t_to is not None:
        cmd += ["-t", "%.3f" % max(0.0, a.t_to - s0)]
    cmd += ["-vf", ",".join(vf),
            "-c:v", "libx264", "-preset", a.preset, "-crf", str(a.crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", out]
    run(cmd, cwd=work, quiet=False)

    size_mb = os.path.getsize(out) / 1024 / 1024
    dur = duration(out)
    if size_mb < 0.05 or not dur:
        hint = ""
        if seek_v > 0:
            hint = ("\n提示：视频比 --from 短。如果视频本身是从原曲中途切出来的片段，"
                    "用 --offset 声明它的起点（例如 --offset 40）。")
        raise SystemExit("导出失败：输出为空。%s" % hint)
    print("成片: %s  (%.1f MB · %.1f 秒)" % (out, size_mb, dur))

    cleanup(work, ass_path, keep_name)


if __name__ == "__main__":
    main()

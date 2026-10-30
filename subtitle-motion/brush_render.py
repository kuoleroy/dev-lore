# -*- coding: utf-8 -*-
"""毛笔书法巨字字幕：把字形轮廓直接画成 ASS 矢量路径（\\p1）。

不依赖 libass 的字体加载，因此志莽行书、马善政这些在本机无法被 libass 读到的
书法字体也能正常显示。代价是失去 \\k 标签，逐字染色改为按字拆分事件实现。
"""
import os
import random
import brush
from karaoke import W, H, ts, parse_lrc, split_lines

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")

CFG = {
    # 志莽行书：狂放行草，连笔多，气质最"手写"
    "brush-zhi": dict(
        fontfile=os.path.join(FONTS, "ZhiMangXing-Regular.ttf"),
        name="志莽行书",
        base_size=330, max_chars=4, margin=44,
        y=1010, line_gap=1.12, space_ratio=0.02,
        sung="&H001414E8", unsung="&H001414E8", unsung_alpha="&H82&",
        glow="&H003030FF",
        tilt=2.2, jitter=0.035,
        delay_ms=55, drop_px=64, entry_ms=230,
        pop=112,
        speed=3.4,
    ),
    # 马善政毛笔楷：笔画饱满、端正，力量感强
    "brush-ma": dict(
        fontfile=os.path.join(FONTS, "Ma Shan Zheng Regular.ttf"),
        name="马善政毛笔楷",
        base_size=330, max_chars=4, margin=44,
        y=1010, line_gap=1.12, space_ratio=0.04,
        sung="&H001414E8", unsung="&H001414E8", unsung_alpha="&H82&",
        glow="&H003030FF",
        tilt=1.6, jitter=0.03,
        delay_ms=55, drop_px=64, entry_ms=230,
        pop=110,
        speed=3.4,
    ),
}


def _fit(text, cfg):
    """算出统一字号与各行坐标（所有行用同一字号，短行居中）"""
    ff = cfg["fontfile"]
    base, sr = cfg["base_size"], cfg["space_ratio"]
    lines = split_lines(text, cfg["max_chars"])

    # 用基准字号量一遍，按最宽行缩放
    widths = [brush.measure(l, ff, base, base * sr)[0] for l in lines]
    avail = W - cfg["margin"] * 2
    k = min(1.0, avail / max(widths)) if max(widths) else 1.0
    size = base * k
    spacing = size * sr

    gap = size * cfg["line_gap"]
    total = gap * len(lines)
    top = cfg["y"] - total / 2
    # 汉字视觉中心略低于几何中心，基线再往下压 0.36em
    baselines = [top + gap * (i + 0.5) + size * 0.36 for i in range(len(lines))]

    out = []
    for line, yb in zip(lines, baselines):
        w, xs, _ = brush.measure(line, ff, size, spacing)
        x0 = (W - w) / 2
        out.append((line, yb, [x0 + x for x in xs]))
    return out, size


def build_brush(cfg, text, st, en, dur_cs):
    """逐字四层：投影 / 未唱淡字 / 唱到点亮 / 当前字红光"""
    ff = cfg["fontfile"]
    rows, size = _fit(text, cfg)
    rnd = random.Random(hash(text) & 0xFFFF)

    # 先把每个字的几何与时间算齐，发光层需要知道"下一个字何时点亮"
    chars = []
    idx = 0
    total = sum(len(r[0]) for r in rows)
    for line, yb, xs in rows:
        for ch, x in zip(line, xs):
            path, adv, _ = brush.glyph(ch, ff, size) if ch.strip() else (None, 0, 0)
            if not path:
                idx += 1
                continue
            t_entry = st + idx * cfg["delay_ms"] / 1000.0
            t_sing = st + dur_cs / 100.0 * (idx + 1) / total
            chars.append(dict(
                path=path, x=x, yb=yb,
                t_entry=t_entry,
                t_lit=max(t_sing, t_entry + cfg["entry_ms"] / 1000.0),
                tilt=rnd.uniform(-cfg["tilt"], cfg["tilt"]),
                sc=1.0 + rnd.uniform(-cfg["jitter"], cfg["jitter"]),
            ))
            idx += 1

    ev = []
    for i, c in enumerate(chars):
        tilt, sc = c["tilt"], c["sc"]
        fsc = cfg["pop"] * sc
        base = ("\\an7\\pos(%.1f,%.1f)\\p1\\bord0\\shad0\\frz%.2f" %
                (c["x"], c["yb"], tilt))
        nxt = chars[i + 1]["t_lit"] if i + 1 < len(chars) else en

        # 层 1：投影
        ev.append("Dialogue: 1,%s,%s,K,,0,0,0,,"
                  "{\\an7\\pos(%.1f,%.1f)\\p1\\1c&H000000&\\bord0\\shad0"
                  "\\frz%.2f\\alpha&H78&\\fscx%f\\fscy%f\\blur2}%s"
                  % (ts(c["t_entry"]), ts(en), c["x"] + 6, c["yb"] + 9,
                     tilt, fsc, fsc, c["path"]))

        # 层 2：整句淡红，从上方砸入
        ev.append("Dialogue: 2,%s,%s,K,,0,0,0,,"
                  "{%s\\1c%s\\alpha%s\\fscx%f\\fscy%f"
                  "\\t(0,%d,0.55,\\fscx%f\\fscy%f)}%s"
                  % (ts(c["t_entry"]), ts(en), base, cfg["sung"],
                     cfg["unsung_alpha"], fsc * 1.30, fsc * 1.30,
                     cfg["entry_ms"], fsc, fsc, c["path"]))

        # 层 3：唱到点亮
        ev.append("Dialogue: 3,%s,%s,K,,0,0,0,,"
                  "{%s\\1c%s\\alpha&HFF&\\fscx%f\\fscy%f"
                  "\\t(0,110,0.6,\\alpha&H00&)"
                  "\\t(0,160,0.45,\\fscx%f\\fscy%f)}%s"
                  % (ts(c["t_lit"]), ts(en), base, cfg["sung"],
                     fsc * 1.16, fsc * 1.16, fsc, fsc, c["path"]))

        # 层 4：正在唱的这个字泛红光，唱完熄灭
        if nxt > c["t_lit"] + 0.03:
            ev.append("Dialogue: 4,%s,%s,K,,0,0,0,,"
                      "{%s\\1c%s\\alpha&H58&\\blur9\\fscx%f\\fscy%f"
                      "\\t(0,%d,0.5,\\alpha&HFF&)}%s"
                      % (ts(c["t_lit"]), ts(nxt), base, cfg["glow"],
                         fsc * 1.18, fsc * 1.18,
                         int(min(520, (nxt - c["t_lit"]) * 1000 * 0.82)),
                         c["path"]))
    return ev


def header():
    return "\n".join([
        "[Script Info]", "ScriptType: v4.00+",
        "PlayResX: %d" % W, "PlayResY: %d" % H,
        "WrapStyle: 2", "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: K,Microsoft YaHei,100,&H00FFFFFF,&H00FFFFFF,&H00000000,"
        "&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text",
    ])


def build(style_name, lrc, t_from=None, t_to=None, shift=None, out=None):
    cfg = CFG[style_name]
    lines = parse_lrc(lrc)
    if t_from is not None:
        lines = [(t, s) for (t, s) in lines if t >= t_from - 0.05]
    if t_to is not None:
        lines = [(t, s) for (t, s) in lines if t <= t_to]
    if not lines:
        raise SystemExit("窗口内没有歌词行")
    shift = shift or 0.0

    ev = []
    n = len(lines)
    for i, (st, text) in enumerate(lines):
        nxt = lines[i + 1][0] if i + 1 < n else st + 7.0
        est = len(text) / cfg["speed"]
        dur = min(est * 1.10, max(nxt - st - 0.10, est * 0.55))
        if dur < 0.8:
            dur = min(est, max(nxt - st, 0.8))
        dur_cs = int(round(dur * 100))

        show_end = min(nxt + 0.12, st + dur + 1.6)
        if i + 1 >= n:
            show_end = st + dur + 2.2

        ev += build_brush(cfg, text, st - shift, show_end - shift, dur_cs)

    content = header() + "\n" + "\n".join(ev) + "\n"
    out = out or os.path.join(HERE, "_style_%s.ass" % style_name)
    open(out, "w", encoding="utf-8-sig").write(content)
    print("  %-10s %2d 行 / %3d 事件 -> %s"
          % (style_name, n, len(ev), os.path.basename(out)))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="毛笔书法巨字字幕（矢量轮廓），输出 *_brush-*.ass")
    ap.add_argument("--lrc", required=True, help="歌词 LRC 路径（UTF-8）")
    ap.add_argument("--from", dest="t_from", type=float, help="起始秒")
    ap.add_argument("--to", dest="t_to", type=float, help="结束秒")
    ap.add_argument("--shift", type=float, help="时间轴整体平移")
    a = ap.parse_args()
    for k in CFG:
        build(k, a.lrc, t_from=a.t_from, t_to=a.t_to, shift=a.shift)

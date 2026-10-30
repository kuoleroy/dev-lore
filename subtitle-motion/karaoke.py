# -*- coding: utf-8 -*-
"""炫酷 MV 字幕引擎 —— 从行级 LRC 生成逐字动效 ASS（10 种风格）

用法:
    python karaoke.py --lrc 歌词.lrc --style all                # 全部风格，竖屏
    python karaoke.py --lrc 歌词.lrc --video 片子.mp4 --style neon
    python karaoke.py --lrc 歌词.lrc --size 1920x1080 --style neon,huge

十种风格
    neon    逐字扫色（卡拉OK）＋冷光晕，最稳的"跟唱"效果
    slam    整行砸入回弹，重拍冲击
    cine    居中大字＋关键词点亮（--keywords 指定），电影片名质感
    fadeup  逐字上浮＋单字点时放大，动态感最强
    ink     墨色细字、宽字距，日系电影字幕质感
    huge    全屏巨字，占满画宽，逐字砸入
    vtext   竖排古风，从右往左一列，字字落下
    type    打字机，逐字硬切
    blur    从糊到清，镜头对焦感
    mirror  倒影，字落在玻璃/水面上

技术要点
  · 染色用 \\kf（卡拉OK sweep），SecondaryColour=未唱 / PrimaryColour=已唱
  · \\1c 是累积标签，必须每字显式重置，否则颜色会串到后面所有字
  · 中文全角字宽≈字号，字级定位可直接按 size+spacing 累加算 X
  · 画布由 set_canvas() 按目标视频换算，位置按高度、字号按宽高双系数缩放
"""
import argparse
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920          # 当前画布，set_canvas() 可改
SCALE = 1.0                # 垂直缩放系数（位置按它）
FSCALE = 1.0               # 字号缩放系数（字号/描边/字距按它）

# 跟字号走的参数
_FONT_KEYS = ("size", "spacing", "border", "shadow",
              "glow_blur", "glow_border", "max_size", "drop_px")
# 跟画布高度走的位置参数
_POS_KEYS = ("y", "margin")


def set_canvas(w, h):
    """按目标视频分辨率设置画布。基准是 1080x1920（竖屏）。

    位置按高度缩放；字号除高度外还参考宽度，否则横屏上字会瘦得像小字报
    （竖屏 70px 占宽 6.5%，横屏若只按高度缩放只剩 2%）。
    """
    global W, H, SCALE, FSCALE
    W, H = int(w), int(h)
    SCALE = H / 1920.0
    FSCALE = max(SCALE, (W / 1080.0) * 0.52)
    return W, H, SCALE


def probe_size(video):
    """用 ffprobe 读视频分辨率（自动处理旋转元数据）"""
    import subprocess, json
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:stream_tags=rotate:stream_side_data=rotation",
         "-of", "json", video],
        capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffprobe 读取失败: %s" % r.stderr[-300:])
    st = json.loads(r.stdout)["streams"][0]
    w, h = int(st["width"]), int(st["height"])
    rot = 0
    for sd in st.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = abs(int(float(sd["rotation"])))
    if not rot and st.get("tags", {}).get("rotate"):
        rot = abs(int(float(st["tags"]["rotate"])))
    if rot % 180 == 90:
        w, h = h, w
    return w, h


def scaled(cfg):
    """返回按当前画布缩放过的参数副本：字号类走 FSCALE，位置类走 SCALE"""
    c = dict(cfg)
    for k in _FONT_KEYS:
        if k in c and isinstance(c[k], (int, float)):
            c[k] = c[k] * FSCALE
    for k in _POS_KEYS:
        if k in c and isinstance(c[k], (int, float)):
            c[k] = c[k] * SCALE
    # 竖排的横向位置按画宽比例，不按高度
    if "x" in c:
        c["x_ratio"] = c["x"] / 1080.0
        c["x"] = W * c["x_ratio"]
    # intro 里的位置占位符按当前画布展开
    if "{" in c.get("intro", ""):
        c["intro"] = c["intro"].format(
            CX=W / 2.0,
            Y0=c["y"] + 22 * SCALE,
            Y1=c["y"] - 2 * SCALE,
        )
    return c

PUNCT = "，。！？、；：“”‘’（）…—《》·,.!?;:"


def cweight(ch):
    """标点不发音，占时短"""
    return 0.32 if ch in PUNCT else 1.0


def is_wide(ch):
    """全角判定：中文/标点按字宽算，ASCII 按半宽"""
    return ord(ch) > 0x2000


def parse_lrc(path):
    out = []
    for ln in open(path, encoding="utf-8-sig"):
        m = re.match(r"\[(\d+):(\d+\.\d+)\](.*)", ln.strip())
        if not m:
            continue
        t = int(m.group(1)) * 60 + float(m.group(2))
        txt = m.group(3).strip()
        if not txt:
            continue
        if re.match(r"^(作词|作曲|编曲|制作|演唱|混音|母带|出品)", txt):
            continue
        out.append((t, txt))
    return out


def ts(t):
    t = max(t, 0)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def kf_string(text, dur_cs):
    """把一句话拆成 {\\kfNN}字 序列，按字重分配厘秒，末字补齐误差"""
    if dur_cs <= 0:
        dur_cs = 1
    ws = [cweight(c) for c in text]
    total = sum(ws) or 1
    parts, used = [], 0
    for i, (c, w) in enumerate(zip(text, ws)):
        cs = max(int(round(w / total * dur_cs)), 1)
        if i == len(text) - 1:
            cs = max(dur_cs - used, 1)
        used += cs
        parts.append(("\\kf%d}%s" % (cs, c), cs))
    return parts


def layout(text, size, spacing):
    """返回每个字的中心 X（an5 居中锚），中文全角、ASCII 半宽"""
    widths = [size * (1.0 if is_wide(c) else 0.56) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = W / 2 - total / 2
    out = []
    for w in widths:
        out.append(x + w / 2)
        x += w + spacing
    return out


STYLES = {
    # ---------- 1 逐字扫色：卡拉OK 本体 ----------
    "neon": dict(
        font="Microsoft YaHei", size=70, bold=-1, spacing=5,
        y=1440, an=5,
        sung="&H00FFFFFF", unsung="&H0068707A",
        outline="&H00080A0C", border=4.4, shadow=2.2,
        glow_color="&H0090D8FF", glow_blur=28, glow_border=14,
        intro="\\fad(240,300)\\fscx107\\fscy107\\t(0,300,\\fscx100\\fscy100)",
        speed=3.4,
    ),
    # ---------- 2 砸入回弹 ----------
    "slam": dict(
        font="Source Han Sans SC", size=82, bold=-1, spacing=3,
        y=1396, an=5,
        sung="&H00FFFFFF", unsung="&H004E545C",
        outline="&H00060608", border=5.2, shadow=2.8,
        glow_color=None, glow_blur=18, glow_border=10,
        intro="\\fad(60,360)\\fscx130\\fscy130\\frz-2.2"
              "\\t(0,240,\\fscx100\\fscy100\\frz0)"
              "\\t(240,360,\\fscx105\\fscy105)\\t(360,540,\\fscx100\\fscy100)",
        speed=3.6,
    ),
    # ---------- 3 电影大字：关键词点亮 ----------
    "cine": dict(
        font="Source Han Sans SC", size=76, bold=-1, spacing=7,
        y=1050, an=5,
        sung="&H00F7F7F7", unsung="&H00666C74",
        outline="&H00101012", border=3.8, shadow=2.6,
        glow_color="&H00384A54", glow_blur=34, glow_border=10,
        intro="\\fad(420,420)\\move({CX},{Y0},{CX},{Y1},0,2600)",
        speed=3.2,
        keywords=[],               # 用 --keywords "词1,词2" 指定要点亮的词
        kw_color="&H00307ED6", kw_scale=114,
    ),
    # ---------- 4 逐字浮起点亮 ----------
    "fadeup": dict(
        font="Source Han Sans SC", size=74, bold=-1, spacing=4,
        y=1420, an=5,
        sung="&H00FFFFFF", unsung="&H005A6470",
        outline="&H0008080A", border=4.0, shadow=2.0,
        glow_color="&H0070B8E8", glow_blur=24, glow_border=10,
        intro="", speed=3.4,
        per_char=True,
    ),
    # ---------- 5 墨色细字：宽字距、细字重，日系电影字幕质感 ----------
    "ink": dict(
        font="Noto Sans SC", size=64, bold=0, spacing=14,
        y=1330, an=5,
        sung="&H00181A1E", unsung="&H0092969C",
        outline="&H40FFFFFF", border=1.2, shadow=0,
        glow_color="&H50FFFFFF", glow_blur=16, glow_border=6,
        intro="\\fad(520,520)\\fscx100\\fscy100",
        speed=3.2,
    ),
    # ---------- 6 全屏巨字：占满画宽、纯红毛笔、逐字砸入 ----------
    "huge": dict(
        font="Tiejili SC", size=200, bold=0, spacing=-4,
        y=980, an=5,
        sung="&H001414E8", unsung="&H000A080E",
        outline="&H30000000", border=1.6, shadow=0,
        glow_color=None, glow_blur=0, glow_border=0,
        intro="", speed=3.4,
        huge=True, max_chars=5, max_size=340, margin=30,
                delay_ms=70, drop_px=52,
    ),
    # ---------- 7 竖排古风：从右往左一列，字字落下 ----
    "vtext": dict(
        font="Source Han Sans SC", size=72, bold=-1, spacing=0,
        y=330, an=5, x=884, step=1.10,
        sung="&H00FFFFFF", unsung="&H00808A92",
        outline="&H00101418", border=3.4, shadow=0,
        glow_color=None, glow_blur=0, glow_border=0,
        intro="", speed=3.0, alt="vtext",
    ),
    # ---------- 8 打字机：逐字硬切，像被敲出来 ----
    "type": dict(
        font="Microsoft YaHei", size=70, bold=0, spacing=7,
        y=1446, an=5,
        sung="&H00FFFFFF", unsung="&H008A9098",
        outline="&H00101012", border=2.6, shadow=0,
        glow_color=None, glow_blur=0, glow_border=0,
        intro="", speed=3.0, alt="type",
    ),
    # ---------- 9 模糊聚焦：从糊到清，镜头对焦感 ----
    "blur": dict(
        font="Source Han Sans SC", size=76, bold=-1, spacing=6,
        y=1440, an=5,
        sung="&H00FFFFFF", unsung="&H00808A92",
        outline="&H00101418", border=2.8, shadow=0,
        glow_color=None, glow_blur=0, glow_border=0,
        intro="", speed=3.2, alt="blur",
    ),
    # ---------- 10 倒影：字落在玻璃/水面上 ----
    "mirror": dict(
        font="Source Han Sans SC", size=70, bold=-1, spacing=6,
        y=1420, an=5,
        sung="&H00F5F7FA", unsung="&H00808A92",
        outline="&H00101418", border=2.6, shadow=0,
        glow_color=None, glow_blur=0, glow_border=0,
        intro="", speed=3.0, alt="mirror",
    ),
}


def header(cfg):
    base = [
        "[Script Info]", "ScriptType: v4.00+",
        "PlayResX: %d" % W, "PlayResY: %d" % H,
        "WrapStyle: 2", "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: K,%s,%d,%s,%s,%s,&HA0000000,%d,0,0,0,100,100,%d,0,1,%.1f,%.1f,%d,40,40,%d,1"
        % (cfg["font"], cfg["size"], cfg["sung"], cfg["unsung"],
           cfg["outline"], cfg["bold"], cfg["spacing"], cfg["border"],
           cfg["shadow"], cfg["an"], cfg["y"]),
        "Style: G,%s,%d,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,%d,0,0,0,"
        "100,100,%d,0,1,0,0,%d,40,40,%d,1"
        % (cfg["font"], cfg["size"], cfg["bold"], cfg["spacing"],
           cfg["an"], cfg["y"]),
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text",
    ]
    return "\n".join(base)


def build(style_name, lrc, t_from=None, t_to=None, shift=None, out=None,
          keywords=None):
    """生成某一个风格的 ASS。keywords 只对 cine 有效，用于点亮关键词。"""
    cfg = scaled(STYLES[style_name])
    if keywords:
        cfg["keywords"] = list(keywords)
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

        a, b = ts(st - shift), ts(show_end - shift)

        if cfg.get("huge"):
            ev += build_huge(cfg, text, st - shift, show_end - shift, dur_cs)
        elif cfg.get("alt"):
            ev += build_alt(cfg, text, st - shift, show_end - shift, dur_cs)
        elif cfg.get("per_char"):
            ev += build_per_char(cfg, text, st - shift, show_end - shift, dur_cs)
        else:
            ev += build_karaoke(cfg, text, a, b, dur_cs)

    content = header(cfg) + "\n" + "\n".join(ev) + "\n"
    out = out or os.path.join(HERE, "_style_%s.ass" % style_name)
    d = os.path.dirname(out)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    open(out, "w", encoding="utf-8-sig").write(content)
    print("  %-7s %2d 行 / %2d 事件 -> %s"
          % (style_name, n, len(ev), os.path.basename(out)))
    return out


def build_karaoke(cfg, text, a, b, dur_cs):
    """整行一个事件，\\kf 逐字扫色 + 发光层"""
    ev = []
    intro = cfg["intro"]
    pos = "" if "\\move(" in intro else "\\pos(%.1f,%d)" % (W / 2.0, cfg["y"])
    pairs = kf_string(text, dur_cs)

    body = ""
    for (frag, cs) in pairs:
        ch = frag.split("}")[-1]
        hit = cfg.get("keywords") and any(ch in kw for kw in cfg["keywords"])
        if hit:
            body += "{\\kf%d\\fscx%d\\fscy%d\\1c%s}%s" % (
                cs, cfg["kw_scale"], cfg["kw_scale"], cfg["kw_color"], ch)
        elif cfg.get("keywords"):
            body += "{\\kf%d\\fscx100\\fscy100\\1c%s}%s" % (cs, cfg["sung"], ch)
        else:
            body += "{\\kf%d}%s" % (cs, ch)

    if cfg["glow_color"]:
        ev.append("Dialogue: 1,%s,%s,G,,0,0,0,,"
                  "{%s%s\\1c%s\\bord%d\\shad0\\blur%d\\alpha&H30&}%s"
                  % (a, b, pos, intro, cfg["glow_color"],
                     cfg["glow_border"], cfg["glow_blur"], body))
    ev.append("Dialogue: 3,%s,%s,K,,0,0,0,,{%s%s\\1c%s}%s"
              % (a, b, pos, intro, cfg["sung"], body))
    return ev


def build_per_char(cfg, text, st, en, dur_cs):
    """逐字上浮 + 点中放大：每个字独立定位，暗底层常驻，亮字层按时点亮"""
    ev = []
    xs = layout(text, cfg["size"], cfg["spacing"])
    pairs = kf_string(text, dur_cs)
    y = cfg["y"]

    # 暗底字：整句常在，让"未唱"有轮廓、不跳动
    sa, sb = ts(st), ts(en)
    for ch, x in zip(text, xs):
        ev.append("Dialogue: 1,%s,%s,K,,0,0,0,,"
                  "{\\pos(%.1f,%d)\\alpha&H20&\\1c%s\\blur0.6}%s"
                  % (sa, sb, x, y, cfg["unsung"], ch))

    t = st
    for (frag, cs), ch, x in zip(pairs, text, xs):
        d = cs / 100.0
        s0 = t
        s1 = en
        if ch.strip():
            # 亮字层：从 y+14 上浮到 y，缩放 1.18 → 1.0，同时淡入
            ev.append(
                "Dialogue: 3,%s,%s,K,,0,0,0,,"
                "{\\move(%.1f,%d,%.1f,%d,0,190)\\alpha&HFF&"
                "\\fscx118\\fscy118"
                "\\t(0,95,\\alpha&H00&)\\t(0,180,\\fscx100\\fscy100)"
                "\\1c%s}%s"
                % (ts(s0), ts(s1), x, y + 14 * FSCALE, x, y, cfg["sung"], ch))
        t += d
    return ev


def build_alt(cfg, text, st, en, dur_cs):
    """逐字替代风格：竖排 / 打字机 / 模糊聚焦 / 倒影"""
    mode = cfg["alt"]
    ev = []
    n = max(1, len(text))
    if mode == "vtext":
        xs = [cfg["x"]] * n
        ys = [cfg["y"] + i * cfg["size"] * cfg["step"] for i in range(n)]
    else:
        xs = layout(text, cfg["size"], cfg["spacing"])
        ys = [cfg["y"]] * n

    pairs = kf_string(text, dur_cs)
    t = st
    for i, ch in enumerate(text):
        cs = pairs[i][1] if i < len(pairs) else dur_cs / n
        d = cs / 100.0
        if not ch.strip():
            t += d
            continue
        x, y = xs[i], ys[i]

        # 未唱：淡影，不抢视线
        ev.append("Dialogue: 1,%s,%s,K,,0,0,0,,"
                  "{\\pos(%.1f,%.1f)\\alpha&H38&\\1c%s}%s"
                  % (ts(st), ts(en), x, y, cfg["unsung"], ch))

        if mode == "type":
            anim = "\\alpha&HFF&\\t(0,1,\\alpha&H00&)"
        elif mode == "blur":
            anim = ("\\alpha&HFF&\\blur16\\fscx106\\fscy106"
                    "\\t(0,170,\\blur0\\alpha&H00&)"
                    "\\t(0,220,\\fscx100\\fscy100)")
        elif mode == "vtext":
            anim = ("\\alpha&HFF&\\move(%.1f,%.1f,%.1f,%.1f,0,170)"
                    "\\t(0,110,\\alpha&H00&)" % (x, y - 12 * FSCALE, x, y))
        else:
            anim = "\\alpha&HFF&\\t(0,110,\\alpha&H00&)"

        ev.append("Dialogue: 3,%s,%s,K,,0,0,0,,"
                  "{\\pos(%.1f,%.1f)%s\\1c%s}%s"
                  % (ts(t), ts(en), x, y, anim, cfg["sung"], ch))

        # 倒影：垂直翻转压到下方，半透明 + 模糊
        if mode == "mirror":
            ev.append("Dialogue: 0,%s,%s,K,,0,0,0,,"
                      "{\\pos(%.1f,%.1f)\\fscy-100\\alpha&H5A&"
                      "\\blur2.4\\1c%s}%s"
                      % (ts(t), ts(en), x, y + cfg["size"] * 0.88,
                         cfg["sung"], ch))
        t += d
    return ev


def split_lines(text, maxc):
    """按字数均分成若干行，避免巨字超宽"""
    if len(text) <= maxc:
        return [text]
    n = (len(text) + maxc - 1) // maxc
    per = (len(text) + n - 1) // n
    return [text[i:i + per] for i in range(0, len(text), per)]


def build_huge(cfg, text, st, en, dur_cs):
    """全屏巨字：字号自动撑满画宽，逐字砸入，带斜切回正

    每行字数随画幅自适应：竖屏 4-5 字一行（窄而高），
    横屏一行能放更多，否则三行会把 1080 高撑满。
    """
    ev = []
    per_line = cfg["max_chars"]
    if W > H:
        per_line = max(per_line, 8 if W / H < 2.0 else 10)
    lines = split_lines(text, per_line)
    maxw = W - cfg["margin"] * 2
    per = max(len(l) for l in lines)
    uni = min(cfg["max_size"], int(maxw / max(1, per) * 0.94))
    sizes = [uni] * len(lines)
    gap = 1.12
    total_h = sum(sz * gap for sz in sizes)
    top = cfg["y"] - total_h / 2
    idx = 0
    for li, (line, size) in enumerate(zip(lines, sizes)):
        cy = top + sum(sz * gap for sz in sizes[:li]) + size * gap / 2
        widths = [size * (1.0 if is_wide(c) else 0.56) for c in line]
        tw = sum(widths) + cfg["spacing"] * max(0, len(line) - 1)
        x = W / 2 - tw / 2
        for c, w in zip(line, widths):
            cx = x + w / 2
            x += w + cfg["spacing"]
            t0 = st + idx * cfg["delay_ms"] / 1000.0
            idx += 1
            if not c.strip():
                continue
            tilt = -3.5 if (idx % 2) else 3.5
            body = ("{\\an5\\fs%d\\move(%.1f,%.1f,%.1f,%.1f,0,150)"
                    "\\alpha&HFF&\\fscx158\\fscy158\\frz%.1f"
                    "\\t(0,80,\\alpha&H00&)"
                    "\\t(0,200,1.55,\\fscx100\\fscy100\\frz0)"
                    "\\1c%s}%s") % (size, cx, cy - cfg["drop_px"], cx, cy,
                                     tilt, cfg["sung"], c)
            ev.append("Dialogue: 3,%s,%s,K,,0,0,0,,%s" % (ts(t0), ts(en), body))
    return ev


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="根据 LRC 生成卡拉OK字幕 ASS。默认画布 1080x1920，"
                    "用 --video 或 --size 自动适配任意分辨率。")
    ap.add_argument("--lrc", required=True, help="歌词 LRC 路径（UTF-8）")
    ap.add_argument("--style", default="all",
                    help="风格名，或 all 生成全部；也可逗号分隔多个")
    ap.add_argument("--video", help="目标视频路径，自动探测分辨率")
    ap.add_argument("--size", help="手动指定画布，格式 1920x1080")
    ap.add_argument("--from", dest="t_from", type=float, help="起始秒")
    ap.add_argument("--to", dest="t_to", type=float, help="结束秒")
    ap.add_argument("--shift", type=float, help="时间轴整体平移（做片段测试用）")
    ap.add_argument("--keywords",
                    help="cine 风格要点亮的关键词，逗号分隔，如 \"离开,再见\"")
    ap.add_argument("--outdir", default=HERE, help="ASS 输出目录")
    ap.add_argument("--prefix", default="_style_", help="输出文件名前缀")
    a = ap.parse_args()

    # 画布：--video > --size > 默认竖屏
    if a.video:
        w, h = probe_size(a.video)
        print("探测到画面 %dx%d（缩放系数 %.3f）" % (w, h, h / 1920.0))
        set_canvas(w, h)
    elif a.size:
        try:
            w, h = [int(x) for x in a.size.lower().replace("*", "x").split("x")]
        except Exception:
            raise SystemExit("--size 格式应为 1920x1080")
        print("指定画面 %dx%d（缩放系数 %.3f）" % (w, h, h / 1920.0))
        set_canvas(w, h)

    names = list(STYLES) if a.style == "all" else [
        x.strip() for x in a.style.split(",") if x.strip()]
    kws = [x.strip() for x in (a.keywords or "").replace("，", ",").split(",")
           if x.strip()]
    for nm in names:
        if nm not in STYLES:
            raise SystemExit("没有这个风格: %s（可用: %s）"
                             % (nm, ", ".join(STYLES)))
        build(nm, a.lrc, a.t_from, a.t_to, a.shift,
              out=os.path.join(a.outdir, a.prefix + nm + ".ass"),
              keywords=kws)

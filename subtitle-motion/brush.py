# -*- coding: utf-8 -*-
"""把 TTF 字形轮廓抽成 ASS 矢量绘图命令（\\p1），绕开 libass 的字体加载。

用途：libass 在本机只认带 hinting 的字体，书法字体全被回退成黑体。
把轮廓直接画出来，任何字体都能用，代价是失去 \\k 标签，染色改为按字独立事件。
"""
import os
import math
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

HERE = os.path.dirname(os.path.abspath(__file__))
_CACHE = {}


class _AssPen(BasePen):
    """fontTools 画笔 → ASS 绘图命令。y 轴翻转（字体向上，ASS 向下）。"""

    def __init__(self, glyphSet, scale):
        super().__init__(glyphSet)
        self.scale = scale
        self.cmds = []

    def _pt(self, p):
        return p[0] * self.scale, -p[1] * self.scale

    def _moveTo(self, p):
        self.cmds.append("m %s" % _f(*self._pt(p)))

    def _lineTo(self, p):
        self.cmds.append("l %s" % _f(*self._pt(p)))

    def _curveToOne(self, p1, p2, p3):
        a, b, c = self._pt(p1), self._pt(p2), self._pt(p3)
        self.cmds.append("b %s %s %s" % (_f(*a), _f(*b), _f(*c)))

    def _qCurveToOne(self, p1, p2):
        # 二次 → 三次（基画笔此方法默认是折线，这里升级成真曲线）
        ctrl = self._getCurrentPoint()
        c1 = (ctrl[0] + 2.0 / 3.0 * (p1[0] - ctrl[0]),
              ctrl[1] + 2.0 / 3.0 * (p1[1] - ctrl[1]))
        c2 = (p2[0] + 2.0 / 3.0 * (p1[0] - p2[0]),
              p2[1] + 2.0 / 3.0 * (p1[1] - p2[1]))
        self._curveToOne(c1, c2, p2)

    def _closePath(self):
        pass        # 多轮廓用各自的 m 分隔，libass 自动闭合并填充

    def _endPath(self):
        pass


def _f(x, y):
    return "%.1f %.1f" % (x, y)


def load(font_path):
    key = os.path.abspath(font_path)
    if key not in _CACHE:
        f = TTFont(font_path, lazy=False)
        _CACHE[key] = dict(font=f, gs=f.getGlyphSet(),
                           cmap=f.getBestCmap(),
                           upem=f["head"].unitsPerEm,
                           asc=f["hhea"].ascent,
                           desc=f["hhea"].descent)
    return _CACHE[key]


_GCACHE = {}


def glyph(ch, font_path, size):
    """返回 (ass_drawing, advance_px, bbox)。drawing 已按 size 缩放，原点在字基线左端。"""
    key = (ch, os.path.abspath(font_path), round(size, 2))
    if key in _GCACHE:
        return _GCACHE[key]
    r = _glyph(ch, font_path, size)
    _GCACHE[key] = r
    return r


def _glyph(ch, font_path, size):
    d = load(font_path)
    gname = d["cmap"].get(ord(ch))
    if gname is None:
        return None, size * 0.5, (0, 0, 0, 0)
    scale = size / float(d["upem"])
    pen = _AssPen(d["gs"], scale)
    d["gs"][gname].draw(pen)
    adv = d["gs"][gname].width * scale
    path = " ".join(pen.cmds)

    # 用字体单位算 bbox，用于垂直居中
    from fontTools.pens.boundsPen import BoundsPen
    bp = BoundsPen(d["gs"])
    d["gs"][gname].draw(bp)
    if bp.bounds:
        x0, y0, x1, y1 = bp.bounds
        bbox = (x0 * scale, -y1 * scale, x1 * scale, -y0 * scale)
    else:
        bbox = (0, -size, size, 0)
    return path, adv, bbox


def measure(text, font_path, size, spacing=0.0):
    """整行宽度与各字左端偏移。"""
    xs, advs = [], []
    x = 0.0
    for ch in text:
        xs.append(x)
        _, adv, _ = glyph(ch, font_path, size)
        advs.append(adv)
        x += adv + spacing
    w = x - spacing if text else 0.0
    return w, xs, advs


def line_bbox(text, font_path, size, spacing=0.0):
    """整行的垂直范围（相对基线，向下为正）。"""
    top, bot = 0.0, 0.0
    for ch in text:
        _, _, bb = glyph(ch, font_path, size)
        top = min(top, bb[1])
        bot = max(bot, bb[3])
    return top, bot

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
webp2png.py —— 把 WebP 批量转成 PNG（无损、保留透明通道）

用法：
    python webp2png.py 图片1.webp 图片2.webp D:\\某个文件夹
    python webp2png.py .                 # 当前目录下所有 webp
选项：
    -o, --out DIR     输出到指定目录（默认与原文件同目录）
    --overwrite       覆盖已存在的同名 png（默认跳过）
    --no-keep-size    不保留原尺寸（默认就是保留，此项无实际作用，留作兼容）

也可以直接把文件/文件夹拖到 拖进来转PNG.bat 上。
"""

import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("缺少 Pillow：请先执行  pip install pillow")


def collect(paths):
    """展开文件与目录，返回 (webp 文件列表, 跳过的非 webp 数量)"""
    files, skipped = [], 0
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for n in sorted(names):
                    if n.lower().endswith(".webp"):
                        files.append(os.path.join(root, n))
        elif os.path.isfile(p):
            if p.lower().endswith(".webp"):
                files.append(p)
            else:
                skipped += 1
        else:
            print(f"[跳过] 路径不存在: {p}")
            skipped += 1
    return files, skipped


def convert(src, out_dir, overwrite=False):
    name = os.path.splitext(os.path.basename(src))[0] + ".png"
    dst_dir = out_dir or os.path.dirname(os.path.abspath(src))
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, name)

    if os.path.exists(dst) and not overwrite:
        print(f"[跳过] 已存在: {name}")
        return "skip"

    try:
        with Image.open(src) as im:
            im.load()
            has_alpha = im.mode in ("RGBA", "LA", "PA") or \
                (im.mode == "P" and "transparency" in im.info)
            # 有透明 → RGBA；否则一律 RGB（避免带无用 alpha 让文件变大）
            out = im.convert("RGBA" if has_alpha else "RGB")
            out.save(dst, "PNG", optimize=True)
        size_kb = os.path.getsize(dst) / 1024
        print(f"[完成] {name}  {out.size[0]}x{out.size[1]}  {size_kb:.0f} KB  {'RGBA' if has_alpha else 'RGB'}")
        return "ok"
    except Exception as e:
        print(f"[失败] {os.path.basename(src)}: {e}")
        return "fail"


def main():
    ap = argparse.ArgumentParser(description="WebP 批量转 PNG")
    ap.add_argument("paths", nargs="*", help="webp 文件或所在文件夹")
    ap.add_argument("-o", "--out", default=None, help="输出目录")
    ap.add_argument("--overwrite", action="store_true", help="覆盖同名 png")
    args = ap.parse_args()

    if not args.paths:
        args.paths = ["."]

    files, skipped = collect(args.paths)
    if not files:
        print("没有找到 .webp 文件。")
        return

    print(f"共 {len(files)} 个 webp 待转换" + (f"（另有 {skipped} 个非 webp 已忽略）" if skipped else ""))
    print("-" * 52)

    ok = skip = fail = 0
    for f in files:
        r = convert(f, args.out, args.overwrite)
        if r == "ok":
            ok += 1
        elif r == "skip":
            skip += 1
        else:
            fail += 1

    print("-" * 52)
    print(f"成功 {ok}    跳过 {skip}    失败 {fail}")


if __name__ == "__main__":
    main()

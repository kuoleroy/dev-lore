#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式删除 EPUB 阅读顺序前 N 个文档
运行后输入文件夹路径，自动搜索该目录下所有 epub 文件
所有选项均通过终端交互输入，无写死参数
"""
import os
import shutil
import zipfile
from lxml import etree


def ns(tag, nsmap):
    return f"{{{nsmap['opf']}}}{tag}"


def process(epub_path, count, dry_run=False, overwrite=False):
    """
    overwrite=True  → 直接覆盖原文件
    overwrite=False → 生成 _cleaned.epub，原文件保留
    """
    if not os.path.isfile(epub_path):
        print(f"  [跳过] 文件不存在: {epub_path}")
        return False

    base, ext = os.path.splitext(epub_path)
    tmp = base + "_unzip_tmp"

    if overwrite:
        out = epub_path + ".tmp.epub"
    else:
        out = base + "_cleaned" + ext

    # 1. 解压
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    with zipfile.ZipFile(epub_path) as z:
        z.extractall(tmp)

    # 2. 找 content.opf
    container = etree.parse(os.path.join(tmp, "META-INF", "container.xml")).getroot()
    opf_path = container.xpath(
        "//c:rootfile/@full-path",
        namespaces={"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
    )[0]
    opf_full = os.path.join(tmp, opf_path)
    opf_dir = os.path.dirname(opf_full)

    opf = etree.parse(opf_full)
    root = opf.getroot()
    nsmap = {"opf": root.nsmap.get("opf", "http://www.idpf.org/2007/opf")}

    manifest = root.find(ns("manifest", nsmap))
    spine = root.find(ns("spine", nsmap))
    itemrefs = spine.findall(ns("itemref", nsmap))

    actual_count = min(count, len(itemrefs))
    if actual_count == 0:
        print(f"  [跳过] 内部没有可删除的文档")
        shutil.rmtree(tmp)
        return False

    to_remove = itemrefs[:actual_count]

    removed = []
    for ref in to_remove:
        idref = ref.get("idref")
        item = manifest.find(f'{ns("item", nsmap)}[@id="{idref}"]')
        if item is not None:
            href = item.get("href")
            fpath = os.path.join(opf_dir, href.split("#")[0])
            removed.append(href)
            if not dry_run:
                if os.path.exists(fpath):
                    os.remove(fpath)
                manifest.remove(item)
        if not dry_run:
            spine.remove(ref)

    # 3. 清理 nav/toc
    if not dry_run and removed:
        for xml_f in [os.path.join(opf_dir, "nav.xhtml"),
                      os.path.join(opf_dir, "toc.ncx")]:
            if os.path.exists(xml_f):
                try:
                    t = etree.parse(xml_f)
                    for a in t.xpath("//*[@href]"):
                        if a.get("href").split("#")[0] in removed:
                            a.getparent().remove(a)
                    t.write(xml_f, xml_declaration=True, encoding="utf-8")
                except Exception:
                    pass
        opf.write(opf_full, xml_declaration=True, encoding="utf-8")

    print(f"\n  [{'预览' if dry_run else '完成'}] {os.path.basename(epub_path)}")
    print(f"  删除前 {actual_count} 个文档:")
    for r in removed:
        print(f"    - {r}")

    if not dry_run and removed:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
            for root_d, _, files in os.walk(tmp):
                for f in files:
                    full = os.path.join(root_d, f)
                    arc = os.path.relpath(full, tmp)
                    if arc == "mimetype":
                        continue
                    z.write(full, arc, zipfile.ZIP_DEFLATED)
            z.write(os.path.join(tmp, "mimetype"), "mimetype", zipfile.ZIP_STORED)
        shutil.rmtree(tmp)

        if overwrite:
            # 覆盖原文件：把临时文件移过去
            os.replace(out, epub_path)
            print(f"  -> 已覆盖原文件")
        else:
            print(f"  -> 输出: {out}")

    elif dry_run:
        shutil.rmtree(tmp, ignore_errors=True)

    return True


def find_epubs(folder):
    """递归搜索文件夹内所有 .epub 文件"""
    epubs = []
    for root_d, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith('.epub'):
                epubs.append(os.path.join(root_d, f))
    return epubs


def main():
    print("=" * 55)
    print("       EPUB 前 N 页删除工具（交互模式）")
    print("=" * 55)

    # ---- 1. 输入文件夹路径 ----
    print("\n请输入包含 epub 文件的文件夹路径")
    print("  （Windows 示例: E:\\books）")
    print("  （脚本会递归搜索该文件夹下所有 .epub 文件）")
    folder = input("  >>> 文件夹路径: ").strip().strip('"').strip("'")

    if not folder:
        print("未输入路径，退出。")
        return

    if not os.path.isdir(folder):
        print(f"  [错误] 该路径不是有效文件夹: {folder}")
        input("\n按 Enter 键退出...")
        return

    # ---- 2. 搜索 epub 文件 ----
    print("\n正在搜索 epub 文件...")
    epubs = find_epubs(folder)

    if not epubs:
        print("  该文件夹下没有找到任何 .epub 文件。")
        input("\n按 Enter 键退出...")
        return

    print(f"\n  找到 {len(epubs)} 个 epub 文件:")
    for ep in epubs:
        rel = os.path.relpath(ep, folder)
        print(f"    - {rel}")

    # ---- 3. 输入删除页数 ----
    while True:
        try:
            count_input = input("\n请输入要删除的前几个文档（阅读顺序）: ").strip()
            count = int(count_input)
            if count <= 0:
                print("  请输入大于 0 的数字！")
                continue
            break
        except ValueError:
            print("  请输入有效的数字！")

    # ---- 4. 是否预览 ----
    dry_input = input("\n是否先预览再删除？(y/N): ").strip().lower()
    dry_run = dry_input in ("y", "yes", "是")

    # ---- 5. 原文件处理策略 ----
    print("\n处理后的文件如何保存？")
    print("  1) 保留原文件，生成新文件（原文件作为备份）")
    print("  2) 直接覆盖原文件（不保留备份，节省空间）")
    while True:
        save_choice = input("  请选择 (1/2) [默认1]: ").strip()
        if save_choice == "":
            save_choice = "1"
        if save_choice in ("1", "2"):
            break
        print("  请输入 1 或 2！")

    overwrite = (save_choice == "2")

    if overwrite:
        print("\n  ⚠ 注意：选择覆盖模式，原文件将被替换，无法恢复！")
        confirm = input("  确认覆盖原文件？(y/N): ").strip().lower()
        if confirm not in ("y", "yes", "是"):
            print("  已取消，改为保留原文件模式。")
            overwrite = False

    # ---- 6. 执行 ----
    print("\n" + "=" * 55)
    print("  开始处理...")
    print("=" * 55)

    success = 0
    for i, ep in enumerate(epubs, 1):
        print(f"\n{'─' * 50}")
        print(f"  [{i}/{len(epubs)}] {os.path.basename(ep)}")
        print('─' * 50)
        ok = process(ep, count, dry_run=dry_run, overwrite=overwrite)
        if ok:
            success += 1

    print(f"\n{'=' * 55}")
    if overwrite:
        print(f"  完成！成功处理 {success}/{len(epubs)} 个文件（已覆盖原文件）")
    else:
        print(f"  完成！成功处理 {success}/{len(epubs)} 个文件（原文件已保留）")
    print(f"{'=' * 55}")
    input("\n按 Enter 键退出...")


if __name__ == "__main__":
    main()

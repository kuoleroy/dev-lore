#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量重命名脚本（合并两种规则）：
1. 文件名【开头有数字】：在数字与后续内容之间插入 "_"
   - 004中后台列表页.md  -> 004_中后台列表页.md
   - 029uni-app.md        -> 029_uni-app.md
   - 001_权限控制.md      -> (已规范，保持不变)
2. 文件名【开头没有数字】：自动递增补上编号前缀 "NNN_"
   - README.md   -> 001_README.md
   - utils.js    -> 002_utils.js

说明：
- 只处理当前目录文件，不递归子目录
- 幂等安全：已规范的不会重复处理，可反复运行
- 默认先【预览】模式；加 --apply 才真正执行
用法：
    python3 rename_files.py           # 预览
    python3 rename_files.py --apply   # 真正执行
"""

import os
import re
import argparse

# 是否只处理 .md 文件；设为 False 则处理目录下所有文件
ONLY_MD = False

# 递增编号起始值
START_INDEX = 1


def has_leading_number(name: str) -> bool:
    """判断文件名（不含扩展名）是否以数字开头"""
    base = os.path.splitext(name)[0]
    return bool(re.match(r'^\d+', base))


def add_underscore(name: str) -> str:
    """在数字与后续非数字内容之间插入一个下划线（仅一处，幂等）"""
    base, ext = os.path.splitext(name)
    # ^(\d+)        捕获开头的数字
    # (?<!_)        确保数字前面没有下划线（其实开头不可能有）
    # (?!_)         确保数字后面还没有下划线（已有则跳过，幂等）
    # ([^0-9])      紧接数字之后的第一个非数字字符
    new_base, n = re.subn(r'^(\d+)(?!_)([^0-9])', r'\1_\2', base, count=1)
    return new_base + ext


def auto_number(existing_indices, name: str, next_index: int):
    """为没有数字开头的文件中自动递增编号 NNN_"""
    base, ext = os.path.splitext(name)
    new_name = f"{next_index:03d}_{base}{ext}"
    return new_name, next_index + 1


def main():
    parser = argparse.ArgumentParser(description="批量重命名脚本")
    parser.add_argument('--apply', action='store_true', help='真正执行重命名（默认仅预览）')
    args = parser.parse_args()

    files = []
    for f in sorted(os.listdir('.')):
        if not os.path.isfile(f):
            continue
        if ONLY_MD and not f.endswith('.md'):
            continue
        # 忽略脚本自身
        if f == os.path.basename(__file__):
            continue
        files.append(f)

    # 第一轮：处理【有数字】的文件（加下划线），并收集已被占用的编号
    occupied_indices = set()
    plan = []          # (old, new)
    remaining = []     # 留给第二轮自动编号的文件

    for f in files:
        if has_leading_number(f):
            new_name = add_underscore(f)
            if new_name != f:
                plan.append((f, new_name))
            # 记录该编号已被占用（避免第二轮撞号）
            m = re.match(r'^(\d+)', os.path.splitext(new_name)[0])
            if m:
                occupied_indices.add(int(m.group(1)))
        else:
            remaining.append(f)

    # 第二轮：处理【无数字】的文件，自动递增（跳过已占用编号）
    next_index = START_INDEX
    for f in remaining:
        while next_index in occupied_indices:
            next_index += 1
        new_name, next_index = auto_number(None, f, next_index)
        plan.append((f, new_name))
        next_index += 1

    # 输出预览 / 执行
    if not plan:
        print("✅ 所有文件名均已规范，无需重命名。")
        return

    print("预览如下（" + ("将真正执行" if args.apply else "未真正执行，加 --apply 才生效") + "）：\n")
    for old, new in plan:
        flag = "有数字→加_" if has_leading_number(old) else "无数字→自动编号"
        print(f"  [{flag}] {old}  ->  {new}")

    if not args.apply:
        print("\n⚠️  当前为预览模式，未做任何修改。确认无误后运行：python3 rename_files.py --apply")
        return

    # 真正执行（先检查目标是否冲突）
    targets = [new for _, new in plan]
    if len(targets) != len(set(targets)):
        print("\n❌ 存在目标文件名冲突，已中止，请检查。")
        return

    for old, new in plan:
        if os.path.exists(new):
            print(f"  ⚠️ 跳过：{new} 已存在")
            continue
        os.rename(old, new)
        print(f"  ✅ {old} -> {new}")

    print("\n🎉 全部处理完成！")


if __name__ == '__main__':
    main()

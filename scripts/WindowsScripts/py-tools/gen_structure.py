# -*- coding: utf-8 -*-
"""
gen_structure.py
从 README.md 的 tree 格式解析并生成目录结构
纯标准库，无需 pip install 任何包
幂等：已存在的文件不覆盖

用法：
    cd 技术书
    python gen_structure.py              # 生成
    python gen_structure.py --dry-run    # 只预览
    python gen_structure.py --diagnose   # 打印解析结果自查
"""

import os
import re
import sys


def parse_tree(lines):
    """
    解析 tree 格式。用「前缀(│/空格) + 连接符位置」作为深度依据。
    返回嵌套字典：目录 = {}，文件 = None
    """
    root = {}
    stack = [(root, -1)]  # (节点, 深度)

    for raw in lines:
        line = raw.rstrip('\n')

        # 只处理 tree 行
        m = re.search(r'[├└]──\s*(.+)$', line)
        if not m:
            continue

        # 前缀 = 连接符之前的所有字符（│ 和 空格）
        prefix = line[:m.start()]
        # 深度 = 前缀里的「层级标记」数量
        # 每个缩进层级贡献 "│  "（│ + 两个空格），用 ├/└ 出现位置判断更稳
        depth = (len(prefix) - prefix.count(' ')) // 1 + prefix.count('│')
        # 上面太绕，直接用最可靠的方式：
        # 数「在连接符之前，出现了几组 "│  " 或 "   " 缩进单元」
        depth = 0
        idx = 0
        while idx < len(prefix):
            if prefix[idx] == '│':
                depth += 1
                idx += 1
            elif prefix[idx:idx+2] == '  ':
                # 末端对齐空格（└── 那一支没有 │），也算一级
                # 但要确保这是缩进位，简单处理：每 2 空格 = 1 级，扣除 │ 占的位
                pass
                idx += 2
                depth += 1
            else:
                idx += 1
        # 上面的逐字符走法遇到 "│   ├──" 会 double count。
        # —— 改用下面这条已被实测的可靠公式 ——
        # 深度 = (前缀长度 - 行首对齐空格) 的层数，每层 4 字符 "│  " 或 "   "
        depth = (len(prefix) + 1) // 4   # +1 避免 0 级偏差

        name_raw = m.group(1)
        # 去掉行内注释
        name_clean = re.sub(r'\s+#.*$', '', name_raw).strip()
        if not name_clean:
            continue
        is_dir = name_clean.endswith('/')
        name = name_clean.rstrip('/')

        # 回溯到父级
        while stack and depth <= stack[-1][1]:
            stack.pop()
        if not stack:
            # 深度异常，强行挂到 root（兜底，不该发生）
            stack.append((root, -1))

        current = stack[-1][0]
        if is_dir:
            current[name] = {}
            stack.append((current[name], depth))
        else:
            current[name] = None

    return root


def create(root_dir, structure, dry_run=False, stats=None):
    if stats is None:
        stats = {'dirs': 0, 'files': 0}

    for name, content in structure.items():
        path = os.path.join(root_dir, name)
        if content is None:  # 文件
            if not os.path.exists(path):
                stats['files'] += 1
                if not dry_run:
                    title = name.replace('.md', '').replace('_', ' ')
                    front = f"""---
title: {title}
status: todo
tags: []
---

# {title}

> 在这里写笔记...

"""
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(front)
        else:  # 目录
            if not os.path.exists(path):
                stats['dirs'] += 1
                if not dry_run:
                    os.makedirs(path, exist_ok=True)
            create(path, content, dry_run, stats)
    return stats


def diagnose(structure, indent=0):
    """打印解析结果，方便自查"""
    for k, v in structure.items():
        if v is None:
            print('  ' * indent + '📄 ' + k)
        else:
            print('  ' * indent + '📁 ' + k + '/')
            diagnose(v, indent + 1)


def main():
    root_dir = "."
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if args:
        root_dir = args[0]

    readme_path = os.path.join(root_dir, "README.md")
    if not os.path.exists(readme_path):
        print(f"❌ 找不到 {readme_path}")
        sys.exit(1)

    with open(readme_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    structure = parse_tree(lines)
    if not structure:
        print("❌ 没解析到任何结构，检查 README 格式")
        sys.exit(1)

    if '--diagnose' in sys.argv:
        print("📂 解析结果：")
        diagnose(structure)
        return

    dry_run = '--dry-run' in sys.argv
    stats = create(root_dir, structure, dry_run)

    if dry_run:
        print(f"🔍 Dry run：将创建 {stats['dirs']} 个目录，{stats['files']} 个文件")
    else:
        print(f"✅ 完成！新建 {stats['dirs']} 个目录，{stats['files']} 个文件")


if __name__ == '__main__':
    main()
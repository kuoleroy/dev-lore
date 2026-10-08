import os
import re
import sys

# ===== 获取路径 =====
if len(sys.argv) > 1:
    # 方式1：命令行参数传入，如 python jianyi.py "E:\Books"
    folder_path = sys.argv[1]
else:
    # 方式2：交互输入，直接回车则用当前目录
    folder_path = input("请输入文件夹路径（直接回车使用当前目录）: ").strip()
    if not folder_path:
        folder_path = os.getcwd()

# 去掉Windows路径两端可能带的引号
folder_path = folder_path.strip('"').strip("'")

# 检查路径是否存在
if not os.path.isdir(folder_path):
    print(f"错误：路径不存在或不是文件夹: {folder_path}")
    input("按回车键退出...")
    sys.exit(1)

print(f"\n目标文件夹: {folder_path}\n")

# ===== 匹配文件名格式：数字-书名.epub =====
pattern = re.compile(r'^(\d+)[-_－](.*)')

# 先收集，预览
rename_list = []

for filename in sorted(os.listdir(folder_path)):
    if filename.endswith('.epub'):
        match = pattern.match(filename)
        if match:
            num = int(match.group(1))
            rest = match.group(2)

            new_num = num - 1
            new_num_str = f"{new_num:02d}"
            new_filename = f"{new_num_str}-{rest}"

            rename_list.append((filename, new_filename))

if not rename_list:
    print("没有找到需要处理的文件（需以数字开头，如 '01-书名.epub'）")
    input("按回车键退出...")
    sys.exit(0)

# 预览
print("以下文件将被重命名：\n")
for old, new in rename_list:
    print(f"  {old}")
    print(f"  -> {new}")
    print()

print(f"共 {len(rename_list)} 个文件待处理。")

# ===== 确认 =====
confirm = input("确认执行重命名？(输入 y 确认，其他取消): ").strip().lower()

if confirm != 'y':
    print("已取消操作。")
    input("按回车键退出...")
    sys.exit(0)

# ===== 冲突检测 =====
existing_files = set(os.listdir(folder_path))
conflicts = []

for old, new in rename_list:
    if new in existing_files and new != old:
        conflicts.append((old, new))

if conflicts:
    print(f"\n⚠ 警告：以下操作会导致文件名冲突（目标已存在）：")
    for old, new in conflicts:
        print(f"  {old} -> {new}  (目标已存在!)")
    print("为避免数据丢失，操作已取消。请先手动处理冲突文件。")
    input("按回车键退出...")
    sys.exit(1)

# ===== 执行重命名 =====
success = 0
fail = 0

for old, new in rename_list:
    old_file = os.path.join(folder_path, old)
    new_file = os.path.join(folder_path, new)
    try:
        os.rename(old_file, new_file)
        print(f"✓ {old} -> {new}")
        success += 1
    except Exception as e:
        print(f"✗ {old} 失败: {e}")
        fail += 1

print(f"\n完成！成功 {success} 个，失败 {fail} 个。")
input("按回车键退出...")

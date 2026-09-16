import os
import sys
import glob

def clean_txt_file(filepath, keywords, remove_blank_lines=True):
    # 尝试常见编码
    content = None
    enc_used = None
    for enc in ['utf-8', 'gbk']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                lines = f.readlines()
            content = lines
            enc_used = enc
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        print(f"  ❌ {filepath} — 编码读取失败，跳过")
        return 0

    new_lines = []
    removed_count = 0

    for line in lines:
        # 1. 处理空行
        if remove_blank_lines and line.strip() == '':
            removed_count += 1
            continue

        # 2. 处理关键词
        if any(kw in line for kw in keywords):
            removed_count += 1
            continue

        new_lines.append(line)

    if removed_count == 0:
        print(f"  ⏭  {filepath} — 没有匹配行，跳过")
        return 0

    # 写入备份文件
    backup_path = filepath + '.bak'
    with open(backup_path, 'w', encoding=enc_used) as f:
        f.writelines(lines)

    # 写入清理后的内容
    with open(filepath, 'w', encoding=enc_used) as f:
        f.writelines(new_lines)

    print(f"  ✅ {filepath} — 删除了 {removed_count} 行（备份 → {backup_path}）")
    return removed_count

def main():
    # ========== 获取关键词 ==========
    if len(sys.argv) > 1:
        keywords = sys.argv[1:]
        print(f"🔑 关键词（来自命令行）: {keywords}")
    else:
        user_input = input("📝 请输入要删除的关键词（多个用空格或逗号分隔，直接回车则不删关键词）: ").strip()
        if user_input:
            if ',' in user_input:
                keywords = [k.strip() for k in user_input.split(',') if k.strip()]
            else:
                keywords = [k.strip() for k in user_input.split() if k.strip()]
        else:
            keywords = []
        if keywords:
            print(f"🔑 关键词（交互输入）: {keywords}")
        else:
            print("🔑 关键词（交互输入）: 无")

    # 询问是否删除空行
    blank_input = input("🗑️  是否删除空行？(Y/n，默认Y): ").strip().lower()
    remove_blank = False if blank_input == 'n' else True

    # ========== 获取要处理的文件 ==========
    filepath = None
    if '-f' in sys.argv:
        idx = sys.argv.index('-f')
        if idx + 1 < len(sys.argv):
            filepath = sys.argv[idx + 1]

    if filepath and os.path.isfile(filepath):
        print(f"\n📄 处理单个文件: {filepath}\n")
        clean_txt_file(filepath, keywords, remove_blank)
    else:
        txt_files = glob.glob('*.txt')
        if not txt_files:
            print("❌ 当前目录没有找到 .txt 文件")
            return

        print(f"\n📁 批量处理当前目录 {len(txt_files)} 个 .txt 文件:\n")
        total_removed = 0
        for txt in txt_files:
            total_removed += clean_txt_file(txt, keywords, remove_blank)

        print(f"\n🎉 完成！共删除 {total_removed} 行")

if __name__ == '__main__':
    main()

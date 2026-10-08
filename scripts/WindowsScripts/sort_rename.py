# -*- coding: utf-8 -*-
"""
交互式批量重命名脚本
功能：
  1. 将文件名中的中文数字（一二三...二十）转为补零的阿拉伯数字（第01集）
  2. 去除用户自行输入的"牛皮癣"广告词（支持多个，逐个输入）
用法：
  把本脚本放在视频所在文件夹，运行 python sort.py
  按控制台提示输入要去除的广告词即可（直接回车结束输入）
"""
import os
import re
import shutil # 新增：用于备份
from datetime import datetime # 新增：用于生成备份文件夹名称
# 中文数字 -> 阿拉伯数字（按长度从长到短，避免"十一"被拆成"十"+"一"）
NUM_MAP = {
    # ===== 3字符（二十一~九十九）=====
    '九十九': '99', '九十八': '98', '九十七': '97', '九十六': '96', '九十五': '95',
    '九十四': '94', '九十三': '93', '九十二': '92', '九十一': '91',
    '八十九': '89', '八十八': '88', '八十七': '87', '八十六': '86', '八十五': '85',
    '八十四': '84', '八十三': '83', '八十二': '82', '八十一': '81',
    '七十九': '79', '七十八': '78', '七十七': '77', '七十六': '76', '七十五': '75',
    '七十四': '74', '七十三': '73', '七十二': '72', '七十一': '71',
    '六十九': '69', '六十八': '68', '六十七': '67', '六十六': '66', '六十五': '65',
    '六十四': '64', '六十三': '63', '六十二': '62', '六十一': '61',
    '五十九': '59', '五十八': '58', '五十七': '57', '五十六': '56', '五十五': '55',
    '五十四': '54', '五十三': '53', '五十二': '52', '五十一': '51',
    '四十九': '49', '四十八': '48', '四十七': '47', '四十六': '46', '四十五': '45',
    '四十四': '44', '四十三': '43', '四十二': '42', '四十一': '41',
    '三十九': '39', '三十八': '38', '三十七': '37', '三十六': '36', '三十五': '35',
    '三十四': '34', '三十三': '33', '三十二': '32', '三十一': '31',
    '二十九': '29', '二十八': '28', '二十七': '27', '二十六': '26', '二十五': '25',
    '二十四': '24', '二十三': '23', '二十二': '22', '二十一': '21',
    # ===== 2字符 =====
    '一百': '100',
    '二十': '20', '三十': '30', '四十': '40', '五十': '50', '六十': '60', '七十': '70', '八十': '80', '九十': '90',
    '十一': '11', '十二': '12', '十三': '13', '十四': '14', '十五': '15',
    '十六': '16', '十七': '17', '十八': '18', '十九': '19',
    # ===== 1字符 =====
    '十': '10', '九': '9', '八': '8', '七': '7', '六': '6', '五': '5', '四': '4', '三': '3', '二': '2', '一': '1'
}

# 需要处理的文件扩展名
TARGET_EXTS = (
    # 视频
    '.mp4', '.mkv', '.avi', '.mov', '.flv', '.ts', '.wmv', '.rmvb',
    '.mpeg', '.mpg', '.3gp', '.webm', '.m4v', '.vob', '.ogv', '.asf',
    # 音频
    '.mp3', '.flac', '.wav', '.aac', '.ogg', '.wma', '.m4a', '.ape',
    '.opus', '.mid', '.midi', '.aiff',
    # 图片
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif',
    '.svg', '.ico', '.heic', '.heif', '.raw', '.psd', '.ai',
    # 文档
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.odt', '.ods', '.odp', '.rtf', '.epub', '.mobi', '.azw', '.azw3',
    # 文本 & Markdown
    '.txt', '.md', '.markdown', '.rst', '.tex',
    # 代码 & 数据
    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.htm', '.css', '.scss', '.less',
    '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.sh', '.bat', '.cmd', '.ps1',
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.cs', '.java', '.go', '.rs',
    '.rb', '.php', '.sql', '.r', '.m', '.swift', '.kt', '.dart',
    # 压缩包
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.lz', '.lzma',
    '.iso', '.dmg', '.pkg',
    # 字幕
    '.srt', '.ass', '.ssa', '.sub', '.vtt',
    # 其他常见
    '.exe', '.msi', '.apk', '.ipa', '.deb', '.rpm',
)


def convert_number(filename: str) -> str:
    """把"第X集"中的中文数字转成补零的阿拉伯数字"""
    match = re.search(r'第(.+?)集', filename)
    if not match:
        return filename
    cn_num = match.group(1)
    if cn_num not in NUM_MAP:
        return filename
    ar_num = NUM_MAP[cn_num]
    # 统一用 zfill 补零到 3 位
    ar_num = ar_num.zfill(3)
    return filename.replace(f'第{cn_num}集', f'第{ar_num}集')


def input_words(prompt: str) -> list:
    """让用户在控制台自行输入要去除的词，直接回车结束"""
    words = []
    print(prompt)
    print('  （每输入一个后按回车，直接按回车结束输入）')
    while True:
        try:
            w = input('  > ').strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not w:
            break
        words.append(w)
    return words


def clean_filename(name: str) -> str:
    """清理文件名中多余的空格、下划线"""
    # 多个空格变一个
    name = re.sub(r'\s{2,}', ' ', name)
    # 多个下划线变一个
    name = re.sub(r'_{2,}', '_', name)
    # 去除首尾空格和下划线
    name = name.strip(' _')
    return name


def main():
    path = os.getcwd()
    print(f'当前工作目录：{path}\n')

    # ================= 新增：批量清理文件夹名称 =================
    print('--- 第一步：批量整理文件夹名称 ---')
    # 获取当前目录下所有的文件夹
    all_dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

    # 让用户输入要匹配的文件夹关键词
    folder_keyword = input('请输入要匹配的文件夹关键词（如：分集 或 合集，直接回车跳过）: ').strip()

    folder_plan = []
    if folder_keyword:
        # 匹配包含关键词的文件夹
        target_dirs = [d for d in all_dirs if folder_keyword in d]

        print('\n即将清理以下文件夹名称（去掉 _YYYY-MM-DD_ 日期格式）：')
        for d in target_dirs:
            # 使用正则表达式去掉 _2026-07-30_ 这种格式的日期
            new_d = re.sub(r'_{1}\d{4}-\d{2}-\d{2}_{1}', '_', d)
            # 清理可能产生的多余下划线
            new_d = re.sub(r'_{2,}', '_', new_d).strip('_')

            if new_d != d:
                folder_plan.append((d, new_d))
                print(f'  {d}\n    -> {new_d}')

    if folder_plan:
        confirm_dir = input('\n确认执行文件夹重命名吗？(y/n) > ').strip().lower()
        if confirm_dir == 'y':
            # 1. 创建备份
            backup_name = f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            os.makedirs(backup_name)
            print(f'  ✔ 备份文件夹已生成：{backup_name}')

            # 2. 执行重命名
            for old, new in folder_plan:
                old_path = os.path.join(path, old)
                new_path = os.path.join(path, new)

                # 如果目标文件夹已存在，先备份
                if os.path.exists(new_path):
                    backup_dup = os.path.join(backup_name, new + '_冲突备份')
                    shutil.move(new_path, backup_dup)
                    print(f'  ⚠ 目标 {new} 已存在，已移至备份')

                os.rename(old_path, new_path)
                print(f'  ✔ 已重命名：{old} -> {new}')
        else:
            print('  已取消文件夹重命名。')
    # ================= 文件夹清理步骤结束 =================

    print('\n--- 第二步：批量清理文件名 ---')

    # 原有的文件处理逻辑（保持不变）
    files = [f for f in os.listdir(path)
             if os.path.isfile(os.path.join(path, f)) and f.lower().endswith(TARGET_EXTS)]
    if not files:
        print('未找到需要处理的文件，脚本退出。')
        return

    print(f'共发现 {len(files)} 个目标文件。')

    # 让用户在控制台输入要去除的广告词
    words = input_words('请输入要批量去除的"牛皮癣"广告词：')

    # 预览将要发生的改名
    print('\n即将执行以下文件重命名（预览）：')
    file_plan = []
    for f in files:
        new = convert_number(f)          # 先转数字
        for w in words:                  # 再逐个去除广告词
            if w and w in new:
                new = new.replace(w, '')
        # 清理多余空格/下划线
        new = re.sub(r'\s{2,}', ' ', new).strip()
        new = re.sub(r'_{2,}', '_', new).strip('_')
        if new != f:
            file_plan.append((f, new))
            print(f'  {f}\n    -> {new}')
        else:
            print(f'  （不变）{f}')

    if not file_plan:
        print('\n没有需要改名的文件，退出。')
        return

    # 二次确认后执行
    confirm_file = input('\n确认执行以上文件重命名吗？(y/n) > ').strip().lower()
    if confirm_file != 'y':
        print('已取消，未做任何修改。')
        return

    for old, new in file_plan:
        os.rename(os.path.join(path, old), os.path.join(path, new))
    print(f'\n🎉 完成！共重命名 {len(file_plan)} 个文件。')


if __name__ == '__main__':
    main()

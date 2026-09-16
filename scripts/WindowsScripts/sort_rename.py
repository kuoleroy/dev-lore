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

# 中文数字 -> 阿拉伯数字（按长度从长到短，避免"十一"被拆成"十"+"一"）
NUM_MAP = {
    '五十': '50', '四十九': '49', '四十八': '48', '四十七': '47', '四十六': '46',
    '四十五': '45', '四十四': '44', '四十三': '43', '四十二': '42', '四十一': '41',
    '四十': '40', '三十九': '39', '三十八': '38', '三十七': '37', '三十六': '36',
    '三十五': '35', '三十四': '34', '三十三': '33', '三十二': '32', '三十一': '31',
    '三十': '30', '二十九': '29', '二十八': '28', '二十七': '27', '二十六': '26',
    '二十五': '25', '二十四': '24', '二十三': '23', '二十二': '22', '二十一': '21',
    '二十': '20', '十九': '19', '十八': '18', '十七': '17', '十六': '16',
    '十五': '15', '十四': '14', '十三': '13', '十二': '12', '十一': '11',
    '十': '10', '九': '9', '八': '8', '七': '7', '六': '6', '五': '5',
    '四': '4', '三': '3', '二': '2', '一': '1'
}

# 需要处理的文件扩展名
TARGET_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.ts')


def convert_number(filename: str) -> str:
    """把"第X集"中的中文数字转成补零的阿拉伯数字"""
    match = re.search(r'第(.+?)集', filename)
    if not match:
        return filename
    cn_num = match.group(1)
    if cn_num not in NUM_MAP:
        return filename
    ar_num = NUM_MAP[cn_num]
    if len(ar_num) == 1:  # 补零：1 -> 01
        ar_num = '0' + ar_num
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


def main():
    path = os.getcwd()
    print(f'当前工作目录：{path}\n')

    # 1. 先收集需要处理的视频文件，展示给用户确认
    files = [f for f in os.listdir(path)
             if os.path.isfile(os.path.join(path, f)) and f.lower().endswith(TARGET_EXTS)]
    if not files:
        print('未找到视频文件，脚本退出。')
        return

    print(f'共发现 {len(files)} 个视频文件：')
    for f in files:
        print(f'  - {f}')
    print()

    # 2. 让用户在控制台输入要去除的广告词
    words = input_words('请输入要批量去除的"牛皮癣"广告词：')

    # 3. 预览将要发生的改名
    print('\n即将执行以下重命名（预览）：')
    plan = []
    for f in files:
        new = convert_number(f)          # 先转数字
        for w in words:                  # 再逐个去除广告词
            if w and w in new:
                new = new.replace(w, '')
        # 清理多余空格/下划线
        new = re.sub(r'\s{2,}', ' ', new).strip()
        new = re.sub(r'_{2,}', '_', new).strip('_')
        if new != f:
            plan.append((f, new))
            print(f'  {f}\n    -> {new}')
        else:
            print(f'  （不变）{f}')

    if not plan:
        print('\n没有需要改名的文件，退出。')
        return

    # 4. 二次确认后执行
    confirm = input('\n确认执行以上重命名吗？(y/n) > ').strip().lower()
    if confirm != 'y':
        print('已取消，未做任何修改。')
        return

    for old, new in plan:
        os.rename(os.path.join(path, old), os.path.join(path, new))
    print(f'\n🎉 完成！共重命名 {len(plan)} 个文件。')


if __name__ == '__main__':
    main()

import os

def batch_remove_text():
    # 1. 用户在控制台输入文件所在路径
    folder_path = input("请输入文件所在的文件夹路径: ").strip()

    # 检查路径是否存在
    if not os.path.isdir(folder_path):
        print("错误：输入的路径不存在或不是一个文件夹，请检查后重试。")
        return

    # 2. 用户输入需要删除的“牛皮癣”文字
    unwanted_text = input("请输入需要删除的牛皮癣文字(直接回车退出): ").strip()

    if not unwanted_text:
        print("未输入需要删除的文字，程序已退出。")
        return

    # 记录修改的文件数量
    modified_count = 0

    # 3. 遍历文件夹中的所有文件
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            # 分离文件名和扩展名（防止误删扩展名）
            file_base, file_ext = os.path.splitext(filename)

            # 如果基础文件名中包含牛皮癣文字，则进行替换
            if unwanted_text in file_base:
                # 替换掉牛皮癣文字（替换为空字符串）
                new_file_base = file_base.replace(unwanted_text, "")
                new_filename = new_file_base + file_ext

                # 拼接完整的旧路径和新路径
                old_file_path = os.path.join(root, filename)
                new_file_path = os.path.join(root, new_filename)

                # 重命名文件
                try:
                    os.rename(old_file_path, new_file_path)
                    modified_count += 1
                    print(f"已重命名: {filename}  ->  {new_filename}")
                except Exception as e:
                    print(f"重命名失败: {filename}，错误信息: {e}")

    # 修复点：将 \n 写在字符串里，不再直接换行
    print(f"\n处理完成！共修改了 {modified_count} 个文件。")

if __name__ == "__main__":
    batch_remove_text()

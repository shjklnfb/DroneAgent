import os

def count_code_lines(directory):
    """
    递归统计指定目录下所有 Python 文件的代码行数。
    忽略空行和注释行。
    """
    total_lines = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') or file.endswith('.yaml'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        stripped_line = line.strip()
                        if stripped_line and not stripped_line.startswith('#'):
                            total_lines += 1
    return total_lines

# 示例：统计当前目录及其子目录中的 Python 代码行数
directory = "."  # 当前目录
total_lines = count_code_lines(directory)
print(f"Total lines of Python code: {total_lines}")
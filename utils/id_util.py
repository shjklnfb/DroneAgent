import uuid
import time

def generate_random_id():
    """
    生成一个随机的唯一标识符，以task_随机数的形式。

    返回:
        str: 一个随机生成的ID字符串。
    """
    random_part = uuid.uuid4().hex[:8]
    return f"task_{random_part}"

# 示例用法
if __name__ == "__main__":
    print("生成的ID:", generate_random_id())
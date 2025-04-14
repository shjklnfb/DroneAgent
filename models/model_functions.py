import base64
import io
from PIL import Image
from models.yolo.yolov8 import detect_with_yolov8  # 导入 yolov8 检测方法
from models.llm.qwen import *  # 导入 qwen 模型方法
'''
这个文件是模型接口文件
云端调用模型写在mdoels文件夹下的各个模型文件中
这个文件是对外接口，用于调用各个模型文件中的方法，实现对外接口的功能
对于同一个模型，可以在这个文件中写多个接口，实现不同的功能
'''

# 检测目标是否存在
def detect_target(picture: str, target: str) -> list:
    """
    检测图片中是否包含指定目标。

    :param picture: 图片路径
    :param target: 目标名称
    :return: 目标标注框的坐标
    """
    try:
        response = detect_with_yolov8(picture)
        if response.status_code == 200:
            data = response.json()
            annotations = data.get('annotations', [])
            res = []
            for annotation in annotations:
                if annotation.get('class') == target:
                    res.append(annotation.get('bbox'))
                    # return res
                    return annotation.get('bbox')
        return None
    except Exception as e:
        print(f"Error during detection: {e}")
        return None


def task_decomposition(task_description):
    """
    任务分解方法，调用call_deepseek_r1进行任务分解

    :param task_description: 任务描述
    :return: 分解后的任务列表
    """
    try:
        # 调用call_deepseek_r1函数进行任务分解
        decomposed_tasks = call_deepseek_r1(task_description)
        #TODO: 格式化输出
        return decomposed_tasks
    except Exception as e:
        print(f"Error during task decomposition: {e}")
        return []

def generate_launch_file(drones,world_file):
    """
    生成launch文件
    :param drones: 无人机列表
    :param world_file: 世界文件路径
    :return: 生成的launch文件内容
    """
    # TODO: 调用大模型生成launch文件内容
    # TODO: 格式化输出
    return "launch file content"

def subtask_to_python(subtasks):
    """
    将任务描述转换为Python代码
    """
    # TODO: 调用大模型生成Python代码
    pass

def perception_func(task, logs, monitor_data):
    """
    感知器调用，根据日志和监控数据检查任务执行情况
    :param logs: 日志数据
    :param monitor_data: 监控数据
    :return: 感知结果
    """
    try:
        # 调用call_with_messages方法，根据日志和监控数据检查任务执行情况
        messages = f"当前正在执行的子任务: {task}"+f"子任务的执行日志: {logs}"+f"当前时刻的无人机监控器数据: {monitor_data}"
        messages += "请分析当前子任务的执行情况，分析子任务是否完成，是否存在错误。注意只有当任务的最终目标得到满足时，才认为任务完成。"
        messages += "每个步骤执行都可以重复一定的次数，因此暂时的错误不算错误，只有出现“xxx失败超过n次,任务终止”时，才认为这个步骤失败，导致任务失败。运行中表示任务的步骤错误还没有超过最大次数，最后一个步骤也没有执行完成。"
        messages += "任意一个步骤出错超过限度时，任务就会失败。失败时给出失败的原因和在哪个步骤失败的。"
        messages += "要求的输出的内容格式为：{\"task\":\"task.name\",\"state\":\"finish/error/running\",\"reason\":\"reason\"}。字数在200字以内，不要换行。注意这个task.name是subtask1,subtask2等子任务的名称,而不是步骤的名称或描述。"
        
        result = call_with_messages(messages)
        return result
    except Exception as e:
        print(f"Error during perception: {e}")
        return None
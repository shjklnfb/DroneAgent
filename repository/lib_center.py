import json
from models.llm.qwen import call_with_messages,generate_response_with_images  # 引入qwen模块
from utils.log_configurator import setup_script_logger


# 调度器的自定义库函数
def get_drone_status(dronemonitor):
    """获取无人机的状态"""
    return dronemonitor.data.get('state', 'unknown')

def get_drone_position(dronemonitor):
    """获取无人机的位置"""
    position = dronemonitor.data.get('position')
    if position:
        return {'x': position.x, 'y': position.y, 'z': position.z}
    return 'unknown'

def get_drone_height(dronemonitor):
    """获取无人机的高度"""
    position = dronemonitor.data.get('position')
    if position:
        return position.z
    return 'unknown'

def get_drone_speed(dronemonitor):
    """获取无人机的速度"""
    velocity = dronemonitor.data.get('velocity')
    if velocity:
        return {'x': velocity.x, 'y': velocity.y, 'z': velocity.z}
    return 'unknown'

def get_drone_sensor_data(dronemonitor, sensor):
    """获取无人机指定传感器的数据"""
    return dronemonitor.data.get(sensor, 'unknown')

def process_data(data, model):
    """使用指定模型处理数据"""
    return "success"


def check(drone, info, target):
    """检查无人机是否满足特定条件"""
    prompt = f"无人机状态: {info}, 目标: {target}。请判断无人机是否满足条件，并给出理由。你的推理过程和其他内容都写到json的reason中，即使你无法进行判断，也请按照以下 JSON 格式输出：{{\"result\": true/false, \"reason\": \"原因\"}}"
    response = call_with_messages(prompt)
    # print(response)
    if response and response.status_code == 200:
            # 获取 content 部分
        content = response["output"]["choices"][0]["message"]["content"]
        # 提取 JSON 格式部分（假设 JSON 部分被 ```json 和 ``` 包裹）
        json_start = content.find("```json") + len("```json")
        json_end = content.find("```", json_start)
        json_string = content[json_start:json_end].strip()

        # 解析 JSON 字符串
        result_dict = json.loads(json_string)
        return result_dict["result"],result_dict["reason"]
    return False, "请求失败或无响应"

import json

def check_with_picture(drone, info, target, picture=None):
    """检查无人机是否满足特定条件"""
    prompt = f"无人机信息: {info}, 目标: {target}。请判断无人机是否满足条件，并给出理由。当你70%确定时，result为true，你的推理过程和其他内容都写到json的reason中,即使你无法评估，也请按照以下 JSON 格式输出：{{\"result\": true/false, \"reason\": \"原因\"}}"
    response = generate_response_with_images(prompt, picture)
    if response :
            try:
                # 确保 response 是一个字典
                response = json.loads(response)
                # 提取 message.content 字段
                content = response["choices"][0]["message"]["content"]

                # 提取 JSON 格式部分（假设 JSON 部分被 ```json 和 ``` 包裹）
                json_start = content.find("```json") + len("```json")
                json_end = content.find("```", json_start)
                json_string = content[json_start:json_end].strip()

                # 解析 JSON 字符串
                result_dict = json.loads(json_string)
                return result_dict["result"],result_dict["reason"]
            except Exception as e:
                print("JSON解析出错:", e)
                print("Response内容:", response)
                return False, "JSON解析失败"
    else:
        print("未能成功获取响应")
        return False, "请求失败或无响应"


def log_info(id, information, func_name):
    """记录信息日志"""
    logger = setup_script_logger(id, func_name)
    logger.info(information)
    

# def send_to_drone(connector, sender, receiver, type, message):
#     """发送消息到无人机"""
#     # 这里可以实现具体的发送逻辑
#     connector.send_message(sender,receiver,type,message)
#     print(f"Sending info to drone: {message}")
#     return True
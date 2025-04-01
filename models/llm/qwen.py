import dashscope
import json
import yaml
import os
import base64
from openai import OpenAI

# qwen-plus大模型
def call_with_messages(prompt):
    messages = [{"role":"system","content":"你是一个关于无人机执行任务的专家，了解ROS+PX4+Gazebo无人机仿真，了解无人机mavros的各种话题和服务，懂得无人机基本的控制原理和基本控制指令，知道无人机各种任务的情景。"},
                {"role":"user","content":""}]
    messages[1]["content"] = prompt
    responses = dashscope.Generation.call(
        model="qwen-plus",
        api_key="sk-d34cba22d2a04a5c8c191f082106d07e",
        messages=messages,
        stream=False,
        result_format='message',  # 将返回结果格式设置为 message
        top_p=0.8,
        temperature=0.7,
        enable_search=False
    )
    if(responses.status_code == 200):
        return responses
    else:
        print(responses)

# qwen-vl-plus多模态大模型
def generate_response_with_images(prompt, image_paths):
    """
    调用大模型，根据提示词和本地图片生成响应。
    
    :param prompt: str，提示词
    :param image_paths: list，本地图片路径列表
    :return: str，大模型的响应结果
    """
    client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key="sk-d34cba22d2a04a5c8c191f082106d07e",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
    messages = [{"role": "system", "content": "你是一个关于无人机执行任务的专家，了解ROS+PX4无人机仿真，了解无人机的各种话题和服务，懂得无人机基本的控制原理和基本控制指令。"
    "图片是无人机携带摄像头航拍的结果"},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}]
    
    for image_path in image_paths:
        image_path = os.path.expanduser(image_path)
        # 读取本地图片并编码为 Base64
        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })
    
    completion = client.chat.completions.create(
        model="qwen-vl-plus",  # 模型名称，可按需更换
        messages=messages
    )
    return completion.model_dump_json()



# deekseep-r1大模型
def call_deepseek_r1(prompt):
    client = OpenAI(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key="sk-d34cba22d2a04a5c8c191f082106d07e",  # 如何获取API Key：https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    completion = client.chat.completions.create(
        model="deepseek-r1",  # 此处以 deepseek-r1 为例，可按需更换模型名称。
        messages=[
            {'role': 'system', 'content': '你是无人机规划问题的专家，你擅长分析无人机执行任务的问题'},
            {'role': 'user', 'content': prompt}
        ]
    )

    # 通过reasoning_content字段获取思考过程
    reasoning_process = completion.choices[0].message.reasoning_content
    # 通过content字段获取最终答案
    final_answer = completion.choices[0].message.content

    return reasoning_process, final_answer

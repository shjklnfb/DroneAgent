import requests
from PIL import Image
import io
import json
import base64

def detect_with_yolov8(image_path: str) -> bytes:
    """
    调用云服务器中的yolov8模型，发送图片并返回带标注框的图片和标注信息。

    :param image_path: 本地图片路径
    :return: 带标注框的图片的二进制数据和标注信息
    """
    url = "http://47.113.185.245:8000/detect"
    with open(image_path, 'rb') as file:
        files = {'file': file}
        response = requests.post(url, files=files)
        response.raise_for_status()  # 如果请求失败则抛出异常
        return response


# response=detect_with_yolov8("/home/ubuntu/Desktop/1.jpg")
# if response.status_code == 200:
#     data = response.json()
#     # 处理标注信息
#     print('标注信息:', data['annotations'])

#     # 保存标注后的图片
#     img_data = base64.b64decode(data['image'])
#     img = Image.open(io.BytesIO(img_data))
#     img.save('annotated_image.jpg')
#     print('标注后的图片已保存为 annotated_image.jpg')
# image = Image.open(io.BytesIO(res))
# image.show()


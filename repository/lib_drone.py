import asyncio
from models.model_functions import func_detect_target
from repository.lib_center import get_drone_sensor_data
from repository.instructions.command_takeoff import command_takeoff
import threading
from repository.instructions.command_land import send_land_command
from repository.instructions.command_hover import send_hover_command
from repository.instructions.command_search import publish_random_flight_command
from repository.instructions.command_twist import send_rotate_command
from repository.instructions.command_pos import publish_command
import cv2
from datetime import datetime
from drone.drone_monitor import DroneMonitor   
from repository.instructions.command_vel import send_velocity_command
import math
from repository.instructions.command_spiral import send_spiral_command
import time

# 无人机的自定义库函数
def takeoff(drone):
    """让 {drone} 起飞"""
    takeoff_thread = threading.Thread(target=command_takeoff, args=(drone,))
    takeoff_thread.start()

def land(drone):
    """让 {drone} 降落到原地"""
    send_land_command(drone)
    return True

def hover(drone, duration):
    """让 {drone} 在当前位置悬停时间 {duration}"""
    send_hover_command(drone, duration)
    return True

def move_forward(drone, dronemonitor, velocity, duration):
    """让 {drone} 以速度 {velocity} 向前飞行时间 {duration}"""
    if isinstance(dronemonitor, DroneMonitor):
        imu_data = dronemonitor.data.get('imu_data')
        if imu_data:
            orientation = imu_data['orientation']
            yaw = math.atan2(2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
                             1.0 - 2.0 * (orientation.y**2 + orientation.z**2))
            vel_x = velocity * math.cos(yaw)
            vel_y = velocity * math.sin(yaw)
            send_velocity_command(drone, vel_x, vel_y, 0, duration)
            return True
    return False

def move_backward(drone, dronemonitor, velocity, duration):
    """让 {drone} 以速度 {velocity} 向后飞行时间 {duration}"""
    if isinstance(dronemonitor, DroneMonitor):
        imu_data = dronemonitor.data.get('imu_data')
        if imu_data:
            orientation = imu_data['orientation']
            yaw = math.atan2(2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
                             1.0 - 2.0 * (orientation.y**2 + orientation.z**2))
            vel_x = -velocity * math.cos(yaw)
            vel_y = -velocity * math.sin(yaw)
            send_velocity_command(drone.drone_id, vel_x, vel_y, 0, duration)
            return True
    return False

def move_left(drone,dronemonitor ,velocity, duration):
    """让 {drone} 以速度 {velocity} 向左飞行时间 {duration}"""
    if isinstance(dronemonitor, DroneMonitor):
        imu_data = dronemonitor.data.get('imu_data')
        if imu_data:
            orientation = imu_data['orientation']
            yaw = math.atan2(2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
                             1.0 - 2.0 * (orientation.y**2 + orientation.z**2))
            vel_x = -velocity * math.sin(yaw)
            vel_y = velocity * math.cos(yaw)
            send_velocity_command(drone.drone_id, vel_x, vel_y, 0, duration)
            return True
    return False

def move_right(drone, dronemonitor, velocity, duration):
    """让 {drone} 以速度 {velocity} 向右飞行时间 {duration}"""
    if isinstance(dronemonitor, DroneMonitor):
        imu_data = dronemonitor.data.get('imu_data')
        if imu_data:
            orientation = imu_data['orientation']
            yaw = math.atan2(2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
                             1.0 - 2.0 * (orientation.y**2 + orientation.z**2))
            vel_x = velocity * math.sin(yaw)
            vel_y = -velocity * math.cos(yaw)
            send_velocity_command(drone.drone_id, vel_x, vel_y, 0, duration)
            return True
    return False

def move_ascend(drone, velocity, duration):
    """让 {drone} 以速度 {velocity} 向上飞行时间 {duration}"""
    send_velocity_command(drone, 0, 0, velocity, duration)
    return True

def move_decend(drone, velocity, duration):
    """让 {drone} 以速度 {velocity} 向下飞行时间 {duration}"""
    send_velocity_command(drone, 0, 0, -velocity, duration)
    return True

def search(drone, dronemonitor, target, radius, duration):
    """让 {drone} 以半径 {radius} 搜索持续时间 {duration}"""
    publish_random_flight_command(drone, radius, duration)

    '''
    已经发布了无人机搜寻的控制命令，在这段时间内，同时进行目标检测
    根据drone获取dronemonitor监控器对象，然后获取其中的图像数据
    把图像保存，然后调用yolo
    格式化输出结果
    这个过程每5秒检测一次
    '''
    start_time = time.time()
    while time.time() - start_time < duration:
        # 开始目标检测
        image = get_drone_sensor_data(dronemonitor, 'depth_image')
        photo_file = take_photo(dronemonitor)
        
        if func_detect_target(photo_file, target):
            # 计算坐标
            depth_file = save_depth_image(dronemonitor)
            # cal_pos()
            res = {"x": 0, "y": 0, "z": 0}
            return True,res
        time.sleep(3)  # 每3秒检测一次
    return False,None


def spiral(drone, dronemonitor, target, radius, velocity, duration):
    """让 {drone} 以半径 {radius} 和速度 {velocity} 螺旋飞行持续时间 {duration}"""
    send_spiral_command(drone, radius, velocity, duration)
    
    '''
    已经发布了无人机搜寻的控制命令，在这段时间内，同时进行目标检测
    根据drone获取dronemonitor监控器对象，然后获取其中的图像数据
    把图像保存，然后调用yolo
    格式化输出结果
    这个过程每5秒检测一次
    '''
    start_time = time.time()
    while time.time() - start_time < duration:
        # 开始目标检测
        image = get_drone_sensor_data(dronemonitor, 'depth_image')
        depth_file,photo_file = save_depth_image(dronemonitor)
        bbox = func_detect_target(photo_file, target)
        print(bbox)
        if bbox is not None:
            # 计算坐标
            camera_info = dronemonitor.data.get('camera_info')
            position = dronemonitor.data.get('position')
            imu_data = dronemonitor.data.get('imu_data')
            print(camera_info,position,imu_data)
            if camera_info and position and imu_data:
                # Load depth image
                depth_image = cv2.imread(depth_file, cv2.IMREAD_UNCHANGED)
                if depth_image is not None:
                    # Extract bounding box center
                    x_center = int((bbox[0] + bbox[2]) / 2)
                    y_center = int((bbox[1] + bbox[3]) / 2)
                    
                    # Get depth value at the center of the bounding box
                    depth = depth_image[y_center, x_center]
                    
                    # Camera intrinsic parameters
                    fx = camera_info.K[0]
                    fy = camera_info.K[4]
                    cx = camera_info.K[2]
                    cy = camera_info.K[5]
                    
                    # Convert pixel coordinates to camera coordinates
                    x_camera = (x_center - cx) * depth / fx
                    y_camera = (y_center - cy) * depth / fy
                    z_camera = depth
                    
                    # Convert camera coordinates to world coordinates
                    orientation = imu_data['orientation']
                    yaw = math.atan2(2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
                                     1.0 - 2.0 * (orientation.y**2 + orientation.z**2))
                    world_x = position.x + x_camera * math.cos(yaw) - y_camera * math.sin(yaw)
                    world_y = position.y + x_camera * math.sin(yaw) + y_camera * math.cos(yaw)
                    world_z = position.z + z_camera
                    
                    res = {"x": world_x, "y": world_y, "z": world_z}
            return True,res
        time.sleep(3)  # 每3秒检测一次
    return False,None

def yaw(drone, velocity, duration):
    """让 {drone} 以线速度 {velocity} 绕 z 轴旋转持续时间 {duration}"""
    send_rotate_command(drone, velocity, duration)
    return True

def fly_to(drone, x, y, z):
    """让 {drone} 飞行到坐标点 ({x}, {y}, {z})"""
    publish_command(drone, x, y, z)
    return True

def take_photo(dronemonitor):
    """让 {drone} 拍摄照片并存储到 images 文件夹下"""
    if isinstance(dronemonitor, DroneMonitor):
        image = dronemonitor.data.get('image')
        if image is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"images/photo_{timestamp}.jpg"
            cv2.imwrite(filename, image)
            return f"{filename}"
        else:
            return "没有图像数据"
    else:
        return "监控器对象无效"

import os
import cv2
from datetime import datetime
import numpy as np

def save_depth_image(dronemonitor):
    """保存 {drone} 的深度图像和图像到对应文件夹下，文件名相同"""
    if isinstance(dronemonitor, DroneMonitor):
        depth_image = dronemonitor.data.get('depth_image')
        image = dronemonitor.data.get('image')
        if depth_image is not None and depth_image.size > 0 and image is not None:
            # 创建时间戳文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            depth_filename = f"depth_images/depth_{timestamp}.png"
            image_filename = f"images/photo_{timestamp}.jpg"
            
            # 保存深度图像
            depth_success = cv2.imwrite(depth_filename, depth_image)
            # 保存普通图像
            image_success = cv2.imwrite(image_filename, image)
            
            if depth_success and image_success:
                return depth_filename, image_filename
            else:
                return "保存深度图像或普通图像失败",None
        else:
            return "没有深度图像数据或普通图像数据无效",None
    else:
        return "监控器对象无效",None

def follow(drone, target):
    """让 {drone} 跟踪目标 {target}"""
    return True

# 辅助函数：在同步函数中发送P2P消息
def send_p2p_message(p2p_node, target_id: str, message: dict) -> bool:
    """
    在同步函数中使用p2p_node发送消息
    
    Args:
        p2p_node: P2P节点对象
        target_id: 目标节点ID
        message: 要发送的消息内容
        
    Returns:
        bool: 发送是否成功
    """
    # 获取事件循环 - 按优先级尝试不同方式获取
    loop = None
    
    # 1. 首先尝试从p2p_node对象获取event_loop属性
    if hasattr(p2p_node, 'event_loop') and p2p_node.event_loop:
        loop = p2p_node.event_loop
        print("使用p2p_node.event_loop")
    
    # 2. 其次尝试获取p2p_node对象的p2p_event_loop属性
    elif hasattr(p2p_node, 'p2p_event_loop') and p2p_node.p2p_event_loop:
        loop = p2p_node.p2p_event_loop
        print("使用p2p_node.p2p_event_loop")
        
    # 3. 再尝试获取当前线程的事件循环
    if loop is None:
        try:
            loop = asyncio.get_event_loop()
            print("使用当前线程事件循环")
        except RuntimeError:
            # 4. 如果以上都失败，尝试创建新的事件循环
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                print("创建并使用新事件循环")
            except Exception as e:
                print(f"无法创建新事件循环: {str(e)}")
                print("无法获取事件循环，消息发送失败")
                return False
    
    try:
        # 在事件循环中执行异步发送操作
        future = asyncio.run_coroutine_threadsafe(
            p2p_node.send_message(target_id, message),
            loop
        )
        # 等待操作完成，最多等待5秒
        success = future.result(timeout=5.0)
        return success
    except Exception as e:
        print(f"发送消息时出错: {str(e)}")
        return False

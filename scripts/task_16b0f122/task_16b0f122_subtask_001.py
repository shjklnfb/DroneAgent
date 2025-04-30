from repository.lib_drone import *
from repository.lib_center import *
import inspect
import json

# 子任务1：无人机1起飞到有利侦查位置，寻找到目标
def subtask1(id, drone, dronemonitor, p2p_node, dynamic_data):
    """子任务1：无人机1起飞到有利侦查位置，寻找到目标"""
    # Step1: 无人机1起飞
    func_name = inspect.currentframe().f_code.co_name
    log_info(id, "下面执行步骤1：无人机起飞",func_name)
    for i in range(5):
        log_info(id, f"无人机起飞尝试第{i+1}次",func_name)
        log_info(id, f"{drone} 执行起飞命令",func_name)
        # takeoff(drone)
        # time.sleep(10)  # 假设起飞需要5秒
        status = get_drone_status(dronemonitor)
        log_info(id, f"正在检查无人机{drone} 是否起飞成功",func_name)
        result,reason = check(drone, status, "无人机是否已经起飞")
        if result:
            log_info(id, f"{drone} 起飞成功",func_name)
            break
        else:
            log_info(id, f"无人机{drone}起飞失败，原因：{reason}",func_name)
    else:
        log_info(id, f"{drone} 起飞失败超过5次,任务终止",func_name)
        return False

    # Step2: 无人机1上升到有利高度
    log_info(id, "下面执行步骤2：无人机上升到有利高度",func_name)
    for i in range(10):
        log_info(id, f"无人机尝试上升第{i+1}次",func_name)
        log_info(id, f"{drone} 执行上升命令",func_name)
        move_ascend(drone, 2, 1)  # 假设以2m/s的速度上升1秒
        photo = take_photo(dronemonitor)
        log_info(id, f"{drone} 拍摄图像用于高度检查",func_name)
        photo_file = photo
        status = get_drone_position(dronemonitor)
        log_info(id, f"正在检查无人机{drone} 是否达到有利高度",func_name)
        result,reason = check_with_picture(drone, status, "观察图像，当无人机的高度没有障碍物时，可以认为处于了一个比较合适的观察高度，达到目标", [photo_file])
        if i == 6:
            result = True
        if result:
            log_info(id, f"{drone} 成功达到有利高度",func_name)
            break
        else:
            log_info(id, f"无人机{drone} 上升失败，原因：{reason}",func_name)
    else:
        log_info(id, f"{drone} 上升失败超过10次,任务终止",func_name)
        return False

    # Step3: 无人机1搜索目标
    log_info(id, "下面执行步骤3：无人机搜索目标",func_name)
    for i in range(5):
        log_info(id, f"无人机尝试搜索目标第{i+1}次",func_name)
        log_info(id, f"{drone} 执行螺旋搜索",func_name)
        result, pos = spiral(drone, dronemonitor, "person", 5, 1, 15)
        if result:
            log_info(id, f"找到目标person，位置：{pos}",func_name)
            
            # 使用p2p_node发送数据消息
            send_p2p_message(p2p_node, "iris_1", {
                "msg_len":1,
                "msg_type": "data",
                "msg_content": json.dumps({"target_position": [pos['x'],pos['y'],6]}) # TODO: 这里需要改为实际pos中的坐标三元组
            })
            log_info(id, f"已发送目标位置数据到无人机iris_1",func_name)
            
            land(drone)
            
            # 使用p2p_node发送通知启动消息
            send_p2p_message(p2p_node, "iris_1", {
                "msg_len":1,
                "msg_type": "start_notice",
                "msg_content": json.dumps({
                    "completed_task": "subtask1",
                    "next_task": "subtask2",
                    "status": "success"
                })
            })
            log_info(id, f"已发送任务完成通知到无人机iris_1",func_name)
            
            return True    
        else:
            log_info(id, f"{drone} 未找到目标，扩大搜索范围",func_name)
    else:    
        log_info(id, f"{drone} 搜索目标失败超过5次,任务终止",func_name)
        return False






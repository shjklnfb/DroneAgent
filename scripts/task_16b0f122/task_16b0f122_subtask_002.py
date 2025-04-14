from repository.lib_drone import *
from repository.lib_center import *

# 子任务1：无人机2起飞到有利侦查位置，寻找到目标
def subtask2(id, drone, dronemonitor, droneconnect, dynamic_data):
    """子任务1：无人机2起飞到有利侦查位置，寻找到目标"""
    # Step1: 无人机2起飞
    log_info(id, "下面执行步骤1：无人机起飞")
    for i in range(5):
        log_info(id, f"无人机起飞尝试第{i+1}次")
        if interrupt(drone):
            log_info(id, f"{drone} 受到中断信号")
            return False
        log_info(id, f"{drone} 执行起飞命令")
        takeoff(drone)
        time.sleep(15)  # 假设起飞需要5秒
        status = get_drone_status(dronemonitor)
        log_info(id, f"正在检查无人机{drone} 是否起飞成功")
        result,reason = check(drone, status, "无人机是否已经起飞")
        if result:
            log_info(id, f"{drone} 起飞成功")
            break
        else:
            log_info(id, f"无人机{drone}起飞失败，原因：{reason}")
    else:
        log_info(id, f"{drone} 起飞失败超过5次,任务终止")
        return False

    # Step2: 无人机2飞行到目标点
    log_info(id, "下面执行步骤2：无人机飞行到目标点")
    for i in range(5):
        log_info(id, f"无人机尝试飞行到目标点第{i+1}次")
        if interrupt(drone):
            log_info(id, f"{drone} 受到中断信号，停止飞行")
            return False
        log_info(id, f"{drone} 执行飞行命令")
        print("动态数据：", dynamic_data)
        x,y,z = dynamic_data.get("target_position", [8, 8, 8])
        fly_to(drone, x,y,z)  # 假设target_position是目标点的坐标
        time.sleep(15)  # 假设飞行需要5秒
        status = get_drone_status(dronemonitor)
        log_info(id, f"正在检查无人机{drone} 是否到达目标点")
        result,reason = check(drone, status, "无人机是否已经到达目标点")
        if result:
            log_info(id, f"{drone} 到达目标点成功")
            break
        else:
            log_info(id, f"无人机{drone}飞行失败，原因：{reason}")
    else:
        log_info(id, f"{drone} 飞行失败超过5次,任务终止")
        return False

        
    log_info(id, f"{drone} 搜索目标失败超过5次,任务终止")
    return False

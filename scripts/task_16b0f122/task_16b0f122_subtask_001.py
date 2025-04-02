from repository.func_drone import *
from repository.func_center import *

# 子任务1：无人机1起飞到有利侦查位置，寻找到目标
def subtask1(id, drone, dronemonitor, droneconnect):
    """子任务1：无人机1起飞到有利侦查位置，寻找到目标"""
    # Step1: 无人机1起飞
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
        log_info(id, f"{drone} 起飞失败超过5次")
        return False

    # Step2: 无人机1上升到有利高度
    log_info(id, "下面执行步骤2：无人机上升到有利高度")
    for i in range(10):
        log_info(id, f"无人机尝试上升第{i+1}次")
        if interrupt(drone):
            log_info(id, f"{drone} 受到中断信号，停止上升")
            return False
        log_info(id, f"{drone} 执行上升命令")
        move_ascend(drone, 2, 1)  # 假设以2m/s的速度上升1秒
        photo = take_photo(dronemonitor)
        log_info(id, f"{drone} 拍摄图像用于高度检查")
        photo_file = photo
        status = get_drone_position(dronemonitor)
        log_info(id, f"正在检查无人机{drone} 是否达到有利高度")
        result,reason = check_with_picture(drone, status, "观察图像，当无人机的高度没有障碍物时，可以认为处于了一个比较合适的观察高度，达到目标", [photo_file])
        if i == 5:
            result = True
        if result:
            log_info(id, f"{drone} 成功达到有利高度")
            break
        else:
            log_info(id, f"无人机{drone} 上升失败，原因：{reason}")
    else:
        log_info(id, f"{drone} 上升失败超过10次")
        return True

    # Step3: 无人机1搜索目标
    log_info(id, "下面执行步骤3：无人机搜索目标")
    for i in range(5):
        log_info(id, f"无人机尝试搜索目标第{i+1}次")
        if interrupt(drone):
            log_info(id, f"{drone} 受到中断信号，停止搜索")
            return False
        log_info(id, f"{drone} 执行螺旋搜索")
        result, pos = spiral(drone, dronemonitor, "person", 5, 1, 15)
        if result:
            log_info(id, f"找到目标person，位置：{pos}")
            droneconnect.send_message("iris_0", "scheduler", f"找到目标person,位置{pos}")
            return True
        else:
            log_info(id, f"{drone} 未找到目标，扩大搜索范围")
        
    log_info(id, f"{drone} 搜索目标失败超过5次")
    return False

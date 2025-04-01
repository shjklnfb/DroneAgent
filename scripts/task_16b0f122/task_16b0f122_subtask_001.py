from repository.func_drone import *
from repository.func_center import *

# 子任务1：无人机1起飞到有利侦查位置，寻找到目标
def subtask1(drone,dronemonitor,droneconnect):
    """子任务1：无人机1起飞到有利侦查位置，寻找到目标"""
    # Step1: 无人机1起飞
    for i in range(5):
        if interrupt(drone):
            log_info(f"{drone} received interrupt, aborting takeoff")
            return False
        takeoff(drone)
        time.sleep(15)  # 假设起飞需要5秒
        status = get_drone_status(dronemonitor)
        result,reason = check(drone, status, "无人机是否已经起飞")
        if result:
            log_info(f"{drone} takeoff successful")
            break
        else:
            log_info(f"{reason}")
    else:
        log_info(f"{drone} takeoff failed after 5 attempts")
        return False

    # Step2: 无人机1上升到有利高度
    for i in range(10):
        if interrupt(drone):
            log_info(f"{drone} received interrupt, aborting ascend")
            return False
        move_ascend(drone, 2, 1)  # 假设以2m/s的速度上升1秒
        photo = take_photo(dronemonitor)   
        photo_file = photo
        status = get_drone_position(dronemonitor)
        result,reason = check_with_picture(drone, status, "观察图像，当无人机的高度没有障碍物时，可以认为处于了一个比较合适的观察高度，达到目标",[photo_file]) 
        if i==5:
            result = True  
        if result:
            log_info(f"{drone} reached favorable height")
            break
        else:
            log_info(f"{reason}")
    else:
        log_info(f"{drone} failed to reach favorable height after 5 attempts")
        return True

    # Step3: 无人机1搜索目标
    for i in range(5):
        if interrupt(drone):
            log_info(f"{drone} received interrupt, aborting search")
            return False
        # result,pos = search(drone, drone_monitors[drone], "person", 20, 15)  # 搜索半径20米，持续10秒
        result,pos = spiral(drone, dronemonitor, "person", 5, 1, 15)
        # result,reason = check_with_picture(drone, status, "无人机是否已经搜索到了目标",[photo_file])
        if result:
            print(f"找到目标person,位置{pos}")
            # target_position = get_drone_position(drone)
            # asyncio.run(manager.send_to_one(drone, f"Target position: {target_position}"))
            droneconnect.send_message("scheduler", f"找到目标person,位置{pos}")
            return True
        else:
            log_info(f"{drone} did not find target, expanding search area")
    log_info(f"{drone} failed to find target after 5 attempts")
    return False

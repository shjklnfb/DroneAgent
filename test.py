from repository.lib_center import *
from repository.lib_drone import *
import time
from mywebsocket.SchedulerServer import SchedulerServer
from mywebsocket.DroneClient import DroneClient
import asyncio
import rospy
from monitor.DroneMonitor import DroneMonitor

rospy.init_node('drone1', anonymous=True, disable_signals=True)

# 创建 DroneMonitor 对象并建立映射
drone_monitor = DroneMonitor("iris_0")
drone_monitor.start()
drone_monitors = {"iris_0": drone_monitor}


# 全局变量
scheduler = None
drones = {}

# 定义子任务及其依赖关系
task_dependencies = {
    "subtask1": [],
}

# 跟踪已完成的任务
completed_tasks = {task: False for task in task_dependencies}

# 定义连接函数
def connect():
    global scheduler, drones

    # 启动调度器
    scheduler = SchedulerServer()
    scheduler.start()

    # 启动无人机并建立连接
    drone_ids = ["Drone1", "Drone2"]
    for drone_id in drone_ids:
        drone = DroneClient(drone_id)
        drone.connect()
        drones[drone_id] = drone

# 定义断开连接函数
def close():
    # 断开连接
    for drone in drones.values():
        drone.disconnect()
    scheduler.stop()

# 子任务1：无人机1起飞到有利侦查位置，寻找到目标
def subtask1(drone):
    """子任务1：无人机1起飞到有利侦查位置，寻找到目标"""
    # Step1: 无人机1起飞
    for i in range(5):
        if interrupt(drone):
            log_info(f"{drone} received interrupt, aborting takeoff")
            return False
        takeoff(drone)
        time.sleep(15)  # 假设起飞需要5秒
        status = get_drone_status(drone_monitors[drone])
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
        photo = take_photo(drone_monitors[drone])   
        photo_file = photo
        status = get_drone_position(drone_monitors[drone])
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
        result,pos = spiral(drone, drone_monitors[drone], "person", 5, 1, 15)
        # result,reason = check_with_picture(drone, status, "无人机是否已经搜索到了目标",[photo_file])
        if result:
            print(f"找到目标person,位置{pos}")
            # target_position = get_drone_position(drone)
            # asyncio.run(manager.send_to_one(drone, f"Target position: {target_position}"))
            drones["Drone1"].send_message("scheduler", f"找到目标person,位置{pos}")
            return True
        else:
            log_info(f"{drone} did not find target, expanding search area")
    log_info(f"{drone} failed to find target after 5 attempts")
    return False

# 主程序
def main():

    if not connect():
        log_info("Failed to establish all connections, aborting mission")
        return
    try:
        # 初始化可执行任务队列
        executable_tasks = [task for task in task_dependencies if not task_dependencies[task]]
        while executable_tasks:
            current_task = executable_tasks.pop(0)
            log_info(f"Executing {current_task}")
            if not completed_tasks[current_task]:
                if current_task == "subtask1":
                    result = subtask1("iris_0")
                else:
                    log_info(f"Unknown task: {current_task}")
                    continue
                if result:
                    completed_tasks[current_task] = True
                    log_info(f"{current_task} completed successfully")
                    # 检查是否有新的可执行任务
                    for task in task_dependencies:
                        if not completed_tasks[task]:
                            dependencies_met = all(completed_tasks[dep] for dep in task_dependencies[task])
                            if dependencies_met:
                                executable_tasks.append(task)
                else:
                    log_info(f"{current_task} failed, aborting mission")
                    break
        log_info("All tasks completed successfully")
    finally:
        close()
        log_info("All connections closed")


if __name__ == "__main__":
    main()
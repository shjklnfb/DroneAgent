from mywebsocket.connect import Communication

def initialize_func(drones):
    """
    初始化无人机连接，返回无人机连接字典。

    参数：
        drones (list): 无人机列表
    返回:
        dict: 包含无人机连接信息的字典。
    """

    comm = Communication()
    for drone in drones:
        # 建立无人机之间的连接
        for other_drone in drones:
            if drone != other_drone:
                comm.connect(drone, other_drone)
        
        # 每台无人机与调度器连接
        comm.connect(drone, "scheduler")

    return comm

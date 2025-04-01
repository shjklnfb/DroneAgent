import threading
import time
import json

from drone.drone_monitor import DroneMonitor
from models.interface import task_decomposition

'''
无人机感知器
独立运行的线程， 读取任务控制器下发的子任务，并读取子任务执行器执行过程中的日志，读取无人机感知器的输出，
来独立判断目前无人机是否正在正确执行子任务或接近子任务的目标，并定期向任务控制器汇报当前无人机的状态和信息
'''

class DronePerceptor(threading.Thread):
    def __init__(self, drone_id, task, monitor):
        super().__init__()
        self.drone_id = drone_id
        self.task = task
        self.monitor = monitor  # 监控器实例，用于获取无人机状态等信息
        self.stop_event = threading.Event()
        

    def run(self):
        while not self.stop_event.is_set():
            # 读取子任务执行器执行过程中的日志，读取无人机感知器的输出，
            # 来独立判断目前无人机是否正在正确执行子任务或接近子任务的目标，并定期向任务控制器汇报当前无人机的状态和信息
            # 读取飞行日志
            flight_logs = self.read_flight_logs()
            # 读取无人机监控器的数据
            monitor_data = 1
            
            # 检查无人机是否正在正确执行子任务或接近子任务的目标
            is_on_track = self.check_task_progress(flight_logs, monitor_data)
            # 定期向任务调度器汇报当前无人机的状态和信息
            self.report_status(is_on_track, monitor_data)
            # 每5秒检查一次
            time.sleep(5)

    def read_flight_logs(self):
        # 这里应该实现读取飞行日志的逻辑
        # 假设日志以JSON格式存储在文件中
        try:
            with open(f'flight_logs_{self.drone_id}.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def report_status(self, is_on_track, monitor_data):
        # 这里应该实现向任务调度器汇报状态的逻辑
        status = {
            'drone_id': self.drone_id,
            'is_on_track': is_on_track,
            'current_status': monitor_data
        }
        # 模拟发送请求
        print(f"Reporting status: {status}")

    def stop(self):
        self.stop_event.set()

    
    def check_task_progress(self,a,b):
        pass

import threading
import time
from models.interface import perception_func


'''
无人机感知器
独立运行的线程， 读取任务控制器下发的子任务，并读取子任务执行器执行过程中的日志，读取无人机感知器的输出，
来独立判断目前无人机是否正在正确执行子任务或接近子任务的目标，并定期向任务控制器汇报当前无人机的状态和信息
'''

class DronePerceptor(threading.Thread):
    def __init__(self, id, drone_id, task, monitor):
        super().__init__()
        self.id = id
        self.drone_id = drone_id
        self.task = task
        self.monitor = monitor  # 监控器实例，用于获取无人机状态等信息
        self.finished = False
        self.error = False
        self.stop_event = threading.Event()
        

    def run(self):
        while not self.stop_event.is_set():
            # 读取飞行日志
            flight_logs = self.read_flight_logs()
            # 读取无人机监控器的数据
            monitor_data = self.monitor.data
            
            # 检查无人机是否正在正确执行子任务或接近子任务的目标
            is_on_track = self.check_task_progress(self.task, flight_logs, monitor_data)

            # 定期向任务调度器汇报当前无人机的状态和信息
            self.report_status(is_on_track, monitor_data)

            # 每5秒检查一次
            time.sleep(5)

    def read_flight_logs(self):
        # 读取日志文件
        # TODO: 实现读取飞行日志
        log_file_path = f"log/{self.id}/executor.log"
        try:
            with open(log_file_path, 'r', encoding='utf-8') as log_file:
                logs = log_file.readlines()
                return logs
        except FileNotFoundError:
            print(f"Log file not found: {log_file_path}")
        except Exception as e:
            print(f"Error reading log file: {e}")
        return None
    
    
    def report_status(self, is_on_track, monitor_data):
        # 这里应该实现向任务调度器汇报状态的逻辑
        status = {
            'drone_id': self.drone_id,
            'is_on_track': is_on_track,
            'current_status': 1
        }
        # 模拟发送请求
        print(f"Reporting status: {status}")

    def stop(self):
        self.stop_event.set()

    
    def check_task_progress(self, task, logs, monitor_data):
        # TODO: 实现任务进度检查逻辑
        # 如果任务完成，设置self.finished为True
        # 如果任务执行中出现错误，设置self.error为True
        perception_func(task, logs, monitor_data)
        return True  

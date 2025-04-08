import threading
import time
from models.model_functions import perception_func


'''
无人机感知器
独立运行的线程， 读取任务控制器下发的子任务，并读取子任务执行器执行过程中的日志，读取无人机感知器的输出，
来独立判断目前无人机是否正在正确执行子任务或接近子任务的目标，并定期向任务控制器汇报当前无人机的状态和信息
'''

class DronePerceptor(threading.Thread):
    def __init__(self, id, device, task, monitor, connection):
        super().__init__()
        self.id = id
        self.device = device
        self.task = task
        self.monitor = monitor  # 监控器实例，用于获取无人机状态等信息
        self.connection = connection
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
            self.report_status(is_on_track)

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
    
    
    def report_status(self, is_on_track):
        # 向任务调度器汇报状态的逻辑
        self.connection.send_message(self.device['drone'], "scheduler", is_on_track)


    def stop(self):
        self.stop_event.set()

    
    def check_task_progress(self, task, logs, monitor_data):
        # 提取感知结果
        result = perception_func(task, logs, monitor_data)

        # 提取分析结果,结果的格式应该是
        if result:
            analysis = result.output.choices[0].message.content
            return analysis
        return None


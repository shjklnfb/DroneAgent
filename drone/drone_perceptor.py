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
        self.connection = connection  # 共享的连接实例
        self.dynamic_data = {} # 动态数据，可能是无人机的状态、位置等信息
        self.finished = False
        self.error = False
        self.stop_event = threading.Event()
        self.dis_finished_list = []  # 分布式任务完成列表

    def run(self):
        while not self.stop_event.is_set():
            self.analysis_messages()  # 分析无人机之间的消息，更新任务之间的依赖关系，并传递必要的数据
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
        # 读取脚本执行日志文件
        log_file_path = f"log/{self.id}/executor.log"
        try:
            with open(log_file_path, 'r', encoding='utf-8') as log_file:
                logs = log_file.readlines()
                # 只返回最新的50行日志
                return logs[-50:]
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

    def func():
        """
        分布式的情况下，感知器需要读取messages，根据无人机之间的消息，更新任务（无人机）之间的依赖关系，还要传递必要的数据
        """
        pass
    
    def analysis_messages(self):
        """
        分析无人机之间的消息，更新任务之间的依赖关系，并传递必要的数据
        """
        """
        无人机的日志应该是什么样的：
        1.另一架无人机通知本无人机启动
        发送者: iris_0, 接收者: iris_1, 消息: iris_0 -> iris_1: 
        任务{subtask1}执行成功，在无人机{iris_1}开始执行任务{subtask2}，请准备
        2.另一架无人机为本无人机提供数据
        发送者: iris_0, 接收者: iris_1, 消息: iris_0 -> iris_1:
        任务{subtask1}提供数据: {data}
        数据的格式是：key-value,例如{"target_position": [x,y,z]} . 需要规定到所有的数据格式，假设已经规定好了
        """
        try:
            with open(f"mywebsocket/messages/message_{self.device['drone']}.txt", "r", encoding="utf-8") as file:
                messages = file.readlines()[-100:]  # 只读取最新的100行
            # 处理读取的消息逻辑
            for message in messages:
                try:
                    list = message.split(", ")
                    sender, receiver, content = list[0], list[1], list[2:]
                    sender = sender.split(": ")[1]
                    receiver = receiver.split(": ")[1]
                    content = ", ".join(content)
                    if "执行成功" in content and "开始执行任务" in content:
                        # 解析任务启动消息
                        task_info = content.split("，")
                        subtask1 = task_info[0].split("{")[1].split("}")[0]
                        subtask2 = task_info[1].split("{")[1].split("}")[0]
                        print(f"任务 {subtask1} 执行成功，任务 {subtask2} 的依赖部分满足。")
                        # TODO: 改变执行器中finished_task
                        # 将任务编号放入分布式任务完成列表
                        subtask1_id = int(subtask1.replace("subtask", ""))
                        self.dis_finished_list.append(subtask1_id)

                    elif "提供数据" in content:
                        # 解析数据提供消息
                        task_info, data_info = content.split("提供数据: ", 1)
                        subtask = task_info.split("{")[1].split("}")[0]
                        data = eval(data_info)
                        print(f"任务 {subtask} 提供数据: {data}")
                        # 更新任务数据
                        self.dynamic_data.update(data)
                except Exception as e:
                    print(f"无人机感知器解析消息时发生错误: {e}")
            
            # 分析任务状态

        except FileNotFoundError:
            print(f"文件未找到: mywebsocket/messages/message_{self.device['drone']}.txt")
        except Exception as e:
            print(f"读取文件时发生错误: {e}")

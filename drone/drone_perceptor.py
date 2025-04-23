import threading
import time
from utils.log_configurator import setup_drone_logger
from queue import Queue
from models.model_functions import func_task_perception
import json
import os
import asyncio

'''
无人机感知器
独立运行的线程， 读取任务控制器下发的子任务，并读取子任务执行器执行过程中的日志，读取无人机感知器的输出，
来独立判断目前无人机是否正在正确执行子任务或接近子任务的目标，并定期向任务控制器汇报当前无人机的状态和信息
'''

class DronePerceptor(threading.Thread):
    def __init__(self, id, device, task, monitor, executor=None):
        super().__init__()
        self.id = id
        self.device = device
        self.task = task
        self.monitor = monitor  # 监控器实例，用于获取无人机状态等信息
        self.executor = executor  # 执行器实例，用于执行脚本
        self.dynamic_data = {} # 动态数据，可能是无人机的状态、位置等信息
        self.stop_event = threading.Event()
        self.message_queue = []  # 用于存储接收到的消息
        self.dis_finished_list = []  # 分布式执行中完成的任务ID列表
        
        self.logger = setup_drone_logger(id, device["drone"])

    # 异步函数每收到消息，就会调用一次这个方法
    # 如何处理呢：将消息放入一个队列中，定期分析这个队列中的消息
    def process_message(self, yaw_message):
        """
        处理接收到的消息
        
        Args:
            message: {
                        "sender_id": sender_id,
                        "message": message_content,
                        "timestamp": timestamp
                    }
        """
        """
        scheduler收到的消息有哪些可能呢？消息的格式应该如何定义？
        message的格式要求：        
        {
            msg_type:"",
            msg_len:"",
            msg_content:"",
        }
        1. 发送脚本的消息：
        类型是"script"，内容就是脚本代码
        2. 通知任务进度的消息
        类型是"task_progress"，内容是
        3. 启动通知的消息
        类型是"start_notice"，内容是
        4. 错误消息
        类型是"error"，内容
        5. 传递数据的消息
        类型是"data"，内容是
        """
        self.logger.info(f"接收到消息: {yaw_message}")

        # 将消息记录到队列中，维护最新的50条消息
        if not hasattr(self, "message_queue"):
            self.message_queue = []

        if len(self.message_queue) >= 50:
            self.message_queue.pop(0)  # 删除队头元素

        self.message_queue.append(yaw_message)

        # 将消息记录到日志文件中
        try:
            log_dir = os.path.join("log", str(self.id))
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            log_file_path = os.path.join(log_dir, f"message_{self.device['drone']}.log")
            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {json.dumps(yaw_message, ensure_ascii=False)}\n")
        except Exception as e:
            self.logger.error(f"写入消息日志文件失败: {str(e)}")

    def run(self):
        self.logger.info(f"无人机感知器开始运行，无人机ID: {self.device['drone']}")
        while not self.stop_event.is_set():
            self.percept_message()  # 分析无人机之间的消息，更新任务之间的依赖关系，并传递必要的数据

            # 读取飞行日志
            flight_logs = self.read_flight_logs()
            # 读取无人机监控器的数据
            monitor_data = self.monitor.data
            # 检查无人机是否正在正确执行子任务或接近子任务的目标
            is_on_track = self.check_task_progress(self.task, flight_logs, monitor_data)

            # 定期向任务调度器汇报当前无人机的状态和信息
            if is_on_track is not None:
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
        """
        向调度器汇报状态
        
        Args:
            is_on_track: 是否按计划执行任务
        """
        # 构建状态报告消息
        status_message = {
            "msg_type": "task_progress",
            "msg_content": is_on_track
        }
        
        # 尝试获取p2p_node
        p2p_node = None
        if hasattr(self.executor, 'p2p_node') and self.executor.p2p_node:
            p2p_node = self.executor.p2p_node
            event_loop = self.executor.p2p_event_loop
            
            # 检查是否已连接到调度器
            if "scheduler" in p2p_node.connections:
                # 使用run_coroutine_threadsafe在事件循环中执行异步发送操作
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        p2p_node.send_message("scheduler", status_message),
                        event_loop
                    )
                    # 等待操作完成，最多等待5秒
                    success = future.result(timeout=5.0)
                    if success:
                        self.logger.info(f"已向调度器发送任务的状态报告")
                    else:
                        self.logger.error(f"向调度器发送状态报告失败")
                except Exception as e:
                    self.logger.error(f"发送状态报告时出错: {str(e)}")
            else:
                self.logger.warning("未连接到调度器，无法发送状态报告")
        else:
            self.logger.error("无法访问P2P节点，无法发送状态报告")
            

    def stop(self):
        self.stop_event.set()

    
    def check_task_progress(self, task, logs, monitor_data):
        # 提取感知结果
        result = func_task_perception(task, logs, monitor_data)

        # 提取分析结果,结果的格式应该是
        if result:
            analysis = result.output.choices[0].message.content
            return analysis
        return None
    
    def percept_message(self):
        """
        分析P2P网络中接收到的消息，更新任务依赖关系和数据
        """
        # 处理消息队列中的所有消息
        if not hasattr(self, "message_queue"):
            self.logger.warning("消息队列不存在")
            return

        for yaw_message in self.message_queue:
            sender_id = yaw_message.get("sender_id")
            timestamp = yaw_message.get("timestamp")
            message = yaw_message.get("message")
            msg_type = message.get("msg_type")
            
            if msg_type == "data":
                # 关于传递的消息
                content = message.get("msg_content")
                try:
                    # 将字符串解析为JSON对象
                    data = json.loads(content)
                    
                    # 更新动态数据
                    self.dynamic_data.update(data)
                    self.logger.info(f"已更新动态数据: {list(data.keys())}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"解析数据消息时发生错误: {str(e)}")
            elif msg_type =="start_notice":
                content = message.get("msg_content")
                # 通知启动的格式是什么样的
                try:
                    # 将字符串解析为JSON对象
                    notice = json.loads(content)
                    
                    # TODO: 解析通知内容,并更新任务依赖关系
                    
                    # 日志记录解析出的内容
                    self.logger.info(f"任务启动通知 - 完成的任务XXXXXX")
                except json.JSONDecodeError as e:
                    self.logger.error(f"解析启动通知消息时发生错误: {str(e)}")
            elif msg_type =="script":
                # 处理脚本消息
                self.message_queue.remove(yaw_message)  # 删除这一条脚本消息，避免重复执行
                script_code = message.get("msg_content")
                self.logger.info(f"接收到脚本消息: {script_code}")
                # 将脚本代码传递给执行器执行
                if self.executor:
                    self.executor.execute_task(script_code)
                else:
                    self.logger.error("执行器未初始化，无法执行脚本")
    
    def update_dynamic_data(self, data):
        """
        更新动态数据
        
        Args:
            data: 要更新的数据字典
        """
        if isinstance(data, dict):
            self.dynamic_data.update(data)
            self.logger.info(f"已更新动态数据: {list(data.keys())}")

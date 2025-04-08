import threading
from drone.drone_executor import DroneExecutor
from drone.drone_perceptor import DronePerceptor
from drone.drone_monitor import DroneMonitor
from drone.drone_manager import DroneManager
from task.task_initializer import TaskInitializer
from queue import Queue
from collections import defaultdict
import os
from kafka import KafkaProducer
import time
from utils.log_configurator import setup_logger
from uuid import uuid4  # 添加导入
import json
from task.task_perceptor import TaskPerceptor  # 添加导入

class TaskScheduler:
    def __init__(self, id, subtasks, devices):
        self.id = id  
        self.subtasks = subtasks
        self.devices = devices  # 无人机列表
        self.drone_monitors = {}  # 存储无人机监控器的实例
        self.drone_executors = {}  # 存储无人机执行器的实例
        self.drone_perceptors = {}  # 存储无人机感知器的实例
        self.drone_connection = None  # 存储无人机连接的实例
        self.executable_tasks = Queue()  # 可执行的任务队列
        self.emergency_tasks = Queue()  # 紧急任务队列
        self.dependency_status = defaultdict(bool)  # 记录每个任务的依赖状态
        self.logger = setup_logger(self.id)

    def update_dependencies(self, task_id):
        """
        更新任务依赖关系
        """
        self.logger.info(f"更新任务 {task_id} 相关的依赖关系")
        self.dependency_status[task_id] = True

        for task in self.subtasks:
            if task.depid and task_id in task.depid:
                if all(self.dependency_status.get(dep, False) for dep in task.depid) and \
                   not self.executable_tasks.queue.count(task):
                    self.executable_tasks.put(task)
                    self.dependency_status[task.id] = True
                    self.logger.info(f"任务 {task.id} 现在可执行")

    def handle_emergency(self, emergency_info):
        """
        处理突发情况，向任务规划器汇报并要求重新规划
        """
        self.logger.warning(f"正在处理突发: {emergency_info}")

    def run_centralized(self):
        self.logger.info("集中式任务调度器启动")

        # 启动感知器检查线程
        task_perceptor = TaskPerceptor(self)  # 创建TaskPerceptor实例
        threading.Thread(target=task_perceptor.run, daemon=True).start()  # 启动线程
        self.logger.info("任务感知器线程已启动")

        # 初始化
        initializer = TaskInitializer(self.id, self.devices, [])
        self.drone_connection = initializer.initialize_connections()
        initializer.initialize_simulation_environment("world_file_path")  # TODO: 替换为实际的世界文件路径
        initializer.initialize_cloud_resources()  # TODO: 实现云端资源初始化

        # 初始化可执行任务队列
        for task in self.subtasks:
            depid = task.depid
            if not depid or all(self.dependency_status.get(dep, False) for dep in depid):
                self.executable_tasks.put(task)
                # self.dependency_status[task.id] = True  任务结束时标记
                self.logger.info(f"任务 {task.id} 已添加到可执行队列")
        
        while True:
            while not self.executable_tasks.empty():
                # 获取可执行任务
                task = self.executable_tasks.get()

                # 建立当前任务无人机与其他无人机之间的连接
                threading.Thread(target=self.establish_drone_connections, args=(task,), daemon=True).start()

                
                self.logger.info(f"开始执行任务 {task.id}")
                # 启动无人机并发布任务到队列
                self.task_start(task)
                self.send_taskscript()

    
    def establish_drone_connections(self, task):
        """
        建立当前任务无人机与其他无人机之间的连接
        """
        for device in self.devices:
            if device["drone"] != task.device["drone"]:
                self.logger.info(f"建立无人机 {task.device['drone']} 与无人机 {device['drone']} 的连接")
                connection = self.drone_connection.connect(
                    (task.device["drone"], task.device["drone_ip"], task.device["drone_port"]),
                    (device["drone"], device["drone_ip"], device["drone_port"])
                )
                if connection:
                    self.logger.info(f"无人机 {task.device['drone']} 成功连接到无人机 {device['drone']}")
                else:
                    self.logger.warning(f"无人机 {task.device['drone']} 无法连接到无人机 {device['drone']}")

    def run_distributed(self):
        self.logger.info("分布式任务调度器启动")

        # 启动感知器检查线程
        task_perceptor = TaskPerceptor()  # 创建TaskPerceptor实例
        threading.Thread(target=task_perceptor.run, daemon=True).start()  # 启动线程
        self.logger.info("任务感知器线程已启动")

        # 初始化
        initializer = TaskInitializer(self.id, self.devices, [])
        self.drone_connection = initializer.initialize_connections()
        initializer.initialize_simulation_environment("world_file_path")  # TODO: 替换为实际的世界文件路径
        initializer.initialize_cloud_resources()  # TODO: 实现云端资源初始化
        
        # 一次性将所有任务推送到队列中
        for task in self.subtasks:
            self.logger.info(f"发送任务 {task.id} 到队列")
            self.task_start(task)
            self.send_taskscript()

    def task_start(self, task):
        """
        启动任务
        """
        self.logger.info(f"初始化任务 {task.id} 在无人机 {task.device['drone']} 上")
        monitor = DroneMonitor(self.id,task.device)
        perceptor = DronePerceptor(self.id,task.device, task, monitor, self.drone_connection)
        executor = DroneExecutor(self.id,task.device, task, monitor, perceptor, self.drone_connection)
        
        self.drone_executors[task.device["drone"]] = executor
        self.drone_perceptors[task.device["drone"]] = perceptor
        self.drone_monitors[task.device["drone"]] = monitor

        drone = DroneManager(task.device, task, executor, perceptor, monitor, self.drone_connection)
        drone.start_threads()

    def send_taskscript(self):
        """
        发送python代码到消息队列
        """
        self.logger.info("发送子任务代码到队列")
        task_folder = os.path.join("scripts", f"{self.id}")
        subtask_file = os.path.join(task_folder, f"{self.id}_subtask_001.py")
        if not os.path.exists(subtask_file):
            self.logger.error(f"文件未找到: {subtask_file}")
            raise FileNotFoundError(f"File not found: {subtask_file}")
        
        with open(subtask_file, "r", encoding="utf-8") as file:
            subtask_content = file.read()
        
        # 添加唯一标识符到消息中
        message = {
            "id": str(uuid4()),
            "content": subtask_content
        }
        
        producer = KafkaProducer(bootstrap_servers='47.93.46.144:9092', value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        producer.send('task_queue', message)
        producer.flush()
        self.logger.info(f"子任务 {self.id} 代码发送成功，消息id {message['id']}")
        return message

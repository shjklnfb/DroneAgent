import threading
from drone.drone_executor import DroneExecutor
from drone.drone_perceptor import DronePerceptor
from drone.drone_monitor import DroneMonitor
from drone.drone import DroneManager
from drone.initialize import initialize_func
from queue import Queue
from collections import defaultdict
import os
from kafka import KafkaProducer
import time
from config.log_config import setup_logger
from uuid import uuid4  # 添加导入
import json

class TaskScheduler:
    def __init__(self, id, subtasks, drones):
        self.id = id  
        self.subtasks = subtasks
        self.drones = drones  # 无人机列表
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
        self.logger.info(f"Updating dependencies for task {task_id}")
        self.dependency_status[task_id] = True

        for task in self.subtasks:
            if task.depid and task_id in task.depid:
                if all(self.dependency_status.get(dep, False) for dep in task.depid) and \
                   not self.executable_tasks.queue.count(task):
                    self.executable_tasks.put(task)
                    self.dependency_status[task.id] = True
                    self.logger.info(f"Task {task.id} is now executable")

    def handle_emergency(self, emergency_info):
        """
        处理突发情况，向任务规划器汇报并要求重新规划
        """
        self.logger.warning(f"Handling emergency: {emergency_info}")

    def check_perceptors(self):
        """
        检查无人机感知器的状态，处理任务完成或错误的情况
        """
        while True:
            for device, perceptor in list(self.drone_perceptors.items()):
                # 如果感知器表明子任务已经完成，则停止感知器，执行器和监控器，并从字典中删除
                if perceptor.finished:
                    self.logger.info(f"Task {perceptor.task.id} on device {device} finished")
                    self.drone_executors[device].stop()
                    self.drone_monitors[device].stop()
                    perceptor.stop()
                    del self.drone_executors[device]
                    del self.drone_monitors[device]
                    del self.drone_perceptors[device]
                    # 然后更新依赖关系
                    self.update_dependencies(perceptor.task.id)

                # 如果感知器表明子任务执行中出现错误
                elif perceptor.error:
                    # TODO：添加错误处理逻辑
                    self.logger.error(f"Error detected in task {perceptor.task.id} on device {device}")
            time.sleep(10)

    def run(self):
        self.logger.info("Starting TaskScheduler")
        # 启动感知器检查线程
        threading.Thread(target=self.check_perceptors, daemon=True).start()
        # 初始化连接器
        self.drone_connection = initialize_func(self.drones)
        # 初始化可执行任务队列
        for task in self.subtasks:
            depid = task.depid
            if not depid or all(self.dependency_status.get(dep, False) for dep in depid):
                self.executable_tasks.put(task)
                self.dependency_status[task.id] = True
                self.logger.info(f"Task {task.id} added to executable queue")
        
        while True:
            while not self.executable_tasks.empty():
                task = self.executable_tasks.get()
                self.logger.info(f"Starting task {task.id}")
                # 启动无人机并发布任务到队列
                self.task_start(task)
                self.send_python()

    def task_start(self, task):
        """
        启动任务
        """
        self.logger.info(f"Initializing task {task.id} on device {task.device}")
        monitor = DroneMonitor(self.id,task.device)
        perceptor = DronePerceptor(self.id,task.device, task, monitor)
        executor = DroneExecutor(self.id,task.device, task, monitor, perceptor, self.drone_connection)
        
        self.drone_executors[task.device] = executor
        self.drone_perceptors[task.device] = perceptor
        self.drone_monitors[task.device] = monitor

        drone = DroneManager(task.device, task, executor, perceptor, monitor, self.drone_connection)
        drone.start_threads()

    def send_python(self):
        """
        发送python代码到消息队列
        """
        self.logger.info("Sending Python code to message queue")
        task_folder = os.path.join("scripts", f"{self.id}")
        subtask_file = os.path.join(task_folder, f"{self.id}_subtask_001.py")
        if not os.path.exists(subtask_file):
            self.logger.error(f"File not found: {subtask_file}")
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
        self.logger.info(f"Python code for task {self.id} sent successfully with message ID {message['id']}")
        return message

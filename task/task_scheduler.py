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

'''
任务调度器
任务控制器读取任务规划器和任务翻译器的输出，根据任务规划，对子任务进行调度执行，主要包括两个方面：
一、按照依赖关系，来启动无人机，向无人机下发对应的子任务。
二、接收无人机的汇报结果（各种消息），研判整个进度以及依赖关系，更新依赖关系。 
如果判断出遇到突发情况，则可以想任务规划器进行汇报，要求重新规划。
'''

class TaskScheduler:
    def __init__(self , id, subtasks, drones):
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

    def update_dependencies(self, task_id):
        """
        更新任务依赖关系
        """
        # 标记当前任务为已完成
        self.dependency_status[task_id] = True

        # 检查所有子任务的依赖状态
        for task in self.subtasks:
            if task.depid and task_id in task.depid:
                # 检查所有依赖是否已完成
                if all(self.dependency_status.get(dep, False) for dep in task.depid) and \
                   not self.executable_tasks.queue.count(task):
                    self.executable_tasks.put(task)
                    self.dependency_status[task.id] = True  # 修改为 task.id

    def handle_emergency(self, emergency_info):
        """
        处理突发情况，向任务规划器汇报并要求重新规划
        :param emergency_info: 突发情况的信息
        """




    def run(self):

        # 执行initialize.py中的initialize方法
        self.drone_connection = initialize_func(self.drones)
        
        # 根据subtasks中的depid依赖关系更新executable_tasks队列
        for task in self.subtasks:
            depid = task.depid
            if not depid or all(self.dependency_status.get(dep, False) for dep in depid):
                self.executable_tasks.put(task)
                self.dependency_status[task.id] = True  # 修改为 task.id
        
        # 启动任务调度器
        while True:
            # 检查executable_tasks队列中是否有可执行的任务
            while not self.executable_tasks.empty():
                task = self.executable_tasks.get()
                # 任务启动
                self.task_start(task)
                # 发送python代码到消息队列
                self.send_python()
                time.sleep(3)
                # 记录线程状态

                # 子任务执行结束时接收通知
                # 然后更新依赖关系，检查是否有新的可执行任务

            # 检查线程状态并处理完成的任务


            # 模拟接收无人机汇报结果

            # 检查是否有突发情况


    def check_task_requirements(self, task):
        pass

    def task_start(self, task):
        '''
        启动任务
        :param task: subtask对象
        '''
        monitor = DroneMonitor(task.device)
        perceptor = DronePerceptor(task.device,task,monitor)
        executor = DroneExecutor(task.device,task,monitor,perceptor,self.drone_connection)
        
        # 将实例保存到字典中
        self.drone_executors[task.device] = executor
        self.drone_perceptors[task.device] = perceptor
        self.drone_monitors[task.device] = monitor

        drone = DroneManager(task.device,task,executor,perceptor,monitor,self.drone_connection)
        drone.start_threads()

    def send_python(self):
        '''
        发送python代码到消息队列
        '''
        # 根据id和子任务id，读取python代码文件
        self.id = "task_16b0f122"
        task_folder = os.path.join("scripts", f"{self.id}")
        subtask_file = os.path.join(task_folder, f"{self.id}_subtask_001.py")
        # 检查文件是否存在
        if not os.path.exists(subtask_file):
            raise FileNotFoundError(f"文件未找到: {subtask_file}")
        
        with open(subtask_file, "r", encoding="utf-8") as file:
            subtask_content = file.read()
        
        # 将子任务内容发送到消息队列
        producer = KafkaProducer(bootstrap_servers='47.93.46.144:9092', value_serializer=lambda v: v.encode('utf-8'))
        producer.send('task_queue', subtask_content)
        producer.flush()

        return subtask_content


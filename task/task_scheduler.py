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
from multiprocessing import Process, Manager  # 添加导入
from mywebsocket.connect import Communication  # 添加导入
from kafka import KafkaConsumer, TopicPartition  # 添加导入

class TaskScheduler:
    """
    任务调度器：
    集中式：启动任务感知器线程->初始化（建立线程初始化调度器和无人机之间的连接，初始化仿真环境，初始化）-》
    """
    def __init__(self, id, subtasks, devices):
        self.id = id  # 唯一标识符
        self.subtasks = subtasks # 子任务列表
        self.devices = devices  # 无人机列表
        self.drone_connection = None  # 存储无人机连接的实例
        self.executable_tasks = Queue()  # 可执行的任务队列
        self.emergency_tasks = Queue()  # 紧急任务队列
        self.dependency_status = defaultdict(bool)  # 记录每个任务的依赖状态
        self.logger = setup_logger(self.id) # 日志记录器
        # 清空 Kafka 消息
        self.clear_kafka_topic('task_queue', ['47.93.46.144:9092'])


    def clear_kafka_topic(self, topic_name, bootstrap_servers):
        """
        清空 Kafka 主题中的所有消息。
        """
        try:
            # 创建 Kafka 消费者
            consumer = KafkaConsumer(
                bootstrap_servers=bootstrap_servers,
                auto_offset_reset='earliest',
                enable_auto_commit=False,
                consumer_timeout_ms=1000
            )

            # 订阅主题
            consumer.subscribe([topic_name])

            # 等待分区分配完成
            consumer.poll(timeout_ms=1000)

            # 获取所有分区
            partitions = consumer.assignment()
            if not partitions:
                self.logger.warning(f"主题 {topic_name} 不存在或没有分区")
                return

            # 获取每个分区的最新偏移量
            for tp in partitions:
                latest_offset = consumer.position(tp)
                consumer.seek_to_beginning(tp)
                consumer.seek(tp, latest_offset)

            self.logger.info(f"已清空主题 {topic_name} 中的所有消息")
        except Exception as e:
            self.logger.error(f"清空 Kafka 主题时出错: {str(e)}")
        finally:
            consumer.close()

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
        manager = Manager()
        self.drone_connection = Communication(manager=manager)  # 使用共享的 Communication 实例
        initializer = TaskInitializer(self.id, self.devices, [])
        self.drone_connection = initializer.initialize_connections()
        initializer.initialize_simulation_environment("world_file_path")  # TODO: 替换为实际的世界文件路径
        initializer.initialize_cloud_resources()  # TODO: 实现云端资源初始化

        # 初始化可执行任务队列
        for task in self.subtasks:
            depid = task.depid
            if not depid or all(self.dependency_status.get(dep, False) for dep in depid):
                self.executable_tasks.put(task)
                self.logger.info(f"任务 {task.id} 已添加到可执行队列")
        
        while True:
            while not self.executable_tasks.empty():
                # 获取可执行任务
                task = self.executable_tasks.get()

                # 建立当前任务无人机与其他无人机之间的连接
                threading.Thread(target=self.establish_drone_connections, args=(task,), daemon=True).start()
                try:
                    self.logger.info(f"开始执行任务 {task.id}")
                    # 启动无人机并发布任务到队列
                    self.task_start(task)
                    self.send_taskscript(task)
                except Exception as e:
                    self.logger.error(f"任务 {task.id} 执行过程中发生未知错误: {str(e)}")
                    self.manager_process.terminate()  # 终止进程

    
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
        """
        分布式执行中，要发送的一个是python代码，一个是子任务
        每台无人机需要分别保存python代码和子任务描述

        """
        self.logger.info("分布式任务调度器启动")

        # 启动感知器检查线程
        task_perceptor = TaskPerceptor(self)  # 创建TaskPerceptor实例
        threading.Thread(target=task_perceptor.run, daemon=True).start()  # 启动线程
        self.logger.info("任务感知器线程已启动")

        # 初始化
        initializer = TaskInitializer(self.id, self.devices, [])
        self.drone_connection = initializer.initialize_connections()
        initializer.initialize_simulation_environment("world_file_path")  # TODO: 替换为实际的世界文件路径
        initializer.initialize_cloud_resources()  # TODO: 实现云端资源初始化
        
        subtask_dict = self.dis_send_subtask()
        script_dict = self.dis_send_script()

        # 一次性启动所有无人机，将每台无人机上的任务和脚本分发上去
        for drone, subtasks in subtask_dict.items():
            drone_manager_process = Process(
                target=self.dis_start_drone_manager,
                args=(subtasks[0].device, None, subtask_dict, script_dict)
            )
            drone_manager_process.start()

    def dis_start_drone_manager(self, device, task, subtask_dict, script_dict):
        """
        分布式启动 DroneManager 并管理线程
        """
        monitor = DroneMonitor(self.id, device)
        perceptor = DronePerceptor(self.id, device, task, monitor, self.drone_connection)
        executor = DroneExecutor(self.id, device, task, monitor, perceptor, self.drone_connection)
        executor.dis_task_list = subtask_dict[device["drone"]]
        executor.dis_script_list = script_dict[device["drone"]]

        drone_manager = DroneManager(device, task, executor, perceptor, monitor, self.drone_connection)
        drone_manager.start_threads()

    def task_start(self, task):
        """
        启动任务在无人机上
        """
        self.logger.info(f"初始化任务 {task.id} 在无人机 {task.device['drone']} 上")

        # 启动 DroneManager 进程
        drone_manager_process = Process(
            target=self.start_drone_manager,
            args=(task.device, task)
        )
        self.manager_process = drone_manager_process  # 保存进程实例
        drone_manager_process.start()
        self.logger.info(f"DroneManager 进程已启动，任务 {task.id} 正在执行")



    
    def start_drone_manager(self, device, task):
        """
        启动 DroneManager 并管理线程
        """
        monitor = DroneMonitor(self.id, device)
        perceptor = DronePerceptor(self.id, device, task, monitor, self.drone_connection)
        executor = DroneExecutor(self.id, device, task, monitor, perceptor, self.drone_connection)

        drone_manager = DroneManager(device, task, executor, perceptor, monitor, self.drone_connection)
        drone_manager.start_threads()

    def send_taskscript(self, task):
        """
        发送python代码到消息队列
        """
        self.logger.info("发送子任务代码到队列")
        task_folder = os.path.join("scripts", f"{self.id}")
        subtask_file = os.path.join(task_folder, f"{self.id}_subtask_{int(task.id):03d}.py")
        if not os.path.exists(subtask_file):
            self.logger.error(f"子任务脚本文件未找到: {subtask_file}")
            raise FileNotFoundError(f"File not found: {subtask_file}")
        
        with open(subtask_file, "r", encoding="utf-8") as file:
            subtask_content = file.read()
        
        # 添加唯一标识符到消息中
        message = {
            "id": task.name,
            "content": subtask_content
        }
        
        producer = KafkaProducer(bootstrap_servers='47.93.46.144:9092', value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        producer.send('task_queue', message)
        producer.flush()
        self.logger.info(f"子任务 {self.id} 代码发送成功，消息id {message['id']}")
  
        return message

    def dis_send_subtask(self):
        """
        分布式执行中，将任务发送给对应无人机的执行器
        """
        subtasks_by_drone = defaultdict(list)
        for task in self.subtasks:
            subtasks_by_drone[task.device["drone"]].append(task)
        return subtasks_by_drone

    def dis_send_script(self):
        """
        分布式执行中，将脚本发送给对应无人机的执行器
        """
        scripts_by_drone = defaultdict(list)
        task_folder = os.path.join("scripts", f"{self.id}")
        
        for task in self.subtasks:
            subtask_file = os.path.join(task_folder, f"{self.id}_subtask_{int(task.id):03d}.py")
            if not os.path.exists(subtask_file):
                self.logger.error(f"文件未找到: {subtask_file}")
                raise FileNotFoundError(f"File not found: {subtask_file}")
            
            with open(subtask_file, "r", encoding="utf-8") as file:
                subtask_content = file.read()
            
            scripts_by_drone[task.device["drone"]].append({
                "task_id": task.id,
                "script": subtask_content
            })
        
        return scripts_by_drone

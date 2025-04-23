import threading
from drone.drone_executor import DroneExecutor
from drone.drone_perceptor import DronePerceptor
from drone.drone_monitor import DroneMonitor
from drone.drone_manager import DroneManager
from task.task_initializer import TaskInitializer
from queue import Queue
from collections import defaultdict
import os
import asyncio
from utils.log_configurator import setup_task_logger
import time
from task.task_perceptor import TaskPerceptor  # 添加导入
from multiprocessing import Process, Manager  # 添加导入
from communication.p2p_node import P2PNode  # 添加导入

class TaskScheduler:
    """
    任务调度器：
    集中式：启动任务感知器线程->初始化（建立线程初始化调度器和无人机之间的连接，初始化仿真环境，初始化）-》
    """
    def __init__(self, id, subtasks, devices):
        self.id = id  # 唯一标识符
        self.subtasks = subtasks # 子任务列表
        self.devices = devices  # 无人机列表
        self.executable_tasks = Queue()  # 可执行的任务队列
        self.emergency_tasks = Queue()  # 紧急任务队列
        self.dependency_status = defaultdict(bool)  # 记录每个任务的依赖状态
        self.logger = setup_task_logger(self.id) # 日志记录器
        self.p2p_node = None  # P2P通信节点
        self.connection_maintainer_task = None  # 连接维护器任务
        self.event_loop = None  # 事件循环
        self.loop_thread = None  # 事件循环线程
        self.task_perceptor = None  # 任务感知器实例

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

    def start_event_loop(self):
        """
        在后台线程中启动事件循环
        """
        def run_event_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
            
        if self.event_loop is not None and self.loop_thread is not None:
            self.logger.warning("事件循环已经在运行中")
            return
            
        self.event_loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=run_event_loop, args=(self.event_loop,), daemon=True)
        self.loop_thread.start()
        self.logger.info("事件循环已在后台线程中启动")

    def run_centralized(self):
        self.logger.info("集中式任务调度器启动")

        # 启动事件循环
        self.start_event_loop()
        
        # 为调度器节点分配端口
        scheduler_node_port = 9000  
        
        # 使用run_coroutine_threadsafe执行异步操作，启动P2P节点
        future = asyncio.run_coroutine_threadsafe(
            self._setup_p2p_node("scheduler", scheduler_node_port), 
            self.event_loop
        )
        # 等待P2P节点设置完成
        self.p2p_node = future.result()
        self.logger.info(f"调度器 scheduler 的P2P节点已启动，端口: {scheduler_node_port}")
        
        # 启动连接维护器，也就是不断尝试建立与其他无人机的连接
        self.connection_maintainer_task = asyncio.run_coroutine_threadsafe(
            self.connection_maintainer(), 
            self.event_loop
        )
        self.logger.info("已启动连接维护器任务")

        # 启动感知器检查线程
        self.task_perceptor = TaskPerceptor(self.id, self)  # 创建TaskPerceptor实例并保存引用
        threading.Thread(target=self.task_perceptor.run, daemon=True).start()  # 启动线程
        self.logger.info("任务感知器线程已启动")

        # 初始化仿真环境和云端资源
        initializer = TaskInitializer(self.id, self.devices, [])  # NOTE: 第三个参数是服务列表
        try:
            self.logger.info("初始化仿真环境和云端资源...")
            initializer.initialize_simulation_environment("world_file_path")  # TODO: 替换为实际的世界文件路径
            initializer.initialize_cloud_resources()
            self.logger.info("仿真环境和云端资源初始化完成")
        except Exception as e:
            self.logger.error(f"仿真环境或云端资源初始化失败: {e}")
            return

        # 初始化可执行任务队列
        for task in self.subtasks:
            depid = task.depid
            if not depid or all(self.dependency_status.get(dep, False) for dep in depid):
                self.executable_tasks.put(task)
                self.logger.info(f"任务 {task.id} 已添加到可执行队列")

        while True:  # FIXME: ******************这里的死循环可能会导致线程一直占用资源
            while not self.executable_tasks.empty():
                # 获取可执行任务
                task = self.executable_tasks.get()

                try:
                    self.logger.info(f"开始执行任务 {task.id}")
                    # 启动无人机并发布任务到队列
                    self.task_start(task)
                    self.send_taskscript(task)
                except Exception as e:
                    self.logger.error(f"任务 {task.id} 执行过程中发生未知错误: {str(e)}")
                    self.manager_process.terminate()  # 终止进程

    def run_distributed(self):
        """
        分布式执行中，要发送的一个是python代码，一个是子任务
        每台无人机需要分别保存python代码和子任务描述
        """
        self.logger.info("分布式任务调度器启动")

        # 启动事件循环
        self.start_event_loop()
        
        # 使用调度器ID作为节点ID
        scheduler_node_port = 9000  # 为调度器节点设置一个基准端口
        
        # 使用run_coroutine_threadsafe执行异步操作
        future = asyncio.run_coroutine_threadsafe(
            self._setup_p2p_node(self.id, scheduler_node_port), 
            self.event_loop
        )
        # 等待P2P节点设置完成
        self.p2p_node = future.result()
        self.logger.info(f"调度器 {self.id} 的P2P节点已启动，端口: {scheduler_node_port}")
        
        # 启动连接维护器
        self.connection_maintainer_task = asyncio.run_coroutine_threadsafe(
            self.connection_maintainer(), 
            self.event_loop
        )
        self.logger.info("已启动连接维护器任务")

        # 启动感知器检查线程
        self.task_perceptor = TaskPerceptor(self.id, self)  # 创建TaskPerceptor实例并保存引用
        threading.Thread(target=self.task_perceptor.run, daemon=True).start()  # 启动线程
        self.logger.info("任务感知器线程已启动")

        # 初始化仿真环境和云端资源
        initializer = TaskInitializer(self.id, self.devices, [])
        try:
            self.logger.info("初始化仿真环境和云端资源...")
            initializer.initialize_simulation_environment("world_file_path")  # TODO: 替换为实际的世界文件路径
            initializer.initialize_cloud_resources()
            self.logger.info("仿真环境和云端资源初始化完成")
        except Exception as e:
            self.logger.error(f"仿真环境或云端资源初始化失败: {e}")
            return

        # 分发子任务和脚本
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
        分布式使用到的方法
        分布式启动 DroneManager 并管理线程
        """
        monitor = DroneMonitor(self.id, device)
        perceptor = DronePerceptor(self.id, device, task, monitor)
        executor = DroneExecutor(self.id, device, self.devices, task, monitor, perceptor)
        executor.dis_task_list = subtask_dict[device["drone"]]
        executor.dis_script_list = script_dict[device["drone"]]

        drone_manager = DroneManager(device, task, executor, perceptor, monitor)
        drone_manager.start_threads()

    def task_start(self, task):
        """
        集中式使用到的方法
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
        集中式使用到的方法
        启动 DroneManager 并管理线程
        """
        monitor = DroneMonitor(self.id, device)
        perceptor = DronePerceptor(self.id, device, task, monitor)
        executor = DroneExecutor(self.id, device, self.devices, task, monitor, perceptor)

        drone_manager = DroneManager(device, task, executor, perceptor, monitor)
        drone_manager.start_threads()

    def send_taskscript(self, task):
        """
        集中式使用到的方法
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
            "msg_type": "script",
            "msg_len": len(subtask_content),
            "msg_content": subtask_content,
        }
        
        time.sleep(5) # 等待5秒，确保连接建立完成
        
        drone_id = task.device["drone"]
        
        # 使用event_loop发送消息
        if self.event_loop and self.p2p_node:
            future = asyncio.run_coroutine_threadsafe(
                self.p2p_node.send_message(drone_id, message),
                self.event_loop
            )
            try:
                success = future.result(timeout=5.0)  # 给5秒超时时间
                if success:
                    self.logger.info(f"成功发送任务脚本 {task.name} 到无人机 {drone_id}")
                else:
                    self.logger.error(f"无法发送任务脚本到无人机 {drone_id}")
            except Exception as e:
                self.logger.error(f"发送任务脚本时出错: {str(e)}")
                success = False
        else:
            self.logger.error("事件循环或P2P节点未初始化")
            success = False
        
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
        
    async def connect_to_drone(self, drone_id):
        """
        连接到指定的无人机P2P节点
        
        Args:
            drone_id: 无人机ID
            
        Returns:
            bool: 连接是否成功
        """
        # 从self.devices中查找对应的无人机信息
        drone_device = None
        for device in self.devices:
            if device["drone"] == drone_id:
                drone_device = device
                break
                
        if not drone_device:
            self.logger.error(f"无人机 {drone_id} 的信息未找到")
            return False
        
        # 从device中获取IP和端口
        drone_ip = drone_device["drone_ip"]
        drone_port = drone_device["drone_port"]
        
        # 尝试连接到无人机节点
        try:
            connected = await self.p2p_node.connect(
                drone_id,
                drone_ip,
                drone_port
            )
            
            if connected:
                self.logger.info(f"成功连接到无人机 {drone_id} 节点")
                return True
            else:
                self.logger.error(f"连接到无人机 {drone_id} 节点失败")
                return False
                
        except Exception as e:
            self.logger.error(f"连接到无人机 {drone_id} 节点时出错: {str(e)}")
            return False
            
    def handle_p2p_message(self, sender_id, message):
        """
        处理从P2P网络接收到的消息
        
        Args:
            sender_id: 发送方ID
            message: 消息内容
        """
        self.logger.info(f"收到来自 {sender_id} 的消息: {message}")
        
        # 将消息放入TaskPerceptor的消息队列进行处理
        task_perceptor_message = {
            "sender_id": sender_id,
            "message": message,
            "timestamp": time.time()
        }
        
        # 检查调度器是否有关联的TaskPerceptor实例
        if hasattr(self, 'task_perceptor') and self.task_perceptor is not None:
            self.task_perceptor.process_message(task_perceptor_message)
            self.logger.info(f"已将消息转发到TaskPerceptor进行处理")
        else:
            # 如果没有TaskPerceptor，就直接在这里处理消息
            self.logger.error("没有可用的TaskPerceptor")
            
    async def connection_maintainer(self, interval=5, max_retries=3, retry_delay=2):
        """
        持续运行的连接维护器，尝试连接到所有未连接的设备
        
        Args:
            interval: 重新检查间隔(秒)
            max_retries: 每次检查时每个设备的最大重试次数
            retry_delay: 重试之间的延迟(秒)
        """
        self.logger.info("连接维护器启动，将持续尝试连接到所有配置的无人机...")
        
        while True:
            try:
                # 获取已连接的设备ID列表
                connected_ids = set(self.p2p_node.connections.keys())
                
                # 获取所有设备ID列表
                all_device_ids = {device["drone"] for device in self.devices}
                
                # 找出未连接的设备ID列表
                unconnected_ids = all_device_ids - connected_ids
                
                if unconnected_ids:
                    self.logger.info(f"存在 {len(unconnected_ids)} 个未连接的无人机，尝试连接...")
                    
                    for device in self.devices:
                        drone_id = device["drone"]
                        
                        if drone_id in unconnected_ids:
                            drone_ip = device["drone_ip"]
                            drone_port = device["drone_port"]
                            
                            for attempt in range(1, max_retries + 1):
                                try:
                                    self.logger.info(f"尝试连接到无人机 {drone_id}({drone_ip}:{drone_port}) - 第 {attempt}/{max_retries} 次尝试")
                                    
                                    connected = await self.p2p_node.connect(
                                        drone_id,
                                        drone_ip,
                                        drone_port
                                    )
                                    
                                    if connected:
                                        self.logger.info(f"成功连接到无人机 {drone_id}")
                                        break
                                    else:
                                        self.logger.warning(f"连接到无人机 {drone_id} 失败")
                                        if attempt < max_retries:
                                            await asyncio.sleep(retry_delay)
                                
                                except Exception as e:
                                    self.logger.error(f"连接到无人机 {drone_id} 时出错: {str(e)}")
                                    if attempt < max_retries:
                                        await asyncio.sleep(retry_delay)
                else:
                    self.logger.debug("所有无人机都已连接")
                
                # 等待下一次检查
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                self.logger.info("连接维护器任务被取消")
                break
            except Exception as e:
                self.logger.error(f"连接维护器遇到未处理的异常: {str(e)}")
                await asyncio.sleep(interval)  # 出现异常后仍然继续运行
    
    async def _setup_p2p_node(self, node_id, port):
        """
        设置P2P节点
        
        Args: 默认ip为localhost
            node_id: 节点ID
            port: 端口号
        """
        p2p_node = P2PNode(node_id, port=port)
        p2p_node.add_message_handler(self.handle_p2p_message)
        await p2p_node.start_server()
        return p2p_node

    def close_p2p_node(self):
        """
        关闭P2P节点和事件循环
        """
        if self.p2p_node and self.event_loop:
            # 取消连接维护器任务
            if self.connection_maintainer_task:
                self.connection_maintainer_task.cancel()
                self.logger.info("已取消连接维护器任务")
            
            # 关闭P2P节点
            future = asyncio.run_coroutine_threadsafe(
                self.p2p_node.stop_server(),
                self.event_loop
            )
            try:
                future.result(timeout=5.0)  # 给5秒超时时间
                self.logger.info(f"调度器 {self.id} 的P2P节点已关闭")
            except Exception as e:
                self.logger.error(f"关闭P2P节点时出错: {str(e)}")
            
            # 停止事件循环
            if self.event_loop:
                self.event_loop.call_soon_threadsafe(self.event_loop.stop)
                if self.loop_thread and self.loop_thread.is_alive():
                    self.loop_thread.join(timeout=5.0)
                    self.logger.info("事件循环线程已停止")

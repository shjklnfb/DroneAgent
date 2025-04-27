import threading
from drone.drone_executor import DroneExecutor
from drone.drone_perceptor import DronePerceptor
from drone.drone_monitor import DroneMonitor
from drone.drone_manager import DroneManager
from queue import Queue
from collections import defaultdict
import os
import asyncio
from utils.log_configurator import setup_task_logger
import time
from task.task_perceptor import TaskPerceptor  # 添加导入
from multiprocessing import Process, Manager  # 添加导入
from communication.p2p_node import P2PNode  # 添加导入
from api.emergency_api import EmergencyAPI

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
        self.task_completed = defaultdict(bool)  # 记录子任务是否完成
        self.logger = setup_task_logger(self.id) # 日志记录器
        self.p2p_node = None  # P2P通信节点
        self.event_loop = None  # 事件循环
        self.loop_thread = None  # 事件循环线程
        self.task_perceptor = None  # 任务感知器实例
        self.manager_processes = {}  # 存储所有启动的DroneManager进程

        
        # 启动突发任务API服务器
        emergency_api = EmergencyAPI(self)
        emergency_api.start()

    def update_dependencies(self, task_id):
        """
        更新任务依赖关系
        当任务感知器检测到任务完成时，会调用这个方法
        """
        self.logger.info(f"更新任务 {task_id} 相关的依赖关系")
        self.dependency_status[task_id] = True
        self.task_completed[task_id] = True  # 标记任务已完成

        for task in self.subtasks:
            if task.depid and task_id in task.depid:
                if all(self.dependency_status.get(dep, False) for dep in task.depid) and \
                   not self.task_completed.get(task.id, False) and \
                   not self.executable_tasks.queue.count(task):
                    self.executable_tasks.put(task)
                    self.task_completed[task.id] = True  # 标记任务已加入队列
                    self.logger.info(f"任务 {task.id} 现在可执行")

    def handle_emergency(self, emergency_info):
        """
        处理突发情况，重新规划或者是给无人机下发新的任务
        """
        self.logger.warning(f"准备处理突发: {emergency_info}")
        
        # 解析突发情况信息
        drone_id = emergency_info.get("drone_id")
        priority = emergency_info.get("priority", 1)  # 默认优先级为1
        restore = emergency_info.get("restore", True)  # 默认完成后恢复原任务
        subtask = emergency_info.get("subtask")
        code = emergency_info.get("code", "")
        
        if not drone_id:
            self.logger.error("缺少目标无人机ID，无法发送突发任务")
            return False
        
        # 构建中断消息
        interrupt_message = {
            "msg_type": "interrupt",
            "msg_len": len(str(code)),
            "msg_content": {
                "priority": priority,
                "restore": restore,
                "subtask": subtask,
                "code": code
            }
        }
        
        # 使用event_loop发送消息
        if self.event_loop and self.p2p_node:
            future = asyncio.run_coroutine_threadsafe(
                self.p2p_node.send_message(drone_id, interrupt_message),
                self.event_loop
            )
            try:
                success = future.result(timeout=5.0)  # 给5秒超时时间
                if success:
                    self.logger.info(f"成功发送突发任务(优先级:{priority})到无人机 {drone_id}")
                else:
                    self.logger.error(f"无法发送突发任务到无人机 {drone_id}")
            except Exception as e:
                self.logger.error(f"发送突发任务时出错: {str(e)}")
                success = False
            return success
        else:
            self.logger.error("事件循环或P2P节点未初始化，无法发送突发任务")
            return False

    def send_interrupt_task(self, drone_id, priority, restore, subtask, code):
        """
        发送中断任务到指定无人机
        
        Args:
            drone_id: 目标无人机ID
            priority: 中断任务的优先级
            restore: 是否在完成后恢复原任务
            subtask: 子任务对象
            code: 要执行的脚本代码
            
        Returns:
            bool: 是否成功发送中断任务
        """
        self.logger.info(f"准备向无人机 {drone_id} 发送优先级为 {priority} 的中断任务")
        
        # 构建中断消息
        interrupt_message = {
            "msg_type": "interrupt",
            "msg_len": len(str(code)),
            "msg_content": {
                "priority": priority,
                "restore": restore,
                "subtask": subtask,
                "code": code
            }
        }
        
        # 使用event_loop发送消息
        if self.event_loop and self.p2p_node:
            # 确保与目标无人机有连接
            if drone_id not in self.p2p_node.connections:
                self.logger.warning(f"未连接到无人机 {drone_id}，尝试建立连接")
                for device in self.devices:
                    if device["drone"] == drone_id:
                        self.p2p_node.add_node(drone_id, device["drone_ip"], device["drone_port"])
                        time.sleep(2)  # 给连接一点建立的时间
                        break
            
            future = asyncio.run_coroutine_threadsafe(
                self.p2p_node.send_message(drone_id, interrupt_message),
                self.event_loop
            )
            try:
                success = future.result(timeout=5.0)  # 给5秒超时时间
                if success:
                    self.logger.info(f"成功发送中断任务(优先级:{priority})到无人机 {drone_id}")
                else:
                    self.logger.error(f"无法发送中断任务到无人机 {drone_id}")
            except Exception as e:
                self.logger.error(f"发送中断任务时出错: {str(e)}")
                success = False
            return success
        else:
            self.logger.error("事件循环或P2P节点未初始化，无法发送中断任务")
            return False

    def start_event_loop(self):
        """
        在后台线程中启动事件循环，用于异步函数的调用
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
        """
        集中式启动方法
        """
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
        
        # 添加所有无人机节点到P2P节点的连接列表
        for device in self.devices:
            drone_id = device["drone"]
            drone_ip = device["drone_ip"]
            drone_port = device["drone_port"]
            self.p2p_node.add_node(drone_id, drone_ip, drone_port)
            self.logger.info(f"已添加无人机 {drone_id} 到连接列表: {drone_ip}:{drone_port}")


        # 启动感知器检查线程
        self.task_perceptor = TaskPerceptor(self.id, self)  # 创建TaskPerceptor实例并保存引用
        threading.Thread(target=self.task_perceptor.run, daemon=True).start()  # 启动线程
        self.logger.info("任务感知器线程已启动")

        # 初始化可执行任务队列
        for task in self.subtasks:
            depid = task.depid
            if not depid or all(self.dependency_status.get(dep, False) for dep in depid):
                if not self.task_completed.get(task.id, False):  # 只有未完成的任务才添加
                    self.executable_tasks.put(task)
                    self.task_completed[task.id] = True  # 标记任务已加入队列
                    self.logger.info(f"任务 {task.id} 已添加到可执行队列")

        # FIXME: 这里是根据task启动的，可能有多个task在同一台无人机上
        # 提前启动所有的无人机控制程序
        for task in self.subtasks:
            self.task_start(task)

        time.sleep(3)

        while True:  # FIXME: ******************这里的死循环可能会导致线程一直占用资源
            while not self.executable_tasks.empty():
                # 获取可执行任务
                task = self.executable_tasks.get()

                try:
                    self.logger.info(f"开始执行任务 {task.id}")
                    
                    # 发布任务到队列
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
            self._setup_p2p_node("scheduler", scheduler_node_port), 
            self.event_loop
        )
        # 等待P2P节点设置完成
        self.p2p_node = future.result()
        self.logger.info(f"调度器 scheduler 的P2P节点已启动，端口: {scheduler_node_port}")
        
        # 添加所有无人机节点到P2P节点的连接列表
        for device in self.devices:
            drone_id = device["drone"]
            drone_ip = device["drone_ip"]
            drone_port = device["drone_port"]
            self.p2p_node.add_node(drone_id, drone_ip, drone_port)
            self.logger.info(f"已添加无人机 {drone_id} 到连接列表: {drone_ip}:{drone_port}")


        # 启动感知器检查线程
        self.task_perceptor = TaskPerceptor(self.id, self)  # 创建TaskPerceptor实例并保存引用
        threading.Thread(target=self.task_perceptor.run, daemon=True).start()  # 启动线程
        self.logger.info("任务感知器线程已启动")


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
            self.manager_processes[drone] = drone_manager_process  # 将进程添加到进程字典中

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
        drone_id = task.device['drone']
        self.manager_processes[drone_id] = drone_manager_process  # 将进程添加到进程字典中
        drone_manager_process.start()

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

    def terminate_all_processes(self):
        """
        终止所有DroneManager进程
        """
        for drone_id, process in self.manager_processes.items():
            if process.is_alive():
                process.terminate()
                self.logger.info(f"已终止无人机 {drone_id} 的DroneManager进程")
        
        self.manager_processes.clear()
        self.logger.info("所有DroneManager进程已终止")
        
    def clear_task(self):
        """
        清空当前任务，终止所有进程并重置调度器状态
        """
        self.logger.info("开始清空当前任务...")
        
        # 终止所有DroneManager进程
        self.terminate_all_processes()
        
        # 关闭P2P节点和事件循环
        self.close_p2p_node()
        
        # 重置任务队列
        while not self.executable_tasks.empty():
            self.executable_tasks.get()
        while not self.emergency_tasks.empty():
            self.emergency_tasks.get()
            
        # 重置状态记录
        self.dependency_status = defaultdict(bool)
        self.task_completed = defaultdict(bool)
        
        # 关闭任务感知器
        self.task_perceptor.finish = True  # 设置感知器停止标志
        # 重置任务感知器
        self.task_perceptor = None
        
        # 重置通信相关属性
        self.p2p_node = None
        self.event_loop = None
        self.loop_thread = None
        
        # 清空进程记录
        self.manager_processes = {}
        
        self.logger.info("任务已清空，调度器状态已重置")

        # # 清空后应该自动重新规划任务，之后按顺序运行
        # from task.task_planner import TaskPlanner
        # from task.task_initializer import TaskInitializer
        # from task.task_translator import TaskTranslator
        # task_planner = TaskPlanner("id","任务")
        # task_planner.run()
        # taskInitializer = TaskInitializer("id", ["设备"], ["服务"])
        # taskInitializer.run()
        # taskTranslator = TaskTranslator("id", ["子任务"])
        # taskTranslator.run()
        # self.logger.info("任务已重新规划，调度器状态已重置")

        # # 重新运行集中式调度器或者分布式
        # self.run_centralized()  
        # # self.run_distributed()

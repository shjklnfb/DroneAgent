import threading
import json
import traceback
import time
import asyncio
from queue import Queue, PriorityQueue
from communication.p2p_node import P2PNode  # 添加导入
from utils.log_configurator import setup_drone_logger
import os
import json

'''
无人机执行器
独立运行的线程，负责接收并读取任务调度器下发给自己的子任务（包括：python代码和子任务描述）
只需要执行python脚本即可
'''

class DroneExecutor(threading.Thread):

    def __init__(self, id, device, devices, task, monitor, perceptor):
        super().__init__()
        self.id = id  # id
        self.device = device  # 无人机型号、ip、port
        self.devices = devices  # 所有无人机的列表
        self.task = task      # 子任务
        self.monitor = monitor  # 监控器实例，用于获取无人机状态等信息
        self.perceptor = perceptor  # 感知器实例，用于获取无人机感知信息
        self.stop_event = threading.Event()
        self.dis_task_list = []  # 分布式执行中，用于保存脚本的列表
        self.dis_script_list = []  # 分布式执行中，用于保存脚本的字典列表
        self.message_queue = Queue()  # 用于存储接收到的消息
        self.cur_script = None  # 当前执行的脚本
        self.waiting_script = None  # 用于存储待执行的脚本

        self.p2p_node = None  # P2P通信节点
        self.p2p_event_loop = None  # P2P节点的事件循环

        self.task_stack = []  # 任务栈，用于存储被中断的任务信息
        self.current_priority = 0  # 当前任务的优先级，普通任务为0
        self.executing = False  # 是否有任务正在执行
        
        # 添加优先级队列，用于存储待执行的中断任务
        self.pending_interrupts = PriorityQueue()

        self.logger = setup_drone_logger(id, device["drone"])

    def record_task(self):
        """
        记录当前任务和分布式任务列表到文件。
        """
        try:
            # 确保日志文件夹存在
            log_dir = os.path.join("log", str(self.id))
            os.makedirs(log_dir, exist_ok=True)

            # 定义文件路径
            file_path = os.path.join(log_dir, "cur_task.txt")

            # 准备要写入的数据
            data = {}
            if self.task:
                data["task"] = self.task.to_dict()  # 调用 to_dict 方法
            if self.dis_task_list:
                data["dis_task_list"] = [task.to_dict() for task in self.dis_task_list]  # 列表推导式中调用 to_dict

            # 将数据写入文件
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

            self.logger.info(f"任务数据已成功写入到 {file_path}")
        except Exception as e:
            self.logger.error(f"记录任务数据时出错: {str(e)}")
            traceback.print_exc()

    def execute_task(self, message):
        """
        执行接收到的任务代码。
        """
        try:
            # 解析消息内容
            code = message
            self.cur_script = code  # 保存当前脚本
            if not code:
                print("接收到的消息中没有任务代码")
                return

            # 在执行之前，确保p2p_node对象能够访问到事件循环
            if self.p2p_node and not hasattr(self.p2p_node, 'event_loop'):
                self.p2p_node.event_loop = self.p2p_event_loop

            # 标记当前有任务正在执行
            self.executing = True

            global_namespace = {
                'id': self.id,
                'drone': self.device["drone"],
                'dronemonitor': self.monitor,
                'p2p_node': self.p2p_node,  
                'dynamic_data': self.perceptor.dynamic_data,
                'interrupt_flag': self.perceptor.interrupt_flag,  # 传递包装类对象
                '__builtins__': __builtins__,
            }
            exec(code, global_namespace)
            if self.task and self.task.name in global_namespace:
                result = global_namespace[self.task.name](
                    self.id, self.device["drone"], self.monitor, self.p2p_node, self.perceptor.dynamic_data,
                    self.perceptor.interrupt_flag  # 传递包装类对象
                )
                print(f"函数执行结果: {result}")
            elif "emergency_task" in global_namespace:
                result = global_namespace["emergency_task"](
                    self.id, self.device["drone"], self.monitor, self.p2p_node, self.perceptor.dynamic_data,
                    self.perceptor.interrupt_flag  # 传递包装类对象
                )
                print(f"紧急任务执行结果: {result}")
            else:
                print("集中式执行器未找到函数")
            
            # 执行完毕，标记为未执行状态
            self.executing = False
            
            # 任务完成后，先检查是否有待执行的中断任务
            if not self.pending_interrupts.empty():
                self.logger.info("检测到待执行的中断任务，优先处理")
                self.process_pending_interrupt()
                return
                
            # 如果没有待执行的中断任务，再检查是否需要恢复被中断的任务
            self.restore_interrupted_task()
        except Exception as e:
            print(f"Error executing received code: {str(e)}")
            traceback.print_exc()
            # 发生错误，也尝试恢复任务
            self.executing = False
            
            # 先检查是否有待执行的中断任务
            if not self.pending_interrupts.empty():
                self.logger.info("检测到待执行的中断任务，优先处理")
                self.process_pending_interrupt()
                return
                
            # 再检查是否需要恢复被中断的任务
            self.restore_interrupted_task()

    def handle_interrupt(self, priority, restore, subtask, code):
        """
        处理中断任务
        
        Args:
            priority: 中断任务的优先级
            restore: 是否在完成后恢复原任务
            subtask: 子任务对象
            code: 要执行的脚本代码
        
        Returns:
            bool: 是否成功处理中断
        """
        self.logger.info(f"收到优先级为{priority}的中断任务，当前任务优先级为{self.current_priority}")
        
        # 如果没有任务正在执行，直接执行中断任务
        if not self.executing:
            self.current_priority = priority
            self.task = subtask
            self.cur_script = code
            self.execute_task(code)
            self.logger.info(f"无任务执行中，直接执行中断任务，优先级: {priority}")
            return True
        
        # 如果有任务正在执行，根据优先级判断处理方式
        if priority > self.current_priority:
            # 优先级更高，中断当前任务
            if restore:
                # 需要保存当前任务到栈中以便后续恢复
                interrupted_task = {
                    'script': self.cur_script,
                    'priority': self.current_priority,
                    'task': self.task
                }
                self.task_stack.append(interrupted_task)
                self.logger.info(f"当前任务已保存到栈中以便后续恢复")
            
            # 设置新任务的优先级
            self.current_priority = priority
            
            # 设置中断标志，终止当前执行的任务
            self.perceptor.interrupt_flag.set()  # 使用set()方法设置中断标志
            time.sleep(1)  # 给当前任务一点时间来响应中断标志
            self.perceptor.interrupt_flag.clear()  # 使用clear()方法清除中断标志
            
            # 更新子任务对象并执行新任务
            self.task = subtask
            self.cur_script = code
            self.execute_task(code)
            self.logger.info(f"高优先级中断任务已开始执行，优先级: {priority}")
            return True
        else:
            # 优先级不够高，将任务添加到待执行队列
            interrupt_task = {
                'priority': priority,
                'restore': restore,
                'subtask': subtask,
                'code': code
            }
            # 使用负优先级作为队列排序依据(PriorityQueue是最小优先)
            self.pending_interrupts.put((-priority, time.time(), interrupt_task))
            self.logger.info(f"中断任务优先级不足，已添加到待执行队列，优先级: {priority}")
            return True  # 任务已接受，虽然暂时未执行

    def process_pending_interrupt(self):
        """
        从待执行队列中获取并执行最高优先级的中断任务
        """
        if self.pending_interrupts.empty():
            return False
            
        # 获取队列中优先级最高的中断任务
        _, _, interrupt_task = self.pending_interrupts.get()
        self.logger.info(f"处理队列中的中断任务，优先级: {interrupt_task['priority']}")
        
        # 执行该中断任务
        priority = interrupt_task['priority']
        restore = interrupt_task['restore']
        subtask = interrupt_task['subtask']
        code = interrupt_task['code']
        
        # 设置任务属性
        self.current_priority = priority
        self.task = subtask
        self.cur_script = code
        
        # 执行中断任务
        self.logger.info(f"开始执行队列中的中断任务，优先级: {priority}")
        self.execute_task(code)
        return True

    def restore_interrupted_task(self):
        """
        尝试恢复被中断的任务
        """
        # 如果队列中还有待执行的中断任务，先处理它们
        if not self.pending_interrupts.empty():
            self.process_pending_interrupt()
            return True
            
        # 如果任务栈为空，没有需要恢复的任务
        if not self.task_stack:
            self.logger.info("任务栈为空，没有需要恢复的任务")
            self.current_priority = 0  # 重置为普通任务优先级
            return False
        
        # 从栈顶弹出最近被中断的任务
        interrupted_task = self.task_stack.pop()
        
        self.logger.info(f"从任务栈中恢复任务，优先级: {interrupted_task['priority']}")
        
        # 恢复任务属性
        self.task = interrupted_task['task']
        self.current_priority = interrupted_task['priority']
        self.cur_script = interrupted_task['script']
        
        # 执行恢复的任务
        self.execute_task(self.cur_script)
        return True

    def run_cen(self):
        """
        集中式模式下的线程运行方法
        """
        self.record_task()  # 记录当前任务
        self.logger.info("集中式执行器等待P2P网络就绪")
        
        # P2P网络已由DroneManager启动，此处无需再启动
        # 等待DroneManager完成P2P节点的初始化
        while self.p2p_node is None or self.p2p_event_loop is None:
            self.logger.info("等待P2P节点初始化...")
            time.sleep(1)
            
        self.logger.info("P2P网络已准备就绪，等待执行任务")
        
        # 主循环：检查并执行waiting_script
        while not self.stop_event.is_set():
            if self.waiting_script:
                script = self.waiting_script
                self.waiting_script = None  # 清空待执行的脚本
                self.logger.info("从waiting_script检测到新脚本，准备执行")
                self.execute_task(script)
            time.sleep(1)  # 每秒检查一次是否有新的脚本需要执行

    def handle_p2p_message(self, sender_id, message):
        """
        处理从P2P网络接收到的消息
        
        Args:
            sender_id: 发送方ID
            message: 消息内容
        """
        self.logger.info(f"收到来自 {sender_id} 的消息")
        
        # 将消息放入DronePerceptor的消息队列进行处理
        perceptor_message = {
            "sender_id": sender_id,
            "message": message,
            "timestamp": time.time()
        }
        
        # 检查感知器是否已初始化消息队列
        if self.perceptor and hasattr(self.perceptor, 'message_queue') and self.perceptor.message_queue is not None:
            self.perceptor.process_message(perceptor_message)
            self.logger.info(f"已将消息转发到DronePerceptor进行处理")
        else:
            self.logger.error(f"DronePerceptor消息队列未初始化")

    def close_p2p_node(self):
        """
        关闭P2P节点
        注意：实际关闭工作已移至DroneManager，此方法暂时保留
        """
        self.logger.info(f"P2P节点关闭请求由DroneManager处理")
    
    def run(self):
        """
        启动分布式执行器
        需要同时接受子任务描述和每个子任务的python代码
        从子任务描述中检查依赖关系，得到满足的可以执行python代码
        无人机之间需要建立连接，互相发送消息
        无人机感知器需要检查消息，更新依赖关系，传递数据
        """
        self.record_task()  # 记录当前任务和分布式任务列表到文件
        
        # P2P网络已由DroneManager启动，此处无需再启动
        # 等待DroneManager完成P2P节点的初始化
        while self.p2p_node is None or self.p2p_event_loop is None:
            self.logger.info("等待P2P节点初始化...")
            time.sleep(1)
        
        self.logger.info("P2P网络已就绪，开始处理任务")
        
        # 主线程处理任务
        while not self.stop_event.is_set():
            for task in self.dis_task_list[:]:  # 使用列表的副本进行迭代，避免修改迭代中的集合
                depid = task.depid
                task_id = task.id
                if not depid or all(dep in self.perceptor.dis_finished_list for dep in depid):
                    # 找到对应的脚本
                    self.task = task
                    self.perceptor.task = task
                    script = next((script for script in self.dis_script_list if script.get("task_id") == task_id), None)
                    if script:
                        self.cur_script = script.get("script")
                        # 从列表中移除当前任务和脚本
                        self.dis_task_list.remove(task)
                        self.dis_script_list.remove(script)
                        try:
                            self.logger.info(f"开始执行任务 {task_id}")
                            # 执行脚本
                            global_namespace = {
                                'id': self.id,
                                'drone': self.device["drone"],
                                'dronemonitor': self.monitor,
                                'p2p_node': self.p2p_node,
                                'dynamic_data': self.perceptor.dynamic_data,
                                'interrupt_flag': self.perceptor.interrupt_flag,  # 传递包装类对象
                                '__builtins__': __builtins__
                            }
                            exec(script.get("script", ""), global_namespace)
                            if task.name in global_namespace:
                                result = global_namespace[task.name](
                                    self.id, self.device["drone"], self.monitor, self.p2p_node, 
                                    self.perceptor.dynamic_data, self.perceptor.interrupt_flag  # 传递包装类对象
                                )
                                self.logger.info(f"任务 {task_id} 执行结果: {result}")
                                self.perceptor.dis_finished_list.append(task_id)
                            else:
                                self.logger.error(f"找不到任务函数 {task.name}")
                        except Exception as e:
                            self.logger.error(f"执行任务 {task_id} 时出错: {str(e)}")
                            traceback.print_exc()
            # 防止过高的CPU占用率
            time.sleep(2)

    def clear_executor(self):
        """
        清空当前执行器的所有属性和状态
        """
        self.logger.info(f"正在清空执行器 {self.device['drone']} 的所有属性和状态...")
        
        # 设置停止事件，通知所有线程停止
        self.stop_event.set()

        # 清空消息队列
        while not self.message_queue.empty():
            self.message_queue.get()
        
        # 清空分布式任务和脚本列表
        self.dis_task_list.clear()
        self.dis_script_list.clear()
        self.task = None

        # 重置当前脚本
        self.cur_script = None
        
        # 清空任务栈
        self.task_stack.clear()
        
        # 重置优先级
        self.current_priority = 0
        
        # 重置执行状态
        self.executing = False
        
        # 清空优先级队列
        while not self.pending_interrupts.empty():
            self.pending_interrupts.get()
            
        # 重置停止事件
        self.stop_event.clear()
        
        self.logger.info(f"执行器 {self.device['drone']} 的属性和状态已清空")






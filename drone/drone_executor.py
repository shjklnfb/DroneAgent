import threading
import json
import traceback
import time
import asyncio
import ctypes
import inspect
import signal
from queue import Queue, PriorityQueue
from communication.p2p_node import P2PNode
from utils.log_configurator import setup_drone_logger
import os
import json

'''
无人机执行器
独立运行的线程，负责接收并读取任务调度器下发给自己的子任务（包括：python代码和子任务描述）
只需要执行python脚本即可
'''

class ScriptThread(threading.Thread):
    """可以被强制终止的脚本执行线程，改进版"""
    
    def __init__(self, target, args=(), kwargs={}):
        super(ScriptThread, self).__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.daemon = True  # 设为守护线程
        self.result = None
        self.exception = None
        self._stop_requested = False
        self._thread_id = None
        
    def run(self):
        """执行目标函数并捕获结果或异常"""
        # 存储当前线程ID
        self._thread_id = threading.get_ident()
        try:
            self.result = self.target(*self.args, **self.kwargs)
        except SystemExit:
            # 捕获 SystemExit 异常，这是我们用来终止线程的信号
            # 可以进行一些后处理
            print(f"通过 SystemExit 成功终止线程")
            self._stop_requested = True
        except Exception as e:
            self.exception = e
            traceback.print_exc()
    
    def _async_raise(self, thread_id, exception_class):
        """向线程注入异常"""
        # 确保线程ID有效
        if thread_id not in threading._active:
            return False
            
        # 获取线程对象
        thread = threading._active.get(thread_id)
        if not thread:
            return False
            
        # 注入异常到线程
        ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(thread_id),
            ctypes.py_object(exception_class)
        )
        
        # 检查结果
        if ret == 0:
            return False  # 线程ID无效
        elif ret > 1:
            # 如果返回值大于1，可能有问题，尝试恢复
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_long(thread_id),
                ctypes.py_object(None)
            )
            return False
        return True  # 成功注入异常
    
    def get_id(self):
        """获取线程ID"""
        if self._thread_id:
            return self._thread_id
            
        for thread_id, thread in threading._active.items():
            if thread is self:
                self._thread_id = thread_id
                return thread_id
        return None
    
    def terminate(self, timeout=2.0):
        """
        强制终止线程，使用多种策略确保终止成功
        
        Args:
            timeout: 等待线程终止的超时时间(秒)
            
        Returns:
            bool: 终止是否成功
        """
        if not self.is_alive():
            return True
            
        # 标记终止请求
        self._stop_requested = True
        
        # 下面是三种方式：
        # 注入SystemExit异常
        thread_id = self.get_id()
        if thread_id and self._async_raise(thread_id, SystemExit):
            # 给线程一点时间来退出
            start_time = time.time()
            while self.is_alive() and time.time() - start_time < timeout:
                time.sleep(0.1)
                
            if not self.is_alive():
                return True
        
        # 尝试使用KeyboardInterrupt
        # if thread_id:
        #     self._async_raise(thread_id, KeyboardInterrupt)
        #     # 再次等待一点时间
        #     time.sleep(0.5)
        #     if not self.is_alive():
        #         return True
        
        # 尝试使用BaseException (几乎无法捕获的异常)
        # if thread_id:
        #     self._async_raise(thread_id, BaseException)
        #     time.sleep(0.5)
        #     return not self.is_alive()
            
        return False

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
        self.script_thread = None  # 用于存储执行脚本的线程
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

    def _execute_script(self, code, namespace):
        """在线程内执行脚本代码的方法"""
        try:
            # 执行脚本代码
            exec(code, namespace)
            
            # 查找并执行任务函数
            if self.task and self.task.name in namespace:
                result = namespace[self.task.name](
                    self.id, self.device["drone"], self.monitor, self.p2p_node, 
                    self.perceptor.dynamic_data
                )
                self.logger.info(f"任务 {self.task.name} 执行结果: {result}")
                # 将任务标记为完成(只有分布式有用)
                if hasattr(self.perceptor, "dis_finished_list") and self.task:
                    self.perceptor.dis_finished_list.append(self.task.id)
                return result
            elif "emergency_task" in namespace:
                result = namespace["emergency_task"](
                    self.id, self.device["drone"], self.monitor, self.p2p_node, 
                    self.perceptor.dynamic_data
                )
                self.logger.info(f"紧急任务执行结果: {result}")
                return result
            else:
                self.logger.warning("未找到可执行函数")
                return None
        except Exception as e:
            self.logger.error(f"执行脚本时出错: {str(e)}")
            traceback.print_exc()
            return None

    def execute_task(self, message):
        """
        执行接收到的任务代码。
        """
        
        # # 终止正在运行的线程
        # if self.script_thread and self.script_thread.is_alive():
        #     self.logger.info("终止当前正在执行的脚本线程")
        #     success = self.script_thread.terminate(timeout=3.0)  # 增加超时时间
        #     self.logger.info(f"线程终止{'成功' if success else '失败'}")
        #     if not success:
        #         self.logger.warning("线程终止失败，强制继续执行新任务")
        #     time.sleep(1.0)  # 给线程更多时间完成终止
        
        # 解析消息内容
        code = message
        self.cur_script = code  # 保存当前脚本
        if not code:
            self.logger.warning("接收到的消息中没有任务代码")
            return

        # 在执行之前，确保p2p_node对象能够访问到事件循环
        if self.p2p_node and not hasattr(self.p2p_node, 'event_loop'):
            self.p2p_node.event_loop = self.p2p_event_loop

        # 标记当前有任务正在执行
        self.executing = True

        # 准备全局命名空间
        global_namespace = {
            'id': self.id,
            'drone': self.device["drone"],
            'dronemonitor': self.monitor,
            'p2p_node': self.p2p_node,  
            'dynamic_data': self.perceptor.dynamic_data,
            '__builtins__': __builtins__,
        }
        
        # 创建并启动执行线程
        self.script_thread = ScriptThread(
            target=self._execute_script,
            args=(code, global_namespace)
        )
        self.script_thread.start()
        self.logger.info(f"已启动脚本执行线程")
        
        # 等待线程完成
        self.script_thread.join() # FIXME: *************************************************
        
        # 检查执行结果
        if self.script_thread.exception:
            self.logger.error(f"脚本执行异常: {self.script_thread.exception}")
        elif self.script_thread.result is not None:
            self.logger.info(f"脚本执行结果: {self.script_thread.result}")
        
        # 执行完毕，标记为未执行状态
        self.executing = False
        
        # 任务完成后，先检查是否有待执行的中断任务
        if not self.pending_interrupts.empty():
            self.logger.info("检测到待执行的中断任务，优先处理")
            self.process_pending_interrupt()
            return
            
        # 如果没有待执行的中断任务，再检查是否需要恢复被中断的任务
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
            
            # 强制终止当前执行的线程，尝试多次确保成功终止
            if self.script_thread and self.script_thread.is_alive():
                self.logger.info("强制终止当前执行的脚本线程")
                for attempt in range(3):  # 尝试最多3次终止
                    success = self.script_thread.terminate(timeout=1.0)
                    if success:
                        self.logger.info(f"线程终止成功 (尝试 {attempt+1})")
                        break
                    self.logger.warning(f"线程终止尝试 {attempt+1} 失败，再次尝试...")
                    time.sleep(0.5)
                
                # 即使终止失败，仍然继续执行新任务
                time.sleep(1.0)  # 给线程一点时间完成终止
                
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

    def run(self):
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
    
    def run_dis(self):
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
                        self.execute_task(self.cur_script)
            # 防止过高的CPU占用率
            time.sleep(2)

    def clear_executor(self):
        """
        清空当前执行器的所有属性和状态
        """
        self.logger.info(f"正在清空执行器 {self.device['drone']} 的所有属性和状态...")
        
        # 设置停止事件，通知所有线程停止
        self.stop_event.set()
        
        # 强制终止当前执行的线程
        if self.script_thread and self.script_thread.is_alive():
            self.logger.info("终止当前执行的脚本线程")
            for attempt in range(3):  # 尝试最多3次终止
                success = self.script_thread.terminate(timeout=1.0)
                if success:
                    self.logger.info(f"线程终止成功 (尝试 {attempt+1})")
                    break
                self.logger.warning(f"线程终止尝试 {attempt+1} 失败，再次尝试...")
                time.sleep(0.5)

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






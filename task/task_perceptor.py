import asyncio
from queue import Queue
import time
from utils.log_configurator import setup_task_logger
import json
import os

"""
任务感知器
读取日志文件，检查无人机监控器数据，处理任务完成或错误的情况
"""
class TaskPerceptor:
    def __init__(self, id, scheduler):
        """
        初始化任务感知器。
        """
        self.id = id
        self.scheduler = scheduler  # 任务调度器实例
        self.finish = False
        self.finish_tasks = []
        self.message_queue = [] # 用于存储接收到的消息     
        self.logger = setup_task_logger(self.id)

    def process_message(self, yaw_message):
        """
        处理接收到的消息
        
        Args:
            yaw_message: {
            "sender_id": sender_id,
            "message": message,
            "timestamp": time.time()
            }
        message的格式要求：        
        {
            msg_type: "",
            msg_len: "",
            msg_content: "",
        }
        """
        self.logger.info(f"接收到消息: {yaw_message}")

        # 将消息记录到队列中，维护最新的50条消息
        if not hasattr(self, "message_queue"):
            self.message_queue = []

        if len(self.message_queue) >= 50:
            self.message_queue.pop(0)  # 删除队头元素

        self.message_queue.append(yaw_message)

        # 将消息写入日志文件
        log_dir = f"log/{self.id}"
        log_file = f"{log_dir}/message_scheduler.log"
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 将消息写入日志文件
        with open(log_file, "a", encoding="utf-8") as log_f:
            log_f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {json.dumps(yaw_message, ensure_ascii=False)}\n")

    def percept_message(self):
        """
        定期处理队列中的消息。
        """
        if not hasattr(self, "message_queue"):
            self.logger.warning("消息队列不存在")
            return

        for yaw_message in self.message_queue:
            self.message_queue.remove(yaw_message)  # 从队列中删除已处理的消息
            sender_id = yaw_message.get("sender_id")
            timestamp = yaw_message.get("timestamp")
            message = yaw_message.get("message")
            msg_type = message.get("msg_type")
            
            if msg_type == "task_progress":
                # 关于任务进度的消息
                progress_content = message.get("msg_content")
                try:
                    # 将字符串解析为JSON对象
                    progress_content = json.loads(progress_content)
                    
                    task = progress_content.get("task")
                    state = progress_content.get("state")
                    reason = progress_content.get("reason", "无具体原因")
                    
                    # 日志记录解析出的内容
                    self.logger.info(f"任务进度更新 - 任务: {task}, 状态: {state}, 原因: {reason}")
                    
                    if state == "error*********":  # FIXME: 无人机感知器传来的error不一定就是error
                        # 调用错误处理函数
                        self.handle_error(progress_content)
                    elif state == "finish":
                        # 调用更新依赖函数
                        if task:
                            # 提取任务编号
                            import re
                            task_number = int(re.findall(r'\d+$', task)[0])
                            self.scheduler.update_dependencies(task_number)
                    elif state == "running":
                        # 不处理
                        pass
                    else:
                        self.logger.warning(f"未知任务状态: {state}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"任务感知器解析任务进度内容时发生错误: {str(e)}")
            
            # 自定义的未知消息类型处理
            elif msg_type == "unknown":
                self.logger.warning(f"接收到自定义未知消息类型: {message}")
                # TODO: 处理未知消息类型的逻辑


    def handle_error(self, progress_content):
        """
        处理任务错误的情况
        
        Args:
            progress_content: 包含任务错误信息的字典
        """
        print("处理错误,应该需要重新规划任务")
        self.scheduler.clear_task()    # 终止所有进程


    def run(self):
        """
        运行任务感知器，持续检查无人机感知器状态。
        """
        self.logger.info("任务感知器开始运行")
        while not self.finish:
            try:
                self.percept_message()
            except Exception as e:
                self.logger.error(f"任务感知器运行时发生错误: {str(e)}")
            time.sleep(5)  # 每5秒检查一次




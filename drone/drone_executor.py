import threading
import json
import traceback
import time
import asyncio
from queue import Queue
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

        self.p2p_node = None  # P2P通信节点
        self.p2p_event_loop = None  # P2P节点的事件循环
        self.connection_maintainer_task = None  # 连接维护任务

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
            data = {
            "task": self.task,
            "dis_task_list": self.dis_task_list
            }

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
            code =message
            if not code:
                print("接收到的消息中没有任务代码")
                return

            global_namespace = {
                'id': self.id,
                'drone': self.device["drone"],
                'dronemonitor': self.monitor,
                'p2p_node': self.p2p_node,  
                'dynamic_data': self.perceptor.dynamic_data,
                '__builtins__': __builtins__,
            }
            exec(code, global_namespace)
            if self.task.name in global_namespace:
                result = global_namespace[self.task.name](
                    self.id, self.device["drone"], self.monitor, self.p2p_node, self.perceptor.dynamic_data
                )
                print(f"函数执行结果: {result}")
            else:
                print("集中式执行器未找到函数")
        except Exception as e:
            print(f"Error executing received code: {str(e)}")
            traceback.print_exc()


    def listen_distributed(self):
        """
        分布式执行的监听方法，持续监听消息队列，将任务消息放入任务队列。
        """
        consumer = self.connect_to_kafka()
        if not consumer:
            return

        try:
            print("开始监听消息队列并将消息放入任务队列...")
            for message in consumer:

                self.dis_script_list.append(message.value)  # 将消息放入队列
                if self.stop_event.is_set():
                    print("停止事件已触发，退出监听")
                    break
        finally:
            self.disconnect_from_kafka(consumer)

    def run(self):
        """
        线程运行方法，初始化客户端并监听服务器消息。
        """
        self.record_task()  # 记录当前任务和分布式任务列表到文件

        # CODE: 启动self.device的p2p节点，并尝试连接到其他无人机以及scheduler的p2p节点

        # 创建事件循环
        self.p2p_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.p2p_event_loop)
        
        # 使用无人机ID创建P2P节点
        drone_id = self.device["drone"]
        drone_port = self.device["drone_port"]
        
        self.p2p_node = P2PNode(drone_id, port=drone_port)
        
        # 添加消息处理函数
        self.p2p_node.add_message_handler(self.handle_p2p_message)
        
        try:
            # 启动P2P节点服务器
            self.p2p_event_loop.run_until_complete(self.p2p_node.start_server())
            self.logger.info(f"无人机 {drone_id} 的P2P节点已启动，端口: {drone_port}")
            
            # 启动连接维护器
            self.connection_maintainer_task = self.p2p_event_loop.create_task(self.connection_maintainer())
            self.logger.info("已启动连接维护器任务")
            
            # 运行事件循环，保持节点活跃
            try:
                self.p2p_event_loop.run_forever()
            except asyncio.CancelledError:
                self.logger.info("P2P事件循环被取消")
            finally:
                # 清理和关闭节点
                self.close_p2p_node()
                
        except Exception as e:
            self.logger.error(f"启动P2P节点时出错: {str(e)}")
            traceback.print_exc()

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

    async def connection_maintainer(self, interval=5, max_retries=3, retry_delay=2):
        """
        持续运行的连接维护器，尝试连接到调度器和其他无人机
        
        Args:
            interval: 重新检查间隔(秒)
            max_retries: 每次检查时的最大重试次数
            retry_delay: 重试之间的延迟(秒)
        """
        self.logger.info("连接维护器启动，将持续尝试连接到调度器和其他无人机...")
        
        # 调度器节点信息
        scheduler_id = "scheduler"  # 使用固定的调度器ID
        scheduler_host = "localhost"  # 本地测试使用localhost
        scheduler_port = 9000  # 使用固定的调度器端口
        
        # 当前无人机ID
        current_drone_id = self.device["drone"]
        
        while True:
            try:
                # 1. 检查并连接调度器
                connected_to_scheduler = scheduler_id in self.p2p_node.connections
                
                if not connected_to_scheduler:
                    for attempt in range(1, max_retries + 1):
                        try:
                            self.logger.info(f"尝试连接到调度器 - 第 {attempt}/{max_retries} 次尝试")
                            connected = await self.p2p_node.connect(
                                scheduler_id,
                                scheduler_host,
                                scheduler_port
                            )
                            
                            if connected:
                                self.logger.info(f"成功连接到调度器")
                                break
                            else:
                                self.logger.warning(f"连接到调度器失败")
                                if attempt < max_retries:
                                    await asyncio.sleep(retry_delay)
                        except Exception as e:
                            self.logger.error(f"连接到调度器时出错: {str(e)}")
                            if attempt < max_retries:
                                await asyncio.sleep(retry_delay)
                
                # 2. 检查并连接其他无人机
                # 获取已连接的节点ID列表
                connected_ids = set(self.p2p_node.connections.keys())
                
                # 获取所有无人机ID列表（除了自己）
                other_drone_ids = {device["drone"] for device in self.devices if device["drone"] != current_drone_id}
                
                # 找出未连接的无人机ID列表
                unconnected_drone_ids = other_drone_ids - connected_ids
                
                if unconnected_drone_ids:
                    self.logger.info(f"存在 {len(unconnected_drone_ids)} 个未连接的其他无人机，尝试连接...")
                    
                    for device in self.devices:
                        drone_id = device["drone"]
                        
                        # 跳过当前无人机和已连接的无人机
                        if drone_id == current_drone_id or drone_id not in unconnected_drone_ids:
                            continue
                        
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
                    self.logger.debug("已连接到所有其他无人机")
                
                # 等待下一次检查
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                self.logger.info("连接维护器任务被取消")
                break
            except Exception as e:
                self.logger.error(f"连接维护器遇到未处理的异常: {str(e)}")
                await asyncio.sleep(interval)  # 出现异常后仍然继续运行
                
    def close_p2p_node(self):
        """
        关闭P2P节点
        """
        # 取消连接维护器任务
        if self.connection_maintainer_task:
            self.connection_maintainer_task.cancel()
            self.logger.info("已取消连接维护器任务")
        
        # 关闭P2P节点
        if self.p2p_node and self.p2p_event_loop:
            try:
                self.p2p_event_loop.run_until_complete(self.p2p_node.stop_server())
                self.logger.info(f"无人机 {self.device['drone']} 的P2P节点已关闭")
            except Exception as e:
                self.logger.error(f"关闭P2P节点时出错: {str(e)}")
    
    def run_dis(self):
        """
        启动分布式执行器
        需要同时接受子任务描述和每个子任务的python代码
        从子任务描述中检查依赖关系，得到满足的可以执行python代码
        无人机之间需要建立连接，互相发送消息
        无人机感知器需要检查消息，更新依赖关系，传递数据
        """
        # 启动分布式监听器，将该无人机的任务和脚本加入到任务队列中
        # threading.Thread(target=self.listen_distributed, daemon=True).start()
        # 执行任务
        while True:
            for task in self.dis_task_list:
                depid = task.depid
                task_id = task.id
                if not depid or all(dep in self.perceptor.dis_finished_list for dep in depid):  # 修改为使用 self.perceptor.dis_finished_list
                    # 找到对应的脚本
                    script = next((script for script in self.dis_script_list if script.get("task_id") == task_id), None)
                    if script:
                        self.dis_task_list.remove(task)
                        self.dis_script_list.remove(script)
                        try:
                            # 执行脚本
                            global_namespace = {
                            'id': self.id,
                            'drone': self.device["drone"],
                            'dronemonitor': self.monitor,
                            'p2p_node': self.p2p_node,
                            'dynamic_data' : self.perceptor.dynamic_data,
                            '__builtins__': __builtins__
                            }
                            exec(script.get("script", ""), global_namespace)
                            if task.name in global_namespace:
                                result = global_namespace[task.name](self.id, self.device["drone"], self.monitor, self.connection, self.perceptor.dynamic_data)
                                print(f"函数执行结果: {result}")
                                self.perceptor.dis_finished_list.append(task_id)  # 修改为使用 self.perceptor.dis_finished_list
                            else:
                                print("未找到函数 subtask1")
                            
                        except Exception as e:
                            print(f"执行任务 {task_id} 时出错: {str(e)}")
                            traceback.print_exc()
                # 防止过高的 CPU 占用率
                time.sleep(5)






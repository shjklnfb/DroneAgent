import threading
import json
import traceback
from kafka import KafkaConsumer
import time
'''
无人机执行器
独立运行的线程，负责接收并读取任务调度器下发给自己的子任务（包括：python代码和子任务描述）
只需要执行python脚本即可
'''

class DroneExecutor(threading.Thread):

    def __init__(self, id, device, task, monitor, perceptor, connection):
        super().__init__()
        self.id = id  # id
        self.device = device  # 无人机型号、ip、port
        self.task = task      # 子任务
        self.monitor = monitor  # 监控器实例，用于获取无人机状态等信息
        self.perceptor = perceptor  # 感知器实例，用于获取无人机感知信息
        self.connection = connection  # 共享的连接实例
        self.stop_event = threading.Event()
        self.dis_task_list = []  # 分布式执行中，用于保存脚本的列表
        self.dis_script_list = []  # 分布式执行中，用于保存脚本的字典列表
        # self.dis_finished_list = []  # 分布式执行中，用于保存已完成子任务序号的列表

    def connect_to_kafka(self):
        """
        建立 Kafka 连接并返回消费者实例。
        """
        try:
            print("正在尝试连接到 Kafka...")
            consumer = KafkaConsumer(
                'task_queue',
                bootstrap_servers=['47.93.46.144:9092'],
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=f'drone_{self.device["drone"]}_group',
                value_deserializer=lambda v: v.decode('utf-8')
            )
            print("成功连接到 Kafka")
            return consumer
        except Exception as e:
            print(f"Error connecting to Kafka: {str(e)}")
            traceback.print_exc()
            return None

    def execute_task(self, message):
        """
        执行接收到的任务代码。
        """
        try:
            # 解析消息内容
            task_data = json.loads(message)
            code = task_data.get("content", "")
            if not code:
                print("接收到的消息中没有任务代码")
                return

            global_namespace = {
                'id': self.id,
                'drone': self.device["drone"],
                'dronemonitor': self.monitor,
                'droneconnect': self.connection,
                'dynamic_data' : self.perceptor.dynamic_data,
                '__builtins__': __builtins__,

            }
            exec(code, global_namespace)
            if self.task.name in global_namespace:
                result = global_namespace[self.task.name](self.id, self.device["drone"], self.monitor, self.connection, self.perceptor.dynamic_data)
                print(f"函数执行结果: {result}")
            else:
                print("集中式执行器未找到函数")
        except Exception as e:
            print(f"Error executing received code: {str(e)}")
            traceback.print_exc()


    def disconnect_from_kafka(self, consumer):
        """
        关闭 Kafka 消费者连接。
        """
        if consumer:
            print("关闭 Kafka 消费者连接")
            consumer.close()

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

    def run_cen(self):
        """
        线程运行方法，持续监听消息队列并处理任务。
        """
        consumer = self.connect_to_kafka()
        if not consumer:
            return

        try:
            print("开始监听消息队列...")
            for message in consumer:
                # 使用 message.value 作为 JSON 格式的字符串
                task_data = json.loads(message.value)
                task_name = task_data.get("id", "")
                if task_name == self.task.name:
                    consumer.commit()
                    self.execute_task(message.value)
                    # 手动提交偏移量，确保消息被标记为已处理
                if self.stop_event.is_set():
                    print("停止事件已触发，退出监听")
                    break
        finally:
            self.disconnect_from_kafka(consumer)

    def run(self):
        """
        启动分布式执行器
        需要同时接受子任务描述和每个子任务的python代码
        从子任务描述中检查依赖关系，得到满足的可以执行python代码
        无人机之间需要建立连接，互相发送消息
        无人机感知器需要检查消息，更新依赖关系，传递数据
        """
        # 启动分布式监听器，将该无人机的任务和脚本加入到任务队列中
        threading.Thread(target=self.listen_distributed, daemon=True).start()
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
                            'droneconnect': self.connection,
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






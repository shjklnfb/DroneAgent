import threading
import json
import traceback
from kafka import KafkaConsumer
import queue
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
        self.connection = connection  # 连接实例，用于与任务调度器通信
        self.stop_event = threading.Event()
        self.task_queue = queue.Queue()  # 任务队列

    # def establish_connection(self):
    #     """
    #     建立与任务调度器和其他无人机的连接。
    #     """
    #     try:
    #         print("正在尝试建立与任务调度器的连接...")
    #         self.connection.connect()  
    #     except Exception as e:
    #         print(f"Error establishing connection: {str(e)}")
    #         traceback.print_exc()
       
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
                'drone': self.device["drone"],
                'dronemonitor': self.monitor,
                'droneconnect': self.connection,
                '__builtins__': __builtins__
            }
            exec(code, global_namespace)
            if 'subtask1' in global_namespace:
                result = global_namespace['subtask1'](self.id, self.device["drone"], self.monitor, self.connection)
                print(f"函数执行结果: {result}")
            else:
                print("未找到函数 subtask1")
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

    def listen(self):
        """
        分布式执行的监听方法，持续监听消息队列，将任务消息放入任务队列。
        """
        consumer = self.connect_to_kafka()
        if not consumer:
            return

        try:
            print("开始监听消息队列并将消息放入任务队列...")
            for message in consumer:
                self.task_queue.put(message.value)  # 将消息放入队列
                if self.stop_event.is_set():
                    print("停止事件已触发，退出监听")
                    break
        finally:
            self.disconnect_from_kafka(consumer)

    def run(self):
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
                self.execute_task(message.value)
                if self.stop_event.is_set():
                    print("停止事件已触发，退出监听")
                    break
        finally:
            self.disconnect_from_kafka(consumer)

    def run_distributed(self):
        """
        启动分布式执行器，监听消息队列并处理任务。
        """
        self.listen()
        pass


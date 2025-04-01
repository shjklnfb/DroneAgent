import threading
import queue
import json
import importlib
import sys
import time
import os
import traceback
from kafka import KafkaConsumer
'''
无人机执行器
独立运行的线程，负责接收并读取任务调度器下发给自己的子任务（包括：python代码和子任务描述）
只需要执行python脚本即可
'''

class DroneExecutor(threading.Thread):

    def __init__(self, drone_id, task, monitor, perceptor, connection):
        super().__init__()
        self.drone_id = drone_id  # 无人机ID
        self.task = task      # 子任务
        self.monitor = monitor  # 监控器实例，用于获取无人机状态等信息
        self.perceptor = perceptor  # 感知器实例，用于获取无人机感知信息
        self.connection = connection  # 连接实例，用于与任务调度器通信
        self.stop_event = threading.Event()
        

    def run(self):
        """
        线程运行方法，持续监听消息队列并处理任务。
        """
        consumer = None
        try:
            print("正在尝试连接到 Kafka...")
            consumer = KafkaConsumer(
                'task_queue',
                bootstrap_servers=['47.93.46.144:9092'],
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=f'drone_{self.drone_id}_group',
                value_deserializer=lambda v: v.decode('utf-8')
            )
            print("成功连接到 Kafka，开始监听消息队列...")
            for message in consumer:
                try:
                    # 动态执行代码
                    code = message.value
                    # 设置全局和局部作用域
                    global_namespace = {
                        'drone': self.drone_id,
                        'dronemonitor': self.monitor,
                        'droneconnect': self.connection,
                        '__builtins__': __builtins__
                    }
                    # 执行代码
                    exec(code, global_namespace)
                    # 检查是否成功加载了函数
                    if 'subtask1' in global_namespace:
                        # 调用加载的函数
                        result = global_namespace['subtask1'](self.drone_id, self.monitor, self.connection)
                        print(f"函数执行结果: {result}")
                    else:
                        print("未找到函数 subtask1")
                except Exception as e:
                    print(f"Error executing received code: {str(e)}")
                    traceback.print_exc()
                if self.stop_event.is_set():
                    print("停止事件已触发，退出监听")
                    break
        except Exception as e:
            print(f"Error connecting to Kafka: {str(e)}")
            traceback.print_exc()
        finally:
            if consumer:
                print("关闭 Kafka 消费者连接")
                consumer.close()


        # # 根据task从script文件夹下找到对应子任务的python脚本并执行
        # if self.task:
        #     script_name = self.task.name
        #     if script_name:
        #         try:
        #             # 动态导入模块
        #             module_path = f'scripts.{script_name}'
        #             module = importlib.import_module(module_path)
        #             # 获取同名函数
        #             task_func = getattr(module, script_name)
        #             # 执行任务函数并传递参数
        #             task_func(
        #                 drone=self.drone_id,
        #                 dronemonitor=self.monitor,
        #                 droneconnect=self.connection
        #             )
        #         except ModuleNotFoundError:
        #             print(f'Script module {script_name} not found')
        #         except AttributeError:
        #             print(f'Function {script_name} not found in module')
        #         except Exception as e:
        #             print(f'Error executing {script_name}: {str(e)}')
        #     # run方法执行完成，代表子任务执行完成
        #     # TODO:同时结束其他线程
        #     # self.monitor.stop()
        #     # self.perceptor.stop()

    def another_run(self):
        consumer = None
        try:
            consumer = KafkaConsumer(
                'task_queue',
                bootstrap_servers=['47.93.46.144:9092'],
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=f'drone_{self.drone_id}_group',
                value_deserializer=lambda v: v.decode('utf-8')
            )
            for message in consumer:
                try:
                    # Execute the received Python code
                    code = message.value
                    exec(code, {'drone': self.drone_id, 'dronemonitor': self.monitor, 'droneconnect': self.connection})
                except Exception as e:
                    print(f"Error executing received code: {str(e)}")
                if self.stop_event.is_set():
                    break
        except Exception as e:
            print(f"Error connecting to Kafka: {str(e)}")
        finally:
            if consumer:
                consumer.close()
import threading
import queue
import asyncio
from communication.p2p_node import P2PNode
import time
import traceback

class DroneManager:
    def __init__(self, device, task, drone_executor, drone_perceptor, drone_monitor):
        self.device = device
        self.task = task
        self.drone_executor = drone_executor
        self.drone_perceptor = drone_perceptor
        self.drone_monitor = drone_monitor
        self.stop_event = threading.Event()
        
        # 设置感知器的执行器引用
        if self.drone_perceptor and self.drone_executor:
            self.drone_perceptor.executor = self.drone_executor
            
        # P2P通信相关属性
        self.p2p_node = None
        self.p2p_event_loop = None
        self.p2p_thread = None

    def start_p2p_network(self):
        """
        在独立线程中启动P2P网络通信
        """
        try:
            # 创建事件循环
            self.p2p_event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.p2p_event_loop)
            
            # 使用无人机ID创建P2P节点
            drone_id = self.device["drone"]
            drone_port = self.device["drone_port"]
            
            self.p2p_node = P2PNode(drone_id, port=drone_port)
            
            # 为p2p_node添加事件循环引用
            self.p2p_node.event_loop = self.p2p_event_loop
            
            # 添加消息处理函数
            if hasattr(self.drone_executor, 'handle_p2p_message'):
                self.p2p_node.add_message_handler(self.drone_executor.handle_p2p_message)
            
            # 启动P2P节点服务器
            self.p2p_event_loop.run_until_complete(self.p2p_node.start_server())
            print(f"无人机 {drone_id} 的P2P节点已启动，端口: {drone_port}")
            
            # 添加调度器节点和其他无人机到连接列表
            scheduler_id = "scheduler"
            scheduler_host = "localhost"
            scheduler_port = 9000
            self.p2p_node.add_node(scheduler_id, scheduler_host, scheduler_port)
            
            # 添加所有其他无人机节点到连接列表
            current_drone_id = self.device["drone"]
            if hasattr(self.drone_executor, 'devices') and self.drone_executor.devices:
                for device in self.drone_executor.devices:
                    if device["drone"] != current_drone_id:
                        other_drone_id = device["drone"]
                        other_drone_ip = device["drone_ip"]
                        other_drone_port = device["drone_port"]
                        self.p2p_node.add_node(other_drone_id, other_drone_ip, other_drone_port)
            
            # 运行事件循环，保持节点活跃
            self.p2p_event_loop.run_forever()
        except Exception as e:
            print(f"P2P网络线程遇到异常: {str(e)}")
            traceback.print_exc()
        finally:
            print("P2P网络线程结束")
        
    def start_threads(self):
        """启动所有线程"""
        # 初始化 ROS 节点
        import rospy
        rospy.init_node("drone_manager", anonymous=True, disable_signals=True)

        # 先启动P2P网络线程
        self.p2p_thread = threading.Thread(target=self.start_p2p_network, daemon=True)
        self.p2p_thread.start()
        print(f"已启动P2P网络线程: {self.device['drone']}")
        
        # 等待P2P网络初始化完成
        time.sleep(2)
        
        # 将P2P节点传递给执行器和感知器
        if self.drone_executor:
            self.drone_executor.p2p_node = self.p2p_node
            self.drone_executor.p2p_event_loop = self.p2p_event_loop
        
        # 启动其他线程
        self.drone_executor.start()
        self.drone_perceptor.start()
        self.drone_monitor.start()
        self.stop_event.clear()
        print(f"DroneManager 已启动所有线程: {self.device['drone']}")

    def stop_threads(self):
        """停止所有线程"""
        self.drone_executor.stop_event.set()
        self.drone_perceptor.stop_event.set()
        self.drone_monitor.stop_event.set()

        # 关闭P2P节点
        if self.p2p_node and self.p2p_event_loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.p2p_node.stop_server(),
                    self.p2p_event_loop
                ).result(timeout=5.0)
                print(f"无人机 {self.device['drone']} 的P2P节点已关闭")
            except Exception as e:
                print(f"关闭P2P节点时出错: {str(e)}")
                
        # 停止事件循环
        if self.p2p_event_loop:
            self.p2p_event_loop.call_soon_threadsafe(self.p2p_event_loop.stop)

        self.drone_executor.join()
        self.drone_perceptor.join()
        self.drone_monitor.join()
        
        # 等待P2P线程结束
        if self.p2p_thread and self.p2p_thread.is_alive():
            self.p2p_thread.join(timeout=5.0)
            
        self.stop_event.set()
        print(f"DroneManager 已停止所有线程: {self.device['drone']}")


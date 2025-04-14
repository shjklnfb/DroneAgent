import threading
import queue

class DroneManager:
    def __init__(self, device, task, drone_executor, drone_perceptor, drone_monitor, drone_connection):
        self.device = device
        self.task = task
        self.drone_executor = drone_executor
        self.drone_perceptor = drone_perceptor
        self.drone_monitor = drone_monitor
        self.drone_connection = drone_connection  # 共享的 Communication 实例
        self.stop_event = threading.Event()

    def start_threads(self):
        """启动所有线程"""
        import rospy
        rospy.init_node("drone_manager", anonymous=True, disable_signals=True)
        self.drone_executor.start()
        self.drone_perceptor.start()
        self.drone_monitor.start()
        self.stop_event.clear()
        print(f"DroneManager 已启动所有线程: {self.device['drone']}")

    def stop_threads(self):
        """停止所有线程"""
        self.drone_executor.stop()
        self.drone_perceptor.stop()
        self.drone_monitor.stop()

        self.drone_executor.join()
        self.drone_perceptor.join()
        self.drone_monitor.join()
        self.stop_event.set()
        print(f"DroneManager 已停止所有线程: {self.device['drone']}")


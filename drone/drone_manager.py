import threading
import queue

class DroneManager:
    def __init__(self, device, task, drone_executor, drone_perceptor, drone_monitor, drone_connection):
        self.device = device
        self.task = task
        self.drone_executor = drone_executor
        self.drone_perceptor = drone_perceptor
        self.drone_monitor = drone_monitor
        self.drone_connection = drone_connection
        self.stop_event = threading.Event()

    def start_threads(self):
        """启动所有线程"""
        self.drone_executor.start()
        self.drone_perceptor.start()
        self.drone_monitor.start()
        
    def stop_threads(self):
        """停止所有线程"""
        # self.drone_executor.stop()
        # self.drone_perceptor.stop()
        # self.drone_monitor.stop()
        
        # self.drone_executor.join()
        # self.drone_perceptor.join()
        # self.drone_monitor.join()


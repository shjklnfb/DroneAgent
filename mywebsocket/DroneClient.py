import json
from websocket import create_connection
import threading

class DroneClient:
    def __init__(self, drone_id, server_address="ws://localhost:8765"):
        self.drone_id = drone_id
        self.server_address = server_address
        self.websocket = None

    def connect(self):
        self.websocket = create_connection(self.server_address)
        print(f"无人机 {self.drone_id} 连接到调度器服务器")
        # 注册无人机ID
        self.websocket.send(json.dumps({"drone_id": self.drone_id}))
        # 启动接收消息的线程
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def receive_messages(self):
        try:
            while True:
                message = json.loads(self.websocket.recv())
                if message["type"] == "message":
                    print(f"无人机 {self.drone_id} 收到消息来自 {message['from']}: {message['message']}")
        except Exception:
            print(f"无人机 {self.drone_id} 断开连接")

    def send_message(self, target_drone_id, message):
        """向目标无人机或调度器发送消息"""
        if target_drone_id.lower() == "scheduler":
            # 向调度器发送消息
            self.websocket.send(json.dumps({"type": "to_scheduler", "message": message}))
        else:
            # 向目标无人机发送消息
            self.websocket.send(json.dumps({"type": "send", "target_drone_id": target_drone_id, "message": message}))

    def disconnect(self):
        self.websocket.close()
        print(f"无人机 {self.drone_id} 已断开连接")
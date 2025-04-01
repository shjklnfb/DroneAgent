import json
from websocket_server import WebsocketServer
import threading

class SchedulerServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients = {}  # 存储连接的无人机，键为无人机ID，值为客户端信息
        self.server = WebsocketServer(host=self.host, port=self.port)
        self.server_thread = None

    def handle_new_client(self, client, server):
        server.send_message(client, json.dumps({"type": "register", "message": "请发送您的无人机ID"}))

    def handle_client_message(self, client, server, message):
        try:
            message = json.loads(message)
            if "drone_id" in message:  # 注册无人机
                drone_id = message["drone_id"]
                if drone_id in self.clients:
                    server.send_message(client, json.dumps({"type": "error", "message": "无人机ID已存在"}))
                else:
                    self.clients[drone_id] = client
                    print(f"无人机 {drone_id} 连接成功: {client['address']}")
            elif message["type"] == "send":  # 转发消息
                target_drone_id = message["target_drone_id"]
                sender_id = next((key for key, value in self.clients.items() if value == client), "Unknown")
                if target_drone_id in self.clients:
                    target_client = self.clients[target_drone_id]
                    server.send_message(target_client, json.dumps({"type": "message", "message": message["message"], "from": sender_id}))
                else:
                    server.send_message(client, json.dumps({"type": "error", "message": "目标无人机不存在"}))
            elif message["type"] == "to_scheduler":  # 处理发给调度器的消息
                sender_id = next((key for key, value in self.clients.items() if value == client), "Unknown")
                print(f"调度器收到来自无人机 {sender_id} 的消息: {message['message']}")
                # 可以在这里添加更多逻辑来处理无人机发给调度器的消息
        except Exception as e:
            print(f"消息处理错误: {e}")

    def handle_client_disconnection(self, client, server):
        for drone_id, drone_client in list(self.clients.items()):
            if drone_client == client:
                del self.clients[drone_id]
                print(f"无人机 {drone_id} 已断开连接")
                break

    def send_to_drone(self, drone_id, message):
        """调度器向特定无人机发送消息"""
        if drone_id in self.clients:
            client = self.clients[drone_id]
            self.server.send_message(client, json.dumps({"type": "message", "message": message, "from": "Scheduler"}))
            print(f"消息已发送到无人机 {drone_id}: {message}")
        else:
            print(f"无人机 {drone_id} 不存在，无法发送消息")

    def start(self):
        self.server.set_fn_new_client(self.handle_new_client)
        self.server.set_fn_message_received(self.handle_client_message)
        self.server.set_fn_client_left(self.handle_client_disconnection)
        self.server_thread = threading.Thread(target=self.server.run_forever, daemon=True)
        self.server_thread.start()
        print(f"调度器服务器已启动: ws://{self.host}:{self.port}")

    def stop(self):
        self.server.shutdown()
        if self.server_thread:
            self.server_thread.join()
        print("调度器服务器已停止")
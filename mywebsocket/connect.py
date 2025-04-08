import socket
import threading

class Communication:
    def __init__(self):
        # 保存连接的字典，键为连接对 (id1, id2)，值为连接实例
        self.connections = {}

    def connect(self, device1, device2):
        """
        建立两个设备之间的连接。

        参数：
            device1 (tuple): (id, ip, port) 表示设备1的信息。
            device2 (tuple): (id, ip, port) 表示设备2的信息。
        """
        id1, ip1, port1 = device1
        id2, ip2, port2 = device2

        if (id1, id2) in self.connections or (id2, id1) in self.connections:
            print(f"连接已存在: {id1} <-> {id2}")
            return

        connection = Connection(device1, device2)
        self.connections[(id1, id2)] = connection
        print(f"已建立连接: {id1} <-> {id2}")

    def send_message(self, sender_id, receiver_id, message):
        """发送消息"""
        connection = self.connections.get((sender_id, receiver_id)) or self.connections.get((receiver_id, sender_id))
        if not connection:
            print(f"连接不存在: {sender_id} <-> {receiver_id}")
            return
        connection.send(sender_id, receiver_id, message)

    def close_connection(self, id1, id2):
        """关闭连接"""
        if (id1, id2) in self.connections:
            self.connections[(id1, id2)].close()
            del self.connections[(id1, id2)]
            print(f"连接已关闭: {id1} <-> {id2}")
        elif (id2, id1) in self.connections:
            self.connections[(id2, id1)].close()
            del self.connections[(id2, id1)]
            print(f"连接已关闭: {id2} <-> {id1}")
        else:
            print(f"连接不存在: {id1} <-> {id2}")


class Connection:
    def __init__(self, device1, device2):
        """
        初始化连接。

        参数：
            device1 (tuple): (id, ip, port) 表示设备1的信息。
            device2 (tuple): (id, ip, port) 表示设备2的信息。
        """
        self.id1, self.ip1, self.port1 = device1
        self.id2, self.ip2, self.port2 = device2
        self.sockets = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()  # 用于停止监听线程

        # 创建两个socket
        self.sockets[self.id1] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockets[self.id2] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 建立客户端连接
        self._connect_sockets()

    def _connect_sockets(self):
        """为两个套接字建立连接"""
                # 尝试绑定到指定端口，如果失败则选择一个空闲端口
        try:
            self.sockets[self.id1].bind((self.ip1, self.port1))  # 绑定到指定端口
        except OSError as e:
            if e.errno == 98:  # 端口占用错误码
                print(f"端口 {self.port1} 被占用，尝试绑定到空闲端口...")
                self.sockets[self.id1].bind((self.ip1, 0))  # 绑定到一个空闲端口
                self.port1 = self.sockets[self.id1].getsockname()[1]  # 更新为实际绑定的端口
                print(f"已绑定到新的端口: {self.port1}")
            else:
                raise
        self.sockets[self.id1].listen(1)

        # 连接到对方
        client_thread = threading.Thread(target=self._connect_client)
        client_thread.start()
        client_thread.join()  # 确保连接完成后再启动监听线程

        # 启动监听线程
        self.threads = {
            self.id1: threading.Thread(target=self._listen, args=(self.id1,)),
            self.id2: threading.Thread(target=self._listen, args=(self.id2,))
        }
        self.threads[self.id1].start()
        self.threads[self.id2].start()

    def _connect_client(self):
        """连接到监听的套接字"""
        try:
            self.sockets[self.id2].connect((self.ip1, self.port1))
            conn, _ = self.sockets[self.id1].accept()  # 接受连接
            self.sockets[self.id1] = conn  # 替换为已连接的套接字
        except Exception as e:
            print(f"连接错误: {e}")
            self.sockets[self.id2].close()
            del self.sockets[self.id2]

    def send(self, sender_id, receiver_id, message):
        """发送消息"""
        if sender_id not in self.sockets or receiver_id not in self.sockets:
            print(f"无效的发送或接收ID: {sender_id}, {receiver_id}")
            return
        with self.lock:
            try:
                self.sockets[sender_id].sendall(f"{sender_id} -> {receiver_id}: {message}".encode())
                print(f"消息已发送: {sender_id} -> {receiver_id}: {message}")
            except Exception as e:
                print(f"发送错误: {e}")

    def _listen(self, receiver_id):
        """监听接收消息"""
        sock = self.sockets[receiver_id]
        while not self.stop_event.is_set():
            try:
                data = sock.recv(4096)  # 扩大缓冲区大小到4096字节
                if data:
                    # 假设消息格式为 "sender_id -> receiver_id: message"
                    decoded_message = data.decode()
                    sender_id = decoded_message.split(" -> ")[0]
                    # 将数据记录到以接收者命名的文件中
                    file_path = f"mywebsocket/messages/message_{receiver_id}.txt"
                    with open(file_path, "a", encoding="utf-8") as f:
                        f.write(f"发送者: {sender_id}, 接收者: {receiver_id}, 消息: {decoded_message.strip()}\n")
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"监听错误: {e}")
                break

    def close(self):
        """关闭连接"""
        self.stop_event.set()  # 停止监听线程
        for sock in self.sockets.values():
            sock.close()
        for thread in getattr(self, "threads", {}).values():
            thread.join()
        print(f"连接已关闭: {self.id1} <-> {self.id2}")

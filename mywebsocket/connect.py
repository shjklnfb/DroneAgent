import socket
import threading

class Communication:
    def __init__(self):
        # 保存连接的字典，键为连接对 (id1, id2)，值为连接实例
        self.connections = {}

    def connect(self, id1, id2):
        """建立两个id之间的连接"""
        if (id1, id2) in self.connections or (id2, id1) in self.connections:
            print(f"连接已存在: {id1} <-> {id2}")
            return
        connection = Connection(id1, id2)
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
    def __init__(self, id1, id2):
        self.id1 = id1
        self.id2 = id2
        self.sockets = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()  # 用于停止监听线程

        # 创建两个socket
        self.sockets[id1] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockets[id2] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 建立客户端连接
        self._connect_sockets(id1, id2)

    def _connect_sockets(self, id1, id2):
        """为两个套接字建立连接"""
        self.sockets[id1].bind(("localhost", 0))  # 绑定到随机端口
        self.sockets[id1].listen(1)
        port = self.sockets[id1].getsockname()[1]

        # 连接到对方
        client_thread = threading.Thread(target=self._connect_client, args=(id1, id2, port))
        client_thread.start()
        client_thread.join()  # 确保连接完成后再启动监听线程

        # 启动监听线程
        if id1 in self.sockets and id2 in self.sockets:
            self.threads = {}
            self.threads[id1] = threading.Thread(target=self._listen, args=(id1,))
            self.threads[id2] = threading.Thread(target=self._listen, args=(id2,))
            self.threads[id1].start()
            self.threads[id2].start()

    def _connect_client(self, id1, id2, port):
        """连接到监听的套接字"""
        try:
            self.sockets[id2].connect(("localhost", port))
            conn, _ = self.sockets[id1].accept()  # 接受连接
            self.sockets[id1] = conn  # 替换为已连接的套接字
        except Exception as e:
            print(f"连接错误: {e}")
            self.sockets[id2].close()
            del self.sockets[id2]

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
                data = sock.recv(1024)
                if data:
                    print(f"{receiver_id} 接收到消息: {data.decode()}")
                    # 处理消息，有接受者id和消息内容

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

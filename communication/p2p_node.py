import asyncio
import websockets
import json
from utils.log_configurator import setup_connect_logger
from typing import Dict, Any, List, Callable, Optional

class P2PNode:
    """
    点对点通信节点，既作为服务器也作为客户端
    每个节点可以与其他节点建立连接，发送和接收消息
    """
    
    def __init__(self, node_id: str, host: str = 'localhost', port: int = 8000):
        """
        初始化P2P节点
        
        Args:
            node_id: 节点ID，用于识别
            host: 主机地址，默认为localhost
            port: 监听端口，默认为8000
        """
        self.node_id = node_id
        self.host = host
        self.port = port
        self.connections = {}  # 存储与其他节点的连接 {node_id: websocket}
        self.server = None  # WebSocket服务器
        self.running = False  # 服务器运行状态
        self.message_handlers = []  # 消息处理函数列表
        self.logger = setup_connect_logger("task_16b0f122")  # 日志记录器
        self.nodes_to_connect = {}  # 存储要连接的节点信息 {node_id: {"host": host, "port": port}}
        self.connection_maintainer_task = None  # 连接维护器任务
    
    async def start_server(self):
        """
        启动WebSocket服务器和连接维护器
        """
        if self.running:
            self.logger.info(f"{self.node_id}服务器已经在运行")
            return
        
        self.running = True
        self.server = await websockets.serve(
            self._handle_connection, 
            self.host, 
            self.port
        )
        self.logger.info(f"节点 {self.node_id} 服务器启动在 {self.host}:{self.port}")
        
        # 启动连接维护器
        self.connection_maintainer_task = asyncio.create_task(self.connection_maintainer())
        self.logger.info(f"节点 {self.node_id} 的连接维护器已启动")
    
    async def stop_server(self):
        """
        停止WebSocket服务器和连接维护器
        """
        if not self.running:
            return
        
        self.running = False
        
        # 停止连接维护器
        if self.connection_maintainer_task:
            self.connection_maintainer_task.cancel()
            try:
                await self.connection_maintainer_task
            except asyncio.CancelledError:
                self.logger.info("连接维护器任务已取消")
        
        # 停止服务器
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.logger.info(f"节点 {self.node_id} 服务器已停止")
        
        # 关闭所有连接
        for node_id, ws in list(self.connections.items()):
            await self.disconnect(node_id)
    
    def add_node(self, node_id: str, host: str, port: int):
        """
        添加需要连接的节点信息
        
        Args:
            node_id: 节点ID
            host: 主机地址
            port: 端口号
        """
        self.nodes_to_connect[node_id] = {
            "host": host, 
            "port": port
        }
        self.logger.info(f"连接方{self.node_id} 添加节点 {node_id}({host}:{port}) 到连接列表")
    
    async def connection_maintainer(self, interval=5, max_retries=3, retry_delay=2):
        """
        持续运行的连接维护器，尝试连接到所有未连接的节点
        
        Args:
            interval: 重新检查间隔(秒)
            max_retries: 每次检查时每个节点的最大重试次数
            retry_delay: 重试之间的延迟(秒)
        """
        self.logger.info(f"连接维护器启动，将持续尝试连接到所有配置的节点...")
        
        while self.running:
            try:
                # 获取已连接的节点ID列表
                connected_ids = set(self.connections.keys())
                
                # 获取所有要连接的节点ID列表
                all_node_ids = set(self.nodes_to_connect.keys())
                
                # 找出未连接的节点ID列表
                unconnected_ids = all_node_ids - connected_ids
                
                if unconnected_ids:
                    self.logger.info(f"连接方{self.node_id} 存在 {len(unconnected_ids)} 个未连接的节点，尝试连接...")
                    
                    for node_id in unconnected_ids:
                        node_info = self.nodes_to_connect[node_id]
                        host = node_info["host"]
                        port = node_info["port"]
                        
                        for attempt in range(1, max_retries + 1):
                            try:
                                self.logger.info(f"连接方{self.node_id} 尝试连接到节点 {node_id}({host}:{port}) - 第 {attempt}/{max_retries} 次尝试")
                                
                                connected = await self.connect(
                                    node_id,
                                    host,
                                    port
                                )
                                
                                if connected:
                                    self.logger.info(f"连接方{self.node_id} 成功连接到节点 {node_id}")
                                    break
                                else:
                                    self.logger.warning(f"连接方{self.node_id} 连接到节点 {node_id} 失败")
                                    if attempt < max_retries:
                                        await asyncio.sleep(retry_delay)
                            
                            except Exception as e:
                                self.logger.error(f"连接方{self.node_id} 连接到节点 {node_id} 时出错: {str(e)}")
                                if attempt < max_retries:
                                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.debug(f"连接方{self.node_id} 所有节点都已连接")
                
                # 等待下一次检查
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                self.logger.info(f"连接方{self.node_id} 的连接维护器任务被取消")
                break
            except Exception as e:
                self.logger.error(f"连接方{self.node_id} 的连接维护器遇到未处理的异常: {str(e)}")
                await asyncio.sleep(interval)  # 出现异常后仍然继续运行
    
    async def connect(self, peer_id: str, peer_host: str, peer_port: int) -> bool:
        """
        连接到另一个P2P节点
        
        Args:
            peer_id: 对方节点ID
            peer_host: 对方主机地址
            peer_port: 对方端口
        
        Returns:
            bool: 连接是否成功
        """
        if peer_id in self.connections:
            self.logger.info(f"连接方{self.node_id} 已经连接到节点 {peer_id}")
            return True
        
        try:
            uri = f"ws://{peer_host}:{peer_port}"
            websocket = await websockets.connect(uri)
            
            # 发送自己的节点ID进行身份识别
            await websocket.send(json.dumps({
                "type": "hello",
                "node_id": self.node_id
            }))
            
            # 等待对方确认
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "hello_ack" and data.get("node_id") == peer_id:
                self.connections[peer_id] = websocket
                self.logger.info(f"连接方{self.node_id} 已连接到节点 {peer_id}")
                
                # 启动接收消息的协程
                asyncio.create_task(self._listen_for_messages(peer_id, websocket))
                return True
            else:
                await websocket.close()
                self.logger.error(f"节点 {peer_id} 身份验证失败")
                return False
        
        except Exception as e:
            self.logger.error(f"连接方{self.node_id} 连接到节点 {peer_id} 失败: {str(e)}")
            return False
    
    async def disconnect(self, peer_id: str):
        """
        断开与指定节点的连接
        
        Args:
            peer_id: 要断开连接的节点ID
        """
        if peer_id not in self.connections:
            self.logger.info(f"连接方{self.node_id} 未连接到节点 {peer_id}")
            return
        
        try:
            websocket = self.connections[peer_id]
            await websocket.close()
            del self.connections[peer_id]
            self.logger.info(f"连接方{self.node_id} 已断开与节点 {peer_id} 的连接")
        except Exception as e:
            self.logger.error(f"连接方{self.node_id} 断开与节点 {peer_id} 的连接时出错: {str(e)}")
    
    async def send_message(self, peer_id: str, message: Dict[str, Any]) -> bool:
        """
        向指定节点发送消息
        
        Args:
            peer_id: 接收消息的节点ID
            message: 要发送的消息(字典)
        
        Returns:
            bool: 发送是否成功
        """
        if peer_id not in self.connections:
            self.logger.error(f"连接方{self.node_id} 未连接到节点 {peer_id}，无法发送消息")
            return False
        
        try:
            websocket = self.connections[peer_id]
            await websocket.send(json.dumps(message))
            self.logger.info(f"连接方{self.node_id} 向节点 {peer_id} 发送消息: {message}")
            return True
        except Exception as e:
            self.logger.error(f"连接方{self.node_id} 向节点 {peer_id} 发送消息失败: {str(e)}")
            return False
    
    def add_message_handler(self, handler: Callable[[str, Dict[str, Any]], None]):
        """
        添加消息处理函数
        
        Args:
            handler: 消息处理函数，接收发送者ID和消息内容
        """
        self.message_handlers.append(handler)
    
    async def broadcast(self, message: Dict[str, Any]) -> List[str]:
        """
        向所有连接的节点广播消息
        
        Args:
            message: 要广播的消息
        
        Returns:
            List[str]: 成功发送的节点ID列表
        """
        successful = []
        for peer_id in self.connections:
            if await self.send_message(peer_id, message):
                successful.append(peer_id)
        return successful
    
    async def _handle_connection(self, websocket, path):
        """
        处理新的WebSocket连接（服务器端）
        """
        try:
            # 等待对方发送身份识别消息
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get("type") != "hello" or "node_id" not in data:
                await websocket.close()
                self.logger.error("连接方{self.node_id} 收到无效的握手消息")
                return
            
            peer_id = data["node_id"]
            
            # 回复确认
            await websocket.send(json.dumps({
                "type": "hello_ack",
                "node_id": self.node_id
            }))
            
            # 存储连接
            self.connections[peer_id] = websocket
            self.logger.info(f"连接方{self.node_id} 接受来自节点 {peer_id} 的连接")
            
            # 开始接收消息
            await self._listen_for_messages(peer_id, websocket)
            
        except Exception as e:
            self.logger.error(f"连接方{self.node_id} 处理连接时出错: {str(e)}")
    
    async def _listen_for_messages(self, peer_id: str, websocket):
        """
        监听来自特定节点的消息
        
        Args:
            peer_id: 发送消息的节点ID
            websocket: WebSocket连接
        """
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    self.logger.info(f"连接方{self.node_id} 从节点 {peer_id} 收到消息: {data}")
                    
                    # 调用所有消息处理函数
                    for handler in self.message_handlers:
                        handler(peer_id, data)
                        
                except json.JSONDecodeError:
                    self.logger.error(f"连接方{self.node_id} 从节点 {peer_id} 收到无效的JSON: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"连接方{self.node_id} 与节点 {peer_id} 的连接已关闭")
        except Exception as e:
            self.logger.error(f"连接方{self.node_id} 从节点 {peer_id} 接收消息时出错: {str(e)}")
        
        finally:
            # 清理连接
            if peer_id in self.connections:
                del self.connections[peer_id]

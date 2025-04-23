import asyncio
import sys
import os
import logging
from pathlib import Path

# 添加父目录到sys.path以导入P2PNode
sys.path.append(str(Path(__file__).parent.parent))
from communication.p2p_node import P2PNode

# 配置日志级别
logging.basicConfig(level=logging.INFO)

# 存储每个节点接收到的消息
received_messages = {
    "node1": [],
    "node2": [],
    "node3": []
}

def message_handler_factory(node_id):
    """为每个节点创建一个消息处理函数"""
    def handler(sender_id, message):
        received_messages[node_id].append((sender_id, message))
        print(f"{node_id} 收到来自 {sender_id} 的消息: {message}")
    return handler

async def test_p2p_network():
    """测试三个P2P节点之间的连接和通信"""
    print("创建三个P2P节点...")
    
    # 创建三个节点，使用不同的端口
    node1 = P2PNode("node1", port=8001)
    node2 = P2PNode("node2", port=8002)
    node3 = P2PNode("node3", port=8003)
    
    # 为每个节点添加消息处理函数
    node1.add_message_handler(message_handler_factory("node1"))
    node2.add_message_handler(message_handler_factory("node2"))
    node3.add_message_handler(message_handler_factory("node3"))
    
    try:
        # 启动所有节点的服务器
        print("启动所有节点...")
        await node1.start_server()
        await node2.start_server()
        await node3.start_server()
        
        # 建立连接
        print("建立节点间连接...")
        
        # node1 连接到 node2
        connected = await node1.connect("node2", "localhost", 8002)
        assert connected, "node1 连接到 node2 失败"
        
        # node2 连接到 node3
        connected = await node2.connect("node3", "localhost", 8003)
        assert connected, "node2 连接到 node3 失败"
        
        # node3 连接到 node1，形成三角形拓扑
        connected = await node3.connect("node1", "localhost", 8001)
        assert connected, "node3 连接到 node1 失败"
        
        # 给连接一点时间稳定
        await asyncio.sleep(1)
        
        print("\n测试点对点消息发送...")
        # node1 发送消息给 node2
        await node1.send_message("node2", {
            "type": "test",
            "content": "从node1到node2的测试消息"
        })
        
        # node2 发送消息给 node3
        await node2.send_message("node3", {
            "type": "test",
            "content": "从node2到node3的测试消息"
        })
        
        # node3 发送消息给 node1
        await node3.send_message("node1", {
            "type": "test",
            "content": "从node3到node1的测试消息"
        })
        
        # 等待消息处理
        await asyncio.sleep(1)
        
        # 验证消息接收
        assert any(msg[0] == "node1" and msg[1].get("content") == "从node1到node2的测试消息" for msg in received_messages["node2"]), "node2 未接收到 node1 的消息"
        assert any(msg[0] == "node2" and msg[1].get("content") == "从node2到node3的测试消息" for msg in received_messages["node3"]), "node3 未接收到 node2 的消息"
        assert any(msg[0] == "node3" and msg[1].get("content") == "从node3到node1的测试消息" for msg in received_messages["node1"]), "node1 未接收到 node3 的消息"
        
        print("点对点消息测试成功！\n")
    
        
        print("测试断开连接...")
        # 断开node1和node2之间的连接
        await node1.disconnect("node2")
        
        # 尝试发送消息，应该失败
        result = await node1.send_message("node2", {
            "type": "test",
            "content": "这条消息不应该发送成功"
        })
        assert not result, "断开连接后仍然能够发送消息"
        
        print("断开连接测试成功！\n")
        
    finally:
        print("关闭所有节点...")
        # 停止所有节点的服务器
        await node1.stop_server()
        await node2.stop_server()
        await node3.stop_server()

if __name__ == "__main__":
    asyncio.run(test_p2p_network())

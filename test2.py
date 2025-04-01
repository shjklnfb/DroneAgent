from kafka import KafkaProducer
import json
import time

# 创建 KafkaProducer 实例
producer = KafkaProducer(
    bootstrap_servers="47.93.46.144:9092",  # Kafka 服务器地址
    value_serializer=lambda v: json.dumps(v).encode("utf-8")  # 消息序列化器，将消息转换为 JSON 格式
)

# 发送消息
topic = "test-topic"  # Kafka 主题
for i in range(5):  # 发送 5 条消息
    message = {"key": f"value-{i}"}  # 消息内容
    producer.send(topic, message)  # 发送消息到指定主题
    print(f"Sent message: {message}")
    time.sleep(1)  # 每隔 1 秒发送一条消息
producer.flush()  # 确保消息发送完成
print("All messages sent successfully!")
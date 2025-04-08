from connect import Communication
import time

def test_communication():
    comm = Communication()

    # 定义设备信息
    device1 = ("device1", "localhost", 8001)
    device2 = ("device2", "localhost", 8002)
    device3 = ("device3", "localhost", 8003)

    # 建立连接
    comm.connect(device1, device2)
    comm.connect(device2, device3)
    comm.connect(device2, device1)

    # 等待连接建立完成
    time.sleep(1)

    # 发送消息
    comm.send_message("device1", "device2", "Hello from device1 to device2")
    comm.send_message("device2", "device3", "Hello from device2 to device3")
    comm.send_message("device3", "device1", "Hello from device3 to device1")

    # 等待消息传输完成
    time.sleep(1)

    # 关闭连接
    comm.close_connection("device1", "device2")
    comm.close_connection("device2", "device3")
    comm.close_connection("device1", "device3")

if __name__ == "__main__":
    test_communication()

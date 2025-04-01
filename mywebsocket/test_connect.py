from connect import Communication
import time
 
comm = Communication()
def test_communication():
   

    # 建立连接
    comm.connect("connect1", "connect2")
    comm.connect("connect2", "connect3")
    comm.connect("connect1", "connect3")

    # 等待连接建立完成
    time.sleep(1)

   

if __name__ == "__main__":
    test_communication()

     # 发送消息
    comm.send_message("connect1", "connect2", "Hello from connect1 to connect2")
    comm.send_message("connect2", "connect3", "Hello from connect2 to connect3")
    comm.send_message("connect3", "connect1", "Hello from connect3 to connect1")

    # 等待消息传输完成
    time.sleep(1)

    # 关闭连接
    comm.close_connection("connect1", "connect2")
    comm.close_connection("connect2", "connect3")
    comm.close_connection("connect1", "connect3")

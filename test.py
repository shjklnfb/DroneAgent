from task.task_initializer import TaskInitializer
import asyncio

async def main():
    ini = TaskInitializer(
        "task_16b0f122",
        [{"drone": "drone1", "drone_ip": "localhost", "drone_port": 8900},
         {"drone": "drone2", "drone_ip": "localhost", "drone_port": 8901}],
        []
    )
    conn = await ini.initialize_connections()  # 初始化连接
    await conn.send_message("Scheduler", "Hello from Scheduler")  # 发送消息

if __name__ == "__main__":
    asyncio.run(main())
from models.model_functions import func_task_decomposition, func_generate_launch_file
from utils.log_configurator import setup_task_logger
from threading import Thread
from models.model_libirary import ModelLibrary
from multiprocessing import Manager
import os
import time


class TaskInitializer:
    """
    任务初始化器
    负责初始化任务所需的环境，包括无人机连接、模拟环境和云端资源等。
    输入：无人机列表，id
    输出：无人机连接字典，模拟环境配置，云端资源配置
    """
    def __init__(self, id, devices, services):
        self.id = id
        self.devices = devices # 无人机列表，包含型号、ip、port信息,ip和port是已经分配好的
        self.services = services  # 服务列表
        self.logger = setup_task_logger(self.id)
        self.model_library = ModelLibrary()  # 模型库实例

    # async def initialize_connections(self):
    #     """
    #     初始化 WebSocket 客户端连接。
    #     """
    #     try:
    #         self.logger.info("尝试连接到调度器服务器...")
    #         scheduler = WebSocketClient("ws://localhost:6789", "Scheduler")
    #         await scheduler.connect()  # 客户端注册到服务器
    #         self.logger.info("调度器成功连接到服务器")
    #         return scheduler
    #     except Exception as e:
    #         self.logger.error(f"调度器连接到服务器失败: {e}")
    #         raise

    def initialize_simulation_environment(self, world_file):
        """
        根据分解结果，初始化仿真的环境。
        """
        self.logger.info(f"初始化模拟环境，使用世界文件: {world_file}")
        try:
            # 更新设备信息的引用
            devices_info = [{"drone": device['drone'], "ip": device['drone_ip'], "port": device['drone_port']} for device in self.devices]
            content = func_generate_launch_file(devices_info, world_file)
            # TODO：将content写入launch文件中
            self.logger.info("模拟环境初始化完成")
        except Exception as e:
            self.logger.error(f"模拟环境初始化失败: {e}")
            raise

    def initialize_cloud_resources(self):
        """
        初始化云端环境，配置任务所需的云端资源。

        参数:
        self.services: 包含云端配置，例如计算资源、存储等。
        """
        self.logger.info(f"初始化云端环境，配置: {self.services}")
        try:
            for service_name in self.services:
                # 检查服务是否已存在
                if not self.model_library.service_exists(service_name):
                    self.logger.info(f"服务 {service_name} 不存在，正在部署...")
                    deployed_service = self.model_library.deploy_service(service_name)
                    self.logger.info(f"服务 {service_name} 部署完成: {deployed_service}")
                else:
                    self.logger.info(f"服务 {service_name} 已存在，跳过部署")
            self.logger.info("云端环境初始化完成")
        except Exception as e:
            self.logger.error(f"云端环境初始化失败: {e}")
            raise
    
    def record_service_info(self):
        """
        根据服务列表记录服务信息到文件。
        """

        self.logger.info("记录服务信息到文件")
        try:
            # 创建目标文件夹
            folder_path = os.path.join("scripts", self.id)
            os.makedirs(folder_path, exist_ok=True)

            # 文件路径
            file_path = os.path.join(folder_path, "task_info.txt")

            # 记录服务信息
            with open(file_path, "a", encoding="utf-8") as file:
                file.write("services:\n")
                for service_name in self.services:
                    service_info = self.model_library.get_service_info(service_name)
                    if service_info is None:
                        raise ValueError(f"找不到服务 {service_name}")
                    file.write(f"- service_name: {service_name}\n")
                    file.write(f"  service_type: {service_info.get('type', 'N/A')}\n")
                    file.write(f"  service_description: {service_info.get('description', 'N/A')}\n")
                    file.write(f"  service_ip: {service_info.get('ip', 'N/A')}\n")
                    file.write(f"  service_url: {service_info.get('url', 'N/A')}\n")
                    file.write(f"  service_port: {service_info.get('port', 'N/A')}\n")
                    file.write(f"  service_apikey: {service_info.get('apikey', 'N/A')}\n")

            self.logger.info(f"服务信息已记录到 {file_path}")
        except Exception as e:
            self.logger.error(f"记录服务信息失败: {e}")
            raise

    def run(self):
        """
        运行任务初始化器，执行所有初始化步骤。
        """
        self.logger.info("任务初始化器开始运行")

        # 初始化模拟环境
        world_file = "path/to/world/file"
        self.initialize_simulation_environment(world_file)

        # 初始化云端资源
        self.initialize_cloud_resources()

        self.record_service_info()
        self.logger.info("任务初始化器运行完成")

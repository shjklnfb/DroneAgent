from mywebsocket.connect import Communication
from models.model_functions import task_decomposition, generate_launch_file
from utils.log_configurator import setup_logger
from threading import Thread
from models.model_libirary import ModelLibrary
from multiprocessing import Manager

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
        self.logger = setup_logger(self.id)
        self.model_library = ModelLibrary()  # 模型库实例

    def connection_worker(self,comm):
        while True:
            for device in self.devices:
                # 每台无人机与调度器连接
                scheduler_id, scheduler_ip, scheduler_port = "scheduler", "localhost", 9000
                drone = device['drone']
                drone_ip = device['drone_ip']
                drone_port = device['drone_port']
                if not comm.connections.get((drone, scheduler_id)) and not comm.connections.get((scheduler_id, drone)):
                    comm.connect((drone, drone_ip, drone_port), (scheduler_id, scheduler_ip, scheduler_port))

    def initialize_connections(self):
        """
        初始化无人机连接，仅建立调度器和无人机之间的连接。
        """
        manager = Manager()
        comm = Communication(manager=manager)  # 使用共享的 Manager

        # 启动线程不断尝试建立连接
        connection_thread = Thread(target=self.connection_worker, args=(comm,))
        connection_thread.start()

        return comm
    

    def initialize_simulation_environment(self, world_file):
        """
        根据分解结果，初始化仿真的环境。
        """
        self.logger.info(f"初始化模拟环境，使用世界文件: {world_file}")
        try:
            # 更新设备信息的引用
            devices_info = [{"drone": device['drone'], "ip": device['drone_ip'], "port": device['drone_port']} for device in self.devices]
            content = generate_launch_file(devices_info, world_file)
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

    def run(self):
        """
        运行任务初始化器，执行所有初始化步骤。
        """
        self.logger.info("任务初始化器开始运行")
        
        # 初始化无人机连接
        comm = self.initialize_connections()

        # 初始化模拟环境
        world_file = "path/to/world/file"
        self.initialize_simulation_environment(world_file)

        # 初始化云端资源
        self.initialize_cloud_resources()
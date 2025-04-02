import yaml
from models.interface import task_decomposition, generate_launch_file
from config.log_config import setup_logger

'''
任务规划器
负责将用户输入的任务进行分解，生成子任务列表，并验证子任务之间的依赖关系。
同时负责初始化模拟环境和云端环境。
'''
class TaskPlanner:
    def __init__(self, id, task):
        self.id = id
        self.task = task
        self.subtasks = []
        self.drones = []  # 将 drones 作为类的一个属性
        self.logger = setup_logger(self.id)

    def decompose_task(self, task):
        """
        根据prompt和task,调用deepseekr1，生成任务分解方案

        输入格式: 任务描述
        返回格式: [subtask1,subtask2...,subtaskN]
        """
        self.logger.info("开始任务分解")
        try:
            # 读取 YAML 文件
            with open('resource/prompt.yaml', 'r', encoding='utf-8') as file:
                yaml_data = yaml.safe_load(file)

            # 获取 task_decompose 字段
            task_decompose = yaml_data.get('task_decompose', '')

            # 将 task 填充到 user_task
            prompt = task_decompose.format(user_task=task)
            
            # 调用models中的接口
            self.subtasks = task_decomposition(prompt)
            self.logger.info(f"任务分解完成: {self.subtasks}")
        except Exception as e:
            self.logger.error(f"任务分解失败: {e}")
            raise
        return self.subtasks

    def validate_dependencies(self, subtasks):
        """
        验证子任务依赖关系是否符合规范
        """
        self.logger.info("开始验证子任务依赖关系")
        # TODO: 添加验证逻辑
        self.logger.info("子任务依赖关系验证完成")

    def initialize_simulation(self, world_file):
        """
        根据分解结果，初始化模拟环境。
        """
        self.logger.info(f"初始化模拟环境，使用世界文件: {world_file}")
        try:
            content = generate_launch_file(self.drones, world_file)
            # TODO：将content写入launch文件中
            self.logger.info("模拟环境初始化完成")
        except Exception as e:
            self.logger.error(f"模拟环境初始化失败: {e}")
            raise

    def initialize_cloud(self, cloud_config):
        """
        初始化云端环境，配置任务所需的云端资源。
        
        参数:
        cloud_config: dict 包含云端配置，例如计算资源、存储等。
        """
        self.logger.info(f"初始化云端环境，配置: {cloud_config}")
        try:
            # 模拟云端资源初始化
            self.logger.info("云端环境初始化完成")
        except Exception as e:
            self.logger.error(f"云端环境初始化失败: {e}")
            raise

    def run(self):
        self.logger.info("任务规划器开始运行")
        try:
            # 进行任务分解
            subtasks = self.decompose_task(self.task)
            # 校验子任务依赖关系
            self.validate_dependencies(subtasks)
            # 从subtasks列表中获取drones列表
            for subtask in subtasks:
                if subtask.device not in self.drones:
                    self.drones.append(subtask.device)
            self.logger.info(f"获取到的无人机列表: {self.drones}")
            # 初始化模拟环境
            self.initialize_simulation("worlds/empty.world")
            # 初始化云端环境
            self.initialize_cloud({"compute": "high", "storage": "large"})
            self.logger.info("任务规划器运行完成")
        except Exception as e:
            self.logger.error(f"任务规划器运行失败: {e}")
            raise

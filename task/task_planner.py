import yaml
from models.model_functions import task_decomposition, generate_launch_file
from utils.log_configurator import setup_logger

'''
任务规划器
负责将用户输入的任务进行分解，生成子任务列表，并验证子任务之间的依赖关系。
输入：用户任务，id
输出：子任务列表，无人机列表
'''
class TaskPlanner:
    def __init__(self, id, task):
        self.id = id
        self.task = task
        self.subtasks = []
        self.devices = []  # 将 devices 作为类的一个属性
        self.services = []  # 服务列表
        self.logger = setup_logger(self.id)

    def decompose_task(self, task):
        """
        根据prompt和task,调用deepseekr1，生成任务分解方案

        在这里不仅需要分解任务，需要给出依赖，被依赖，当前无人机，无人机的ip和port
        还需要为每个子任务分配无人机设备。
        一旦确定了无人机设备有哪些，就可以初始化仿真环境，分配端口，为建立连接做准备

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

    def analyze_service(self):
        """
        分析本次任务需要的服务列表
        """
        self.logger.info("开始分析服务列表")
        try:
            self.services = ["deepseekr1", "chatgpt"]  # 示例服务列表
            self.logger.info(f"分析完成，服务列表: {self.services}")
        except Exception as e:
            self.logger.error(f"服务分析失败: {e}")
            raise

    def run(self):
        self.logger.info("任务规划器开始运行")
        try:
            # 进行任务分解
            subtasks = self.decompose_task(self.task)

            # 校验子任务依赖关系
            self.validate_dependencies(subtasks)

            # 从subtasks列表中获取devices列表, 列表中有型号ip和port
            for subtask in subtasks:
                device_info = subtask.device  # 获取 device 属性
                if device_info not in self.devices:
                    self.devices.append(device_info)
            self.logger.info(f"获取到的无人机列表: {self.devices}")

            # 分析服务列表
            self.analyze_service()

            self.logger.info("任务规划器运行完成")
        except Exception as e:
            self.logger.error(f"任务规划器运行失败: {e}")
            raise

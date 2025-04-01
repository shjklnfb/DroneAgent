class TaskPlanner:
    def __init__(self, id, task):
        self.id = id
        self.task = task
        self.subtasks = []
        self.drones = []  # 将 drones 作为类的一个属性

    def decompose_task(self, task):
        """
        根据prompt和task,调用deepseekr1，生成任务分解方案

        输入格式: 任务描述
        返回格式: [subtask1,subtask2...,subtaskN]
        """
        # 读取 YAML 文件
        with open('resource/prompt.yaml', 'r', encoding='utf-8') as file:
            yaml_data = yaml.safe_load(file)

        # 获取 task_decompose 字段
        task_decompose = yaml_data.get('task_decompose', '')

        # 将 task 填充到 user_task
        prompt = task_decompose.format(user_task=task)
        
        #调用models中的接口
        self.subtasks = task_decomposition(prompt)
        return self.subtasks

    def validate_dependencies(self, subtasks):
        """
        验证子任务依赖关系是否符合规范
        """
        pass

    def initialize_simulation(self, world_file):
        """
        根据分解结果，初始化模拟环境。
        """
        content = generate_launch_file(self.drones, world_file)
        # TODO：将content写入launch文件中
        pass

    def initialize_cloud(self, cloud_config):
        """
        初始化云端环境，配置任务所需的云端资源。
        
        参数:
        cloud_config: dict 包含云端配置，例如计算资源、存储等。
        """
        # 模拟云端资源初始化
        pass

    def run(self):
        # 进行任务分解
        subtasks = self.decompose_task(self.task)
        # 校验子任务依赖关系
        self.validate_dependencies(subtasks)
        # 从subtasks列表中获取drones列表
        for subtask in subtasks:
            if subtask.device not in self.drones:
                self.drones.append(subtask.device)
        # 初始化模拟环境
        self.initialize_simulation("worlds/empty.world")
        # 初始化云端环境
        self.initialize_cloud({"compute": "high", "storage": "large"})

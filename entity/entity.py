class SubTask:
    def __init__(self, id, name, description, depid, device, steps, requirements):
        """
        初始化子任务实体类。

        :param id: 任务ID
        :param name: 任务名称
        :param description: 任务描述
        :param depId: 依赖任务ID，为任务ID
        :param device: 使用的无人机
        :param steps: 步骤列表
        :param requirements: 要求字典
        """
        self.id = id
        self.name = name
        self.description = description
        self.depid = depid if isinstance(depid, list) else [depid]
        self.device = device
        self.steps = steps
        self.requirements = requirements




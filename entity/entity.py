class SubTask:
    def __init__(self, id, name, description, depid, drone, steps, requirements, drone_ip, drone_port, services):
        """
        初始化子任务实体类。

        :param id: 任务ID
        :param name: 任务名称
        :param description: 任务描述
        :param depId: 依赖任务ID，为任务ID
        :param drone: 使用的无人机,ip和端口
        :param services: 使用的服务列表
        :param steps: 步骤列表
        :param requirements: 要求字典
        :param dependent_by_task_ids: 依赖于该任务的任务ID列表,用于分布式中主动发送消息通知该任务已完成
        """
        self.id = id
        self.name = name
        self.description = description
        self.depid = depid if isinstance(depid, list) else [depid]
        self.steps = steps
        self.requirements = requirements
        self.device = {
            "drone": drone,
            "drone_ip": drone_ip,
            "drone_port": drone_port
        }
        self.services = services 
        self.dependent_by_subtask_ids = []

    def __str__(self):
        """
        返回子任务的详细信息字符串表示。
        """
        return (
            f"SubTask(id={self.id}, name={self.name}, description={self.description}, "
            f"depid={self.depid}, steps={self.steps}, requirements={self.requirements}, "
            f"device={self.device}, services={self.services}, "
            f"dependent_by_subtask_ids={self.dependent_by_subtask_ids})"
        )




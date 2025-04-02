import threading
from queue import Queue
from config.log_config import setup_logger
from models.interface import subtask_to_python

'''
任务翻译器（将分解好的子任务翻译为python脚本）
任务翻译由大模型来完成，针对大模型的特点，我们采用如下策略：
1、提供知识库。将无人机的基本动作和组合动作（例如：起飞，下降，拐弯，网格式搜索，传感器信息读取与分析等等），封装成函数调用。由大模型来选择使用。
2、由于大模型只能用自然语言输入和输出，如果某一个过程需要利用大模型来完成理解和判断，在对应的函数代码中需要采用如下两个机制：
1）在提示词中对大模型的输出进行规范化，必要时提供样例。2需要在返回前提取出大模型的输出，进行转化满足函数的返回值要求。
'''

class TaskTranslator:
    def __init__(self, id, subtasks):
        self.id = id
        self.subtasks = subtasks
        self.knowledge_base = {
            '基本动作': [],
        }
        self.logger = setup_logger(self.id)

    def translate_subtask(self, subtasks):
        """
        将自然语言子任务翻译为可执行Python代码
        返回格式: True/False, 代码直接写到script中该任务的文件夹（文件夹名为self.id）下,py文件名为id+subtask_id.py
        """
        # TODO: 集成大模型调用逻辑
        self.logger.info(f"开始翻译子任务: {subtasks}")
        subtask_to_python(subtasks)
        self.logger.info(f"完成翻译子任务: {subtasks}")
        return []

    def run(self):
        """
        运行任务翻译器，处理所有子任务
        """
        for subtask in self.subtasks:
            self.logger.info(f"翻译子任务: {subtask}")
            success, code = self.translate_subtask(subtask)
            if success:
                self.logger.info(f"成功翻译子任务: {subtask}")
            else:
                self.logger.error(f"翻译子任务失败: {subtask}")
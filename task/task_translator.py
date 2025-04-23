import threading
from queue import Queue
from utils.log_configurator import setup_task_logger
from models.model_functions import func_subtask_to_python
import os

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
            '基本动作': [], # 基本的函数库
        }
        self.logger = setup_task_logger(self.id)

    def translate_subtask(self):
        """
        将自然语言子任务翻译为可执行Python代码
        返回格式: True/False, 代码直接写到script中该任务的文件夹（文件夹名为self.id）下,py文件名为id+subtask_id.py
        """
        self.logger.info(f"开始翻译子任务: {self.subtasks}")
        # for subtask in self.subtasks:
        #     prompt = 1
        #     script = func_subtask_to_python(prompt)
        #     try:
        #         folder_path = f"./{self.id}/"
        #         file_name = f"{self.id}_{subtask['id']}.py"
        #         os.makedirs(folder_path, exist_ok=True)
        #         with open(os.path.join(folder_path, file_name), 'w', encoding='utf-8') as file:
        #             file.write(script)
        #         self.logger.info(f"子任务脚本已保存: {file_name}")
        #     except Exception as e:
        #         self.logger.error(f"保存子任务脚本失败: {e}")
        self.logger.info(f"完成翻译子任务: {self.subtasks}")

    def log_subtasks_info(self):
        """
        将所有的子任务信息记录到scripts文件夹下的self.id为名称的文件夹下的task_info.txt文件中
        """
        try:
            folder_path = f"scripts/{self.id}/"
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder_path, "task_info.txt")
            with open(file_path, 'a', encoding='utf-8') as file:
                file.write("subtasks:\n")
                for subtask in self.subtasks:
                    file.write(f"- subtask{self.subtasks.index(subtask) + 1}:\n")
                    file.write(f"  - subtask_id: {subtask.id}\n")
                    file.write(f"  - subtask_name: {subtask.name}\n")
                    file.write(f"  - subtask_description: {subtask.description}\n")
                    file.write(f"  - subtask_requirements: {subtask.requirements}\n")
                    file.write(f"  - subtask_steps: {subtask.steps}\n")
                    file.write(f"  - subtask_depid: {subtask.depid}\n")
                    file.write(f"  - subtask_dep_by_id: {subtask.dependent_by_subtask_ids}\n")
                    file.write(f"  - subtask_script: {self.id}_subtask_{subtask.id:03}.py\n")
            self.logger.info(f"子任务信息已记录到: {file_path}")
        except Exception as e:
            self.logger.error(f"记录子任务信息失败: {e}")

    def run(self):
        """
        运行任务翻译器，处理所有子任务
        """
        self.logger.info("任务翻译器开始运行")
        for subtask in self.subtasks:
            self.logger.info(f"翻译子任务: {subtask}")
            self.translate_subtask()

        self.log_subtasks_info()
        self.logger.info("任务翻译器运行完成")
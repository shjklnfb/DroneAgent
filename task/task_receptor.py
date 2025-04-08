import os
import logging
import logging.handlers
from utils.id_generator import generate_random_id
from utils.log_configurator import setup_logger

'''
任务接收器
负责接收用户输入的指令。并利用语音识别支持语音输出。

输入：
输出：id，原始输入
'''

class TaskReceptor:
    def __init__(self):
        self.id = generate_random_id()  # 任务的唯一标识符
        self.input = None
        self.logger = setup_logger(self.id)

    def process_user_input(self, user_input):  # 修改函数名
        """
        处理原始用户输入并生成标准任务格式
        """
        self.logger.info(f"处理用户输入: {user_input}")
        return {
            # 'type': 'new_task',
            'task_id': f'{self.id}',
            'raw_input': user_input
        }

    def get_input_from_console(self):  # 修改函数名
        '''
        从控制台获取用户输入
        '''
        user_input = input("请输入任务指令：")
        self.logger.info(f"从控制台接收到输入: {user_input}")
        self.input = self.process_user_input(user_input)

    def get_input_from_voice(self):  # 修改函数名
        '''
        从语音输入获取用户输入
        '''
        self.logger.warning("语音输入功能尚未实现")
        print("暂未实现语音输入功能")

    def run(self):  # 修改函数名
        source = input("请选择输入方式 (console/voice): ")
        self.logger.info(f"用户选择的输入方式: {source}")
        if source == 'console':
            self.get_input_from_console()
        elif source == 'voice':
            self.get_input_from_voice()
        else:
            self.logger.error("无效的输入方式")
            print("无效的输入方式，请重新运行程序。")

        if self.input:
            self.logger.info(f"保存任务: {self.input}")
            print(f"保存任务: {self.input}")

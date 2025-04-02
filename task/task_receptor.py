import os
import logging
import logging.handlers
from utils.id_util import generate_random_id
from config.log_config import setup_logger
'''
任务接收器
负责接收用户输入的指令。并利用语音识别支持语音输出。
'''

class TaskReceptor:
    def __init__(self):
        self.id = generate_random_id()  # 任务的唯一标识符
        self.input = None
        self.logger = setup_logger(self.id)

    def process_input(self, user_input):
        """
        处理原始用户输入并生成标准任务格式
        """
        self.logger.info(f"处理用户输入: {user_input}")
        return {
            # 'type': 'new_task',
            'task_id': f'{self.id}',
            'raw_input': user_input
        }

    def get_console_input(self):
        '''
        从控制台获取用户输入
        '''
        user_input = input("请输入任务指令：")
        self.logger.info(f"从控制台接收到输入: {user_input}")
        self.input = self.process_input(user_input)

    def get_voice_input(self):
        '''
        从语音输入获取用户输入
        '''
        self.logger.warning("语音输入功能尚未实现")
        print("暂未实现语音输入功能")

    def run(self):
        source = input("请选择输入方式 (console/voice): ")
        self.logger.info(f"用户选择的输入方式: {source}")
        if source == 'console':
            self.get_console_input()
        elif source == 'voice':
            self.get_voice_input()
        else:
            self.logger.error("无效的输入方式")
            print("无效的输入方式，请重新运行程序。")

        if self.input:
            self.logger.info(f"保存任务: {self.input}")
            print(f"保存任务: {self.input}")

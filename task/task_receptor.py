import os
from utils.id_generator import generate_random_id
from utils.log_configurator import setup_task_logger

'''
任务接收器
负责接收用户输入的指令。并利用语音识别支持语音输出。

输入：
输出：id，原始输入
'''

class TaskReceptor:
    def __init__(self):
        # self.id = generate_random_id()  # 任务的唯一标识符
        self.id = 'task_16b0f122'
        self.raw_input = None
        self.input = None
        self.logger = setup_task_logger(self.id)

    def process_user_input(self, user_input):  # 修改函数名
        """
        处理原始用户输入并生成标准任务格式
        """
        self.logger.info(f"处理用户输入: {user_input}")
        # TODO: 将用户的输入转换为标准的任务格式
        return user_input.strip()  # 去除首尾空格

    def get_input_from_console(self):  # 修改函数名
        '''
        从控制台获取用户输入
        '''
        user_input = input("请输入任务指令：")
        self.raw_input = user_input
        self.logger.info(f"从控制台接收到输入: {user_input}")
        self.input = self.process_user_input(user_input)

    def get_input_from_voice(self):  # 修改函数名
        '''
        从语音输入获取用户输入
        '''
        self.logger.warning("语音输入功能尚未实现")
        print("暂未实现语音输入功能")

    def log_task_info(self, user_input, processed_input):
        """
        记录任务信息，包括id, 原始输入和规范后的输入，并保存到文件中
        """
        log_message = f"task_id: {self.id}\nraw_input: {user_input}\nprocessed_input: {processed_input}\n"
        self.logger.info("记录任务信息")
        
        # 将任务信息写入到scripts文件夹下以self.id为名称的文件夹中的task_info.txt文件
        scripts_folder = os.path.join(os.getcwd(), "scripts", self.id)
        os.makedirs(scripts_folder, exist_ok=True)  # 确保文件夹存在
        log_file_path = os.path.join(scripts_folder, "task_info.txt")
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_message)

    def run(self):  # 修改函数名
        self.logger.info("程序开始运行，任务接收器启动")
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
            self.log_task_info(self.raw_input, self.input)
            self.logger.info(f"保存任务: {self.input}")
            self.logger.info("任务接受器运行完成")
            self.process_user_input(self.input)  # 处理用户输入
            print(f"输入完成，保存任务: {self.input}")
            print("系统将继续运行，执行任务......")

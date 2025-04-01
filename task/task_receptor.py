from utils.id_util import generate_random_id
'''
任务接收器
负责接收用户输入的指令。并利用语音识别支持语音输出。
'''

class TaskReceptor:
    def __init__(self):
        self.id=generate_random_id()   # 任务的唯一标识符
        self.input = None

    def process_input(self, user_input):
        """
        处理原始用户输入并生成标准任务格式
        """
        return {
            'type': 'new_task',
            'task_id': f'task_{hash(user_input)}',
            'raw_input': user_input
        }

    def get_console_input(self):
        '''
        从控制台获取用户输入
        '''
        user_input = input("请输入任务指令：")
        self.input = self.process_input(user_input)

    def get_voice_input(self):
        '''
        从语音输入获取用户输入
        '''
        print("暂未实现语音输入功能")

    def run(self):
        source = input("请选择输入方式 (console/voice): ")
        if source == 'console':
            self.get_console_input()
        elif source == 'voice':
            self.get_voice_input()
        else:
            print("无效的输入方式，请重新运行程序。")

        if self.input:
            print(f"保存任务: {self.input}")

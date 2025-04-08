import time

"""
任务感知器
读取日志文件，检查无人机监控器数据，处理任务完成或错误的情况
"""
class TaskPerceptor:
    def __init__(self, scheduler):
        """
        初始化任务感知器。
        """
        self.scheduler = scheduler  # 任务调度器实例
        self.tasks = []

    def drone_perceptor_receiver(self):
        """
        检查无人机感知器的状态，处理任务完成或错误的情况

        :return: 任务完成/错误/执行中，原因
        """
        try:
            with open("mywebsocket/messages/message_scheduler.txt", "r", encoding="utf-8") as file:
                messages = file.readlines()
            # 处理读取的消息逻辑
            task_states = {}
            for message in messages:
                try:
                    # 提取JSON部分并解析
                    json_start = message.find("{")
                    json_end = message.rfind("}") + 1
                    if json_start == -1 or json_end == -1:
                        continue
                    log_data = eval(message[json_start:json_end])  # 使用eval解析JSON字符串
                    task = log_data.get("task")
                    state = log_data.get("state")
                    
                    if task not in task_states:
                        task_states[task] = {"states": [], "reasons": []}
                    
                    task_states[task]["states"].append(state)
                    task_states[task]["reasons"].append(log_data.get("reason", ""))
                except Exception as e:
                    print(f"解析消息时发生错误: {e}")
            
            # 分析任务状态
            for task, data in task_states.items():
                if "error" in data["states"]:
                    print(f"任务 {task} 出现错误: {data['reasons']}")
                    # TODO: 重新分解任务或处理错误
                elif data["states"][-1] == "finish" and "error" not in data["states"]:
                    print(f"任务 {task} 已完成")
                    # TODO: 更新依赖关系   出现多次执行
                    self.scheduler.update_dependencies(1)
        except FileNotFoundError:
            print("文件未找到: mywebsocket/messages/message_scheduler.txt")
        except Exception as e:
            print(f"读取文件时发生错误: {e}")

    def run(self):
        """
        运行任务感知器，持续检查无人机感知器状态。
        """
        while True:
            self.drone_perceptor_receiver()
            # 如果任务完成，更新依赖关系
            # 如果任务失败，重新分解任务
            time.sleep(5)  # 添加适当的间隔时间




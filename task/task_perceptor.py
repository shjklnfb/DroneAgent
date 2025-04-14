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
        self.finish_tasks = []

    def drone_perceptor_receiver(self):
        """
        检查无人机感知器的状态，处理任务完成或错误的情况

        :return: 任务完成/错误/执行中，原因
        """
        """
        一种消息时无人机感知器给调度器的定期汇报
        另一种消息是数据
        """
        try:
            with open("mywebsocket/messages/message_scheduler.txt", "r", encoding="utf-8") as file:
                messages = file.readlines()[-100:]  # 只读取最新的100行
            # 处理读取的消息逻辑
            task_states = {}
            for message in messages:
                # 提取JSON部分并解析
                json_start = message.find("{")
                json_end = message.rfind("}") + 1
                if json_start == -1 or json_end == -1:
                    continue
                try:
                    log_data = eval(message[json_start:json_end])  # 使用eval解析JSON字符串
                    task = log_data.get("task")
                    state = log_data.get("state")
                    
                    if not task or not state:  # 如果缺少必要字段，跳过
                        continue
                    
                    if task not in task_states:
                        task_states[task] = {"states": [], "reasons": []}
                    
                    task_states[task]["states"].append(state)
                    task_states[task]["reasons"].append(log_data.get("reason", ""))
                except:
                    continue  # 如果解析失败，跳过该消息
            
            # 分析任务状态
            for task, data in task_states.items():
                if "error" in data["states"]:
                    print("任务感知器：感知到错误")
                    # print(f"任务感知器：任务 {task} 出现错误: {data['reasons']}")
                    # TODO: 需要结束所有线程，重新分解任务
                    
                elif data["states"][-1] == "finish" and "error" not in data["states"]:
                    if task not in self.finish_tasks:  # 确保只处理一次
                        print(f"任务 {task} 已完成")
                        task_id= int(task.replace("subtask", ""))
                        self.scheduler.update_dependencies(task_id)
                        self.finish_tasks.append(task)  # 标记任务为已处理
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




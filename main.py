# from task.task_planner import TaskPlanner
from task.task_receptor import TaskReceptor
# from task.task_scheduler import TaskScheduler
# from task.task_translator import TaskTranslator

if __name__ == "__main__":
    # 任务接收器
    receptor = TaskReceptor()
    # 启动接收的方法
    receptor.run()
    # # 任务规划器, 任务规划器需要读取任务接收器的输入
    # planner = TaskPlanner(receptor.input)
    # # 规划，检查，初始化
    # planner.run()
    # # 任务翻译器
    # translator = TaskTranslator(planner.subtasks)
    # # 翻译,代码写到文件中
    # translator.run()
    # # 任务调度器
    # scheduler = TaskScheduler(translator.subtasks)
    # # 调度, 执行
    # scheduler.run()
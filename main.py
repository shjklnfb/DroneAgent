from task.task_planner import TaskPlanner
from task.task_receptor import TaskReceptor
from task.task_scheduler import TaskScheduler
from task.task_translator import TaskTranslator
from task.task_initializer import TaskInitializer
from task.task_perceptor import TaskExecutor

# 程序启动入口
if __name__ == "__main__":
    # 任务接收器
    receptor = TaskReceptor()
    # 启动接收的方法
    receptor.run()

    # 任务规划器, 任务规划器需要读取任务接收器的输入
    planner = TaskPlanner("task_16b0f122", "receptor.input")
    # 规划，检查，初始化
    planner.run()

    # 任务初始化器
    initializer = TaskInitializer("task_16b0f122", [{"device": "iris_0", "ip": "127.0.0.1", "port": 8080}], services=["云服务1", "云服务2"])
    # 初始化连接，仿真环境，云端资源
    initializer.run()

    # 任务翻译器
    translator = TaskTranslator("task_16b0f122", planner.subtasks)
    # 翻译,代码写到文件中
    translator.run()

    # 任务调度器
    scheduler = TaskScheduler("task_16b0f122", translator.subtasks, planner.drones)
    # 调度, 执行
    scheduler.run_centralized()
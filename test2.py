from task.task_receptor import TaskReceptor
from task.task_planner import TaskPlanner  # 假设 TaskPlanner 类在 task_planner.py 文件中
from task.task_initializer import TaskInitializer  # 假设 TaskInitializer 类在 task_initializer.py 文件中
from task.task_translator import TaskTranslator  # 假设 TaskTranslator 类在 task_translator.py 文件中
from task.task_scheduler import TaskScheduler  # 假设 TaskScheduler 类在 task_scheduler.py 文件中


# taskReceptor = TaskReceptor()
# taskReceptor.run()
# taskPlanner = TaskPlanner(taskReceptor.id, taskReceptor.input)
# taskPlanner.run()
# taskInitializer = TaskInitializer(taskReceptor.id, taskPlanner.devices, taskPlanner.services)
# taskInitializer.run()
# taskTranslator = TaskTranslator(taskReceptor.id, taskPlanner.subtasks)
# taskTranslator.run()


if __name__ == '__main__':
    subtask1_instance = SubTask(
        id=1,
        name='subtask1',
        description='子任务1：无人机1起飞到有利侦查位置，寻找到目标',
        depid=[],
        drone="iris_0",
        drone_ip="localhost",
        drone_port=8900,
        steps="无人机1起飞到有利侦查位置，寻找到目标",
        requirements={
        'interrupt_handling': True,
        'status_check_interval': 3,
        'position_accuracy': 0.5
        },
        services=[]
    )
    subtask2_instance = SubTask(
        id=2,
        name='subtask2',
        description='子任务2：无人机2起飞，飞行到无人机1返回的目标位置',
        depid=[1],
        drone="iris_1",
        drone_ip="localhost",
        drone_port=8901,
        steps="无人机2起飞，飞行到无人机1返回的目标位置",
        requirements={
        'interrupt_handling': True,
        'status_check_interval': 3,
        'position_accuracy': 0.5
        },
        services=[]
    )
    subtasks = [subtask1_instance, subtask2_instance]
    scheduler = TaskScheduler("task_16b0f122",subtasks,[{"drone":"iris_0","drone_ip":"localhost","drone_port":8900},{"drone":"iris_1","drone_ip":"localhost","drone_port":8901}])
    scheduler.send_taskscript(subtasks[0])
    print(scheduler.drone_connection.received_messages)
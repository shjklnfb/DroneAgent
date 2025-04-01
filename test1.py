import unittest
from repository import func_center
from task import task_planner
from task.task_receptor import TaskReceptor  # 假设 TaskReceptor 类在 task_receptor.py 文件中
from task.task_planner import TaskPlanner  # 假设 TaskPlanner 类在 task_planner.py 文件中
from task.task_scheduler import TaskScheduler  # 假设 TaskScheduler 类在 task_scheduler.py 文件中
from entity.entity import SubTask  # 假
import threading
import time
from mywebsocket.DroneClient import DroneClient
from mywebsocket.SchedulerServer import SchedulerServer

class TestTaskReceptor(unittest.TestCase):
    
    # 测试scheduler
    def test_1(self):
        subtask1_instance = SubTask(
        id=1,
        name='subtask1',
        description='子任务1：无人机1起飞到有利侦查位置，寻找到目标',
        depid=[],
        device='iris_0',
        steps=[
        {
            'type': 'takeoff',
            'params': {'retries': 5, 'sleep_duration': 15},
            'checks': ['interrupt', 'status']
        },
        ],
        requirements={
        'interrupt_handling': True,
        'status_check_interval': 3,
        'position_accuracy': 0.5
        }
    )
        subtasks = [subtask1_instance]
        scheduler = TaskScheduler("task_16b0f122",subtasks,["iris_0"])
        scheduler.run()




if __name__ == '__main__':
    import rospy
    rospy.init_node("node",anonymous=True)
    unittest.main()
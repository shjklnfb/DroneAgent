import unittest
from repository import lib_center
from task import task_planner
from task.task_receptor import TaskReceptor  # 假设 TaskReceptor 类在 task_receptor.py 文件中
from task.task_planner import TaskPlanner  # 假设 TaskPlanner 类在 task_planner.py 文件中
from task.task_scheduler import TaskScheduler  # 假设 TaskScheduler 类在 task_scheduler.py 文件中
from entity.entity import SubTask  # 假
import threading
import time


class TestTaskReceptor(unittest.TestCase):
    
    # 测试scheduler
    def test_1(self):
        subtask1_instance = SubTask(
        id=1,
        name='subtask1',
        description='子任务1：无人机1起飞到有利侦查位置，寻找到目标',
        depid=[],
        drone="iris_0",
        drone_ip="127.0.0.1",
        drone_port=8900,
        steps="无人机1起飞到有利侦查位置，寻找到目标",
        requirements={
        'interrupt_handling': True,
        'status_check_interval': 3,
        'position_accuracy': 0.5
        }
    )
        subtask2_instance = SubTask(
        id=2,
        name='subtask2',
        description='子任务2：无人机2起飞，飞行到无人机1返回的目标位置',
        depid=[1],
        drone="iris_1",
        drone_ip="127.0.0.1",
        drone_port=8901,
        steps="无人机2起飞，飞行到无人机1返回的目标位置",
        requirements={
        'interrupt_handling': True,
        'status_check_interval': 3,
        'position_accuracy': 0.5
        }
    )
        subtasks = [subtask1_instance, subtask2_instance]
        scheduler = TaskScheduler("task_16b0f122",subtasks,[{"drone":"iris_0","drone_ip":"localhost","drone_port":8900},{"drone":"iris_1","drone_ip":"localhost","drone_port":8901}])
        scheduler.run_centralized()




if __name__ == '__main__':
    import rospy
    rospy.init_node("node",anonymous=True)
    unittest.main()
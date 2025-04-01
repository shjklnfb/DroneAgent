import threading
import time
import os
from datetime import datetime  # 确保 datetime 已导入
import rospy
from mavros_msgs.msg import State
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, CameraInfo
from mavros_msgs.srv import CommandBool
from sensor_msgs.msg import Imu  # Add this import
from cv_bridge import CvBridge
import cv2  # 确保 cv2 已导入

'''
无人机监控器类，用于监控无人机的状态、位置、速度、图像数据等信息。
使用多线程方式实现，每个无人机对应一个监控器实例。
'''

# 无人机监控器类
class DroneMonitor(threading.Thread):
    def __init__(self, drone_id):
        super().__init__()
        self.drone_id = drone_id
        self.data = {
            'state': None,
            'position': None,
            'velocity': None,
            'image': None,
            'depth_image': None,
            'camera_info': None,
            'imu_data': None,
            'time': None,
            'other': None
        }
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            self.monitor_drone()

    def state_cb(self, state):
        self.data['state'] = state


    def local_pos_cb(self, odom):
        self.data['position'] = odom.pose.pose.position
        self.data['velocity'] = odom.twist.twist.linear

    def image_cb(self, image):
        self.data['image'] = CvBridge().imgmsg_to_cv2(image, "bgr8")  # 转换为OpenCV格式
        

    def depth_image_cb(self, image):
        self.data['depth_image'] = CvBridge().imgmsg_to_cv2(image, "32FC1")  # 深度图像

    def depth_camera_info_cb(self, camera_info):
        self.data['camera_info'] = camera_info
        
    def imu_data_cb(self, imu_data):
        self.data['imu_data'] = {
            'orientation': imu_data.orientation,
            'angular_velocity': imu_data.angular_velocity,
            'linear_acceleration': imu_data.linear_acceleration
        }  # 存储IMU数据

    # 监控无人机
    def monitor_drone(self):
        # rospy.init_node(f'drone_monitor_{self.drone_id}', anonymous=True)
        prefix = f'{self.drone_id}'
        
        state_sub = rospy.Subscriber(f'/{prefix}/mavros/state', State, self.state_cb)
        local_pos_sub = rospy.Subscriber(f'/{prefix}/mavros/local_position/odom', Odometry, self.local_pos_cb)
        image_sub = rospy.Subscriber(f'/{prefix}/realsense/depth_camera/color/image_raw', Image, self.image_cb)
        depth_image_sub = rospy.Subscriber(f'/{prefix}/realsense/depth_camera/depth/image_raw', Image, self.depth_image_cb)
        depth_camera_info_sub = rospy.Subscriber(f'/{prefix}/realsense/depth_camera/depth/camera_info', CameraInfo, self.depth_camera_info_cb)
        imu_data_sub = rospy.Subscriber(f'/{prefix}/mavros/imu/data', Imu, self.imu_data_cb)
        arming_client = rospy.ServiceProxy(f'/{prefix}/mavros/cmd/arming', CommandBool)
        
        # 每秒执行一次，将无人机的状态、位置、速度、图像数据等信息存储到共享数据中
        rate = rospy.Rate(1)  # 1 Hz
        while not rospy.is_shutdown():
            rate.sleep()

    def stop(self):
        self.stop_event.set()



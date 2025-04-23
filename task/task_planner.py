import yaml
from models.model_functions import *
from utils.log_configurator import setup_task_logger
import os

'''
任务规划器
负责将用户输入的任务进行分解，生成子任务列表，并验证子任务之间的依赖关系。
输入：用户任务，id
输出：子任务列表，无人机列表
'''
class TaskPlanner:
    def __init__(self, id, task):
        self.id = id
        self.task = task # 用户输入的任务
        self.subtasks = []  # 规划后的子任务列表
        self.devices = []  # 本次任务需要的无人机列表
        self.services = []  # 本次任务需要的服务列表
        self.logger = setup_task_logger(self.id) # 日志记录器

    def decompose_task(self, task):
        """
        根据prompt和task,调用deepseekr1，生成任务分解方案
        在这里不仅需要分解任务，需要给出依赖，被依赖，子任务的要求，以及本次任务需要的软件服务
        输入格式: 任务描述
        返回格式: [subtask1,subtask2...,subtaskN]
        """
        self.logger.info("开始任务分解")
        try:
            # 读取 YAML 文件
            with open('resource/prompt.yaml', 'r', encoding='utf-8') as file:
                yaml_data = yaml.safe_load(file)

            # 获取配置文件中的提示词 task_decompose 字段
            task_decompose = yaml_data.get('task_decompose', '')
            # 将 task 填充到 user_task
            prompt = task_decompose.format(user_task=task)
            
            # 调用models中的接口
            self.subtasks = func_task_decomposition(prompt)
            self.logger.info(f"任务分解完成: {self.subtasks}")
        except Exception as e:
            self.logger.error(f"任务分解失败: {e}")
            raise
        return self.subtasks

    def assign_drones(self,subtasks):
        """
        为每个子任务分配无人机设备
        使用大模型，从无人机库中选择，resource/drone.yaml
        """
        self.logger.info("开始为子任务分配无人机设备")
        try:
            for subtask in self.subtasks:
                # 读取 YAML 文件
                with open('resource/prompt.yaml', 'r', encoding='utf-8') as file:
                    yaml_data = yaml.safe_load(file)
                
                # 获取配置文件中的提示词 assign_drone 字段
                prompt = yaml_data.get('assign_drone', '')
                # 将 task 填充到 user_task
                prompt = prompt.format()
                # 调用models中的接口
                assigned_drone = func_assign_drone(prompt)
                subtask.device = assigned_drone  # 为子任务分配无人机
                self.logger.info(f"子任务 {subtask.name} 分配到无人机: {assigned_drone}")
        except Exception as e:
            self.logger.error(f"无人机分配失败: {e}")
            raise

    def generate_steps(self,subtasks):
        """
        为每个子任务生成执行步骤
        """
        self.logger.info("开始为子任务生成执行步骤")
        try:
            for subtask in self.subtasks:
                # 读取 YAML 文件
                with open('resource/prompt.yaml', 'r', encoding='utf-8') as file:
                    yaml_data = yaml.safe_load(file)
                
                # 获取配置文件中的提示词 generate_steps 字段
                prompt = yaml_data.get('generate_steps', '')
                # 将 task 填充到 user_task
                prompt = prompt.format()
                # 调用models中的接口
                steps = func_generate_steps(prompt)
                subtask.steps = steps  # 为子任务添加步骤
                self.logger.info(f"子任务 {subtask.name} 的执行步骤生成完成: {steps}")
        except Exception as e:
            self.logger.error(f"生成子任务执行步骤失败: {e}")
            raise

    def record_drone_info(self):
        """
        将分配到的无人机信息追加到文件，并分析每个无人机上的任务
        """
        self.logger.info("开始导出无人机信息")
        try:
            # 定义输出文件路径
            output_dir = f'scripts/{self.id}'
            output_file = f'{output_dir}/task_info.txt'

            # 创建文件夹（如果不存在）
            os.makedirs(output_dir, exist_ok=True)

            # 准备无人机信息
            drones = []
            for subtask in self.subtasks:
                device_info = subtask.device
                drone_entry = next((drone for drone in drones if drone['drone'] == device_info['drone']), None)
                if not drone_entry:
                    drone_entry = {
                        'drone': device_info['drone'],
                        'drone_ip': device_info['drone_ip'],
                        'drone_port': device_info['drone_port'],
                        'drone_capability': [],
                        'drone_subtasks': []
                    }
                    drones.append(drone_entry)
                drone_entry['drone_subtasks'].append({
                    subtask.name: subtask.description
                })

            resources = {
                'drones': drones
            }

            # 如果文件已存在，读取现有内容并合并
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as file:
                    existing_data = yaml.safe_load(file) or {}
                existing_drones = existing_data.get('drones', [])

                # 合并 drones 信息
                for drone in drones:
                    if drone not in existing_drones:
                        existing_drones.append(drone)

                resources['drones'] = existing_drones

            # 如果文件已存在，追加无人机信息到文件的下一行
            with open(output_file, 'a', encoding='utf-8') as file:
                yaml.dump(resources, file, allow_unicode=True)

            self.logger.info(f"无人机信息已追加到 {output_file}")
        except Exception as e:
            self.logger.error(f"导出无人机信息失败: {e}")
            raise

    def run(self):
        self.logger.info("任务规划器开始运行")
        try:
            # 进行任务分解
            subtasks = self.decompose_task(self.task)
            # # 为每个子任务分配无人机设备
            # subtasks = self.assign_drones(subtasks) 
            # # 为每个子任务生成执行步骤  
            # subtasks = self.generate_steps(subtasks)

            # 从subtasks列表中获取devices列表, 列表中有型号ip和port
            for subtask in subtasks:
                device_info = subtask.device  # 获取 device 属性
                if device_info not in self.devices:
                    self.devices.append(device_info)
            self.logger.info(f"获取到的无人机列表: {self.devices}")

            # 从subtasks列表中获取services列表
            for subtask in subtasks:
                for service_info in subtask.services:  # 遍历 services 列表
                    if service_info not in self.services:
                        self.services.append(service_info)
            self.logger.info(f"获取到的服务列表: {self.services}")

            self.record_drone_info()  # 记录无人机和服务信息

            self.logger.info("任务规划器运行完成")
        except Exception as e:
            self.logger.error(f"任务规划器运行失败: {e}")
            raise

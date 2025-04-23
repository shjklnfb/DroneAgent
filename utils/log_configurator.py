import os
import logging

_loggers = {"task": {}, "executor": {}, "connect":{}, "script":{} }  # 用于存储单例日志记录器

def setup_task_logger(filename):
    """
    配置task.log日志记录器（单例模式）
    """
    if filename not in _loggers["task"]:
        log_dir = os.path.join("log", filename)
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "task.log")

        # 使用FileHandler并设置编码为utf-8，避免中文乱码
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        logger = logging.getLogger(f"{__name__}.{filename}.task")
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.propagate = False
        _loggers["task"][filename] = logger

    return _loggers["task"][filename]


def setup_drone_logger(filename, drone):
    """
    配置日志记录器（单例模式）
    针对每个drone创建单独的日志文件
    """
    # 修改键名格式为"filename_drone"以确保每个drone都有唯一的logger
    key = f"{filename}_{drone}"
    
    if key not in _loggers["executor"]:
        log_dir = os.path.join("log", filename)
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"executor_{drone}.log")

        # 使用FileHandler并设置编码为utf-8，避免中文乱码
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        logger = logging.getLogger(f"{__name__}.{filename}.executor.{drone}")
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.propagate = False
        _loggers["executor"][key] = logger

    return _loggers["executor"][key]

def setup_connect_logger(filename):
    """
    配置日志记录器（单例模式）
    """
    if filename not in _loggers["connect"]:
        log_dir = os.path.join("log", filename)
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "connect.log")

        # 使用FileHandler并设置编码为utf-8，避免中文乱码
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        logger = logging.getLogger(f"{__name__}.{filename}.connect")
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.propagate = False
        _loggers["connect"][filename] = logger

    return _loggers["connect"][filename]

def setup_script_logger(filename, script_name):
    """
    配置日志记录器（单例模式）
    """
    key = f"{filename}_{script_name}"
    
    if key not in _loggers["script"]:
        log_dir = os.path.join("log", filename)
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"script_{script_name}.log")

        # 使用FileHandler并设置编码为utf-8，避免中文乱码
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        logger = logging.getLogger(f"{__name__}.{filename}.script.{script_name}")
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.propagate = False
        _loggers["script"][key] = logger

    return _loggers["script"][key]
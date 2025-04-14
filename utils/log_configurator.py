import os
import logging

_loggers = {"task": {}, "executor": {}, "connect":{}}  # 用于存储单例日志记录器

def setup_logger(filename):
    """
    配置日志记录器（单例模式）
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

def setup_logger_exec(filename):
    """
    配置日志记录器（单例模式）
    """
    if filename not in _loggers["executor"]:
        log_dir = os.path.join("log", filename)
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "executor.log")

        # 使用FileHandler并设置编码为utf-8，避免中文乱码
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        logger = logging.getLogger(f"{__name__}.{filename}.executor")
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.propagate = False
        _loggers["executor"][filename] = logger

    return _loggers["executor"][filename]

def setup_logger_connect(filename):
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
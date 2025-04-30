import pickle
import json
import types
from functools import partial

class SerializableNamespace:
    """
    用于创建可序列化命名空间的辅助类，将不可序列化的对象包装为可序列化形式
    """
    def __init__(self, original_dict):
        self.serializable_dict = {}
        
        # 处理原始字典中的每个元素
        for key, value in original_dict.items():
            if isinstance(value, (int, float, str, bool, list, dict, tuple)):
                # 基本类型可直接使用
                self.serializable_dict[key] = value
            elif hasattr(value, '__dict__') and not callable(value):
                # 对象类型，尝试转换为字典
                try:
                    self.serializable_dict[key] = vars(value)
                except:
                    self.serializable_dict[key] = str(value)
            elif callable(value) and not key.startswith('__'):
                # 可调用对象(函数)，保存函数名
                self.serializable_dict[key] = f"FUNCTION:{value.__name__}"
            else:
                # 其他不可序列化对象，转为字符串
                self.serializable_dict[key] = f"OBJECT:{str(value)}"
    
    def get_dict(self):
        return self.serializable_dict

def prepare_for_process(namespace_dict):
    """
    准备传递给进程的命名空间字典，处理不可序列化对象
    
    Args:
        namespace_dict: 原始命名空间字典
        
    Returns:
        dict: 可序列化的命名空间字典
    """
    serializable_namespace = SerializableNamespace(namespace_dict)
    return serializable_namespace.get_dict()

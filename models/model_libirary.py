class ModelLibrary:
    def __init__(self):
        # 初始化模型库，存储多云服务的配置信息
        self.services = {
            "yolov8": {
                "ip": "47.93.46.144",
                "port": 8000,
                "description": "YOLO object detection service",
                "apikey": "your-yolo-apikey"
            },
            "qwen-vl-plus": {
                "domain": "large-model.example.com",
                "port": 443,
                "description": "Large language model service",
                "apikey": "sk-d34cba22d2a04a5c8c191f082106d07e"
            },
            "qwen-plus": {
                "domain": "qwen.example.com",
                "port": 443,
                "description": "Qwen large language model service",
                "apikey": "sk-d34cba22d2a04a5c8c191f082106d07e"
            },
            "deepseek": {
                "domain": "deepseek.example.com",
                "port": 443,
                "description": "Deepseek task decomposition model service",
                "apikey": "sk-d34cba22d2a04a5c8c191f082106d07e"
            }
            # 可以继续添加其他服务
        }

    def get_service_info(self, service_name):
        """
        获取指定服务的配置信息。
        :param service_name: 服务名称，例如 'yolo' 或 'large_model'
        :return: 包含服务信息的字典，如果服务不存在则返回 None
        """
        return self.services.get(service_name)

    def deploy_service(self, service_name):
        """
        模拟部署服务并返回服务的资源信息。
        :param service_name: 服务名称
        :return: 部署的服务资源信息
        """
        print(f"部署服务: {service_name}")

    def service_exists(self, service_name):
        """
        检查指定服务是否存在于模型库中。
        :param service_name: 服务名称
        :return: 如果服务存在返回 True，否则返回 False
        """
        return service_name in self.services
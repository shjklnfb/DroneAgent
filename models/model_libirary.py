import yaml

class ModelLibrary:
    def __init__(self):
        # 从 resource/service.yaml 文件加载服务配置
        with open("./resource/service.yaml", "r", encoding="utf-8") as file:
            self.services = yaml.safe_load(file)

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
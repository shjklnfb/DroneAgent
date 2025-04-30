from flask import Flask, request, jsonify
import threading
import json
import sys
import os

# 添加项目根目录到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EmergencyAPI:
    """
    提供API接口接收突发任务请求并转发给任务调度器
    """
    def __init__(self, scheduler, host='0.0.0.0', port=5000):
        self.app = Flask(__name__)
        self.scheduler = scheduler
        self.host = host
        self.port = port
        self.server_thread = None
        
        # 注册API路由
        self.register_routes()
    
    def register_routes(self):
        """注册API路由"""
        
        @self.app.route('/emergency', methods=['POST'])
        def handle_emergency():
            """
            接收突发任务请求
            """
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({"success": False, "message": "请求缺少JSON数据"}), 400
                
                # 验证必需字段
                required_fields = ["drone_id", "code"]
                for field in required_fields:
                    if field not in data:
                        return jsonify({"success": False, "message": f"缺少必需字段 {field}"}), 400
                
                # 准备突发任务信息
                emergency_info = {
                    "drone_id": data["drone_id"],
                    "priority": data.get("priority", 1),  # 默认优先级为1
                    "restore": data.get("restore", True),  # 默认完成后恢复原任务
                    "subtask": None, # 这里可以根据需要设置子任务,暂不使用，简化测试
                    "code": data["code"]
                }
                
                # 将请求转发给调度器处理
                success = self.scheduler.handle_emergency(emergency_info)
                
                if success:
                    return jsonify({"success": True, "message": "突发任务已发送"}), 200
                else:
                    return jsonify({"success": False, "message": "发送突发任务失败"}), 500
                
            except Exception as e:
                return jsonify({"success": False, "message": f"处理请求时出错: {str(e)}"}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """健康检查接口"""
            return jsonify({"status": "ok"}), 200
    
    def start(self):
        """启动API服务器"""
        def run_app():
            self.app.run(host=self.host, port=self.port, debug=False)
        
        self.server_thread = threading.Thread(target=run_app)
        self.server_thread.daemon = True  # 设置为守护线程，主程序退出时自动退出
        self.server_thread.start()
        print(f"突发任务API服务器已启动，监听地址: {self.host}:{self.port}")
    


# curl -X POST http://localhost:5000/emergency \
#   -H "Content-Type: application/json" \
#   -d '{
#     "drone_id": "iris_0",
#     "priority": 3,
#     "restore": true,
#     "code": "def emergency_task(id, drone, monitor, p2p_node, dynamic_data):\n    print(\"执行紧急返回任务\")\n    import time\n    for i in range(5):\n        print(f\"返回中... {i+1}/5\")\n        time.sleep(1)\n    return \"紧急返回完成\""
#   }'

# curl -X POST http://localhost:5000/emergency \
#   -H "Content-Type: application/json" \
#   -d '{
#     "drone_id": "iris_0",
#     "priority": 5,
#     "restore": true,
#     "code": "from repository.lib_drone import *\nfrom repository.lib_center import *\nimport inspect\nimport time\n\ndef emergency_task(id, drone, dronemonitor, p2p_node, dynamic_data):\n    func_name = inspect.currentframe().f_code.co_name\n    fly_to(drone, -5,-8,7)\n    time.sleep(10)"
#   }'

# from repository.lib_drone import *
# from repository.lib_center import *
# import inspect
# import time

# def emergency_task(id, drone, dronemonitor, p2p_node, dynamic_data):
#     func_name = inspect.currentframe().f_code.co_name
#     fly_to(drone, -5,-8,7)
#     time.sleep(10) 


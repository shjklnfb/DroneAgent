import rospy
import sys
from geometry_msgs.msg import PoseStamped

def send_spiral_command(prefix, radius, step, duration):
    if step <= 0 or radius <= 0 or duration <= 0:
        rospy.logerr("Invalid parameters: radius, step, and duration must be positive values.")
        return

    node_name = f'{prefix}_spiral_search_command_publisher'
    # rospy.init_node(node_name, anonymous=True)
    command_topic = f'/{prefix}/drone/spiral_search_command'
    command_pub = rospy.Publisher(command_topic, PoseStamped, queue_size=100)

    rospy.sleep(1)
    # 创建一个 PoseStamped 消息
    command = PoseStamped()
    command.pose.position.x = radius  # 初始半径
    command.pose.position.y = step    # 每步角度增量
    command.pose.position.z = duration  # 持续时间
    command.header.stamp = rospy.Time.now()
    rospy.loginfo(f"Publishing spiral search command: radius={radius}, step={step}, duration={duration}")
    command_pub.publish(command)

    rospy.loginfo("Spiral search command published")

if __name__ == '__main__':
    try:
        # 获取命令行参数
        if len(sys.argv) != 5:
            rospy.logerr("Usage: command_spiral.py prefix radius step duration")
            sys.exit(1)

        prefix = sys.argv[1]
        radius = float(sys.argv[2])
        step = float(sys.argv[3])
        duration = float(sys.argv[4])
        
        send_spiral_command(prefix, radius, step, duration)  # 发布螺旋搜索指令

    except rospy.ROSInterruptException:
        pass

from src.paths import get_trajectory_dir
from src.ui import AgentUI

current_version = "0.1.0"

valid_msg_types = {"message", "broadcast", "shutdown_request",
    "shutdown_response", "plan_approval_response"}

dangerous_commands = [
    "rm -rf",
    "sudo",
    "shutdown",
    "poweroff",
    "reboot",
    "> /dev"
]

slash_commands = {
    "/init": "初始化项目",
    "/compact": "压缩上下文",
    "/status": "显示当前会话的状态信息"
}

ui = AgentUI(record=False, version=current_version, trajectory_dir=get_trajectory_dir())

max_text_length = 50000
token_threshold = 128*1024
max_retry_num = 2

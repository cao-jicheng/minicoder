from __future__ import annotations

from src.ui import AgentUI

current_version = "0.1.0"

dangerous_commands = [
    "rm -rf",
    "dd if=/dev/zero",
    "mkfs",
    "sudo",
    "chmod",
    "chown",
    "passwd",
    "crontab",
    "wget",
    ":(){ :|:& };:",
    "/dev",
]

slash_commands = {
    "/help": "显示帮助信息",
    "/init": "初始化项目，生成 CLAUDE.md 文件",
    "/status": "显示当前会话的状态信息",
    "/prompt": "显示系统提示词",
    "/permission": "显示或设置权限模式（Default、Auto、Plan）",
    "/tools": "列出已安装的工具",
    "/skills": "列出已安装的技能",
    "/compact": "手动执行上下文压缩",
}

ui = AgentUI(record=False, version=current_version)

# 工具输出结果的最大字符长度
max_output_length = 50000
# 大模型上下文窗口的最大tokens数量
max_context_tokens = 100*1000
# 大模型API调用最多重试次数
max_retry_num = 2


from __future__ import annotations

from src.ui import AgentUI

current_version = "1.0.0"

dangerous_commands = (
    "rm -rf",
    "dd if=/dev/zero",
    "mkfs",
    "sudo",
    "chmod",
    "chown",
    "passwd",
    "crontab",
    "wget",
    "shutdown",
    "poweroff",
)

glob_ignored = (
    ".git",
    ".svn",
    ".vscode",
    ".DS_Store",
    ".venv",
    ".cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "site-packages",
    "__pycache__",
)

llm_models = (
    "Pro/zai-org/GLM-5.1",
    "Pro/MiniMaxAI/MiniMax-M2.5",
    "Pro/moonshotai/Kimi-K2.5",
    "Pro/deepseek-ai/DeepSeek-V3.2",
    "Custom",
)

slash_commands = {
    "/help": "显示帮助信息",
    "/init": "初始化项目，生成 CLAUDE.md 文件",
    "/status": "显示当前会话的状态信息",
    "/prompt": "显示系统提示词",
    "/messages": "显示最近10条会话消息",
    "/model": "更换大语言模型（目前只能从 Siliconflow 系列模型中选择）",
    "/permission": "设置权限模式（Default、Auto、Plan）",
    "/tools": "列出已安装的工具",
    "/skills": "列出已安装的技能",
    "/memory": "列出已保存的记忆",
    "/compact": "手动执行上下文压缩",
    "/clear": "清空上下文中所有的消息",
}

ui = AgentUI(record=False, version=current_version)

# 工具输出结果的最大字符长度
max_output_length = 30000
# 大模型上下文窗口的最大tokens数量
max_context_tokens = 100*1000
# 主智能体最大循环次数
max_agent_rounds = 50
# 子智能体最大循环次数
max_subagent_rounds = 20
# 记忆条目的最大保存数量
max_memory_entities = 200

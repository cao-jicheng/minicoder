import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 项目根目录
def get_project_root() -> Path:
    env_dir = os.getenv("PROJECT_ROOT")
    project_root = Path(env_dir) if env_dir else Path.home() / ".minicoder"
    project_root.mkdir(parents=True, exist_ok=True)
    return project_root.resolve()

# 用于存放技能文件
def get_skills_dir() -> Path:
    skills_dir = get_project_root() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir.resolve()

# 用于存放用户和编程助手交互过程的轨迹
def get_trajectory_dir() -> Path:
    trajectory_dir = get_project_root() / ".trajectory"
    trajectory_dir.mkdir(parents=True, exist_ok=True)
    return trajectory_dir.resolve()

# 用于存放上下文压缩前消息列表的副本
def get_transcripts_dir() -> Path:
    transcripts_dir = get_project_root() / ".transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    return transcripts_dir.resolve()

# 用于存放调用工具后产生的大尺寸文件
def get_persistence_dir() -> Path:
    persistence_dir = get_project_root() / ".persistence"
    persistence_dir.mkdir(parents=True, exist_ok=True)
    return persistence_dir.resolve()

# 用于存放记忆文件
def get_memory_dir() -> Path:
    memory_dir = get_project_root() / ".memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir.resolve()

# 获取权限模式
def get_permission_mode() -> str:
    env = os.getenv("PERMISSION_MODE")
    return env if env in ["Default", "Auto", "Plan"] else "Default"

# 是否允许运行子智能体
def allow_subagent() -> bool:
    allow = os.getenv("ALLOW_SUBAGENT")
    return True if allow == "true" else False

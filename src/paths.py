import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_project_root() -> Path:
    env_dir = os.getenv("PROJECT_ROOT")
    project_root = Path(env_dir) if env_dir else Path.home() / ".minicoder"
    project_root.mkdir(parents=True, exist_ok=True)
    return project_root.resolve()

def get_skills_dir() -> Path:
    skills_dir = get_project_root() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir.resolve()

def get_trajectory_dir() -> Path:
    trajectory_dir = get_project_root() / "trajectory"
    trajectory_dir.mkdir(parents=True, exist_ok=True)
    return trajectory_dir.resolve()

def get_transcripts_dir() -> Path:
    transcripts_dir = get_project_root() / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    return transcripts_dir.resolve()

def get_permission_mode() -> str:
    env = os.getenv("PERMISSION_MODE")
    return env if env in ["Default", "Auto", "Plan"] else "Default"

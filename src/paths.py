import os
from pathlib import Path
from dotenv import load_dotenv

def get_project_root() -> Path:
    load_dotenv()
    env_dir = os.getenv("PROJECT_ROOT")
    project_root = Path(env_dir) if env_dir else Path.home() / ".minicoder"
    return project_root.resolve()

def get_skills_dir() -> Path:
    skills_dir = get_project_root() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir

def get_trajectory_dir() -> Path:
    trajectory_dir = get_project_root() / "trajectory"
    trajectory_dir.mkdir(parents=True, exist_ok=True)
    return trajectory_dir

def get_transcripts_dir() -> Path:
    transcripts_dir = get_project_root() / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    return transcripts_dir
import os
from dotenv import load_dotenv

load_dotenv()

llm_model_name = os.getenv("LLM_MODEL_NAME", "Pro/deepseek-ai/DeepSeek-V3.2")
llm_base_url = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
llm_api_key = os.getenv("LLM_API_KEY", "sk-xxx")

project_root = os.getenv("PROJECT_ROOT", "./project")

dangerous_commands = [
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "> /dev/"
]

max_text_length = 50000


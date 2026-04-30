import os
import time
import random
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from typing import List, Dict, Optional
from rich.status import Status

def backoff_delay(attempt: int) -> float:
    """带抖动的指数级回退延迟算法：base * 2^attempt + random(0, 1)"""
    delay = min(1.0 * (2 ** attempt), 30.0)
    jitter = random.uniform(0, 1)
    return delay + jitter

class OpenAILLM:
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        ):
        load_dotenv()
        self.model = model or os.getenv("LLM_MODEL", "Pro/MiniMaxAI/MiniMax-M2.5")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.provider = self._detect_provider()
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=30
        )
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_hit_tokens = 0
        self.cache_miss_tokens = 0

    def _detect_provider(self) -> str:
        if "api.siliconflow.cn" in self.base_url:
            return "SiliconFlow"
        elif "api.deepseek.com" in self.base_url:
            return "DeepSeek"
        elif "dashscope.aliyuncs.com" in self.base_url:
            return "Qwen"
        elif "localhost:11434" in self.base_url:
            return "Ollama"
        else:
            return "Unknown"

    def get_provider(self) -> str:
        return f"{self.provider}:{self.model}"
    
    def clear_usage(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_hit_tokens = 0
        self.cache_miss_tokens = 0
    
    def reset_model(self, model_name: str):
        self.model = model_name
        self.clear_usage()

    def invoke(self, prompts: str|List, max_retry: int=2, **kwargs) -> Dict:
        messages = [{"role": "user", "content": prompts}] if isinstance(prompts, str) else prompts
        retry_num = 0
        error_reason = ""
        generate_ok = False
        while retry_num <= max_retry:
            # 延迟后重试，延迟时间随重试次数指数级增长（最长不超过30秒）
            time.sleep(backoff_delay(retry_num))
            info = f"第 {retry_num} 次重试" if retry_num > 0 else "正在调用"
            try:
                print() # 空一行，便于终端美观显示
                with Status(status=f"{info} {self.get_provider()} ...") as status:
                    status.start()
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        **kwargs,
                    )
                generate_ok = True
            except Exception as e:
                error_reason = str(e)
                retry_num += 1
            if generate_ok:
                break
        # 多次重试后仍然失败
        if not generate_ok:
            return {
                "content": f"大模型调用已重试 {max_retry} 次，仍然失败，原因是 {error_reason}",
                "finish_reason": "error",
            }
        # 累计本次调用的 token 使用量          
        self.input_tokens += int(response.usage.prompt_tokens)
        self.output_tokens += int(response.usage.completion_tokens)
        # 有些 LLM 提供商不返回 cache hit/miss 的统计数据，需要在此检测是否存在相关字段，避免报错
        if hasattr(response.usage, "prompt_cache_hit_tokens"):
            self.cache_hit_tokens += int(response.usage.prompt_cache_hit_tokens)
        if hasattr(response.usage, "prompt_cache_miss_tokens"):
            self.cache_miss_tokens += int(response.usage.prompt_cache_miss_tokens)
        tool_calls = []
        if response.choices[0].finish_reason == "tool_calls":
            tool_calls = [(t.id, t.function.name, t.function.arguments) for t in response.choices[0].message.tool_calls]
        return {
            "content": response.choices[0].message.content,
            "finish_reason": response.choices[0].finish_reason, # 可选取值有：stop、eos、length、tool_calls
            "tool_calls": tool_calls,
            "context_tokens": int(response.usage.prompt_tokens) + int(response.usage.completion_tokens)
        }


if __name__ == "__main__":
    my_llm = OpenAILLM()
    my_llm.invoke("介绍一下你自己")

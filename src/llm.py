import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Optional
from rich.status import Status

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
    
    def change_model(model_name: str):
        self.model = model_name
        self.clear_usage()

    def invoke(self, prompts: str|List, **kwargs) -> Dict:
        messages = [{"role": "user", "content": prompts}] if isinstance(prompts, str) else prompts
        try:
            with Status(status=f"调用 {self.get_provider()} ...") as status:
                status.start()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **kwargs,
                )
            self.input_tokens += int(response.usage.prompt_tokens)
            self.output_tokens += int(response.usage.completion_tokens)
            self.cache_hit_tokens += int(response.usage.prompt_cache_hit_tokens)
            self.cache_miss_tokens += int(response.usage.prompt_cache_miss_tokens)
            tool_calls = []
            if response.choices[0].finish_reason == "tool_calls":
                tool_calls = [(t.function.name, t.function.arguments) for t in response.choices[0].message.tool_calls]
            return {
                "content": response.choices[0].message.content,
                "finish_reason": response.choices[0].finish_reason, # 可选取值有：stop、eos、length、tool_calls
                "tool_calls": tool_calls,
            }
        except Exception as e:
            return {
                "content": f"大模型调用失败 {e}",
                "finish_reason": "error",
            }


if __name__ == "__main__":
    llm = OpenAILLM()
    response = llm.invoke("介绍一下你自己")
    print(response)
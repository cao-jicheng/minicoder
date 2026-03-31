from openai import OpenAI
from typing import List, Dict, Optional
from config import llm_model_name, llm_base_url, llm_api_key

class OpenAILLM:
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
        ):
        self.model = model or llm_model_name
        self.base_url = base_url or llm_base_url
        self.api_key = api_key or llm_api_key
        self.provider = self._auto_detect_provider()
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=30
        )

    def _auto_detect_provider(self) -> str:
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

    def invoke(self, prompts: List|str, **kwargs) -> Dict:
        messages = [{"role": "user", "content": prompts}] if isinstance(prompts, str) else prompts
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs,
            )
            return {
                "content": response.choices[0].message.content,
                # finish_reason 可选取值有：stop、eos、length、tool_calls
                "finish_reason": response.choices[0].finish_reason,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        except Exception as e:
            return {
                "content": f"大模型调用失败：{e}",
                "finish_reason": "error",
            }


if __name__ == "__main__":
    llm = OpenAILLM()
    response = llm.invoke("介绍一下你自己")
    print(response)
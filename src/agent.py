from __future__ import annotations

import os
import json
import time
from typing import List
from src.config import ui, max_retry_num, max_context_tokens
from src.paths import get_transcripts_dir
from src.llm import OpenAILLM
from src.tools import tools_schema, tool_hander

def auto_compact(llm: OpenAILLM, messages: List) -> List:
    keep_messages = []
    for msg in messages:
        # 保留系统提示词
        if msg["role"] == "system":
            keep_messages.append(msg)
        # 保留已经压缩过的会话
        elif msg["role"] == "user" and msg["content"].startswith("[Compressed."):
            keep_messages.append(msg)
    path = get_transcripts_dir() / f"transcript_{int(time.time())}.jsonl"
    # 会话历史保存一份副本到磁盘
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False, default=str) + "\n")
    messages.append({"role": "user", "content": "请总结以上对话, 回答内容限制在 2000 字以内"})
    response = llm.invoke(messages, max_tokens=2000)
    # 上下文压缩失败，回退会话列表
    if response["finish_reason"] == "error":
        ui.warning(f"上下文压缩失败, 由于{response['content']}")
        return messages[:-1]
    keep_messages.append({"role": "user", "content": f"[Compressed. Transcript: {path}]\n{response['content']}"})
    ui.update(f"已完成上下文压缩: {len(messages) - 1} messages -> {len(keep_messages)} messages")
    return keep_messages

def assemble_system_prompt():
    pass

def agent_loop(llm: OpenAILLM, messages: List):
    while True:
        # LLM 调用失败重试机制
        retry_num = 0
        while retry_num <= max_retry_num:
            response = llm.invoke(messages, tools=tools_schema)
            if response["finish_reason"] != "error":
                break
            retry_num += 1
        messages.append({"role": "assistant", "content": response["content"]})
        if response["finish_reason"] == "error":
            ui.error(f"大模型调用已重试 {max_retry_num} 次, 仍然失败, 任务终止。\n失败原因：{response['content']}")
            return
        elif response["finish_reason"] != "tool_calls":
            ui.update(f"全部任务已完成")
            return
        ui.print(response["content"])
        tool_results = []
        for tc in response["tool_calls"]:
            ui.tool(f"名称：{tc[0]}\n\n参数：{tc[1]}")
            result = tool_hander(tc[0], tc[1])
            ui.console.print(f"\n\n执行结果：{result}")
            tool_results.append({"type": "tool_result", "content": result})
        messages.append({"role": "user", "content": json.dumps(tool_results, ensure_ascii=False, default=str)})
        if (response["context_tokens"] / max_context_tokens) > 0.85:
            ui.warning("上下文即将超限（已达85%），触发自动压缩")
            messages[:] = auto_compact(llm, messages)

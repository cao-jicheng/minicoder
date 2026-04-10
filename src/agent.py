from __future__ import annotations

import os
import re
import json
import time
import datetime
from typing import List
from pathlib import Path
from src.llm import OpenAILLM
from src.paths import (get_project_root, get_transcripts_dir, 
    get_skills_dir, get_memory_dir)
from src.config import (ui, max_retry_num, max_context_tokens,
    max_rounds_elapsed)
from src.tools import (tools_schema, tool_hander, todo_manager, 
    skill_loader, memory_manager)

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
    messages.append({"role": "user", "content": "请总结以上对话，回答内容限制在 2000 字以内"})
    response = llm.invoke(messages, max_tokens=2000)
    # 上下文压缩失败，回退会话列表
    if response["finish_reason"] == "error":
        ui.warning(f"上下文压缩失败，由于{response['content']}")
        return messages[:-1]
    keep_messages.append({"role": "user", "content": f"[Compressed. Transcript: {path}]\n{response['content']}"})
    ui.update(f"已完成上下文压缩：{len(messages) - 1} 条消息 -> {len(keep_messages)} 条消息")
    return keep_messages

class SystemPromptBuilder:
    def __init__(self):
        pass

    def _build_core(self) -> str:
        return (
            f"你是 MiniCoder，Caojicheng 开发的个人命令行编程助手。你是一个交互式智能体，用来帮助用户完成软件工程相关任务。"
            f"用户可能会要求你修复软件缺陷、添加新功能、重构代码、解释代码等。当你收到含糊或泛化的指令时，要结合这些软件工程任务"
            f"以及当前工作目录来理解用户的意图。\n你工作的项目根目录是 {get_project_root()}，你的任何操作都不要超出这个目录，"
            f"以免触发访问越界的错误。\n不要对你没有读过的代码提出修改建议，如果用户询问某个文件，或希望你修改某个文件，先把它读一遍，"
            f"在提出修改建议之前，先理解已有代码。\n注意不要引入命令注入、XSS、SQL 注入以及其他 OWASP Top 10 类安全漏洞。"
            f"如果你发现自己写出了不安全的代码，应立即修复。\n不要额外添加功能、重构代码，或做超出要求范围的优化。不要给未修改的代码"
            f"补充注释或类型注解。不要为本不可能发生的场景添加错误处理、兜底逻辑或额外校验，要相信内部代码和框架自身的保证。\n"
            f"除非为了完成任务绝对的必要，否则不要创建新文件，应该优先修改已有文件。这样可以避免文件膨胀，也能更好地复用已有工作。\n"
            f"如果用户拒绝了你调用的某个工具，不要再次发起完全相同的工具调用。相反，你应该思考用户拒绝的原因，并调整你的处理方式。" 
        )
    
    def _build_tools(self) -> str:
        lines = []
        for ts in tools_schema:
            params = [f"{k}: {v['type']}" for k, v in ts["parameters"]["properties"].items()]
            lines.append(f"- {ts['function']['name']}({', '.join(params)})：{ts['function']['description']}")
        return "# 可供使用的工具（tools）\n\n" + "\n".join(lines)

    def _build_skills(self) -> str:
        skills = skill_loader.skills
        if not skills:
            return ""
        skills_meta = [f"- {n}：{s['meta'].get('description', '')}" for n, s in skills.items()]
        return "# 可供使用的技能（skills）\n\n" + "\n".join(skills_meta)

    def _build_memory(self) -> str:
        memories = memory_manager.memories
        if not memories:
            return ""
        memory_meta = [f"[{v['type']}] {k}：{v['description']}\n{v['content']}" for k, v in memories.items()]
        return "# 持久化的记忆（memory）\n\n" + "\n\n".join(memory_meta)

    def _build_claude(self) -> str:
        sources = []
        # 用户级 CLAUDE.md
        user_claude = Path.home() / ".minicoder" / "CLAUDE.md"
        if user_claude.exists():
            sources.append(("用户级 (~/.minicoder/CLAUDE.md)", user_claude.read_text()))
        # 项目级 CLAUDE.md（如果和用户级 CLAUDE.md 相同，则跳过）
        project_claude = get_project_root() / "CLAUDE.md"
        if project_claude.exists() and project_claude != user_claude:
            sources.append(("项目级 (CLAUDE.md)", project_claude.read_text()))
        # 子目录级 CLAUDE.md
        cwd = Path.cwd()
        if cwd != get_project_root():
            subdir_claude = cwd / "CLAUDE.md"
            if subdir_claude.exists():
                sources.append((f"子目录级 ({cwd.name}/CLAUDE.md)", subdir_claude.read_text()))
        if not sources:
            return ""
        parts = []
        for label, content in sources:
            parts.append(f"## 来自于{label}")
            parts.append(content.strip())
        return "# CLAUDE.md 中包含的指令\n\n" + "\n\n".join(parts)

    def _build_todo(self) -> str:
        return (
            f"# TODO 任务步骤列表\n\n"
            f"如果用户要处理的是一个复杂的问题，你需要在执行前先将其分解为若干个解决步骤。"
            f"分解的步骤不要超过 10 个，每个步骤是一个字典格式，包含 content、status、activeForm 三个键。"
            f"content 是任务描述，应该简洁概要。activeForm是你现在正在做的任务。status 是执行状态，"
            f"可以取值 pending、in_progress、completed 三者之一。"
            f"你需要在每一轮执行完成后，调用 update_todo 工具来更新步骤列表。"
        )

    def _build_environment(self) -> str:
        lines = (
            f"当前日期：{datetime.date.today().isoformat()}\n"
            f"项目根目录：{get_project_root()}\n"
            f"大语言模型：{ui.llm.get_provider()}\n"
            f"工作平台：{os.uname().sysname}\n"
        )
        return "# 环境信息（environment）\n\n" + lines

    def build(self) -> str:
        sections = [self._build_core(), self._build_tools()]
        skills = self._build_skills()
        if skills:
            sections.append(skills)
        memory = self._build_memory()
        if memory:
            sections.append(memory)
        claude = self._build_claude()
        if claude:
            sections.append(claude)
        sections.append(self._build_todo())
        sections.append(self._build_environment())
        return "\n\n".join(sections)

prompt_builder = SystemPromptBuilder()

def agent_loop(llm: OpenAILLM, messages: List):
    rounds_elapsed = 0
    while True:
        rounds_elapsed += 1
        # 达到最大循环次数
        if rounds_elapsed > max_rounds_elapsed:
            ui.warning(f"智能体循环达到最大限制 {max_rounds_elapsed} 次，任务终止。")
            return
        # LLM 调用失败重试机制
        retry_num = 0
        while retry_num <= max_retry_num:
            response = llm.invoke(messages, tools=tools_schema)
            if response["finish_reason"] != "error":
                break
            retry_num += 1
        messages.append({"role": "assistant", "content": response["content"]})
        # 大模型重试仍然失败，大多数时候是网络原因引起的 timeout
        if response["finish_reason"] == "error":
            ui.error(f"大模型调用已重试 {max_retry_num} 次，仍然失败，任务终止。\n失败原因：{response['content']}")
            return
        # 大模型直接输出文本，不再调用工具，任务完成
        elif response["finish_reason"] != "tool_calls":
            ui.update(f"经过 {rounds_elapsed} 轮循环，全部任务已经完成")
            return
        # 显示大模型的回答内容
        ui.print(response["content"])
        tool_results = []
        used_todo = False
        for tc in response["tool_calls"]:
            ui.tool(f"名称：{tc[1]}\n\n参数：{tc[2]}")
            result = tool_hander(tc[1], tc[2])
            ui.console.print(f"\n\n执行结果：\n{result}")
            tool_results.append({"type": "tool_result", "tool_calls_id": tc[0], "content": result})
            if tc[1] == "update_todo":
                used_todo = True
        if not used_todo:
            todo_manager.rounds_since_update += 1
            reminder = todo_manager.reminder()
            # 经过3轮还没有更新 todo 任务步骤，则提醒大模型
            if reminder:
                tool_results.append({"type": "text", "text": reminder})
        messages.append({"role": "user", "content": json.dumps(tool_results, ensure_ascii=False, default=str)})
        # 上下文超限，自动压缩
        if (response["context_tokens"] / max_context_tokens) > 0.85:
            ui.warning("上下文即将超限（已达85%），触发自动压缩")
            messages[:] = auto_compact(llm, messages)

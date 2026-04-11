from __future__ import annotations

import os
import typer
from src.config import ui

app = typer.Typer(
    name="minicoder",
    help=(
        "一个由大语言模型驱动的简易编程助手"
    ),
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,
)

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    name: str = typer.Option(
        "新建会话",
        "--name",
        help="为当前会话取一个用于显示的名称",
    ),
    model: str = typer.Option(
        None,
        "--model",
        help="大语言模型的名称（默认 Pro/MiniMaxAI/MiniMax-M2.5）",
    ),
    base_url: str = typer.Option(
        None,
        "--base-url",
        help="大语言模型 API 访问地址（默认 https://api.siliconflow.cn/v1）",
    ),
    api_key: str = typer.Option(
        None,
        "--api-key",
        help="大语言模型 API 访问密钥",
    ),
    project_root: str = typer.Option(
        None,
        "--project-root",
        help="项目工作区根目录（默认 ~/.minicoder）",
    ),
    permission_mode: str = typer.Option(
        "Auto",
        "--permission_mode",
        help="权限模式（Default、Auto、Plan）",
    ),
    allow_subagent: bool = typer.Option(
        True,
        "--allow_subagent",
        help="是否允许启动子智能体（默认允许）",
    ),    
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    # 将命令行传入的参数设置为环境变量，以便全局可用
    if project_root:
        os.environ["PROJECT_ROOT"] = project_root
    os.environ["PERMISSION_MODE"] = permission_mode
    os.environ["ALLOW_SUBAGENT"] = "true" if allow_subagent else "false"

    from src.llm import OpenAILLM
    from src.agent import agent_loop, prompt_builder
    from src.commands import (parse_slash_command, show_help, 
        show_status, show_messages, set_permission, set_model,
        list_tools, list_skills, list_memory, clear_context,
        compact_context)

    llm = OpenAILLM(model=model, base_url=base_url, api_key=api_key)
    ui.set_llm(llm)
    ui.show_banner()
    system_prompt = prompt_builder.build()
    context_history = [{"role": "system", "content": system_prompt}]
    while True:
        try:
            query = ui.input()
        except (EOFError, KeyboardInterrupt):
            ui.bye()
            break
        if query.lower() in ("quit", "bye", "exit"):
            ui.bye()
            break
        # 处理斜杠命令
        if query.startswith('/'):
            items = parse_slash_command(query)
            # 处理非法命令的情况
            if len(items) == 0:
                continue
            command = items[0]
            if command == "/help":
                show_help()
                continue
            elif command == "/init":
                continue
            elif command == "/permission":
                set_permission(items)
                continue
            elif command == "/model":
                set_model(items)
                continue
            elif command == "/tools":
                list_tools()
                continue
            elif command == "/skills":
                list_skills()
                continue
            elif command == "/memory":
                list_memory()
                continue
            elif command == "/status":
                show_status()
                continue
            elif command == "/prompt":
                ui.output(system_prompt)
                continue
            elif command == "/messages":
                show_messages(context_history[-10:]) # 显示最近10条消息
                continue
            elif command == "/clear":
                clear_context(context_history)
                continue
            elif command == "/compact":
                compact_context(context_history)
                continue
        context_history.append({"role": "user", "content": query})
        agent_loop(context_history)
        # 显示最终结果
        ui.result(context_history[-1]["content"])


if __name__ == "__main__":
    app()
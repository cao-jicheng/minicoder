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

mcp_app = typer.Typer(name="mcp", help="管理 MPC 服务器")
plugin_app = typer.Typer(name="plugin", help="管理插件")

app.add_typer(mcp_app)
app.add_typer(plugin_app)

@mcp_app.command("list")
def mcp_list() -> None:
    """List configured MCP servers."""
    print("this is mcp list")

@plugin_app.command("install")
def plugin_install(
    source: str = typer.Argument(..., help="Plugin source (path or URL)"),
) -> None:
    """Install a plugin from a source path."""
    pass

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
        help="大语言模型的名称",
    ),
    base_url: str = typer.Option(
        None,
        "--base-url",
        help="大语言模型 API 访问地址",
    ),
    api_key: str = typer.Option(
        None,
        "--api-key",
        help="大语言模型 API 访问密钥",
    ),
    project_root: str = typer.Option(
        None,
        "--project-root",
        help="项目工作区根目录（默认~/.minicoder）",
    ),
    permission_mode: str = typer.Option(
        "Default",
        "--permission_mode",
        help="权限模式（Default、Auto、Plan）",
    ),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    # 将命令行传入的参数设置为环境变量
    if project_root:
        os.environ["PROJECT_ROOT"] = project_root
    os.environ["PERMISSION_MODE"] = permission_mode

    from src.llm import OpenAILLM
    from src.agent import agent_loop, auto_compact, prompt_builder
    from src.commands import (parse_slash_command, show_help, 
        set_permission, list_tools, show_status)

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
            if items[0] == "/help":
                show_help()
                continue
            if items[0] == "/init":
                continue
            if items[0] == "/permission":
                set_permission(items)
                continue
            if items[0] == "/tools":
                list_tools()
                continue
            if items[0] == "/skills":
                list_skills()
                continue
            if items[0] == "/status":
                show_status()
                continue
            if items[0] == "/prompt":
                ui.print(system_prompt)
                continue
            if query == "/compact" and context_history:
                context_history[:] = auto_compact(llm, context_history)
                continue
        context_history.append({"role": "user", "content": query})
        agent_loop(llm, context_history)
        ui.result(context_history[-1]["content"])


if __name__ == "__main__":
    app()
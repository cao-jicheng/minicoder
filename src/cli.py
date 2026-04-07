import os
import typer

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
        None,
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
        help="项目工作区根目录",
    ),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    # 将命令行传入的参数设置为环境变量
    if project_root:
        os.environ["PROJECT_ROOT"] = project_root
    
    from src.config import ui
    from src.llm import OpenAILLM
    from src.agent import agent_loop, auto_compact, show_help

    llm = OpenAILLM(model=model, base_url=base_url, api_key=api_key)
    ui.set_llm(llm)
    ui.show_banner()
    context_history = []
    while True:
        try:
            query = ui.input()
        except (EOFError, KeyboardInterrupt):
            ui.bye()
            break
        if query.lower() in ("quit", "bye", "exit"):
            ui.bye()
            break
        if query == "/init":
            pass
        if query == "/help":
            show_help()
            continue
        if query == "/compact" and context_history:
            context_history[:] = auto_compact(llm, context_history)
            continue
        context_history.append({"role": "user", "content": query})
        agent_loop(llm, context_history)
        ui.result(context_history[-1]["content"])
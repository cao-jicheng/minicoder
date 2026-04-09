from __future__ import annotations

import os
from typing import List
from rich import box
from rich.table import Table
from src.config import ui, slash_commands
from src.tools import tools_schema, get_skills_meta
from src.paths import get_project_root, get_permission_mode

def parse_slash_command(command: str) -> List:
    items = command.split()
    if items[0] not in slash_commands.keys():
        ui.warning(f"{items[0]} 不是一个合法的命令，请通过 /help 查看支持的命令")
        return []
    return items

def show_help():
    table = Table(box=box.ASCII, show_lines=True)
    table.add_column("命令", style="cyan", no_wrap=True)
    table.add_column("解释", overflow="fold")
    for (cmd, desc) in slash_commands.items():
        table.add_row(cmd, desc)
    ui.console.print(table)

def show_status():
    ui.show_banner()
    status = (
        f"工具数量：{len(tools_schema)}\n"
        f"技能数量：{len(get_skills_meta())}"
    )
    ui.console.print(status)
    ui.show_usage()
        
def set_permission(items: List):
    if len(items) == 1: # 只显示当前的权限模式
        ui.console.print(f"当前正处于 {get_permission_mode()} 模式")
        return
    # 通过环境变量设置权限模式
    if items[1].capitalize() == "Auto":
        os.environ["PERMISSION_MODE"] = "Auto"
    elif items[1].capitalize() == "Plan":
        os.environ["PERMISSION_MODE"] = "Plan"
    else:
        os.environ["PERMISSION_MODE"] = "Default"
    ui.update(f"已设置权限为 {get_permission_mode()} 模式")

def set_model(items: List):
    if len(items) == 1: # 只显示当前的大模型
        ui.console.print(f"当前使用的是 {ui.llm.get_provider()} 大语言模型")
        return
    ui.llm.reset_model(items[1])
    ui.update(f"已更换大语言模型为 {ui.llm.get_provider()}")

def list_tools():
    table = Table(box=box.ASCII, show_lines=True)
    table.add_column("工具", style="cyan", no_wrap=True)
    table.add_column("参数", overflow="fold")
    table.add_column("描述", overflow="fold")
    for ts in tools_schema:
        params = [f"{k}: {v['type']}" for k, v in ts["parameters"]["properties"].items()]
        table.add_row(ts["function"]["name"], ', '.join(params), ts["function"]["description"])
    ui.console.print(table)

def list_skills():
    table = Table(box=box.ASCII, show_lines=True)
    table.add_column("技能", style="cyan", no_wrap=True)
    table.add_column("描述", overflow="fold")
    for s in get_skills_meta():
        table.add_row(s[0], s[1])
    ui.console.print(table)


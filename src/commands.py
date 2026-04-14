from __future__ import annotations

import os
import subprocess
from typing import List
from rich import box
from rich.table import Table
from src.config import ui, slash_commands, llm_models
from src.agent import auto_compact
from src.paths import (get_project_root, get_current_dir, 
    get_skills_dir, get_permission_mode)
from src.tools import (tools_schema, skill_loader, memory_manager,
    subagent_llm_usage)

def check_command_passed(command: str) -> bool:
    if command not in slash_commands.keys():
        ui.warning(f"{command} 不是一个合法的命令，请通过 /help 查看支持的命令")
        return False
    return True

def show_help():
    table = Table(box=box.ASCII, show_lines=True)
    table.add_column("命令名称", style="cyan", no_wrap=True)
    table.add_column("功能说明", overflow="fold")
    for (cmd, desc) in slash_commands.items():
        table.add_row(cmd, desc)
    ui.console.print(table)

def show_status():
    ui.show_banner()
    status = (
        f"工具数量：{len(tools_schema)}\n"
        f"技能数量：{len(skill_loader.skills.keys())}\n"
        f"记忆数量：{len(memory_manager.memories.keys())}\n"
    )
    ui.console.print(status)

    def _convert_num(num: int) -> str:
        if num > 1e6:
            return f"{num / 1e6}M"
        elif num > 1e3:
            return f"{num / 1e3}K"
        else:
            return str(num)

    ui.console.print(f"\n[cadet_blue][子智能体 tokens 使用量统计]\n"
        f"输入 {_convert_num(subagent_llm_usage['input_tokens'])} tokens, "
        f"输出 {_convert_num(subagent_llm_usage['output_tokens'])} tokens [/cadet_blue]\n"
    )
    ui.show_usage()

def show_messages(messages: List):
    table = Table(box=box.ASCII, show_lines=True)
    table.add_column("角色", style="cyan", no_wrap=True)
    table.add_column("内容（最多显示 500 字符）", overflow="fold")
    for msg in messages:
        table.add_row(msg["role"], msg["content"][:500])
    ui.console.print(table)
        
def set_permission():
    if not ui.confirm(f"是否需要更改权限模式（当前为 {get_permission_mode()} 模式）？"):
        return
    new_mode = ui.choose("  请选择一种权限模式：", ["Default", "Auto", "Plan"])
    os.environ["PERMISSION_MODE"] = new_mode

def set_model():
    if not ui.confirm(f"是否需要更改大语言模型（当前为 {ui.llm.get_provider()} 模型）？"):
        return
    new_model = ui.choose("  请选择一个模型名称：", llm_models)
    from datetime import datetime
    from rich.prompt import Prompt
    if new_model == "Custom":
        response = Prompt.ask(f"\n请输入自定义模型名称")
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ui.console.print(f"\n[green][{time_now}]🎙️\x20\x20用户输入:\n\r{response}[/green]")
        new_model = response.strip()
    ui.llm.reset_model(new_model)

def list_tools():
    table = Table(box=box.ASCII, show_lines=True)
    table.add_column("工具名称", style="cyan", no_wrap=True)
    table.add_column("参数说明", overflow="fold")
    table.add_column("功能描述", overflow="fold")
    for ts in tools_schema:
        params = [f"{k}: {v['type']}" for k, v in ts["parameters"]["properties"].items()]
        table.add_row(ts["function"]["name"], ', '.join(params), ts["function"]["description"])
    ui.console.print(table)

def list_skills():
    table = Table(box=box.ASCII, show_lines=True)
    table.add_column("技能名称", style="cyan", no_wrap=True)
    table.add_column("功能描述", overflow="fold")
    for n, s in skill_loader.skills.items():
        table.add_row(n, s["meta"].get("description", ''))
    ui.console.print(table)

def install_skills(command: str, messages: List):
    # ["npx", "skills", "add", "<skills_repo>", ...]
    items = command.split()
    skill_repo_name = items[items.index("add") + 1]
    _, skill_name = os.path.split(skill_repo_name)
    if skill_repo_name.endswith(".zip"):
        need_download = False
        tmp_file = os.path.abspath(skill_repo_name)
        skill_name = skill_name[:-9]  # 去除 -main.zip 后缀名
    else:
        need_download = True
        tmp_file = "/tmp/skills.zip"
    if need_download:
        download_cmd = f"wget -O {tmp_file} https://github.com/{skill_repo_name}/archive/refs/heads/main.zip"
        try:
            r = subprocess.run(download_cmd, shell=True, cwd=get_current_dir(), capture_output=True, text=True, timeout=120)
        except Exception as e:
            ui.error(f"{skill_repo_name} 安装包下载失败，错误原因 {e}")
            return
    name_idx = [i for i, t in enumerate(items) if t == "--skill" or t == "-s"]
    rename = items[name_idx[0] + 1] if len(name_idx) > 0 else skill_name
    unzip_cmd = f"unzip -o {tmp_file} && mv {skill_name}-main {rename}"
    try:
        r = subprocess.run(unzip_cmd, shell=True, cwd=get_skills_dir(), capture_output=True, text=True)
        ui.update(f"技能 {skill_repo_name} 已成功安装，通过 /skills 可以查看详情")
    except Exception as e:
        ui.error(f"{skill_repo_name} 解压缩失败，错误原因 {e}")
        return
    # 更新技能列表
    skill_loader.update()
    added_skill = [(n, s) for n, s in skill_loader.skills.items() if s["folder"] == rename][0]
    skill_schema = f"- {added_skill[0]}：{added_skill[1]['meta'].get('description', '')}"
    messages.append({"role": "user", "content": f"[Important. 新添加的技能（skills）]\n\n{skill_schema}"})
    messages.append({"role": "assistant", "content": ""})

def list_memory():
    table = Table(box=box.ASCII, show_lines=True)
    table.add_column("记忆名称", style="cyan", no_wrap=True)
    table.add_column("记忆类型")
    table.add_column("内容简介", overflow="fold")
    for n, s in memory_manager.memories.items():
        table.add_row(n, s.get("type"), s.get("description"))
    ui.console.print(table)

def clear_context(messages: List):
    # 安全措施：用户二次确认
    if not ui.confirm(f"是否同意清空上下文中所有的消息？"):
        return
    # 只保留系统提示词（第一条消息）
    messages[:] = [m for m in messages if m["role"] == "system"]
    ui.update("已清空上下文消息（只保留系统提示词）")

def compact_context(messages: List):
    # 安全措施：用户二次确认
    if not ui.confirm(f"是否同意压缩上下文？"):
        return
    messages[:] = auto_compact(messages)

from __future__ import annotations

import os
import pickle
import subprocess
from typing import List
from rich import box
from rich.table import Table
from src.config import ui, slash_commands, llm_models
from src.agent import auto_compact
from src.paths import (get_project_root, get_current_dir, 
    get_skills_dir, get_permission_mode, get_snapshot_dir)
from src.tools import (tools_schema, skill_loader, memory_manager,
    subagent_llm_usage)

def check_command_passed(command: str) -> bool:
    # 前面已经判断 command 以 “/” 开头，因此无需再判空
    cmd = command.split()[0]
    if cmd not in slash_commands.keys():
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

    ui.console.print(
        f"\n[cadet_blue][子智能体词元使用量统计]"
        f"\n输入 {_convert_num(subagent_llm_usage['input_tokens'])} tokens"
        f"\n输出 {_convert_num(subagent_llm_usage['output_tokens'])} tokens"
        f"[/cadet_blue]"
    )
    ui.show_usage()

def show_messages(messages: List):
    table = Table(box=box.ASCII, show_lines=True)
    table.add_column("角色", style="cyan", no_wrap=True)
    table.add_column("内容（最多显示 500 字符）", overflow="fold")
    for msg in messages:
        table.add_row(msg["role"], msg["content"][:500])
    ui.console.print(table)
        
def set_permission(messages: List):
    if not ui.confirm(f"是否需要更改权限模式（当前为 {get_permission_mode()} 模式）？"):
        return
    new_mode = ui.choose("  请选择一种权限模式：", ["Default", "Auto", "Plan"])
    os.environ["PERMISSION_MODE"] = new_mode
    messages.append({"role": "user", "content": f"权限模式已切换为 {get_permission_mode()}"})
    messages.append({"role": "assistant", "content": ""})

def set_model(messages: List):
    if not ui.confirm(f"是否需要更改大语言模型（当前为 {ui.llm.get_provider()} 模型）？"):
        return
    new_model = ui.choose("  请选择一个模型名称：", llm_models)
    from rich.prompt import Prompt
    if new_model == "Custom":
        response = Prompt.ask(f"\n请输入自定义模型名称")
        ui.show_user_input(response)
        new_model = response.strip()
    ui.llm.reset_model(new_model)
    messages.append({"role": "user", "content": f"大语言模型已切换为 {ui.llm.get_provider()}"})
    messages.append({"role": "assistant", "content": ""})

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

def invoke_with_llm_once(query: str, messages: List):
    # 去除开头的 /btw 字符串
    prompt = query[4:].strip()
    if not prompt:
        return
    # 直接使用当前的会话历史，提供背景信息和复用 prefix cache
    messages.append({"role": "user", "content": prompt})
    result = ui.llm.invoke(messages)
    if result["finish_reason"] == "error":
        ui.error(result["content"])
    else:
        ui.output(result["content"])
    # 与大模型交互完成后，删除添加的 user 信息，恢复原始的会话历史
    messages.pop()

def backout_messages(query: str, messages: List):
    # 安全措施：用户二次确认
    if not ui.confirm(f"是否要回退会话历史信息？"):
        return
    # 默认回退最近一轮
    num_backout = 1
    items = query.split()
    if len(items) > 1:
        try:
            num_backout = int(items[1])
            assert num_backout <= 3
        except:
            ui.warning(f"回退超过 3 轮或者不是整数：{items[1]}，默认回退 1 轮")
            num_backout = 1
    if len(messages) < 2:
        ui.warning(f"会话历史只有 system 消息，无法回退")
        return
    # 每一轮交互信息包含 user 和 assistant
    messages[:] = messages[:-2 * num_backout]
    ui.update(f"已回退最近 {num_backout} 轮会话历史信息")

def load_snapshot(query: str, messages: List):
    # 去除开头的 /resume 字符串
    uid = query[8:].strip()
    if not uid:
        ui.warning("会话 ID 为空，恢复会话失败")
        return
    path = get_snapshot_dir() / f"resume_{uid}.pkl"
    if not path.exists():
        ui.warning(f"路径 {path} 不存在，恢复会话失败")
        return
    with open(path, "rb") as f:
        data = pickle.load(f)
    # 设置环境变量
    os.environ["PROJECT_ROOT"] = str(data["project_root"])
    os.environ["PERMISSION_MODE"] = str(data["permission_mode"])
    # 设置大语言模型
    llm_provider = str(data["llm_provider"])
    ui.llm.reset_model(llm_provider.split(':')[1])
    # 设置会话消息
    messages[:] = data["messages"]
    ui.update(f"会话已从 {path} 恢复")

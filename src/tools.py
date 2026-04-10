from __future__ import annotations

import re
import json
import inspect
import subprocess
from pathlib import Path
from dataclasses import dataclass
from json_repair import repair_json
from typing import List, Dict, Callable, Any
from src.config import (ui, dangerous_commands, max_output_length, 
    max_memory_entities)
from src.paths import (get_project_root, get_skills_dir, get_memory_dir,
    get_permission_mode)

@dataclass
class TodoItem:
    content: str
    status: str
    active_form: str

class TodoManager:
    def __init__(self):
        self.items: List[TodoItem] = []
        self.rounds_since_update: int = 0
        self.status_types = ("pending", "in_progress", "completed")
    
    def update(self, items: List) -> str:
        if len(items) > 10:
            return f"你规划的步骤已达 {len(items)} 个，过于冗长，请裁剪到10个以内"
        normalized_items = []
        in_progress_count = 0
        for idx, raw_item in enumerate(items):
            content = str(raw_item.get("content", "")).strip()
            if not content:
                return f"第 {idx} 步的 content 为空，请检查字典的键是否合法，期望：content、status、activeForm"
            status = str(raw_item.get("status", "pending")).lower()
            if status not in self.status_types:
                return f"第 {idx} 步的 status 为无效值，期望：{'、'.join(self.status_types)}"
            active_form = str(raw_item.get("activeForm", "")).strip()
            normalized_items.append(TodoItem(content=content, status=status, active_form=active_form))
            if status == "in_progress":
                in_progress_count += 1
        if in_progress_count > 1:
            return (
                f"当前有 {in_progress_count} 个步骤处于 in_progress 状态，"
                f"但是只允许有1个步骤处于 in_progress 状态，"
                f"以便你可以专注于当前步骤"
            )
        self.items = normalized_items
        self.rounds_since_update = 0
        return self.render()

    def render(self) -> str:
        if len(self.items) == 0:
            return "当前还没有为任务分解步骤"
        lines = []
        for item in self.items:
            marker = {
                "pending": "[ ]",
                "in_progress": "[>]",
                "completed": "[+]",
            }[item.status]
            line = f"{marker} {item.content}"
            if item.status == "in_progress" and item.active_form:
                line += f" ({item.active_form})"
            lines.append(line)
        completed = sum(1 for t in self.items if t.status == "completed")
        lines.append(f"\n(已完成 {completed}/{len(self.items)} 个步骤)")
        return "\n".join(lines)
    
    def reminder(self) -> str:
        if len(self.items) == 0:
            return ""
        # 超过3轮没有更新todo计划，则提醒大模型
        if self.rounds_since_update < 3:
            return ""
        return "<reminder>在你继续执行任务前，先调用 update_todo 工具更新步骤</reminder>"

todo_manager = TodoManager()

class MemoryManager:
    def __init__(self):
        self.memory_types = ("user", "feedback", "project", "reference")
        self.load()
    
    def _rebuild_index(self):
        lines = []
        for name, memory in self.memories.items():
            lines.append(f"- {name}：{memory['description']} [{memory['type']}]")
            if len(lines) >= max_memory_entities:
                lines.append(f"... (最多保留 {max_memory_entities} 条记忆)")
                break
        memory_path = get_memory_dir() / "MEMORY.md"
        memory_path.write_text("# 记忆索引\n\n" + "\n".join(lines))

    def _parse_frontmatter(self, text: str) -> Dict | None:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
        if not match:
            return None
        header, body = match.group(1), match.group(2)
        result = {"content": body.strip()}
        for line in header.splitlines():
            # 同时支持中文冒号和英文冒号
            separator = '：' if '：' in line else ':'
            if separator in line:
                key, _, value = line.partition(separator)
                result[key.strip()] = value.strip()
        return result

    def save(self, name: str, mem_desc: str, mem_type: str, content: str) -> str:
        if mem_type not in self.memory_types:
            return f"{mem_type} 不是合法的记忆类型，期望：{'、'.join(self.memory_types)}"
        # 将空格、$、#、*等特殊字符转换为下划线，避免保存文件时出现路径错误
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", '_', name.lower())
        frontmatter = (
            f"---\n"
            f"name: {name}\n"
            f"description: {mem_desc}\n"
            f"type: {mem_type}\n"
            f"---\n"
            f"{content}\n"
        )
        file_name = f"{safe_name}.md"
        file_path = get_memory_dir() / file_name
        file_path.write_text(frontmatter)
        self.memories[name] = {
            "description": mem_desc,
            "type": mem_type,
            "content": content,
            "file": file_name,
        }
        self._rebuild_index()
        return f"已保存记忆 '{name}' [{mem_type}] 到路径 {file_path}"

    def load(self) -> str:
        self.memories = {}
        for md_file in sorted(get_memory_dir().glob("*.md")):
            if md_file.name == "MEMORY.md":
                continue
            parsed_memory = self._parse_frontmatter(md_file.read_text())
            if parsed_memory:
                name = parsed_memory.get("name", md_file.stem)
                self.memories[name] = {
                    "description": parsed_memory.get("description", ""),
                    "type": parsed_memory.get("type", "project"),
                    "content": parsed_memory.get("content", ""),
                    "file": md_file.name,
                }
        return f"已加载 {len(self.memories)} 条记忆"

memory_manager = MemoryManager()

class SkillLoader:
    def __init__(self):
        self.skills = {}
        for f in sorted(get_skills_dir().rglob("SKILL.md")):
            text = f.read_text()
            match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
            meta, body = {}, text
            if match:
                for line in match.group(1).strip().splitlines():
                    separator = '：' if '：' in line else ':'
                    if separator in line:
                        k, _, v = line.partition(separator)
                        meta[k.strip()] = v.strip()
                body = match.group(2).strip()
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body}
    
    def load(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            return f"暂无 {name} 技能，可选的技能有：{'、'.join(self.skills.keys())}"
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"

skill_loader = SkillLoader()

## 工具注册的 wrapper 函数
function_registry = {}

def register(require_approval: bool=False):
    def wrap_func(func):
        function_registry[func.__name__] = (require_approval, func)
        return func
    return wrap_func

def _run_tool(func, args) -> Any:
    try:
        return func(**args)
    except Exception as e:
        return f"工具运行出错 {e}"

def tool_hander(name, args) -> Any:
    if name in function_registry:
        args = json.loads(repair_json(args))
        mode = get_permission_mode()
        (require_approval, func) = function_registry[name]
        if mode == "Plan" and require_approval:
            return f"Plan 模式只允许运行 Read-Only 工具"
        can_run = True
        if mode == "Default" and require_approval:
            can_run = (ui.confirm(f"是否允许运行 {name} 工具？") == True)
        if not can_run:
            return f"用户拒绝运行 {name} 工具"
        return _run_tool(func, args)
    else:
        return f"工具 {name} 未注册"

def parse_docstring(doc: str) -> Dict:
    # 判断输入的 docstring 是否为空
    if not doc:
        return {"description": "", "params": {}}
    items = [t.strip() for t in doc.split("\n\n")]
    # 截取 docstring 中 Args 的部分
    fn_params = [t for t in items if t.startswith("Args")][0].split("\n")
    params_dict = {}
    # 去除第一段包含 “Args” 的部分，从第二部分开始遍历
    for param in fn_params[1:]:
        # 支持中文冒号或英文冒号作为分隔符
        separator = '：' if '：' in param else ':'
        # 以第一个引号为准，只分割一次
        parts = param.split(separator, maxsplit=1)
        params_dict[parts[0].strip()] = parts[1].strip()
    return {"description": items[0].strip(), "params": params_dict}

def generate_tools_schema(funcs: List[Callable]) -> List:
    tools_schema = []
    for fn in funcs:
        # 解析工具函数的 docstring
        doc = inspect.getdoc(fn)
        parsed_doc = parse_docstring(doc)
        schema = {
            "type": "function",
            "function": {
                "name": fn.__name__,
                "description": parsed_doc["description"]
            }}
        # 解析工具函数的签名
        sig = inspect.signature(fn)
        params_dict = {"type": "object"}
        properties = {}
        required = []
        for name, param in sig.parameters.items():
            param_type = param.annotation if param.annotation != param.empty else ""
            param_desc = parsed_doc["params"][name] if name in parsed_doc["params"].keys() else ""
            properties[name] = {"type": param_type, "description": param_desc}
            # 如果参数的默认值为空，则该参数为必填参数
            if param.default == param.empty:
                required.append(name)
        params_dict["properties"] = properties
        params_dict["required"] = required
        schema["parameters"] = params_dict
        tools_schema.append(schema)
    return tools_schema

def safe_path(path: str) -> Path:
    abs_path = Path(path).resolve()
    if not abs_path.is_relative_to(get_project_root()):
        raise ValueError(f"工具访问越界，路径 {path} 不在项目根目录内")
    return abs_path

# ================================================================================
# -----------------------------  在此处定义工具  ----------------------------------
# ================================================================================

@register(require_approval=True)
def run_bash(command: str) -> str:
    """运行shell命令，遇到危险指令，将自动终止运行。
    选择 run_bash 工具不是第一优先级，应该先尝试其他专用工具，无法满足要求时才使用 run_bash 工具来兜底。
    
    Args：
        command：传入的命令字符串

    Returns：
        命令执行结果（包含stdout和stderr）
    """
    if any(cmd in command for cmd in dangerous_commands):
        return f"命令 {command} 中包含危险指令, 终止运行"
    try:
        r = subprocess.run(command, shell=True, cwd=Path.cwd(), capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip() or "暂无输出内容"
        if len(out) > max_output_length:
            out = out[:max_output_length] + " [内容超长已截断...]"
        return out
    except subprocess.TimeoutExpired:
        return "执行命令超时（120秒）"

@register(require_approval=False)
def read_file(file: str) -> str:
    """读取指定文件的内容
    
    Args：
        file：传入的文件路径

    Returns：
        读取的文本字符串或输出报错信息
    """
    try:
        lines = safe_path(file).read_text().splitlines()
        out = "\n".join(lines) if lines else "暂无输出内容"
        if len(out) > max_output_length:
            out = out[:max_output_length] + " [内容超长已截断...]"
        return out
    except Exception as e:
        return f"读取文件出错 {e}"

@register(require_approval=True)
def write_file(file: str, content: str) -> str:
    """向指定文件中写入数据
    
    Args：
        file：传入的文件路径
        content：待写入的文本内容

    Returns：
        写入的字节数或输出报错信息
    """
    try:
        fp = safe_path(file)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"写入 {len(content)} 字节到文件 {file}"
    except Exception as e:
        return f"写入文件出错 {e}"

@register(require_approval=True)
def edit_file(file: str, old_text: str, new_text: str) -> str:
    """编辑文件，将文件中的旧文本替换为新文本
    
    Args：
        file：传入的文件路径
        old_text：旧的数据
        new_text：新的数据

    Returns：
        文件修改成功或失败的信息
    """
    try:
        fp = safe_path(file)
        content = fp.read_text()
        if old_text not in content:
            return f"在文件 {file} 中未找到要替换的内容"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"已完成对文件 {file} 的修改"
    except Exception as e:
        return f"修改文件出错 {e}"

@register(require_approval=False)
def update_todo(steps: List) -> str:
    """更新你规划的任务分解步骤（todo），每个步骤都是一个字典，包含 content、status、activeForm 三个键，
    status 可以取值 pending、in_progress、completed 三者之一。
    
    Args：
        steps：你生成的步骤列表

    Returns：
        更新后的步骤列表或报错信息
    """
    return todo_manager.update(steps)

@register(require_approval=False)
def load_skill(name: str) -> str:
    """根据 skill name 加载对应的 skill body
    
    Args：
        name：需要加载的 skill 名称

    Returns：
        skill body
    """
    return skill_loader.load(name)

@register(require_approval=False)
def save_memory(name: str, memory_description: str, memory_type: str, content: str) -> str:
    """将当前会话中的用户偏好信息、用户反馈信息、总结的客观事实、内部资源的链接保存为持久化的记忆，
    以便跨会话交互时，你可以复用这些信息。记忆类型包含 user、feedback、project、reference 四种。
    **以下这些场景需要你主动保存记忆：**
    1、用户明确表明的偏好，例如 “我喜欢简洁的回答”、“我希望使用 pytest 框架”，这种场景下将记忆保存为 user 类型。
    2、用户明确纠正你的地方，例如 “不能这样修改”、“以后遇到这种情况要先问我”，这种场景下将记忆保存为 feedback 类型。
    3、从项目代码中总结的客观事实，例如 “这段代码的设计是因为合规，而不是技术偏好”，这种场景下将记忆保存为 project 类型。
    4、内部资源的链接地址，例如 “模板库在 ~/.minicoder/template 目录下”，这种场景下将记忆保存为 reference 类型。
    **以下这些场景绝对不能保存为记忆：**
    1、文件结构、函数签名、目录布局，这些信息可以重新读代码得到。
    2、当前任务的进度，属于 todo/task 领域。
    3、临时分支名、当前 commit 号、环境变量，这些信息会很快过时。
    4、密钥、密码、凭证，存在信息安全风险。

    Args：
        name：记忆持久化后的名称
        memory_description：这段记忆的简要描述
        memory_type：记忆类型（user、feedback、project、reference）
        content：记忆的详细内容

    Returns：
        保存成功或报错信息
    """
    return memory_manager.save(name, memory_description, memory_type, content)

tools_schema = generate_tools_schema([run_bash, read_file, write_file, 
    edit_file, update_todo, load_skill, save_memory])

from __future__ import annotations

import json
import inspect
import subprocess
from pathlib import Path
from json_repair import repair_json
from typing import List, Dict, Callable, Any
from src.paths import get_project_root, get_permission_mode, get_skills_dir
from src.config import ui, dangerous_commands, max_output_length

## 注册工具的 wrapper 函数
function_registry = {}

def register(require_approval: bool=True):
    def wrap_func(func):
        function_registry[func.__name__] = (require_approval, func)
        return func
    return wrap_func

## ===== 定义工具函数 =====

@register(require_approval=True)
def run_bash(command: str) -> str:
    """运行shell命令，遇到危险指令，将自动终止。不推荐首先使用shell命令，
    只有在专用工具无法实现目标任务时，才允许谨慎地使用shell命令。
    
    Args：
        command：传入的命令字符串

    Returns：
        命令运行结果（包含stdout和stderr）
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
    """读取文件的文本内容
    
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
        return f"读取文件出错: {e}"

@register(require_approval=True)
def write_file(file: str, content: str) -> str:
    """向文件中写入数据
    
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
        return f"写入 {len(content)} 字节到文件 {file} 中"
    except Exception as e:
        return f"写入文件出错: {e}"

@register(require_approval=True)
def edit_file(file: str, old_text: str, new_text: str) -> str:
    """编辑文件，以修改文件的内容
    
    Args：
        file：传入的文件路径
        old_text：旧的数据
        new_text：新的数据

    Returns：
        文件修改状态
    """
    try:
        fp = safe_path(file)
        content = fp.read_text()
        if old_text not in content:
            return f"在文件 {file} 中未找到要替换的内容"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"已完成对文件 {file} 的修改"
    except Exception as e:
        return f"修改文件出错: {e}"

## ===== 以下是辅助函数 =====

def _run_tool(func, args) -> Any:
    try:
        return func(**args)
    except Exception as e:
        return f"工具运行出错：{e}"

def tool_hander(name, args) -> Any:
    if name in function_registry:
        args = json.loads(repair_json(args))
        mode = get_permission_mode()
        (require_approval, func) = function_registry[name]
        if mode == "Plan" and require_approval:
            return f"Plan模式只允许运行Read-Only工具"
        can_run = True
        if mode == "Default" and require_approval:
            can_run = (ui.confirm(f"是否允许运行 {name} 工具？") == True)
        if not can_run:
            return f"用户拒绝运行 {name} 工具"
        return _run_tool(func, args)
    else:
        return f"工具 {name} 未注册"

def safe_path(path: str) -> Path:
    abs_path = Path(path).resolve()
    if not abs_path.is_relative_to(get_project_root()):
        raise ValueError(f"访问越界，路径 {path} 不在项目根目录内")
    return abs_path

def get_skills_meta() -> List:
    skills = []
    # 遍历 skills 目录中所有的 SKILL.md 文件
    for skill_dir in sorted(get_skills_dir().iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text()
        # 匹配 "---" 标识符
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            continue
        meta = {}
        for line in match.group(1).splitlines():
            # 同时支持中文冒号和英文冒号
            separator = '：' if '：' in line else ':'
            if separator in line:
                k, _, v = line.partition(separator)
                meta[k.strip()] = v.strip()
        name = meta.get("name", skill_dir.name)
        desc = meta.get("description", "")
        skills.append((name, desc))
    return skills

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

tools_schema = generate_tools_schema([run_bash, read_file, write_file, edit_file])

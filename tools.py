import inspect
import subprocess
from pathlib import Path
from typing import List, Dict, Callable
from config import project_root, dangerous_commands, max_text_length

## ===== 定义工具函数 =====

def run_bash(command: str) -> str:
    """安全地运行shell命令，遇到危险指令，将自动终止。
    
    Args：
        command：输入的命令字符串

    Returns：
        命令运行结果（包含 stdout 和 stderr）
    """
    if any(cmd in command for cmd in dangerous_commands):
        return "命令中包含危险指令, 终止运行"
    try:
        r = subprocess.run(command, shell=True, cwd=project_root, capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:max_text_length] if out else "没有输出内容"
    except subprocess.TimeoutExpired:
        return "执行命令超时（120秒）"

def read_file(path: str, limit: int=1000) -> str:
    """读取文件的内容
    
    Args：
        path：输入的文件路径
        limit：限制读取的行数

    Returns：
        读取的文本字符串或输出报错信息
    """
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit > 0 and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} 行未显示)"]
        return "\n".join(lines)[:max_text_length]
    except Exception as e:
        return f"读取文件出错: {e}"

def write_file(path: str, content: str) -> str:
    """向文件中写入数据
    
    Args：
        path：输入的文件路径
        content：待写入的字符串数据

    Returns：
        写入的字节数或输出报错信息
    """
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"写入 {len(content)} 字节到文件 {path} 中"
    except Exception as e:
        return f"写入文件出错: {e}"

def edit_file(path: str, old_text: str, new_text: str) -> str:
    """编辑文件，以修改文本内容
    
    Args：
        path：输入的文件路径
        old_text：旧的数据
        new_text：新的数据

    Returns：
        文件修改状态
    """
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"在文件 {path} 中未找到要替换的内容"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"已完成对文件 {path} 的修改"
    except Exception as e:
        return f"修改文件出错: {e}"

## ===== 以下是辅助函数 =====

def safe_path(path: str) -> Path:
    abs_path = Path(path).resolve()
    if not abs_path.is_relative_to(Path(project_root)):
        raise ValueError(f"访问越界，目录 {path} 不在项目根目录内")
    return abs_path

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
            param_type = param.annotation.__name__ if param.annotation != param.empty else ""
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
        # 支持中文引号或英文引号作为分隔符
        separator = '：' if '：' in param else ':'
        # 以第一个引号为准，只分割一次
        parts = param.split(separator, maxsplit=1)
        params_dict[parts[0].strip()] = parts[1].strip()
    return {"description": items[0].strip(), "params": params_dict}
    

if __name__ == "__main__":
    schema = generate_tools_schema([run_bash, read_file, write_file, edit_file])
    print(schema)



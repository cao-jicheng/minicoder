import os
import time
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.status import Status
from rich.markdown import Markdown
from src.llm import OpenAILLM

minicoder_logo = [
    ' ███╗   ███╗ ██╗ ███╗   ██╗ ██╗  ██████╗  ██████╗  ██████╗   ███████╗ ██████╗ ',
    ' ████╗ ████║ ██║ ████╗  ██║ ██║ ██╔════╝ ██╔═══██╗ ██╔══██╗  ██╔════╝ ██╔══██╗',
    ' ██╔████╔██║ ██║ ██╔██╗ ██║ ██║ ██║      ██║   ██║ ██║   ██║ █████╗   ██████╔╝',
    ' ██║╚██╔╝██║ ██║ ██║╚██╗██║ ██║ ██║      ██║   ██║ ██║  ██╔╝ ██╔══╝   ██╔══██╗',
    ' ██║ ╚═╝ ██║ ██║ ██║ ╚████║ ██║ ╚██████╗ ╚██████╔╝ █████╔═╝  ███████╗ ██║  ██║',
    ' ╚═╝     ╚═╝ ╚═╝ ╚═╝  ╚═══╝ ╚═╝  ╚═════╝  ╚═════╝  ╚════╝    ╚══════╝ ╚═╝  ╚═╝',
]

def time_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _convert_num(num: int) -> str:
    if num > 1e6:
        return f"{num / 1e6}M"
    elif num > 1e3:
        return f"{num / 1e3}K"
    else:
        return str(num)

class AgentUI():
    def __init__(
        self,
        width: int=120,
        record: bool=False,
        version: Optional[str]=None,
        llm: Optional[OpenAILLM]=None,
        trajectory_dir: Optional[Path]=None,
    ):
        self.record = record
        self.console = Console(width=width, record=record)
        self.version = version or "0.1.0"
        self.llm = llm or OpenAILLM()
        self.trajectory_dir = trajectory_dir or Path(".trajectory")
        
    def set_llm(self, llm: OpenAILLM):
        self.llm = llm
    
    def warning(self, data: str):
        self.console.print(f"\n[yellow][{time_now()}]⚠️\x20\x20警告提醒:\n\r{data}[/yellow]")

    def error(self, data: str):
        self.console.print(f"\n[red][{time_now()}]❌\x20严重错误:\n\r{data}[/red]")
    
    def print(self, data: str):
        md_data = Markdown(data)
        self.console.print(f"\n[white][{time_now()}]🖨️\x20\x20执行结果:[/white]")
        self.console.print(md_data, style="white")
    
    def think(self, data: str):
        self.console.print(f"\n[magenta][{time_now()}]🧠\x20思考过程:\n\r{data}[/magenta]")

    def tool(self, data: str):
        self.console.print(f"\n[dark_goldenrod][{time_now()}]🛠️\x20\x20工具选用:\n\r{data}[/dark_goldenrod]")

    def result(self, data: str):
        md_data = Markdown(data)
        self.console.print(f"\n[cadet_blue][{time_now()}]🎉\x20最终结果:[/cadet_blue]")
        self.console.print(md_data, style="cadet_blue")

    def update(self, data: str):
        self.console.print(f"\n[blue][{time_now()}]📝\x20状态更新:\n\r{data}[/blue]") 
    
    def input(self) -> str:
        response = Prompt.ask("\n用户输入")
        self.console.print(f"\n[green][{time_now()}]🎙️\x20\x20用户输入:\n\r{response}[/green]")
        return response.strip()

    def confirm(self, question: str) -> bool:
        response = Confirm.ask("\n" + question)
        self.console.print(f"\n[green][{time_now()}]🖱️\x20\x20用户确认:\n\r{response}[/green]")
        return response

    def choose(self, options: List[str]) -> str:
        response = Prompt.ask("\n请从下列选项中选择一个", choices=options)
        self.console.print(f"\n[green][{time_now()}]🖱️\x20\x20用户选择:\n\r{response}[/green]")
        return response

    def bye(self):
        with Status(status="正在保存会话历史，期待下次再见！！！", spinner="clock") as status:
            status.start()
            self.show_usage()
            self.save_trajectory()
            time.sleep(2)
    
    def save_trajectory(self):
        if not self.record:
            return
        path = self.trajectory_dir / f"record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        data = self.console.export_html()
        with open(path, "w") as f:
            f.write(data)
    
    def show_usage(self):
        total_tokens = self.llm.input_tokens + self.llm.output_tokens
        cached_tokens = self.llm.cache_hit_tokens + self.llm.cache_miss_tokens
        cached_ratio = (100 * cached_tokens / self.llm.input_tokens) if self.llm.input_tokens else 0.0
        cache_hit_ratio = (100 * self.llm.cache_hit_tokens / cached_tokens) if cached_tokens else 0.0
        self.console.print(f"\n[cadet_blue][Tokens 使用量统计]\n输入 {_convert_num(self.llm.input_tokens)} tokens, "
            f"输出 {_convert_num(self.llm.output_tokens)} tokens, 总共 {_convert_num(total_tokens)} tokens,\n"
            f"输入缓存 {_convert_num(cached_tokens)} tokens, 缓存率为 {cached_ratio:.2f} %, \n"
            f"缓存命中 {_convert_num(self.llm.cache_hit_tokens)} tokens, 未命中 {_convert_num(self.llm.cache_miss_tokens)} tokens, "
            f"缓存命中率为 {cache_hit_ratio:.2f} % [/cadet_blue]")
        
    def show_banner(self):
        from src.paths import get_project_root
        logo = '\n'.join(minicoder_logo)
        self.console.print(f"[bright_red]{'-'*80}\n\n{logo}\n[/bright_red]")
        self.console.print(f"[green bold] 当前版本: [/green bold]{self.version}")
        self.console.print(f"[green bold] 语言模型: [/green bold]{self.llm.get_provider()}")
        self.console.print(f"[green bold] 项目路径: [/green bold]{get_project_root()}")
        self.console.print(f"[bright_red]{'-'*80}[/bright_red]")


if __name__ == "__main__":
    ui = AgentUI()
    ui.show_banner()
#     ui.input()
#     ui.choose(["小学", "初中", "高中", "大学"])
#     ui.confirm("是否允许继续执行？")
#     ui.save_html()
#     ui.error("错误测试")
#     ui.print("输出测试")
#     ui.think("推理测试")
#     ui.tool("工具测试")
#     ui.result("结果测试")
#     ui.update("状态测试")


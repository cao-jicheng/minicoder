from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.prompt import Confirm

def time_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class AgentUI():
    def __init__(self, width: int=120, record: bool=False):
        self.record = record
        self.console = Console(width=width, record=record)
    
    def warning(self, data: str):
        self.console.print(f"\n[yellow][{time_now()}]⚠️\x20\x20警告提醒:\n\r{data}[/yellow]")

    def error(self, data: str):
        self.console.print(f"\n[red][{time_now()}]❌\x20严重错误:\n\r{data}[/red]")
    
    def print(self, data: str):
        self.console.print(f"\n[white][{time_now()}]🖨️\x20\x20执行结果:\n\r{data}[/white]")
    
    def think(self, data: str):
        self.console.print(f"\n[magenta][{time_now()}]🧠\x20思考过程:\n\r{data}[/magenta]")

    def tool(self, data: str):
        self.console.print(f"\n[dark_goldenrod][{time_now()}]🛠️\x20\x20工具选用:\n\r{data}[/dark_goldenrod]")

    def result(self, data: str):
        self.console.print(f"\n[cadet_blue][{time_now()}]🎉\x20最终结果:\n\r{data}[/cadet_blue]") 

    def update(self, data: str):
        self.console.print(f"\n[blue][{time_now()}]📝\x20更新状态:\n\r{data}[/blue]") 
    
    def save_html(self, dir: Optional[str]=None):
        if not self.record:
            self.warning("record=False, 请打开 record 开关")
            return
        dir = dir if dir else "."
        path = f"{dir}/record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        data = self.console.export_html()
        with open(path, "w") as f:
            f.write(data)
    
    def input(self) -> str:
        response = Prompt.ask("用户输入")
        self.console.print(f"\n[green][{time_now()}]📝\x20用户输入:\n\r{response}[/green]")
        return response

    def confirm(self, question: str) -> bool:
        response = Confirm.ask(question)
        self.console.print(f"\n[green][{time_now()}]📝\x20用户确认:\n\r{response}[/green]")
        return response

    def choose(self, options: List[str]) -> str:
        response = Prompt.ask("请从下列选项中选择一个", choices=options)
        self.console.print(f"\n[green][{time_now()}]📝\x20用户选择:\n\r{response}[/green]")
        return response


# if __name__ == "__main__":
#     ui = AgentUI()
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


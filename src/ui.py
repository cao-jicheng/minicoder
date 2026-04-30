from __future__ import annotations

import os
import time
import random
from datetime import datetime
from typing import List, Tuple, Optional
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.status import Status
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.filters import is_done
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.formatted_text import HTML
from src.llm import OpenAILLM
from src.paths import get_project_root, get_permission_mode

minicoder_logo = [
    ' ███╗   ███╗ ██╗ ███╗   ██╗ ██╗  ██████╗  ██████╗  ██████╗   ███████╗ ██████╗ ',
    ' ████╗ ████║ ██║ ████╗  ██║ ██║ ██╔════╝ ██╔═══██╗ ██╔══██╗  ██╔════╝ ██╔══██╗',
    ' ██╔████╔██║ ██║ ██╔██╗ ██║ ██║ ██║      ██║   ██║ ██║   ██║ █████╗   ██████╔╝',
    ' ██║╚██╔╝██║ ██║ ██║╚██╗██║ ██║ ██║      ██║   ██║ ██║  ██╔╝ ██╔══╝   ██╔══██╗',
    ' ██║ ╚═╝ ██║ ██║ ██║ ╚████║ ██║ ╚██████╗ ╚██████╔╝ █████╔═╝  ███████╗ ██║  ██║',
    ' ╚═╝     ╚═╝ ╚═╝ ╚═╝  ╚═══╝ ╚═╝  ╚═════╝  ╚═════╝  ╚════╝    ╚══════╝ ╚═╝  ╚═╝',
]

box_style = Style.from_dict({
    "frame.border": "#575557",
    "selected-option": "bold",
    "bottom-toolbar": "#ffffff bg:#333333 noreverse"
})

poems = (
	"春风又绿江南岸，明月何时照我还。",
	"人生自古谁无死？留取丹心照汗青。",
	"日月之行，若出其中；星汉灿烂，若出其里。",
	"老骥伏枥，志在千里；烈士暮年，壮心不已。",
	"天苍苍，野茫茫，风吹草低见牛羊。",
	"小荷才露尖尖角，早有蜻蜓立上头。",
	"少壮不努力，老大徒伤悲。",
	"不识庐山真面目，只缘身在此山中。",
	"春去花还在，人来鸟不惊。",
	"春色满园关不住，一枝红杏出墙来。",
	"草长莺飞二月天，拂堤杨柳醉春烟。",
	"水光潋滟晴方好，山色空濛雨亦奇。",
	"儿童急走追黄蝶，飞入菜花无处寻。",
	"千磨万击还坚劲，任尔东西南北风。",
	"接天莲叶无穷碧，映日荷花别样红。",
	"出师一表真名世，千载谁堪伯仲间。",
	"吾家洗砚池头树，个个花开淡墨痕。",
	"竹外桃花三两枝，春江水暖鸭先知。",
	"王师北定中原日，家祭无忘告乃翁。",
	"千门万户曈曈日，总把新桃换旧符。",
	"山外青山楼外楼，西湖歌舞几时休。",
	"夜阑卧听风吹雨，铁马冰河入梦来。",
	"等闲识得东风面，万紫千红总是春。",
	"生当做人杰，死亦为鬼雄。",
	"采菊东篱下，悠然见南山。",
	"我自横刀向天笑，去留肝胆两昆仑。",
	"小楼一夜听春雨，深巷明朝卖杏花。",
	"梅须逊雪三分白，雪却输梅一段香。",
	"春宵一刻值千金，花有清香月有阴。",
	"荷尽已无擎雨盖，菊残犹有傲霜枝。",
	"涉江采芙蓉，兰泽多芳草。",
	"胡马依北风，越鸟巢南枝。",
	"解把飞花蒙日月，不知天地有清霜。",
	"墙角数枝梅，凌寒独自开。",
	"月黑见渔灯，孤光一点萤。",
	"黄梅时节家家雨，青草池塘处处蛙。",
	"好峰随处改，幽径独行迷。",
	"落红不是无情物，化作春泥更护花。",
	"秋风萧瑟天气凉，草木摇落露为霜。",
	"天地神灵扶庙社，京华父老望和銮。",
	"云淡风轻近午天，傍花随柳过前川。",
	"宁可枝头抱香死，何曾吹落北风中。",
	"人生到处知何似，应似飞鸿踏雪泥。",
	"南国有佳人，容华若桃李。",
	"昆仑之高有积雪，蓬莱之远常遗寒。",
	"白鸟一双临水立，见人惊起入芦花。",
	"子规夜半犹啼血，不信东风唤不回。",
	"江山代有才人出，各领风骚数百年。",
	"风日晴和人意好，夕阳箫鼓几船归。",
	"为天地立心，为生民立命，为往圣继绝学，为万世开太平。",    
)

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
    ):
        self.record = record
        self.console = Console(width=width, record=record)
        self.version = version or "0.1.0"
        self.llm = llm or OpenAILLM()
        self.history_path = str(Path(__file__).parent.parent / ".chat-history")
        if not os.path.exists(self.history_path):
            open(self.history_path, 'w').close()
        self.session = PromptSession(show_frame=~is_done, history=FileHistory(self.history_path))

    def set_llm(self, llm: OpenAILLM):
        self.llm = llm
    
    def warning(self, data: str):
        self.console.print(f"\n[yellow][{time_now()}]⚠️\x20\x20警告提醒:\n\r{data}[/yellow]")

    def error(self, data: str):
        self.console.print(f"\n[red][{time_now()}]❌\x20执行出错:\n\r{data}[/red]")
    
    def output(self, data: str):
        md_data = Markdown(data)
        self.console.print(f"\n[white][{time_now()}]🖨️\x20\x20模型输出:[/white]")
        self.console.print(md_data, style="white")

    def result(self, data: str):
        md_data = Markdown(data)
        self.console.print(f"\n[magenta][{time_now()}]🎉\x20最终结果:[/magenta]")
        self.console.print(md_data, style="magenta")

    def tool(self, data: str):
        self.console.print(f"\n[dark_goldenrod][{time_now()}]🛠️\x20\x20工具调用:\n\r{data}[/dark_goldenrod]")

    def update(self, data: str):
        self.console.print(f"\n[blue][{time_now()}]📝\x20状态更新:\n\r{data}[/blue]")

    def subagent(self, data: str):
        self.console.print(f"\n[cadet_blue][{time_now()}]👽\x20子智能体:\n\r{data}[/cadet_blue]")
    
    def input(self) -> str:
        response = self.session.prompt("> ", 
            style=box_style,
            placeholder=f"  请欣赏古诗词：{random.choice(poems)}",
            bottom_toolbar=HTML(f"权限模式：{get_permission_mode()} | 语言模型：{self.llm.get_provider()} | 帮助信息：/help")
        )
        self.console.print(f"\n[green][{time_now()}]🎙️\x20\x20用户输入:\n\r{response}[/green]")
        return response.strip()

    def show_user_input(self, message: str):
        self.console.print(f"\n[green][{time_now()}]🎙️\x20\x20用户输入:\n\r{message}[/green]")
    
    def confirm(self, question: str) -> bool:
        response = Confirm.ask("\n" + question)
        self.console.print(f"\n[green][{time_now()}]🖱️\x20\x20用户确认:\n\r{response}[/green]")
        return response

    def choose(self, message: str, options: List|Tuple) -> str:
        response = choice(
            message=message,
            options=[(r, r) for r in options],
            style = box_style, 
            show_frame=~is_done,
            bottom_toolbar=HTML(" <b>[Up]</b>/<b>[Down]</b> 浏览 | <b>[Enter]</b> 确认")
        )
        self.console.print(f"\n[green][{time_now()}]🖱️\x20\x20用户选择:\n\r{response}[/green]")
        return response

    def bye(self):
        with Status(status="正在保存会话历史，期待下次再见！！！", spinner="clock") as status:
            status.start()
            self.show_usage()
            self.save_trajectory()
            time.sleep(3)
    
    def save_trajectory(self):
        if not self.record:
            return
        from src.paths import get_trajectory_dir
        path = get_trajectory_dir() / f"record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        data = self.console.export_html()
        with open(path, "w") as f:
            f.write(data)
    
    def show_usage(self):
        total_tokens = self.llm.input_tokens + self.llm.output_tokens
        cached_tokens = self.llm.cache_hit_tokens + self.llm.cache_miss_tokens
        usage_info = (
            f"\n[cadet_blue][主智能体词元使用量统计]"
            f"\n输入 {_convert_num(self.llm.input_tokens)} tokens"
            f"\n输出 {_convert_num(self.llm.output_tokens)} tokens"
            f"\n总共 {_convert_num(total_tokens)} tokens"
        )
        if cached_tokens > 0:
            cached_ratio = (100 * cached_tokens / self.llm.input_tokens)
            cache_hit_ratio = (100 * self.llm.cache_hit_tokens / cached_tokens)
            usage_info += f"\n输入缓存 {_convert_num(cached_tokens)} tokens（缓存率为 {cached_ratio:.2f} %）"
            usage_info += f"\n缓存命中 {_convert_num(self.llm.cache_hit_tokens)} tokens, "
            usage_info += f"未命中 {_convert_num(self.llm.cache_miss_tokens)} tokens"
            usage_info += f"（缓存命中率为 {cache_hit_ratio:.2f} %）"
        usage_info += "[/cadet_blue]"
        self.console.print(usage_info)
        
    def show_banner(self):
        logo = '\n'.join(minicoder_logo)
        self.console.print(f"[cyan]{'-'*80}\n\n{logo}\n[/cyan]")
        self.console.print(f"[green bold] 当前版本: [/green bold]{self.version}")
        self.console.print(f"[green bold] 权限模式: [/green bold]{get_permission_mode()}")
        self.console.print(f"[green bold] 语言模型: [/green bold]{self.llm.get_provider()}")
        self.console.print(f"[green bold] 项目路径: [/green bold]{get_project_root()}")
        self.console.print(f"[cyan]{'-'*80}[/cyan]")

# minicoder：一个由大语言模型驱动的简易编程助手

## 主要特性

- 提供基于 Rich 和 Prompt-toolkit 库的 TUI 交互式界面      
- 内置 Bash、Read、Write、Edit、Glob、Grep 等文件读写改搜的基础工具     
- 支持 Default、Auto、Plan 三种权限模式     
- 支持渐进式加载 Skills 技能的功能     
- 支持路径沙箱检查的功能，确保工具访问不越界    
- 支持上下文超限触发自动压缩的功能    
- 支持根据工具函数 docstring 自动推导 schema 的功能，方便拓展工具集合     
- 支持任务自动拆解和全流程状态跟踪的功能，创建 TODOs 列表，确保目标任务不漂移    
- 支持按需保存记忆，和跨会话复用记忆的功能，保留用户偏好信息    
- 支持工具输出结果的大尺寸文件落盘持久化，仅返回预览版本和引用链接的功能     
- 支持创建子智能体执行任务，隔离父智能体上下文的功能    
- 支持自动导出用户和编程助手交互过程的轨迹文件的功能     
- 支持大模型访问失败自动重试的功能    
- 支持统计大模型 tokens 消耗量和缓存命中率的功能   
- 支持 Bash 高危命令黑名单的功能    
- 支持系统提示词按需组装的功能    


## 快速开始

### 1、安装

```bash
git clone git@github.com:cao-jicheng/minicoder.git

cd minicoder/

uv sync
```

### 2、配置大模型

在 `minicoder` 文件中新建 `.env` 文件，填入 LLM_MODEL、LLM_BASE_URL、LLM_API_KEY 信息。

```bash
LLM_MODEL=Pro/MiniMaxAI/MiniMax-M2.5
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_API_KEY=sk-xxx
```

注意：minicoder 目前只支持 OpenAI Compatible 格式的 API 调用。

### 3、运行 minicoder

```bash
cd minicoder/

uv run minicoder
```

以上命令会启动交互式终端界面，在最下面一行输入你的问题，和编程助手交互。输入 `/help` 可查看 minicoder 支持哪些交互命令，输入 `bye` 可退出会话界面。

### 4、查看轨迹文件

退出会话界面后，在你的项目根目录的 .trajectory 文件夹（默认是 ~/.minicoder/.trajectory）可查看类似 `record_xxxxxxxx_yyyyyy.html` 的轨迹文件，
它记录了你在会话界面和编程助手交互的每一次操作。轨迹文件中 “xxxxxxxx” 表示保存时的日期（例如 20260411），“yyyyyy” 表示保存时的时间（例如 182512）。

### 5、命令行参数

输入`uv run minicoder --help` 查看 minicoder 在启动时，可以设置哪些命令行参数。


## 致谢

本项目的代码实现部分参考了 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)。

感谢 learn-claude-code 项目组提供的珍贵的学习材料！！！
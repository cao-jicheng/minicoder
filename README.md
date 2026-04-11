# minicoder：一个由大语言模型驱动的简易编程助手

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
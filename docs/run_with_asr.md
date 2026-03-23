# 🎙️ 带有语音识别 (ASR) 的运行指南

本项目现在集成了本地语音识别功能，依赖于底层的 SenseVoice 模型。由于 ASR 模型与其他业务组件具有不同的环境依赖策略（ASR 运行在专门的 `agent` conda 环境，而主程序运行在 `uv` 环境下），你需要分别启动它们。

## 1. 启动本地 ASR 服务 (Conda `agent` 环境)

为了不跟主程序的依赖冲突，语音识别服务需要在单独配置了 CUDA 和深度学习依赖的 conda 环境中运行，并占用 `8001` 端口。

打开一个新的终端窗口：

```bash
# 激活 agent 环境
conda activate agent

# 进入项目根目录
cd D:\project\emotional_companion

# 使用 uvicorn 启动 ASR 服务，指定端口为 8001
uvicorn asr.sensevoice:app --host 127.0.0.1 --port 8001
```

启动成功后，你将看到类似 `Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)` 的提示。

## 2. 启动主 Web 服务 (UV 环境)

主程序仍然使用原有的 `uv` 环境，它将在 `8000` 端口启动，并将前端的语音请求转发给后端的 ASR 服务。

在**另一个终端窗口**中：

```bash
# 进入项目根目录
cd D:\project\emotional_companion

# 运行主程序 Web API 模式
uv run python main.py --mode api
```

## 3. 使用方法

1. 在浏览器中打开 http://127.0.0.1:8000
2. 在底部的输入框旁边，你将看到一个 **🎤 麦克风** 按钮。
3. 点击麦克风按钮，授权浏览器使用录音功能后，按钮会闪烁（表示正在录音）。
4. 再次点击麦克风按钮即可结束录音。
5. 系统会自动将音频上传至主服务并转发至 ASR 服务，识别出文本后会自动发送至对话中。

## 故障排除

* **麦克风无响应**：请确保你的浏览器授予了网页录音权限，某些浏览器要求必须使用 `http://127.0.0.1` 或是 `https://` 协议才会开启麦克风权限。
* **语音识别返回错误**：请检查第一步中的 ASR 服务终端是否输出了错误（如显存不足）。默认使用 `device="cuda:0"` 进行推理，如果没有独立显卡可能会失败，可以修改 `asr/sensevoice.py` 里的配置以回退到 CPU。
# 🚀 EmotionAgent API 使用指南

本指南详细说明了 EmotionAgent 系统中各模块的 API 接口、数据流向以及 3D 数字人（Three.js）的集成方式。

## 1. 核心架构概述

系统采用 **“感知 -> 认知 -> 干预”** 的主动式闭环设计：
- **感知层 (Perception)**: 提取情绪、压力源。
- **认知层 (Cognition)**: 评估心理状态与风险。
- **干预层 (Intervention)**: 生成共情回复与干预策略。

---

## 2. 后端 API 接口 (FastAPI)

### 2.1 ASR 语音识别
- **Endpoint**: `POST /api/asr`
- **输入**: `.webm` 或 `.wav` 音频文件。
- **输出**: `{"text": "识别出的文字", "emotion": "识别的情感"}`。

### 2.2 情感对话 (Chat)
- **Endpoint**: `POST /api/chat` (或 WebSocket `ws://...`)
- **Payload**: `{"text": "用户输入", "session_id": "..."}`
- **输出**: SSE 流式输出干预话术及 `structured_payload`。

---

## 3. 3D 数字人集成 (Three.js)

### 3.1 A2F 实时驱动
系统通过 WebSocket 连接 NVIDIA Audio2Face (A2F) 服务端：
- **A2F 地址**: `ws://localhost:9001`
- **数据协议**:
  - `is_bs:1|w0,w1,w2...`: 52 维 ARKit Blendshape 权重字符串。

### 3.2 前端渲染 (Three.js)
- **组件位置**: `frontend/src/components/views/Avatar3D.tsx`
- **渲染流程**:
  1. 建立 A2F WebSocket 连接。
  2. 接收权重数据帧。
  3. 将权重应用至 Three.js 模型的 `morphTargetInfluences`。

---

## 4. 开发与部署

### 4.1 环境要求
- **Python**: 3.10+ (使用 `uv` 管理)
- **Node.js**: 18+ (Vite)
- **NVIDIA Audio2Face**: 需运行 SDK 服务端以支持实时面部驱动。

### 4.2 快速启动 (多终端运行)

为确保系统完整运行，建议依次打开 **4 个终端** 执行以下命令：

#### 终端 1: 后端主服务 (LLM + LangGraph)
处理对话逻辑、情感分析与干预计划生成。
```bash
# 根目录下执行
uv run python main.py --mode api
```

#### 终端 2: 前端开发服务器 (Three.js UI)
提供用户界面与数字人渲染环境。
```bash
# 进入 frontend 目录执行
cd frontend
npm run dev
```

#### 终端 3: ASR 语音识别服务 (SenseVoice)
将用户语音实时转为文本并识别初始情感。
```bash
# 根目录下执行 (根据硬件选择)
# N卡 GPU/Torch 模式:
uvicorn asr.sensevoice:app --host 127.0.0.1 --port 8001
# 或 ONNX CPU 模式:
# uvicorn asr.sensevoice_onnx:app --host 127.0.0.1 --port 8001
```

#### 终端 4: Audio2Face (A2F) SDK 服务端
处理音频到面部权重 (Blendshape) 的实时转换。
# 切换到 SDK 根目录（模型路径依赖）
cd D:\Audio2Face-3D-SDK-main\Audio2Face-3D-SDK-main

# 启动服务
.\_build\release\audio2face-sdk\bin\a2f-server.exe
```

---

## 5. 最近更新 (2026-03-25)
- **架构重构**: 彻底移除 Unity 渲染引擎，全面转向 **Three.js** 路线。
- **UI 优化**: 重新设计了 `ChatView` 布局，在右侧为 Three.js 数字人预留了专属渲染区域。
- **依赖清理**: 卸载了 `react-unity-webgl` 依赖，确保环境轻量化。

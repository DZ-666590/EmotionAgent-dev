# Audio2Face 实时数字人 API 使用文档

## 概述

本系统集成了 NVIDIA Audio2Face 3D SDK，实现了**文本 → 语音 → 面部动画**的完整实时流水线。前端可以通过 REST API 和 WebSocket 获取同步的音频流与 3D 面部几何数据，用于驱动数字人头像。

---

## 系统架构

```
┌─────────────┐     HTTP/WS      ┌──────────────┐      TCP       ┌─────────────┐
│   前端应用   │ ◄─────────────► │  FastAPI     │ ◄────────────► │  C++ A2F    │
│  (浏览器)    │                 │  Python 服务  │                │  推理服务    │
└─────────────┘                 └──────────────┘                └─────────────┘
      │                               │                               │
      │  1. POST /api/a2f/speak       │                               │
      │  2. WS /api/a2f/ws            │   TCP 9001                    │
      │                               │   PCM 音频 ─────────────────► │
      │  ◄── 音频流 (MP3)             │                               │
      │  ◄── geometry 帧 (WS)         │   ◄─────────────── 几何帧     │
      └───────────────────────────────┴───────────────────────────────┘
```

---

## 快速开始

### 1. 启动 C++ 推理服务

```powershell
# 切换到 SDK 根目录（模型路径依赖）
cd D:\Audio2Face-3D-SDK-main\Audio2Face-3D-SDK-main

# 启动服务
.\_build\release\audio2face-sdk\bin\a2f-server.exe
```

服务启动后监听 `127.0.0.1:9001`。

### 2. 启动 Python API 服务

```powershell
# 切换到项目目录
cd E:\EmotionAgent-dev

# 使用项目虚拟环境启动 FastAPI
.\.venv\Scripts\uvicorn.exe src.interfaces.api:app --host 0.0.0.0 --port 8000
```

### 3. 验证服务

- **API 文档**: http://localhost:8000/docs
- **健康检查**: 浏览器访问 http://localhost:8000

---

## API 端点详解

### POST `/api/a2f/speak`

**功能**: 文本转语音 + 面部动画生成

**请求体**:
```json
{
  "text": "你好，我是你的数字人助手。",
  "voice": "zh-CN-XiaoxiaoNeural"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | ✅ | - | 要合成的文本内容 |
| `voice` | string | ❌ | `zh-CN-XiaoxiaoNeural` | Edge TTS 语音模型 |

**可用语音**:
- `zh-CN-XiaoxiaoNeural` - 中文女声（默认）
- `zh-CN-YunxiNeural` - 中文男声
- `zh-CN-YunyangNeural` - 中文男声（新闻风格）
- `en-US-JennyNeural` - 英文女声
- `en-US-GuyNeural` - 英文男声

**响应**: 流式 MP3 音频 (`audio/mpeg`)

**cURL 示例**:
```bash
curl -X POST "http://localhost:8000/api/a2f/speak" \
  -H "Content-Type: application/json" \
  -d '{"text": "你好世界"}' \
  --output test.mp3
```

**PowerShell 示例**:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/a2f/speak" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"text": "你好世界"}' `
  -OutFile "test.mp3"
```

**JavaScript 示例**:
```javascript
const response = await fetch('/api/a2f/speak', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: '你好世界' })
});

const audioBlob = await response.blob();
const audioUrl = URL.createObjectURL(audioBlob);
const audio = new Audio(audioUrl);
audio.play();
```

---

### WebSocket `/api/a2f/ws`

**功能**: 实时接收面部几何帧数据

**连接**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/a2f/ws');
```

**接收消息类型**:

#### 1. 几何帧 (`frame`)
```json
{
  "type": "frame",
  "index": 0,
  "geometry": [0.123, -0.456, 0.789, ...],
  "size": 184560
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `index` | int | 帧序号 (0-based) |
| `geometry` | float[] | 3D 顶点坐标数组 |
| `size` | int | 数组长度 (61520 顶点 × 3 坐标 = 184560) |

#### 2. 完成标记 (`done`)
```json
{
  "type": "done"
}
```

#### 3. 错误信息 (`error`)
```json
{
  "type": "error",
  "message": "Connection to A2F service failed"
}
```

#### 4. 心跳 (`ping` / `pong`)
```json
{"type": "ping"}
{"type": "pong"}
```

**完整示例**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/a2f/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'frame':
      // 更新 3D 模型顶点
      updateAvatarGeometry(data.geometry);
      console.log(`Frame ${data.index}: ${data.size} floats`);
      break;
      
    case 'done':
      console.log('Animation complete');
      break;
      
    case 'error':
      console.error('A2F Error:', data.message);
      break;
      
    case 'ping':
      ws.send(JSON.stringify({ type: 'pong' }));
      break;
  }
};

// 保持连接：定期发送心跳
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send('ping');
  }
}, 30000);
```

---

### POST `/api/chat`

**功能**: AI 情感陪伴对话（SSE 流式响应）

**请求体**:
```json
{
  "message": "我今天心情不太好",
  "history": [],
  "session_id": "user_123"
}
```

**响应**: Server-Sent Events (SSE)

```
data: {"type": "status", "content": "正在提取多模态情绪特征..."}
data: {"type": "internal_state", "data": {...}}
data: {"type": "chunk", "content": "我"}
data: {"type": "chunk", "content": "理解"}
data: {"type": "done"}
```

---

### GET `/api/tts/stream`

**功能**: 纯 TTS 流式音频（不触发 A2F）

**参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | ✅ | - | 要合成的文本 |
| `voice` | string | ❌ | `zh-CN-XiaoxiaoNeural` | 语音模型 |

**示例**:
```
GET /api/tts/stream?text=你好世界&voice=zh-CN-YunxiNeural
```

---

### POST `/api/asr`

**功能**: 语音转文本

**请求**: `multipart/form-data`，字段 `file` 为音频文件

**响应**:
```json
{
  "text": "识别出的文本内容",
  "emotion": "happy",
  "emotion_confidence": 0.85
}
```

---

### POST `/api/vision`

**功能**: 图像情绪检测

**请求**: `multipart/form-data`，字段 `file` 为图片文件

**响应**:
```json
{
  "status": "success",
  "visual_emotion": "happy",
  "confidence": 0.92,
  "message": "视觉帧已接收并记录"
}
```

---

## 完整集成示例

### 前端 JavaScript 控制器

```javascript
class DigitalHumanController {
  constructor(avatarMesh) {
    this.avatarMesh = avatarMesh;
    this.ws = null;
    this.audio = null;
    this.frameBuffer = [];
    this.isPlaying = false;
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket('ws://localhost:8000/api/a2f/ws');
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        resolve();
      };
      this.ws.onerror = (e) => reject(e);
      this.ws.onmessage = (event) => this.handleMessage(JSON.parse(event.data));
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        // 自动重连
        setTimeout(() => this.connect(), 2000);
      };
    });
  }

  handleMessage(data) {
    switch (data.type) {
      case 'frame':
        this.frameBuffer.push(data);
        break;
      case 'done':
        console.log(`Received ${this.frameBuffer.length} frames`);
        this.startAnimation();
        break;
      case 'error':
        console.error('A2F Error:', data.message);
        break;
      case 'ping':
        this.ws.send('pong');
        break;
    }
  }

  async speak(text, voice = 'zh-CN-XiaoxiaoNeural') {
    // 清空帧缓冲
    this.frameBuffer = [];
    this.isPlaying = false;

    // 请求 TTS + A2F
    const response = await fetch('/api/a2f/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice })
    });

    // 播放音频
    const audioBlob = await response.blob();
    this.audio = new Audio(URL.createObjectURL(audioBlob));
    
    // 音频开始播放时启动动画
    this.audio.onplay = () => {
      if (this.frameBuffer.length > 0 && !this.isPlaying) {
        this.startAnimation();
      }
    };
    
    this.audio.play();
  }

  startAnimation() {
    if (this.isPlaying || this.frameBuffer.length === 0) return;
    this.isPlaying = true;

    const fps = 60;
    const frameDuration = 1000 / fps;
    let frameIndex = 0;
    
    const animate = () => {
      if (frameIndex < this.frameBuffer.length) {
        this.updateGeometry(this.frameBuffer[frameIndex].geometry);
        frameIndex++;
        setTimeout(animate, frameDuration);
      } else {
        this.isPlaying = false;
      }
    };
    
    animate();
  }

  updateGeometry(geometry) {
    // geometry 格式: [x0, y0, z0, x1, y1, z1, ...]
    const positions = this.avatarMesh.geometry.attributes.position;
    
    for (let i = 0; i < geometry.length; i++) {
      positions.array[i] = geometry[i];
    }
    
    positions.needsUpdate = true;
  }
}

// 使用示例
const controller = new DigitalHumanController(avatarMesh);
await controller.connect();
await controller.speak('你好，欢迎使用数字人系统！');
```

### Three.js 渲染器

```javascript
import * as THREE from 'three';

// 创建场景
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// 创建 61520 顶点的面部几何体
const geometry = new THREE.BufferGeometry();
const vertexCount = 61520;
const positions = new Float32Array(vertexCount * 3);
geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

// 材质
const material = new THREE.MeshStandardMaterial({
  color: 0xffcc99,
  flatShading: false,
  side: THREE.DoubleSide
});

// 网格
const avatarMesh = new THREE.Mesh(geometry, material);
scene.add(avatarMesh);

// 光照
const ambientLight = new THREE.AmbientLight(0x404040);
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
directionalLight.position.set(1, 1, 1);
scene.add(directionalLight);

// 相机位置
camera.position.z = 5;

// 渲染循环
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
```

---

## 数据格式说明

### 几何数据结构

每帧返回的 `geometry` 数组包含 **184,560 个 float32 值**：

```
geometry = [
  x0, y0, z0,  // 顶点 0
  x1, y1, z1,  // 顶点 1
  ...
  x61519, y61519, z61519  // 顶点 61519
]
```

- **顶点数量**: 61,520
- **每顶点坐标**: 3 (x, y, z)
- **数据类型**: float32
- **帧率**: 60 FPS

### 音频格式

| 阶段 | 格式 | 采样率 | 通道 |
|------|------|--------|------|
| TTS 输出 | MP3 | 可变 | 单声道 |
| A2F 输入 | PCM float32 | 16000 Hz | 单声道 |

---

## Python SDK 直接使用

如果需要在 Python 代码中直接调用（不通过 HTTP API）：

```python
import asyncio
import numpy as np
from src.services.a2f_bridge import get_a2f_bridge

async def main():
    bridge = get_a2f_bridge()
    
    # 方式 1: 从 MP3 文件处理
    with open('audio.mp3', 'rb') as f:
        mp3_data = f.read()
    
    frames = await bridge.process_audio(mp3_data)
    print(f'生成 {len(frames)} 帧动画')
    
    # 方式 2: 直接提供 PCM 数据
    pcm_data = np.random.randn(16000).astype(np.float32)  # 1秒音频
    pcm_data = np.clip(pcm_data * 0.1, -1.0, 1.0)  # 归一化
    
    frames = await bridge.process_pcm(pcm_data)
    
    # 处理每一帧
    for frame in frames:
        print(f'Frame {frame.frame_index}: {len(frame.geometry)} floats')
        vertices = frame.geometry.reshape(-1, 3)  # (61520, 3)
        # ... 渲染或保存

asyncio.run(main())
```

---

## 错误处理

### 常见错误

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `Connection to A2F service failed` | C++ 服务未启动 | 启动 `a2f-server.exe` |
| `Failed to connect to A2F service` | 端口被占用或防火墙 | 检查 9001 端口 |
| `文本内容不能为空` | 请求体 text 为空 | 提供非空文本 |
| `ffmpeg not found` | 缺少 ffmpeg | `winget install ffmpeg` |
| `No module named 'soundfile'` | 缺少依赖 | `pip install soundfile scipy` |

### 健壮性建议

```javascript
// 自动重连 WebSocket
function createReconnectingWebSocket(url, maxRetries = 5) {
  let retries = 0;
  let ws;

  function connect() {
    ws = new WebSocket(url);
    
    ws.onopen = () => {
      retries = 0;
      console.log('WebSocket connected');
    };
    
    ws.onclose = () => {
      if (retries < maxRetries) {
        retries++;
        console.log(`Reconnecting... (${retries}/${maxRetries})`);
        setTimeout(connect, 1000 * retries);
      }
    };
    
    return ws;
  }

  return connect();
}
```

---

## 性能参数

| 指标 | 数值 |
|------|------|
| TTS 延迟 | ~200-500ms（取决于文本长度） |
| A2F 推理延迟 | ~100-300ms（GPU 加速） |
| 帧率 | 60 FPS |
| 每帧数据量 | ~720 KB (184560 × 4 bytes) |
| WebSocket 带宽 | ~43 MB/s (满帧率时) |

---

## 环境依赖

### Python 环境 (.venv)

```bash
# 核心依赖
pip install fastapi uvicorn edge-tts numpy loguru

# 音频处理（Python 3.13 兼容）
pip install soundfile scipy

# ffmpeg（系统级，用于 MP3 解码）
winget install ffmpeg
```

### C++ 服务

- NVIDIA GPU (CUDA 支持)
- Audio2Face 3D SDK 模型文件
- Visual Studio 2022 运行时

### 端口占用

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI | 8000 | HTTP/WebSocket API |
| A2F C++ | 9001 | TCP 推理服务 |
| ASR 服务 | 8001 | 语音识别（可选） |

---

## 注意事项

1. **内存管理**: 每帧 geometry 数据较大（~720KB），前端应及时释放不需要的帧
2. **音视频同步**: 使用 `requestAnimationFrame` 配合音频 `currentTime` 实现精确同步
3. **网络延迟**: WebSocket 帧到达时间可能不均匀，建议使用缓冲队列
4. **GPU 负载**: A2F 推理会占用 GPU 资源，避免同时运行其他 GPU 密集任务
5. **Python 版本**: 项目使用 Python 3.13，需使用 `soundfile` + `scipy` 替代 `pydub`（因 `audioop` 已移除）

---

## 文件结构

```
E:\EmotionAgent-dev\
├── src\
│   ├── interfaces\
│   │   ├── api.py           # FastAPI 主入口
│   │   ├── API_USAGE.md     # 本文档
│   │   └── cli.py           # 命令行接口
│   └── services\
│       └── a2f_bridge.py    # A2F TCP 桥接客户端
└── .venv\                   # Python 虚拟环境

D:\Audio2Face-3D-SDK-main\Audio2Face-3D-SDK-main\
├── _build\release\
│   └── audio2face-sdk\bin\
│       └── a2f-server.exe   # C++ 推理服务
└── _data\generated\
    └── audio2face-sdk\samples\data\mark\
        └── model.json       # 面部模型
```

---

## 版本信息

- API 版本: 1.0.0
- Python: 3.13
- Audio2Face SDK: 3D (Bundle API)
- 最后更新: 2025年

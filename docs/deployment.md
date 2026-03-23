# 📦 项目部署指南

本指南介绍如何下载和部署 AI 情感陪护智能体系统。

## 📥 下载项目

### 方式一：Git 克隆（推荐）

```bash
git clone https://github.com/your-username/emotional_companion.git
cd emotional_companion
```

### 方式二：下载 ZIP 包

1. 在 GitHub 页面点击 "Code" -> "Download ZIP"
2. 解压到本地目录
3. 进入项目目录

## 🚀 快速部署

### 1. 环境准备

本项目使用 [uv](https://github.com/astral-sh/uv) 作为包管理器：

```bash
# 安装 uv (Windows)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或者使用 pip
pip install uv
```

### 2. 安装依赖

```bash
# 进入项目目录
cd emotional_companion

# 安装 Python 依赖
uv sync
```

### 3. 配置环境变量

复制环境变量模板并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写您的 DeepSeek API Key：

```env
API_KEY="sk-your-deepseek-api-key"
LITELLM_MODEL="deepseek/deepseek-chat"
```

### 4. 启动服务

#### 后端服务

```bash
# 启动 API 服务（端口 8002）
uv run python main.py --mode api
```

访问: http://127.0.0.1:8002

#### 前端服务

前端构建产物已包含在项目中（`frontend/dist`），可以直接使用：

**方式一：使用内置的静态文件服务（推荐）**

后端服务已配置自动服务 `frontend/dist` 目录，访问 http://127.0.0.1:8002 即可看到前端界面。

**方式二：开发模式（需要 Node.js）**

```bash
cd frontend
npm install
npm run dev
```

访问: http://localhost:5173

#### ASR 语音识别服务（可选）

如需语音识别功能，需要额外启动 ASR 服务：

```bash
# 需要 CUDA 环境
uvicorn asr.sensevoice:app --host 127.0.0.1 --port 8001
```

## 🐳 Docker 部署（推荐生产环境）

### 1. 构建镜像

```bash
docker build -t emotional-companion .
```

### 2. 运行容器

```bash
docker run -d \
  -p 8002:8002 \
  -v $(pwd)/.env:/app/.env \
  --name emotional-companion \
  emotional-companion
```

### 3. 访问服务

浏览器访问: http://your-server-ip:8002

## 📋 部署检查清单

- [ ] Python 3.10+ 已安装
- [ ] uv 包管理器已安装
- [ ] DeepSeek API Key 已配置
- [ ] 端口 8002 未被占用
- [ ] 如需 ASR，确保 CUDA 环境可用

## 🔧 生产环境配置

### 使用 Gunicorn（替代 uvicorn）

```bash
uv pip install gunicorn

gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8002
```

### 设置环境变量

```bash
export API_KEY="your-api-key"
export LITELLM_MODEL="deepseek/deepseek-chat"
export ENVIRONMENT=production
```

## 📝 故障排除

### 1. 端口被占用

```bash
# Windows
netstat -ano | findstr :8002

# Linux/Mac
lsof -i :8002
```

### 2. 依赖安装失败

```bash
# 清理并重试
uv pip uninstall -r requirements.txt
uv sync
```

### 3. 前端无法访问

确保 `frontend/dist` 目录存在且包含以下文件：
- `index.html`
- `assets/` 目录
- `favicon.svg`

### 4. ASR 服务启动失败

检查 CUDA 是否可用：
```python
import torch
print(torch.cuda.is_available())
```

如无 GPU，修改 `asr/sensevoice.py` 中的设备设置为 CPU。

## 📚 相关文档

- [运行指南（带 ASR）](run_with_asr.md)
- [架构说明](architecture.md)

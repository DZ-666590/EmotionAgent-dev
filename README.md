# 🤖 AI 情感陪护智能体系统 (Emotional Companion)

本项目是一个基于大语言模型（LLM）、LangGraph 和心理学机制的专用 AI 情感陪护与干预系统。
系统以数字人为核心场景设计，构建了一个数据驱动的 **“感知 -> 认知 -> 干预”** 主动式闭环。

默认底层模型使用 `DeepSeek` (通过 `LiteLLM` 进行通用调度)，采用严密的模块化与状态机编排，保证了逻辑的可解释性与回复的极度共情力。

---
待完成：
[x] ASR语音识别
[x] SER情感识别
[x] 视频/图片识别
[x] 多模态融合
[x] 提示词优化
[x] 情感干预工具
[x] RAG知识库
[x] 仪表盘
[x] 前端
[x] 数字人
[x] 重构，精简
[x] 性能优化

---

## 🌟 核心特性

- 🔄 **三段式心理闭环机制**:
  - **👁️ 感知层 (Perception)**: 从多模态输入（当前为文本流，已预留 `modality` 扩展）中提取用户的核心情绪、强度、症状线索与压力源。
  - **🧠 认知层 (Cognition)**: 基于提取的情感信号，评估用户的整体心理状态（如焦虑倾向、抑郁倾向、双向风险），不作医疗诊断，仅作干预研判。
  - **⚡ 干预层 (Intervention)**: 类似于“心理督导”角色，根据认知状态评估出安全风险等级（`Safety Gate`），生成专业且极具同理心的干预策略和话术方向。
- ⚡ **流式数字人输出**: 干预计划生成后，交给生成服务进行 SSE 流式输出，保证 C 端用户的打字机极速体验。已预留 `structured_payload` 给后续的 TTS 和 3D 骨骼表情驱动。
- 🛠️ **模块化与图状编排**: 业务逻辑与图解耦。通过 `LangGraph` 状态机流转 `CompanionGraphState` 数据，节点薄、服务厚，高度可维护。
- 📚 **本地知识库增强**: 支持基于 `knowledge_base/` 中的心理问答与治疗对话语料进行规则检索，把命中的知识片段注入认知评估、干预计划和最终回复。
- 🎨 **可解释性仪表盘**: 提供了一个开箱即用的前端 Web 界面，用户在对话时，能直观看到系统是如何评估“风险”、“症状”并实施“干预技术”的。

---

## 🚀 快速开始

### 1. 环境准备

本项目使用 [uv](https://github.com/astral-sh/uv) 作为极速包和环境管理器，请确保已安装。

```bash
# 1. 进入项目目录
cd emotional_companion

# 2. 安装并同步依赖
uv sync
```

### 2. 配置密钥

请将同级目录下的 `.env.example` 复制为 `.env`，并填入您的 DeepSeek API Key：

```bash
cp .env.example .env
```

`.env` 内容示例：
```env
API_KEY="sk-your-real-deepseek-api-key"
LITELLM_MODEL="deepseek/deepseek-chat"
```
*(由于引入了 LiteLLM，您也可以轻松切换至其他任意兼容模型)*

### 3. 运行应用

本项目提供两种交互方式，推荐使用交互体验极佳的 Web API 模式。

**后端:**
```bash
uv run python main.py --mode api
```
启动后，请在浏览器中访问: [http://127.0.0.1:8002](http://127.0.0.1:8002)

**前端:**
前端构建产物已包含在项目中（`frontend/dist`），后端服务会自动提供静态文件服务，无需额外启动前端服务。
如果您想使用开发模式（需要 Node.js）：
```bash
cd frontend
npm install
npm run dev
```
访问: http://localhost:5173

**ASR服务（可选）**
- N卡GPU/torch:
```bash
uvicorn asr.sensevoice:app --host 127.0.0.1 --port 8001
```
- ONNX (CPU)
```bash
uvicorn asr.sensevoice_onnx:app --host 127.0.0.1 --port 8001
```
  
---

## 📝 开发指南

### 1. 环境准备

本项目使用 [uv](https://github.com/astral-sh/uv) 作为极速包和环境管理器，请确保已安装。

```bash
# 1. 进入项目目录
cd emotional_companion

# 2. 安装并同步依赖
uv sync
```


```

---

## 🏗️ 架构说明

系统被精心设计为解耦的洋葱/领域驱动架构：

```text
src/
├── domain/       # 纯业务领域模型(Pydantic)与 LangGraph State定义，无任何框架依赖
├── providers/    # 大模型与第三方接口适配层 (LiteLLM的封装、结构化和流式输出处理)
├── services/     # 核心业务服务 (PerceptionService, KnowledgeService, CognitionService, InterventionService 等)
├── graph/        # LangGraph 状态机编排，定义边(Edges)与节点(Nodes)
└── interfaces/   # 暴露的交互层 (CLI, FastAPI流式路由, HTML/Tailwind前端)
```

### 多模态扩展指南
如需将文本转为语音/视频输入输出，只需进行以下扩充：
1. **输入**: 在 `PerceptionInput` 的 `modality` 字段扩展。新增预处理节点（如 ASR），将其文字或图像意图灌入 `PerceptionInput`，不影响后续闭环链路。
2. **输出**: 在 `CompanionResponse` 的 `structured_payload` 注入如表情指令、语气标注等元信息。前端通过解析这些 Payload 驱动 TTS 播放。

### 知识库扩展现状
当前版本已经接入了一个本地知识库检索层：
1. `PerceptionService` 先抽取情绪、症状、压力源等结构化信号。
2. `KnowledgeService` 基于这些信号从 `knowledge_base/` 中召回最相关的条目。
3. `CognitionService` 与 `InterventionService` 将检索结果作为参考上下文，提升评估与回复的一致性。
4. `OutputService` 在最终话术生成时继续参考这些片段，避免前后策略脱节。

如果后续需要升级到向量检索，只需保留 `KnowledgeService.retrieve` 接口，把内部实现替换为 Embedding + Vector Store 即可。

---

## 📜 更多文档

详细的工程说明与后续开发指南，请参阅：
- [部署指南](docs/deployment.md)
- [架构与模块扩展指南](docs/architecture.md)
- [运行指南（带 ASR）](docs/run_with_asr.md)


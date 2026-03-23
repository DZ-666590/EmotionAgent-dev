# 系统架构与模块扩展指南

本文档面向开发者，说明情感陪护智能体的内部架构原理以及未来可能的多模态及RAG（检索增强生成）扩展方式。

## 1. 为什么使用 LangGraph 状态机？
在心理辅助场景下，传统的“一问一答”式直接丢给大模型是不严谨且极不安全的。
系统必须有**主动的研判流**。通过状态机将思考过程强制解构为：
`感知 -> 认知 -> 安全门控(Safety Gate) -> 策略干预 -> 最终话术输出`

**带来的好处：**
- **安全拦截**：如果在 `认知阶段`（Cognition）打分判定为高危（如自残倾向），状态机内的 `safety_gate` 会瞬间将干预级别置为最高（escalation），要求最终生成的话术必须走危机话术底线，且不会生成随意的安慰。
- **结构化溯源**：对话出问题了？看一下当时的 `CompanionGraphState` 快照，就知道是感知层没提取到关键词，还是干预层选错了技术。

## 2. Pydantic 领域模型 (Domain)
所有的数据结构都在 `domain/models.py` 内。
*任何节点传递的数据都不应该是松散的字典。*

- **PerceptionInput**: 是对用户输入的抽象，包含了 `modality`（形态，比如as r/text/multimodal）。
- **PsychologicalAssessment**: 核心指标：焦虑风险(0-1)、抑郁风险(0-1)、双相风险(0-1)。
- **InterventionPlan**: 决定接下来的回复调性，它包含 `mode` (如 grounding正念接地、supportive共情支持) 以及 `constraints`（比如：严禁开处方药）。

## 3. LiteLLM 的封装逻辑
系统统一通过 `providers/llm_client.py` 包装 LiteLLM。
主要用到了两个模式：
1. **JSON 结构化输出模式** (`acompletion_structured`): 在认知和干预层调用，大模型的 temperature 会被设定得很低，强制输出准确的 JSON。
2. **文本流式生成模式** (`astream`): 仅在最终面向用户的话术层(`output_service.py`) 调用，具有较高的 temperature 以保证拟人化和温暖的口吻，返回的是极速的 Token 流。

## 4. 如何扩展 TTS 与数字人 (Digital Human)？
当前 `OutputService.generate_response_stream` 在响应历史消息后只输出了文字 Token。
要将其扩展为支持虚拟数字人驱动，您只需要：

**步骤 1**: 在 `domain/models.py` 的 `CompanionResponse` 内扩展 `structured_payload` 字段。
**步骤 2**: 在 `OutputService` 流式输出的末尾（或并行），根据当前的 `InterventionPlan.mode`，补充生成一个 JSON。
例如：
```json
{
  "tts_hints": { "pace": "slow", "tone": "empathetic" },
  "avatar_action": { "expression": "warm_smile", "gesture": "nod" }
}
```
**步骤 3**: 前端接口 (`api.py`) 捕捉到 SSE 结束后，将上述 JSON 追加发送一个特殊 SSE 类型：`yield f"data: {{'type': 'avatar_payload', 'data': ...}}\n\n"`，前端去触发相应的 3D 渲染库（如 WebGL / Live2D）。

## 5. 如何扩展基于 RAG 的专业心理知识库？
当前工程已经具备一个可运行的知识库增强版本：
1. 在 `node_perception` 中先完成 `NormalizedUserSignal` 提取。
2. 在 `node_cognition` 中调用 `KnowledgeService.retrieve(...)`，从 `knowledge_base/` 里的本地 JSON 语料召回相关片段。
3. 检索结果写入 `state["retrieved_knowledge"]`。
4. `CognitionService`、`InterventionService` 和 `OutputService` 都会读取这些片段，保证评估、策略和最终话术使用一致上下文。

如果要进一步升级为标准 RAG：
1. 保留 `KnowledgeService.retrieve` 作为统一抽象接口。
2. 使用 embeddings 将 `knowledge_base/` 中的问答、指南、案例切块后写入向量库（如 FAISS、Chroma、Milvus）。
3. 将当前规则打分替换为“召回 + 重排”，并保留 `KnowledgeSnippet` 作为统一返回结构。
4. 在 `metadata` 中增加来源、主题、风险等级、技术标签等字段，便于前端解释和审核。

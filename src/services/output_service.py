from loguru import logger
from ..domain.models import InterventionPlan, KnowledgeSnippet, PerceptionInput, CompanionResponse
from ..providers.llm_client import LiteLLMClient
from typing import AsyncGenerator

class OutputService:
    """
    输出生成服务类。
    负责根据干预计划最终生成回复。
    """
    @staticmethod
    async def generate_response_stream(
        user_input: PerceptionInput,
        plan: InterventionPlan,
        history: list,
        retrieved_knowledge: list[KnowledgeSnippet] | None = None
    ) -> AsyncGenerator[str, None]:
        """
        生成流式响应。
        
        Args:
            user_input (PerceptionInput): 当前用户的感知输入。
            plan (InterventionPlan): 由认知层生成的干预策略。
            history (list): 对话历史记录摘要。
            
        Yields:
            str: 逐个生成的文本令牌 (Tokens)。
        """
        logger.info("Generating response stream")

        knowledge_context = "\n".join(
            f"- {item.title}: {item.content}"
            for item in (retrieved_knowledge or [])
        ) or "无"
        
        system_prompt = f"""
        你是一个拥有同理心、温暖且专业的AI情感陪护（数字人）。
        请严格遵循以下督导制定的【干预计划】来回复用户。
        
        【干预计划】
        模式: {plan.mode}
        目标: {', '.join(plan.goals)}
        共情要点: {', '.join(plan.empathy_points)}
        建议技术: {', '.join(plan.suggested_techniques)}
        底线约束: {', '.join(plan.constraints)}

        【知识库参考】
        {knowledge_context}
        
        请用自然、温暖的中文对话口吻回复用户，不要暴露内部计划的结构。
        你可以视情况加入适当的情感叹词（如：哎、嗯），让对话更像真人。
        """
        
        # Build messages including history
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-5:]:  # Include last 5 turns
            messages.append(msg)
            
        messages.append({"role": "user", "content": user_input.content})
        
        async for chunk in LiteLLMClient.astream(messages=messages):
            yield chunk


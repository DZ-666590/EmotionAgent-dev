from loguru import logger
from ..domain.models import InterventionPlan, KnowledgeSnippet, NormalizedUserSignal, PsychologicalAssessment, RiskAssessment
from ..providers.llm_client import LiteLLMClient

class InterventionService:
    @staticmethod
    async def plan_intervention(
        signal: NormalizedUserSignal,
        pa: PsychologicalAssessment,
        ra: RiskAssessment,
        retrieved_knowledge: list[KnowledgeSnippet] | None = None
    ) -> InterventionPlan:
        logger.info(f"Planning intervention. Risk level: {ra.level}")

        knowledge_context = "\n".join(
            f"- 来源: {item.source}\n  标题: {item.title}\n  内容: {item.content}"
            for item in (retrieved_knowledge or [])
        ) or "无命中的知识库内容"
        
        prompt = f"""
        你是一个心理咨询督导，负责为心理陪护AI制定干预和回复策略。
        
        用户信息：
        状态总结: {signal.summary}
        风险评估等级: {ra.level}
        支持需求: {pa.support_needs}

        可参考的知识库片段:
        {knowledge_context}

        请优先吸收知识库中的干预建议、沟通边界和风险应对方式，输出时不要直接照抄原文。
        
        请输出一个JSON格式的干预计划 (InterventionPlan):
        - mode: 策略模式（必须是 "supportive", "grounding", "clarifying", "escalation" 之一）
        - goals: 列表，本次回复试图达成的目标
        - empathy_points: 列表，如何进行共情与确认(Validation)
        - suggested_techniques: 列表，建议AI使用的心理学技术（如：CBT情绪认知、正念接地、积极倾听等）
        - constraints: 列表，AI在回复中必须遵守的底线（如：不乱建议药物、不批评等）
        """
        
        messages = [
            {"role": "system", "content": "You are a clinical supervisor. Return structured JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = await LiteLLMClient.acompletion_structured(
                messages=messages,
                response_format={"type": "json_object"}
            )
            return InterventionPlan(**result)
        except Exception as e:
            logger.error(f"Intervention Planning failed: {e}")
            return InterventionPlan(
                mode="supportive",
                goals=["Provide a safe space"],
                empathy_points=["Acknowledge distress"],
                suggested_techniques=["Active listening"],
                constraints=["Do not diagnose"]
            )

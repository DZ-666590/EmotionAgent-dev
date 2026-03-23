from loguru import logger
from ..domain.models import KnowledgeSnippet, NormalizedUserSignal, PsychologicalAssessment, RiskAssessment
from ..providers.llm_client import LiteLLMClient

class CognitionService:
    @staticmethod
    async def assess_state(
        signal: NormalizedUserSignal,
        retrieved_knowledge: list[KnowledgeSnippet] | None = None
    ) -> dict:
        logger.info("Assessing psychological state")

        knowledge_context = "\n".join(
            f"- 来源: {item.source}\n  标题: {item.title}\n  内容: {item.content}"
            for item in (retrieved_knowledge or [])
        ) or "无命中的知识库内容"
        
        prompt = f"""
        你是一个基于AI的心理健康支持系统认知模块。注意：你的评估仅用于内部辅导策略生成，非医疗诊断。
        
        用户当前状态信号:
        情绪: {signal.primary_emotions} (强度: {signal.emotion_intensity})
        症状线索: {signal.symptom_signals}
        压力源: {signal.stressors}
        总结: {signal.summary}

        可参考的知识库片段:
        {knowledge_context}

        请优先参考知识库中的风险线索、支持要点和干预边界，但不要把知识库原文逐字照搬到输出中。
        
        请评估用户的状态，以JSON格式输出两部分内容（需合并在一个JSON对象中返回）：
        
        1. "psychological_assessment":
           - overall_state (字符串，总体状态描述)
           - anxiety_risk (0-1浮点数，焦虑风险)
           - depression_risk (0-1浮点数，抑郁风险)
           - bipolar_risk (0-1浮点数，双相风险)
           - key_evidence (列表，支撑评估的证据)
           - support_needs (列表，用户需要的支持类型)
           - not_diagnostic_notice (默认: "This is a supportive assessment, not a clinical diagnosis.")
           
        2. "risk_assessment":
           - level (字符串，必须是 "low", "moderate", "high", 或 "critical")
           - immediate_danger (布尔值)
           - escalation_reasons (列表，如果有危险需写明原因)
        """
        
        messages = [
            {"role": "system", "content": "You are a psychological assessment expert. Output strictly JSON."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = await LiteLLMClient.acompletion_structured(
                messages=messages,
                response_format={"type": "json_object"}
            )
            # Map into domain models
            pa = PsychologicalAssessment(**result.get("psychological_assessment", {}))
            ra = RiskAssessment(**result.get("risk_assessment", {}))
            return {"pa": pa, "ra": ra}
            
        except Exception as e:
            logger.error(f"Cognition failed: {e}")
            # Fallback
            pa = PsychologicalAssessment(
                overall_state="Unknown state due to parsing error",
                anxiety_risk=0.0, depression_risk=0.0, bipolar_risk=0.0,
                key_evidence=[], support_needs=[]
            )
            ra = RiskAssessment(level="low", immediate_danger=False, escalation_reasons=[])
            return {"pa": pa, "ra": ra}

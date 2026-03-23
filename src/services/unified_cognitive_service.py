from loguru import logger
from ..domain.models import NormalizedUserSignal, PsychologicalAssessment, RiskAssessment, InterventionPlan
from ..providers.llm_client import LiteLLMClient

class UnifiedCognitiveService:
    @staticmethod
    async def process_all_cognitive_tasks(perception_input_content: str) -> dict:
        """
        将感知(Perception)、认知(Cognition)和干预(Intervention)合并为一个大的结构化 LLM 调用。
        这通过减少往返延迟（Round-trip latency）来显著提升 Agent 部分的响应速度。
        """
        logger.info("Running unified cognitive cycle to optimize latency")
        
        prompt = f"""
        你是一个集成了【感知分析】、【心理评估】与【干预决策】于一体的高效心理系统。
        
        用户输入: "{perception_input_content}"
        
        请执行以下全套认知任务，并严格按指定的 JSON 结构返回：
        
        1. [Perception] 情绪信号提取:
           - primary_emotions: 提取的主要情绪列表（如愤怒、悲伤、焦虑）
           - emotion_intensity: 0-10的情绪强度浮点数
           - symptom_signals: 心理症状相关关键词列表
           - stressors: 压力源列表
           - summary: 简短总结
           
        2. [Cognition] 状态与风险评估:
           - overall_state: 总体状态描述
           - anxiety_risk, depression_risk, bipolar_risk: 0-1 风险分值
           - risk_level: 选择 "low", "moderate", "high", 或 "critical"
           - immediate_danger: 布尔值
           
        3. [Intervention] 干预策略制定:
           - intervention_mode: 必须是 "supportive", "grounding", "clarifying", "escalation" 之一
           - goals: 本次回复目标列表
           - empathy_points: 共情确认要点列表
           - techniques: 建议使用的心理技术列表
        """
        
        messages = [
            {"role": "system", "content": "You are a professional clinical assessor and supervisor. Output strictly valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            raw = await LiteLLMClient.acompletion_structured(
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            # 1. 映射到 NormalizedUserSignal
            signal = NormalizedUserSignal(
                primary_emotions=raw.get("primary_emotions", ["unknown"]),
                emotion_intensity=float(raw.get("emotion_intensity", 5.0)),
                symptom_signals=raw.get("symptom_signals", []),
                stressors=raw.get("stressors", []),
                risk_clues=[], # 简化，如果需要也可提取
                summary=raw.get("summary", "No summary.")
            )
            
            # 2. 映射到 PsychologicalAssessment & RiskAssessment
            pa = PsychologicalAssessment(
                overall_state=raw.get("overall_state", "Stable"),
                anxiety_risk=float(raw.get("anxiety_risk", 0.0)),
                depression_risk=float(raw.get("depression_risk", 0.0)),
                bipolar_risk=float(raw.get("bipolar_risk", 0.0)),
                key_evidence=[], 
                support_needs=[]
            )
            
            ra = RiskAssessment(
                level=raw.get("risk_level", "low"),
                immediate_danger=bool(raw.get("immediate_danger", False)),
                escalation_reasons=[]
            )
            
            # 3. 映射到 InterventionPlan
            plan = InterventionPlan(
                mode=raw.get("intervention_mode", "supportive"),
                goals=raw.get("goals", ["Empathize"]),
                empathy_points=raw.get("empathy_points", []),
                suggested_techniques=raw.get("techniques", []),
                constraints=["Do not diagnose"]
            )
            
            return {
                "signal": signal,
                "pa": pa,
                "ra": ra,
                "plan": plan
            }
            
        except Exception as e:
            logger.error(f"Unified cognitive cycle failed: {e}")
            # 返回最小可用 fallback
            return {
                "signal": NormalizedUserSignal(primary_emotions=["unknown"], emotion_intensity=5.0, symptom_signals=[], stressors=[], risk_clues=[], summary="Error"),
                "pa": PsychologicalAssessment(overall_state="Error", anxiety_risk=0, depression_risk=0, bipolar_risk=0, key_evidence=[], support_needs=[]),
                "ra": RiskAssessment(level="low", immediate_danger=False, escalation_reasons=[]),
                "plan": InterventionPlan(mode="supportive", goals=[], empathy_points=[], suggested_techniques=[], constraints=[])
            }

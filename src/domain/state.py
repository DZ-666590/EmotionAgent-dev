from typing import TypedDict, List, Optional
from .models import (
    PerceptionInput,
    NormalizedUserSignal,
    KnowledgeSnippet,
    PsychologicalAssessment,
    RiskAssessment,
    InterventionPlan,
    CompanionResponse
)

class CompanionGraphState(TypedDict, total=False):
    # IDs - 用户会话和身份标识
    session_id: str  # 会话ID，用于标识当前对话会话
    user_id: Optional[str]  # 用户ID，可选字段，用于标识用户身份
    
    # History - 对话历史记录
    conversation_history: List[dict] # { "role": "user" | "assistant", "content": str }
    
    # 1.感知 Perception
    raw_input: dict
    perception_input: PerceptionInput
    normalized_signal: NormalizedUserSignal
    
    # 2.认知 Cognition
    retrieved_knowledge: List[KnowledgeSnippet] #知识库
    psychological_assessment: PsychologicalAssessment #评估结果
    risk_assessment: RiskAssessment #风险评估结果
    
    # 3.干预 Intervention Gate & Plan
    requires_escalation: bool
    intervention_plan: InterventionPlan
    
    # 4. Output
    draft_response: str
    final_response: CompanionResponse
    
    # Execution trace
    errors: List[str]

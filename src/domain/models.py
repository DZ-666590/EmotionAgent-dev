from datetime import datetime
from typing import Any, Literal, Optional, List
from pydantic import BaseModel, Field

class PerceptionInput(BaseModel):
    """
    感知层原始输入模型。
    封装来自用户的各种模态（文本、语音转文字等）的原始数据。
    """
    session_id: str
    user_id: Optional[str] = None
    modality: Literal["text", "asr", "multimodal"] = "text"
    content: str
    audio_emotion: Optional[str] = Field(None, description="置信度最高的语音情感(如来源于ASR模型)")
    audio_emotion_confidence: Optional[float] = Field(None, description="audio_emotion的置信度")
    audio_emotion_candidates: Optional[Any] = Field(None, description="语音情感的所有候选标签及对应置信度")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

class NormalizedUserSignal(BaseModel):
    """
    归一化用户情绪信号模型。
    从用户原始输入中提取出的、结构化的情感和心理指标。
    """
    primary_emotions: List[str] = Field(description="检测到的主要情绪列表")
    emotion_intensity: float = Field(ge=0.0, le=10.0, description="情绪强度 0-10")
    symptom_signals: List[str] = Field(description="心理症状相关的关键词（如失眠、绝望等）")
    stressors: List[str] = Field(description="识别出的压力源（如工作、家庭）")
    risk_clues: List[str] = Field(description="潜在的风险线索")
    summary: str = Field(description="用户当前状态的简短总结")

class PsychologicalAssessment(BaseModel):
    """
    心理状态评估模型。
    基于归一化信号，对用户的心理健康状态进行定性和定量的初步评估。
    """
    overall_state: str = Field(description="整体心理状态估算描述")
    anxiety_risk: float = Field(ge=0.0, le=1.0, description="焦虑风险系数")
    depression_risk: float = Field(ge=0.0, le=1.0, description="抑郁风险系数")
    bipolar_risk: float = Field(ge=0.0, le=1.0, description="双相情感风险系数")
    key_evidence: List[str] = Field(description="评估支持依据")
    support_needs: List[str] = Field(description="用户当前需要的支持类型")
    not_diagnostic_notice: str = "本评估仅为支持性参考，不作为临床诊断依据。"

class RiskAssessment(BaseModel):
    """
    风险评估模型。
    专门用于安全筛查，判断用户是否存在即时危险。
    """
    level: Literal["low", "moderate", "high", "critical"] # 风险分级：低、中、高、危机
    immediate_danger: bool # 是否存在即时危险（如自伤、他伤意图）
    escalation_reasons: List[str] # 触发风险的具体理由

class InterventionPlan(BaseModel):
    """
    干预策略计划模型。
    决定了系统接下来的回复策略和采取的心理咨询技术。
    """
    mode: Literal["supportive", "grounding", "clarifying", "escalation"] # 干预模式：支持、着陆、澄清、预警
    goals: List[str] # 本轮回复的目标
    empathy_points: List[str] # 共情确认的具体切入点
    suggested_techniques: List[str] # 建议使用的心理干预技术
    constraints: List[str] # 行为准则与约束

class KnowledgeSnippet(BaseModel):
    """
    知识库检索片段。
    用于承载命中的本地知识条目，供认知、干预和生成阶段参考。
    """
    source: str = Field(description="知识来源")
    title: str = Field(description="知识条目标题")
    content: str = Field(description="提供给模型参考的知识内容")
    score: float = Field(default=0.0, description="检索匹配分数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")

class CompanionResponse(BaseModel):
    """
    最终结果反馈模型。
    包含最终生成的文本回复及相关的安全提示、结构化数据（用于TTS/数字人）。
    """
    text: str
    safety_footer: Optional[str] = None
    structured_payload: dict = Field(default_factory=dict, description="用于文本转语音或数字人展示的参数负载")

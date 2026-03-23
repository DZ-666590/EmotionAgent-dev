from loguru import logger
from ..domain.models import NormalizedUserSignal, PerceptionInput
from ..providers.llm_client import LiteLLMClient

class PerceptionService:
    """
    情感感知服务类。
    负责从原始用户文本中分析、提取情绪和心理信号。
    """
    @staticmethod
    async def extract_signal(perception_input: PerceptionInput) -> NormalizedUserSignal:
        """
        提取用户情绪信号。
        
        Args:
            perception_input (PerceptionInput): 包含用户原始内容的感知输入对象。
            
        Returns:
            NormalizedUserSignal: 结构化后的心理/情感信号。
        """
        logger.info(f"Extracting signal for session: {perception_input.session_id}")
        
        prompt = f"""
        你是一个心理学情感感知助手。
        你的任务是分析用户的输入，并提取出心理状态相关的结构化信号。
        
        用户输入: "{perception_input.content}"
        """
        
        if perception_input.audio_emotion_candidates:
            prompt += f"\n[多维度语音情绪特征补充]: 声学情绪模型对该段语音的多维度情绪候选及置信度为：{perception_input.audio_emotion_candidates}。"
            prompt += "人类的情绪是复杂的，请综合分析这些情绪成分，特别是当它们混合出现（如同时具有高SAD和一定程度的ANGRY），或与字面意思冲突时（如强颜欢笑、压抑情绪、阴阳怪气），将其作为感知用户真实心理状态的重要参考。\n"
        elif perception_input.audio_emotion:
            prompt += f"\n        [语音情绪特征补充]: 声学情绪模型识别此段语音为 {perception_input.audio_emotion}"
            if perception_input.audio_emotion_confidence:
                prompt += f" (置信度: {perception_input.audio_emotion_confidence})"
            prompt += "。请在提取信号时将此声学特征作为重要参考，特别是当语音情绪与字面意思冲突时（如强颜欢笑、压抑愤怒、阴阳怪气）。\n"
        
        prompt += """
        请提取以下信息并以JSON格式返回：
        - primary_emotions: 列表，提取的主要情绪（如愤怒、悲伤、焦虑）
        - emotion_intensity: 浮点数，0-10的情绪强度
        - symptom_signals: 列表，可能与心理症状相关的关键词（如“失眠”、“绝望”）
        - stressors: 列表，压力源
        - risk_clues: 列表，任何自伤、暴力或极度崩溃的危险线索
        - summary: 字符串，对用户当前状态的简短总结
        """
        
        messages = [
            {"role": "system", "content": "You must output strictly in JSON format matching the requested schema."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = await LiteLLMClient.acompletion_structured(
                messages=messages,
                response_format={"type": "json_object"}
            )
            return NormalizedUserSignal(**result)
        except Exception as e:
            logger.error(f"Perception failed: {e}")
            # Fallback signal on failure
            return NormalizedUserSignal(
                primary_emotions=["unknown"],
                emotion_intensity=5.0,
                symptom_signals=[],
                stressors=[],
                risk_clues=[],
                summary="Failed to parse user signal."
            )

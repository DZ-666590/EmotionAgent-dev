from loguru import logger
from ...domain.state import CompanionGraphState
from ...services.perception_service import PerceptionService
from ...services.cognition_service import CognitionService
from ...services.intervention_service import InterventionService
from ...services.knowledge_service import KnowledgeService
from ...domain.models import CompanionResponse

async def node_intake(state: CompanionGraphState) -> dict:
    """
    输入接收节点 (INTAKE)。
    
    作为图的起点，该节点主要负责：
    1. 接收并清理原始输入。
    2. 为后续的情绪感知和评估准备状态环境。
    
    Args:
        state (CompanionGraphState): 当前图的状态字典。
        
    Returns:
        dict: 更新的状态增量（此处通常返回空，仅用于流程占位）。
    """
    logger.debug("--- NODE: INTAKE ---")
    return {}

async def node_perception(state: CompanionGraphState) -> dict:
    """
    感知处理节点 (PERCEPTION)。
    
    当前节点仅负责基础信号抽取，为后续知识库检索和认知评估提供干净的结构化输入。
    
    Args:
        state (CompanionGraphState): 当前图的状态字典。
        
    Returns:
        dict: 包含归一化情绪与心理信号的状态增量。
    """
    logger.debug("--- NODE: PERCEPTION ---")
    signal = await PerceptionService.extract_signal(state["perception_input"])
    return {"normalized_signal": signal}

async def node_cognition(state: CompanionGraphState) -> dict:
    """
    认知决策节点 (COGNITION)。
    
    在该阶段执行知识库检索、心理评估与干预计划生成。
    这样可以在不破坏原有图结构的情况下，为后续 RAG 或向量检索保留稳定接入点。
    """
    logger.debug("--- NODE: COGNITION ---")
    signal = state["normalized_signal"]
    knowledge = await KnowledgeService.retrieve(signal, state["perception_input"].content)
    assessment = await CognitionService.assess_state(signal, knowledge)
    plan = await InterventionService.plan_intervention(signal, assessment["pa"], assessment["ra"], knowledge)
    return {
        "retrieved_knowledge": knowledge,
        "psychological_assessment": assessment["pa"],
        "risk_assessment": assessment["ra"],
        "intervention_plan": plan,
    }

async def node_safety_gate(state: CompanionGraphState) -> dict:
    """
    安全闸门节点 (SAFETY GATE)。
    
    负责对上一阶段生成的 `risk_assessment` 进行逻辑判断：
    1. 检查风险等级是否达到 "high" 或 "critical"。
    2. 检查是否存在 `immediate_danger`（即时危险）。
    3. 如果触发风险，设置 `requires_escalation` 标志位，用于后续的路由或警报触发。
    
    Args:
        state (CompanionGraphState): 当前图的状态。
        
    Returns:
        dict: 包含 `requires_escalation` 布尔值的状态增量。
    """
    logger.debug("--- NODE: SAFETY GATE ---")
    ra = state["risk_assessment"]
    requires_escalation = ra.level in ["high", "critical"] or ra.immediate_danger
    if requires_escalation:
        logger.warning(f"ESCALATION REQUIRED: Risk Level {ra.level}")
    return {"requires_escalation": requires_escalation}

async def node_intervention(state: CompanionGraphState) -> dict:
    """
    干预决策执行节点 (INTERVENTION)。
    
    注意：具体的回复生成已根据 `node_cognition` 生成的干预计划进行了预配置。
    此处主要负责在图结束前进行最终的策略修正或日志记录。
    具体的流式输出流水线通常在 API 层通过 OutputService 直接读取状态中的 `intervention_plan` 执行。
    """
    logger.debug("--- NODE: INTERVENTION ---")
    return {}

# Note: The output generation (streaming) will be handled by the orchestrator/API directly
# calling the OutputService using the intervention plan generated in state, 
# so we can stream directly to the client instead of blocking inside a node.

from langgraph.graph import StateGraph, END
from ..domain.state import CompanionGraphState
from .nodes.nodes import (
    node_intake,
    node_perception,
    node_cognition,
    node_safety_gate,
    node_intervention
)

def build_graph() -> StateGraph:
    """
    状态图构建器 (Graph Builder)。
    
    使用 LangGraph 构建情绪陪伴 Agent 的工作流逻辑图。
    本流程采用线性链式结构，并在感知后显式预留知识库检索与认知决策节点，便于后续扩展为 RAG。
    
    工作流顺序：
    1. intake: 接收输入
    2. perception: 提取归一化情绪与症状信号
    3. cognition: 检索知识库并完成认知评估与干预计划
    4. safety_gate: 安全性逻辑判断
    5. intervention: 干预策略收尾
    
    Returns:
        StateGraph: 编译后的 LangGraph 工作流实例。
    """
    workflow = StateGraph(CompanionGraphState)  # 创建状态图实例，使用 CompanionGraphState 作为状态类型
    
    # 添加节点 (Add nodes)
    workflow.add_node("intake", node_intake)      # 添加输入处理节点
    workflow.add_node("perception", node_perception)  # 添加感知处理节点
    workflow.add_node("cognition", node_cognition)    # 添加认知处理节点
    workflow.add_node("safety_gate", node_safety_gate)  # 添加安全检查节点
    workflow.add_node("intervention", node_intervention)  # 添加干预策略节点
    
    # 定义边与路由 (Edges & Routing)
    workflow.set_entry_point("intake") # 入口点
    workflow.add_edge("intake", "perception")
    workflow.add_edge("perception", "cognition")
    workflow.add_edge("cognition", "safety_gate")
    workflow.add_edge("safety_gate", "intervention")
    workflow.add_edge("intervention", END) # 结束点
    
    return workflow.compile()

import asyncio
import sys
from loguru import logger
from ..domain.models import PerceptionInput
from ..domain.state import CompanionGraphState
from ..graph.builder import build_graph
from ..services.output_service import OutputService

async def chat_loop():
    print("🤖 启动 AI情感陪护系统 (感知-认知-干预 闭环) ...")
    graph = build_graph()
    history = []
    
    while True:
        try:
            user_text = input("\n👤 你: ")
            if user_text.lower() in ['quit', 'exit', '退出']:
                break
                
            input_data = PerceptionInput(
                session_id="cli_session",
                content=user_text
            )
            
            initial_state = CompanionGraphState(
                session_id="cli_session",
                perception_input=input_data,
                conversation_history=history,
            )
            
            # Run LangGraph synchronous execution up to Intervention Plan
            print("⏳ 正在感知与认知评估...", end="\r", flush=True)
            result_state = await graph.ainvoke(initial_state)
            
            plan = result_state["intervention_plan"]
            knowledge = result_state.get("retrieved_knowledge") or []
            print(f"✅ 评估完成. 采取策略: [{plan.mode}]")
            if knowledge:
                print(f"📚 命中知识库: {', '.join(item.title for item in knowledge)}")
            
            print("🤖 AI: ", end="", flush=True)
            full_response = ""
            async for chunk in OutputService.generate_response_stream(
                user_input=input_data,
                plan=plan,
                history=history,
                retrieved_knowledge=knowledge,
            ):
                print(chunk, end="", flush=True)
                full_response += chunk
            print()
            
            # Update history
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": full_response})
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error during chat: {e}")
            break

if __name__ == "__main__":
    asyncio.run(chat_loop())

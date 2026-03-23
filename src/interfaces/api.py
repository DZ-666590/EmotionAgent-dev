import json
import asyncio
import httpx
import os
import edge_tts
from collections.abc import AsyncGenerator, Callable, Mapping
from importlib import import_module
from typing import Annotated, Protocol, cast

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Query,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from ..domain.models import (
    InterventionPlan,
    KnowledgeSnippet,
    NormalizedUserSignal,
    PerceptionInput,
    PsychologicalAssessment,
    RiskAssessment,
)
from ..domain.state import CompanionGraphState
from ..services.output_service import OutputService
from ..services.vision_service import VisionEmotionService
from ..services.a2f_bridge import get_a2f_bridge, GeometryFrame


class _CompanionGraphProtocol(Protocol):
    async def ainvoke(
        self, initial_state: CompanionGraphState
    ) -> CompanionGraphState: ...


app = FastAPI(title="AI Emotional Companion API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_graph() -> _CompanionGraphProtocol:
    builder_module = import_module("src.graph.builder")
    build_graph_obj = builder_module.__dict__.get("build_graph")
    if build_graph_obj is None:
        raise RuntimeError("build_graph unavailable")

    build_graph_fn = cast(Callable[[], object], build_graph_obj)
    return cast(_CompanionGraphProtocol, build_graph_fn())


graph = _build_graph()

# Get absolute path for the directory containing this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend", "dist")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    session_id: str = "web_session"
    asr_meta: dict[str, object] | None = None


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    对话接口。

    处理完整的感知-认知-干预流，并返回 Server-Sent Events (SSE) 以支持：
    1. 流式文本输出 (Token Streaming)
    2. 前端状态展示（正在感知、提取特征等）
    3. 内部认知状态的可视化负载。
    """

    async def event_generator():
        try:
            asr_meta = req.asr_meta or {}
            audio_emotion = asr_meta.get("emotion")
            audio_emotion_confidence = asr_meta.get("emotion_confidence")
            audio_emotion_candidates = asr_meta.get("emotion_candidates")

            # 1. 准备输入与历史记录 (Preparation)
            input_data = PerceptionInput(
                session_id=req.session_id,
                content=req.message,
                audio_emotion=str(audio_emotion)
                if isinstance(audio_emotion, str)
                else None,
                audio_emotion_confidence=float(audio_emotion_confidence)
                if isinstance(audio_emotion_confidence, int | float)
                else None,
                audio_emotion_candidates=cast(
                    Mapping[str, float] | None, audio_emotion_candidates
                )
                if isinstance(audio_emotion_candidates, Mapping)
                else None,
            )
            history_dicts: list[dict[str, str]] = [
                {"role": msg.role, "content": msg.content} for msg in req.history
            ]

            initial_state = CompanionGraphState(
                session_id=req.session_id,
                perception_input=input_data,
                conversation_history=history_dicts,
            )

            # 向前端发送当前任务状态
            yield f"data: {json.dumps({'type': 'status', 'content': '正在提取多模态情绪特征...'})}\n\n"
            await asyncio.sleep(0.1)

            # 2. 执行核心感知图逻辑 (Invoke LangGraph State Machine)
            result_state_obj = await graph.ainvoke(initial_state)
            result_state = cast(Mapping[str, object], result_state_obj)

            # 提取内部认知结果数据，发给前端进行仪表盘式展示
            signal = result_state.get("normalized_signal")
            pa = result_state.get("psychological_assessment")
            ra = result_state.get("risk_assessment")
            plan = result_state.get("intervention_plan")
            knowledge_obj = result_state.get("retrieved_knowledge")
            typed_signal = cast(NormalizedUserSignal | None, signal)
            typed_pa = cast(PsychologicalAssessment | None, pa)
            typed_ra = cast(RiskAssessment | None, ra)
            typed_plan = cast(InterventionPlan | None, plan)
            typed_knowledge = (
                cast(list[KnowledgeSnippet], knowledge_obj)
                if isinstance(knowledge_obj, list)
                else []
            )

            if typed_plan is None:
                raise RuntimeError("intervention plan missing from graph result")

            internal_state_payload = {
                "emotions": typed_signal.primary_emotions if typed_signal else [],
                "intensity": typed_signal.emotion_intensity if typed_signal else 0,
                "symptoms": typed_signal.symptom_signals if typed_signal else [],
                "overall_state": typed_pa.overall_state if typed_pa else "Unknown",
                "risk_level": typed_ra.level if typed_ra else "Unknown",
                "intervention_mode": typed_plan.mode,
                "techniques": typed_plan.suggested_techniques,
                "knowledge_titles": [item.title for item in typed_knowledge],
            }
            yield f"data: {json.dumps({'type': 'internal_state', 'data': internal_state_payload})}\n\n"

            status_content = f"采取策略: {typed_plan.mode}，正在生成回复..."
            yield f"data: {json.dumps({'type': 'status', 'content': status_content})}\n\n"

            # 3. 流式生成回复文本 (Final Response Generation)
            response_stream = cast(
                Callable[
                    [
                        PerceptionInput,
                        InterventionPlan,
                        list[dict[str, str]],
                        list[KnowledgeSnippet] | None,
                    ],
                    AsyncGenerator[str, None],
                ],
                cast(object, OutputService.generate_response_stream),
            )
            async for chunk in response_stream(
                input_data,
                typed_plan,
                history_dicts,
                typed_knowledge,
            ):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"API Error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/asr")
async def handle_asr(file: Annotated[UploadFile, File(...)]):
    """语音转文本 (ASR) 代理接口。"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (file.filename, file.file, file.content_type)}
            response = await client.post("http://localhost:8001/asr", files=files)
            _ = response.raise_for_status()
            return cast(dict[str, object], response.json())
    except Exception as e:
        logger.error(f"ASR Service Request Failed: {str(e)}")
        return {"text": f"[ASR Error: {str(e)}]", "error": True}


@app.post("/api/vision")
async def handle_vision(file: Annotated[UploadFile, File(...)]):
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片文件上传")

    try:
        image_bytes = await file.read()
        result = await asyncio.to_thread(
            VisionEmotionService.detect_from_image_bytes,
            image_bytes,
        )
        return {
            "status": "success",
            "visual_emotion": result.visual_emotion,
            "confidence": result.confidence,
            "message": "视觉帧已接收并记录",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(f"Vision inference failed: {exc}")
        return {
            "status": "success",
            "visual_emotion": "unknown",
            "confidence": 0.0,
            "message": "视觉帧已接收并记录",
        }


@app.get("/api/tts/stream")
async def handle_tts(
    text: Annotated[str, Query(min_length=1)],
    voice: Annotated[str, Query()] = "zh-CN-XiaoxiaoNeural",
):
    """返回流式音频响应"""
    if not text.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")

    return StreamingResponse(audio_chunk_stream(text, voice), media_type="audio/mpeg")


from fastapi.staticfiles import StaticFiles

# --- End of TTS Logic Integration ---


async def audio_chunk_stream(text: str, voice: str):
    """异步生成器，直接向前端推送音频二进制流"""
    communicate = edge_tts.Communicate(text=text, voice=voice)
    try:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and "data" in chunk:
                yield chunk["data"]
    except Exception as e:
        logger.error(f"TTS Stream Error: {e}")


# =====================================================
# Audio2Face Integration
# =====================================================


class A2FSpeakRequest(BaseModel):
    """A2F Speak 请求体"""

    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"


# 存储活跃的 WebSocket 连接
_a2f_websockets: set[WebSocket] = set()


@app.websocket("/api/a2f/ws")
async def a2f_websocket(websocket: WebSocket):
    """
    WebSocket 端点，用于向前端实时推送 geometry 帧数据。

    发送格式 (JSON):
    - {"type": "frame", "index": int, "geometry": list[float], "size": int}
    - {"type": "done"}
    - {"type": "error", "message": str}
    """
    await websocket.accept()
    _a2f_websockets.add(websocket)
    logger.info(f"[A2F WS] Client connected, total: {len(_a2f_websockets)}")

    try:
        # 保持连接，等待客户端消息或断开
        while True:
            try:
                # 接收客户端心跳或控制消息
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # 发送心跳检测
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[A2F WS] Error: {e}")
    finally:
        _a2f_websockets.discard(websocket)
        logger.info(f"[A2F WS] Client disconnected, remaining: {len(_a2f_websockets)}")


async def _broadcast_a2f_frame(frame: GeometryFrame):
    """向所有连接的 WebSocket 客户端广播 geometry 帧 (现在支持权重或顶点)"""
    if not _a2f_websockets:
        return

    message = json.dumps(
        {
            "type": "frame",
            "index": frame.frame_index,
            "geometry": frame.geometry.tolist(),
            "size": len(frame.geometry),
            "is_blendshape": getattr(frame, "is_blendshape", False),
        }
    )

    # 并行发送给所有客户端
    dead_sockets: set[WebSocket] = set()
    for ws in _a2f_websockets:
        try:
            await ws.send_text(message)
        except Exception:
            dead_sockets.add(ws)

    # 清理断开的连接
    _a2f_websockets.difference_update(dead_sockets)


async def _broadcast_a2f_done():
    """广播推理完成消息"""
    message = json.dumps({"type": "done"})
    dead_sockets: set[WebSocket] = set()
    for ws in _a2f_websockets:
        try:
            await ws.send_text(message)
        except Exception:
            dead_sockets.add(ws)
    _a2f_websockets.difference_update(dead_sockets)


@app.post("/api/a2f/speak")
async def a2f_speak(req: A2FSpeakRequest):
    """
    Audio2Face Speak 端点。

    1. 调用 Edge TTS 生成 MP3 音频
    2. 将音频发送到 A2F C++ 推理服务
    3. 通过 WebSocket 实时推送 geometry 帧数据给前端

    返回音频流供前端播放。
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")

    async def process_and_stream():
        """生成 TTS 音频，同时触发 A2F 推理"""
        # 1. 收集完整的 TTS 音频
        audio_chunks: list[bytes] = []
        communicate = edge_tts.Communicate(text=req.text, voice=req.voice)

        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio" and "data" in chunk:
                    audio_data = chunk["data"]
                    audio_chunks.append(audio_data)
                    yield audio_data
        except Exception as e:
            logger.error(f"[A2F Speak] TTS Error: {e}")
            return

        # 2. TTS 完成后，启动 A2F 推理（异步，不阻塞音频流）
        if audio_chunks:
            full_audio = b"".join(audio_chunks)
            asyncio.create_task(_run_a2f_inference(full_audio))

    return StreamingResponse(
        process_and_stream(),
        media_type="audio/mpeg",
    )


async def _run_a2f_inference(mp3_data: bytes):
    """后台运行 A2F 推理并通过 WebSocket 推送结果"""
    try:
        logger.info(f"[A2F] Starting inference, audio size: {len(mp3_data)} bytes")
        bridge = get_a2f_bridge()

        # 处理音频并通过回调推送每一帧
        frames = await bridge.process_audio(
            mp3_data,
            on_frame=_broadcast_a2f_frame,
        )

        # 推理完成
        await _broadcast_a2f_done()
        logger.info(f"[A2F] Inference complete, {len(frames)} frames")

    except Exception as e:
        logger.error(f"[A2F] Inference error: {e}")
        # 通知客户端错误
        error_msg = json.dumps({"type": "error", "message": str(e)})
        for ws in _a2f_websockets:
            try:
                await ws.send_text(error_msg)
            except Exception:
                pass


from fastapi.responses import JSONResponse


@app.exception_handler(404)
async def custom_404_handler(request, __):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"error": "Not Found"})

    from fastapi.responses import FileResponse

    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"error": "Frontend build not found"})


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

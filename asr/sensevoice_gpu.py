from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import tempfile
import shutil
import os
import re
import sys

BASE_DIR = Path(__file__).resolve().parent

# Ensure local packages like essential/ and utils/ are importable with uvicorn.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from essential.model import SenseVoiceSmall

app = FastAPI()

# 1 加载模型（启动时加载）
MODEL_DIR = os.getenv("SENSEVOICE_MODEL_DIR", str(BASE_DIR / "essential" / "SenseVoiceSmall"))
DEVICE = os.getenv("SENSEVOICE_DEVICE", "cuda:0")

model, kwargs = SenseVoiceSmall.from_pretrained(model=MODEL_DIR,device=DEVICE)
model.eval()

@app.get("/")
def root():
    return {"message": "SenseVoice API running"}

# 2 语音识别接口
@app.post("/asr")
async def speech_to_text(file: UploadFile = File(...)):
    # 临时保存音频
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        shutil.copyfileobj(file.file, tmp)
        audio_path = tmp.name

    try:
        # 推理
        res, meta = model.inference(
            data_in=audio_path,
            language="zh",
            use_itn=True,
            ban_emo_unk=False,
            **kwargs,
        )

        item = res[0] if isinstance(res, list) and len(res) > 0 else (res or {})
        if not isinstance(item, dict):
            item = {"text": str(item)}

        text = str(item.get("text", ""))

        # SenseVoice 把语言/情绪/事件编码在文本前缀标签里：<|zh|><|HAPPY|><|Speech|>
        tags = re.findall(r"<\|([^|]+)\|>", text)
        language = item.get("language") or (tags[0] if len(tags) > 0 else "unknown")
        emotion = item.get("emotion") or (tags[1] if len(tags) > 1 else "unknown")
        event = item.get("event") or (tags[2] if len(tags) > 2 else "unknown")

        clean_text = rich_transcription_postprocess(text)

        return {
            "text": clean_text,
            # "raw_text": text,
            # "language": language,
            "emotion": emotion,
            "emotion_confidence": item.get("emotion_confidence"),
            "emotion_candidates": item.get("emotion_candidates", []),
            "event": event,
            "meta": meta,
        }
    finally:
        try:
            os.unlink(audio_path)
        except OSError:
            pass
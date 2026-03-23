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

from essential.utils.model_bin import SenseVoiceSmallONNX

try:
    from funasr.tokenizer.sentencepiece_tokenizer import SentencepiecesTokenizer
except ImportError:
    SentencepiecesTokenizer = None

app = FastAPI()

# 1 加载模型（启动时加载）
MODEL_DIR = os.getenv("SENSEVOICE_MODEL_DIR", str(BASE_DIR / "essential" / "SenseVoiceSmall"))
DEVICE = os.getenv("SENSEVOICE_DEVICE", "cuda:0")
MODEL_FILENAME = os.getenv("SENSEVOICE_ONNX_FILE", "model.int8.onnx")


def resolve_device_id(device: str) -> str:
    device = str(device).strip().lower()
    if device in {"cpu", "-1"}:
        return "-1"
    if device.startswith("cuda:"):
        return device.split(":", 1)[1]
    if device == "cuda":
        return "0"
    return device


def build_tokenizer(model_dir: str):
    if SentencepiecesTokenizer is None:
        return None
    bpe_model = Path(model_dir) / "chn_jpn_yue_eng_ko_spectok.bpe.model"
    if not bpe_model.exists():
        return None
    return SentencepiecesTokenizer(bpemodel=str(bpe_model))


def parse_rich_text(text: str):
    tags = re.findall(r"<\|([^|]+)\|>", text)
    return {
        "language": tags[0] if len(tags) > 0 else "unknown",
        "emotion": tags[1] if len(tags) > 1 else "unknown",
        "event": tags[2] if len(tags) > 2 else "unknown",
    }

tokenizer = build_tokenizer(MODEL_DIR)
model = SenseVoiceSmallONNX(
    model_dir=MODEL_DIR,
    device_id=resolve_device_id(DEVICE),
    quantize=True,
    model_filename=MODEL_FILENAME,
)

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
        res = model(
            wav_content=audio_path,
            language=[0],
            textnorm=[15],
            tokenizer=tokenizer,
        )

        text = str(res[0]) if isinstance(res, list) and len(res) > 0 else str(res or "")
        parsed = parse_rich_text(text)

        clean_text = rich_transcription_postprocess(text)

        return {
            "text": clean_text,
            "emotion": parsed["emotion"],
            "emotion_confidence": None,
            "emotion_candidates": [],
            "event": parsed["event"],
            "meta": {
                "backend": "onnx",
                "device": DEVICE,
                "model_dir": MODEL_DIR,
                "model_file": MODEL_FILENAME,
                "language": parsed["language"],
            },
        }
    finally:
        try:
            os.unlink(audio_path)
        except OSError:
            pass
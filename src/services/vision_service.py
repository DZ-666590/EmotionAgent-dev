from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
from threading import Lock
from typing import Callable, ClassVar, Protocol, cast

import cv2
import numpy as np

class _EmotionDetectorProtocol(Protocol):
    def detect_emotions(self, img: np.ndarray) -> list[dict[str, object]]: ...


@dataclass(frozen=True)
class VisionEmotionResult:
    visual_emotion: str
    confidence: float
    face_detected: bool


class VisionEmotionService:
    _detector: ClassVar[_EmotionDetectorProtocol | None] = None
    _detector_lock: ClassVar[Lock] = Lock()
    _emotion_alias: ClassVar[dict[str, str]] = {
        "neutral": "calm",
        "angry": "angry",
        "happy": "happy",
        "sad": "sad",
        "fear": "fear",
        "surprise": "surprised",
        "disgust": "disgust",
    }

    @classmethod
    def _get_detector(cls) -> _EmotionDetectorProtocol:
        if cls._detector is None:
            with cls._detector_lock:
                if cls._detector is None:
                    fer_module = import_module("fer")
                    detector_factory_obj = fer_module.__dict__.get("FER")
                    if detector_factory_obj is None:
                        raise RuntimeError("FER detector unavailable")

                    detector_factory = cast(
                        Callable[..., _EmotionDetectorProtocol],
                        detector_factory_obj,
                    )
                    detector_instance = detector_factory(mtcnn=False)
                    cls._detector = detector_instance
        return cls._detector

    @classmethod
    def detect_from_image_bytes(cls, image_bytes: bytes) -> VisionEmotionResult:
        if not image_bytes:
            raise ValueError("上传图像为空")

        np_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        frame_bgr = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
        if frame_bgr is None:
            raise ValueError("无法解析上传图像，请确认为有效 JPEG/PNG")

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        detector = cls._get_detector()
        detections = detector.detect_emotions(frame_rgb)

        if not detections:
            return VisionEmotionResult(
                visual_emotion="unknown",
                confidence=0.0,
                face_detected=False,
            )

        best_label = "unknown"
        best_score = 0.0
        for detected_face in detections:
            raw_emotions = detected_face.get("emotions")
            if not isinstance(raw_emotions, dict):
                continue

            emotion_items = cast(Mapping[object, object], raw_emotions).items()
            emotions: dict[str, float] = {
                str(key): float(value)
                for key, value in emotion_items
                if isinstance(value, int | float)
            }
            if not emotions:
                continue

            label, score = max(emotions.items(), key=lambda item: item[1])
            score_value = score
            if score_value > best_score:
                best_label = str(label)
                best_score = score_value

        normalized_emotion = cls._emotion_alias.get(best_label, best_label)
        confidence = max(0.0, min(round(best_score, 4), 1.0))
        return VisionEmotionResult(
            visual_emotion=normalized_emotion,
            confidence=confidence,
            face_detected=True,
        )

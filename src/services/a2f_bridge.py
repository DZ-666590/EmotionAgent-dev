"""
Audio2Face Bridge Module - Real-time Implementation
100% Mirroring the successful logic of generate_mouth_data.py
"""

import asyncio
import struct
import subprocess
import tempfile
import os
import numpy as np
import soundfile as sf
from typing import AsyncGenerator, Callable
from dataclasses import dataclass
from collections.abc import Awaitable
from loguru import logger


@dataclass
class BlendshapeFrame:
    """单帧 Blendshape 权重数据"""

    frame_index: int
    weights: np.ndarray
    weight_count: int


# 兼容旧代码
GeometryFrame = BlendshapeFrame


class A2FBridge:
    """Audio2Face TCP 桥接客户端 - 镜像 generate_mouth_data.py 的协议实现"""

    HOST = "127.0.0.1"
    PORT = 9001
    SAMPLE_RATE = 16000
    END_MARKER = 0xFFFFFFFF

    def __init__(self):
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        """连接到 A2F C++ 服务"""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.HOST, self.PORT), timeout=5.0
            )
            logger.info(f"[A2F Bridge] Connected to {self.HOST}:{self.PORT}")
            return True
        except Exception as e:
            logger.error(f"[A2F Bridge] Connection failed: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except:
                pass
        self._reader = None
        self._writer = None
        logger.info("[A2F Bridge] Disconnected")

    @staticmethod
    def mp3_to_pcm(mp3_data: bytes, save_path: str | None = None) -> np.ndarray:
        """将 MP3 转换为 16000Hz float32 PCM"""
        # 如果提供了 save_path 且后缀是 .wav，我们尝试在同目录下保留 .mp3
        mp3_path = None
        if save_path and save_path.endswith(".wav"):
            mp3_path = save_path.replace(".wav", ".mp3")
            with open(mp3_path, "wb") as f:
                f.write(mp3_data)
        else:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_file:
                mp3_file.write(mp3_data)
                mp3_path = mp3_file.name

        wav_path = save_path if save_path else mp3_path.replace(".mp3", ".wav")
        try:
            # 严格按照脚本要求转码
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                mp3_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                wav_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            audio_data, _ = sf.read(wav_path, dtype="float32")

            # --- 核心优化：静音填充 (Mirroring manual logic) ---
            padding_head = np.zeros(int(16000 * 0.15), dtype=np.float32)
            padding_tail = np.zeros(int(16000 * 0.3), dtype=np.float32)
            audio_data = np.concatenate([padding_head, audio_data, padding_tail])

            # 音量归一化 (确保口型有足够的幅度)
            max_val = np.max(np.abs(audio_data))
            if max_val > 0.01:
                audio_data = audio_data / max_val * 0.9

            return np.asarray(audio_data, dtype=np.float32)
        finally:
            # 只有当它是临时文件时才删除 mp3
            if mp3_path and not save_path and os.path.exists(mp3_path):
                os.unlink(mp3_path)
            # 仅当没有指定保存路径时才删除 wav
            if not save_path and os.path.exists(wav_path):
                os.unlink(wav_path)

    async def process_audio(
        self,
        mp3_data: bytes,
        on_frame: Callable[[BlendshapeFrame], Awaitable[None]] | None = None,
        save_path: str | None = None,
    ) -> list[BlendshapeFrame]:
        """主入口：像运行脚本一样处理实时音频"""
        async with self._lock:
            pcm_data = self.mp3_to_pcm(mp3_data, save_path=save_path)

            if not await self.connect():
                raise RuntimeError("A2F SDK not running on 9001")

            try:
                await self._send_audio_payload(pcm_data)
                await asyncio.sleep(0.5)  # 给推理一点启动时间

                frames = []
                async for frame in self._receive_frames():
                    frames.append(frame)
                    if on_frame:
                        await on_frame(frame)

                logger.info(f"[A2F Bridge] Success: {len(frames)} frames generated.")
                return frames
            finally:
                await self.disconnect()

    async def _send_audio_payload(self, pcm_data: np.ndarray):
        """100% 模仿脚本的发送逻辑: [uint32: samples_count][float32 * samples_count]"""
        if self._writer is None:
            return

        # 1. 总采样数
        count_bytes = struct.pack("<I", len(pcm_data))
        # 2. 音频字节
        audio_bytes = pcm_data.tobytes()
        # 3. 结束信号 (0)
        end_bytes = struct.pack("<I", 0)

        # 一次性发送 (Mimic sendall)
        self._writer.write(count_bytes + audio_bytes + end_bytes)
        await self._writer.drain()
        logger.info(f"[A2F Bridge] Sent {len(pcm_data)} samples to A2F SDK.")

    async def _receive_frames(self) -> AsyncGenerator[BlendshapeFrame, None]:
        """100% 模仿脚本的接收逻辑"""
        if self._reader is None:
            return

        while True:
            try:
                # 1. 读 Frame Index
                idx_data = await self._reader.readexactly(4)
                frame_index = struct.unpack("<I", idx_data)[0]
                if frame_index == self.END_MARKER:
                    logger.debug("[A2F Bridge] End Marker Received")
                    break

                # 2. 读 Weight Count
                count_data = await self._reader.readexactly(4)
                weight_count = struct.unpack("<I", count_data)[0]

                # 3. 读 Weights
                weights_data = await self._reader.readexactly(weight_count * 4)
                weights = np.frombuffer(weights_data, dtype=np.float32).copy()

                yield BlendshapeFrame(
                    frame_index=frame_index, weights=weights, weight_count=weight_count
                )
            except asyncio.IncompleteReadError:
                break
            except Exception as e:
                logger.error(f"[A2F Bridge] Recv error: {e}")
                break


# 全局单例
_bridge_instance = None


def get_a2f_bridge() -> A2FBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = A2FBridge()
    return _bridge_instance

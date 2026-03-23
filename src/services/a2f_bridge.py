"""
Audio2Face Bridge Module

连接 C++ A2F 推理服务 (TCP 9001)，处理：
1. MP3 音频流 → 16000Hz float32 PCM 转换
2. 发送 PCM 数据到 C++ 服务
3. 接收 geometry 帧数据
4. 通过 WebSocket 推送给前端
"""

import asyncio
import struct
import io
import subprocess
import tempfile
import os
from typing import AsyncGenerator, Callable, cast
from dataclasses import dataclass
from collections.abc import Awaitable

import numpy as np
import soundfile as sf
from scipy import signal
from loguru import logger


@dataclass
class GeometryFrame:
    """单帧数据，支持顶点或 Blendshape 权重"""

    frame_index: int
    geometry: np.ndarray  # float32 数组 (顶点或权重)
    is_blendshape: bool = False  # 标识是否为权重数据


class A2FBridge:
    """Audio2Face TCP 桥接客户端"""

    HOST = "127.0.0.1"
    PORT = 9001
    SAMPLE_RATE = 16000
    END_MARKER = 0xFFFFFFFF

    # ARKit 52 表情基路径
    BS_DATA_PATH = "D:/Audio2Face-3D-SDK-main/Audio2Face-3D-SDK-main/_data/audio2face-models/audio2face-3d-v3.0/bs_skin_Mark.npz"

    # 灵敏度控制
    OUTPUT_STRENGTH = 1.5  # 放大系数
    STRENGTH_OFFSET = 0.05  # 最小阈值，过滤噪声

    def __init__(self):
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._bs_data: dict | None = None
        self.bs_names: list[str] = []
        self._bs_matrix: np.ndarray | None = None

    def _load_bs_data(self):
        """加载 Blendshape 拓扑数据以便进行权重提取 (解方程)"""
        if self._bs_data is not None:
            return
        try:
            data = np.load(self.BS_DATA_PATH)
            # 提取 52 个标准表情 (去掉 neutral, poseNames, frontalMask, rig_version)
            excluded = {"neutral", "poseNames", "frontalMask", "rig_version"}
            self.bs_names = [k for k in data.keys() if k not in excluded]

            # 构造基矩阵: Shape (24002 * 3, 52)
            bs_basis = []
            neutral = data["neutral"].flatten()
            for name in self.bs_names:
                diff = data[name].flatten() - neutral
                bs_basis.append(diff)

            self._bs_matrix = np.stack(bs_basis, axis=1)  # (72006, 52)
            self._bs_data = data
            logger.info(f"[A2F Bridge] Loaded {len(self.bs_names)} ARKit blendshapes")
        except Exception as e:
            logger.error(f"[A2F Bridge] Failed to load BS data: {e}")

    def solve_blendshapes(self, current_v: np.ndarray) -> np.ndarray:
        """
        将 24,002 个顶点坐标解算为 52 个表情权重
        使用最小二乘法: Basis * weights = (Current - Neutral)
        """
        self._load_bs_data()
        if self._bs_data is None or self._bs_matrix is None:
            return np.zeros(52, dtype=np.float32)

        # 仅取前 24002 个点 (皮肤网格)
        # 每个点 3 个坐标
        skin_v_count = 24002 * 3
        if len(current_v) < skin_v_count:
            return np.zeros(len(self.bs_names), dtype=np.float32)

        skin_v = current_v[:skin_v_count].flatten()
        target = skin_v - self._bs_data["neutral"].flatten()

        # 解方程 (拟合权重)
        weights_tuple = np.linalg.lstsq(self._bs_matrix, target, rcond=None)
        weights_sol = cast(np.ndarray, weights_tuple[0])

        # 应用放大和阈值
        weights_sol = (weights_sol - self.STRENGTH_OFFSET) * self.OUTPUT_STRENGTH

        # 限制范围 [0, 1]
        weights = np.clip(weights_sol, 0, 1)
        final_weights = cast(np.ndarray, weights)
        return final_weights.astype(np.float32)

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
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None
        logger.info("[A2F Bridge] Disconnected")

    @staticmethod
    def mp3_to_pcm(mp3_data: bytes) -> np.ndarray:
        """
        将 MP3 音频转换为 16000Hz 单声道 float32 PCM

        Args:
            mp3_data: MP3 二进制数据

        Returns:
            float32 numpy 数组，范围 [-1.0, 1.0]
        """
        # 使用 ffmpeg 将 MP3 转换为 WAV，再用 soundfile 读取
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_file:
            mp3_file.write(mp3_data)
            mp3_path = mp3_file.name

        wav_path = mp3_path.replace(".mp3", ".wav")

        try:
            # 使用 ffmpeg 转换为 16kHz 单声道 WAV
            subprocess.run(
                [
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
                ],
                check=True,
                capture_output=True,
            )

            # 使用 soundfile 读取 WAV
            audio_data, sample_rate = sf.read(wav_path, dtype="float32")

            # 确保是单声道
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            # 如果采样率不是 16000，重采样（理论上 ffmpeg 已处理）
            if sample_rate != 16000:
                num_samples = int(len(audio_data) * 16000 / sample_rate)
                audio_data = cast(np.ndarray, signal.resample(audio_data, num_samples))

            return audio_data.astype(np.float32)

        finally:
            # 清理临时文件
            if os.path.exists(mp3_path):
                os.unlink(mp3_path)
            if os.path.exists(wav_path):
                os.unlink(wav_path)

    async def _send_chunk(self, pcm_chunk: np.ndarray):
        """发送单个 PCM 块到 C++ 服务"""
        if self._writer is None:
            raise RuntimeError("Not connected to A2F service")

        chunk_size = len(pcm_chunk)
        # 协议: [uint32 chunk_size][float32 * chunk_size]
        header = struct.pack("<I", chunk_size)
        data = pcm_chunk.astype(np.float32).tobytes()

        self._writer.write(header + data)
        await self._writer.drain()

    async def _send_end_signal(self):
        """发送音频结束信号 (chunk_size = 0)"""
        if self._writer is None:
            raise RuntimeError("Not connected to A2F service")

        self._writer.write(struct.pack("<I", 0))
        await self._writer.drain()

    async def _receive_frames(self) -> AsyncGenerator[GeometryFrame, None]:
        """接收 geometry 帧数据"""
        if self._reader is None:
            raise RuntimeError("Not connected to A2F service")

        frame_count = 0
        while True:
            # 读取 frame_index (uint32)
            frame_idx_data = await self._reader.readexactly(4)
            frame_index = struct.unpack("<I", frame_idx_data)[0]

            # 检查结束标志
            if frame_index == self.END_MARKER:
                logger.debug("[A2F Bridge] Received end marker")
                break

            # 读取 geo_size (uint32)
            geo_size_data = await self._reader.readexactly(4)
            geo_size = struct.unpack("<I", geo_size_data)[0]

            # 读取 geometry 数据 (float32 * geo_size)
            if geo_size > 0:
                geo_data = await self._reader.readexactly(geo_size * 4)
                geometry = np.frombuffer(geo_data, dtype=np.float32)
            else:
                geometry = np.array([], dtype=np.float32)

            frame_count += 1
            logger.debug(
                f"[A2F Bridge] Frame {frame_index}: geo_size={geo_size}, "
                f"geometry_bytes={len(geometry) * 4 if len(geometry) > 0 else 0}, "
                f"geometry_elements={len(geometry)}"
            )

            yield GeometryFrame(frame_index=frame_index, geometry=geometry)

    async def process_audio(
        self,
        mp3_data: bytes,
        on_frame: Callable[[GeometryFrame], Awaitable[None]] | None = None,
        chunk_size: int = 4000,  # 约 250ms @ 16000Hz
        use_blendshapes: bool = True,  # 默认为 True，提取权重
    ) -> list[GeometryFrame]:
        """
        处理音频并获取 geometry 帧

        Args:
            mp3_data: MP3 音频数据
            on_frame: 每帧回调（用于实时推送）
            chunk_size: PCM 块大小
            use_blendshapes: 是否将顶点转换为 ARKit 权重

        Returns:
            所有 geometry 帧列表
        """
        async with self._lock:
            # 1. 转换 MP3 → PCM
            logger.info("[A2F Bridge] Converting MP3 to PCM...")
            pcm_data = self.mp3_to_pcm(mp3_data)
            logger.info(
                f"[A2F Bridge] PCM samples: {len(pcm_data)}, duration: {len(pcm_data) / self.SAMPLE_RATE:.2f}s"
            )

            # 2. 连接服务
            if not await self.connect():
                raise RuntimeError("Failed to connect to A2F service")

            try:
                # 3. 分块发送 PCM 数据
                for i in range(0, len(pcm_data), chunk_size):
                    chunk = pcm_data[i : i + chunk_size]
                    await self._send_chunk(chunk)

                # 4. 发送结束信号，触发推理
                await self._send_end_signal()
                logger.info("[A2F Bridge] Audio sent, waiting for inference...")

                # 5. 接收 geometry 帧
                frames: list[GeometryFrame] = []
                async for frame in self._receive_frames():
                    if use_blendshapes:
                        # 核心转换：顶点 -> 52 个权重
                        weights = await asyncio.to_thread(
                            self.solve_blendshapes, frame.geometry
                        )
                        frame.geometry = weights
                        frame.is_blendshape = True

                    frames.append(frame)
                    if on_frame:
                        await on_frame(frame)

                logger.info(
                    f"[A2F Bridge] Received {len(frames)} geometry frames (Blendshapes={use_blendshapes})"
                )
                return frames

            finally:
                await self.disconnect()

    async def process_audio_stream(
        self,
        mp3_data: bytes,
        chunk_size: int = 4000,
    ) -> AsyncGenerator[GeometryFrame, None]:
        """
        流式处理音频，逐帧 yield geometry 数据

        Args:
            mp3_data: MP3 音频数据
            chunk_size: PCM 块大小

        Yields:
            GeometryFrame 对象
        """
        async with self._lock:
            # 1. 转换 MP3 → PCM
            pcm_data = self.mp3_to_pcm(mp3_data)

            # 2. 连接服务
            if not await self.connect():
                raise RuntimeError("Failed to connect to A2F service")

            try:
                # 3. 分块发送 PCM 数据
                for i in range(0, len(pcm_data), chunk_size):
                    chunk = pcm_data[i : i + chunk_size]
                    await self._send_chunk(chunk)

                # 4. 发送结束信号
                await self._send_end_signal()

                # 5. 流式接收并 yield
                async for frame in self._receive_frames():
                    yield frame

            finally:
                await self.disconnect()

    async def process_pcm(
        self,
        pcm_data: np.ndarray,
        on_frame: Callable[[GeometryFrame], Awaitable[None]] | None = None,
        chunk_size: int = 4000,
    ) -> list[GeometryFrame]:
        """
        直接处理 PCM float32 数据

        Args:
            pcm_data: float32 numpy 数组，范围 [-1.0, 1.0]，16000Hz 采样率
            on_frame: 每帧回调（用于实时推送）
            chunk_size: PCM 块大小

        Returns:
            所有 geometry 帧列表
        """
        async with self._lock:
            logger.info(
                f"[A2F Bridge] PCM samples: {len(pcm_data)}, duration: {len(pcm_data) / self.SAMPLE_RATE:.2f}s"
            )

            # 连接服务
            if not await self.connect():
                raise RuntimeError("Failed to connect to A2F service")

            try:
                # 分块发送 PCM 数据
                for i in range(0, len(pcm_data), chunk_size):
                    chunk = pcm_data[i : i + chunk_size]
                    await self._send_chunk(chunk)

                # 发送结束信号，触发推理
                await self._send_end_signal()
                logger.info("[A2F Bridge] Audio sent, waiting for inference...")

                # 接收 geometry 帧
                frames: list[GeometryFrame] = []
                total_geometry_bytes = 0
                async for frame in self._receive_frames():
                    frames.append(frame)
                    total_geometry_bytes += len(frame.geometry) * 4  # float32 = 4 bytes
                    if on_frame:
                        await on_frame(frame)

                logger.info(
                    f"[A2F Bridge] Received {len(frames)} geometry frames, "
                    f"total_data_bytes={total_geometry_bytes}"
                )
                return frames

            finally:
                await self.disconnect()


# 全局单例
_bridge_instance: A2FBridge | None = None


def get_a2f_bridge() -> A2FBridge:
    """获取 A2F Bridge 单例"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = A2FBridge()
    return _bridge_instance

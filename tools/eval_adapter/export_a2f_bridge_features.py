#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import types
from pathlib import Path
from typing import List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import loguru  # type: ignore  # noqa: F401
except ModuleNotFoundError:

    class _FallbackLogger:
        def info(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

        def debug(self, *args, **kwargs):
            pass

    sys.modules["loguru"] = types.SimpleNamespace(logger=_FallbackLogger())

from src.services.a2f_bridge import A2FBridge  # noqa: E402

AUDIO_EXTS = {".wav", ".mp3"}


import csv


def _collect_audio_files(input_path: Path) -> List[Path]:
    if input_path.suffix.lower() == ".csv":
        # Load audio files from official index CSV (matching eval_emotion_metrics logic)
        audio_files = []
        with open(input_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)[1:]  # Skip header
            # Remove the restrictive mini-test limit to allow full sample processing
            # if len(rows) > 10:
            #     rows = rows[:10]

        speaker_paths = [row[1] for row in rows]
        listener_paths = [row[2] for row in rows]

        # Audio source is the local 'val/Audio_files'
        # We need BOTH speaker and listener for N = rows*2
        # matching load_person_specific_order in eval_emotion_metrics.py
        all_speaker_rel = speaker_paths + listener_paths

        # Use the relative path from the CSV location if it's within the dataset structure
        # Assume CSV is in <dataset_root>/, Audio_files are in <dataset_root>/val/Audio_files
        data_root = input_path.parent / "val" / "Audio_files"
        # If not found, try the parent directory (some splits might be different)
        if not (data_root).exists():
            data_root = input_path.parent.parent / "val" / "Audio_files"

        for p in all_speaker_rel:
            full_path = data_root / f"{p}.wav"
            if not full_path.exists():
                raise FileNotFoundError(f"Audio file from CSV not found: {full_path}")
            audio_files.append(full_path)
        return audio_files

    if input_path.is_file():
        return [input_path]
    files = [
        p
        for p in input_path.rglob("*")
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS
    ]
    if not files:
        raise ValueError(f"No audio files found under {input_path}")
    return sorted(files)


def _pad_or_trim(features: np.ndarray, target_length: int) -> np.ndarray:
    if features.shape[0] == target_length:
        return features
    if features.shape[0] > target_length:
        return features[:target_length]
    if features.shape[0] == 0:
        raise ValueError("A2F returned zero frames; cannot pad empty sequence")
    pad = np.repeat(features[-1:, :], target_length - features.shape[0], axis=0)
    return np.concatenate([features, pad], axis=0)


async def _extract_one(bridge: A2FBridge, audio_path: Path) -> np.ndarray:
    audio_bytes = audio_path.read_bytes()
    # 1. 提取 A2F 物理 Blendshape 权重 (52D)
    frames = await bridge.process_audio(audio_bytes)
    if not frames:
        raise RuntimeError(f"No A2F frames returned for {audio_path}")

    a2f_weights = np.stack(
        [frame.weights.astype(np.float32) for frame in frames], axis=0
    )

    # 2. 提取/生成 A2E 语义情感概率 (10D)
    # [模拟 A2E]: [neutral, angry, ?, disgust, fear, ?, happy, ?, ?, sad]
    n_frames = len(frames)
    a2e_probs = np.zeros((n_frames, 10), dtype=np.float32)

    # 这里的启发式逻辑是为了先跑通 62D 混合特征流程。
    # 在真实 SDK 连通后，这里会被替换为 bridge.get_a2e_data()。
    # 我们基于 A2F 的物理动作反向推导一点情感，增加初始相关性。
    # 比如 mouthSmile (idx 28/29) 强时，Happy (idx 6) 概率增加。
    smile_strength = (a2f_weights[:, 28] + a2f_weights[:, 29]) / 2.0
    a2e_probs[:, 6] = np.clip(smile_strength * 2.0, 0, 1)  # Happy
    a2e_probs[:, 0] = 1.0 - a2e_probs[:, 6]  # Neutral

    # 合并为 62D 特征: [A2F:52, A2E:10]
    hybrid_features = np.concatenate([a2f_weights, a2e_probs], axis=-1)

    return hybrid_features


async def _run(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_files = _collect_audio_files(input_path)
    bridge = A2FBridge()

    feature_list = []
    sample_ids = []
    frame_counts = []

    for audio_file in audio_files:
        feature = await _extract_one(bridge, audio_file)
        feature_list.append(feature)
        frame_counts.append(int(feature.shape[0]))
        if input_path.is_dir():
            sample_ids.append(
                audio_file.relative_to(input_path).with_suffix("").as_posix()
            )
        else:
            sample_ids.append(audio_file.stem)

    target_length = args.target_length or min(frame_counts)
    aligned = [_pad_or_trim(feature, target_length) for feature in feature_list]
    stacked = np.stack(aligned, axis=0).astype(np.float32)

    # 统一保存为 hybrid_features.npy
    np.save(out_dir / "hybrid_features.npy", stacked)
    with open(out_dir / "hybrid_feature_summary.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "input": str(input_path),
                "num_samples": len(sample_ids),
                "feature_shape": list(stacked.shape),
                "original_frame_counts": frame_counts,
                "target_length": int(target_length),
                "sample_ids": sample_ids,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(
        json.dumps(
            {"feature_shape": list(stacked.shape), "num_samples": len(sample_ids)},
            indent=2,
            ensure_ascii=False,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export A2F blendshape features using the existing TCP bridge."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=str,
        help="Audio file or directory containing wav/mp3 files.",
    )
    parser.add_argument("--out-dir", required=True, type=str)
    parser.add_argument(
        "--target-length",
        type=int,
        help="Optional unified frame length. Defaults to min length across samples.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()

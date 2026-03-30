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

    sys.modules['loguru'] = types.SimpleNamespace(logger=_FallbackLogger())

from src.services.a2f_bridge import A2FBridge  # noqa: E402

AUDIO_EXTS = {'.wav', '.mp3'}


def _collect_audio_files(input_path: Path) -> List[Path]:
    if input_path.is_file():
        return [input_path]
    files = [p for p in input_path.rglob('*') if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    if not files:
        raise ValueError(f'No audio files found under {input_path}')
    return sorted(files)


def _pad_or_trim(features: np.ndarray, target_length: int) -> np.ndarray:
    if features.shape[0] == target_length:
        return features
    if features.shape[0] > target_length:
        return features[:target_length]
    if features.shape[0] == 0:
        raise ValueError('A2F returned zero frames; cannot pad empty sequence')
    pad = np.repeat(features[-1:, :], target_length - features.shape[0], axis=0)
    return np.concatenate([features, pad], axis=0)


async def _extract_one(bridge: A2FBridge, audio_path: Path) -> np.ndarray:
    audio_bytes = audio_path.read_bytes()
    frames = await bridge.process_audio(audio_bytes)
    if not frames:
        raise RuntimeError(f'No A2F frames returned for {audio_path}')
    weights = [frame.weights.astype(np.float32) for frame in frames]
    return np.stack(weights, axis=0)


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
            sample_ids.append(audio_file.relative_to(input_path).with_suffix('').as_posix())
        else:
            sample_ids.append(audio_file.stem)

    target_length = args.target_length or min(frame_counts)
    aligned = [_pad_or_trim(feature, target_length) for feature in feature_list]
    stacked = np.stack(aligned, axis=0).astype(np.float32)

    np.save(out_dir / 'a2f_features.npy', stacked)
    with open(out_dir / 'a2f_feature_summary.json', 'w', encoding='utf-8') as f:
        json.dump(
            {
                'input': str(input_path),
                'num_samples': len(sample_ids),
                'feature_shape': list(stacked.shape),
                'original_frame_counts': frame_counts,
                'target_length': int(target_length),
                'sample_ids': sample_ids,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(json.dumps({'feature_shape': list(stacked.shape), 'num_samples': len(sample_ids)}, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description='Export A2F blendshape features using the existing TCP bridge.')
    parser.add_argument('--input', required=True, type=str, help='Audio file or directory containing wav/mp3 files.')
    parser.add_argument('--out-dir', required=True, type=str)
    parser.add_argument('--target-length', type=int, help='Optional unified frame length. Defaults to min length across samples.')
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == '__main__':
    main()

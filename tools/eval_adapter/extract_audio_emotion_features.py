#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import List, Tuple

import numpy as np

AUDIO_EXTS = {'.wav', '.mp3'}
TARGET_SR = 16000


def _collect_audio_files(input_path: Path) -> List[Path]:
    if input_path.is_file():
        return [input_path]
    files = [p for p in input_path.rglob('*') if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    if not files:
        raise ValueError(f'No audio files found under {input_path}')
    return sorted(files)


def _load_wav_float32(path: Path) -> np.ndarray:
    with wave.open(str(path), 'rb') as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)

    if sampwidth != 2:
        raise ValueError(f'Only 16-bit wav is supported directly: {path}')
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if nchannels > 1:
        audio = audio.reshape(-1, nchannels).mean(axis=1)
    if framerate != TARGET_SR:
        raise ValueError(f'Expected {TARGET_SR} Hz wav, got {framerate} for {path}')
    return audio


def _load_audio(path: Path) -> np.ndarray:
    if path.suffix.lower() == '.wav':
        return _load_wav_float32(path)

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        cmd = ['ffmpeg', '-y', '-i', str(path), '-ar', str(TARGET_SR), '-ac', '1', '-f', 'wav', str(tmp_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return _load_wav_float32(tmp_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _frame_audio(audio: np.ndarray, frame_size: int, hop_size: int) -> np.ndarray:
    if audio.size < frame_size:
        audio = np.pad(audio, (0, frame_size - audio.size))
    frames = []
    for start in range(0, max(1, audio.size - frame_size + 1), hop_size):
        frame = audio[start:start + frame_size]
        if frame.size < frame_size:
            frame = np.pad(frame, (0, frame_size - frame.size))
        frames.append(frame)
    if not frames:
        frames.append(np.zeros(frame_size, dtype=np.float32))
    return np.stack(frames, axis=0)


def _spectral_features(frame: np.ndarray) -> Tuple[float, float, float]:
    window = np.hanning(frame.shape[0]).astype(np.float32)
    spec = np.abs(np.fft.rfft(frame * window)).astype(np.float32)
    freqs = np.fft.rfftfreq(frame.shape[0], d=1.0 / TARGET_SR).astype(np.float32)
    mag_sum = float(np.sum(spec) + 1e-8)
    centroid = float(np.sum(freqs * spec) / mag_sum)
    bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * spec) / mag_sum))
    cumulative = np.cumsum(spec)
    rolloff_idx = int(np.searchsorted(cumulative, 0.85 * cumulative[-1]))
    rolloff = float(freqs[min(rolloff_idx, len(freqs) - 1)])
    return centroid, bandwidth, rolloff


def _extract_frame_features(frames: np.ndarray) -> np.ndarray:
    feats = []
    prev_rms = 0.0
    for frame in frames:
        rms = float(np.sqrt(np.mean(frame ** 2) + 1e-8))
        abs_mean = float(np.mean(np.abs(frame)))
        std = float(np.std(frame))
        zcr = float(np.mean(np.abs(np.diff(np.signbit(frame).astype(np.int8)))))
        peak = float(np.max(np.abs(frame)))
        centroid, bandwidth, rolloff = _spectral_features(frame)
        delta_rms = rms - prev_rms
        prev_rms = rms
        feats.append([
            rms,
            abs_mean,
            std,
            zcr,
            peak,
            delta_rms,
            centroid / 8000.0,
            bandwidth / 8000.0,
            rolloff / 8000.0,
            float(np.mean(frame > 0.0)),
        ])
    return np.asarray(feats, dtype=np.float32)


def _pad_or_trim(features: np.ndarray, target_length: int) -> np.ndarray:
    if features.shape[0] == target_length:
        return features
    if features.shape[0] > target_length:
        return features[:target_length]
    pad = np.repeat(features[-1:, :], target_length - features.shape[0], axis=0)
    return np.concatenate([features, pad], axis=0)


def main() -> None:
    parser = argparse.ArgumentParser(description='Extract simple framewise audio emotion baseline features.')
    parser.add_argument('--input', required=True, type=str, help='Audio file or directory containing wav/mp3 files.')
    parser.add_argument('--out-dir', required=True, type=str)
    parser.add_argument('--frame-ms', type=float, default=33.333)
    parser.add_argument('--hop-ms', type=float, default=33.333)
    parser.add_argument('--target-length', type=int)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frame_size = max(1, int(round(TARGET_SR * args.frame_ms / 1000.0)))
    hop_size = max(1, int(round(TARGET_SR * args.hop_ms / 1000.0)))

    audio_files = _collect_audio_files(input_path)
    feature_list = []
    sample_ids = []
    frame_counts = []

    for audio_file in audio_files:
        audio = _load_audio(audio_file)
        frames = _frame_audio(audio, frame_size, hop_size)
        features = _extract_frame_features(frames)
        feature_list.append(features)
        frame_counts.append(int(features.shape[0]))
        if input_path.is_dir():
            sample_ids.append(audio_file.relative_to(input_path).with_suffix('').as_posix())
        else:
            sample_ids.append(audio_file.stem)

    target_length = args.target_length or min(frame_counts)
    aligned = [_pad_or_trim(feature, target_length) for feature in feature_list]
    stacked = np.stack(aligned, axis=0).astype(np.float32)

    np.save(out_dir / 'audio_emotion_features.npy', stacked)
    with open(out_dir / 'audio_emotion_feature_summary.json', 'w', encoding='utf-8') as f:
        json.dump(
            {
                'input': str(input_path),
                'num_samples': len(sample_ids),
                'feature_shape': list(stacked.shape),
                'frame_ms': args.frame_ms,
                'hop_ms': args.hop_ms,
                'original_frame_counts': frame_counts,
                'target_length': int(target_length),
                'sample_ids': sample_ids,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(json.dumps({'feature_shape': list(stacked.shape), 'num_samples': len(sample_ids)}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()

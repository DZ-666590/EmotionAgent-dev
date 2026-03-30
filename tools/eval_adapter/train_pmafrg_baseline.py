#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import pmafrg_adapter


def _load_feature(path: Path) -> np.ndarray:
    if path.suffix == '.npy':
        return np.load(path, allow_pickle=False)
    if path.suffix == '.npz':
        data = np.load(path, allow_pickle=False)
        try:
            if len(data.files) != 1:
                raise ValueError(f'{path} contains multiple arrays; please convert to single-array npz/npy first')
            return data[data.files[0]]
        finally:
            data.close()
    raise ValueError(f'Unsupported feature file: {path}')


def main() -> None:
    parser = argparse.ArgumentParser(description='One-shot training for PMAFRG baseline adapters.')
    parser.add_argument('--emotion-features', type=str)
    parser.add_argument('--emotion-targets', type=str)
    parser.add_argument('--face-features', type=str)
    parser.add_argument('--face-targets', type=str)
    parser.add_argument('--ridge-lambda', type=float, default=1e-3)
    parser.add_argument('--out-dir', type=str, required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fit_summary = {
        'ridge_lambda': args.ridge_lambda,
        'models': {},
    }

    if args.emotion_features and args.emotion_targets:
        emotion_features = pmafrg_adapter._ensure_4d_features(_load_feature(Path(args.emotion_features)))
        emotion_targets = pmafrg_adapter._ensure_3d_targets(_load_feature(Path(args.emotion_targets)), 25)
        emotion_model = pmafrg_adapter._fit_ridge(emotion_features, emotion_targets, args.ridge_lambda)
        pmafrg_adapter._save_model(
            out_dir / 'emotion_adapter.npz',
            emotion_model,
            {'kind': 'emotion', 'target_dim': 25, 'source_shape': list(emotion_features.shape)},
        )
        fit_summary['models']['emotion'] = {
            'input_dim': emotion_model['input_dim'],
            'output_dim': emotion_model['output_dim'],
            'train_mse': emotion_model['train_mse'],
        }

    if args.face_features and args.face_targets:
        face_features = pmafrg_adapter._ensure_4d_features(_load_feature(Path(args.face_features)))
        face_targets = pmafrg_adapter._ensure_3d_targets(_load_feature(Path(args.face_targets)), 58)
        face_model = pmafrg_adapter._fit_ridge(face_features, face_targets, args.ridge_lambda)
        pmafrg_adapter._save_model(
            out_dir / 'face_adapter.npz',
            face_model,
            {'kind': 'face', 'target_dim': 58, 'source_shape': list(face_features.shape)},
        )
        fit_summary['models']['face'] = {
            'input_dim': face_model['input_dim'],
            'output_dim': face_model['output_dim'],
            'train_mse': face_model['train_mse'],
        }

    if not fit_summary['models']:
        raise ValueError('No valid train pair provided.')

    with open(out_dir / 'fit_summary.json', 'w', encoding='utf-8') as f:
        json.dump(fit_summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(fit_summary, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()

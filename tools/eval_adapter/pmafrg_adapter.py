#!/usr/bin/env python3
"""Train and run simple adapters from Audio2Emotion / Audio2Face features.

This script implements a practical baseline for the PMAFRG-style evaluation
format described by the user:

- Emotion target: prediction_emotion[N, K, T, 25]
- 3D face target: prediction_3dfv[N, K, T, 58]

The adapters are intentionally simple ridge-regression baselines so they can be
trained with only numpy and run in constrained environments. They are meant to
be replaced by stronger models later, while preserving the same data contract.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np


Array = np.ndarray


def _load_array(path: Path, key: Optional[str]) -> Array:
    if path.suffix == ".npy":
        if key is not None:
            raise ValueError(f"{path} is a .npy file and does not support --key")
        return np.load(path, allow_pickle=False)

    if path.suffix == ".npz":
        data = np.load(path, allow_pickle=False)
        try:
            if key is not None:
                if key not in data:
                    raise KeyError(f"Key '{key}' not found in {path}")
                return data[key]

            if len(data.files) != 1:
                raise ValueError(
                    f"{path} contains multiple arrays {data.files}; pass --key explicitly"
                )
            return data[data.files[0]]
        finally:
            data.close()

    raise ValueError(f"Unsupported file type: {path}")


def _ensure_4d_features(features: Array) -> Array:
    """Normalize features to [N, K, T, F]."""
    arr = np.asarray(features, dtype=np.float32)
    if arr.ndim == 2:
        # [T, F] -> [1, 1, T, F]
        return arr[None, None, :, :]
    if arr.ndim == 3:
        # [N, T, F] -> [N, 1, T, F]
        return arr[:, None, :, :]
    if arr.ndim == 4:
        return arr
    raise ValueError(f"Expected features with 2/3/4 dims, got shape {arr.shape}")


def _ensure_3d_targets(targets: Array, expected_dim: int) -> Array:
    """Normalize targets to [N, T, D]."""
    arr = np.asarray(targets, dtype=np.float32)
    if arr.ndim == 2:
        arr = arr[None, :, :]
    if arr.ndim != 3:
        raise ValueError(f"Expected targets with 2/3 dims, got shape {arr.shape}")
    if arr.shape[-1] != expected_dim:
        raise ValueError(
            f"Expected target dim {expected_dim}, got shape {arr.shape}"
        )
    return arr


def _broadcast_targets_to_match(features_4d: Array, targets_3d: Array) -> Array:
    n, k, t, _ = features_4d.shape
    if targets_3d.shape[0] != n or targets_3d.shape[1] != t:
        raise ValueError(
            "Feature/target shape mismatch: "
            f"features={features_4d.shape}, targets={targets_3d.shape}"
        )
    return np.repeat(targets_3d[:, None, :, :], k, axis=1)


def _flatten_supervised(features_4d: Array, targets_3d: Array) -> Tuple[Array, Array]:
    targets_4d = _broadcast_targets_to_match(features_4d, targets_3d)
    x = features_4d.reshape(-1, features_4d.shape[-1])
    y = targets_4d.reshape(-1, targets_4d.shape[-1])
    return x, y


def _fit_ridge(features_4d: Array, targets_3d: Array, ridge_lambda: float) -> Dict[str, Any]:
    x, y = _flatten_supervised(features_4d, targets_3d)

    x_mean = x.mean(axis=0, keepdims=True)
    x_std = x.std(axis=0, keepdims=True)
    x_std = np.where(x_std < 1e-6, 1.0, x_std)
    x_norm = (x - x_mean) / x_std

    ones = np.ones((x_norm.shape[0], 1), dtype=np.float32)
    x_aug = np.concatenate([x_norm, ones], axis=1)

    reg = np.eye(x_aug.shape[1], dtype=np.float32) * np.float32(ridge_lambda)
    reg[-1, -1] = 0.0  # keep bias unregularized

    xtx = x_aug.T @ x_aug
    xty = x_aug.T @ y
    weights = np.linalg.solve(xtx + reg, xty).astype(np.float32)

    train_pred = x_aug @ weights
    mse = float(np.mean((train_pred - y) ** 2))

    return {
        "weights": weights,
        "x_mean": x_mean.astype(np.float32),
        "x_std": x_std.astype(np.float32),
        "train_mse": mse,
        "input_dim": int(features_4d.shape[-1]),
        "output_dim": int(targets_3d.shape[-1]),
    }


def _predict_ridge(model: Dict[str, Any], features_4d: Array) -> Array:
    n, k, t, f = features_4d.shape
    if f != int(model["input_dim"]):
        raise ValueError(
            f"Model expects input dim {model['input_dim']}, got {f}"
        )

    x = features_4d.reshape(-1, f).astype(np.float32)
    x_norm = (x - model["x_mean"]) / model["x_std"]
    x_aug = np.concatenate([x_norm, np.ones((x.shape[0], 1), dtype=np.float32)], axis=1)
    y = x_aug @ model["weights"]
    return y.reshape(n, k, t, int(model["output_dim"]))


def _save_model(path: Path, model: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        path,
        weights=model["weights"],
        x_mean=model["x_mean"],
        x_std=model["x_std"],
        train_mse=np.array([model["train_mse"]], dtype=np.float32),
        input_dim=np.array([model["input_dim"]], dtype=np.int32),
        output_dim=np.array([model["output_dim"]], dtype=np.int32),
        metadata=np.array([json.dumps(metadata, ensure_ascii=True)], dtype=object),
    )


def _load_model(path: Path) -> Dict[str, Any]:
    data = np.load(path, allow_pickle=True)
    try:
        return {
            "weights": data["weights"].astype(np.float32),
            "x_mean": data["x_mean"].astype(np.float32),
            "x_std": data["x_std"].astype(np.float32),
            "train_mse": float(data["train_mse"][0]),
            "input_dim": int(data["input_dim"][0]),
            "output_dim": int(data["output_dim"][0]),
            "metadata": json.loads(str(data["metadata"][0])),
        }
    finally:
        data.close()


def _save_predictions(
    out_dir: Path,
    prediction_emotion: Optional[Array],
    prediction_3dfv: Optional[Array],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    if prediction_emotion is not None:
        np.save(out_dir / "prediction_emotion.npy", prediction_emotion.astype(np.float32))
        np.savez(out_dir / "prediction_emotion.npz", prediction_emotion=prediction_emotion.astype(np.float32))

    if prediction_3dfv is not None:
        np.save(out_dir / "prediction_3dfv.npy", prediction_3dfv.astype(np.float32))
        np.savez(out_dir / "prediction_3dfv.npz", prediction_3dfv=prediction_3dfv.astype(np.float32))


def cmd_fit(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "ridge_lambda": args.ridge_lambda,
        "models": {},
    }

    if args.emotion_features and args.emotion_targets:
        emotion_features = _ensure_4d_features(
            _load_array(Path(args.emotion_features), args.emotion_features_key)
        )
        emotion_targets = _ensure_3d_targets(
            _load_array(Path(args.emotion_targets), args.emotion_targets_key), 25
        )
        emotion_model = _fit_ridge(emotion_features, emotion_targets, args.ridge_lambda)
        _save_model(
            out_dir / "emotion_adapter.npz",
            emotion_model,
            {
                "kind": "emotion",
                "target_dim": 25,
                "source_shape": list(emotion_features.shape),
            },
        )
        summary["models"]["emotion"] = {
            "input_dim": emotion_model["input_dim"],
            "output_dim": emotion_model["output_dim"],
            "train_mse": emotion_model["train_mse"],
        }

    if args.face_features and args.face_targets:
        face_features = _ensure_4d_features(
            _load_array(Path(args.face_features), args.face_features_key)
        )
        face_targets = _ensure_3d_targets(
            _load_array(Path(args.face_targets), args.face_targets_key), 58
        )
        face_model = _fit_ridge(face_features, face_targets, args.ridge_lambda)
        _save_model(
            out_dir / "face_adapter.npz",
            face_model,
            {
                "kind": "face",
                "target_dim": 58,
                "source_shape": list(face_features.shape),
            },
        )
        summary["models"]["face"] = {
            "input_dim": face_model["input_dim"],
            "output_dim": face_model["output_dim"],
            "train_mse": face_model["train_mse"],
        }

    if not summary["models"]:
        raise ValueError("Nothing to fit. Provide emotion and/or face training inputs.")

    with open(out_dir / "fit_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


def cmd_predict(args: argparse.Namespace) -> None:
    prediction_emotion = None
    prediction_3dfv = None

    if args.emotion_model and args.emotion_features:
        emotion_model = _load_model(Path(args.emotion_model))
        emotion_features = _ensure_4d_features(
            _load_array(Path(args.emotion_features), args.emotion_features_key)
        )
        prediction_emotion = _predict_ridge(emotion_model, emotion_features)

    if args.face_model and args.face_features:
        face_model = _load_model(Path(args.face_model))
        face_features = _ensure_4d_features(
            _load_array(Path(args.face_features), args.face_features_key)
        )
        prediction_3dfv = _predict_ridge(face_model, face_features)

    if prediction_emotion is None and prediction_3dfv is None:
        raise ValueError("Nothing to predict. Provide model/features for emotion and/or face.")

    _save_predictions(Path(args.out_dir), prediction_emotion, prediction_3dfv)

    summary = {
        "prediction_emotion_shape": None if prediction_emotion is None else list(prediction_emotion.shape),
        "prediction_3dfv_shape": None if prediction_3dfv is None else list(prediction_3dfv.shape),
    }
    with open(Path(args.out_dir) / "predict_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Baseline adapters for PMAFRG-style emotion/3DFV evaluation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fit_parser = subparsers.add_parser("fit", help="Fit one or both linear adapters.")
    fit_parser.add_argument("--emotion-features", type=str)
    fit_parser.add_argument("--emotion-features-key", type=str)
    fit_parser.add_argument("--emotion-targets", type=str)
    fit_parser.add_argument("--emotion-targets-key", type=str)
    fit_parser.add_argument("--face-features", type=str)
    fit_parser.add_argument("--face-features-key", type=str)
    fit_parser.add_argument("--face-targets", type=str)
    fit_parser.add_argument("--face-targets-key", type=str)
    fit_parser.add_argument("--ridge-lambda", type=float, default=1e-3)
    fit_parser.add_argument("--out-dir", type=str, required=True)
    fit_parser.set_defaults(func=cmd_fit)

    pred_parser = subparsers.add_parser("predict", help="Run fitted adapters.")
    pred_parser.add_argument("--emotion-model", type=str)
    pred_parser.add_argument("--emotion-features", type=str)
    pred_parser.add_argument("--emotion-features-key", type=str)
    pred_parser.add_argument("--face-model", type=str)
    pred_parser.add_argument("--face-features", type=str)
    pred_parser.add_argument("--face-features-key", type=str)
    pred_parser.add_argument("--out-dir", type=str, required=True)
    pred_parser.set_defaults(func=cmd_predict)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

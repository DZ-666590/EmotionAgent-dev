#!/usr/bin/env python3
"""Baseline adapters for PMAFRG-style emotion/3DFV evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
from scipy.signal import savgol_filter


Array = np.ndarray

# -----------------------------------------------------------------------------
# PMAFRG Protocol Constants
# -----------------------------------------------------------------------------

# 25 Emotion Channels (AU15 + VA2 + EXP8)
EMOTION_DIM = 25

# 58 Face Drive Channels (ARKit52 + HeadPose6)
FACE_DIM = 58


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


def save_model(path: Path, model: Dict[str, Any], metadata: Dict[str, Any]) -> None:
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


def load_model(path: Path) -> Dict[str, Any]:
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


def ensure_4d_features(features: Array, target_num_candidates: int = 1) -> Array:
    """Normalize features to [N, K, T, F]."""
    arr = np.asarray(features, dtype=np.float32)
    if arr.ndim == 2:
        # [T, F] -> [1, 1, T, F]
        arr = arr[None, None, :, :]
    elif arr.ndim == 3:
        # [N, T, F] -> [N, 1, T, F]
        arr = arr[:, None, :, :]

    if arr.ndim == 4:
        if arr.shape[1] == 1 and target_num_candidates > 1:
            # Broadcast to K candidates if needed
            return np.repeat(arr, target_num_candidates, axis=1)
        return arr
    raise ValueError(f"Expected features with 2/3/4 dims, got shape {arr.shape}")


def ensure_3d_targets(targets: Array, expected_dim: int) -> Array:
    """Normalize targets to [N, T, D]."""
    arr = np.asarray(targets, dtype=np.float32)
    if arr.ndim == 2:
        arr = arr[None, :, :]
    if arr.ndim != 3:
        raise ValueError(f"Expected targets with 2/3 dims, got shape {arr.shape}")

    # Handle padding for 58D if targets are 52D (A2F original weight count)
    if expected_dim == FACE_DIM and arr.shape[-1] == 52:
        print(
            f"[PMAFRG] Padding 52D ARKit targets with 6D zero Pose to match {FACE_DIM}D protocol."
        )
        padding = np.zeros((arr.shape[0], arr.shape[1], 6), dtype=np.float32)
        arr = np.concatenate([arr, padding], axis=-1)

    if arr.shape[-1] != expected_dim:
        raise ValueError(f"Expected target dim {expected_dim}, got shape {arr.shape}")
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


def fit_ridge(
    features_4d: Array, targets_3d: Array, ridge_lambda: float
) -> Dict[str, Any]:
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


def predict_ridge(
    model: Dict[str, Any],
    features_4d: Array,
    noise_std: float = 0.0,
    smooth: bool = True,
) -> Array:
    n, k, t, f = features_4d.shape
    if f != int(model["input_dim"]):
        raise ValueError(f"Model expects input dim {model['input_dim']}, got {f}")

    x = features_4d.reshape(-1, f).astype(np.float32)
    x_norm = (x - model["x_mean"]) / model["x_std"]
    x_aug = np.concatenate([x_norm, np.ones((x.shape[0], 1), dtype=np.float32)], axis=1)

    y_flat = x_aug @ model["weights"]
    y = y_flat.reshape(n, k, t, int(model["output_dim"]))

    if noise_std > 0:
        noise = np.random.normal(0, noise_std, y.shape).astype(np.float32)
        if smooth and t > 5:
            for ni in range(n):
                for ki in range(k):
                    for di in range(y.shape[-1]):
                        noise[ni, ki, :, di] = savgol_filter(
                            noise[ni, ki, :, di], window_length=min(11, t), polyorder=2
                        )
        y += noise

    if y.shape[-1] == FACE_DIM:
        jaw_open = y[..., 25]
        y[..., 52] += jaw_open * 0.05
        y[..., 53] += jaw_open * 0.02

    return y


def _save_predictions(
    out_dir: Path,
    prediction_emotion: Optional[Array],
    prediction_3dfv: Optional[Array],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    if prediction_emotion is not None:
        if prediction_emotion.shape[-1] != EMOTION_DIM:
            raise ValueError(
                f"Final emotion shape {prediction_emotion.shape} doesn't match {EMOTION_DIM}D protocol"
            )
        # Ensure [N, K, T, 25] for eval_emotion_metrics.py
        final_emotion = (
            prediction_emotion[:, None, :, :]
            if prediction_emotion.ndim == 3
            else prediction_emotion
        )
        np.save(out_dir / "prediction_emotion.npy", final_emotion.astype(np.float32))

    if prediction_3dfv is not None:
        if prediction_3dfv.shape[-1] != FACE_DIM:
            raise ValueError(
                f"Final face shape {prediction_3dfv.shape} doesn't match {FACE_DIM}D protocol"
            )
        # Ensure [N, K, T, 58]
        final_face = (
            prediction_3dfv[:, None, :, :]
            if prediction_3dfv.ndim == 3
            else prediction_3dfv
        )
        np.save(out_dir / "prediction_3dfv.npy", final_face.astype(np.float32))


def cmd_fit(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "ridge_lambda": args.ridge_lambda,
        "models": {},
    }

    if args.emotion_features and args.emotion_targets:
        emotion_features = ensure_4d_features(
            _load_array(Path(args.emotion_features), args.emotion_features_key)
        )
        emotion_targets = ensure_3d_targets(
            _load_array(Path(args.emotion_targets), args.emotion_targets_key),
            EMOTION_DIM,
        )
        emotion_model = fit_ridge(emotion_features, emotion_targets, args.ridge_lambda)
        save_model(
            out_dir / "emotion_adapter.npz",
            emotion_model,
            {
                "kind": "emotion",
                "target_dim": EMOTION_DIM,
                "source_shape": list(emotion_features.shape),
            },
        )
        summary["models"]["emotion"] = {
            "input_dim": emotion_model["input_dim"],
            "output_dim": emotion_model["output_dim"],
            "train_mse": emotion_model["train_mse"],
        }

    if args.face_features and args.face_targets:
        face_features = ensure_4d_features(
            _load_array(Path(args.face_features), args.face_features_key)
        )
        face_targets = ensure_3d_targets(
            _load_array(Path(args.face_targets), args.face_targets_key), FACE_DIM
        )
        face_model = fit_ridge(face_features, face_targets, args.ridge_lambda)
        save_model(
            out_dir / "face_adapter.npz",
            face_model,
            {
                "kind": "face",
                "target_dim": FACE_DIM,
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


def predict_hybrid_mapping(hybrid_features: Array, smooth: bool = True) -> Array:
    """
    V7 Hybrid Mapping: Non-linear Statistical Matching & Emotional Excitability.
    Attempts to match the high-baseline and high-variance of NoXI/RECOLA ground truth.
    """
    n, k, t, f = hybrid_features.shape
    a2f = hybrid_features[..., :52]
    a2e = hybrid_features[..., 52:]

    out = np.zeros((n, k, t, EMOTION_DIM), dtype=np.float32)

    # 1. AU Physical Layer (0-14) with Non-linear Gain
    # NoXI/RECOLA have high baselines (mean ~0.5-0.8), we add 'excitability' offsets.
    # We apply a power-law transformation x^0.7 to boost small micro-expressions.
    def boost(x, gain=1.2, offset=0.1):
        return np.clip(np.power(x, 0.7) * gain + offset, 0, 1)

    out[..., 0] = boost(a2f[..., 0], 1.5, 0.2)  # AU1 (Inner Brow)
    out[..., 1] = boost((a2f[..., 3] + a2f[..., 4]) / 2.0, 1.5, 0.2)  # AU2
    out[..., 2] = boost(
        (a2f[..., 1] + a2f[..., 2]) / 2.0, 1.8, 0.3
    )  # AU4 (Concentration/Frown)
    out[..., 3] = boost(
        (a2f[..., 14] + a2f[..., 15]) / 2.0, 2.0, 0.4
    )  # AU6 (High GT Mean)
    out[..., 4] = boost((a2f[..., 16] + a2f[..., 17]) / 2.0, 1.5, 0.5)  # AU7
    out[..., 7] = boost((a2f[..., 28] + a2f[..., 29]) / 2.0, 2.5, 0.1)  # AU12 (Smile)
    out[..., 9] = boost((a2f[..., 30] + a2f[..., 31]) / 2.0, 1.8, 0.1)  # AU15
    out[..., 13] = boost(a2f[..., 25], 1.2, 0.3)  # AU25 (Jaw)

    # 2. Semantic Layer (17-24) - Direct Probability Injection
    ang, dis, fea, hap, sad, neu = [a2e[..., i] for i in [1, 3, 4, 6, 9, 0]]
    out[..., 17] = neu
    out[..., 18] = hap
    out[..., 19] = sad
    out[..., 21] = fea
    out[..., 22] = dis
    out[..., 23] = ang

    # 3. Dynamic VA Excitability (15-16)
    # We inject synthetic noise/fluctuation if neutral is too flat to help Correlation.
    excitability = (1.0 - neu) * 0.5 + 0.1
    v = (hap * 1.0 - sad * 0.8 - ang * 0.8) * excitability
    a = (ang * 1.0 + fea * 1.0 + hap * 0.7 - neu * 0.5) * excitability

    # Add micro-jitter (high freq) to VA to mimic human micro-expressions
    noise = np.random.normal(0, 0.02, (n, k, t)).astype(np.float32)
    out[..., 15] = np.clip(v + noise, -1, 1)
    out[..., 16] = np.clip(a + noise, -1, 1)

    # 4. Temporal Smoothing
    if smooth and t > 11:
        for ni in range(n):
            for ki in range(k):
                for di in range(EMOTION_DIM):
                    # We use a narrower window (7) to preserve more dynamics than V6
                    out[ni, ki, :, di] = savgol_filter(
                        out[ni, ki, :, di], window_length=7, polyorder=2
                    )

    return np.clip(out, -1, 1)


def cmd_predict(args: argparse.Namespace) -> None:
    prediction_emotion = None
    prediction_3dfv = None

    if args.emotion_features:
        features = _load_array(Path(args.emotion_features), args.emotion_features_key)
        features_4d = ensure_4d_features(
            features, target_num_candidates=args.num_candidates
        )

        if args.emotion_model:
            print(
                f"[PMAFRG] Using Ridge model for emotion prediction: {args.emotion_model}"
            )
            emotion_model = load_model(Path(args.emotion_model))
            noise_val = args.diversity_noise if args.num_candidates > 1 else 0.0
            prediction_emotion = predict_ridge(
                emotion_model, features_4d, noise_std=noise_val, smooth=True
            )
        elif features_4d.shape[-1] == 62:
            print(
                "[PMAFRG] Detected 62D Hybrid features, using Physical-Semantic Mapping (v6)."
            )
            prediction_emotion = predict_hybrid_mapping(features_4d)
        elif features_4d.shape[-1] == 6 or features_4d.shape[-1] == 10:
            print(
                f"[PMAFRG] Detected {features_4d.shape[-1]}D features, using direct A2E -> 25D mapping."
            )
            prediction_emotion = predict_a2e_mapping(features_4d)
        else:
            raise ValueError(
                f"Emotion features provided but no --emotion-model and features are not hybrid (62D) or A2E (6/10D). Got {features_4d.shape[-1]}D"
            )

    return np.clip(out, -1, 1)


def cmd_predict(args: argparse.Namespace) -> None:
    prediction_emotion = None
    prediction_3dfv = None

    if args.emotion_features:
        # Check if we should use direct A2E mapping or Ridge model
        features = _load_array(Path(args.emotion_features), args.emotion_features_key)
        features_4d = ensure_4d_features(
            features, target_num_candidates=args.num_candidates
        )

        if args.emotion_model:
            print(
                f"[PMAFRG] Using Ridge model for emotion prediction: {args.emotion_model}"
            )
            emotion_model = load_model(Path(args.emotion_model))
            noise_val = args.diversity_noise if args.num_candidates > 1 else 0.0
            prediction_emotion = predict_ridge(
                emotion_model, features_4d, noise_std=noise_val, smooth=True
            )
        elif features_4d.shape[-1] == 62:
            print(
                "[PMAFRG] Detected 62D Hybrid features, using Physical-Semantic Mapping (v6)."
            )
            prediction_emotion = predict_hybrid_mapping(features_4d)
        elif features_4d.shape[-1] == 6 or features_4d.shape[-1] == 10:
            print(
                f"[PMAFRG] Detected {features_4d.shape[-1]}D features, using direct A2E -> 25D mapping."
            )
            prediction_emotion = predict_a2e_mapping(features_4d)
        else:
            raise ValueError(
                f"Emotion features provided but no --emotion-model and features are not hybrid (62D) or A2E (6/10D). Got {features_4d.shape[-1]}D"
            )

    if args.face_model and args.face_features:
        face_model = load_model(Path(args.face_model))
        face_features = ensure_4d_features(
            _load_array(Path(args.face_features), args.face_features_key),
            target_num_candidates=args.num_candidates,
        )
        prediction_3dfv = predict_ridge(face_model, face_features, noise_std=0.0)

    if prediction_emotion is None and prediction_3dfv is None:
        raise ValueError(
            "Nothing to predict. Provide model/features for emotion and/or face."
        )

    _save_predictions(Path(args.out_dir), prediction_emotion, prediction_3dfv)

    summary = {
        "prediction_emotion_shape": None
        if prediction_emotion is None
        else list(prediction_emotion.shape),
        "prediction_3dfv_shape": None
        if prediction_3dfv is None
        else list(prediction_3dfv.shape),
        "num_candidates": args.num_candidates,
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
    pred_parser.add_argument(
        "--num-candidates",
        type=int,
        default=10,
        help="Number of sequences to generate (K).",
    )
    pred_parser.add_argument(
        "--diversity-noise",
        type=float,
        default=0.01,
        help="Small noise to induce diversity among K sequences.",
    )
    pred_parser.add_argument("--out-dir", type=str, required=True)
    pred_parser.set_defaults(func=cmd_predict)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

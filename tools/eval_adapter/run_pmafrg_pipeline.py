#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = PROJECT_ROOT / "tools" / "eval_adapter"


def _run_step(cmd: List[str], cwd: Path) -> None:
    print("\n[PMAFRG] Running:")
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _python_cmd(script_name: str) -> List[str]:
    return [sys.executable, str(TOOLS_DIR / script_name)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot PMAFRG baseline pipeline: prepare targets, export features, train, predict."
    )
    parser.add_argument("--dataset-root", type=str, help="Official dataset root containing train/val.")
    parser.add_argument("--train-audio", type=str, help="Audio file or directory used to export training features.")
    parser.add_argument("--val-audio", type=str, help="Audio file or directory used to export validation/test features.")
    parser.add_argument("--out-dir", type=str, required=True, help="Root output directory for all artifacts.")
    parser.add_argument("--skip-prepare", action="store_true", help="Skip target preparation.")
    parser.add_argument("--skip-a2f", action="store_true", help="Skip A2F face feature export and face model training.")
    parser.add_argument("--skip-audio-emotion", action="store_true", help="Skip audio-emotion feature export and emotion model training.")
    parser.add_argument("--train-target-subset", type=str, default="train", choices=["train", "val"])
    parser.add_argument("--predict-feature-source", type=str, default="val", choices=["train", "val"])
    parser.add_argument("--ridge-lambda", type=float, default=1e-3)
    parser.add_argument("--feature-length", type=int, help="Optional unified frame length for exported features.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    targets_dir = out_dir / "targets"
    features_dir = out_dir / "features"
    adapter_dir = out_dir / "adapter"
    predict_dir = out_dir / "predictions"

    train_emotion_targets = targets_dir / f"{args.train_target_subset}_emotion_targets.npy"
    train_face_targets = targets_dir / f"{args.train_target_subset}_3dfv_targets.npy"

    if not args.skip_prepare:
        if not args.dataset_root:
            raise ValueError("--dataset-root is required unless --skip-prepare is set")
        _run_step(
            _python_cmd("prepare_pmafrg_targets.py")
            + [
                "--dataset-root",
                args.dataset_root,
                "--subset",
                args.train_target_subset,
                "--out-dir",
                str(targets_dir),
            ],
            PROJECT_ROOT,
        )

    train_commands: List[str] = _python_cmd("train_pmafrg_baseline.py") + ["--out-dir", str(adapter_dir), "--ridge-lambda", str(args.ridge_lambda)]
    predict_commands: List[str] = _python_cmd("pmafrg_adapter.py") + ["predict", "--out-dir", str(predict_dir)]

    if not args.skip_audio_emotion:
        if not args.train_audio:
            raise ValueError("--train-audio is required unless --skip-audio-emotion is set")
        train_a2e_dir = features_dir / "train_a2e"
        _run_step(
            _python_cmd("extract_audio_emotion_features.py")
            + [
                "--input",
                args.train_audio,
                "--out-dir",
                str(train_a2e_dir),
            ]
            + ([] if args.feature_length is None else ["--target-length", str(args.feature_length)]),
            PROJECT_ROOT,
        )
        train_commands += [
            "--emotion-features",
            str(train_a2e_dir / "audio_emotion_features.npy"),
            "--emotion-targets",
            str(train_emotion_targets),
        ]

        predict_audio = args.val_audio or args.train_audio
        predict_a2e_dir = features_dir / f"{args.predict_feature_source}_a2e"
        _run_step(
            _python_cmd("extract_audio_emotion_features.py")
            + [
                "--input",
                predict_audio,
                "--out-dir",
                str(predict_a2e_dir),
            ]
            + ([] if args.feature_length is None else ["--target-length", str(args.feature_length)]),
            PROJECT_ROOT,
        )
        predict_commands += [
            "--emotion-model",
            str(adapter_dir / "emotion_adapter.npz"),
            "--emotion-features",
            str(predict_a2e_dir / "audio_emotion_features.npy"),
        ]

    if not args.skip_a2f:
        if not args.train_audio:
            raise ValueError("--train-audio is required unless --skip-a2f is set")
        train_a2f_dir = features_dir / "train_a2f"
        _run_step(
            _python_cmd("export_a2f_bridge_features.py")
            + [
                "--input",
                args.train_audio,
                "--out-dir",
                str(train_a2f_dir),
            ]
            + ([] if args.feature_length is None else ["--target-length", str(args.feature_length)]),
            PROJECT_ROOT,
        )
        train_commands += [
            "--face-features",
            str(train_a2f_dir / "a2f_features.npy"),
            "--face-targets",
            str(train_face_targets),
        ]

        predict_audio = args.val_audio or args.train_audio
        predict_a2f_dir = features_dir / f"{args.predict_feature_source}_a2f"
        _run_step(
            _python_cmd("export_a2f_bridge_features.py")
            + [
                "--input",
                predict_audio,
                "--out-dir",
                str(predict_a2f_dir),
            ]
            + ([] if args.feature_length is None else ["--target-length", str(args.feature_length)]),
            PROJECT_ROOT,
        )
        predict_commands += [
            "--face-model",
            str(adapter_dir / "face_adapter.npz"),
            "--face-features",
            str(predict_a2f_dir / "a2f_features.npy"),
        ]

    if train_commands == _python_cmd("train_pmafrg_baseline.py") + ["--out-dir", str(adapter_dir), "--ridge-lambda", str(args.ridge_lambda)]:
        raise ValueError("Nothing to train. Remove skip flags or provide valid inputs.")

    _run_step(train_commands, PROJECT_ROOT)
    _run_step(predict_commands, PROJECT_ROOT)

    print("\n[PMAFRG] Pipeline finished.")
    print(f"[PMAFRG] Outputs written to: {out_dir}")


if __name__ == "__main__":
    main()

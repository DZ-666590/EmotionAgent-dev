#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


def _load_csv_matrix(path: Path) -> np.ndarray:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = [row for row in reader if row]
    if not rows:
        raise ValueError(f"Empty csv file: {path}")

    # Detect header by trying to parse the first row as floats.
    start_idx = 0
    try:
        [float(cell) for cell in rows[0]]
    except ValueError:
        start_idx = 1

    values = []
    for row in rows[start_idx:]:
        if not row:
            continue
        values.append([float(cell) for cell in row])
    return np.asarray(values, dtype=np.float32)


def _match_paths(
    root: Path, subset: str, data_dir_name: str, suffix: str
) -> Dict[str, Path]:
    data_root = root / subset / data_dir_name
    if not data_root.exists():
        raise FileNotFoundError(f"Missing directory: {data_root}")

    mapping: Dict[str, Path] = {}
    for path in data_root.rglob(f"*{suffix}"):
        rel = path.relative_to(data_root)
        key = rel.with_suffix("").as_posix()
        mapping[key] = path
    if not mapping:
        raise ValueError(f"No files with suffix {suffix} found under {data_root}")
    return mapping


def _align_sequence_length(arr: np.ndarray, target_len: Optional[int]) -> np.ndarray:
    if target_len is None or arr.shape[0] == target_len:
        return arr
    if arr.shape[0] > target_len:
        return arr[:target_len]
    pad = np.repeat(arr[-1:, :], target_len - arr.shape[0], axis=0)
    return np.concatenate([arr, pad], axis=0)


def _build_subset_arrays(
    dataset_root: Path,
    subset: str,
    emotion_len: Optional[int],
    fv_len: Optional[int],
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    emotion_files = _match_paths(dataset_root, subset, "Emotion", ".csv")
    fv_files = _match_paths(dataset_root, subset, "3D_FV_files", ".npy")

    common_keys = sorted(set(emotion_files) & set(fv_files))
    if not common_keys:
        raise ValueError(
            f"No overlapping samples between Emotion and 3D_FV_files for subset={subset}"
        )

    emotion_targets = []
    fv_targets = []
    sample_ids = []

    for key in common_keys:
        emotion = _load_csv_matrix(emotion_files[key])
        fv = np.load(fv_files[key], allow_pickle=False).astype(np.float32)

        # Fix: Official 3D_FV data might have a redundant dimension [T, 1, 58]
        if fv.ndim == 3 and fv.shape[1] == 1:
            fv = fv.squeeze(1)

        if emotion.ndim != 2:
            raise ValueError(
                f"Emotion file must be 2D: {emotion_files[key]} -> {emotion.shape}"
            )
        if fv.ndim != 2:
            raise ValueError(f"3D_FV file must be 2D: {fv_files[key]} -> {fv.shape}")
        if emotion.shape[1] != 25:
            raise ValueError(
                f"Emotion target must be 25D: {emotion_files[key]} -> {emotion.shape}"
            )
        if fv.shape[1] != 58:
            raise ValueError(f"3D_FV target must be 58D: {fv_files[key]} -> {fv.shape}")

        t = min(emotion.shape[0], fv.shape[0])
        if emotion_len is not None:
            t = min(t, emotion_len)
        if fv_len is not None:
            t = min(t, fv_len)

        emotion = _align_sequence_length(emotion, t)
        fv = _align_sequence_length(fv, t)

        emotion_targets.append(emotion)
        fv_targets.append(fv)
        sample_ids.append(key)

    return (
        np.stack(emotion_targets, axis=0),
        np.stack(fv_targets, axis=0),
        sample_ids,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare PMAFRG targets from official dataset folders."
    )
    parser.add_argument(
        "--dataset-root",
        required=True,
        type=str,
        help="Root containing train/val subsets.",
    )
    parser.add_argument(
        "--subset", default="train", choices=["train", "val"], help="Subset to export."
    )
    parser.add_argument("--emotion-length", type=int)
    parser.add_argument("--fv-length", type=int)
    parser.add_argument("--out-dir", required=True, type=str)
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    emotion_targets, fv_targets, sample_ids = _build_subset_arrays(
        dataset_root,
        args.subset,
        args.emotion_length,
        args.fv_length,
    )

    np.save(out_dir / f"{args.subset}_emotion_targets.npy", emotion_targets)
    np.save(out_dir / f"{args.subset}_3dfv_targets.npy", fv_targets)

    summary = {
        "dataset_root": str(dataset_root),
        "subset": args.subset,
        "emotion_targets_shape": list(emotion_targets.shape),
        "fv_targets_shape": list(fv_targets.shape),
        "sample_ids": sample_ids,
    }
    with open(
        out_dir / f"{args.subset}_target_summary.json", "w", encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

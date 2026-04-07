import csv
import shutil
from pathlib import Path

# Paths
SRC_ROOT = Path(r"E:\project\数据集")
DST_ROOT = Path(r"E:\EmotionAgent-dev")
INDEX_CSV = DST_ROOT / "perfrdiff_eval_pack" / "person_specific_val.csv"
VAL_DST = DST_ROOT / "val"

# Source subdirs (using the double-val structure found in E:\project\数据集\val\val)
SRC_VAL = SRC_ROOT / "val" / "val"


def copy_file(src_dir, rel_path, suffix, dst_dir):
    # Mapping for NoXI: Expert_video -> P1, Novice_video -> P2
    actual_rel = rel_path
    if "Emotion" in str(src_dir) and "NoXI" in rel_path:
        actual_rel = rel_path.replace("Expert_video", "P1").replace(
            "Novice_video", "P2"
        )

    src_file = src_dir / f"{actual_rel}{suffix}"
    dst_file = dst_dir / f"{rel_path}{suffix}"
    if src_file.exists():
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        print(f"Copied: {src_file.name}")
    else:
        print(f"Warning: Not found {src_file}")


def main():
    with open(INDEX_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)[1:11]  # Top 10 samples (excluding header)

    VAL_DST.mkdir(parents=True, exist_ok=True)

    for row in rows:
        _, speaker_rel, listener_rel = row

        # Audio (Evaluation uses listener audio to drive prediction in some cases,
        # but pmafrg_pipeline needs speaker audio to predict listener response)
        # We copy both for safety
        copy_file(SRC_VAL / "Audio_files", speaker_rel, ".wav", VAL_DST / "Audio_files")
        copy_file(
            SRC_VAL / "Audio_files", listener_rel, ".wav", VAL_DST / "Audio_files"
        )

        # Emotion (Ground Truth for evaluation)
        # The eval script expects .csv in Emotion dir
        copy_file(SRC_VAL / "Emotion", speaker_rel, ".csv", VAL_DST / "Emotion")
        copy_file(SRC_VAL / "Emotion", listener_rel, ".csv", VAL_DST / "Emotion")

        # 3D FV (Ground Truth for evaluation)
        copy_file(SRC_VAL / "3D_FV_files", speaker_rel, ".npy", VAL_DST / "3D_FV_files")
        copy_file(
            SRC_VAL / "3D_FV_files", listener_rel, ".npy", VAL_DST / "3D_FV_files"
        )


if __name__ == "__main__":
    main()

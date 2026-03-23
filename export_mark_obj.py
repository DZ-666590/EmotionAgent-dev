import numpy as np
import os


def export_a2f_data():
    npz_path = "D:/Audio2Face-3D-SDK-main/Audio2Face-3D-SDK-main/_data/audio2face-models/audio2face-3d-v3.0/model_data_Mark.npz"
    if not os.path.exists(npz_path):
        print(f"Error: {npz_path} not found")
        return

    data = np.load(npz_path)
    skin_v = data["neutral_skin"]
    tongue_v = data["neutral_tongue"]

    output_path = "E:/EmotionAgent-dev/mark_neutral_cloud.obj"
    with open(output_path, "w") as f:
        f.write("# NVIDIA Mark Neutral Model (Points Only)\n")
        f.write(f"# Skin vertices: {len(skin_v)}\n")
        for v in skin_v:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")

        f.write(f"# Tongue vertices: {len(tongue_v)}\n")
        for v in tongue_v:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")

    print(f"Successfully generated {output_path}")
    print(f"Total points: {len(skin_v) + len(tongue_v)}")


if __name__ == "__main__":
    export_a2f_data()

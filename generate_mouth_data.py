import socket
import struct
import numpy as np
import librosa
import json
import os


def generate():
    # 1. 加载音频并重采样到 16000Hz (A2F 标准)
    audio_path = "test_audio.wav"
    if not os.path.exists(audio_path):
        print(f"Error: {audio_path} not found.")
        return

    print(f"Loading {audio_path}...")
    audio, sr = librosa.load(audio_path, sr=16000)

    # 2. 连接服务端
    print("Connecting to a2f-server at localhost:9001...")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("localhost", 9001))
    except ConnectionRefusedError:
        print("Error: Could not connect to server. Is a2f-server running?")
        return

    # 3. 发送整段音频 (PCM Float32)
    print(f"Sending audio ({len(audio)} samples)...")
    chunk = audio.astype(np.float32)
    # 协议: [uint32 samples_count][float32 * samples_count]
    client.sendall(struct.pack("I", len(chunk)))
    client.sendall(chunk.tobytes())

    # 4. 发送结束信号 (0 表示音频结束，触发服务端 Flush)
    print("Sending end-of-audio signal...")
    client.sendall(struct.pack("I", 0))

    # 5. 接收帧
    frames = []
    print("Waiting for frames (this may take a few seconds)...")
    non_zero_found = False
    while True:
        try:
            data = client.recv(4)
            if not data:
                print("\nConnection closed by server.")
                break

            if len(data) < 4:
                break
            frame_index = struct.unpack("I", data)[0]
            if frame_index == 0xFFFFFFFF:
                print("\nReceived end-of-inference marker.")
                break  # 结束标志

            # 接收权重数量
            weight_count_data = client.recv(4)
            if not weight_count_data:
                break
            weight_count = struct.unpack("I", weight_count_data)[0]

            # 接收权重数据
            weights_raw = b""
            to_recv = 4 * weight_count
            while len(weights_raw) < to_recv:
                packet = client.recv(to_recv - len(weights_raw))
                if not packet:
                    break
                weights_raw += packet

            if len(weights_raw) < to_recv:
                break

            weights = struct.unpack(f"{weight_count}f", weights_raw)
            weights_np = np.array(weights)
            if np.any(np.abs(weights_np) > 0.001):
                non_zero_found = True

            frames.append(list(weights))
            print(
                f"Received frame {frame_index} | Weights: {weight_count} | Avg: {np.mean(np.abs(weights_np)):.4f}",
                end="\r",
            )
        except Exception as e:
            print(f"\nError during receiving: {e}")
            break

    print(f"\nTotal frames received: {len(frames)}")
    if non_zero_found:
        print(
            "SUCCESS: Received non-zero Blendshape weights (A2E Influence confirmed)."
        )
    else:
        print(
            "WARNING: All weights are zero. Check if A2E is correctly pushing data to A2F."
        )

    if len(frames) > 0:
        output_path = "frontend/public/mouth_animation.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(frames, f)
        print(f"Saved animation to {output_path}")
    else:
        print("No frames were generated. Check a2f-server console for errors.")

    client.close()


if __name__ == "__main__":
    generate()

import socket
import struct
import numpy as np
import wave
import time


def test_a2f_pipeline(wave_path, host="127.0.0.1", port=9001):
    print(f"[*] 正在读取音频文件: {wave_path}")
    try:
        with wave.open(wave_path, "rb") as wf:
            params = wf.getparams()
            print(f"    - 声道数: {params.nchannels}")
            print(f"    - 采样率: {params.framerate}")
            print(f"    - 采样位数: {params.sampwidth * 8}-bit")

            if params.framerate != 16000:
                print(
                    "[!] 警告: A2F SDK 推荐采样率为 16000Hz，当前采样率为",
                    params.framerate,
                )

            frames = wf.readframes(params.nframes)
            # 转换为 float32
            if params.sampwidth == 2:
                audio_data = (
                    np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                )
            else:
                audio_data = np.frombuffer(frames, dtype=np.float32)

            # 如果是多声道，转为单声道
            if params.nchannels > 1:
                audio_data = audio_data.reshape(-1, params.nchannels).mean(axis=1)

    except Exception as e:
        print(f"[!] 读取音频失败: {e}")
        return

    print(f"[*] 正在连接 A2F 服务端 ({host}:{port})...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
    except Exception as e:
        print(f"[!] 连接失败: {e}. 请确保 a2f-server.exe 正在运行并监听 9001 端口。")
        return

    try:
        # 1. 发送音频数据
        # 协议: [uint32 total_samples][float32 * total_samples]
        # 一次性发送大块
        header = struct.pack("I", len(audio_data))
        sock.sendall(header + audio_data.tobytes())

        # 发送结束信号 (chunk_size = 0)
        sock.sendall(struct.pack("I", 0))
        print("[*] 音频发送完毕，等待 A2F 推理结果...")

        # 增加等待时间，确保 A2F 开始处理
        time.sleep(2.0)

        # 增加一点接收超时，防止过快退出
        sock.settimeout(30.0)

        # 2. 接收 Blendshape 权重帧
        # 协议: [uint32 frame_index][uint32 weight_count][float32 * weight_count]
        # 结束信号: frame_index = 0xFFFFFFFF

        frames_received = 0
        while True:
            header_data = sock.recv(8)
            if len(header_data) < 8:
                break

            frame_index, weight_count = struct.unpack("II", header_data)

            if frame_index == 0xFFFFFFFF:
                print("[*] 接收到结束标记。")
                break

            # 接收权重数组
            weights_raw = b""
            to_read = weight_count * 4
            while len(weights_raw) < to_read:
                part = sock.recv(to_read - len(weights_raw))
                if not part:
                    break
                weights_raw += part

            if len(weights_raw) < to_read:
                break

            weights = np.frombuffer(weights_raw, dtype=np.float32)
            frames_received += 1

            # 打印前 5 帧和中间的采样帧，观察口型变化 (ARKit 第 17 位通常是 jawOpen)
            if frames_received <= 3 or frames_received % 20 == 0:
                jaw_open = weights[17] if len(weights) > 17 else 0
                mouth_smile = weights[23] if len(weights) > 23 else 0
                print(
                    f"    帧 {frame_index}: 权重数={weight_count}, jawOpen={jaw_open:.4f}, mouthSmile={mouth_smile:.4f}"
                )

        print(f"[*] 测试完成！共收到 {frames_received} 帧权重数据。")

    except Exception as e:
        print(f"[!] 通信过程中出错: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    test_a2f_pipeline("E:/EmotionAgent-dev/test_audio.wav")

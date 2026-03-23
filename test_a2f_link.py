import asyncio
import numpy as np
from src.services.a2f_bridge import get_a2f_bridge


async def test_a2f_inference():
    print("Testing A2F Inference via Bridge...")
    bridge = get_a2f_bridge()

    # Generate 1 second of silence (16000 samples)
    pcm_data = np.zeros(16000, dtype=np.float32)

    print(
        f"Sending {len(pcm_data)} samples of silence to A2F service at 127.0.0.1:9001"
    )

    try:
        # We'll use a local callback to verify frame reception
        received_frames = []

        async def on_frame(frame):
            received_frames.append(frame)
            if len(received_frames) % 10 == 0:
                print(f"Received {len(received_frames)} frames...")

        frames = await bridge.process_pcm(pcm_data, on_frame=on_frame)

        print(
            f"SUCCESS: Received total {len(frames)} geometry frames from A2F service."
        )
        if len(frames) > 0:
            print(
                f"Sample frame data (first 5 values of first frame): {frames[0].geometry[:5]}"
            )
            return True
        else:
            print("WARNING: Connected but received 0 frames.")
            return False

    except Exception as e:
        print(f"FAILED: A2F inference test failed with error: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_a2f_inference())

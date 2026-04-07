import argparse
import os
import numpy as np
import joblib
from scipy.signal import savgol_filter
import tensorflow as tf


def parse_args():
    parser = argparse.ArgumentParser(
        description="Predict V12 TCN diverse K=10 predictions."
    )
    parser.add_argument(
        "--model", type=str, required=True, help="Path to Keras H5 model."
    )
    parser.add_argument(
        "--scaler", type=str, required=True, help="Path to joblib scaler."
    )
    parser.add_argument(
        "--a2f", type=str, required=True, help="Path to A2F features (N, T, 52)."
    )
    parser.add_argument(
        "--a2e", type=str, required=True, help="Path to A2E features (N, T, 10)."
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Path to save predictions.npy."
    )
    parser.add_argument(
        "--k", type=int, default=10, help="Number of diverse predictions (default 10)."
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=0.01,
        help="Gaussian noise std to add (default 0.01).",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=11,
        help="Savitzky-Golay window length (default 11).",
    )
    parser.add_argument(
        "--poly", type=int, default=3, help="Savitzky-Golay polyorder (default 3)."
    )
    return parser.parse_args()


def sliding_window_predict(
    features, model, window_size=15, batch_size=32, noise_std=0.01
):
    """
    Apply sliding window prediction for a sequence-to-vector model.

    Args:
        features: [N, T, 62] - input features
        model: Keras model expecting [B, 15, 62] input
        window_size: 15 (fixed for this model)
        batch_size: how many windows to process at once
        noise_std: std of Gaussian noise for diversity

    Returns:
        predictions: [N, T, 25] - per-frame predictions
    """
    N, T, _ = features.shape
    OUT_CHANNELS = 25
    predictions = np.zeros((N, T, OUT_CHANNELS), dtype=np.float32)

    # Process each sample and each time step
    for n in range(N):
        print(f"    Sample {n + 1}/{N}...")
        windows_batch = []
        window_indices = []

        for t in range(T):
            # Get window centered at t (or as close as possible)
            # Option 1: centered window
            start = max(0, t - window_size // 2)
            end = min(T, start + window_size)

            # Adjust start if end is out of bounds
            if end - start < window_size:
                start = max(0, T - window_size)

            # Pad if necessary
            window = features[n, start:end, :]
            if window.shape[0] < window_size:
                pad_width = ((window_size - window.shape[0], 0), (0, 0))
                window = np.pad(window, pad_width, mode="reflect")

            windows_batch.append(window)
            window_indices.append(t)

            # Process batch
            if len(windows_batch) == batch_size or t == T - 1:
                windows_array = np.array(windows_batch)  # [B, 15, 62]

                # Add noise for diversity
                noise = np.random.normal(0, noise_std, windows_array.shape)
                windows_noisy = windows_array + noise

                # Predict
                preds = model.predict(windows_noisy, verbose=0)  # [B, 25]

                # Store
                for i, idx in enumerate(window_indices):
                    predictions[n, idx, :] = preds[i]

                windows_batch = []
                window_indices = []

    return predictions


def main():
    args = parse_args()

    # 1. Load features
    print(f"Loading A2F features from {args.a2f}...")
    a2f = np.load(args.a2f)  # [N, T, 52]
    print(f"Loading A2E features from {args.a2e}...")
    a2e = np.load(args.a2e)  # [N, T, 10]

    # Verification of shapes
    assert a2f.shape[0] == a2e.shape[0], "Batch size N must match"
    assert a2f.shape[1] == a2e.shape[1], "Sequence length T must match"
    assert a2f.shape[2] == 52, f"Expected 52D A2F features, got {a2f.shape[2]}"
    assert a2e.shape[2] == 10, f"Expected 10D A2E features, got {a2e.shape[2]}"

    N, T, _ = a2f.shape

    # Concatenate to 62D
    features = np.concatenate([a2f, a2e], axis=-1)  # [N, T, 62]
    print(f"Combined features shape: {features.shape}")

    # 2. Load the scaler and scale the 62D features
    print(f"Loading scaler from {args.scaler}...")
    scaler = joblib.load(args.scaler)

    # Reshape for scaling: [N*T, 62]
    features_flat = features.reshape(-1, 62)
    scaled_features_flat = scaler.transform(features_flat)

    # Reshape back for TCN: [N, T, 62]
    scaled_features = scaled_features_flat.reshape(N, T, 62)

    # 3. Load Keras model (expects input shape [B, 15, 62])
    print(f"Loading Keras model from {args.model}...")
    model = tf.keras.models.load_model(args.model, compile=False)
    print(f"Model input shape: {model.input_shape}, output shape: {model.output_shape}")

    OUT_CHANNELS = 25
    WINDOW_SIZE = 15  # Fixed for this model

    # 4. Run prediction K times with sliding window
    print(
        f"Generating {args.k} predictions with sliding window (size={WINDOW_SIZE}) and noise std={args.noise}..."
    )
    predictions = np.zeros((N, args.k, T, OUT_CHANNELS), dtype=np.float32)

    for k in range(args.k):
        print(f"  Prediction {k + 1}/{args.k}...")

        # Apply sliding window prediction: [N, T, 62] -> [N, T, 25]
        pred_k = sliding_window_predict(
            scaled_features,
            model,
            window_size=WINDOW_SIZE,
            batch_size=32,
            noise_std=args.noise,
        )

        # 5. Apply Savitzky-Golay smoothing
        # Smoothing along time axis (axis=1)
        # Note: mode='nearest' to handle edges safely
        if args.window > 0 and args.window <= T:
            window_len = args.window if args.window % 2 == 1 else args.window + 1
            poly_order = min(args.poly, window_len - 1)
            pred_k_smoothed = savgol_filter(
                pred_k,
                window_length=window_len,
                polyorder=poly_order,
                axis=1,
                mode="nearest",
            )
        else:
            pred_k_smoothed = pred_k

        predictions[:, k, :, :] = pred_k_smoothed

    # 6. Save the resulting .npy
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    print(
        f"Saving diverse predictions to {args.output} with shape {predictions.shape}..."
    )
    np.save(args.output, predictions)
    print("Done!")


if __name__ == "__main__":
    main()

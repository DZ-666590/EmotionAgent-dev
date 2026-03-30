# PMAFRG Workflow Addendum

## Files Added

- `tools/eval_adapter/prepare_pmafrg_targets.py`
- `tools/eval_adapter/train_pmafrg_baseline.py`
- `tools/eval_adapter/pmafrg_adapter.py`

## Recommended End-to-End Flow

### 1. Prepare official targets

```bash
python tools/eval_adapter/prepare_pmafrg_targets.py \
  --dataset-root D:/your_dataset_root \
  --subset train \
  --out-dir artifacts/pmafrg_targets
```

Outputs:

- `train_emotion_targets.npy` with shape `[N, T, 25]`
- `train_3dfv_targets.npy` with shape `[N, T, 58]`

### 2. Prepare your model features

You still need to export upstream features yourself.

Recommended baseline choices in this repo:

- Emotion features:
  - Audio2Emotion postprocessed per-frame vectors
  - shape `[N, T, F_e]` or `[N, K, T, F_e]`
- Face features:
  - blendshape weights from `src/services/a2f_bridge.py`
  - shape `[N, T, F_f]` or `[N, K, T, F_f]`

If your A2F service returns one `BlendshapeFrame` per frame, the simplest face feature is:

```python
feature_t = frame.weights.astype(np.float32)
```

Then stack them to `[T, F_f]` for one sample.

### 3. Train baseline adapters

```bash
python tools/eval_adapter/train_pmafrg_baseline.py \
  --emotion-features artifacts/features/train_a2e_features.npy \
  --emotion-targets artifacts/pmafrg_targets/train_emotion_targets.npy \
  --face-features artifacts/features/train_a2f_features.npy \
  --face-targets artifacts/pmafrg_targets/train_3dfv_targets.npy \
  --out-dir artifacts/pmafrg_adapter
```

### 4. Run prediction export

```bash
python tools/eval_adapter/pmafrg_adapter.py predict \
  --emotion-model artifacts/pmafrg_adapter/emotion_adapter.npz \
  --emotion-features artifacts/features/val_a2e_features.npy \
  --face-model artifacts/pmafrg_adapter/face_adapter.npz \
  --face-features artifacts/features/val_a2f_features.npy \
  --out-dir artifacts/pmafrg_predictions
```

## Notes On Alignment

Your features and official targets must be aligned sample-by-sample and frame-by-frame.

Practical rules:

- keep the same sample ordering for features and targets
- keep the same frame rate before training
- if sequence lengths differ slightly, trim or pad consistently
- if you use diffusion and want `K > 1`, export `[N, K, T, F]`

## Notes On This Repo

`src/services/a2f_bridge.py` already gives you per-frame blendshape weights over TCP.
That makes it a reasonable first face feature source for the `58`-dim adapter.


## Added Baseline Feature Exporters

- `tools/eval_adapter/export_a2f_bridge_features.py`
  - Uses `src/services/a2f_bridge.py`
  - Exports framewise blendshape weights to `a2f_features.npy`
- `tools/eval_adapter/extract_audio_emotion_features.py`
  - Extracts lightweight framewise acoustic features from wav/mp3
  - Exports `audio_emotion_features.npy`

### Example: face features

```bash
python tools/eval_adapter/export_a2f_bridge_features.py \
  --input D:/your_audio_dir \
  --out-dir artifacts/features/train_a2f
```

This requires your A2F TCP service to be running on `127.0.0.1:9001`.

### Example: emotion features

```bash
python tools/eval_adapter/extract_audio_emotion_features.py \
  --input D:/your_audio_dir \
  --out-dir artifacts/features/train_a2e
```

### Then train

```bash
python tools/eval_adapter/train_pmafrg_baseline.py \
  --emotion-features artifacts/features/train_a2e/audio_emotion_features.npy \
  --emotion-targets artifacts/pmafrg_targets/train_emotion_targets.npy \
  --face-features artifacts/features/train_a2f/a2f_features.npy \
  --face-targets artifacts/pmafrg_targets/train_3dfv_targets.npy \
  --out-dir artifacts/pmafrg_adapter
```

## One-Shot Pipeline

You can also run the full baseline flow with one command:

```bash
python tools/eval_adapter/run_pmafrg_pipeline.py \
  --dataset-root D:/your_dataset_root \
  --train-audio D:/your_train_audio_dir \
  --val-audio D:/your_val_audio_dir \
  --out-dir artifacts/pmafrg_run
```

Notes:

- It prepares official targets into `artifacts/pmafrg_run/targets`
- It exports baseline audio-emotion features and A2F bridge features
- It trains adapters into `artifacts/pmafrg_run/adapter`
- It exports prediction files into `artifacts/pmafrg_run/predictions`
- If your A2F TCP service is not running, add `--skip-a2f` and train only the emotion adapter first

# PMAFRG Adapter Guide

## Goal

This repository's stock outputs do not match the competition evaluation tensors:

- `prediction_emotion[N, K, T, 25]`
- `prediction_3dfv[N, K, T, 58]`

The practical solution is to treat Audio2Emotion and Audio2Face as upstream
feature generators and train two lightweight adapters on the official training
set:

- Emotion adapter: upstream features -> `25`-dim listener emotion target
- Face adapter: upstream features -> `58`-dim 3D face target

## Why An Adapter Is Needed

The SDK outputs and the competition targets are different:

- Audio2Emotion sample output is `10`-dim postprocessed emotion curves
- Audio2Face uses emotion input plus audio and returns geometry / rig-related results
- The evaluation spec expects:
  - `25 = 15 AU + 2 VA + 8 EXP`
  - `58 = 52 expression + 3 pose + 3 translation`

So the task is not a field rename. It is a supervised mapping problem.

## Baseline Script

Use [pmafrg_adapter.py](/d:/Audio2Face-3D-SDK-main/Audio2Face-3D-SDK-main/tools/eval_adapter/pmafrg_adapter.py).

It provides a pure-`numpy` ridge-regression baseline with two stages:

1. `fit`: train one or both adapters
2. `predict`: export competition-style tensors

## Expected Data Shapes

### Features

The script accepts upstream features in one of these shapes:

- `[T, F]`
- `[N, T, F]`
- `[N, K, T, F]`

They are normalized internally to `[N, K, T, F]`.

### Targets

Training targets must be:

- Emotion target: `[N, T, 25]`
- 3D face target: `[N, T, 58]`

During fitting, the target is broadcast across `K`.

## Recommended Training Data Preparation

### Emotion Adapter

Prepare per-frame Audio2Emotion-aligned features such as:

- raw Audio2Emotion logits if you expose them
- current sample's `10`-dim postprocessed emotion output
- optional context features you concatenate yourself

Target uses the official training set `Emotion/*.csv` converted to:

- first `15` dims: AU
- next `2` dims: VA
- last `8` dims: EXP

### Face Adapter

Prepare per-frame Audio2Face-aligned features such as:

- blendshape weights if your pipeline already solves them
- jaw transform and eye rotation
- reduced geometry descriptors
- concatenated emotion features if that helps

Target uses the official training set `3D_FV_files/*.npy` converted to:

- first `52` dims: expression
- next `3` dims: pose
- last `3` dims: translation

## Train

Example:

```bash
python tools/eval_adapter/pmafrg_adapter.py fit \
  --emotion-features data/train_a2e_features.npy \
  --emotion-targets data/train_emotion_targets.npy \
  --face-features data/train_a2f_features.npy \
  --face-targets data/train_3dfv_targets.npy \
  --out-dir artifacts/pmafrg_adapter
```

If your arrays live inside `.npz`, pass `--emotion-features-key`, `--emotion-targets-key`,
`--face-features-key`, or `--face-targets-key`.

## Predict

Example:

```bash
python tools/eval_adapter/pmafrg_adapter.py predict \
  --emotion-model artifacts/pmafrg_adapter/emotion_adapter.npz \
  --emotion-features data/val_a2e_features.npy \
  --face-model artifacts/pmafrg_adapter/face_adapter.npz \
  --face-features data/val_a2f_features.npy \
  --out-dir artifacts/pmafrg_predictions
```

Outputs:

- `prediction_emotion.npy`
- `prediction_emotion.npz`
- `prediction_3dfv.npy`
- `prediction_3dfv.npz`

## Multiple Samples Per Input

For metrics such as `FRDiv` and `FRDvs`, `K > 1` matters.

Recommended setup:

- Regression model: usually `K = 1`
- Diffusion model: run multiple stochastic samplings to build `K > 1`

If you only have `[N, T, F]`, the script treats that as `K = 1`.

## Baseline Limitations

This is a practical baseline, not the final best model.

- It is frame-wise and linear
- It does not model long temporal dependencies
- Geometry-heavy Audio2Face outputs should ideally be reduced before fitting

Strong next steps:

- replace the ridge adapter with a temporal model
- expose richer upstream features
- train separate adapters for regression and diffusion outputs

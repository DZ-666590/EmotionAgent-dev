# PMAFRG 评测适配工具说明

## 这次已经完成的工作

为了把当前项目的音频驱动能力接到答疑说明里的“数字人面部驱动模型评测细则”，我在项目里补了一套基线工具链，目标是产出比赛需要的两类张量：

- `prediction_emotion[N, K, T, 25]`
- `prediction_3dfv[N, K, T, 58]`

这套工具链采用的是“适配器方案”：

- 上游特征
  - 音频情绪特征
  - A2F blendshape / 面部驱动特征
- 下游目标
  - 官方 `Emotion` 标注整理成 `25` 维目标
  - 官方 `3D_FV_files` 整理成 `58` 维目标
- 中间模型
  - 使用 `numpy` 实现的 ridge regression baseline adapter

## 新增文件

### `tools/eval_adapter/`

- `pmafrg_adapter.py`
  - 核心 adapter 脚本
  - 支持 `fit` 和 `predict`
- `prepare_pmafrg_targets.py`
  - 从官方数据集整理训练目标
  - 生成 `[N,T,25]` 和 `[N,T,58]`
- `train_pmafrg_baseline.py`
  - 一键训练 emotion / 3dfv 两个 adapter
- `extract_audio_emotion_features.py`
  - 从音频提取逐帧声学 baseline 特征
- `export_a2f_bridge_features.py`
  - 调用现有 `src/services/a2f_bridge.py`
  - 从 A2F TCP 服务导出逐帧 blendshape 特征
- `run_pmafrg_pipeline.py`
  - 一键串联整个流程

### 其他文档

- `docs/PMAFRG_ADAPTER_GUIDE.md`
- `docs/PMAFRG_WORKFLOW_ADDENDUM.md`

## 为什么要这样做

当前仓库默认输出和比赛评测口径不是同一个参数空间，不能直接字段映射：

- 比赛 `Emotion` 要求 `25` 维
  - `15 AU + 2 VA + 8 EXP`
- 比赛 `3D_FV` 要求 `58` 维
  - `52 expression + 3 pose + 3 translation`

而现有项目和 Audio2Face / Audio2Emotion 更像是“上游特征来源”，所以需要训练 adapter 做监督映射。

## 推荐使用方式

### 方式 1：一步一步执行

#### 1. 整理官方目标

```bash
python tools/eval_adapter/prepare_pmafrg_targets.py \
  --dataset-root D:/your_dataset_root \
  --subset train \
  --out-dir artifacts/pmafrg_targets
```

输出：

- `train_emotion_targets.npy`
- `train_3dfv_targets.npy`

#### 2. 导出音频情绪特征

```bash
python tools/eval_adapter/extract_audio_emotion_features.py \
  --input D:/your_train_audio_dir \
  --out-dir artifacts/features/train_a2e
```

输出：

- `audio_emotion_features.npy`

#### 3. 导出 A2F 特征

```bash
python tools/eval_adapter/export_a2f_bridge_features.py \
  --input D:/your_train_audio_dir \
  --out-dir artifacts/features/train_a2f
```

说明：

- 这个脚本依赖 A2F TCP 服务
- 默认连接 `127.0.0.1:9001`
- 如果 A2F 服务未启动，这一步会失败

输出：

- `a2f_features.npy`

#### 4. 训练 adapter

```bash
python tools/eval_adapter/train_pmafrg_baseline.py \
  --emotion-features artifacts/features/train_a2e/audio_emotion_features.npy \
  --emotion-targets artifacts/pmafrg_targets/train_emotion_targets.npy \
  --face-features artifacts/features/train_a2f/a2f_features.npy \
  --face-targets artifacts/pmafrg_targets/train_3dfv_targets.npy \
  --out-dir artifacts/pmafrg_adapter
```

输出：

- `emotion_adapter.npz`
- `face_adapter.npz`

#### 5. 导出预测结果

```bash
python tools/eval_adapter/pmafrg_adapter.py predict \
  --emotion-model artifacts/pmafrg_adapter/emotion_adapter.npz \
  --emotion-features artifacts/features/val_a2e/audio_emotion_features.npy \
  --face-model artifacts/pmafrg_adapter/face_adapter.npz \
  --face-features artifacts/features/val_a2f/a2f_features.npy \
  --out-dir artifacts/pmafrg_predictions
```

输出：

- `prediction_emotion.npy`
- `prediction_emotion.npz`
- `prediction_3dfv.npy`
- `prediction_3dfv.npz`

### 方式 2：一键执行整条链

```bash
python tools/eval_adapter/run_pmafrg_pipeline.py \
  --dataset-root D:/your_dataset_root \
  --train-audio D:/your_train_audio_dir \
  --val-audio D:/your_val_audio_dir \
  --out-dir artifacts/pmafrg_run
```

### 如果暂时没有 A2F 服务

可以先只训练 emotion 分支：

```bash
python tools/eval_adapter/run_pmafrg_pipeline.py \
  --dataset-root D:/your_dataset_root \
  --train-audio D:/your_train_audio_dir \
  --val-audio D:/your_val_audio_dir \
  --skip-a2f \
  --out-dir artifacts/pmafrg_run
```

## 数据格式要求

### 特征输入

工具支持以下特征形状：

- `[T, F]`
- `[N, T, F]`
- `[N, K, T, F]`

内部会统一处理成 `[N, K, T, F]`。

### 目标输入

- emotion target：`[N, T, 25]`
- 3dfv target：`[N, T, 58]`

## 当前基线的定位

这是一套“先跑通评测口径”的 baseline，不是最终最优模型。

优点：

- 依赖少
- 易调试
- 能快速验证数据链路是否打通

局限：

- adapter 是线性的
- 没有显式时序建模
- 音频情绪特征目前是 baseline 声学特征，不是强监督 A2E 模型

## 后续建议

如果后面要继续提升结果，建议按这个顺序迭代：

1. 先确认这套 baseline 能稳定产出比赛格式结果
2. 再替换 `extract_audio_emotion_features.py`，换成更强的 A2E 特征
3. 再替换 `export_a2f_bridge_features.py` 的 face 特征，加入更稳定的驱动表示
4. 最后把 ridge adapter 升级成时序模型

## 快速定位

如果只记一个入口，优先用：

```bash
python tools/eval_adapter/run_pmafrg_pipeline.py --help
```

如果只记一个说明文档，优先看：

- `tools/PMAFRG_EVAL_ADAPTER_README.md`

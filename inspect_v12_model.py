#!/usr/bin/env python3
"""Inspect V12 TCN model and scaler for prediction script requirements."""

import os
import sys
import h5py

# Model paths
MODEL_PATH = "artifacts/pmafrg_final_test/adapter/v12_tcn_model.h5"
SCALER_PATH = "artifacts/pmafrg_final_test/adapter/v12_scaler.joblib"

print("=" * 80)
print("V12 MODEL AND SCALER INSPECTION")
print("=" * 80)

# 1. Check model file
print("\n[1] MODEL FILE INSPECTION")
print("-" * 80)
if os.path.exists(MODEL_PATH):
    print(f"[OK] Model file found: {MODEL_PATH}")
    file_size = os.path.getsize(MODEL_PATH)
    print(f"  File size: {file_size / 1024 / 1024:.2f} MB")
else:
    print(f"[ERROR] Model file NOT found: {MODEL_PATH}")
    sys.exit(1)

# 2. Try loading with Keras first
print("\n[2] MODEL ARCHITECTURE")
print("-" * 80)

model_loaded_successfully = False
try:
    import tensorflow as tf
    from tensorflow import keras

    model = keras.models.load_model(MODEL_PATH)
    model_loaded_successfully = True

    print("\nModel Summary:")
    print("-" * 80)
    model.summary()

    print("\n\nModel Details:")
    print(f"  Model name: {model.name}")
    print(f"  Total layers: {len(model.layers)}")
    print(f"  Total trainable parameters: {model.count_params():,}")

    print("\n\nINPUT SPECIFICATIONS:")
    print("-" * 80)
    print(f"  Number of inputs: {len(model.inputs)}")
    for i, inp in enumerate(model.inputs):
        print(f"  Input {i}:")
        print(f"    Name: {inp.name}")
        print(f"    Shape: {inp.shape}")
        print(f"    Dtype: {inp.dtype}")

    print("\n\nOUTPUT SPECIFICATIONS:")
    print("-" * 80)
    print(f"  Number of outputs: {len(model.outputs)}")
    for i, out in enumerate(model.outputs):
        print(f"  Output {i}:")
        print(f"    Name: {out.name}")
        print(f"    Shape: {out.shape}")
        print(f"    Dtype: {out.dtype}")

    print("\n\nLAYER DETAILS:")
    print("-" * 80)
    for i, layer in enumerate(model.layers):
        print(f"  Layer {i}: {layer.__class__.__name__}")
        print(f"    Name: {layer.name}")
        if hasattr(layer, "units"):
            print(f"    Units: {layer.units}")
        if hasattr(layer, "activation"):
            print(f"    Activation: {layer.activation}")
        if hasattr(layer, "kernel_initializer"):
            print(f"    Kernel initializer: {layer.kernel_initializer}")
        if hasattr(layer, "config"):
            config = layer.get_config()
            if "filters" in config:
                print(f"    Filters: {config['filters']}")
            if "kernel_size" in config:
                print(f"    Kernel size: {config['kernel_size']}")
        print()

except Exception as e:
    print(f"[WARNING] Keras loading failed: {e}")
    print("\n[FALLBACK] Reading HDF5 structure directly...")
    print("-" * 80)

    try:
        with h5py.File(MODEL_PATH, "r") as f:
            print("\nHDF5 Structure:")

            def print_structure(name, obj):
                indent = "  " * (name.count("/"))
                if isinstance(obj, h5py.Dataset):
                    print(f"{indent}{name}: shape={obj.shape}, dtype={obj.dtype}")
                else:
                    print(f"{indent}{name}/")

            f.visititems(print_structure)

            # Try to extract model config
            if "model_config" in f.attrs:
                import json

                config = json.loads(f.attrs["model_config"])
                print(f"\n\nModel Config: {json.dumps(config, indent=2)[:500]}...")

    except Exception as e2:
        print(f"[ERROR] HDF5 fallback also failed: {e2}")

# 3. Check and inspect scaler
print("\n\n[3] SCALER FILE INSPECTION")
print("-" * 80)
if os.path.exists(SCALER_PATH):
    print(f"[OK] Scaler file found: {SCALER_PATH}")
    file_size = os.path.getsize(SCALER_PATH)
    print(f"  File size: {file_size / 1024:.2f} KB")
else:
    print(f"[ERROR] Scaler file NOT found: {SCALER_PATH}")
    sys.exit(1)

print("\n[4] SCALER TYPE AND CONFIGURATION")
print("-" * 80)
try:
    import joblib

    scaler = joblib.load(SCALER_PATH)
    print(f"[OK] Scaler loaded successfully")
    print(f"  Scaler type: {type(scaler).__name__}")
    print(f"  Scaler module: {type(scaler).__module__}")

    # Check if it's a scikit-learn scaler
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

    if isinstance(scaler, (StandardScaler, MinMaxScaler, RobustScaler)):
        print(f"  [OK] Standard scikit-learn scaler detected")

        # Print scaler attributes
        print(f"\n  Scaler attributes:")
        if hasattr(scaler, "mean_"):
            print(f"    mean_: {scaler.mean_}")
        if hasattr(scaler, "var_"):
            print(f"    var_: {scaler.var_}")
        if hasattr(scaler, "scale_"):
            print(f"    scale_: {scaler.scale_}")
        if hasattr(scaler, "data_min_"):
            print(f"    data_min_: {scaler.data_min_}")
        if hasattr(scaler, "data_max_"):
            print(f"    data_max_: {scaler.data_max_}")
        if hasattr(scaler, "n_features_in_"):
            print(f"    n_features_in_: {scaler.n_features_in_}")
    else:
        print(f"  [WARNING] Not a standard scikit-learn scaler, but joblib-compatible")

except Exception as e:
    print(f"[ERROR] Error loading scaler: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
print("INSPECTION COMPLETE")
print("=" * 80)

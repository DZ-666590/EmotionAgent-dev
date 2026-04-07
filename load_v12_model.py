from tensorflow import keras
import os

model_path = "artifacts/pmafrg_final_test/adapter/v12_tcn_model.h5"
if os.path.exists(model_path):
    try:
        model = keras.models.load_model(model_path, compile=False)
    except Exception as e:
        print(f"Error loading: {e}")
        import tensorflow.keras as keras_legacy

        model = keras_legacy.models.load_model(model_path, compile=False)

    print("=" * 80)
    print("V12 TCN MODEL SUMMARY")
    print("=" * 80)
    model.summary()
    print("\n" + "=" * 80)
    print("INPUT SHAPE:", model.input_shape)
    print("OUTPUT SHAPE:", model.output_shape)
    print("=" * 80)
else:
    print(f"Model not found at {model_path}")

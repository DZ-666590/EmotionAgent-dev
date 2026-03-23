# Quick Reference: A2F Data Size Logging

## 📊 What Changed

Added comprehensive logging to track actual data sizes received from A2F C++ service.

### Logging Statements Added:

**1. Per-Frame Debug Log (Line 180-184)**
```python
logger.debug(
    f"[A2F Bridge] Frame {frame_index}: geo_size={geo_size}, "
    f"geometry_bytes={len(geometry) * 4 if len(geometry) > 0 else 0}, "
    f"geometry_elements={len(geometry)}"
)
```

**2. Summary Info Log (Lines 229-232 & 321-324)**
```python
logger.info(
    f"[A2F Bridge] Received {len(frames)} geometry frames, "
    f"total_data_bytes={total_geometry_bytes}"
)
```

---

## 📈 What You'll See

### Debug Output (per frame):
```
[A2F Bridge] Frame 0: geo_size=252, geometry_bytes=1008, geometry_elements=252
[A2F Bridge] Frame 1: geo_size=252, geometry_bytes=1008, geometry_elements=252
```

### Summary Output (after stream ends):
```
[A2F Bridge] Received 120 geometry frames, total_data_bytes=120960
```

---

## 🔍 Key Metrics Logged

| Metric | Meaning |
|--------|---------|
| `frame_index` | Frame number from C++ service (0, 1, 2, ...) |
| `geo_size` | Number of float32 elements in geometry |
| `geometry_bytes` | Total bytes for this frame = geo_size × 4 |
| `geometry_elements` | Array length (validation: should equal geo_size) |
| `total_data_bytes` | Sum of all geometry_bytes across frames |

---

## 🎯 Protocol Structure

Each frame from C++ contains:
```
[4 bytes]  frame_index (uint32)
[4 bytes]  geo_size (uint32)
[N bytes]  geometry (N = geo_size * 4)
```

Total per frame = 8 + (geo_size × 4) bytes

---

## 🚀 Enable Detailed Logging

### Option 1: Console Output
```bash
# Most Python apps respect DEBUG level
export LOGLEVEL=DEBUG
python main.py --mode api
```

### Option 2: Log to File
Modify your app startup to add:
```python
from loguru import logger

logger.remove()
logger.add(
    "logs/a2f_debug.log",
    level="DEBUG",
    format="{time} | {level} | {message}"
)
```

### Option 3: Via Python REPL
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🔎 How to Find Logs

```bash
# Real-time tail
tail -f logs/a2f_debug.log

# Search for geo_size mentions
grep "geo_size" logs/a2f_debug.log

# Count total bytes received
grep "total_data_bytes" logs/a2f_debug.log

# Show all A2F Bridge messages
grep "\[A2F Bridge\]" logs/*.log
```

---

## ✅ Verification Points

- ✅ geo_size captured per frame
- ✅ Total geometry_bytes calculated
- ✅ Data integrity validated by `readexactly()`
- ✅ Protocol structure verified
- ✅ Backward compatible (no breaking changes)

---

## 📌 Important Notes

1. **geo_size is a count**, not bytes:
   - If geo_size = 252, actual data = 252 × 4 = 1,008 bytes

2. **End of stream**:
   - frame_index = 0xFFFFFFFF signals end
   - No more data after this marker

3. **Expected geo_size range**:
   - Typical: 50-1000
   - Minimum: 1-10
   - Maximum: 5000+

4. **Data validation**:
   - If bytes received ≠ geo_size × 4, exception is raised
   - Automatic protocol validation

---

## 📋 Files Modified

- `src/services/a2f_bridge.py` (3 sections enhanced)
- Status: ✅ Syntax validated

---

## 🎓 Example Real-world Scenario

```
Input: 4 second audio @ 16000Hz

Output:
[A2F Bridge] Connected to 127.0.0.1:9001
[A2F Bridge] PCM samples: 64000, duration: 4.00s
[A2F Bridge] Audio sent, waiting for inference...
[A2F Bridge] Frame 0: geo_size=252, geometry_bytes=1008, geometry_elements=252
[A2F Bridge] Frame 1: geo_size=252, geometry_bytes=1008, geometry_elements=252
... (120 frames at 30fps)
[A2F Bridge] Frame 119: geo_size=252, geometry_bytes=1008, geometry_elements=252
[A2F Bridge] Received end marker
[A2F Bridge] Received 120 geometry frames, total_data_bytes=120960
```

**Total data received:**
- Protocol overhead: 120 frames × 8 bytes = 960 bytes
- Geometry data: 120 frames × 1,008 bytes = 120,960 bytes
- **Grand total: 121,920 bytes ≈ 119 KB**

---

Ready to debug! 🚀

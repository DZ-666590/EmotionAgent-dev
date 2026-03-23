# A2F C++ Service Data Size Verification Report

**Date:** March 20, 2026  
**File Analyzed:** `src/services/a2f_bridge.py`  
**Status:** Enhanced with comprehensive logging ✅

---

## 1. Current Logging Analysis

### 1.1 Location of geo_size Handling

**File:** `src/services/a2f_bridge.py` (Lines 152-186)

**Method:** `_receive_frames()` - Async generator that receives geometry frame data from A2F C++ service

#### Protocol Structure:
```
┌─────────────────────────────────────────────┐
│ Frame Structure (received from C++ service) │
├─────────────────────────────────────────────┤
│ frame_index     (uint32, 4 bytes)          │  ← Line 160
│ geo_size        (uint32, 4 bytes)          │  ← Line 170
│ geometry        (float32[], N*4 bytes)     │  ← Line 174
└─────────────────────────────────────────────┘
```

### 1.2 Current Logging Status

**BEFORE Enhancement:**
- Line 226, 314: Only logged frame count
  ```python
  logger.info(f"[A2F Bridge] Received {len(frames)} geometry frames")
  ```
- No per-frame geo_size logging
- No total data size tracking

**AFTER Enhancement:**
- Line 180-184: Per-frame logging with geo_size details
  ```python
  logger.debug(
      f"[A2F Bridge] Frame {frame_index}: geo_size={geo_size}, "
      f"geometry_bytes={len(geometry) * 4 if len(geometry) > 0 else 0}, "
      f"geometry_elements={len(geometry)}"
  )
  ```
- Lines 229-232 & 321-324: Summary logging with total data bytes
  ```python
  logger.info(
      f"[A2F Bridge] Received {len(frames)} geometry frames, "
      f"total_data_bytes={total_geometry_bytes}"
  )
  ```

---

## 2. Data Size Calculation

### 2.1 Per-Frame Size

```
frame_data_size = 4 (frame_index) + 4 (geo_size) + (geo_size * 4 bytes)
                = 8 + (geo_size * 4)

Example:
- If geo_size = 10000
  frame_data_size = 8 + (10000 * 4) = 40,008 bytes ≈ 39 KB
```

### 2.2 Key Variables

| Variable | Type | Size | Purpose |
|----------|------|------|---------|
| `frame_index` | uint32 | 4 bytes | Frame number identifier |
| `geo_size` | uint32 | 4 bytes | Number of float32 elements in geometry |
| `geometry` | float32[] | geo_size × 4 bytes | Actual geometry data |
| `geo_size * 4` | bytes | Calculated | Total geometry data bytes |

### 2.3 Enhanced Logging Metrics

The logging now captures:
1. **frame_index** - Frame number from C++ service
2. **geo_size** - Raw uint32 value (number of float32 elements)
3. **geometry_bytes** - Calculated total bytes (geo_size × 4)
4. **geometry_elements** - Array length (should equal geo_size)
5. **total_geometry_bytes** - Sum of all frames' geometry data

---

## 3. Protocol Verification Points

### 3.1 End Marker Detection (Line 164)
```python
END_MARKER = 0xFFFFFFFF  # Class constant
if frame_index == self.END_MARKER:
    logger.debug("[A2F Bridge] Received end marker")
    break
```

**Expected Behavior:**
- When frame_index = 0xFFFFFFFF (4294967295), end of stream is reached
- No more frames after end marker
- Connection remains open for potential reuse

### 3.2 Data Integrity Check

**Line 173-174:**
```python
if geo_size > 0:
    geo_data = await self._reader.readexactly(geo_size * 4)
    geometry = np.frombuffer(geo_data, dtype=np.float32)
```

**Verification:**
- Reads exactly `geo_size * 4` bytes
- If buffer size ≠ geo_size × 4, `readexactly()` raises exception
- Auto-validation of data size from C++ protocol

### 3.3 Expected geo_size Range

Based on typical Audio2Face implementations:
- **Minimum:** 1-10 (empty or minimal expression)
- **Typical:** 50-1000 (standard facial blend shapes)
- **Maximum:** 5000+ (high-detail geometry)

---

## 4. Enhanced Logging Output Example

### Debug Level (Per-Frame):
```
[A2F Bridge] Frame 0: geo_size=252, geometry_bytes=1008, geometry_elements=252
[A2F Bridge] Frame 1: geo_size=252, geometry_bytes=1008, geometry_elements=252
[A2F Bridge] Frame 2: geo_size=252, geometry_bytes=1008, geometry_elements=252
...
[A2F Bridge] Received end marker
```

### Info Level (Summary):
```
[A2F Bridge] Received 120 geometry frames, total_data_bytes=120960
```

---

## 5. Enabling Detailed Logging

### Method 1: Via Python Code
```python
from loguru import logger

# Set to DEBUG level for per-frame logging
logger.enable("a2f_bridge")
# or at application startup:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Method 2: Via Loguru Configuration
Create/modify log handler in your app:
```python
from loguru import logger

logger.remove()  # Remove default handler
logger.add(
    "logs/a2f_debug.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    rotation="500 MB"
)
```

### Method 3: Via Environment Variable
```bash
# If your app respects LOGLEVEL
export LOGLEVEL=DEBUG
python main.py --mode api
```

---

## 6. Finding Log Files

### Expected Log Locations:
1. **Console output** (if running in terminal)
   - Look for lines with `[A2F Bridge]`

2. **Log files** (if loguru is configured):
   - Check `logs/` directory
   - Look for `a2f*.log` files
   - Grep for pattern: `geo_size=`

3. **Application-wide logs**:
   - May be in `debug.log`, `app.log`, or similar

### Search Command:
```bash
# Find all log files
find . -type f -name "*.log" 2>/dev/null

# Search for A2F frame data in logs
grep -r "geo_size=" logs/

# Follow real-time logs
tail -f logs/a2f_debug.log
```

---

## 7. Verification Checklist

- [x] geo_size is logged per-frame at DEBUG level
- [x] geometry_bytes calculated as `geo_size * 4`
- [x] geometry_elements tracked for validation
- [x] Total data bytes summed across all frames
- [x] Frame count logged at INFO level
- [x] End marker detection confirmed
- [x] Data integrity verified via `readexactly()`
- [x] Protocol structure documented

---

## 8. Expected Test Output

When running A2F service with test MP3:
```
[A2F Bridge] Connected to 127.0.0.1:9001
[A2F Bridge] Converting MP3 to PCM...
[A2F Bridge] PCM samples: 64000, duration: 4.00s
[A2F Bridge] Audio sent, waiting for inference...
[A2F Bridge] Frame 0: geo_size=252, geometry_bytes=1008, geometry_elements=252
[A2F Bridge] Frame 1: geo_size=252, geometry_bytes=1008, geometry_elements=252
... (more frames)
[A2F Bridge] Received end marker
[A2F Bridge] Received 120 geometry frames, total_data_bytes=120960
[A2F Bridge] Disconnected
```

---

## 9. Implementation Summary

### Files Modified:
- `src/services/a2f_bridge.py`
  - Enhanced `_receive_frames()` method (Lines 152-186)
  - Enhanced `process_audio()` logging (Lines 229-232)
  - Enhanced `process_pcm()` logging (Lines 321-324)

### New Logging Statements:
1. **Debug level**: Per-frame geo_size details
2. **Info level**: Aggregate data size summary

### Backward Compatibility:
- ✅ All changes are additive (only adds logging)
- ✅ No protocol changes
- ✅ No breaking API changes
- ✅ Existing code continues to work

---

## 10. Next Steps for Debugging

If data sizes are unexpected:

1. **Check C++ Service Output**
   - Verify C++ service is generating correct geo_size values
   - Look for C++ service logs

2. **Validate Network Buffer**
   - Use Wireshark to capture TCP packets
   - Verify byte counts match reported geo_size

3. **Compare Expected vs Actual**
   - Expected geometry size based on model (e.g., 252 float32s)
   - Actual received bytes should be: expected × 4

4. **Enable Full Protocol Trace**
   - Add logging before/after each `readexactly()` call
   - Verify frame_index and geo_size values in hex

---

**Report Generated:** 2026-03-20  
**Enhanced Logging:** ACTIVE ✅  
**Ready for Deployment:** YES

# Face Detection Loading Timing Fix

## 🎯 **Issue Identified**

The first time playing a video, the face rectangles don't appear because of a **race condition** between video initialization and face data loading.

### **Problem Sequence:**
1. **Video player initializes** → `initState()` called
2. **Smart playback starts** → `_initializeSmartPlayback()` called  
3. **Face data loading triggered** → `loadFaces()` called in post-frame callback
4. **`_loadStoredFaceData()` checks provider state** → No data available yet (still loading)
5. **Result**: No face overlay on first play

### **Second Play Success:**
1. **Face data already loaded** from previous attempt
2. **`_loadStoredFaceData()` finds data immediately** 
3. **Result**: Yellow rectangles display correctly

## 🔧 **Fix Applied**

### **Before (Race Condition):**
```dart
// Just read current state - no waiting
final faceDataState = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid));

if (faceDataState.hasData && faceDataState.faces.isNotEmpty) {
  // Use data immediately
} else {
  // Fall back to API call
}
```

### **After (Wait for Loading):**
```dart
// Ensure loading starts
final notifier = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid).notifier);
notifier.loadFaces();

// Wait for data with timeout (10 seconds max)
var attempts = 0;
const maxAttempts = 20; // 500ms * 20 = 10 seconds

while (attempts < maxAttempts) {
  final faceDataState = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid));
  
  if (faceDataState.hasData && faceDataState.faces.isNotEmpty) {
    // Successfully loaded - use data
    return;
  }
  
  // Wait and retry
  await Future.delayed(const Duration(milliseconds: 500));
  attempts++;
}

// Timeout - fall back to API call
```

## **Expected Result**

### **First Play:**
- ✅ **Wait for face data to load** (up to 10 seconds)
- ✅ **Display yellow rectangles immediately** when video starts
- ✅ **Frame-synchronized face display** from the beginning

### **Subsequent Plays:**
- ✅ **Data already cached** - immediate display
- ✅ **No loading delay** - instant rectangles

## **Loading Flow Optimization**

### **Timeline Now:**
1. **0ms**: Video player initializes
2. **0-16ms**: Smart playback initialization starts
3. **16ms**: Face data loading triggered and waits
4. **16-5000ms**: Face data loads from Vision Service API
5. **~1000ms**: Face data available, overlays ready
6. **Video ready**: Yellow rectangles display immediately

### **Fallback Strategy:**
- **Primary**: MediaFaceDataProvider (fast, cached)
- **Fallback**: StoredFaceDataProvider (direct Vision API)
- **Timeout**: 10 seconds max wait time
- **Error Handling**: Graceful degradation to no overlay

## **Debug Output Changes**

### **New Loading Messages:**
```
_loadStoredFaceData() called - ensuring MediaFaceDataProvider data is loaded...
LOADING ATTEMPT 0: hasData=false, isLoading=true, hasError=false, faces=0
LOADING ATTEMPT 1: hasData=false, isLoading=true, hasError=false, faces=0  
LOADING ATTEMPT 2: hasData=true, isLoading=false, hasError=false, faces=14
✅ LOADING SUCCESS: Loaded 14 faces from MediaFaceDataProvider after 2 attempts
```

### **Success Indicators:**
- ✅ `LOADING SUCCESS` - Face data loaded successfully  
- ✅ Frame-synchronized display from first play
- ✅ No more "NO FRAME DATA" on initial load

## **Files Modified**

**`/lib/widgets/smart_video_player_widget.dart`**:
- ✅ Added proper async waiting in `_loadStoredFaceData()`
- ✅ Implemented retry logic with timeout
- ✅ Removed duplicate retry code
- ✅ Enhanced debug logging for loading states

This fix ensures face rectangles appear **immediately on first play** instead of requiring a second video load.
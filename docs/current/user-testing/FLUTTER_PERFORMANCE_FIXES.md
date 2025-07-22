# Flutter Performance Optimization - IDE Crash Prevention

## 🚨 **Issue**: Flutter App Crashing IDE

**Root Causes:**
1. High memory usage (524MB+ for Dart process)
2. 302 code analysis issues causing compilation overhead
3. Network connectivity problems
4. Font loading errors
5. Excessive debug logging in production code

## ✅ **Immediate Solutions**

### **1. Memory Optimization**

```bash
# Clean Flutter cache to reduce memory usage
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend
flutter clean
flutter pub get

# Clear build cache
rm -rf build/
rm -rf .dart_tool/build/
```

### **2. Remove Debug Print Statements**

Critical: 24+ print statements are causing memory leaks in production code:

Files to clean:
- `lib/core/config/app_config.dart:37`
- `lib/services/media_api_client.dart` (15+ print statements)
- `lib/widgets/responsive_media_gallery.dart`
- `lib/widgets/video_player_widget.dart`

**Fix: Replace print() with proper logging:**

```dart
// Instead of: print('Debug message');
// Use: logger.debug('Debug message');

import 'package:logger/logger.dart';
final logger = Logger();
```

### **3. Fix Network Connectivity**

**Issue**: XMLHttpRequest errors during login

**Solution**: Add network timeout and retry logic:

```dart
// In dio configuration
final dio = Dio(BaseOptions(
  connectTimeout: Duration(seconds: 30),
  receiveTimeout: Duration(seconds: 30),
  sendTimeout: Duration(seconds: 30),
));
```

### **4. Fix Font Loading Issues**

**Issue**: Roboto fonts failing to load

**Solution**: 
1. Font paths are correct in pubspec.yaml
2. Issue is likely web-specific caching
3. Clear browser cache and restart

### **5. Performance Improvements**

**Critical Code Issues to Fix:**

```dart
// Fix deprecated API usage
// Replace: .withOpacity(0.5)
// With: .withValues(alpha: 0.5)

// Add const constructors where possible
const Icon(Icons.home)  // Instead of Icon(Icons.home)

// Remove unused imports and variables
// Fix: 15+ unused imports identified
```

## 🎯 **Recommended Actions (Priority Order)**

### **High Priority (Do Now)**
1. **Clean Flutter Project**: `flutter clean && flutter pub get`
2. **Remove Print Statements**: Replace with proper logging
3. **Restart IDE**: Close VS Code completely and restart
4. **Clear Chrome Cache**: Delete browser cache for localhost:3000

### **Medium Priority (Next)**
1. **Fix Analysis Issues**: Address the 302 analysis warnings
2. **Update Dependencies**: Check for Flutter/package updates
3. **Optimize Memory**: Use `const` constructors where possible

### **Low Priority (Later)**
1. **Update Deprecated APIs**: Replace `withOpacity` with `withValues`
2. **Remove Dead Code**: Clean up unused methods and imports

## 🔧 **Quick Fix Commands**

```bash
# 1. Clean and reset Flutter
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend
flutter clean
flutter pub get
flutter pub run build_runner clean

# 2. Restart Flutter app with memory optimization
flutter run -d chrome --web-port 3000 --release

# 3. Monitor memory usage
ps aux | grep -E "(flutter|dart)" | grep -v grep
```

## 🚀 **Prevention Strategies**

1. **Regular Cleanup**: Run `flutter clean` weekly
2. **Code Quality**: Fix analysis issues immediately  
3. **Memory Monitoring**: Check process memory regularly
4. **Proper Logging**: Use logger instead of print statements
5. **Cache Management**: Clear browser cache regularly

## 📊 **Memory Benchmarks**

**Before Fixes:**
- Dart process: 524MB (HIGH)
- Chrome renderer: 346MB
- Total Flutter memory: ~870MB

**Target After Fixes:**
- Dart process: <200MB 
- Chrome renderer: <200MB
- Total Flutter memory: <400MB

## ⚠️ **Warning Signs to Watch**

- Dart process >300MB memory
- IDE becoming unresponsive
- Frequent "hot reload" failures
- Chrome renderer crashes
- Analysis server timeouts

**When you see these signs**: Restart Flutter immediately and run cleanup commands.

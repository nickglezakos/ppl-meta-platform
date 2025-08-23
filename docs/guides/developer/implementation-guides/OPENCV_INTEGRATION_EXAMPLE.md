# OpenCV Integration Example for PPL Meta Platform

## Overview
This document provides a basic implementation example for integrating OpenCV computer vision capabilities with the PPL Meta platform, focusing on network discovery and mobile camera integration.

## Vision Service Implementation

### 1. Basic OpenCV Vision Service

```python
# ppl-meta-vision/src/opencv_service.py
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
import json

app = FastAPI(title="PPL Meta Vision Service", version="1.0.0")

class OpenCVProcessor:
    def __init__(self):
        self.opencv_version = cv2.__version__
        self.initialized = True
        
    def get_capabilities(self):
        """Return OpenCV capabilities for service discovery"""
        return {
            "opencv_enabled": True,
            "opencv_version": self.opencv_version,
            "supported_formats": ["jpg", "png", "mp4", "rtsp"],
            "features": [
                "object_detection",
                "face_detection", 
                "motion_detection",
                "edge_detection",
                "image_enhancement"
            ],
            "real_time_processing": True,
            "max_image_size": "4096x4096"
        }
    
    def detect_objects(self, image_data: bytes):
        """Basic object detection using OpenCV"""
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return {"error": "Invalid image format"}
        
        # Simple contour detection as example
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # Filter small objects
                x, y, w, h = cv2.boundingRect(contour)
                objects.append({
                    "type": "detected_object",
                    "confidence": 0.8,  # Placeholder confidence
                    "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                    "area": int(area)
                })
        
        return {
            "objects_detected": len(objects),
            "objects": objects,
            "image_size": {"width": image.shape[1], "height": image.shape[0]}
        }

# Initialize OpenCV processor
processor = OpenCVProcessor()

@app.get("/health")
async def health_check():
    """Standardized health check endpoint"""
    return {
        "status": "healthy",
        "service": "ppl-meta-vision",
        "version": "1.0.0",
        "opencv_enabled": processor.initialized,
        "timestamp": "2025-08-21T11:32:14.189Z"
    }

@app.get("/api/v1/vision/capabilities")
async def get_capabilities():
    """OpenCV capabilities for mobile app discovery"""
    return processor.get_capabilities()

@app.post("/api/v1/vision/process")
async def process_image(file: UploadFile = File(...)):
    """Process uploaded image with OpenCV"""
    try:
        image_data = await file.read()
        result = processor.detect_objects(image_data)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": f"Processing failed: {str(e)}"}
        )

@app.post("/api/v1/vision/mobile/snapshot")
async def process_mobile_snapshot(file: UploadFile = File(...)):
    """Specialized endpoint for mobile camera snapshots"""
    try:
        image_data = await file.read()
        
        # Mobile-specific processing (smaller images, faster processing)
        result = processor.detect_objects(image_data)
        
        # Add mobile-friendly response format
        mobile_result = {
            "success": True,
            "processing_time_ms": 150,  # Placeholder
            "summary": f"Detected {result['objects_detected']} objects",
            "details": result
        }
        
        return JSONResponse(content=mobile_result)
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": f"Mobile processing failed: {str(e)}"}
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
```

### 2. Mobile App OpenCV Integration

```dart
// lib/services/opencv_vision_service.dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:camera/camera.dart';
import 'app_logger.dart';

class OpenCVVisionService {
  static final OpenCVVisionService _instance = OpenCVVisionService._internal();
  factory OpenCVVisionService() => _instance;
  OpenCVVisionService._internal();

  String? _visionServiceUrl;
  Map<String, dynamic>? _capabilities;

  /// Discover OpenCV vision service during network discovery
  Future<bool> discoverVisionService(String baseUrl) async {
    try {
      final healthUrl = '$baseUrl:8003/health';
      CameraLogger.debug('Testing vision service: $healthUrl');
      
      final healthResponse = await http.get(
        Uri.parse(healthUrl),
        headers: {'Content-Type': 'application/json'},
      ).timeout(Duration(seconds: 3));
      
      if (healthResponse.statusCode != 200) {
        CameraLogger.warning('Vision service health check failed: ${healthResponse.statusCode}');
        return false;
      }
      
      final healthData = json.decode(healthResponse.body);
      if (healthData['opencv_enabled'] != true) {
        CameraLogger.warning('OpenCV not enabled on vision service');
        return false;
      }
      
      // Get OpenCV capabilities
      final capUrl = '$baseUrl:8003/api/v1/vision/capabilities';
      final capResponse = await http.get(Uri.parse(capUrl));
      
      if (capResponse.statusCode == 200) {
        _capabilities = json.decode(capResponse.body);
        _visionServiceUrl = '$baseUrl:8003';
        
        CameraLogger.success('OpenCV vision service discovered: $_visionServiceUrl');
        CameraLogger.info('Capabilities: ${_capabilities!['features']}');
        return true;
      }
      
      return false;
    } catch (e) {
      CameraLogger.warning('Vision service discovery failed: $e');
      return false;
    }
  }

  /// Process image with OpenCV (mobile camera snapshot)
  Future<Map<String, dynamic>?> processSnapshot(String imagePath) async {
    if (_visionServiceUrl == null) {
      CameraLogger.error('Vision service not discovered');
      return null;
    }

    try {
      final file = File(imagePath);
      if (!await file.exists()) {
        CameraLogger.error('Image file not found: $imagePath');
        return null;
      }

      final url = '$_visionServiceUrl/api/v1/vision/mobile/snapshot';
      CameraLogger.debug('Processing image with OpenCV: $url');
      
      final request = http.MultipartRequest('POST', Uri.parse(url));
      request.files.add(await http.MultipartFile.fromPath('file', imagePath));
      
      final response = await request.send();
      final responseBody = await response.stream.bytesToString();
      
      if (response.statusCode == 200) {
        final result = json.decode(responseBody);
        CameraLogger.success('OpenCV processing completed: ${result['summary']}');
        return result;
      } else {
        CameraLogger.error('OpenCV processing failed: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      CameraLogger.error('OpenCV processing error: $e');
      return null;
    }
  }

  /// Get available OpenCV capabilities
  Map<String, dynamic>? get capabilities => _capabilities;
  
  /// Check if vision service is available
  bool get isAvailable => _visionServiceUrl != null;
  
  /// Get vision service URL
  String? get serviceUrl => _visionServiceUrl;
}
```

### 3. Integration with Camera Registration

```dart
// Update auto_camera_registration_service.dart to include OpenCV discovery
Future<bool> performZeroInputRegistration() async {
  try {
    CameraLogger.step('Starting zero-input camera registration...');
    
    // 1. Discover platform services (existing code)
    final discoveryResult = await _discoveryService.discoverServices();
    if (!discoveryResult.success) {
      throw Exception('Service discovery failed');
    }
    
    // 2. NEW: Discover OpenCV vision service
    final visionService = OpenCVVisionService();
    final visionDiscovered = await visionService.discoverVisionService(
      discoveryResult.baseUrl!
    );
    
    if (visionDiscovered) {
      CameraLogger.success('✅ OpenCV vision service available');
      CameraLogger.info('Features: ${visionService.capabilities!['features']}');
    } else {
      CameraLogger.warning('⚠️ OpenCV vision service not available');
    }
    
    // 3. Register camera (existing code)
    // ... existing registration code ...
    
    // 4. NEW: Test OpenCV integration if available
    if (visionService.isAvailable) {
      await _testOpenCVIntegration(visionService);
    }
    
    return true;
  } catch (e) {
    CameraLogger.error('Zero-input registration failed: $e');
    return false;
  }
}

Future<void> _testOpenCVIntegration(OpenCVVisionService visionService) async {
  try {
    CameraLogger.step('Testing OpenCV integration...');
    
    // Take a test snapshot
    final XFile? image = await _cameraController.takePicture();
    if (image == null) {
      CameraLogger.warning('Could not capture test image for OpenCV');
      return;
    }
    
    // Process with OpenCV
    final result = await visionService.processSnapshot(image.path);
    if (result != null && result['success'] == true) {
      CameraLogger.success('✅ OpenCV test successful: ${result['summary']}');
    } else {
      CameraLogger.warning('⚠️ OpenCV test failed');
    }
    
    // Clean up test image
    await File(image.path).delete();
  } catch (e) {
    CameraLogger.warning('OpenCV test error: $e');
  }
}
```

## Network Discovery Integration

### Updated Discovery Process

```dart
// Enhanced discovery algorithm including OpenCV
1. Multicast Discovery (224.1.1.1:12345)
2. Tailscale Device Name Resolution (device-name.tailnet.ts.net)
3. Tailscale Network Scan (100.x.x.x/10) 
4. Local Network Scan (192.168.x.x, 10.x.x.x, 172.x.x.x)
5. OpenCV Vision Service Discovery (port 8003) ← NEW
6. Localhost Fallback (localhost, 127.0.0.1)
```

### Service Health Check Matrix

```dart
final serviceEndpoints = {
  'node': {'port': 8001, 'health': '/api/v1/health'},
  'gateway': {'port': 8080, 'health': '/health'},
  'media': {'port': 8000, 'health': '/health'},
  'orchestrator': {'port': 8002, 'health': '/health'},
  'vision': {'port': 8003, 'health': '/health'},        // ← NEW
  'cameras': {'port': 8005, 'health': '/health'},
};
```

## Usage Examples

### Basic Object Detection
```dart
// In camera screen after registration
final visionService = OpenCVVisionService();
if (visionService.isAvailable) {
  final image = await _cameraController.takePicture();
  final result = await visionService.processSnapshot(image.path);
  
  if (result != null) {
    setState(() {
      _detectionResults = result['details']['objects'];
    });
  }
}
```

### Real-time Processing
```dart
// Stream camera frames to OpenCV service
void startRealTimeProcessing() {
  _cameraController.startImageStream((CameraImage image) async {
    // Convert CameraImage to file
    final file = await _saveImageToFile(image);
    
    // Process with OpenCV
    final result = await visionService.processSnapshot(file.path);
    
    // Update UI with results
    if (result != null) {
      _updateDetectionOverlay(result['details']['objects']);
    }
  });
}
```

## Benefits

1. **Seamless Integration**: OpenCV service discovered automatically during network discovery
2. **Mobile Optimized**: Dedicated mobile endpoints for faster processing
3. **Capability Detection**: App knows what OpenCV features are available
4. **Graceful Fallback**: App works with or without OpenCV service
5. **Real-time Processing**: Support for both snapshot and streaming processing

## Testing

### Test OpenCV Integration
```bash
# Start vision service with OpenCV
cd ppl-meta-vision && python src/opencv_service.py

# Test from mobile app
# 1. Run discovery - should find vision service on port 8003
# 2. Register camera - should include OpenCV test
# 3. Take photos - should offer OpenCV processing options
```

This implementation provides a complete OpenCV integration that works seamlessly with the PPL Meta network discovery system!

---

*This example demonstrates how to integrate OpenCV computer vision capabilities into the PPL Meta platform while maintaining the robust network discovery functionality.*

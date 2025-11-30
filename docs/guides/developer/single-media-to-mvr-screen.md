# Single Media to MVR Screen - Developer Guide

**Document Version**: 1.0  
**Date**: November 29, 2025  
**Feature**: Vision Processing from Multi-Select  
**Location**: `http://localhost:3000/#/collections`  
**Services**: Media Service (port 8000), VMeta Service (port 8008)

---

## Table of Contents

1. [Overview](#overview)
2. [User Flow](#user-flow)
3. [Architecture & Integration](#architecture--integration)
4. [Implementation Steps](#implementation-steps)
5. [UI Components](#ui-components)
6. [State Management](#state-management)
7. [API Integration](#api-integration)
8. [Progress & Feedback](#progress--feedback)
9. [Error Handling](#error-handling)
10. [Testing Strategy](#testing-strategy)
11. [Performance Considerations](#performance-considerations)

---

## Overview

This feature extends the existing **Multi-Select Media** functionality by adding a new "Vision" action that processes selected media through the VMeta service's Single-Media MVR Processing endpoint. Users can select multiple photos/videos and trigger facial recognition processing in bulk, receiving immediate feedback on the results.

### Feature Goals

1. **Seamless Integration**: Add Vision processing to existing multi-select workflow
2. **Bulk Processing**: Process multiple media items efficiently
3. **Real-Time Feedback**: Show progress and results to users
4. **Error Resilience**: Handle partial failures gracefully
5. **Performance**: Process media quickly with visual feedback

### Key Components

- **Multi-Select UI**: Existing media selection interface
- **Vision Action**: New action in the actions menu
- **Progress Dialog**: Real-time processing feedback
- **Results Summary**: MVR people count and success metrics
- **VMeta Integration**: Single-Media MVR endpoint client

---

## User Flow

### Complete User Journey

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: Enable Multi-Select Mode                        │
├─────────────────────────────────────────────────────────┤
│  User taps multi-select icon in navigation bar          │
│  → Selection checkboxes appear on media cards           │
│  → Action button becomes visible (disabled)             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Step 2: Select Media Items                              │
├─────────────────────────────────────────────────────────┤
│  User taps on media cards to select them                │
│  → Selected media show checkmarks and highlights        │
│  → Selection counter shows "X items selected"           │
│  → Action button becomes enabled                        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Step 3: Open Actions Menu                               │
├─────────────────────────────────────────────────────────┤
│  User taps floating action button (bottom-right)        │
│  → Actions menu opens as bottom sheet/modal             │
│  → Available actions displayed:                         │
│    • Move to Collection                                 │
│    • Copy to Collection                                 │
│    • Add Tags                                           │
│    • Download                                           │
│    • Vision  ← NEW ACTION                               │
│    • Delete                                             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Step 4: Select Vision Action                            │
├─────────────────────────────────────────────────────────┤
│  User taps "Vision" action                              │
│  → Actions menu closes                                  │
│  → Confirmation dialog appears (optional)               │
│  → Processing begins                                    │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Step 5: Processing with Progress                        │
├─────────────────────────────────────────────────────────┤
│  Progress dialog displays:                              │
│  • "Processing media with Vision AI..."                 │
│  • Progress bar (0% → 100%)                             │
│  • Current media being processed                        │
│  • Processing stats (X/Y complete)                      │
│  • Estimated time remaining                             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Step 6: Results Summary                                 │
├─────────────────────────────────────────────────────────┤
│  Success dialog displays:                               │
│  • ✓ "Vision Processing Complete"                       │
│  • Total MVR people created: 15                         │
│  • Successfully processed: 8/10 media                   │
│  • Failed: 2 media (with reasons)                       │
│  • [View Details] [Dismiss]                             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Step 7: Return to Collections                           │
├─────────────────────────────────────────────────────────┤
│  User taps "Dismiss"                                    │
│  → Multi-select mode disabled                           │
│  → Selection cleared                                    │
│  → Collections view refreshed                           │
│  → Notification banner (optional): "15 people detected" │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture & Integration

### System Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                    Flutter Frontend                         │
│                  (http://localhost:3000)                    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           Collections Page                            │ │
│  │                                                       │ │
│  │  ┌─────────────────────────────────────────────┐    │ │
│  │  │  Multi-Select State                          │    │ │
│  │  │  - isMultiSelectMode: true                   │    │ │
│  │  │  - selectedMediaIds: [id1, id2, id3]        │    │ │
│  │  └─────────────────────────────────────────────┘    │ │
│  │                                                       │ │
│  │  ┌─────────────────────────────────────────────┐    │ │
│  │  │  Actions Menu                                │    │ │
│  │  │  - Move to Collection                        │    │ │
│  │  │  - Copy to Collection                        │    │ │
│  │  │  - Add Tags                                  │    │ │
│  │  │  - Download                                  │    │ │
│  │  │  - Vision ← NEW                              │    │ │
│  │  │  - Delete                                    │    │ │
│  │  └─────────────────────────────────────────────┘    │ │
│  │                                                       │ │
│  └──────────────────────────────────────────────────────┘ │
│                              │                              │
│                              ↓                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         VisionProcessingService                       │ │
│  │  - processSelectedMedia(mediaIds)                    │ │
│  │  - showProgressDialog()                              │ │
│  │  - showResultsDialog()                               │ │
│  └──────────────────────────────────────────────────────┘ │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               │
                               ↓ HTTP POST
                ┌──────────────────────────────┐
                │   VMeta Service (port 8008)  │
                │                              │
                │  POST /api/v1/mvr-people/   │
                │       process-media          │
                │                              │
                │  Request:                    │
                │  {                           │
                │    media_uuids: [...]       │
                │    processing_options: {...} │
                │  }                           │
                │                              │
                │  Response:                   │
                │  {                           │
                │    success: true,           │
                │    mvr_people_count: 15,    │
                │    results: [...]           │
                │  }                           │
                └──────────────────────────────┘
                               │
                               ↓
                ┌──────────────────────────────┐
                │  Vision Service (port 8003)  │
                │  - Face Detection V2         │
                │  - Person Objects            │
                └──────────────────────────────┘
                               │
                               ↓
                ┌──────────────────────────────┐
                │    Media Service (port 8000) │
                │  - Media metadata            │
                │  - File paths                │
                └──────────────────────────────┘
```

### Integration Points

1. **Multi-Select State** → Vision Action Trigger
2. **Vision Action** → VMeta Service API Call
3. **VMeta Service** → Vision Service (Face Detection V2)
4. **VMeta Service** → Media Service (Metadata)
5. **VMeta Response** → Results Dialog
6. **Results Dialog** → Collections Refresh

---

## Implementation Steps

### Step 1: Add Vision Action to Actions Menu

**File**: `ppl-meta-frontend/lib/screens/collections/widgets/actions_menu.dart`

```dart
class ActionsMenu extends StatelessWidget {
  final List<String> selectedMediaIds;
  final VoidCallback onActionComplete;
  
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Actions',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              IconButton(
                icon: Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          
          Divider(),
          
          // Existing actions
          ListTile(
            leading: Icon(Icons.drive_file_move),
            title: Text('Move to Collection'),
            onTap: () => _handleMoveToCollection(context),
          ),
          
          ListTile(
            leading: Icon(Icons.content_copy),
            title: Text('Copy to Collection'),
            onTap: () => _handleCopyToCollection(context),
          ),
          
          ListTile(
            leading: Icon(Icons.label),
            title: Text('Add Tags'),
            onTap: () => _handleAddTags(context),
          ),
          
          ListTile(
            leading: Icon(Icons.download),
            title: Text('Download'),
            onTap: () => _handleDownload(context),
          ),
          
          // NEW: Vision Action
          ListTile(
            leading: Icon(
              Icons.visibility,
              color: Theme.of(context).primaryColor,
            ),
            title: Text(
              'Vision',
              style: TextStyle(
                color: Theme.of(context).primaryColor,
                fontWeight: FontWeight.w500,
              ),
            ),
            subtitle: Text('Process with AI face recognition'),
            onTap: () => _handleVisionProcessing(context),
          ),
          
          Divider(),
          
          ListTile(
            leading: Icon(Icons.delete, color: Colors.red),
            title: Text('Delete', style: TextStyle(color: Colors.red)),
            onTap: () => _handleDelete(context),
          ),
        ],
      ),
    );
  }
  
  Future<void> _handleVisionProcessing(BuildContext context) async {
    // Close actions menu
    Navigator.pop(context);
    
    // Show confirmation dialog (optional)
    final confirmed = await _showVisionConfirmationDialog(context);
    
    if (confirmed == true) {
      // Trigger vision processing
      await _processWithVision(context);
    }
  }
  
  Future<bool?> _showVisionConfirmationDialog(BuildContext context) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(Icons.visibility, color: Theme.of(context).primaryColor),
            SizedBox(width: 8),
            Text('Vision Processing'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Process ${selectedMediaIds.length} media items with AI face recognition?',
              style: TextStyle(fontSize: 16),
            ),
            SizedBox(height: 16),
            Text(
              'This will:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 8),
            Text('• Detect faces in selected media'),
            Text('• Create MVR people records'),
            Text('• Extract demographics (age, gender)'),
            Text('• Generate face embeddings'),
            SizedBox(height: 16),
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.blue),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Processing may take a few seconds per media item',
                      style: TextStyle(fontSize: 12, color: Colors.blue.shade900),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('Cancel'),
          ),
          ElevatedButton.icon(
            onPressed: () => Navigator.pop(context, true),
            icon: Icon(Icons.play_arrow),
            label: Text('Start Processing'),
          ),
        ],
      ),
    );
  }
  
  Future<void> _processWithVision(BuildContext context) async {
    final visionService = Provider.of<VisionProcessingService>(
      context,
      listen: false,
    );
    
    try {
      // Show progress dialog
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => VisionProcessingDialog(
          mediaIds: selectedMediaIds,
          visionService: visionService,
        ),
      );
      
      // Execute vision processing
      final result = await visionService.processSelectedMedia(
        mediaIds: selectedMediaIds,
      );
      
      // Close progress dialog
      Navigator.pop(context);
      
      // Show results dialog
      await _showResultsDialog(context, result);
      
      // Call completion callback
      onActionComplete();
      
    } catch (e) {
      // Close progress dialog if open
      Navigator.pop(context);
      
      // Show error dialog
      _showErrorDialog(context, e.toString());
    }
  }
  
  Future<void> _showResultsDialog(
    BuildContext context,
    VisionProcessingResult result,
  ) async {
    return showDialog(
      context: context,
      builder: (context) => VisionResultsDialog(result: result),
    );
  }
}
```

---

### Step 2: Create Vision Processing Service

**File**: `ppl-meta-frontend/lib/services/vision_processing_service.dart`

```dart
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class VisionProcessingService extends ChangeNotifier {
  final Dio _dio;
  final String _vmetaBaseUrl = 'http://localhost:8008';
  
  // Processing state
  bool _isProcessing = false;
  int _currentProgress = 0;
  int _totalItems = 0;
  String? _currentMediaId;
  
  // Getters
  bool get isProcessing => _isProcessing;
  int get currentProgress => _currentProgress;
  int get totalItems => _totalItems;
  String? get currentMediaId => _currentMediaId;
  double get progressPercent => 
      _totalItems > 0 ? _currentProgress / _totalItems : 0.0;
  
  VisionProcessingService({Dio? dio}) 
      : _dio = dio ?? Dio();
  
  /// Process selected media with Vision AI
  Future<VisionProcessingResult> processSelectedMedia({
    required List<String> mediaIds,
    double? similarityThreshold,
    double? minFaceQuality,
    bool includeDemographics = true,
    bool includeRouteData = true,
  }) async {
    _isProcessing = true;
    _currentProgress = 0;
    _totalItems = mediaIds.length;
    notifyListeners();
    
    try {
      // Get auth token
      final token = await _getAuthToken();
      
      // Call VMeta Single-Media MVR endpoint
      final response = await _dio.post(
        '$_vmetaBaseUrl/api/v1/mvr-people/process-media',
        options: Options(
          headers: {
            'Authorization': 'Bearer $token',
            'Content-Type': 'application/json',
          },
        ),
        data: {
          'media_uuids': mediaIds,
          'processing_options': {
            'similarity_threshold': similarityThreshold ?? 0.8,
            'min_face_quality': minFaceQuality ?? 0.70,
            'include_demographics': includeDemographics,
            'include_route_data': includeRouteData,
          },
        },
      );
      
      // Parse response
      final data = response.data;
      
      // Update progress to 100%
      _currentProgress = _totalItems;
      notifyListeners();
      
      // Create result object
      final result = VisionProcessingResult.fromJson(data);
      
      return result;
      
    } on DioException catch (e) {
      throw VisionProcessingException(
        message: _parseDioError(e),
        originalError: e,
      );
    } catch (e) {
      throw VisionProcessingException(
        message: 'Unexpected error: ${e.toString()}',
        originalError: e,
      );
    } finally {
      _isProcessing = false;
      _currentProgress = 0;
      _totalItems = 0;
      _currentMediaId = null;
      notifyListeners();
    }
  }
  
  String _parseDioError(DioException e) {
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return 'Request timed out. Please try again.';
    } else if (e.type == DioExceptionType.connectionError) {
      return 'Unable to connect to Vision service. Check your connection.';
    } else if (e.response != null) {
      final statusCode = e.response!.statusCode;
      if (statusCode == 401) {
        return 'Authentication failed. Please log in again.';
      } else if (statusCode == 403) {
        return 'Permission denied. You do not have access to this feature.';
      } else if (statusCode == 400) {
        final message = e.response!.data['message'] ?? 'Invalid request';
        return message;
      } else if (statusCode! >= 500) {
        return 'Server error. Please try again later.';
      }
    }
    return 'An unexpected error occurred: ${e.message}';
  }
  
  Future<String> _getAuthToken() async {
    // TODO: Implement actual token retrieval from auth service
    // For now, return a placeholder
    return 'your_jwt_token_here';
  }
}

/// Result of vision processing operation
class VisionProcessingResult {
  final bool success;
  final int processedMedia;
  final int failedMedia;
  final int mvrPeopleCount;
  final List<MediaProcessingResult> results;
  final Map<String, dynamic> aggregateStatistics;
  
  VisionProcessingResult({
    required this.success,
    required this.processedMedia,
    required this.failedMedia,
    required this.mvrPeopleCount,
    required this.results,
    required this.aggregateStatistics,
  });
  
  factory VisionProcessingResult.fromJson(Map<String, dynamic> json) {
    return VisionProcessingResult(
      success: json['success'] ?? false,
      processedMedia: json['processed_media'] ?? 0,
      failedMedia: json['failed_media'] ?? 0,
      mvrPeopleCount: json['mvr_people_count'] ?? 0,
      results: (json['results'] as List?)
          ?.map((r) => MediaProcessingResult.fromJson(r))
          .toList() ?? [],
      aggregateStatistics: json['aggregate_statistics'] ?? {},
    );
  }
}

/// Result for individual media item
class MediaProcessingResult {
  final String mediaUuid;
  final String status;
  final int mvrPeopleCount;
  final int totalFacesDetected;
  final String? error;
  
  MediaProcessingResult({
    required this.mediaUuid,
    required this.status,
    required this.mvrPeopleCount,
    required this.totalFacesDetected,
    this.error,
  });
  
  factory MediaProcessingResult.fromJson(Map<String, dynamic> json) {
    return MediaProcessingResult(
      mediaUuid: json['media_uuid'] ?? '',
      status: json['status'] ?? 'unknown',
      mvrPeopleCount: json['mvr_people_count'] ?? 0,
      totalFacesDetected: json['total_faces_detected'] ?? 0,
      error: json['error'],
    );
  }
  
  bool get isSuccess => status == 'completed';
  bool get isFailed => status == 'failed';
}

/// Exception thrown during vision processing
class VisionProcessingException implements Exception {
  final String message;
  final dynamic originalError;
  
  VisionProcessingException({
    required this.message,
    this.originalError,
  });
  
  @override
  String toString() => message;
}
```

---

### Step 3: Create Vision Processing Dialog

**File**: `ppl-meta-frontend/lib/screens/collections/widgets/vision_processing_dialog.dart`

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class VisionProcessingDialog extends StatefulWidget {
  final List<String> mediaIds;
  final VisionProcessingService visionService;
  
  const VisionProcessingDialog({
    Key? key,
    required this.mediaIds,
    required this.visionService,
  }) : super(key: key);
  
  @override
  State<VisionProcessingDialog> createState() => _VisionProcessingDialogState();
}

class _VisionProcessingDialogState extends State<VisionProcessingDialog> {
  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: widget.visionService,
      child: Consumer<VisionProcessingService>(
        builder: (context, service, child) {
          return WillPopScope(
            // Prevent closing during processing
            onWillPop: () async => !service.isProcessing,
            child: AlertDialog(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              content: Container(
                width: 300,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Icon
                    Icon(
                      Icons.visibility,
                      size: 48,
                      color: Theme.of(context).primaryColor,
                    ),
                    
                    SizedBox(height: 16),
                    
                    // Title
                    Text(
                      'Processing with Vision AI',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    
                    SizedBox(height: 24),
                    
                    // Progress bar
                    LinearProgressIndicator(
                      value: service.progressPercent,
                      backgroundColor: Colors.grey[200],
                      valueColor: AlwaysStoppedAnimation<Color>(
                        Theme.of(context).primaryColor,
                      ),
                    ),
                    
                    SizedBox(height: 12),
                    
                    // Progress text
                    Text(
                      '${service.currentProgress} / ${service.totalItems} media processed',
                      style: TextStyle(fontSize: 14, color: Colors.grey[600]),
                    ),
                    
                    SizedBox(height: 8),
                    
                    // Percentage
                    Text(
                      '${(service.progressPercent * 100).toStringAsFixed(0)}%',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).primaryColor,
                      ),
                    ),
                    
                    SizedBox(height: 16),
                    
                    // Status messages
                    Container(
                      padding: EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  valueColor: AlwaysStoppedAnimation<Color>(
                                    Colors.blue,
                                  ),
                                ),
                              ),
                              SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'Detecting faces and creating MVR people...',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.blue.shade900,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          SizedBox(height: 8),
                          Text(
                            '• Face Detection V2 processing',
                            style: TextStyle(fontSize: 11, color: Colors.grey[700]),
                          ),
                          Text(
                            '• Generating embeddings',
                            style: TextStyle(fontSize: 11, color: Colors.grey[700]),
                          ),
                          Text(
                            '• Extracting demographics',
                            style: TextStyle(fontSize: 11, color: Colors.grey[700]),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
```

---

### Step 4: Create Vision Results Dialog

**File**: `ppl-meta-frontend/lib/screens/collections/widgets/vision_results_dialog.dart`

```dart
import 'package:flutter/material.dart';

class VisionResultsDialog extends StatelessWidget {
  final VisionProcessingResult result;
  
  const VisionResultsDialog({
    Key? key,
    required this.result,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      title: Row(
        children: [
          Icon(
            result.success ? Icons.check_circle : Icons.error,
            color: result.success ? Colors.green : Colors.red,
            size: 32,
          ),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              result.success 
                  ? 'Vision Processing Complete' 
                  : 'Processing Completed with Errors',
              style: TextStyle(fontSize: 20),
            ),
          ),
        ],
      ),
      content: Container(
        width: double.maxFinite,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Summary card
              _buildSummaryCard(context),
              
              SizedBox(height: 16),
              
              // MVR People count (highlighted)
              _buildMVRCountCard(context),
              
              SizedBox(height: 16),
              
              // Processing breakdown
              _buildProcessingBreakdown(context),
              
              // Failures section (if any)
              if (result.failedMedia > 0) ...[
                SizedBox(height: 16),
                _buildFailuresSection(context),
              ],
              
              SizedBox(height: 16),
              
              // Additional statistics
              _buildStatisticsSection(context),
            ],
          ),
        ),
      ),
      actions: [
        if (result.failedMedia > 0)
          TextButton(
            onPressed: () => _showDetailedFailures(context),
            child: Text('View Failed Items'),
          ),
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('Dismiss'),
        ),
        ElevatedButton(
          onPressed: () {
            Navigator.pop(context);
            // Navigate to MVR people view (optional)
            // Navigator.pushNamed(context, '/mvr-people');
          },
          child: Text('View MVR People'),
        ),
      ],
    );
  }
  
  Widget _buildSummaryCard(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Theme.of(context).primaryColor.withOpacity(0.1),
            Theme.of(context).primaryColor.withOpacity(0.05),
          ],
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Theme.of(context).primaryColor.withOpacity(0.3),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStatItem(
            context,
            icon: Icons.photo_library,
            label: 'Processed',
            value: '${result.processedMedia}',
            color: Colors.green,
          ),
          _buildStatItem(
            context,
            icon: Icons.error_outline,
            label: 'Failed',
            value: '${result.failedMedia}',
            color: Colors.red,
          ),
          _buildStatItem(
            context,
            icon: Icons.face,
            label: 'Total Faces',
            value: _getTotalFaces().toString(),
            color: Colors.blue,
          ),
        ],
      ),
    );
  }
  
  Widget _buildMVRCountCard(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Colors.green.shade400,
            Colors.green.shade600,
          ],
        ),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.green.withOpacity(0.3),
            blurRadius: 8,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.people, color: Colors.white, size: 48),
          SizedBox(width: 16),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'MVR People Created',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
              Text(
                '${result.mvrPeopleCount}',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 48,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildProcessingBreakdown(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Processing Breakdown',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        SizedBox(height: 8),
        ...result.results.map((r) => _buildMediaResultTile(context, r)),
      ],
    );
  }
  
  Widget _buildMediaResultTile(BuildContext context, MediaProcessingResult media) {
    return Card(
      margin: EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        leading: Icon(
          media.isSuccess ? Icons.check_circle : Icons.error,
          color: media.isSuccess ? Colors.green : Colors.red,
        ),
        title: Text(
          'Media ${media.mediaUuid.substring(0, 8)}...',
          style: TextStyle(fontSize: 14),
        ),
        subtitle: Text(
          media.isSuccess
              ? '${media.mvrPeopleCount} MVR people, ${media.totalFacesDetected} faces'
              : media.error ?? 'Processing failed',
          style: TextStyle(fontSize: 12),
        ),
        trailing: Icon(
          media.isSuccess ? Icons.face : Icons.warning,
          color: Colors.grey,
        ),
      ),
    );
  }
  
  Widget _buildFailuresSection(BuildContext context) {
    final failedResults = result.results.where((r) => r.isFailed).toList();
    
    return Container(
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning, color: Colors.red, size: 20),
              SizedBox(width: 8),
              Text(
                'Failed Items (${failedResults.length})',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.red.shade900,
                ),
              ),
            ],
          ),
          SizedBox(height: 8),
          ...failedResults.take(3).map((r) => Padding(
            padding: EdgeInsets.only(bottom: 4),
            child: Text(
              '• ${r.mediaUuid.substring(0, 8)}: ${r.error ?? "Unknown error"}',
              style: TextStyle(fontSize: 12, color: Colors.red.shade900),
            ),
          )),
          if (failedResults.length > 3)
            Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text(
                'and ${failedResults.length - 3} more...',
                style: TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: Colors.grey,
                ),
              ),
            ),
        ],
      ),
    );
  }
  
  Widget _buildStatisticsSection(BuildContext context) {
    final stats = result.aggregateStatistics;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Statistics',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        SizedBox(height: 8),
        Container(
          padding: EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.grey.shade100,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            children: [
              _buildStatRow('Total Individuals', '${stats['total_individuals_detected'] ?? 0}'),
              _buildStatRow('Avg Processing Time', '${stats['avg_processing_ms']?.toStringAsFixed(0) ?? 0} ms'),
              _buildStatRow('Total Processing Time', '${stats['total_processing_ms']?.toStringAsFixed(0) ?? 0} ms'),
            ],
          ),
        ),
      ],
    );
  }
  
  Widget _buildStatItem(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(fontSize: 12, color: Colors.grey[600]),
        ),
      ],
    );
  }
  
  Widget _buildStatRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(fontSize: 13)),
          Text(
            value,
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }
  
  int _getTotalFaces() {
    return result.results.fold<int>(
      0,
      (sum, r) => sum + r.totalFacesDetected,
    );
  }
  
  void _showDetailedFailures(BuildContext context) {
    final failedResults = result.results.where((r) => r.isFailed).toList();
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Failed Items Detail'),
        content: Container(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: failedResults.length,
            itemBuilder: (context, index) {
              final item = failedResults[index];
              return ListTile(
                leading: Icon(Icons.error, color: Colors.red),
                title: Text(item.mediaUuid),
                subtitle: Text(item.error ?? 'Unknown error'),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Close'),
          ),
        ],
      ),
    );
  }
}
```

---

## State Management

### Vision Processing State Flow

```dart
// Initial State
{
  isMultiSelectMode: false,
  selectedMediaIds: [],
  isProcessing: false,
  processingProgress: 0,
  processingResults: null
}

// Step 1: Enable Multi-Select
{
  isMultiSelectMode: true,
  selectedMediaIds: [],
  ...
}

// Step 2: Select Media
{
  isMultiSelectMode: true,
  selectedMediaIds: ['id1', 'id2', 'id3'],
  ...
}

// Step 3: Start Vision Processing
{
  ...
  isProcessing: true,
  processingProgress: 0
}

// Step 4: Processing Updates
{
  ...
  isProcessing: true,
  processingProgress: 0.33  // 1/3 complete
}

// Step 5: Processing Complete
{
  ...
  isProcessing: false,
  processingProgress: 1.0,
  processingResults: VisionProcessingResult(...)
}

// Step 6: Reset State
{
  isMultiSelectMode: false,
  selectedMediaIds: [],
  isProcessing: false,
  processingProgress: 0,
  processingResults: null
}
```

---

## API Integration

### Request Format

```dart
// POST /api/v1/mvr-people/process-media
{
  "media_uuids": [
    "5c00d13d-1a64-4be7-885b-477f441e2ab9",
    "b663af24-512f-46e3-8281-3e7d591da13a",
    "media-uuid-3"
  ],
  "processing_options": {
    "similarity_threshold": 0.8,
    "min_face_quality": 0.70,
    "include_demographics": true,
    "include_route_data": true
  }
}
```

### Response Format

```dart
{
  "success": true,
  "processed_media": 3,
  "failed_media": 0,
  "mvr_people_count": 15,
  "results": [
    {
      "media_uuid": "5c00d13d-1a64-4be7-885b-477f441e2ab9",
      "status": "completed",
      "mvr_people": [
        {
          "mvr_people_uuid": "4979b5b9-3d76-462f-9aa4-fa89b94fe835",
          "individual_uuids": ["11017f6e-8589-41d1-b8be-82fef0ab0ce8"],
          "demographics": {
            "gender": "male",
            "gender_confidence": 0.9992887377738953,
            "age_min": 30,
            "age_max": 40,
            "age_confidence": 0.85
          },
          "is_isolated": true,
          "source_media_uuid": "5c00d13d-1a64-4be7-885b-477f441e2ab9"
        }
      ],
      "total_faces_detected": 5,
      "mvr_people_count": 2,
      "processing_time_ms": 4085
    }
  ],
  "aggregate_statistics": {
    "total_mvr_people_created": 15,
    "total_individuals_detected": 20,
    "avg_processing_ms": 3542.5
  }
}
```

---

## Progress & Feedback

### Progress Tracking Strategies

#### 1. Simple Progress (Current Implementation)
- Show total progress bar (0-100%)
- Display current/total counts
- No per-media granularity

#### 2. Enhanced Progress (Future)
- Real-time updates via WebSocket/SSE
- Per-media progress tracking
- Estimated time remaining
- Current operation status

#### 3. Batch Processing (Future)
- Process media in batches of 10
- Show batch progress
- Allow cancellation between batches

### Visual Feedback Components

**Loading States**:
- Progress bar (determinate)
- Percentage indicator
- Item count (X/Y complete)
- Status messages
- Animated icons

**Success States**:
- Checkmark icon (green)
- MVR count (large, highlighted)
- Processing breakdown
- Statistics summary
- Call-to-action buttons

**Error States**:
- Error icon (red)
- Error message
- Failed items list
- Retry button
- Support information

---

## Error Handling

### Error Categories

#### 1. Network Errors
- Connection timeout
- Connection refused
- DNS resolution failure

**Handling**:
```dart
try {
  await visionService.processSelectedMedia(...);
} on DioException catch (e) {
  if (e.type == DioExceptionType.connectionTimeout) {
    _showError('Request timed out. Please try again.');
  } else if (e.type == DioExceptionType.connectionError) {
    _showError('Unable to connect to server. Check your connection.');
  }
}
```

#### 2. Authentication Errors
- Invalid token
- Expired token
- Missing permissions

**Handling**:
```dart
if (statusCode == 401) {
  // Token expired - refresh and retry
  await _refreshToken();
  return _retry(operation);
} else if (statusCode == 403) {
  _showError('Permission denied. Contact administrator.');
}
```

#### 3. Validation Errors
- Invalid media UUIDs
- Empty selection
- Too many media items

**Handling**:
```dart
if (selectedMediaIds.isEmpty) {
  _showError('Please select at least one media item.');
  return;
}
if (selectedMediaIds.length > 50) {
  _showError('Maximum 50 media items can be processed at once.');
  return;
}
```

#### 4. Processing Errors
- Face detection failure
- No faces found
- ML model errors

**Handling**:
```dart
// Partial success - some media failed
if (result.failedMedia > 0) {
  _showWarning(
    'Processed ${result.processedMedia} items. '
    '${result.failedMedia} items failed.'
  );
}
```

### Error Recovery Strategies

**1. Automatic Retry**:
```dart
Future<T> _retryOperation<T>(
  Future<T> Function() operation,
  {int maxRetries = 3}
) async {
  int attempt = 0;
  while (attempt < maxRetries) {
    try {
      return await operation();
    } catch (e) {
      attempt++;
      if (attempt >= maxRetries) rethrow;
      await Future.delayed(Duration(seconds: pow(2, attempt).toInt()));
    }
  }
  throw Exception('Max retries exceeded');
}
```

**2. Token Refresh**:
```dart
if (statusCode == 401) {
  await _authService.refreshToken();
  return _retryOperation(() => processSelectedMedia(...));
}
```

**3. Partial Retry**:
```dart
// Retry only failed media items
if (result.failedMedia > 0) {
  final failedIds = result.results
      .where((r) => r.isFailed)
      .map((r) => r.mediaUuid)
      .toList();
  
  final confirmed = await _showRetryDialog(failedIds.length);
  if (confirmed) {
    await processSelectedMedia(mediaIds: failedIds);
  }
}
```

---

## Testing Strategy

### Unit Tests

**1. VisionProcessingService Tests**:
```dart
group('VisionProcessingService', () {
  test('processes media successfully', () async {
    final service = VisionProcessingService(dio: mockDio);
    
    when(mockDio.post(any, ...))
        .thenAnswer((_) async => Response(data: mockSuccessResponse));
    
    final result = await service.processSelectedMedia(
      mediaIds: ['id1', 'id2'],
    );
    
    expect(result.success, true);
    expect(result.mvrPeopleCount, 15);
  });
  
  test('handles network errors', () async {
    when(mockDio.post(any, ...))
        .thenThrow(DioException(type: DioExceptionType.connectionTimeout));
    
    expect(
      () => service.processSelectedMedia(mediaIds: ['id1']),
      throwsA(isA<VisionProcessingException>()),
    );
  });
});
```

**2. Dialog Widget Tests**:
```dart
testWidgets('VisionResultsDialog shows correct MVR count', (tester) async {
  final result = VisionProcessingResult(
    success: true,
    mvrPeopleCount: 25,
    ...
  );
  
  await tester.pumpWidget(
    MaterialApp(
      home: VisionResultsDialog(result: result),
    ),
  );
  
  expect(find.text('25'), findsOneWidget);
  expect(find.text('MVR People Created'), findsOneWidget);
});
```

### Integration Tests

**End-to-End Flow**:
```dart
testWidgets('Complete vision processing flow', (tester) async {
  // 1. Enable multi-select
  await tester.tap(find.byIcon(Icons.check_box_outline_blank));
  await tester.pumpAndSettle();
  
  // 2. Select media
  await tester.tap(find.byType(MediaCard).first);
  await tester.tap(find.byType(MediaCard).at(1));
  await tester.pumpAndSettle();
  
  // 3. Open actions menu
  await tester.tap(find.byType(FloatingActionButton));
  await tester.pumpAndSettle();
  
  // 4. Tap Vision action
  await tester.tap(find.text('Vision'));
  await tester.pumpAndSettle();
  
  // 5. Confirm
  await tester.tap(find.text('Start Processing'));
  await tester.pumpAndSettle();
  
  // 6. Wait for processing (mock)
  await tester.pump(Duration(seconds: 2));
  
  // 7. Verify results dialog
  expect(find.text('Vision Processing Complete'), findsOneWidget);
  expect(find.text('MVR People Created'), findsOneWidget);
});
```

### Manual Testing Checklist

- [ ] Multi-select 1 photo, process with Vision
- [ ] Multi-select 5 videos, process with Vision
- [ ] Multi-select 10 mixed media, process with Vision
- [ ] Test with no faces detected (empty result)
- [ ] Test with partial failures (some media fail)
- [ ] Test with network timeout
- [ ] Test with authentication error
- [ ] Test progress dialog appearance
- [ ] Test results dialog appearance
- [ ] Verify MVR count is correct
- [ ] Check error messages are clear
- [ ] Test dismiss button functionality
- [ ] Test "View MVR People" button navigation

---

## Performance Considerations

### Optimization Strategies

**1. Batch Processing**:
```dart
// Process in batches of 10
const batchSize = 10;
for (int i = 0; i < mediaIds.length; i += batchSize) {
  final batch = mediaIds.sublist(
    i,
    min(i + batchSize, mediaIds.length),
  );
  await processSelectedMedia(mediaIds: batch);
}
```

**2. Parallel Processing (Backend)**:
```python
# Backend processes media in parallel
async def process_media_parallel(media_ids: List[str]):
    tasks = [process_single_media(id) for id in media_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**3. Progress Streaming**:
```dart
// Use Server-Sent Events for real-time progress
Stream<ProgressUpdate> streamProcessingProgress(List<String> mediaIds) {
  final controller = StreamController<ProgressUpdate>();
  
  _dio.get(
    '/api/v1/mvr-people/process-media/stream',
    options: Options(responseType: ResponseType.stream),
  ).then((response) {
    response.data.stream.listen((data) {
      final update = ProgressUpdate.fromJson(data);
      controller.add(update);
    });
  });
  
  return controller.stream;
}
```

### Performance Targets

| Metric | Target | Acceptable |
|--------|--------|------------|
| Dialog open time | < 100ms | < 300ms |
| API call initiation | < 200ms | < 500ms |
| Processing 1 media | < 5s | < 10s |
| Processing 10 media | < 15s | < 30s |
| Results display | < 200ms | < 500ms |
| UI responsiveness | 60 FPS | 30 FPS |

---

## Document Status

**Status**: Complete  
**Last Updated**: November 29, 2025  
**Author**: PPL Meta Development Team  
**Related Documents**:
- Multi-Select Media to Action Guide
- Single-Media MVR Processing Guide
- VMeta API Endpoints Documentation

---

## Summary

The **Single Media to MVR Screen** feature integrates Vision AI processing into the multi-select workflow:

✅ **Seamless Integration**: Adds "Vision" action to existing multi-select menu  
✅ **Bulk Processing**: Process multiple photos/videos with one tap  
✅ **Real-Time Feedback**: Progress dialog with live updates  
✅ **Clear Results**: Summary showing MVR people count and statistics  
✅ **Error Handling**: Partial failure support with retry options  
✅ **Performance**: Optimized for processing multiple media efficiently  

**User Benefits**:
- Quick face recognition for photo galleries
- Batch processing of video collections
- Immediate feedback on detection results
- Easy access to MVR people data
- Efficient workflow for media organization

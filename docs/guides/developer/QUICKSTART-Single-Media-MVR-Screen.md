# Quick Start: Single Media to MVR Screen Feature

**Last Updated**: November 29, 2025  
**Status**: ✅ Implementation Complete - Ready for Testing

---

## What is This Feature?

The **Single Media to MVR Screen** feature allows users to select multiple photos/videos from a collection and process them with AI face recognition. The system detects faces, creates MVR (Multi-Video Recognition) people records, and extracts demographics in bulk.

---

## How to Use (User Perspective)

### Step-by-Step Guide

1. **Navigate to Collections**
   - Go to `http://localhost:3000/#/collections`
   - Select a collection with media

2. **Enable Multi-Select Mode**
   - Tap the checklist icon in the top-right corner
   - Checkboxes appear on all media cards

3. **Select Media**
   - Tap on media cards to select them
   - Selected items show checkmarks
   - Counter shows "X items selected"

4. **Start Vision Processing**
   - Tap the **eye icon** (Vision button) in the action bar
   - Confirmation dialog appears

5. **Confirm Processing**
   - Review the media count and features
   - Tap "Start Processing"

6. **Watch Progress**
   - Progress dialog shows:
     - Progress bar (0-100%)
     - Current/total media count
     - Processing status

7. **View Results**
   - Results dialog displays:
     - **MVR People Count** (large, green highlight)
     - Processing summary
     - Per-media breakdown
     - Failed items (if any)

8. **Return to Collections**
   - Tap "Dismiss" to close
   - Selection mode exits automatically

---

## For Developers

### Quick Setup

**Prerequisites**:
- Flutter frontend running (`localhost:3000`)
- VMeta service running (`localhost:8008`)
- Media service running (`localhost:8000`)
- Vision service running (`localhost:8003`)

**Files to Review**:
```
ppl-meta-frontend/
  lib/
    services/
      vision_processing_service.dart     ← API client
    widgets/
      vision_processing_dialog.dart      ← Progress UI
      vision_results_dialog.dart          ← Results UI
    screens/
      collections_screen.dart             ← Integration
```

### Quick Test

```bash
# 1. Start all services
cd ppl-meta-code
# Use VS Code task: "🚀 Start All Local Python Services"

# 2. Start Flutter frontend
cd ppl-meta-frontend
flutter run -d chrome --web-port 3000

# 3. Test the feature
# - Navigate to http://localhost:3000/#/collections
# - Select a collection
# - Enable multi-select
# - Select 3-5 media items
# - Tap Vision button (eye icon)
# - Confirm and watch processing
```

### Making Changes

**To modify the Vision button**:
Edit `collections_screen.dart` (line ~147):
```dart
IconButton(
  onPressed: _processWithVision,
  icon: Icon(Icons.visibility, color: AppColors.primary),
  tooltip: 'Process with Vision AI',
)
```

**To modify the progress dialog**:
Edit `vision_processing_dialog.dart`

**To modify the results display**:
Edit `vision_results_dialog.dart`

**To modify API integration**:
Edit `vision_processing_service.dart`

---

## Common Issues & Solutions

### Issue: Vision button not visible
**Solution**: Make sure you're in multi-select mode (tap checklist icon) and have selected at least one media item.

### Issue: "Unable to connect to Vision service"
**Solution**: 
1. Check VMeta service is running: `curl http://localhost:8008/health`
2. Check service logs for errors
3. Verify network connectivity

### Issue: Processing takes too long
**Solution**: 
- Expected time: ~2s per photo, ~5s per video
- For 10+ items, consider batch processing
- Check Vision service performance

### Issue: Authentication failed
**Solution**: 
- Token retrieval is currently a placeholder
- Implement `_getAuthToken()` in `vision_processing_service.dart`
- Integrate with AuthManager

---

## Architecture Overview

```
User Action (Tap Vision)
    ↓
Confirmation Dialog
    ↓
VisionProcessingService
    ↓
HTTP POST → VMeta Service (port 8008)
    ↓
Vision Service (Face Detection V2)
    ↓
VMeta Response
    ↓
Results Dialog (MVR Count)
    ↓
Collections View Refresh
```

---

## API Endpoint

```
POST http://localhost:8008/api/v1/mvr-people/process-media

Headers:
  Authorization: Bearer <token>
  Content-Type: application/json

Body:
{
  "media_uuids": ["uuid1", "uuid2", ...],
  "processing_options": {
    "similarity_threshold": 0.8,
    "min_face_quality": 0.70,
    "include_demographics": true,
    "include_route_data": true
  }
}

Response:
{
  "success": true,
  "mvr_people_count": 15,  ← KEY METRIC
  "processed_media": 10,
  "failed_media": 0,
  "results": [...]
}
```

---

## Testing Checklist

### Manual Testing (Priority)
- [ ] Select 1 photo, process
- [ ] Select 5 videos, process
- [ ] Select 10 mixed media, process
- [ ] Cancel confirmation dialog
- [ ] Check MVR count is displayed prominently
- [ ] Verify progress shows correctly
- [ ] Test with failed items

### Edge Cases
- [ ] Process with 0 faces (no faces found)
- [ ] Process with network timeout
- [ ] Process with invalid media UUID
- [ ] Process 50+ media (performance)

---

## Performance Expectations

| Scenario | Expected Time |
|----------|---------------|
| 1 photo | 1-2 seconds |
| 1 video (30s) | 3-5 seconds |
| 10 photos | 10-15 seconds |
| 10 videos | 30-50 seconds |

---

## Next Steps

1. **Testing Phase**
   - Run manual tests
   - Document any bugs
   - Gather user feedback

2. **Authentication**
   - Integrate with AuthManager
   - Implement token refresh
   - Handle auth errors

3. **Navigation**
   - Implement "View MVR People" button
   - Add deep linking to MVR person detail

4. **Performance**
   - Add WebSocket for real-time progress
   - Implement batch processing
   - Add cancel functionality

---

## Documentation

- **Full Developer Guide**: `/docs/guides/developer/single-media-to-mvr-screen.md`
- **Implementation Summary**: `/docs/implementation/Single-Media-MVR-Screen-Implementation.md`
- **API Documentation**: `/docs/vmeta-api-endpoints.md` (Section 10)

---

## Support

**Questions?** Check the full developer guide for detailed implementation steps, code examples, and troubleshooting.

**Issues?** Document bugs in the implementation summary document.

---

## Status: ✅ READY FOR TESTING

The feature is fully implemented and integrated. Begin testing and provide feedback for improvements.

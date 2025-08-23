# CAM-FLUTTER-004 Phase 1 Testing Guide

## 🧪 **Manual Testing Plan for Phase 1**

### **Testing Environment Setup**

1. **Start PPL Meta Platform Services**:
   ```bash
   # Start all services
   🚀 Start All Local Python Services
   
   # Verify services are running
   🏥 Local Python Health Check - All Services
   ```

2. **Verify Camera Service**:
   ```bash
   curl http://localhost:8005/health
   # Should return: {"status": "healthy", "service": "ppl-meta-cameras"}
   ```

3. **Start Flutter Frontend**:
   ```bash
   cd ppl-meta-frontend
   flutter run -d chrome --web-port 3000
   ```

---

## 📋 **Test Cases**

### **Test 1: Snapshot Capture Button Integration**

**Objective**: Verify snapshot capture button works with enhanced resolution control

**Steps**:
1. Navigate to camera detail screen for a connected camera
2. Verify snapshot capture button is visible with gallery button
3. Tap snapshot capture button (should show visual feedback)
4. Verify success notification appears
5. Long-press snapshot capture button to open settings dialog
6. Modify resolution/quality settings and capture
7. Verify different settings produce different snapshot sizes

**Expected Results**:
- ✅ Button responds with pulse animation
- ✅ Flash effect during capture
- ✅ Success notification with "View" action
- ✅ Settings dialog opens on long press
- ✅ Different settings affect snapshot metadata

### **Test 2: Local Storage and Gallery**

**Objective**: Verify snapshots are saved locally and displayed in gallery

**Steps**:
1. Capture 3-5 snapshots from different cameras
2. Navigate to snapshot gallery (home screen → "Snapshots")
3. Verify all captured snapshots appear in grid
4. Verify thumbnails load correctly
5. Check camera indicators show different camera IDs
6. Verify timestamp and file size information

**Expected Results**:
- ✅ All snapshots appear in gallery grid
- ✅ Thumbnails display correctly
- ✅ Camera ID badges show for multi-camera view
- ✅ Metadata (time, size) displays correctly

### **Test 3: Snapshot Preview and Management**

**Objective**: Verify preview dialog and delete functionality

**Steps**:
1. From gallery, tap on any snapshot thumbnail
2. Verify preview dialog opens with full-size image
3. Check metadata display (capture time, size, resolution, format)
4. Tap "Download" button (should show Phase 2 message)
5. Tap "Delete" button and confirm deletion
6. Verify snapshot is removed from gallery

**Expected Results**:
- ✅ Preview dialog displays full-size image
- ✅ All metadata fields populated correctly
- ✅ Download shows Phase 2 placeholder message
- ✅ Delete confirmation dialog appears
- ✅ Snapshot removed after confirmation

### **Test 4: Search and Filtering**

**Objective**: Verify search functionality and camera filtering

**Steps**:
1. Capture snapshots from multiple cameras
2. Use search bar to search for camera ID
3. Verify filtered results show only matching camera
4. Clear search and verify all snapshots return
5. Navigate to camera-specific gallery from camera detail screen
6. Verify only that camera's snapshots appear

**Expected Results**:
- ✅ Search filters snapshots by camera ID and filename
- ✅ Clear search restores full gallery
- ✅ Camera-specific gallery shows only relevant snapshots

### **Test 5: Storage Limits and Performance**

**Objective**: Verify storage limits and performance with many snapshots

**Steps**:
1. Capture 20+ snapshots rapidly
2. Navigate to gallery and verify loading performance
3. Continue capturing until approaching 100 snapshot limit
4. Verify oldest snapshots are automatically removed
5. Check gallery performance with large number of items

**Expected Results**:
- ✅ Gallery loads quickly with many snapshots
- ✅ Automatic cleanup at 100 snapshots
- ✅ No performance degradation with large galleries

### **Test 6: Error Handling**

**Objective**: Verify graceful error handling

**Steps**:
1. Disconnect camera during streaming
2. Attempt snapshot capture
3. Verify error handling and user feedback
4. Try capturing with camera service offline
5. Test storage failure scenarios (if possible)

**Expected Results**:
- ✅ Clear error messages for capture failures
- ✅ Graceful degradation when services unavailable
- ✅ User can retry operations after errors

### **Test 7: Navigation Integration**

**Objective**: Verify all navigation paths work correctly

**Steps**:
1. Home screen → "Snapshots" quick action
2. Camera detail screen → "Gallery" button
3. Camera list → Camera detail → Gallery
4. Use browser back/forward buttons
5. Deep link to snapshot gallery routes

**Expected Results**:
- ✅ All navigation paths reach correct screens
- ✅ Browser navigation works correctly
- ✅ Routes handle parameters correctly

---

## 🔍 **Functional Verification Checklist**

### **Core Functionality**
- [ ] Snapshot capture with visual feedback
- [ ] Local storage persistence between app sessions
- [ ] Gallery grid display with thumbnails
- [ ] Search and filter functionality
- [ ] Preview dialog with metadata
- [ ] Delete operations with confirmation
- [ ] Settings integration (resolution, quality, format)
- [ ] Navigation between screens

### **Enhanced Resolution Integration**
- [ ] Settings dialog opens on long press
- [ ] Different resolution settings work
- [ ] Quality slider affects file size
- [ ] Format selection (JPEG/PNG) works
- [ ] Settings persist per camera

### **Performance & UX**
- [ ] Gallery loads quickly (<1 second)
- [ ] Smooth animations and transitions
- [ ] Responsive grid layout
- [ ] Efficient memory usage
- [ ] No lag during rapid captures

### **Error Handling**
- [ ] Network errors handled gracefully
- [ ] Storage errors provide feedback
- [ ] Corrupted data doesn't crash app
- [ ] Service unavailable scenarios handled

---

## 🎯 **Success Criteria Validation**

### **Functional Requirements**
- ✅ **F1**: Capture snapshots with enhanced resolution control
- ✅ **F2**: Local storage with persistence between sessions
- ✅ **F3**: Gallery display with thumbnail grid
- ✅ **F4**: Search and filter functionality
- ✅ **F5**: Preview with metadata display
- ✅ **F6**: Delete operations with confirmation

### **Technical Requirements**
- ✅ **T1**: Integration with existing camera service
- ✅ **T2**: SharedPreferences storage implementation
- ✅ **T3**: Performance optimization for mobile
- ✅ **T4**: Error handling and graceful degradation
- ✅ **T5**: Material Design 3 UI compliance

### **User Experience Requirements**
- ✅ **UX1**: Intuitive capture with visual feedback
- ✅ **UX2**: Fast gallery access from camera screens
- ✅ **UX3**: Efficient search and navigation
- ✅ **UX4**: Professional preview and management
- ✅ **UX5**: Consistent with existing app design

---

## 🐛 **Known Limitations (Phase 1)**

### **Expected Limitations**
1. **Storage**: Limited to ~100 snapshots (will be expanded in Phase 2)
2. **Sharing**: Download/share functionality placeholder (Phase 2 feature)
3. **Cloud Sync**: No cloud backup (Phase 2 with media service)
4. **Collections**: No advanced organization (Phase 2 feature)
5. **Metadata**: Basic metadata only (Phase 2 will add EXIF, tags)

### **Not Limitations (Should Work)**
1. ❌ Capture failures should have clear error messages
2. ❌ Gallery should load efficiently with many snapshots
3. ❌ Search should be responsive and accurate
4. ❌ Settings should persist correctly
5. ❌ Navigation should be smooth and intuitive

---

## 📊 **Performance Benchmarks**

### **Target Performance**
- **Capture Time**: <3 seconds (enhanced resolution)
- **Gallery Load**: <1 second (50 snapshots)
- **Search Response**: <100ms
- **Preview Display**: Instant
- **Storage Operation**: <500ms

### **Memory Usage**
- **Gallery View**: <50MB additional RAM
- **Preview Mode**: <100MB total
- **Background Storage**: Minimal impact

---

## 🔄 **Regression Testing**

### **Existing Features to Verify**
1. **Camera Management**: Ensure camera detection/listing still works
2. **Live Streaming**: Verify streaming functionality unaffected
3. **Enhanced Snapshots**: Confirm CAM-FLUTTER-003.1 integration intact
4. **Authentication**: Check JWT authentication flows still work
5. **Navigation**: Verify all existing navigation paths functional

---

## 📝 **Test Report Template**

### **Test Session Information**
- **Date**: _____
- **Tester**: _____
- **Environment**: _____
- **Version**: CAM-FLUTTER-004 Phase 1

### **Test Results Summary**
- **Tests Passed**: ___/___
- **Tests Failed**: ___/___
- **Critical Issues**: ___
- **Minor Issues**: ___

### **Issue Template**
```
**Issue ID**: CAM-004-[number]
**Severity**: [Critical/High/Medium/Low]
**Description**: [Clear description of issue]
**Steps to Reproduce**: [Numbered steps]
**Expected Result**: [What should happen]
**Actual Result**: [What actually happened]
**Environment**: [Browser, device, etc.]
**Status**: [Open/Fixed/Verified]
```

---

## ✅ **Phase 1 Approval Criteria**

### **Ready for Production When**
- [ ] All core functionality tests pass
- [ ] Performance benchmarks met
- [ ] No critical or high-severity bugs
- [ ] User experience meets design requirements
- [ ] Documentation complete
- [ ] Code review completed

### **Phase 2 Planning Triggers**
- [ ] Phase 1 stable in production
- [ ] Media service integration prioritized
- [ ] User feedback collected
- [ ] Performance metrics baseline established

---

*Testing guide for CAM-FLUTTER-004 Phase 1 implementation. Update this document as tests are completed and issues are resolved.*

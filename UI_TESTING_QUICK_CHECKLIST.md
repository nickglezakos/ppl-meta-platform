# PPL Meta Platform - UI Testing Quick Reference Checklist

## Pre-Testing Setup ✅

- [ ] All 6 backend services running and healthy
- [ ] Flutter frontend accessible at http://localhost:3000
- [ ] At least 2-3 test cameras available (physical or virtual)
- [ ] Browser developer tools ready for monitoring
- [ ] Test data prepared (videos/images for upload)

## Phase 1: Frontend Initialization (5 min)

- [ ] **1.1 App Startup**: App loads without errors, all services discovered
- [ ] **1.2 Authentication**: Login flow works, user authenticated
- [ ] **1.3 Service Status**: All 6 services show healthy status
- [ ] **1.4 Navigation**: All pages/routes accessible

## Phase 2: Camera Page Features (10 min)

- [ ] **2.1 Camera Detection**: Camera cards display with connection status
- [ ] **2.2 Workflow Controls**: "Start Detection" and "View Status" buttons visible
- [ ] **2.3 Method Selection**: Detection method dialog (MTCNN, Haar, DLib) works
- [ ] **2.4 Confidence Slider**: Threshold setting (0.1-0.9) functions
- [ ] **2.5 Workflow Submission**: Can start workflows successfully

## Phase 3: Workflow Status & Monitoring (10 min)

- [ ] **3.1 Status Dialog**: View Status button opens workflow information
- [ ] **3.2 Progress Updates**: Status updates in real-time or with refresh
- [ ] **3.3 Workflow ID**: Unique identifiers displayed correctly
- [ ] **3.4 Error States**: Failed workflows show appropriate messages
- [ ] **3.5 Completion**: Completed workflows show results summary

## Phase 4: Camera Recording Automation (15 min)

- [ ] **4.1 Recording Start**: Camera recording begins successfully
- [ ] **4.2 Recording Stop**: Recording stops and saves properly
- [ ] **4.3 Auto-Trigger**: Recording completion automatically starts workflow
- [ ] **4.4 Event Publishing**: Check network tab for orchestrator event calls
- [ ] **4.5 Workflow Processing**: Automatic face detection begins
- [ ] **4.6 End-to-End**: Complete recording → detection → results pipeline

## Phase 5: Media Service Integration (15 min)

- [ ] **5.1 Bulk Processing**: Multiple media items can be processed together
- [ ] **5.2 Individual Status**: Each media item shows processing progress
- [ ] **5.3 API Monitoring**: Workflow API calls visible in network tab
- [ ] **5.4 Results Storage**: Processed results appear in Vision Service
- [ ] **5.5 Cross-Service**: Media → Vision data flow works

## Phase 6: Vision Service Features (10 min)

- [ ] **6.1 Face Overlays**: Detection results display on videos/images
- [ ] **6.2 Bounding Boxes**: Face detection boxes are accurate
- [ ] **6.3 Confidence Scores**: Confidence values shown correctly
- [ ] **6.4 Timeline Data**: Face detection timeline/metadata available
- [ ] **6.5 Filtering**: Confidence threshold filtering works

## Phase 7: Error Handling & Edge Cases (15 min)

- [ ] **7.1 Service Offline**: UI handles backend service unavailability
- [ ] **7.2 Network Errors**: Connection failures show user-friendly messages
- [ ] **7.3 Invalid Inputs**: Bad parameters handled gracefully
- [ ] **7.4 Large Files**: Big video files process without timeout
- [ ] **7.5 Recovery**: Service restoration detected automatically

## Phase 8: Performance & UX (10 min)

- [ ] **8.1 Responsiveness**: UI stays responsive during processing
- [ ] **8.2 Concurrent Workflows**: Multiple workflows don't interfere
- [ ] **8.3 Memory Usage**: No memory leaks or performance degradation
- [ ] **8.4 Loading States**: Appropriate loading indicators throughout
- [ ] **8.5 Notification**: Completion notifications appear correctly

## Critical Integration Points to Verify

### 📹 Camera → Orchestrator
- [ ] Recording completion events published successfully
- [ ] Event payload contains correct metadata
- [ ] Orchestrator receives and processes events

### 🎼 Orchestrator → Media Service  
- [ ] Workflow creation requests sent correctly
- [ ] Bulk processing initiated automatically
- [ ] Status updates flow back to frontend

### 🎨 Media Service → Vision Service
- [ ] Face detection results sent to Vision Service
- [ ] Bulk storage endpoint receives data correctly
- [ ] Analytics data available for cross-video processing

### 🔄 End-to-End Automation
- [ ] Complete pipeline: Camera → Orchestrator → Media → Vision
- [ ] No manual intervention required after recording
- [ ] Results visible throughout the UI

## Browser Developer Tools Checklist

### Console Tab
- [ ] No JavaScript errors during normal operation
- [ ] Warning messages (if any) are acceptable
- [ ] No memory leak indicators

### Network Tab
- [ ] API calls to all services successful (200/201 responses)
- [ ] Authentication headers present and valid
- [ ] Reasonable response times (<3s for most requests)
- [ ] WebSocket connections stable (if used)

### Performance Tab
- [ ] Page load times acceptable (<5s)
- [ ] Memory usage stable during workflows
- [ ] CPU usage reasonable during processing

## Quick Issue Identification

### 🔴 Critical Issues (Stop Testing)
- App crashes or freezes
- Authentication completely broken
- No services discoverable
- Major JavaScript errors preventing operation

### 🟡 Medium Issues (Note & Continue)
- Slow response times (>5s)
- Intermittent connection issues
- UI elements not updating
- Non-critical feature failures

### 🟢 Minor Issues (Document)
- Cosmetic display issues
- Minor UX improvements needed
- Performance optimizations possible
- Non-essential feature gaps

## Success Criteria Summary

**✅ Testing Complete When:**
- All critical features work end-to-end
- Error handling prevents app crashes
- Performance meets acceptable standards
- Integration pipeline functions automatically
- User experience is smooth and intuitive

**📊 Metrics to Track:**
- Workflow success rate (target: >95%)
- Average processing time per video
- UI response times for key actions
- Error recovery success rate

**🎯 Final Validation:**
Record a video, verify automatic face detection workflow completion, and view results in UI - all without manual workflow initiation.

---

**Estimated Total Testing Time: 90-120 minutes**  
**Prerequisites Check Time: 15 minutes**  
**Documentation Time: 30 minutes**

Use this checklist alongside the comprehensive testing guide for complete validation coverage.
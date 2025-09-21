# PPL Meta Platform - Use Case Testing Checklist

## ⚠️ Key Testing Notes

**Camera Workflow Buttons (Use Case 3):**
- ✅ Detection method selection works with 4 options: Two-Stage (default), MTCNN, Haar, DLib  
- ✅ "No active workflows found" is **NORMAL behavior** - not a bug
- ✅ Workflow buttons are demonstration UI showing method selection capabilities
- ✅ Two-Stage method (Haar + DLib validation) is the recommended default

## Pre-Testing Setup ✅

- [ ] All 6 backend services running and healthy
- [ ] Flutter frontend accessible at http://localhost:3000
- [ ] At least 2-3 test cameras available (physical or mobile)
- [ ] Browser developer tools ready for monitoring
- [ ] User logged in with valid credentials

---

## 🎥 Use Case 1: Record Basic Video Without Face Detection (5 min)

**Scenario:** Simple video recording for testing camera functionality

### Steps

- [ ] **1.1** Navigate to Cameras page
- [ ] **1.2** Select a connected camera
- [ ] **1.3** Click "Start Recording" 
- [ ] **1.4** Record for 10-15 seconds
- [ ] **1.5** Click "Stop Recording"
- [ ] **1.6** Verify video appears in media gallery
- [ ] **1.7** Play video to confirm quality and duration

### Expected Results:
- [ ] Recording starts immediately
- [ ] Timer shows recording duration
- [ ] Video file saved successfully
- [ ] No face detection workflow triggered
- [ ] Video playback works smoothly

---

## 🤖 Use Case 2: Record Video With Automatic Face Detection (10 min)

**Scenario:** End-to-end automated workflow from recording to face detection

### Prerequisites
- [ ] **2.0** Navigate to Features page (http://localhost:3000/#/features)
- [ ] **2.0.1** Verify "Face Detection" feature is enabled for the user
- [ ] **2.0.2** If disabled, enable the Face Detection feature toggle

### Steps
- [ ] **2.1** Navigate to Cameras page
- [ ] **2.2** Select a connected camera
- [ ] **2.3** Position face(s) in camera view
- [ ] **2.4** Click "Start Recording"
- [ ] **2.5** Notice yellow rectangles appear during live recording (camera service live detection)
- [ ] **2.6** Record for 15-20 seconds with visible faces
- [ ] **2.7** Click "Stop Recording"
- [ ] **2.8** Wait for automatic workflow to start (should be immediate if face detection feature enabled)
- [ ] **2.9** Navigate to Workflows page
- [ ] **2.10** Verify new workflow appears in active sessions
- [ ] **2.11** Wait for processing completion (1-3 minutes)
- [ ] **2.12** Check results in media gallery with face overlays

### Expected Results
- [ ] Recording completes successfully
- [ ] Yellow rectangles visible during live recording (normal camera behavior)
- [ ] Workflow automatically starts after recording stops (due to enabled feature)
- [ ] Workflow shows "Processing" status
- [ ] Face detection completes without errors
- [ ] Video shows bounding boxes around detected faces
- [ ] Confidence scores displayed for each detection
- [ ] Video status changes from "unprocessed" to "processed"

---

## ⚙️ Use Case 3: Manual Camera Workflow Testing (15 min)

**Scenario:** Test camera card workflow buttons and detection method selection

### Steps:
- [ ] **3.1** Navigate to Cameras page
- [ ] **3.2** Locate a connected camera card
- [ ] **3.3** Click "Start Detection" button on camera card
- [ ] **3.4** Verify detection method dialog appears with 4 options:
  - [ ] **3.4.1** Two-Stage Detection (Recommended) - Haar + DLib validation ✅ **DEFAULT**
  - [ ] **3.4.2** MTCNN - High accuracy, multi-stage detection
  - [ ] **3.4.3** Haar Cascade - Fast, good for real-time detection  
  - [ ] **3.4.4** DLib - Reliable detection with landmarks
- [ ] **3.5** Select "Two-Stage Detection" (default recommended option)
- [ ] **3.6** Click to confirm workflow start
- [ ] **3.7** Observe success/confirmation message
- [ ] **3.8** Click "View Status" button on same camera card
- [ ] **3.9** Verify workflow status dialog appears
- [ ] **3.10** **EXPECTED**: Dialog shows "No active workflows found" message
- [ ] **3.11** Click "Start Workflow" button in status dialog
- [ ] **3.12** Repeat with different detection methods

### Expected Results (Current Implementation):
- [ ] Detection method dialog opens correctly ✅
- [ ] All 4 detection methods are selectable ✅
- [ ] Two-Stage is correctly highlighted as recommended default ✅
- [ ] Workflow start shows success message ✅
- [ ] "View Status" dialog displays correctly ✅
- [ ] **"No active workflows found" is NORMAL behavior** ✅
- [ ] Status dialog includes "Start Workflow" button ✅

### Notes:
- **Camera workflow buttons are DEMONSTRATION UI** - they show method selection and status checking
- **"No active workflows found" is expected** - indicates no background processing active  
- **Not a bug** - this is the current implementation state
- **Two-Stage method** combines Haar Cascade + DLib validation for best accuracy

---

## 📊 Use Case 4: Check Video Processing Status (5 min)

**Scenario:** Monitor and verify processing progress of uploaded videos

### Steps:
- [ ] **4.1** Upload a video file via gallery/upload interface
- [ ] **4.2** Start face detection workflow on uploaded video
- [ ] **4.3** Navigate to Workflows page
- [ ] **4.4** Locate the video in active sessions
- [ ] **4.5** Click "View Status" or workflow details
- [ ] **4.6** Refresh status multiple times during processing
- [ ] **4.7** Check processing percentage/progress
- [ ] **4.8** Verify completion notification
- [ ] **4.9** Navigate back to media gallery
- [ ] **4.10** Confirm processed video shows face overlays

### Expected Results:
- [ ] Status shows "Queued" → "Processing" → "Completed"
- [ ] Progress percentage updates appropriately
- [ ] Processing time is reasonable (<2 minutes for short videos)
- [ ] No stuck or failed workflows
- [ ] Results appear in media gallery after completion

---

## 📤 Use Case 5: Batch Process Multiple Videos (15 min)

**Scenario:** Process several videos simultaneously to test system load

### Steps:
- [ ] **5.1** Upload 3-5 videos to media gallery
- [ ] **5.2** Select all videos using checkboxes
- [ ] **5.3** Click "Start Batch Face Detection"
- [ ] **5.4** Choose detection settings for batch
- [ ] **5.5** Confirm batch processing start
- [ ] **5.6** Monitor workflows page for multiple active sessions
- [ ] **5.7** Check system performance during processing
- [ ] **5.8** Wait for all workflows to complete
- [ ] **5.9** Verify all videos have face detection results
- [ ] **5.10** Check for any failed or stuck workflows

### Expected Results:
- [ ] All workflows start successfully
- [ ] System handles multiple concurrent processes
- [ ] No significant UI slowdown during batch processing
- [ ] All videos complete processing
- [ ] Results are accurate across all videos

---

## 🔄 Use Case 6: Test Workflow Error Recovery (10 min)

**Scenario:** Verify system handles errors gracefully and allows retry

### Steps:
- [ ] **6.1** Upload a corrupted or invalid video file
- [ ] **6.2** Attempt to start face detection workflow
- [ ] **6.3** Observe error handling in workflows page
- [ ] **6.4** Try to restart failed workflow
- [ ] **6.5** Upload a very large video file (>100MB)
- [ ] **6.6** Start processing and monitor for timeout issues
- [ ] **6.7** Cancel an in-progress workflow mid-processing
- [ ] **6.8** Verify system state remains stable
- [ ] **6.9** Start new workflow after cancellation

### Expected Results:
- [ ] Invalid files show clear error messages
- [ ] Failed workflows can be retried
- [ ] Large files either process successfully or fail gracefully
- [ ] Cancelled workflows don't leave system in bad state
- [ ] Error messages are user-friendly and actionable

---

## 📱 Use Case 7: Mobile Camera Integration (15 min)

**Scenario:** Test mobile device camera streaming and recording

### Steps:
- [ ] **7.1** Connect mobile device to platform
- [ ] **7.2** Verify mobile camera appears in cameras list
- [ ] **7.3** Start live stream from mobile camera
- [ ] **7.4** Check stream quality and latency
- [ ] **7.5** Record video from mobile camera stream
- [ ] **7.6** Enable face detection for mobile recording
- [ ] **7.7** Test recording while moving mobile device
- [ ] **7.8** Verify mobile camera settings (resolution, fps)
- [ ] **7.9** Test connection stability (disconnect/reconnect)
- [ ] **7.10** Process recorded mobile video with face detection

### Expected Results:
- [ ] Mobile camera detected and connected
- [ ] Live stream works with acceptable latency (<2 seconds)
- [ ] Recording quality matches stream quality
- [ ] Face detection works on mobile recordings
- [ ] Connection handles network fluctuations
- [ ] Mobile-specific metadata captured correctly

---

## 🎯 Use Case 8: End-to-End Complete Workflow (20 min)

**Scenario:** Full pipeline test from camera setup to final results

### Steps:
- [ ] **8.1** Set up new camera (physical or mobile)
- [ ] **8.2** Configure optimal detection settings
- [ ] **8.3** Record test video with multiple people
- [ ] **8.4** Verify automatic workflow trigger
- [ ] **8.5** Monitor processing in real-time
- [ ] **8.6** Review detection accuracy and quality
- [ ] **8.7** Export or share processed video
- [ ] **8.8** Generate analytics report on detections
- [ ] **8.9** Save configuration as preset for future use
- [ ] **8.10** Test preset on new recording

### Expected Results:
- [ ] Complete pipeline works without manual intervention
- [ ] Detection accuracy meets expectations (>90% for clear faces)
- [ ] Processing time is acceptable for video length
- [ ] Results can be exported/shared successfully
- [ ] Analytics provide meaningful insights
- [ ] Configuration presets save and apply correctly

---

## � Critical Issues to Watch For

### 🔴 Stop Testing Immediately If:
- [ ] App crashes or becomes unresponsive
- [ ] Authentication completely fails
- [ ] No cameras can be detected or connected
- [ ] Video recording fails consistently
- [ ] Face detection never starts or always fails

### 🟡 Note But Continue If:
- [ ] Slow processing times (>5 minutes for 30-second video)
- [ ] Occasional connection drops
- [ ] UI elements don't update immediately
- [ ] Some workflows fail intermittently

### 🟢 Minor Issues to Document:
- [ ] Cosmetic UI issues
- [ ] Non-critical feature gaps
- [ ] Performance optimization opportunities
- [ ] UX improvements needed

---

## 📋 Quick Success Verification

**After completing use cases, verify:**

- [ ] ✅ **Recording**: Can record videos from any connected camera
- [ ] ✅ **Detection**: Face detection workflows complete successfully
- [ ] ✅ **Settings**: Detection parameters can be customized and applied
- [ ] ✅ **Monitoring**: Processing status is visible and accurate
- [ ] ✅ **Results**: Face overlays appear on processed videos
- [ ] ✅ **Performance**: System handles multiple workflows concurrently
- [ ] ✅ **Errors**: Failed workflows are handled gracefully
- [ ] ✅ **Mobile**: Mobile cameras integrate seamlessly

**🎯 Final Test: Record a 30-second video with faces, verify automatic detection completes, and view results with bounding boxes - all within 5 minutes total.**

---

**Estimated Testing Time: 90-120 minutes**  
**Critical Path Time: 30 minutes (Use Cases 1, 2, 4, 8)**  
**Full Coverage Time: 120 minutes (All use cases)**
# PPL Meta Platform - Frontend Screens Documentation

This document provides comprehensive information about all frontend screens in the PPL Meta Platform, including widget inventories, layout structures, and reorganization recommendations.

---

## Media Preview Screen

**File**: `ppl-meta-frontend/lib/screens/media_preview_screen.dart`  
**Last Updated**: September 22, 2025  
**Version**: v2.18.4+  
**Status**: ✅ Face detection workflows fully functional - UI reorganized

### 📋 Current Layout Structure (After Reorganization)

The media preview screen has been reorganized for better UX and reduced clutter:

#### 🎯 Main Layout Structure

1. **Simplified AppBar** (`_buildEnhancedAppBar`)
   - Back button with navigation logic
   - Media filename display
   - Home button for quick gallery access

2. **Enhanced Performance Status Bar** (`_buildPerformanceStatusBar`)
   - **Playback mode indicator** (colored badge: Optimized/Session/Real-time)
   - **Processing status display** (compact face detection status with count)
   - **Active sessions status** (active/completed session counters)

3. **Media Content Area** (`_buildMediaContent`)
   - Image preview (`_buildImagePreview`)
   - Video preview (`_buildVideoPreview`)
   - Unsupported media message (`_buildUnsupportedMediaPreview`)
   - Error preview display (`_buildErrorPreview`)

4. **Bottom Control Bar** (`_buildBottomControlBar`)
   - **Workflow Controls header** with expand/collapse toggle
   - **Expandable Enhanced Workflow Controls** (`_buildEnhancedWorkflowControls`)
     - Start Session (face detection)
     - Optimize (stored face data processing)
     - Metrics (performance analytics)
     - Settings (workflow configuration)
     - Stop Session (conditional)
     - Refresh (status update)

### 🔄 Reorganization Changes

**✅ Completed Reorganization:**

- **AppBar Simplified**: Removed performance analytics button and compact metrics widget
- **Enhanced Performance Status Bar**: Consolidated status display with compact widgets
- **Video Player Overlays**: Disabled duplicate status indicators (moved to performance bar)

**🚧 In Progress - Horizontal Widget Layout:**

**Issue**: Performance status bar widgets should display horizontally but may still appear stacked
**Target Layout**: 5 widgets horizontally arranged:
1. **Playback Mode Indicator** - Current playback mode (real-time, stored data, etc.)
2. **Processing Status Display** - Face detection status and count  
3. **Active Sessions Status** - Running session progress indicators
4. **Media Workflow Progress** - Orchestrator-based workflow progress with percentages
5. **Workflow Status Display** - Overall workflow status (processing, completed, etc.)

**Implementation**: 
- ✅ Created compact horizontal methods: `_buildCompactActiveSessionsStatus`, `_buildCompactMediaWorkflowProgress`
- ✅ Updated performance bar with 5-widget Row layout using Flexible containers
- ✅ Disabled video overlay indicators to prevent duplicate displays
- 🔄 **Needs Verification**: Widgets may not be displaying horizontally as expected

**Next Steps**: Test and verify all 5 widgets render horizontally in performance status bar

**⚠️ Known Issues:**
- ✅ **Fixed - Bottom Bar Duplicate Controls**: Removed duplicate "workflow controls" header within `_buildEnhancedWorkflowControls` method
- **Performance Bar Enhanced**: Added playback mode, processing status, and session status from overlay
- **Bottom Bar Created**: Moved workflow controls from overlay to collapsible bottom bar
- **Overlay Removed**: Eliminated the cluttered 280px overlay panel

**🎨 New Layout Benefits:**

- **Clean UI**: No more overlay covering media content
- **Logical Grouping**: Status info in top bar, controls in bottom bar
- **Progressive Disclosure**: Workflow controls expandable when needed
- **Better Focus**: Media content gets full screen space
- **Working Functionality**: Face detection workflow still fully functional

### 🔧 Widget Implementation Details

#### Enhanced Performance Status Bar Widgets

- **Compact Processing Status**: Shows face detection completion, face count, processing state
- **Playback Mode Indicator**: Color-coded badges for different modes
- **Compact Sessions Status**: Active/completed session counters with icons

#### Bottom Control Bar Widgets

- **Expandable Container**: Collapsible workflow controls section
- **Enhanced Control Buttons**: Styled buttons with icons, labels, and state management
- **Toggle Header**: Expand/collapse functionality with visual indicators

### 🚫 Removed/Commented Components

- **Workflow Status Overlay**: The 280px positioned card overlay (commented out)
- **Performance Analytics Button**: Removed from AppBar
- **Compact Performance Metrics Widget**: Removed from AppBar
- **WorkflowSessionControlsWidget**: Replaced with enhanced bottom bar

### 🔄 Current Workflow Status

**✅ Working Workflows:**

- Face Detection (Workflow 4) - Session-based processing
- Real-time progress tracking via MediaWorkflowNotifier
- 57 faces detected successfully in recent tests

**⚠️ Issue Identified:**

- User reports "plethora of widgets" with limited functionality
- Only face detection workflow working as expected
- UI cluttered with multiple overlapping status displays

### 🎨 Reorganization Recommendations

Since only face detection workflow is working properly, here are three reorganization approaches:

#### **Option A: Streamlined Layout**

```text
┌─────────────────────────────────────┐
│ AppBar (keep as-is)                 │
├─────────────────────────────────────┤  
│ ✅ Working Face Detection Panel     │
│   • MediaWorkflow Progress          │
│   • Start Session Button           │  
│   • Results Display                 │
└─────────────────────────────────────┘
│ 📱 Collapse Other Widgets Into:    │
│   • "Advanced Controls" Expandable │
│   • "Debug Info" Collapsible       │
└─────────────────────────────────────┘
```

**Benefits:**

- Highlights working functionality
- Reduces visual clutter
- Maintains access to debug tools

#### **Option B: Tabbed Interface**

```text
┌─────────────────────────────────────┐
│ [Face Detection] [Advanced] [Debug] │
├─────────────────────────────────────┤
│ Tab content based on selection      │
│ • Default: Face Detection tab       │
│ • Advanced: Other workflow controls │
│ • Debug: Session status & metrics   │
└─────────────────────────────────────┘
```

**Benefits:**

- Clear separation of concerns
- Scalable for future workflows
- Better organization

#### **Option C: Sidebar Layout**

```text
┌──────────────┬──────────────────────┐
│ Media        │ Face Detection Panel │
│ Preview      │ ✅ Working widgets   │
│              ├──────────────────────┤
│              │ [Collapsed Others]   │
│              │ [Expandable Sections]│
└──────────────┴──────────────────────┘
```

**Benefits:**

- More screen real estate for media
- Dedicated workflow panel
- Progressive disclosure

### 🔧 Implementation Notes

**Key Files:**

- Main screen: `ppl-meta-frontend/lib/screens/media_preview_screen.dart`
- Workflow provider: `ppl-meta-frontend/lib/providers/workflow_providers.dart`
- Backend integration: `ppl-meta-media/src/api/v1/face_detection_workflows.py`

**Recent Fixes (v2.18.4):**

- Fixed FastAPI BackgroundTasks → asyncio.create_task()
- Enhanced MediaWorkflowNotifier with real-time polling
- Added proper null safety handling
- Implemented comprehensive progress tracking

**Dependencies:**

- Flutter Riverpod for state management
- Custom providers for workflow state
- FastAPI backend with async processing
- Real-time status updates via HTTP polling

---

## Additional Screens

*This section will be expanded as other screens are analyzed and documented.*

### Gallery Screen

Coming soon - to be documented when analyzed.

### Settings Screen

Coming soon - to be documented when analyzed.

### Performance Metrics Screen

Coming soon - to be documented when analyzed.

---

## Documentation Maintenance

**Last Updated**: September 21, 2025  
**Maintainer**: Development Team  
**Review Schedule**: After major UI changes  
**Related Files**:

- `/docs/frontend-screens.md` (this file)
- `/ppl-meta-frontend/lib/screens/`
- `/docs/deployment/`

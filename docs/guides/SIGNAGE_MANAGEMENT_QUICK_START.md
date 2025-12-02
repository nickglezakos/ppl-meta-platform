# Signage Management UI - Quick Start Guide

## Accessing the UI

1. **From Home Screen:**
   - Launch PPL Meta Frontend
   - Look for "Signage Management" card (orange display icon)
   - Click to open

2. **Direct URL:**
   - Navigate to: `http://localhost:3000/signage`

---

## Creating Your First Playlist

### Step 1: Open Playlist Creator
1. Go to "Playlists" tab
2. Click the **+ FAB** button (bottom right)

### Step 2: Configure Playlist
1. **Name:** Enter playlist name (required)
2. **Description:** Add optional description
3. **Loop Mode:** Choose playback mode
   - **Once:** Play through once and stop
   - **Continuous:** Loop forever
   - **Shuffle:** Random order, continuous
4. **Transition Duration:** Seconds between videos (default: 1s)

### Step 3: Select Collections
1. Check boxes next to collections you want to include
2. Each collection shows video count
3. You can select multiple collections

### Step 4: Order Videos
1. Videos from selected collections appear in list
2. **Drag & drop** to reorder videos
3. Or click **"Auto Order Videos"** to arrange sequentially
4. Use **X** button to remove individual videos

### Step 5: Save
1. Review your playlist
2. Click **"Save"** button
3. Success message confirms creation

---

## Managing Playlists

### View Playlists
- All playlists shown in "Playlists" tab
- Each card shows:
  - Playlist name
  - Number of videos
  - Total duration
  - Status (active/inactive)

### Edit Playlist
1. Click **⋮** menu on playlist card
2. Select **"Edit"**
3. Make changes
4. Click **"Save"**

### Duplicate Playlist
1. Click **⋮** menu
2. Select **"Duplicate"**
3. Creates copy with "(Copy)" suffix

### Delete Playlist
1. Click **⋮** menu
2. Select **"Delete"**
3. Confirm deletion

### Search Playlists
- Use search bar at top of Playlists tab
- Searches by name

---

## Managing Devices

### View Devices
1. Go to **"Devices"** tab
2. See all registered signage players
3. Status indicators:
   - **🟢 Green dot:** Online
   - **🔴 Red dot:** Offline

### Device Information
Each device card shows:
- Device name
- Network address (host:port)
- Online status
- Current playback (if playing):
  - Video title
  - Progress bar
  - Playlist name

### Device Actions
Quick action buttons on each card:
- **🔄 Sync:** Sync playlist to this device
- **▶️ Play/⏸️ Pause:** Control playback
- **⏹️ Stop:** Stop playback
- **ℹ️ Info:** View device details

### Sync Playlist to Device
1. Click **🔄 Sync** button on device card
2. Select playlist from list
3. Click to confirm sync
4. Wait for sync to complete

### Select Device for Control
1. Click on device card
2. Switches to "Control" tab
3. Shows full remote control interface

---

## Remote Control

### Accessing Controls
1. Go to "Devices" tab
2. Click on a device card
3. Automatically switches to "Control" tab

### Playback Information
Top card shows:
- Device name and status
- Current video title
- Playlist name
- Progress bar with percentage
- Time elapsed / total duration
- Video position in playlist (X of Y)

### Control Buttons

**Main Controls (Center):**
- **⏮️ Previous:** Go to previous video
- **⏹️ Stop:** Stop playback (red button)
- **▶️ Play / ⏸️ Pause:** Start/pause playback (large green button, center)
- **🔁 Replay:** Restart current playlist
- **⏭️ Next:** Skip to next video

**Playlist Selector:**
- Button: "Select & Play Playlist"
- Opens dialog to choose playlist
- Starts playback immediately after selection

**Volume Control:**
- Slider from 0% to 100%
- Adjusts audio level on device

### Auto-Refresh
- Status updates every 3 seconds automatically
- Shows real-time playback progress
- Or click **🔄 Refresh** button manually

---

## Tips & Tricks

### Creating Playlists
- **Use multiple collections:** Mix content from different sources
- **Auto-order first:** Then fine-tune order manually
- **Test with short transitions:** 1-2 seconds works well
- **Use descriptive names:** Helps when syncing to devices

### Managing Devices
- **Check online status first:** Green dot = ready to sync
- **Sync before playing:** Ensure device has latest playlist
- **Use device names:** Name devices by location (e.g., "Lobby Display")

### Remote Control
- **Volume at 80%:** Safe starting point
- **Watch progress bar:** Verify playback is smooth
- **Stop before syncing:** Stop playback before new sync

### Troubleshooting
- **Device offline?** Check network connection
- **Playlist not syncing?** Verify ETL service is running
- **Playback won't start?** Ensure device has content synced
- **No devices showing?** Check discovery service

---

## Keyboard Shortcuts

*(Coming soon)*

---

## Video Walkthrough

*(Link to video tutorial - coming soon)*

---

## FAQs

**Q: How many videos can be in a playlist?**  
A: No hard limit, but 20-50 videos recommended for performance.

**Q: Can I play different playlists on different devices simultaneously?**  
A: Yes! Each device can play independently.

**Q: What happens if I edit a playlist while it's playing?**  
A: Device continues with current version. Sync again to update.

**Q: Can I schedule playlists to change automatically?**  
A: Not yet - coming in Phase 8 (Scheduling).

**Q: What video formats are supported?**  
A: MP4, AVI, MOV (depends on device player capabilities).

**Q: How do I add videos to collections?**  
A: Use the "Upload Media" → "Collections" flow in main app.

**Q: Can I preview videos before adding to playlist?**  
A: Yes - videos link to media preview from edit dialog.

**Q: How do I monitor multiple devices at once?**  
A: Use the "Devices" tab grid view - shows all statuses.

---

## Common Workflows

### Workflow 1: Create and Deploy Playlist
1. Create playlist with collections
2. Order videos as desired
3. Go to Devices tab
4. Sync playlist to target device(s)
5. Select device for control
6. Start playback

### Workflow 2: Update Running Playlist
1. Edit existing playlist
2. Add/remove/reorder videos
3. Save changes
4. Go to Devices tab
5. Sync playlist to device (overwrites)
6. Playback continues with new content

### Workflow 3: Swap Content on Device
1. Go to Control tab
2. Stop current playback
3. Click "Select & Play Playlist"
4. Choose new playlist
5. Playback starts immediately

### Workflow 4: Monitor Multiple Locations
1. Go to Devices tab
2. View grid of all devices
3. Check online status (green dots)
4. View current playback on each
5. Use quick actions as needed

---

## Support

**Documentation:** `/docs/implementation/SIGNAGE_MANAGEMENT_UI_IMPLEMENTATION.md`  
**Issues:** Report via GitHub issues  
**Questions:** Contact dev team

---

**Last Updated:** December 2, 2024  
**Version:** 1.0

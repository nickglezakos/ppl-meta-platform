# Orientation Toggle Feature

## Overview
The signage player app now supports both landscape and portrait orientations with a user-controlled toggle.

## Changes Made

### Modified File
- [lib/screens/signage_player_screen.dart](lib/screens/signage_player_screen.dart)

### Implementation Details

1. **State Management**
   - Added `_isLandscape` boolean state variable (defaults to `true`)
   - App starts in landscape mode as required

2. **Orientation Control Methods**
   - `_updateOrientation()`: Updates device orientation based on current state
     - Landscape: `DeviceOrientation.landscapeLeft` and `landscapeRight`
     - Portrait: `DeviceOrientation.portraitUp` and `portraitDown`
   - `_toggleOrientation()`: Toggles between landscape and portrait modes

3. **UI Toggle Button**
   - Added a new IconButton in the top-right controls row
   - Icon changes based on current orientation:
     - Landscape mode: Shows `Icons.screen_rotation` (switch to portrait)
     - Portrait mode: Shows `Icons.screen_lock_rotation` (switch to landscape)
   - Tooltip provides clear indication of action
   - Button is only visible when `showControls` is true

4. **Keyboard Shortcut**
   - Press `O` key to toggle orientation
   - Works alongside existing keyboard shortcuts (Space, Arrow keys, I, C, Escape)

## Usage

### Via UI
1. Tap the screen to show controls
2. Look for the orientation toggle icon in the top-right corner (leftmost button)
3. Tap the button to switch between landscape and portrait

### Via Keyboard
- Press the `O` key to toggle orientation

## Testing
To test the feature:
1. Run the app: `flutter run`
2. Tap screen to reveal controls
3. Click the orientation toggle button
4. Verify the screen rotates between landscape and portrait modes

## Notes
- The app starts in landscape mode by default
- Orientation does NOT follow device rotation automatically
- User has full control over the orientation via the toggle
- Orientation preference is session-based (not persisted between app restarts)

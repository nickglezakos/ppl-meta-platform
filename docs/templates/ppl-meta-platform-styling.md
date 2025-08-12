# 🎨 PPL Meta Platform Styling Guide

**Version**: 1.0  
**Last Updated**: August 12, 2025  
**Theme System**: Material 3 with Custom Dark Theme

---

## 📋 **Overview**

This document provides a comprehensive guide to the PPL Meta Platform's styling system, including color palettes, typography, spacing, and component styling guidelines.

---

## 🌈 **Color Palette**

### **Primary & Brand Colors**

| Color Name            | Hex Code | Usage                          | Preview      |
| --------------------- | -------- | ------------------------------ | ------------ |
| `AppColors.primary`   | #1976D2  | Primary brand color, main CTAs | 🔵 Blue      |
| `AppColors.secondary` | #03DAC6  | Secondary brand color, accents | 🔷 Cyan/Teal |
| `AppColors.accent`    | #03DAC6  | Accent highlights, links       | 🔷 Cyan/Teal |

### **Status & Feedback Colors**

| Color Name          | Hex Code | Usage                             | Preview         |
| ------------------- | -------- | --------------------------------- | --------------- |
| `AppColors.success` | #4CAF50  | Success states, completed actions | 🟢 Green        |
| `AppColors.warning` | #FFC107  | Warning states, pending actions   | 🟡 Amber/Yellow |
| `AppColors.error`   | #CF6679  | Error states, failed actions      | 🔴 Red          |
| `AppColors.info`    | #2196F3  | Informational messages, hints     | 🔵 Blue         |

### **Media Type Colors**

| Color Name                | Hex Code | Usage                    | Preview   |
| ------------------------- | -------- | ------------------------ | --------- |
| `AppColors.imageColor`    | #4CAF50  | Image file indicators    | 🟢 Green  |
| `AppColors.videoColor`    | #2196F3  | Video file indicators    | 🔵 Blue   |
| `AppColors.audioColor`    | #9C27B0  | Audio file indicators    | 🟣 Purple |
| `AppColors.documentColor` | #795548  | Document file indicators | 🟤 Brown  |

### **Upload State Colors**

| Color Name                   | Hex Code | Usage                       | Preview  |
| ---------------------------- | -------- | --------------------------- | -------- |
| `AppColors.uploadPending`    | #FFC107  | Files waiting to upload     | 🟡 Amber |
| `AppColors.uploadInProgress` | #2196F3  | Files currently uploading   | 🔵 Blue  |
| `AppColors.uploadCompleted`  | #4CAF50  | Successfully uploaded files | 🟢 Green |
| `AppColors.uploadFailed`     | #CF6679  | Failed upload attempts      | 🔴 Red   |

### **Surface & Background Colors**

| Color Name                 | Hex Code | Usage                               | Preview           |
| -------------------------- | -------- | ----------------------------------- | ----------------- |
| `AppColors.surface`        | #061d36  | Card backgrounds, elevated surfaces | 🌑 Dark Blue      |
| `AppColors.surfaceVariant` | #0c2942  | Alternative surface color           | 🌑 Darker Blue    |
| `AppColors.background`     | #061d36  | Main background color               | 🌑 Dark Blue      |
| `AppColors.widgetFill`     | #041121  | Form inputs, widget backgrounds     | ⚫ Very Dark Blue |

### **Text Colors**

| Color Name                | Hex Code | Usage                               | Preview       |
| ------------------------- | -------- | ----------------------------------- | ------------- |
| `AppColors.textPrimary`   | #FFFFFF  | Primary text, headings              | ⚪ White      |
| `AppColors.textSecondary` | #BBBBBB  | Secondary text, labels              | 🔘 Light Gray |
| `AppColors.textTertiary`  | #888888  | Tertiary text, hints                | ⚫ Gray       |
| `AppColors.textOnPrimary` | #FFFFFF  | Text on primary colored backgrounds | ⚪ White      |

### **Grayscale Palette**

| Color Name          | Hex Code | Usage             |
| ------------------- | -------- | ----------------- |
| `AppColors.white`   | #FFFFFF  | Pure white        |
| `AppColors.black`   | #000000  | Pure black        |
| `AppColors.gray50`  | #FAFAFA  | Lightest gray     |
| `AppColors.gray100` | #F5F5F5  | Very light gray   |
| `AppColors.gray200` | #EEEEEE  | Light gray        |
| `AppColors.gray300` | #E0E0E0  | Medium light gray |
| `AppColors.gray400` | #BDBDBD  | Medium gray       |
| `AppColors.gray500` | #9E9E9E  | True gray         |
| `AppColors.gray600` | #757575  | Medium dark gray  |
| `AppColors.gray700` | #616161  | Dark gray         |
| `AppColors.gray800` | #424242  | Very dark gray    |
| `AppColors.gray900` | #212121  | Darkest gray      |

---

## 🎯 **Action Card Icon Color Mapping**

### **Recommended Icon Colors for Home Screen Action Cards**

| Action Card           | Icon               | Recommended Color      | Hex Code | Rationale                              |
| --------------------- | ------------------ | ---------------------- | -------- | -------------------------------------- |
| **Upload Media**      | 📤 `cloud_upload`  | `AppColors.warning`    | #FFC107  | Amber suggests action/attention needed |
| **My Media**          | 🖼️ `photo_library` | `AppColors.imageColor` | #4CAF50  | Green represents media/images          |
| **Cameras**           | 📹 `videocam`      | `AppColors.videoColor` | #2196F3  | Blue represents video/cameras          |
| **Snapshots**         | 📷 `camera_alt`    | `AppColors.info`       | #2196F3  | Blue for camera-related functionality  |
| **Collections**       | 📁 `collections`   | `AppColors.audioColor` | #9C27B0  | Purple for organization/grouping       |
| **Analytics**         | 📊 `analytics`     | `AppColors.secondary`  | #03DAC6  | Cyan for data/analytics                |
| **Camera Media Sync** | 🔄 `sync`          | `AppColors.success`    | #4CAF50  | Green for successful sync states       |

---

## 📝 **Typography System**

### **Heading Styles**

| Style              | Font Size | Weight | Usage              |
| ------------------ | --------- | ------ | ------------------ |
| `AppTextStyles.h1` | 32px      | Bold   | Page titles        |
| `AppTextStyles.h2` | 28px      | Bold   | Section headers    |
| `AppTextStyles.h3` | 24px      | Bold   | Subsection headers |
| `AppTextStyles.h4` | 20px      | Bold   | Card titles        |
| `AppTextStyles.h5` | 18px      | Bold   | List headers       |
| `AppTextStyles.h6` | 16px      | Bold   | Small headers      |

### **Body Text Styles**

| Style                      | Font Size | Weight  | Usage               |
| -------------------------- | --------- | ------- | ------------------- |
| `AppTextStyles.bodyLarge`  | 16px      | Regular | Primary body text   |
| `AppTextStyles.bodyMedium` | 14px      | Regular | Secondary body text |
| `AppTextStyles.bodySmall`  | 12px      | Regular | Small body text     |

### **Label Styles**

| Style                       | Font Size | Weight | Usage         |
| --------------------------- | --------- | ------ | ------------- |
| `AppTextStyles.labelLarge`  | 14px      | Medium | Button labels |
| `AppTextStyles.labelMedium` | 12px      | Medium | Form labels   |
| `AppTextStyles.labelSmall`  | 11px      | Medium | Small labels  |

### **Utility Styles**

| Style                    | Font Size | Weight  | Usage                     |
| ------------------------ | --------- | ------- | ------------------------- |
| `AppTextStyles.caption`  | 12px      | Regular | Captions, timestamps      |
| `AppTextStyles.overline` | 10px      | Medium  | Overline text, categories |

---

## 📏 **Spacing System**

| Constant         | Value | Usage               |
| ---------------- | ----- | ------------------- |
| `AppSpacing.xs`  | 4px   | Minimal spacing     |
| `AppSpacing.sm`  | 8px   | Small spacing       |
| `AppSpacing.md`  | 16px  | Standard spacing    |
| `AppSpacing.lg`  | 24px  | Large spacing       |
| `AppSpacing.xl`  | 32px  | Extra large spacing |
| `AppSpacing.xxl` | 48px  | Maximum spacing     |

---

## 🔄 **Border Radius System**

| Constant        | Value | Usage             |
| --------------- | ----- | ----------------- |
| `AppRadius.xs`  | 2px   | Minimal rounding  |
| `AppRadius.sm`  | 4px   | Small elements    |
| `AppRadius.md`  | 8px   | Standard elements |
| `AppRadius.lg`  | 12px  | Cards, buttons    |
| `AppRadius.xl`  | 16px  | Large containers  |
| `AppRadius.xxl` | 24px  | Hero elements     |

---

## 🌊 **Shadow System**

| Shadow          | Blur | Offset | Usage               |
| --------------- | ---- | ------ | ------------------- |
| `AppShadows.sm` | 2px  | (0, 1) | Small elevations    |
| `AppShadows.md` | 4px  | (0, 2) | Standard elevations |
| `AppShadows.lg` | 8px  | (0, 4) | High elevations     |

---

## ⏱️ **Animation System**

### **Durations**

| Constant              | Value | Usage               |
| --------------------- | ----- | ------------------- |
| `AppDurations.fast`   | 150ms | Quick interactions  |
| `AppDurations.normal` | 300ms | Standard animations |
| `AppDurations.slow`   | 500ms | Complex transitions |

### **Curves**

| Constant              | Value              | Usage              |
| --------------------- | ------------------ | ------------------ |
| `AppCurves.easeInOut` | `Curves.easeInOut` | Standard easing    |
| `AppCurves.easeIn`    | `Curves.easeIn`    | Entry animations   |
| `AppCurves.easeOut`   | `Curves.easeOut`   | Exit animations    |
| `AppCurves.bounce`    | `Curves.bounceOut` | Playful animations |

---

## 🎨 **Component Styling Guidelines**

### **Action Cards (Home Screen)**

```dart
// Recommended implementation
Icon(
  Icons.cloud_upload,
  size: isCompact ? 36 : 48,
  color: AppColors.warning, // Contextual color
),
```

### **Input Fields**

```dart
InputDecorationTheme(
  filled: true,
  fillColor: AppColors.widgetFill,
  border: OutlineInputBorder(
    borderRadius: BorderRadius.circular(12),
    borderSide: BorderSide(color: AppColors.border),
  ),
)
```

### **Cards**

```dart
Card(
  color: AppColors.surface,
  shape: RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(AppRadius.lg),
  ),
)
```

---

## 🔧 **Utility Methods**

### **Border Decoration**

```dart
AppColors.getOutlineDecoration(
  borderColor: AppColors.border,
  borderRadius: 12.0,
  backgroundColor: AppColors.widgetFill,
)
```

### **Border Side**

```dart
AppColors.getOutlineBorder(
  color: AppColors.border,
)
```

---

## 🌟 **Best Practices**

### **Color Usage Guidelines**

1. **Semantic Colors**: Use status colors (`success`, `warning`, `error`, `info`) for their intended meanings
2. **Contextual Icons**: Match icon colors to their functional context (e.g., green for media, blue for cameras)
3. **Contrast**: Ensure sufficient contrast between text and background colors
4. **Consistency**: Use the same color for similar functions across the platform

### **Typography Guidelines**

1. **Hierarchy**: Maintain clear typographic hierarchy with appropriate font sizes
2. **Line Height**: Use appropriate line heights for readability
3. **Font Weight**: Use bold weights sparingly for emphasis
4. **Color**: Prefer `textPrimary` for main content, `textSecondary` for supporting text

### **Spacing Guidelines**

1. **Consistency**: Use spacing constants rather than arbitrary values
2. **Rhythm**: Maintain consistent vertical rhythm throughout the interface
3. **Responsive**: Adjust spacing appropriately for different screen sizes
4. **Breathing Room**: Provide adequate spacing around interactive elements

---

## 📱 **Responsive Considerations**

### **Mobile Optimizations**

- Reduce icon sizes from 48px to 36px
- Decrease padding from 16px to 12px
- Use smaller font sizes for titles and subtitles
- Maintain touch target sizes of at least 44px

### **Tablet Adaptations**

- Balanced sizing between mobile and desktop
- Optimize for 3-column layouts
- Maintain readability at arm's length

### **Desktop Enhancements**

- Full-size icons and generous spacing
- 4-column layouts for efficient space usage
- Hover states and micro-interactions

---

## 🔮 **Future Enhancements**

### **Planned Color Additions**

- Additional brand color variants
- High contrast mode support
- Light theme color scheme
- Accessibility-focused color options

### **Component Extensions**

- Custom Material 3 component themes
- Advanced animation presets
- Additional utility methods
- Theme switching capabilities

---

**This styling guide serves as the single source of truth for PPL Meta Platform's visual design system. All developers should reference this document when implementing UI components to ensure consistency and brand alignment.**

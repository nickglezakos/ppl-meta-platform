# PPL Meta Frontend Theme Guide

## Overview

This guide explains how the theme system works in the PPL Meta Flutter frontend application and the best practices for implementing and using themes throughout the application.

## Theme Architecture

### Main Theme File

**Location**: `/lib/core/theme/app_theme.dart`

This file serves as the equivalent to a CSS theme template and contains:

- **AppColors**: Comprehensive color palette with Material 3 compatibility
- **AppTextStyles**: Typography definitions using Google Fonts (Roboto)
- **AppSpacing**: Consistent spacing constants
- **AppRadius**: Border radius constants
- **AppShadows**: Box shadow definitions
- **AppDurations & AppCurves**: Animation configurations
- **AppTheme**: Main theme class with dark and light theme configurations

### Theme Variants

- `app_theme_clean.dart` - Minimal Material 3 implementation
- `app_theme_new.dart` - New version variations
- `app_theme_old.dart` - Legacy theme versions

## Implementation Strategy

You have three main approaches for implementing themes in your Flutter application:

### Option 1: Built-in Material 3 Theme (Simple)

Use Flutter's built-in Material 3 theming directly in `main.dart`:

```dart
class PPLMetaApp extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'PPL Meta Platform v2.0.0',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1976D2),
          brightness: Brightness.light,
        ),
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1976D2),
          brightness: Brightness.dark,
        ),
      ),
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
```

**Pros:**
- ✅ Simple setup, no additional files
- ✅ Automatic Material 3 compliance
- ✅ Built-in light/dark mode support
- ✅ Follows Google's design guidelines

**Cons:**
- ❌ Limited customization options
- ❌ No custom utility methods
- ❌ Harder to maintain brand consistency

### Option 2: Custom Theme File (Advanced)

**Import and apply custom theme ONCE in `main.dart`:**

```dart
import 'core/theme/app_theme.dart';

class PPLMetaApp extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'PPL Meta Platform v2.0.0',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
```

**Pros:**
- ✅ Full control over styling
- ✅ Brand-specific colors and spacing
- ✅ Utility methods for consistency
- ✅ Scalable for large projects

**Cons:**
- ❌ More code to maintain
- ❌ Need to ensure Material 3 compliance manually

### Option 3: Hybrid Approach (Recommended)

Extend the built-in Material 3 theme with custom modifications:

```dart
class AppTheme {
  static ThemeData get lightTheme {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF1976D2),
      brightness: Brightness.light,
    );
    
    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      // Extend with custom components
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colorScheme.surfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      cardTheme: CardTheme(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: colorScheme.outline),
        ),
      ),
    );
  }
  
  static ThemeData get darkTheme {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF1976D2),
      brightness: Brightness.dark,
    );
    
    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      // Apply same customizations for dark theme
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colorScheme.surfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      cardTheme: CardTheme(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: colorScheme.outline),
        ),
      ),
    );
  }
}
```

**Pros:**
- ✅ Best of both worlds
- ✅ Material 3 compliance with customization
- ✅ Automatic color generation with brand colors
- ✅ Maintainable and scalable

### ❌ Incorrect Approach: Per-Page Imports

**DO NOT** import the theme file on every page or widget.

## Customizing/Extending Official Material 3 Themes

### Method 1: Using Material Theme Builder

Google's official tool for generating custom Material 3 themes:

1. **Visit**: [Material Theme Builder](https://m3.material.io/theme-builder)
2. **Input**: Upload an image or select colors
3. **Export**: Download as Flutter/Dart code
4. **Implement**:

```dart
// Generated color scheme from Material Theme Builder
static const _brandColor = Color(0xFF1976D2);

static final lightColorScheme = ColorScheme.fromSeed(
  seedColor: _brandColor,
  brightness: Brightness.light,
);

static final darkColorScheme = ColorScheme.fromSeed(
  seedColor: _brandColor,
  brightness: Brightness.dark,
);
```

### Method 2: Custom ColorScheme with Material Base

Extend Material 3 with custom color overrides:

```dart
static final customLightScheme = ColorScheme.fromSeed(
  seedColor: Colors.blue,
  brightness: Brightness.light,
).copyWith(
  // Override specific colors while keeping Material 3 harmony
  primary: const Color(0xFF1976D2),
  secondary: const Color(0xFF03DAC6),
  surface: const Color(0xFFFFFBFE),
  error: const Color(0xFFBA1A1A),
);
```

### Method 3: Component-Level Customization

Customize specific Material components while keeping the base theme:

```dart
static ThemeData get customTheme {
  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
    
    // Customize specific components
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      ),
    ),
    
    inputDecorationTheme: const InputDecorationTheme(
      filled: true,
      border: OutlineInputBorder(),
      contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
    
    cardTheme: CardTheme(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
    ),
  );
}
```

### Method 4: Typography Customization

Extend Material 3 with custom fonts and text styles:

```dart
import 'package:google_fonts/google_fonts.dart';

static ThemeData get customTheme {
  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
    
    // Custom typography
    textTheme: GoogleFonts.robotoTextTheme().copyWith(
      displayLarge: GoogleFonts.roboto(
        fontSize: 57,
        fontWeight: FontWeight.w400,
      ),
      headlineLarge: GoogleFonts.roboto(
        fontSize: 32,
        fontWeight: FontWeight.w500,
      ),
      bodyLarge: GoogleFonts.roboto(
        fontSize: 16,
        fontWeight: FontWeight.w400,
      ),
    ),
  );
}
```

### Method 5: Creating Theme Extensions

For custom properties not covered by Material 3:

```dart
// Define custom theme extension
@immutable
class CustomColors extends ThemeExtension<CustomColors> {
  final Color? brandColor;
  final Color? successColor;
  final Color? warningColor;

  const CustomColors({
    this.brandColor,
    this.successColor,
    this.warningColor,
  });

  @override
  CustomColors copyWith({
    Color? brandColor,
    Color? successColor,
    Color? warningColor,
  }) {
    return CustomColors(
      brandColor: brandColor ?? this.brandColor,
      successColor: successColor ?? this.successColor,
      warningColor: warningColor ?? this.warningColor,
    );
  }

  @override
  CustomColors lerp(ThemeExtension<CustomColors>? other, double t) {
    if (other is! CustomColors) {
      return this;
    }
    return CustomColors(
      brandColor: Color.lerp(brandColor, other.brandColor, t),
      successColor: Color.lerp(successColor, other.successColor, t),
      warningColor: Color.lerp(warningColor, other.warningColor, t),
    );
  }
}

// Use in theme
static ThemeData get extendedTheme {
  return ThemeData(
    useMaterial3: true,
    extensions: <ThemeExtension<dynamic>>[
      const CustomColors(
        brandColor: Color(0xFF1976D2),
        successColor: Color(0xFF4CAF50),
        warningColor: Color(0xFFFFC107),
      ),
    ],
  );
}

// Access in widgets
final customColors = Theme.of(context).extension<CustomColors>();
final brandColor = customColors?.brandColor;
```

### Dynamic Theme Generation

Generate themes based on user preferences or system settings:

```dart
class DynamicTheme {
  static ThemeData generateTheme({
    required Color seedColor,
    required Brightness brightness,
    bool useHighContrast = false,
  }) {
    var colorScheme = ColorScheme.fromSeed(
      seedColor: seedColor,
      brightness: brightness,
    );
    
    // Apply high contrast if needed
    if (useHighContrast) {
      colorScheme = brightness == Brightness.dark
          ? const ColorScheme.highContrastDark()
          : const ColorScheme.highContrastLight();
    }
    
    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      // Add consistent component styling
    );
  }
}
```

### Accessing Theme Values

Once the theme is applied at the app level, access it anywhere using `Theme.of(context)`:

```dart
// Colors from Material 3 color scheme
Container(
  color: Theme.of(context).colorScheme.primary,
  child: Text(
    'Hello World',
    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
      color: Theme.of(context).colorScheme.onPrimary,
    ),
  ),
)
```

### When to Import Theme File Directly

Only import `app_theme.dart` when you need direct access to custom classes:

```dart
import 'package:your_app/core/theme/app_theme.dart';

// Direct access to custom color constants
Container(
  color: AppColors.widgetFill,
  decoration: AppColors.getOutlineDecoration(),
)

// Direct access to spacing constants
Padding(
  padding: EdgeInsets.all(AppSpacing.md),
  child: widget,
)
```

## Best Practices

### 1. Theme Configuration

- ✅ Configure theme once in `main.dart`
- ✅ Use Material 3 compatible color schemes (`useMaterial3: true`)
- ✅ Provide both light and dark theme variants
- ✅ Use consistent naming conventions
- ✅ Consider using `ColorScheme.fromSeed()` for color harmony
- ✅ Test themes with different system settings (high contrast, large text)

### 2. Theme Selection Strategy

**Choose Built-in Material 3 when:**

- Building prototypes or simple apps
- Want automatic Material 3 compliance
- Team prefers minimal theme maintenance
- App follows standard Material Design patterns

**Choose Custom Theme when:**

- Strong brand identity requirements
- Need specific color palettes
- Require custom utility methods
- Large project with complex styling needs

**Choose Hybrid Approach when:**

- Want Material 3 benefits with brand customization
- Need some custom components but not full control
- Want to leverage Material Theme Builder

### 3. Theme Usage

- ✅ Use `Theme.of(context)` to access theme values in widgets
- ✅ Prefer Material 3 color scheme over hardcoded colors
- ✅ Use theme-aware widgets (Card, ElevatedButton, etc.)
- ✅ Access custom extensions with `Theme.of(context).extension<T>()`
- ❌ Don't hardcode colors or styles
- ❌ Don't import theme file unnecessarily
- ❌ Don't override Material 3 semantics without good reason

### 4. Custom Styling

- ✅ Define custom colors, spacing, and styles systematically
- ✅ Use utility methods for consistent decorations
- ✅ Follow Material 3 design guidelines
- ✅ Maintain accessibility standards (contrast ratios, touch targets)
- ✅ Use theme extensions for properties not covered by Material 3
- ✅ Test in both light and dark modes

## Current Theme Features

### Colors

- **Primary Colors**: Material 3 compatible with custom backgrounds
- **Text Colors**: Hierarchical text color system
- **Media Type Colors**: Specific colors for different media types
- **Upload State Colors**: Visual feedback for upload operations
- **Utility Colors**: Gray scale and semantic colors

### Components

- **Input Fields**: Consistent styling with outline borders
- **Buttons**: Elevated, outlined, and text button themes
- **Cards**: Outlined cards with consistent elevation
- **Dialogs**: Themed dialog boxes with proper contrast
- **Navigation**: App bar and navigation component styling

### Typography

- **Google Fonts**: Roboto font family
- **Text Styles**: Hierarchical text styles (h1-h6, body, label, caption)
- **Responsive**: Appropriate font sizes for different screen sizes

## Migration Notes

If updating from older theme systems:

1. Replace direct color references with `Theme.of(context).colorScheme.*`
2. Use theme-aware widgets instead of custom styled containers
3. Remove redundant theme imports from individual files
4. Update custom widgets to respect theme changes

## Troubleshooting

### Theme Not Applied

- Ensure theme is imported in `main.dart`
- Check that `MaterialApp.router` or `MaterialApp` has theme property set
- Verify theme mode is correctly configured

### Colors Not Updating

- Use `Theme.of(context)` instead of hardcoded values
- Rebuild widgets when theme changes
- Check if custom colors override theme colors

### Inconsistent Styling

- Use theme constants instead of magic numbers
- Follow Material 3 design tokens
- Test in both light and dark modes

## Future Considerations

- **Theme Switching**: Implement dynamic theme switching capability
- **Material Theme Builder Integration**: Automate theme generation from design tokens
- **Custom Themes**: Support for user-customizable themes with theme extensions
- **Accessibility**: Enhanced high contrast and large text support
- **Brand Themes**: Multiple brand color scheme support
- **Dynamic Color**: Android 12+ system color integration
- **Theme Analytics**: Track which themes users prefer
- **Performance**: Optimize theme switching animations and rebuilds

## Official Resources

- **Material Design 3**: [https://m3.material.io/](https://m3.material.io/)
- **Material Theme Builder**: [https://m3.material.io/theme-builder](https://m3.material.io/theme-builder)
- **Flutter Theming Guide**: [https://docs.flutter.dev/ui/design/themes](https://docs.flutter.dev/ui/design/themes)
- **ColorScheme Documentation**: [https://api.flutter.dev/flutter/material/ColorScheme-class.html](https://api.flutter.dev/flutter/material/ColorScheme-class.html)
- **ThemeData Documentation**: [https://api.flutter.dev/flutter/material/ThemeData-class.html](https://api.flutter.dev/flutter/material/ThemeData-class.html)

---

**Last Updated**: August 22, 2025  
**Version**: 2.1.0  
**Maintainer**: PPL Meta Development Team

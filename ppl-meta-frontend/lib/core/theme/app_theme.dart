import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Custom color palette for PPL Meta platform
class AppColors {
  // Primary colors (Material 3 compatible)
  static const Color primary = Color(0xFF1976D2);
  static const Color secondary = Color(0xFF03DAC6);
  static const Color accent = Color(0xFF03DAC6);
  static const Color surface = Color(0xFF061d36);
  static const Color surfaceVariant = Color(0xFF0c2942);
  static const Color background = Color(0xFF061d36);
  static const Color widgetFill = Color(0xFF041121);
  static const Color error = Color(0xFFCF6679);
  static const Color success = Color(0xFF4CAF50);
  static const Color warning = Color(0xFFFFC107);
  static const Color info = Color(0xFF2196F3);
  
  // Text colors
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFBBBBBB);
  static const Color textTertiary = Color(0xFF888888);
  static const Color textOnPrimary = Color(0xFFFFFFFF);
  
  // Media type colors
  static const Color imageColor = Color(0xFF4CAF50);
  static const Color videoColor = Color(0xFF2196F3);
  static const Color audioColor = Color(0xFF9C27B0);
  static const Color documentColor = Color(0xFF795548);
  
  // Upload state colors
  static const Color uploadPending = Color(0xFFFFC107);
  static const Color uploadInProgress = Color(0xFF2196F3);
  static const Color uploadCompleted = Color(0xFF4CAF50);
  static const Color uploadFailed = Color(0xFFCF6679);
  
  // Gray scale
  static const Color white = Color(0xFFFFFFFF);
  static const Color black = Color(0xFF000000);
  static const Color gray50 = Color(0xFFFAFAFA);
  static const Color gray100 = Color(0xFFF5F5F5);
  static const Color gray200 = Color(0xFFEEEEEE);
  static const Color gray300 = Color(0xFFE0E0E0);
  static const Color gray400 = Color(0xFFBDBDBD);
  static const Color gray500 = Color(0xFF9E9E9E);
  static const Color gray600 = Color(0xFF757575);
  static const Color gray700 = Color(0xFF616161);
  static const Color gray800 = Color(0xFF424242);
  static const Color gray900 = Color(0xFF212121);
  
  // Border color
  static const Color border = Color(0xFF0c2942);
  
  // Utility method to get consistent border decoration
  static BoxDecoration getOutlineDecoration({
    Color? borderColor,
    double borderRadius = 12.0,
    Color? backgroundColor,
  }) {
    return BoxDecoration(
      color: backgroundColor ?? widgetFill,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(
        color: borderColor ?? border,
        width: 1.0,
      ),
    );
  }
  
  // Utility method to get consistent border side
  static BorderSide getOutlineBorder({Color? color}) {
    return BorderSide(
      color: color ?? border,
      width: 1.0,
    );
  }
}

/// Typography styles
class AppTextStyles {
  static final h1 = GoogleFonts.roboto(fontSize: 32, fontWeight: FontWeight.bold);
  static final h2 = GoogleFonts.roboto(fontSize: 28, fontWeight: FontWeight.bold);
  static final h3 = GoogleFonts.roboto(fontSize: 24, fontWeight: FontWeight.bold);
  static final h4 = GoogleFonts.roboto(fontSize: 20, fontWeight: FontWeight.bold);
  static final h5 = GoogleFonts.roboto(fontSize: 18, fontWeight: FontWeight.bold);
  static final h6 = GoogleFonts.roboto(fontSize: 16, fontWeight: FontWeight.bold);
  
  static final bodyLarge = GoogleFonts.roboto(fontSize: 16);
  static final bodyMedium = GoogleFonts.roboto(fontSize: 14);
  static final bodySmall = GoogleFonts.roboto(fontSize: 12);
  
  static final labelLarge = GoogleFonts.roboto(fontSize: 14, fontWeight: FontWeight.w500);
  static final labelMedium = GoogleFonts.roboto(fontSize: 12, fontWeight: FontWeight.w500);
  static final labelSmall = GoogleFonts.roboto(fontSize: 11, fontWeight: FontWeight.w500);
  
  static final caption = GoogleFonts.roboto(fontSize: 12);
  static final overline = GoogleFonts.roboto(fontSize: 10, letterSpacing: 1.2, fontWeight: FontWeight.w500);
}

/// Spacing constants
class AppSpacing {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;
}

/// Border radius constants
class AppRadius {
  static const double xs = 2.0;
  static const double sm = 4.0;
  static const double md = 8.0;
  static const double lg = 12.0;
  static const double xl = 16.0;
  static const double xxl = 24.0;
}

/// Box shadow constants
class AppShadows {
  static const BoxShadow sm = BoxShadow(
    color: Color(0x1A000000),
    blurRadius: 2,
    offset: Offset(0, 1),
  );
  static const BoxShadow md = BoxShadow(
    color: Color(0x1A000000),
    blurRadius: 4,
    offset: Offset(0, 2),
  );
  static const BoxShadow lg = BoxShadow(
    color: Color(0x1A000000),
    blurRadius: 8,
    offset: Offset(0, 4),
  );
}

/// Animation durations
class AppDurations {
  static const Duration fast = Duration(milliseconds: 150);
  static const Duration normal = Duration(milliseconds: 300);
  static const Duration slow = Duration(milliseconds: 500);
}

/// Animation curves
class AppCurves {
  static const Curve easeInOut = Curves.easeInOut;
  static const Curve easeIn = Curves.easeIn;
  static const Curve easeOut = Curves.easeOut;
  static const Curve bounce = Curves.bounceOut;
}

/// Main theme class with Material 3 support
class AppTheme {
  // Use Material 3's official dark color scheme with custom background
  static final ColorScheme _darkColorScheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    brightness: Brightness.dark,
  ).copyWith(
    background: AppColors.background,
    surface: AppColors.surface,
    surfaceVariant: AppColors.surfaceVariant,
  );

  static final ColorScheme _lightColorScheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    brightness: Brightness.light,
  );

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: _darkColorScheme,
      textTheme: GoogleFonts.robotoTextTheme(
        ThemeData.dark().textTheme,
      ),
      // Clean Material 3 input styling with proper dark theme colors
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.widgetFill,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _darkColorScheme.outline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _darkColorScheme.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _darkColorScheme.primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        // Ensure text is visible in dark mode
        labelStyle: TextStyle(color: _darkColorScheme.onSurfaceVariant),
        hintStyle: TextStyle(color: _darkColorScheme.onSurfaceVariant.withOpacity(0.6)),
      ),
      // Card theme with outline
      cardTheme: CardThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: _darkColorScheme.outline),
        ),
        elevation: 0,
        color: AppColors.widgetFill,
      ),
      // Elevated button theme with outline
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: _darkColorScheme.outline),
          ),
          backgroundColor: AppColors.widgetFill,
          foregroundColor: _darkColorScheme.onSurface,
          elevation: 0,
        ),
      ),
      // Outlined button theme
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          side: BorderSide(color: _darkColorScheme.outline),
          foregroundColor: _darkColorScheme.onSurface,
        ),
      ),
      // Text button theme with subtle outline
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: _darkColorScheme.outline.withOpacity(0.5)),
          ),
          foregroundColor: _darkColorScheme.onSurface,
        ),
      ),
      // Container decoration theme
      dividerTheme: DividerThemeData(
        color: _darkColorScheme.outline,
        thickness: 1,
      ),
      // Dialog theme with outline
      dialogTheme: DialogThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: _darkColorScheme.outline),
        ),
        backgroundColor: AppColors.widgetFill,
        elevation: 0,
      ),
      // Bottom sheet theme with outline
      bottomSheetTheme: BottomSheetThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
          side: BorderSide(color: _darkColorScheme.outline),
        ),
        backgroundColor: AppColors.widgetFill,
        elevation: 0,
      ),
      // App bar theme without outline
      appBarTheme: AppBarTheme(
        backgroundColor: _darkColorScheme.surface,
        foregroundColor: _darkColorScheme.onSurface,
        elevation: 0,
      ),
            // List tile theme with consistent styling
      listTileTheme: ListTileThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: _darkColorScheme.outline.withOpacity(0.3)),
        ),
        tileColor: AppColors.widgetFill,
      ),
      // Floating action button theme with outline
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: AppColors.widgetFill,
        foregroundColor: _darkColorScheme.onSurface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: _darkColorScheme.outline),
        ),
      ),
      // Popup menu theme with consistent styling
      popupMenuTheme: PopupMenuThemeData(
        color: AppColors.widgetFill,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: _darkColorScheme.outline),
        ),
        elevation: 0,
        textStyle: TextStyle(color: _darkColorScheme.onSurface),
        // Remove outlines from individual menu items
        menuPadding: EdgeInsets.zero,
      ),
      // Menu theme for dropdown menus
      menuTheme: MenuThemeData(
        style: MenuStyle(
          backgroundColor: WidgetStateProperty.all(AppColors.widgetFill),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: _darkColorScheme.outline),
            ),
          ),
          elevation: WidgetStateProperty.all(0),
        ),
      ),
      // Dropdown menu theme
      dropdownMenuTheme: DropdownMenuThemeData(
        menuStyle: MenuStyle(
          backgroundColor: WidgetStateProperty.all(AppColors.widgetFill),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: _darkColorScheme.outline),
            ),
          ),
          elevation: WidgetStateProperty.all(0),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: AppColors.widgetFill,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: _darkColorScheme.outline),
          ),
        ),
      ),
    );
  }

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: _lightColorScheme,
      textTheme: GoogleFonts.robotoTextTheme(
        ThemeData.light().textTheme,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: _lightColorScheme.surfaceContainer,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _lightColorScheme.outline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _lightColorScheme.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _lightColorScheme.primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        labelStyle: TextStyle(color: _lightColorScheme.onSurfaceVariant),
        hintStyle: TextStyle(color: _lightColorScheme.onSurfaceVariant.withOpacity(0.6)),
      ),
    );
  }
}

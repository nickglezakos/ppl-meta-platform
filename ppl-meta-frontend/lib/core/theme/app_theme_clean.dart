import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Official Material 3 Dark Theme Implementation
class AppTheme {
  // Use Material 3's official dark color scheme
  static final ColorScheme _darkColorScheme = ColorScheme.fromSeed(
    seedColor: Colors.blue,
    brightness: Brightness.dark,
  );

  static final ColorScheme _lightColorScheme = ColorScheme.fromSeed(
    seedColor: Colors.blue,
    brightness: Brightness.light,
  );

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: _darkColorScheme,
      textTheme: GoogleFonts.robotoTextTheme(
        ThemeData.dark().textTheme,
      ),
      // Let Material 3 handle all input styling automatically
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: _darkColorScheme.surfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
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
        fillColor: _lightColorScheme.surfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),
    );
  }
}

import 'package:flutter/material.dart';

/// Offline-safe font utilities to replace GoogleFonts during development
class OfflineFonts {
  /// Returns a TextStyle with Roboto font (using built-in Roboto)
  static TextStyle roboto({
    double? fontSize,
    FontWeight? fontWeight,
    Color? color,
    double? letterSpacing,
    double? wordSpacing,
    TextDecoration? decoration,
    double? height,
  }) {
    return TextStyle(
      fontFamily: 'Roboto',
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      letterSpacing: letterSpacing,
      wordSpacing: wordSpacing,
      decoration: decoration,
      height: height,
    );
  }

  /// Returns a TextStyle with Inter font (using built-in Roboto as fallback)
  static TextStyle inter({
    double? fontSize,
    FontWeight? fontWeight,
    Color? color,
    double? letterSpacing,
    double? wordSpacing,
    TextDecoration? decoration,
    double? height,
  }) {
    return TextStyle(
      fontFamily: 'Roboto', // Using Roboto as fallback for Inter
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      letterSpacing: letterSpacing,
      wordSpacing: wordSpacing,
      decoration: decoration,
      height: height,
    );
  }

  /// Returns a TextTheme with Roboto font applied to all text styles
  static TextTheme robotoTextTheme(TextTheme base) {
    return base.apply(
      fontFamily: 'Roboto',
    );
  }
}

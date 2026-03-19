import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Service for managing app-wide developer and marketing settings
class DeveloperSettingsService extends ChangeNotifier {
  static const String _keyScreenshotFabEnabled = 'dev_screenshot_fab_enabled';
  
  static final DeveloperSettingsService _instance = DeveloperSettingsService._internal();
  factory DeveloperSettingsService() => _instance;
  DeveloperSettingsService._internal();

  bool _screenshotFabEnabled = false;
  bool _isInitialized = false;

  bool get screenshotFabEnabled => _screenshotFabEnabled;
  bool get isInitialized => _isInitialized;

  /// Initialize settings from persistent storage
  Future<void> initialize() async {
    if (_isInitialized) return;
    
    try {
      final prefs = await SharedPreferences.getInstance();
      _screenshotFabEnabled = prefs.getBool(_keyScreenshotFabEnabled) ?? false;
      _isInitialized = true;
      notifyListeners();
    } catch (e) {
      print('Error loading developer settings: $e');
      _isInitialized = true;
    }
  }

  /// Enable or disable the screenshot FAB
  Future<void> setScreenshotFabEnabled(bool enabled) async {
    _screenshotFabEnabled = enabled;
    notifyListeners();
    
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_keyScreenshotFabEnabled, enabled);
      print('📸 Screenshot FAB ${enabled ? "enabled" : "disabled"}');
    } catch (e) {
      print('Error saving screenshot FAB setting: $e');
    }
  }

  /// Toggle the screenshot FAB setting
  Future<void> toggleScreenshotFab() async {
    await setScreenshotFabEnabled(!_screenshotFabEnabled);
  }
}

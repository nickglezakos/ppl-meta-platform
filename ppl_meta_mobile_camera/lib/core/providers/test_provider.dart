import 'package:flutter/foundation.dart';

/// Test provider to check imports
class TestProvider extends ChangeNotifier {
  bool _isConnected = false;
  
  bool get isConnected => _isConnected;
  
  void setConnected(bool connected) {
    _isConnected = connected;
    notifyListeners();
  }
}

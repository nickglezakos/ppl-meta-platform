/// Stub implementation for web platform
class Platform {
  static bool get isAndroid => false;
  static bool get isMacOS => false;
  static bool get isIOS => false;
  static bool get isWindows => false;
  static bool get isLinux => false;
}

class NetworkInterface {
  static Future<List<NetworkInterface>> list() async => [];
  List<InternetAddress> get addresses => [];
}

class InternetAddress {
  InternetAddressType get type => InternetAddressType.IPv4;
  bool get isLoopback => true;
  String get address => '127.0.0.1';
}

enum InternetAddressType {
  IPv4,
  IPv6,
}

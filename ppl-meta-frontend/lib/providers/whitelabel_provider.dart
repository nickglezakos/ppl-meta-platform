import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api/api_client.dart';

/// Holds the whitelabel state: custom logo bytes + punchline text.
class WhitelabelState {
  final Uint8List? logoBytes;
  final String punchline;

  const WhitelabelState({this.logoBytes, this.punchline = ''});

  WhitelabelState copyWith({Uint8List? logoBytes, String? punchline}) {
    return WhitelabelState(
      logoBytes: logoBytes ?? this.logoBytes,
      punchline: punchline ?? this.punchline,
    );
  }
}

/// Provider for whitelabel customisations (logo + punchline).
final whitelabelProvider = StateNotifierProvider<WhitelabelNotifier, AsyncValue<WhitelabelState>>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WhitelabelNotifier(apiClient);
});

/// Keeps the previous logo-only provider for backward compatibility with AppLogo.
final whitelabelLogoProvider = Provider<AsyncValue<Uint8List?>>((ref) {
  final state = ref.watch(whitelabelProvider);
  return state.when(
    data: (ws) => AsyncValue.data(ws.logoBytes),
    loading: () => const AsyncValue.loading(),
    error: (e, st) => AsyncValue.error(e, st),
  );
});

class WhitelabelNotifier extends StateNotifier<AsyncValue<WhitelabelState>> {
  final ApiClient _apiClient;
  static const String _logoSettingKey = 'whitelabel_logo';
  static const String _punchlineSettingKey = 'whitelabel_punchline';
  static const String _defaultPunchline = 'Welcome to Eyenet Vision';

  WhitelabelNotifier(this._apiClient) : super(const AsyncValue.loading()) {
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        _loadSetting(_logoSettingKey),
        _loadSetting(_punchlineSettingKey),
      ]);
      final logoValue = results[0];
      final punchlineValue = results[1];

      Uint8List? logoBytes;
      if (logoValue != null && logoValue.isNotEmpty) {
        logoBytes = base64Decode(logoValue);
      }

      final punchline = (punchlineValue != null && punchlineValue.isNotEmpty)
          ? punchlineValue
          : _defaultPunchline;

      state = AsyncValue.data(WhitelabelState(logoBytes: logoBytes, punchline: punchline));
    } on Exception catch (e, stack) {
      state = AsyncValue.data(const WhitelabelState());
    }
  }

  Future<String?> _loadSetting(String key) async {
    try {
      final response = await _apiClient.get('/api/v1/settings/$key');
      return response.data['value']?.toString();
    } on Exception {
      return null;
    }
  }

  Future<void> _saveSetting(String key, String value) async {
    await _apiClient.post('/api/v1/settings/', data: {
      'key': key,
      'value': value,
    });
  }

  /// Upload a custom logo.
  Future<void> uploadLogo(Uint8List imageBytes) async {
    final current = state.valueOrNull ?? const WhitelabelState();
    state = AsyncValue.data(current.copyWith(logoBytes: imageBytes));
    try {
      final base64String = base64Encode(imageBytes);
      await _saveSetting(_logoSettingKey, base64String);
      state = AsyncValue.data(current.copyWith(logoBytes: imageBytes));
    } on Exception catch (e, stack) {
      state = AsyncValue.data(current);
      rethrow;
    }
  }

  /// Reset logo to default.
  Future<void> resetLogo() async {
    final current = state.valueOrNull ?? const WhitelabelState();
    final newState = current.copyWith(logoBytes: null);
    state = AsyncValue.data(newState);
    try {
      await _saveSetting(_logoSettingKey, '');
    } on Exception {
      // best effort
    }
  }

  /// Update the punchline.
  Future<void> updatePunchline(String punchline) async {
    final current = state.valueOrNull ?? const WhitelabelState();
    final trimmed = punchline.trim();
    if (trimmed.isEmpty) return;
    state = AsyncValue.data(current.copyWith(punchline: trimmed));
    try {
      await _saveSetting(_punchlineSettingKey, trimmed);
    } on Exception {
      state = AsyncValue.data(current);
    }
  }

  /// Reset punchline to default.
  Future<void> resetPunchline() async {
    final current = state.valueOrNull ?? const WhitelabelState();
    final newState = current.copyWith(punchline: _defaultPunchline);
    state = AsyncValue.data(newState);
    try {
      await _saveSetting(_punchlineSettingKey, '');
    } on Exception {
      // best effort
    }
  }

  Future<void> refresh() async {
    await _load();
  }
}
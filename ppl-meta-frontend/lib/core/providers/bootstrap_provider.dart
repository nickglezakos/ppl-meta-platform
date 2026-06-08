import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';

class BootstrapOwnerStatus {
  final String? approvedOwnerEmail;
  final bool localUserExists;
  final bool localOwnerRolePresent;

  const BootstrapOwnerStatus({
    required this.approvedOwnerEmail,
    required this.localUserExists,
    required this.localOwnerRolePresent,
  });

  factory BootstrapOwnerStatus.fromJson(Map<String, dynamic> json) {
    return BootstrapOwnerStatus(
      approvedOwnerEmail: json['approved_owner_email'] as String?,
      localUserExists: json['local_user_exists'] == true,
      localOwnerRolePresent: json['local_owner_role_present'] == true,
    );
  }
}

class BootstrapStatus {
  final String state;
  final bool complete;
  final bool authorityConfigured;
  final bool applicationKeyConfigured;
  final BootstrapOwnerStatus owner;

  const BootstrapStatus({
    required this.state,
    required this.complete,
    required this.authorityConfigured,
    required this.applicationKeyConfigured,
    required this.owner,
  });

  bool get needsOwnerBootstrap => !complete && state != 'bootstrap_complete';

  factory BootstrapStatus.fromJson(Map<String, dynamic> json) {
    final bootstrap = (json['bootstrap'] as Map<String, dynamic>? ?? const {});
    final authority = (bootstrap['authority'] as Map<String, dynamic>? ?? const {});
    final installation = (bootstrap['installation'] as Map<String, dynamic>? ?? const {});
    final owner = (bootstrap['owner'] as Map<String, dynamic>? ?? const {});

    return BootstrapStatus(
      state: bootstrap['state'] as String? ?? 'not_started',
      complete: bootstrap['complete'] == true,
      authorityConfigured: authority['configured'] == true,
      applicationKeyConfigured: installation['application_key_configured'] == true,
      owner: BootstrapOwnerStatus.fromJson(owner),
    );
  }
}

final bootstrapStatusProvider = FutureProvider<BootstrapStatus>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get(
    '/api/v1/licensing/bootstrap/status',
    options: Options(extra: const {
      'skipAuthHeader': true,
      'skipAuthRecovery': true,
    }),
  );

  return BootstrapStatus.fromJson(response.data ?? const {});
});
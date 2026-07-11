import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/authority_status_providers.dart';
import '../services/authority_status_client.dart';

class AuthorityStatusCard extends ConsumerWidget {
  final bool showAdminDetails;

  const AuthorityStatusCard({
    super.key,
    this.showAdminDetails = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authorityStatus = ref.watch(authorityStatusProvider);

    return authorityStatus.when(
      data: (status) => _AuthorityStatusContent(
        status: status,
        showAdminDetails: showAdminDetails,
        onRefresh: () => ref.invalidate(authorityStatusProvider),
      ),
      loading: () => const Card(
        child: ListTile(
          leading: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          title: Text('Checking authority status'),
          subtitle: Text('Loading owner and licence state...'),
        ),
      ),
      error: (error, _) => Card(
        child: ListTile(
          leading: const Icon(Icons.error_outline, color: Colors.orange),
          title: const Text('Authority status unavailable'),
          subtitle: Text(error.toString()),
          trailing: IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(authorityStatusProvider),
          ),
        ),
      ),
    );
  }
}

class _AuthorityStatusContent extends StatelessWidget {
  final AuthorityStatus status;
  final bool showAdminDetails;
  final VoidCallback onRefresh;

  const _AuthorityStatusContent({
    required this.status,
    required this.showAdminDetails,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final summary = _buildSummary();
    final isApprovedOwner = status.currentUserIsApprovedOwner;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(summary.icon, color: summary.color),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Authority Status',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        summary.title,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: summary.color,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: onRefresh,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(summary.subtitle, style: theme.textTheme.bodyMedium),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _buildChip(
                  label: isApprovedOwner ? 'You are the approved owner' : 'Current user is not the approved owner',
                  color: isApprovedOwner ? Colors.green : Colors.blueGrey,
                ),
                if (status.cachedLicenceStatus != null)
                  _buildChip(
                    label: 'Licence: ${status.cachedLicenceStatus}',
                    color: _licenceColor(status.cachedLicenceStatus),
                  ),
                if (status.cachedLicenceName != null && status.cachedLicenceName!.isNotEmpty)
                  _buildChip(
                    label: status.cachedLicenceName!,
                    color: Colors.indigo,
                  ),
                if (status.cachedTenantName != null && status.cachedTenantName!.isNotEmpty)
                  _buildChip(
                    label: 'Tenant: ${status.cachedTenantName}',
                    color: Colors.cyan,
                  ),
                if (status.isWarningActive)
                  _buildChip(
                    label: status.warningDaysRemaining != null
                        ? 'Warning: ${status.warningDaysRemaining} day(s) remaining'
                        : 'Warning period active',
                    color: Colors.amber,
                  ),
                if (status.isSafeguardActive)
                  _buildChip(
                    label: 'Safeguard active',
                    color: Colors.red,
                  ),
                if (status.isOfflineCached)
                  _buildChip(
                    label: 'Running from cached approval',
                    color: Colors.orange,
                  ),
                if (status.cacheWithinGrace)
                  _buildChip(
                    label: 'Within offline grace window',
                    color: Colors.teal,
                  ),
              ],
            ),
            if (showAdminDetails) ...[
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 8),
              // VPN Mesh section
              Row(
                children: [
                  Icon(status.vpnEnrolled ? Icons.vpn_lock : Icons.vpn_lock_outlined,
                    color: status.vpnEnrolled ? Colors.green : Colors.grey,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    status.vpnEnrolled ? 'VPN Mesh Active' : 'VPN Not Enrolled',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: status.vpnEnrolled ? Colors.green : Colors.grey,
                    ),
                  ),
                ],
              ),
              if (status.matrixGroupId != null && status.matrixGroupId!.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  'Matrix: ${status.matrixGroupId!.substring(0, 12)}...',
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
                ),
                const SizedBox(height: 2),
                Text(
                  'Server: ${status.headscaleServer ?? "vpn.eyenet-vision.com"}',
                  style: const TextStyle(fontSize: 11, color: Colors.grey),
                ),
              ],
              const SizedBox(height: 12),
              _DetailRow(label: 'Authority enabled', value: _boolLabel(status.enabled)),
              _DetailRow(label: 'Authority configured', value: _boolLabel(status.configured)),
              _DetailRow(
                label: 'Application key configured',
                value: _boolLabel(status.applicationKeyConfigured),
              ),
              _DetailRow(
                label: 'Authority key state',
                value: status.applicationKeyConfigured
                    ? 'Active and managed by Authority'
                    : 'Not configured',
              ),
              _DetailRow(
                label: 'Cached owner email',
                value: status.cachedOwnerEmail ?? 'Unavailable',
              ),
              _DetailRow(
                label: 'Licence name',
                value: status.cachedLicenceName ?? 'Unavailable',
              ),
              _DetailRow(
                label: 'Tenant name',
                value: status.cachedTenantName ?? 'Unavailable',
              ),
              _DetailRow(
                label: 'Current user approved owner',
                value: _boolLabel(status.currentUserIsApprovedOwner),
              ),
              _DetailRow(
                label: 'Owner enabled',
                value: status.cachedOwnerEnabled == null
                    ? 'Unknown'
                    : _boolLabel(status.cachedOwnerEnabled!),
              ),
              _DetailRow(
                label: 'Runtime state',
                value: status.runtimeState,
              ),
              _DetailRow(
                label: 'Runtime reason',
                value: status.runtimeReason ?? 'Unavailable',
              ),
              _DetailRow(
                label: 'Can operate',
                value: _boolLabel(status.canOperate),
              ),
              _DetailRow(
                label: 'Warning period days',
                value: status.warningPeriodDays?.toString() ?? 'Unavailable',
              ),
              _DetailRow(
                label: 'Warning started',
                value: _formatDateTime(status.warningStartedAt),
              ),
              _DetailRow(
                label: 'Warning deadline',
                value: _formatDateTime(status.warningDeadline),
              ),
              _DetailRow(
                label: 'Warning days remaining',
                value: status.warningDaysRemaining?.toString() ?? 'Unavailable',
              ),
              _DetailRow(
                label: 'Last result',
                value: status.lastResultReason ?? 'Unavailable',
              ),
              _DetailRow(
                label: 'Last checked',
                value: _formatDateTime(status.lastCheckedAt),
              ),
              _DetailRow(
                label: 'Last successful check',
                value: _formatDateTime(status.lastSuccessfulCheckAt),
              ),
              _DetailRow(
                label: 'Offline grace days',
                value: status.offlineGraceDays?.toString() ?? 'Unavailable',
              ),
              _DetailRow(
                label: 'Cache expires',
                value: _formatDateTime(status.cacheExpiresAt),
              ),
              _DetailRow(
                label: 'Installation UUID',
                value: status.installationUuid.isEmpty ? 'Unavailable' : status.installationUuid,
              ),
              _DetailRow(
                label: 'Resolved installation UUID',
                value: status.resolvedInstallationUuid?.isNotEmpty == true
                    ? status.resolvedInstallationUuid!
                    : 'Unavailable',
              ),
              _DetailRow(
                label: 'Authority service URL',
                value: status.serviceUrl.isEmpty ? 'Unavailable' : status.serviceUrl,
              ),
            ],
          ],
        ),
      ),
    );
  }

  _AuthoritySummary _buildSummary() {
    if (!status.enabled) {
      return const _AuthoritySummary(
        title: 'Authority integration disabled',
        subtitle: 'This environment is using local behavior without remote authority enforcement.',
        color: Colors.blueGrey,
        icon: Icons.toggle_off,
      );
    }
    if (!status.configured) {
      return const _AuthoritySummary(
        title: 'Authority not configured',
        subtitle: 'The frontend is authenticated, but Node does not have a complete authority configuration.',
        color: Colors.orange,
        icon: Icons.settings_input_component,
      );
    }
    if (status.isSafeguardActive) {
      return const _AuthoritySummary(
        title: 'Safeguard active',
        subtitle: 'Protected operations are blocked until the licence state is resolved in Authority.',
        color: Colors.red,
        icon: Icons.gpp_bad,
      );
    }
    if (status.isWarningActive) {
      return _AuthoritySummary(
        title: 'Licence warning active',
        subtitle: status.warningDaysRemaining != null
            ? 'Resolve the licence in Authority within ${status.warningDaysRemaining} day(s) to avoid safeguard mode.'
            : 'Resolve the licence in Authority before the warning period elapses.',
        color: Colors.amber,
        icon: Icons.warning_amber,
      );
    }
    if (status.isOfflineCached) {
      return const _AuthoritySummary(
        title: 'Offline grace mode active',
        subtitle: 'Node is preserving owner approval from the cached authority record.',
        color: Colors.orange,
        icon: Icons.cloud_off,
      );
    }
    if (status.cachedOwnerEnabled == false) {
      return const _AuthoritySummary(
        title: 'Owner approval disabled',
        subtitle: 'The authority record is reachable but owner access is currently disabled.',
        color: Colors.red,
        icon: Icons.block,
      );
    }
    return const _AuthoritySummary(
      title: 'Authority connected',
      subtitle: 'Node is receiving active authority state from the remote owner service.',
      color: Colors.green,
      icon: Icons.verified_user,
    );
  }

  Widget _buildChip({required String label, required Color color}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 12),
      ),
    );
  }

  String _boolLabel(bool value) => value ? 'Yes' : 'No';

  String _formatDateTime(DateTime? value) {
    if (value == null) {
      return 'Unavailable';
    }
    final localValue = value.toLocal();
    String twoDigits(int number) => number.toString().padLeft(2, '0');
    return '${localValue.year}-${twoDigits(localValue.month)}-${twoDigits(localValue.day)} '
        '${twoDigits(localValue.hour)}:${twoDigits(localValue.minute)}';
  }

  Color _licenceColor(String? licenceStatus) {
    switch (licenceStatus) {
      case 'active':
        return Colors.green;
      case 'grace':
        return Colors.orange;
      case 'expired':
      case 'disabled':
        return Colors.red;
      default:
        return Colors.blueGrey;
    }
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 150,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}

class _AuthoritySummary {
  final String title;
  final String subtitle;
  final Color color;
  final IconData icon;

  const _AuthoritySummary({
    required this.title,
    required this.subtitle,
    required this.color,
    required this.icon,
  });
}
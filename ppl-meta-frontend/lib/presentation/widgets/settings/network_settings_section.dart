import 'dart:async';

import 'package:flutter/foundation.dart' show defaultTargetPlatform;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../services/discovery_service_client.dart';
import '../../../services/dynamic_service_provider.dart';
import '../../../services/vpn_status_client.dart';
import '../../../core/api/api_client.dart';
import '../../../core/config/app_config.dart';
import '../../../core/theme/app_theme.dart';

/// Provider for fetching discovery services
final discoveryServicesProvider = FutureProvider<DiscoveryResponse>((ref) async {
  final discoveryClient = ref.watch(discoveryServiceProvider);
  return await discoveryClient.discoverServices();
});

/// Provider for fetching VPN peers from the authority API
final vpnPeersProvider = FutureProvider<List<VpnPeerInfo>>((ref) async {
  final client = ref.watch(vpnStatusClientProvider);
  return await client.fetchPeers();
});

class NetworkSettingsSection extends ConsumerWidget {
  const NetworkSettingsSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final discoveryState = ref.watch(discoveryServicesProvider);
    final vpnStatusAsync = ref.watch(vpnStatusProvider);
    final vpnIp = vpnStatusAsync.valueOrNull?.tailscaleIp;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeader(),
          const SizedBox(height: 16),
          _buildVpnStatusCard(),
          const SizedBox(height: 16),
          const _VpnPeersCard(),
          const SizedBox(height: 16),
          _buildDiscoveryStatus(context, discoveryState),
          const SizedBox(height: 24),
          _buildServicesTable(context, discoveryState, vpnIp),
        ],
      ),
    );
  }

  Widget _buildSectionHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Icon(Icons.network_check, color: AppColors.primary, size: 20),
          const SizedBox(width: 12),
          const Text('Network & Services', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
        ],
      ),
    );
  }

  Widget _buildDiscoveryStatus(BuildContext context, AsyncValue<DiscoveryResponse> discoveryState) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.border)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [Icon(Icons.router, color: AppColors.secondary, size: 20), const SizedBox(width: 8), const Text('Discovery Service Status', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500, color: AppColors.textPrimary))]),
          const SizedBox(height: 12),
          discoveryState.when(
            data: (response) => _buildSuccessStatus(response),
            loading: () => _buildLoadingStatus(),
            error: (error, stack) => _buildErrorStatus(error),
          ),
        ],
      ),
    );
  }

  Widget _buildSuccessStatus(DiscoveryResponse response) {
    return Row(children: [
      Container(width: 8, height: 8, decoration: const BoxDecoration(color: AppColors.success, shape: BoxShape.circle)),
      const SizedBox(width: 8),
      Text('Connected - ${response.services.length} services discovered', style: const TextStyle(color: AppColors.success, fontWeight: FontWeight.w500)),
    ]);
  }

  Widget _buildLoadingStatus() {
    return Row(children: [
      SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary))),
      const SizedBox(width: 12),
      const Text('Discovering services...', style: TextStyle(color: AppColors.textSecondary)),
    ]);
  }

  Widget _buildErrorStatus(Object error) {
    return Row(children: [
      Icon(Icons.error_outline, color: AppColors.error, size: 16),
      const SizedBox(width: 8),
      Expanded(child: Text('Discovery failed: $error', style: const TextStyle(color: AppColors.error, fontSize: 14), maxLines: 2, overflow: TextOverflow.ellipsis)),
    ]);
  }

  Widget _buildServicesTable(BuildContext context, AsyncValue<DiscoveryResponse> discoveryState, String? vpnIp) {
    return discoveryState.when(
      data: (response) => _buildServicesDataTable(response.services, context, vpnIp),
      loading: () => _buildLoadingTable(),
      error: (error, stack) => _buildErrorTable(error),
    );
  }

  Widget _buildServicesDataTable(List<ServiceInfo> services, BuildContext context, String? vpnIp) {
    if (services.isEmpty) return _buildEmptyServicesState();
    return Container(
      decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.border)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(padding: EdgeInsets.all(16), child: Text('Discovered Services', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary))),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(minWidth: MediaQuery.of(context).size.width - 32),
              child: DataTable(
                columnSpacing: 12, dataRowMinHeight: 30, dataRowMaxHeight: 60,
                headingRowColor: WidgetStateProperty.all(AppColors.background),
                dataRowColor: WidgetStateProperty.all(AppColors.background),
                border: TableBorder.all(color: AppColors.border.withValues(alpha: 0.3), width: 1),
                columns: [
                  DataColumn(label: Expanded(flex: 3, child: Text('Service', style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.textPrimary)))),
                  DataColumn(label: Expanded(flex: 2, child: Text('Status', style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.textPrimary)))),
                  DataColumn(label: Expanded(flex: 4, child: Text('URL', style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.textPrimary)))),
                  DataColumn(label: Expanded(flex: 2, child: Text('Version', style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.textPrimary)))),
                  DataColumn(label: Expanded(flex: 2, child: Text('VPN IP', style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.textPrimary)))),
                ],
                rows: services.map((service) => DataRow(cells: [
                  DataCell(_buildServiceCell(service)),
                  DataCell(_buildStatusCell(service)),
                  DataCell(_buildUrlCell(service)),
                  DataCell(_buildVersionCell(service)),
                  DataCell(Padding(padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4), child: Text(vpnIp ?? service.host, style: TextStyle(fontFamily: 'monospace', fontSize: 11, color: vpnIp != null ? AppColors.success : AppColors.textSecondary, fontWeight: vpnIp != null ? FontWeight.w600 : FontWeight.normal), maxLines: 1, overflow: TextOverflow.ellipsis))),
                ])).toList(),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingTable() => Container(padding: const EdgeInsets.all(32), decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.border)), child: Center(child: Column(children: [CircularProgressIndicator(valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary)), const SizedBox(height: 16), const Text('Loading services...', style: TextStyle(color: AppColors.textSecondary))])));
  Widget _buildErrorTable(Object error) => Container(padding: const EdgeInsets.all(32), decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.error)), child: Center(child: Column(children: [Icon(Icons.error_outline, color: AppColors.error, size: 48), const SizedBox(height: 16), const Text('Failed to load services', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.error)), const SizedBox(height: 8), Text(error.toString(), style: const TextStyle(color: AppColors.textSecondary, fontSize: 14), textAlign: TextAlign.center)])));
  Widget _buildEmptyServicesState() => Container(padding: const EdgeInsets.all(32), decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.border)), child: Center(child: Column(children: [Icon(Icons.search_off, color: AppColors.textSecondary, size: 48), const SizedBox(height: 16), const Text('No services discovered', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.textSecondary)), const SizedBox(height: 8), const Text('The discovery service is running but no services were found.', style: TextStyle(color: AppColors.textSecondary, fontSize: 14), textAlign: TextAlign.center)])));

  Widget _buildServiceCell(ServiceInfo service) => Padding(padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4), child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [Text(service.name, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 12, color: AppColors.textPrimary), maxLines: 2, overflow: TextOverflow.visible), if (service.serviceType.isNotEmpty) ...[const SizedBox(height: 2), Text(service.serviceType, style: const TextStyle(fontSize: 10, color: AppColors.textSecondary), maxLines: 1, overflow: TextOverflow.ellipsis)]]));
  Widget _buildStatusCell(ServiceInfo service) { final isHealthy = service.status.toLowerCase() == 'healthy'; return Padding(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4), child: Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3), decoration: BoxDecoration(color: (isHealthy ? AppColors.success : AppColors.error).withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12), border: Border.all(color: isHealthy ? AppColors.success : AppColors.error)), child: Text(service.status, textAlign: TextAlign.center, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: isHealthy ? AppColors.success : AppColors.error), overflow: TextOverflow.ellipsis, maxLines: 1))); }
  Widget _buildUrlCell(ServiceInfo service) => Padding(padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4), child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [Text(service.baseUrl, style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppColors.primary), maxLines: 2, overflow: TextOverflow.visible), const SizedBox(height: 2), Text('${service.host}:${service.port}', style: const TextStyle(fontSize: 10, color: AppColors.textSecondary), maxLines: 1, overflow: TextOverflow.ellipsis)]));
  Widget _buildVersionCell(ServiceInfo service) => Padding(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4), child: Text(service.version, style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: AppColors.textSecondary), overflow: TextOverflow.ellipsis, maxLines: 1));

  // -----------------------------------------------------------------------
  // VPN Status Card
  // -----------------------------------------------------------------------

  Widget _buildVpnStatusCard() {
    return Consumer(
      builder: (context, ref, _) {
        final vpnState = ref.watch(vpnStatusProvider);
        return vpnState.when(
          data: (status) => _buildVpnContent(context, ref, status),
          loading: () => _buildVpnLoading(),
          error: (error, _) => _buildVpnNotAvailable(error.toString()),
        );
      },
    );
  }

  Widget _buildVpnContent(BuildContext context, WidgetRef ref, VpnStatus status) {
    if (!status.available && !status.hasTailscaleInstalled) return _buildVpnNotAvailable('Tailscale not installed on this device');
    if (status.connectedToOtherServer) return _buildVpnWrongServer(status);
    if (!status.enrolled) return _buildVpnNotEnrolled();
    return _buildVpnActive(context, ref, status);
  }

  Widget _buildVpnActive(BuildContext context, WidgetRef ref, VpnStatus status) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppColors.success.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.success.withValues(alpha: 0.5))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [const Icon(Icons.vpn_lock, color: AppColors.success, size: 20), const SizedBox(width: 8), const Text('VPN Mesh Active', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.success))]),
          const SizedBox(height: 12),
          if (status.tailscaleIp != null) _vpnInfoRow('Tailscale IP', status.tailscaleIp!),
          ...status.vpnIps.where((ip) => ip != status.tailscaleIp).map((ip) => _vpnInfoRow('VPN IP', ip)),
          if (status.matrixGroupId != null && status.matrixGroupId!.isNotEmpty) _vpnInfoRow('Matrix Group', '${status.matrixGroupId!.substring(0, 16)}...'),
          if (status.headscaleServer != null) _vpnInfoRow('Server', status.headscaleServer!),
          _vpnInfoRow('Peers', '${status.peerCount} (${status.onlineCount} online)'),
          if (status.hostname != null) _vpnInfoRow('MagicDNS', '${status.hostname!}.eyenet-vpn.local'),
          const SizedBox(height: 12),
          Row(children: [const Text('Tailscale', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500)), const Spacer(), Container(width: 8, height: 8, decoration: BoxDecoration(color: status.enrolled ? AppColors.success : Colors.grey, shape: BoxShape.circle)), const SizedBox(width: 6), Text(status.enrolled ? 'Connected' : 'Disconnected', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: status.enrolled ? AppColors.success : Colors.grey))]),
        ],
      ),
    );
  }

  Widget _buildVpnNotEnrolled() {
    final targetPlatform = defaultTargetPlatform;
    final os = switch (targetPlatform) { TargetPlatform.android => 'android', TargetPlatform.iOS => 'ios', TargetPlatform.linux => 'linux', TargetPlatform.macOS => 'macos', TargetPlatform.windows => 'windows', _ => 'linux' };
    return _VpnEnrollmentCard(os: os, guide: tailscaleInstallGuide(os));
  }

  Widget _buildVpnWrongServer(VpnStatus status) {
    return Container(
      padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: AppColors.warning.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.warning.withValues(alpha: 0.5))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [const Icon(Icons.swap_horiz, color: AppColors.warning, size: 20), const SizedBox(width: 8), Expanded(child: Text('Switch Tailscale to EyeNet', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.warning)))]),
        const SizedBox(height: 8),
        Text('Tailscale is running but connected to ${status.currentServer ?? "another coordination server"}. To join the EyeNet VPN mesh, switch to ${status.expectedServer ?? "https://vpn.eyenet-vision.com"}:', style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
        const SizedBox(height: 12),
        Container(width: double.infinity, padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(6), border: Border.all(color: AppColors.border)), child: SelectableText('# Step 1: Disconnect from the other network\ntailscale logout\n\n# Step 2: Get an enrollment key from the authority\ncurl -s -X POST https://authority.eyenet-vision.com/api/v1/vpn/enroll-installation \\\n  -H "Content-Type: application/json" \\\n  -d \'{"installation_uuid":"<your-installation>","application_key":"<your-key>"}\'\n\n# Step 3: Connect to EyeNet headscale\ntailscale up \\\n  --login-server https://vpn.eyenet-vision.com \\\n  --auth-key <returned-hskey-auth-key> \\\n  --accept-routes', style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppColors.textPrimary))),
        const SizedBox(height: 8),
        const Text('You will get a new 100.64.x.x IP on the EyeNet mesh. Your existing IP from the other network will be released.', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
      ]),
    );
  }

  Widget _buildVpnNotAvailable(String reason) => Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.grey.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.grey.withValues(alpha: 0.3))), child: Row(children: [const Icon(Icons.vpn_lock_outlined, color: Colors.grey, size: 20), const SizedBox(width: 8), Expanded(child: Text('VPN Unavailable: $reason', style: const TextStyle(fontSize: 13, color: Colors.grey)))]));
  Widget _buildVpnLoading() => Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.grey.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.grey.withValues(alpha: 0.3))), child: const Row(children: [SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)), SizedBox(width: 12), Text('Checking VPN status...', style: TextStyle(fontSize: 13))]));
  Widget _vpnInfoRow(String label, String value) => Padding(padding: const EdgeInsets.symmetric(vertical: 3), child: Row(children: [SizedBox(width: 110, child: Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500))), Expanded(child: Text(value, style: const TextStyle(fontFamily: 'monospace', fontSize: 12)))]));

  void _showHostnameEditDialog(BuildContext context, WidgetRef ref, String currentHostname) {
    final controller = TextEditingController(text: currentHostname);
    showDialog(context: context, builder: (ctx) => AlertDialog(title: const Text('Edit MagicDNS Hostname'), content: Column(mainAxisSize: MainAxisSize.min, children: [TextField(controller: controller, decoration: const InputDecoration(labelText: 'Hostname', helperText: 'Alphanumeric + dashes, max 63 chars', border: OutlineInputBorder()), autofocus: true), const SizedBox(height: 8), Text('MagicDNS: ${controller.text}.eyenet-vpn.local', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary))]), actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')), FilledButton(onPressed: () async { final newHostname = controller.text.trim(); if (newHostname.isEmpty || newHostname == currentHostname) { Navigator.pop(ctx); return; } Navigator.pop(ctx); try { final client = ref.read(vpnStatusClientProvider); await client.updateHostname(newHostname); ref.invalidate(vpnStatusProvider); if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Hostname changed to $newHostname'), backgroundColor: AppColors.success)); } catch (e) { if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e'), backgroundColor: AppColors.error)); } }, child: const Text('Save'))]));
  }
}

// -----------------------------------------------------------------------
// VPN Mesh Peers Card (auto-refreshes every 30s)
// -----------------------------------------------------------------------

class _VpnPeersCard extends ConsumerStatefulWidget {
  const _VpnPeersCard();

  @override
  ConsumerState<_VpnPeersCard> createState() => _VpnPeersCardState();
}

class _VpnPeersCardState extends ConsumerState<_VpnPeersCard> {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    // Auto-refresh peers every 30 seconds to match authority cache TTL
    _timer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) ref.invalidate(vpnPeersProvider);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final peersAsync = ref.watch(vpnPeersProvider);
    final vpnStatusAsync = ref.watch(vpnStatusProvider);
    final enrolled = vpnStatusAsync.valueOrNull?.enrolled == true;

    if (!enrolled) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.border)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [const Icon(Icons.hub, color: AppColors.secondary, size: 20), const SizedBox(width: 8), const Text('Mesh Peers', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)), const Spacer(), TextButton.icon(onPressed: () => ref.invalidate(vpnPeersProvider), icon: const Icon(Icons.refresh, size: 16), label: const Text('Refresh', style: TextStyle(fontSize: 12)))]),
        const SizedBox(height: 12),
        peersAsync.when(
          data: (peers) {
            if (peers.isEmpty) return const Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Row(children: [Icon(Icons.info_outline, size: 16, color: AppColors.textSecondary), SizedBox(width: 8), Text('No peers found', style: TextStyle(fontSize: 12, color: AppColors.textSecondary))]));
            return Column(children: peers.map((peer) => _buildPeerRow(context, ref, peer)).toList());
          },
          loading: () => const Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Row(children: [SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)), SizedBox(width: 12), Text('Loading peers...', style: TextStyle(fontSize: 12, color: AppColors.textSecondary))])),
          error: (e, _) => Text('Failed to load peers: $e', style: const TextStyle(fontSize: 12, color: AppColors.error)),
        ),
      ]),
    );
  }

  Widget _buildPeerRow(BuildContext context, WidgetRef ref, VpnPeerInfo peer) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
      decoration: BoxDecoration(border: Border(bottom: BorderSide(color: AppColors.border.withValues(alpha: 0.3)))),
      child: Row(children: [
        Icon(peer.online ? Icons.check_circle : Icons.cancel, color: peer.online ? AppColors.success : AppColors.error, size: 20),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${peer.hostname}.eyenet-vpn.local', style: const TextStyle(fontFamily: 'monospace', fontSize: 13, color: AppColors.textPrimary)),
          const SizedBox(height: 2),
          Row(children: [
            Text(peer.tailscaleIp, style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppColors.textSecondary)),
            const SizedBox(width: 8),
            Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1), decoration: BoxDecoration(color: peer.online ? AppColors.success.withValues(alpha: 0.15) : AppColors.error.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4), border: Border.all(color: peer.online ? AppColors.success : AppColors.error, width: 0.5)), child: Text(peer.online ? 'Online' : 'Offline', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: peer.online ? AppColors.success : AppColors.error))),
          ]),
        ])),
        IconButton(icon: const Icon(Icons.edit, size: 16), tooltip: 'Rename', onPressed: () => _showRenamePeerDialog(context, ref, peer)),
        IconButton(icon: Icon(Icons.delete_outline, size: 16, color: AppColors.error), tooltip: 'Remove', onPressed: () => _showDeletePeerDialog(context, ref, peer)),
      ]),
    );
  }

  void _showRenamePeerDialog(BuildContext context, WidgetRef ref, VpnPeerInfo peer) {
    final controller = TextEditingController(text: peer.hostname);
    showDialog(context: context, builder: (ctx) => AlertDialog(title: const Text('Rename Peer'), content: Column(mainAxisSize: MainAxisSize.min, children: [TextField(controller: controller, decoration: const InputDecoration(labelText: 'New hostname', helperText: 'Alphanumeric + dashes', border: OutlineInputBorder()), autofocus: true)]), actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')), FilledButton(onPressed: () async { final newName = controller.text.trim(); if (newName.isEmpty || newName == peer.hostname) { Navigator.pop(ctx); return; } Navigator.pop(ctx); final client = ref.read(vpnStatusClientProvider); try { await client.renamePeer(peer.nodeId, newName); ref.invalidate(vpnPeersProvider); if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Renamed to $newName'), backgroundColor: AppColors.success)); } catch (e) { if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Rename failed: $e'), backgroundColor: AppColors.error)); } }, child: const Text('Rename'))]));
  }

  void _showDeletePeerDialog(BuildContext context, WidgetRef ref, VpnPeerInfo peer) {
    showDialog(context: context, builder: (ctx) => AlertDialog(title: const Text('Remove Peer'), content: Text('Remove ${peer.hostname}.eyenet-vpn.local from the VPN mesh?\n\nThis device will lose VPN access.'), actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')), FilledButton(style: FilledButton.styleFrom(backgroundColor: AppColors.error, foregroundColor: Colors.white), onPressed: () async { Navigator.pop(ctx); final client = ref.read(vpnStatusClientProvider); try { await client.deletePeer(peer.nodeId); ref.invalidate(vpnPeersProvider); if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${peer.hostname} removed'), backgroundColor: AppColors.success)); } catch (e) { if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Remove failed: $e'), backgroundColor: AppColors.error)); } }, child: const Text('Remove'))]));
  }
}

// -----------------------------------------------------------------------
// Enrollment Card (StatefulWidget — "Get Enrollment Key" button)
// -----------------------------------------------------------------------

class _VpnEnrollmentCard extends StatefulWidget {
  final String os;
  final String guide;
  const _VpnEnrollmentCard({required this.os, required this.guide});
  @override
  State<_VpnEnrollmentCard> createState() => _VpnEnrollmentCardState();
}

class _VpnEnrollmentCardState extends State<_VpnEnrollmentCard> {
  bool _loading = false; String? _error; EnrollmentKey? _key;

  Future<void> _getKey() async {
    if (_loading) return;
    setState(() { _loading = true; _error = null; });
    try { final client = VpnStatusClient(ApiClient(AppConfig.instance)); final key = await client.enroll(); if (!mounted) return; setState(() { _key = key; _loading = false; }); } catch (e) { if (!mounted) return; setState(() { _error = e.toString(); _loading = false; }); }
  }

  @override
  Widget build(BuildContext context) {
    return Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: AppColors.warning.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.warning.withValues(alpha: 0.5))), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [const Icon(Icons.vpn_lock_outlined, color: AppColors.warning, size: 20), const SizedBox(width: 8), const Expanded(child: Text('VPN Not Connected', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.warning)))]),
      const SizedBox(height: 8),
      const Text('This device is not enrolled in the EyeNet VPN mesh. Install Tailscale and enroll to connect with other installations.', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
      const SizedBox(height: 12),
      if (_key != null && _key!.enrolled) ...[
        Container(width: double.infinity, padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: AppColors.success.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(6), border: Border.all(color: AppColors.success)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Row(children: [Icon(Icons.check_circle, color: AppColors.success, size: 18), SizedBox(width: 8), Expanded(child: Text('Enrolled!', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppColors.success)))]), const SizedBox(height: 6), if (_key!.tailscaleIp != null) Text('VPN IP: ${_key!.tailscaleIp}', style: const TextStyle(fontFamily: 'monospace', fontSize: 12, fontWeight: FontWeight.w600)), if (_key!.matrixGroupId != null) Text('Matrix: ${_key!.matrixGroupId!.substring(0, 16)}...', style: const TextStyle(fontSize: 10, color: AppColors.textSecondary))])),
      ] else if (_key != null && !_key!.enrolled) ...[
        Container(width: double.infinity, padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: AppColors.success.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(6), border: Border.all(color: AppColors.success)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Row(children: [Icon(Icons.check_circle, color: AppColors.success, size: 16), SizedBox(width: 6), Text('Key ready — copy and run this command:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.success))]), const SizedBox(height: 8), SelectableText(_key!.tailscaleUpCommand, style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppColors.textPrimary)), if (_key!.matrixGroupId != null) Padding(padding: const EdgeInsets.only(top: 4), child: Text('Matrix: ${_key!.matrixGroupId!.substring(0, 16)}...', style: const TextStyle(fontSize: 10, color: AppColors.textSecondary)))])),
      ] else if (_loading) ...[
        const Center(child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))),
      ] else ...[
        Container(width: double.infinity, padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(6), border: Border.all(color: AppColors.border)), child: SelectableText(widget.guide, style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppColors.textPrimary))),
        const SizedBox(height: 4), Text('(${widget.os} instructions)', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
      ],
      const SizedBox(height: 12),
      Row(children: [
        if (_key == null || !_key!.enrolled) ElevatedButton.icon(onPressed: _loading ? null : _getKey, icon: Icon(_key != null ? Icons.refresh : Icons.vpn_key, size: 16), label: Text(_key != null ? 'Retry' : 'Enroll Now'), style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary, foregroundColor: Colors.white)),
        if (_key != null && _key!.enrolled) TextButton.icon(onPressed: _getKey, icon: const Icon(Icons.refresh, size: 16), label: const Text('Re-enroll')),
      ]),
      if (_error != null) ...[
        const SizedBox(height: 8),
        Container(width: double.infinity, padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: AppColors.error.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(6), border: Border.all(color: AppColors.error.withValues(alpha: 0.3))), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('⚠ Automatic key generation failed', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.error)), const SizedBox(height: 4), Text('Error: $_error', style: TextStyle(fontSize: 10, color: AppColors.error)), const SizedBox(height: 8), const Text('Manual steps (admin):', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textPrimary)), const SizedBox(height: 4), SelectableText('1. Go to https://authority.eyenet-vision.com/admin\n2. Open Data Console → VPN tab\n3. Click "Enrol device" on your installation\n4. Copy the key and run:\n\ntailscale logout\ntailscale up --login-server https://vpn.eyenet-vision.com \\\n  --auth-key <paste-key-here> \\\n  --accept-routes', style: const TextStyle(fontFamily: 'monospace', fontSize: 10, color: AppColors.textSecondary))])),
      ],
    ]));
  }
}
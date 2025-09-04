import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../services/discovery_service_client.dart';
import '../../../services/dynamic_service_provider.dart';
import '../../../core/theme/app_theme.dart';

/// Provider for fetching discovery services
final discoveryServicesProvider = FutureProvider<DiscoveryResponse>((ref) async {
  final discoveryClient = ref.watch(discoveryServiceProvider);
  return await discoveryClient.discoverServices();
});

class NetworkSettingsSection extends ConsumerWidget {
  const NetworkSettingsSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final discoveryState = ref.watch(discoveryServicesProvider);
    
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeader(),
          const SizedBox(height: 16),
          _buildDiscoveryStatus(context, discoveryState),
          const SizedBox(height: 24),
          _buildServicesTable(context, discoveryState),
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
          Icon(
            Icons.network_check,
            color: AppColors.primary,
            size: 20,
          ),
          const SizedBox(width: 12),
          Text(
            'Network & Services',
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDiscoveryStatus(BuildContext context, AsyncValue<DiscoveryResponse> discoveryState) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.router,
                color: AppColors.secondary,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Discovery Service Status',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
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
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: const BoxDecoration(
            color: AppColors.success,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          'Connected - ${response.services.length} services discovered',
          style: const TextStyle(
            color: AppColors.success,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Widget _buildLoadingStatus() {
    return Row(
      children: [
        SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          'Discovering services...',
          style: const TextStyle(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildErrorStatus(Object error) {
    return Row(
      children: [
        Icon(
          Icons.error_outline,
          color: AppColors.error,
          size: 16,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            'Discovery failed: ${error.toString()}',
            style: const TextStyle(
              color: AppColors.error,
              fontSize: 14,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  Widget _buildServicesTable(BuildContext context, AsyncValue<DiscoveryResponse> discoveryState) {
    return discoveryState.when(
      data: (response) => _buildServicesDataTable(response.services, context),
      loading: () => _buildLoadingTable(),
      error: (error, stack) => _buildErrorTable(error),
    );
  }

  Widget _buildServicesDataTable(List<ServiceInfo> services, BuildContext context) {
    if (services.isEmpty) {
      return _buildEmptyServicesState();
    }

    return Container(
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              'Discovered Services',
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minWidth: MediaQuery.of(context).size.width - 32, // Account for screen padding
              ),
              child: DataTable(
                columnSpacing: 12, // Reduced spacing for more room
                dataRowMinHeight: 30, // Increased for better readability
                dataRowMaxHeight: 60, // Increased to allow text wrapping
                headingRowColor: WidgetStateProperty.all(AppColors.background),
                dataRowColor: WidgetStateProperty.all(AppColors.background),
                border: TableBorder.all(
                  color: AppColors.border.withValues(alpha: 0.3),
                  width: 1,
                ),
                columns: [
                  DataColumn(
                    label: Expanded(
                      flex: 3, // Give service column more space
                      child: Text(
                        'Service',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ),
                  DataColumn(
                    label: Expanded(
                      flex: 2,
                      child: Text(
                        'Status',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ),
                  DataColumn(
                    label: Expanded(
                      flex: 4, // URL column gets most space
                      child: Text(
                        'URL',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ),
                  DataColumn(
                    label: Expanded(
                      flex: 2,
                      child: Text(
                        'Version',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ),
                ],
                rows: services.map((service) => DataRow(
                  cells: [
                    DataCell(
                      _buildServiceCell(service), // Remove SizedBox constraint
                    ),
                    DataCell(
                      _buildStatusCell(service), // Remove SizedBox constraint
                    ),
                    DataCell(
                      _buildUrlCell(service), // Remove SizedBox constraint
                    ),
                    DataCell(
                      _buildVersionCell(service), // Remove SizedBox constraint
                    ),
                  ],
                )).toList(),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingTable() {
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Center(
        child: Column(
          children: [
            CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
            ),
            const SizedBox(height: 16),
            Text(
              'Loading services...',
              style: const TextStyle(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorTable(Object error) {
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.error),
      ),
      child: Center(
        child: Column(
          children: [
            Icon(
              Icons.error_outline,
              color: AppColors.error,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'Failed to load services',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.error,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              error.toString(),
              style: const TextStyle(
                color: AppColors.textSecondary,
                fontSize: 14,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyServicesState() {
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Center(
        child: Column(
          children: [
            Icon(
              Icons.search_off,
              color: AppColors.textSecondary,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'No services discovered',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'The discovery service is running but no services were found.',
              style: const TextStyle(
                color: AppColors.textSecondary,
                fontSize: 14,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildServiceCell(ServiceInfo service) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            service.name,
            style: const TextStyle(
              fontWeight: FontWeight.w500,
              fontSize: 12,
              color: AppColors.textPrimary,
            ),
            maxLines: 2, // Allow 2 lines for service names
            overflow: TextOverflow.visible, // Let text wrap naturally
          ),
          if (service.serviceType.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              service.serviceType,
              style: const TextStyle(
                fontSize: 10,
                color: AppColors.textSecondary,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatusCell(ServiceInfo service) {
    final isHealthy = service.status.toLowerCase() == 'healthy';
    
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4), // Reduced vertical padding
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: (isHealthy ? AppColors.success : AppColors.error).withValues(alpha: 0.2),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isHealthy ? AppColors.success : AppColors.error,
          ),
        ),
        child: Text(
          service.status,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: isHealthy ? AppColors.success : AppColors.error,
          ),
          overflow: TextOverflow.ellipsis,
          maxLines: 1,
        ),
      ),
    );
  }

  Widget _buildUrlCell(ServiceInfo service) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            service.baseUrl,
            style: const TextStyle(
              fontFamily: 'monospace',
              fontSize: 11,
              color: AppColors.primary,
            ),
            maxLines: 2, // Allow URL to wrap to 2 lines if needed
            overflow: TextOverflow.visible,
          ),
          const SizedBox(height: 2),
          Text(
            '${service.host}:${service.port}',
            style: const TextStyle(
              fontSize: 10,
              color: AppColors.textSecondary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildVersionCell(ServiceInfo service) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4), // Reduced vertical padding
      child: Text(
        service.version,
        style: const TextStyle(
          fontSize: 11,
          fontFamily: 'monospace',
          color: AppColors.textSecondary,
        ),
        overflow: TextOverflow.ellipsis,
        maxLines: 1,
      ),
    );
  }
}

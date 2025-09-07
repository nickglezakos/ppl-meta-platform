import 'package:flutter/material.dart';

class IpMonitoringStatusWidget extends StatelessWidget {
  final String? currentIp;
  
  const IpMonitoringStatusWidget({
    super.key,
    this.currentIp,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.5),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            currentIp != null ? Icons.wifi : Icons.wifi_off,
            size: 16,
            color: currentIp != null ? Colors.green : Colors.orange,
          ),
          const SizedBox(width: 8),
          Text(
            currentIp ?? 'No Network',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

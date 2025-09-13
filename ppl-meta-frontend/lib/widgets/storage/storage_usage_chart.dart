// Storage Usage Chart Widget
// Visual representation of storage distribution between live and archive

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class StorageUsageChart extends StatelessWidget {
  final double livePercentage;
  final double archivePercentage;
  final double totalSizeGb;

  const StorageUsageChart({
    super.key,
    required this.livePercentage,
    required this.archivePercentage,
    required this.totalSizeGb,
  });

  @override
  Widget build(BuildContext context) {
    final liveSize = (totalSizeGb * livePercentage / 100);
    final archiveSize = (totalSizeGb * archivePercentage / 100);

    return Container(
      height: 200,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Theme.of(context).dividerColor,
        ),
      ),
      child: Column(
        children: [
          Expanded(
            child: PieChart(
              PieChartData(
                sectionsSpace: 2,
                centerSpaceRadius: 40,
                sections: [
                  PieChartSectionData(
                    color: Colors.blue,
                    value: livePercentage,
                    title: '${livePercentage.round()}%',
                    radius: 50,
                    titleStyle: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  PieChartSectionData(
                    color: Colors.orange,
                    value: archivePercentage,
                    title: '${archivePercentage.round()}%',
                    radius: 50,
                    titleStyle: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildLegendItem(
                context,
                'Live Storage',
                '${liveSize.toStringAsFixed(1)} GB',
                Colors.blue,
              ),
              _buildLegendItem(
                context,
                'Archive Storage',
                '${archiveSize.toStringAsFixed(1)} GB',
                Colors.orange,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(BuildContext context, String label, String value, Color color) {
    return Column(
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
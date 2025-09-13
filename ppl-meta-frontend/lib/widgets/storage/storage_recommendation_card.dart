// Storage Recommendation Card Widget
// Provides intelligent recommendations for collection sizes based on usage patterns

import 'package:flutter/material.dart';

class StorageRecommendationCard extends StatelessWidget {
  final double currentSize;
  final Function(double) onSizeRecommendation;

  const StorageRecommendationCard({
    super.key,
    required this.currentSize,
    required this.onSizeRecommendation,
  });

  @override
  Widget build(BuildContext context) {
    final recommendations = _generateRecommendations();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).primaryColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Theme.of(context).primaryColor.withOpacity(0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.lightbulb_outline,
                color: Theme.of(context).primaryColor,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Size Recommendations',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: Theme.of(context).primaryColor,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: recommendations.map((rec) => 
              _buildRecommendationChip(context, rec)
            ).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildRecommendationChip(BuildContext context, StorageRecommendation rec) {
    final isSelected = (currentSize - rec.sizeGb).abs() < 0.1;
    
    return ActionChip(
      avatar: Icon(
        rec.icon,
        size: 16,
        color: isSelected ? Colors.white : Theme.of(context).primaryColor,
      ),
      label: Text(
        '${rec.sizeGb.toStringAsFixed(0)} GB - ${rec.label}',
        style: TextStyle(
          color: isSelected ? Colors.white : Theme.of(context).primaryColor,
          fontSize: 12,
        ),
      ),
      backgroundColor: isSelected 
        ? Theme.of(context).primaryColor 
        : Theme.of(context).primaryColor.withOpacity(0.1),
      onPressed: () => onSizeRecommendation(rec.sizeGb),
    );
  }

  List<StorageRecommendation> _generateRecommendations() {
    return [
      StorageRecommendation(
        sizeGb: 25.0,
        label: 'Basic',
        description: 'Small home setup, 1-2 cameras',
        icon: Icons.home,
      ),
      StorageRecommendation(
        sizeGb: 50.0,
        label: 'Standard',
        description: 'Most home setups, 3-5 cameras',
        icon: Icons.camera_alt,
      ),
      StorageRecommendation(
        sizeGb: 100.0,
        label: 'Professional',
        description: 'Small business, 6-10 cameras',
        icon: Icons.business,
      ),
      StorageRecommendation(
        sizeGb: 250.0,
        label: 'Enterprise',
        description: 'Large installations, 10+ cameras',
        icon: Icons.apartment,
      ),
      StorageRecommendation(
        sizeGb: 500.0,
        label: 'Industrial',
        description: 'High-capacity installations',
        icon: Icons.factory,
      ),
    ];
  }
}

class StorageRecommendation {
  final double sizeGb;
  final String label;
  final String description;
  final IconData icon;

  const StorageRecommendation({
    required this.sizeGb,
    required this.label,
    required this.description,
    required this.icon,
  });
}
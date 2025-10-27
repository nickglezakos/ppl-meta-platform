/// PPL Meta Frontend - Distance-Based Color Coding Service
/// 
/// This service manages the distance-based color coding functionality for 
/// person objects visualization. It provides utility methods for color 
/// assignment, accessibility features, and UI integration.

import 'package:flutter/material.dart';
import '../models/enhanced_person_objects_models.dart';

/// Service for managing distance-based color coding in person objects visualization
class DistanceColorService {
  
  // =============================================================================
  // DISTANCE-BASED COLOR MAPPING
  // =============================================================================
  
  /// Standard PPL Meta distance color scheme
  /// Green gradient based on distance/size:
  /// - Dark Green: Very close/large (< 10m) - Largest faces
  /// - Medium-Dark Green: Close/large (10-20m)
  /// - Medium Green: Medium distance/size (20-30m)
  /// - Medium-Light Green: Far/small (30-50m)
  /// - Light Green: Very far/small (> 50m) - Smallest faces
  static Color getDistanceColor(double distance) {
    if (distance < 10) return const Color(0xFF1B5E20); // Dark Green (closest/largest)
    if (distance < 20) return const Color(0xFF2E7D32); // Medium-Dark Green
    if (distance < 30) return const Color(0xFF388E3C); // Medium Green  
    if (distance < 50) return const Color(0xFF66BB6A); // Medium-Light Green
    return const Color(0xFF81C784); // Light Green (farthest/smallest)
  }
  
  /// Get a lighter version of the distance color for backgrounds
  static Color getDistanceColorLight(double distance) {
    if (distance < 10) return const Color(0xFFFEB2B2); // Light Red
    if (distance < 20) return const Color(0xFFFBD38D); // Light Orange
    if (distance < 30) return const Color(0xFFFAF089); // Light Yellow
    if (distance < 50) return const Color(0xFF9AE6B4); // Light Green
    return const Color(0xFFA3BFFA); // Light Blue
  }
  
  /// Get a darker version of the distance color for text/borders
  static Color getDistanceColorDark(double distance) {
    if (distance < 10) return const Color(0xFFC53030); // Dark Red
    if (distance < 20) return const Color(0xFFDD6B20); // Dark Orange
    if (distance < 30) return const Color(0xFFD69E2E); // Dark Yellow
    if (distance < 50) return const Color(0xFF2F855A); // Dark Green
    return const Color(0xFF2B6CB0); // Dark Blue
  }
  
  // =============================================================================
  // ACCESSIBILITY AND UI HELPERS
  // =============================================================================
  
  /// Get human-readable distance description for accessibility
  static String getDistanceDescription(double distance) {
    if (distance < 10) return 'Very Close (Largest)';
    if (distance < 20) return 'Close (Large)';
    if (distance < 30) return 'Medium Distance';
    if (distance < 50) return 'Far (Small)';
    return 'Very Far (Smallest)';
  }
  
  /// Get color name for UI display and accessibility
  static String getColorName(double distance) {
    if (distance < 10) return 'Dark Green';
    if (distance < 20) return 'Medium-Dark Green';
    if (distance < 30) return 'Medium Green';
    if (distance < 50) return 'Medium-Light Green';
    return 'Light Green';
  }
  
  /// Get priority level for sorting/filtering
  static int getDistancePriority(double distance) {
    if (distance < 10) return 1; // Highest priority - very close
    if (distance < 20) return 2; // High priority - close
    if (distance < 30) return 3; // Medium priority
    if (distance < 50) return 4; // Low priority - far
    return 5; // Lowest priority - very far
  }
  
  /// Check if distance represents a close proximity (red/orange zones)
  static bool isCloseProximity(double distance) {
    return distance < 20; // Red or Orange zones
  }
  
  /// Check if distance represents a safe distance (green/blue zones)
  static bool isSafeDistance(double distance) {
    return distance >= 30; // Green or Blue zones
  }
  
  // =============================================================================
  // PERSON GROUP UTILITIES
  // =============================================================================
  
  /// Get the appropriate color for a person group based on their closest distance
  static Color getPersonGroupColor(EnhancedPersonObjectGroup group) {
    return getDistanceColor(group.closestDistance);
  }
  
  /// Get color for person group summary card background
  static Color getPersonGroupBackgroundColor(EnhancedPersonObjectGroup group) {
    return getDistanceColorLight(group.closestDistance);
  }
  
  /// Get color for person group text and borders
  static Color getPersonGroupAccentColor(EnhancedPersonObjectGroup group) {
    return getDistanceColorDark(group.closestDistance);
  }
  
  /// Get formatted distance string for UI display
  static String formatDistance(double distance) {
    return '${distance.toStringAsFixed(1)}m';
  }
  
  /// Get formatted distance with color description
  static String formatDistanceWithDescription(double distance) {
    return '${formatDistance(distance)} (${getDistanceDescription(distance)})';
  }
  
  // =============================================================================
  // OVERLAY PAINTING HELPERS
  // =============================================================================
  
  /// Create paint object for distance-based rectangle drawing
  static Paint createDistancePaint(double distance, {
    double strokeWidth = 2.0,
    PaintingStyle style = PaintingStyle.stroke,
  }) {
    return Paint()
      ..color = getDistanceColor(distance)
      ..strokeWidth = strokeWidth
      ..style = style;
  }
  
  /// Create paint object for filled distance-based shapes
  static Paint createDistanceFillPaint(double distance, {double opacity = 0.3}) {
    return Paint()
      ..color = getDistanceColor(distance).withOpacity(opacity)
      ..style = PaintingStyle.fill;
  }
  
  // =============================================================================
  // TEXT STYLING HELPERS
  // =============================================================================
  
  /// Create text style for distance labels
  static TextStyle createDistanceTextStyle(double distance, {
    double fontSize = 12.0,
    FontWeight fontWeight = FontWeight.bold,
    bool withShadow = true,
  }) {
    return TextStyle(
      color: Colors.white,
      fontSize: fontSize,
      fontWeight: fontWeight,
      shadows: withShadow ? [
        Shadow(
          offset: const Offset(1, 1),
          blurRadius: 2,
          color: Colors.black54,
        ),
      ] : null,
    );
  }
  
  /// Create text style for person ID labels with distance-based color
  static TextStyle createPersonIdTextStyle(double distance, {
    double fontSize = 12.0,
    FontWeight fontWeight = FontWeight.bold,
  }) {
    return TextStyle(
      color: getDistanceColorDark(distance),
      fontSize: fontSize,
      fontWeight: fontWeight,
    );
  }
  
  // =============================================================================
  // SORTING AND FILTERING UTILITIES
  // =============================================================================
  
  /// Sort person groups by distance (closest first)
  static List<EnhancedPersonObjectGroup> sortByDistance(
    List<EnhancedPersonObjectGroup> groups,
    {bool ascending = true}
  ) {
    final sorted = List<EnhancedPersonObjectGroup>.from(groups);
    sorted.sort((a, b) {
      final comparison = a.closestDistance.compareTo(b.closestDistance);
      return ascending ? comparison : -comparison;
    });
    return sorted;
  }
  
  /// Filter person groups by distance range
  static List<EnhancedPersonObjectGroup> filterByDistanceRange(
    List<EnhancedPersonObjectGroup> groups,
    double minDistance,
    double maxDistance,
  ) {
    return groups.where((group) {
      final distance = group.closestDistance;
      return distance >= minDistance && distance <= maxDistance;
    }).toList();
  }
  
  /// Filter person groups by proximity level
  static List<EnhancedPersonObjectGroup> filterByProximityLevel(
    List<EnhancedPersonObjectGroup> groups,
    String level, // 'close', 'medium', 'far'
  ) {
    switch (level.toLowerCase()) {
      case 'close':
        return groups.where((g) => g.closestDistance < 20).toList();
      case 'medium':
        return groups.where((g) => g.closestDistance >= 20 && g.closestDistance < 50).toList();
      case 'far':
        return groups.where((g) => g.closestDistance >= 50).toList();
      default:
        return groups;
    }
  }
  
  // =============================================================================
  // ANALYTICS AND STATISTICS
  // =============================================================================
  
  /// Get distance distribution statistics for a list of person groups
  static DistanceStatistics getDistanceStatistics(List<EnhancedPersonObjectGroup> groups) {
    if (groups.isEmpty) {
      return const DistanceStatistics.empty();
    }
    
    final distances = groups.map((g) => g.closestDistance).toList();
    distances.sort();
    
    final closeCount = groups.where((g) => g.closestDistance < 20).length;
    final mediumCount = groups.where((g) => g.closestDistance >= 20 && g.closestDistance < 50).length;
    final farCount = groups.where((g) => g.closestDistance >= 50).length;
    
    return DistanceStatistics(
      totalGroups: groups.length,
      minDistance: distances.first,
      maxDistance: distances.last,
      averageDistance: distances.reduce((a, b) => a + b) / distances.length,
      closeProximityCount: closeCount,
      mediumDistanceCount: mediumCount,
      farDistanceCount: farCount,
    );
  }
}

// =============================================================================
// DISTANCE STATISTICS DATA CLASS
// =============================================================================

/// Statistics about distance distribution in person groups
class DistanceStatistics {
  final int totalGroups;
  final double minDistance;
  final double maxDistance;
  final double averageDistance;
  final int closeProximityCount;
  final int mediumDistanceCount;
  final int farDistanceCount;
  
  const DistanceStatistics({
    required this.totalGroups,
    required this.minDistance,
    required this.maxDistance,
    required this.averageDistance,
    required this.closeProximityCount,
    required this.mediumDistanceCount,
    required this.farDistanceCount,
  });
  
  const DistanceStatistics.empty()
      : totalGroups = 0,
        minDistance = 0.0,
        maxDistance = 0.0,
        averageDistance = 0.0,
        closeProximityCount = 0,
        mediumDistanceCount = 0,
        farDistanceCount = 0;
  
  /// Get the percentage of groups in close proximity
  double get closeProximityPercentage {
    if (totalGroups == 0) return 0.0;
    return (closeProximityCount / totalGroups) * 100;
  }
  
  /// Get the percentage of groups at medium distance
  double get mediumDistancePercentage {
    if (totalGroups == 0) return 0.0;
    return (mediumDistanceCount / totalGroups) * 100;
  }
  
  /// Get the percentage of groups at far distance
  double get farDistancePercentage {
    if (totalGroups == 0) return 0.0;
    return (farDistanceCount / totalGroups) * 100;
  }
  
  @override
  String toString() {
    return 'DistanceStatistics(total: $totalGroups, close: $closeProximityCount, '
           'medium: $mediumDistanceCount, far: $farDistanceCount, '
           'avg: ${averageDistance.toStringAsFixed(1)}m)';
  }
}
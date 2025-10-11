/// PPL Meta Frontend - Enhanced Person Counter Demo
/// 
/// Demo widget to showcase the enhanced person counter with drill-down analytics.
/// This demonstrates the new distance-based color coding and detailed person analytics.

import 'package:flutter/material.dart';
import '../models/person_group_models.dart';
import '../widgets/enhanced_person_counter.dart';

class EnhancedPersonCounterDemo extends StatelessWidget {
  const EnhancedPersonCounterDemo({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Enhanced Person Analytics Demo'),
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Demo description
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.info_outline, color: Colors.blue),
                        const SizedBox(width: 8),
                        const Text(
                          'Enhanced Person Analytics Demo',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'This demo showcases the new enhanced person counter with distance-based color coding and detailed drill-down analytics. Tap on person groups to explore comprehensive analytics including movement tracking, quality metrics, and representative faces.',
                      style: TextStyle(fontSize: 14),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      children: [
                        _buildColorLegendChip('Very Close (<10m)', Colors.red),
                        _buildColorLegendChip('Close (10-20m)', Colors.orange),
                        _buildColorLegendChip('Medium (20-30m)', Colors.yellow),
                        _buildColorLegendChip('Far (30-50m)', Colors.green),
                        _buildColorLegendChip('Very Far (>50m)', Colors.blue),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Enhanced counter with mock data
            const Text(
              'Enhanced Person Counter:',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            EnhancedPersonCounter(
              totalPersons: 3,
              totalFaces: 45,
              personGroups: _createMockPersonGroups(),
              groupingMethod: 'rectangle_overlap_detection',
              processingTime: 23.4,
              sessionUuid: 'demo-session-uuid-123',
              isLoading: false,
            ),
            const SizedBox(height: 20),

            // Simple counter for comparison
            const Text(
              'Simple Person Counter (for comparison):',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const SimplePersonCounter(
              totalPersons: 3,
              totalFaces: 45,
              isLoading: false,
            ),
            const SizedBox(height: 20),

            // Summary card demo
            const Text(
              'Person Counter Summary Card:',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            PersonCounterSummaryCard(
              personGroups: _createMockPersonGroups(),
              title: 'Detection Summary',
              onViewAll: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('View All button pressed')),
                );
              },
            ),
            const SizedBox(height: 20),

            // Loading state demo
            const Text(
              'Loading State Demo:',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const EnhancedPersonCounter(
              totalPersons: 0,
              totalFaces: 0,
              personGroups: [],
              isLoading: true,
            ),
            const SizedBox(height: 20),

            // Error state demo
            const Text(
              'Error State Demo:',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const EnhancedPersonCounter(
              totalPersons: 0,
              totalFaces: 15,
              personGroups: [],
              error: 'Person detection failed',
            ),
          ],
        ),
      ),
    );
  }

  /// Create mock person groups for demo
  List<PersonObjectGroup> _createMockPersonGroups() {
    return [
      // Person 1: Close distance (orange)
      PersonObjectGroup(
        personUuid: 'demo-person-1-uuid',
        personId: 'person_1',
        faceCount: 18,
        representativeFaces: [
          RepresentativeFace(
            faceData: {
              'bbox': [231, 107, 448, 324],
              'confidence': 0.85,
              'distance_from_camera': 15.26,
              'center_x': 339.5,
              'center_y': 215.5,
              'face_width': 217,
              'face_height': 217,
              'face_area': 47089,
              'frame_number': 94,
              'timestamp': 3.13,
            },
            qualityScore: 87.3,
            selectionRank: 1,
            selectionCriteria: const SelectionCriteria(
              distanceWeight: 0.3,
              confidenceWeight: 0.3,
              areaWeight: 0.2,
              positionWeight: 0.2,
            ),
          ),
          RepresentativeFace(
            faceData: {
              'bbox': [225, 102, 445, 328],
              'confidence': 0.78,
              'distance_from_camera': 16.7,
              'center_x': 335.0,
              'center_y': 215.0,
              'face_width': 220,
              'face_height': 226,
              'face_area': 49720,
              'frame_number': 67,
              'timestamp': 2.23,
            },
            qualityScore: 82.1,
            selectionRank: 2,
            selectionCriteria: const SelectionCriteria(
              distanceWeight: 0.3,
              confidenceWeight: 0.3,
              areaWeight: 0.2,
              positionWeight: 0.2,
            ),
          ),
        ],
        allFaceIds: List.generate(18, (i) => 'face_${i + 1}'),
        averageConfidence: 0.78,
        spatialBounds: const SpatialBounds(
          minX: 223, maxX: 449,
          minY: 102, maxY: 328,
          centerX: 336, centerY: 215,
        ),
        temporalSpan: const TemporalSpan(
          startFrame: 0, endFrame: 120,
          durationSeconds: 4.0, frameCount: 18,
        ),
        movementTracking: MovementTracking(
          routePoints: _generateMockRoutePoints(18, 336, 215),
          movementStatistics: const MovementStatistics(
            totalRoutePoints: 18,
            totalDistancePixels: 127.3,
            averageVelocity: 23.2,
            maxVelocity: 45.7,
            timeInFrameSeconds: 4.0,
          ),
        ),
        qualityMetrics: const QualityMetrics(
          averageQuality: 84.7,
          maxQuality: 91.2,
          minQuality: 78.3,
          qualityVariance: 6.4,
        ),
      ),

      // Person 2: Medium distance (yellow)
      PersonObjectGroup(
        personUuid: 'demo-person-2-uuid',
        personId: 'person_2',
        faceCount: 15,
        representativeFaces: [
          RepresentativeFace(
            faceData: {
              'bbox': [180, 150, 280, 250],
              'confidence': 0.72,
              'distance_from_camera': 25.8,
              'center_x': 230.0,
              'center_y': 200.0,
              'face_width': 100,
              'face_height': 100,
              'face_area': 10000,
              'frame_number': 45,
              'timestamp': 1.5,
            },
            qualityScore: 76.4,
            selectionRank: 1,
            selectionCriteria: const SelectionCriteria(
              distanceWeight: 0.3,
              confidenceWeight: 0.3,
              areaWeight: 0.2,
              positionWeight: 0.2,
            ),
          ),
        ],
        allFaceIds: List.generate(15, (i) => 'face_p2_${i + 1}'),
        averageConfidence: 0.69,
        spatialBounds: const SpatialBounds(
          minX: 170, maxX: 290,
          minY: 140, maxY: 260,
          centerX: 230, centerY: 200,
        ),
        temporalSpan: const TemporalSpan(
          startFrame: 30, endFrame: 180,
          durationSeconds: 5.0, frameCount: 15,
        ),
        movementTracking: MovementTracking(
          routePoints: _generateMockRoutePoints(15, 230, 200),
          movementStatistics: const MovementStatistics(
            totalRoutePoints: 15,
            totalDistancePixels: 95.7,
            averageVelocity: 19.1,
            maxVelocity: 32.4,
            timeInFrameSeconds: 5.0,
          ),
        ),
        qualityMetrics: const QualityMetrics(
          averageQuality: 72.1,
          maxQuality: 80.5,
          minQuality: 65.2,
          qualityVariance: 8.7,
        ),
      ),

      // Person 3: Far distance (green)
      PersonObjectGroup(
        personUuid: 'demo-person-3-uuid',
        personId: 'person_3',
        faceCount: 12,
        representativeFaces: [
          RepresentativeFace(
            faceData: {
              'bbox': [500, 300, 560, 360],
              'confidence': 0.65,
              'distance_from_camera': 42.1,
              'center_x': 530.0,
              'center_y': 330.0,
              'face_width': 60,
              'face_height': 60,
              'face_area': 3600,
              'frame_number': 78,
              'timestamp': 2.6,
            },
            qualityScore: 68.9,
            selectionRank: 1,
            selectionCriteria: const SelectionCriteria(
              distanceWeight: 0.3,
              confidenceWeight: 0.3,
              areaWeight: 0.2,
              positionWeight: 0.2,
            ),
          ),
        ],
        allFaceIds: List.generate(12, (i) => 'face_p3_${i + 1}'),
        averageConfidence: 0.61,
        spatialBounds: const SpatialBounds(
          minX: 490, maxX: 570,
          minY: 290, maxY: 370,
          centerX: 530, centerY: 330,
        ),
        temporalSpan: const TemporalSpan(
          startFrame: 60, endFrame: 240,
          durationSeconds: 6.0, frameCount: 12,
        ),
        movementTracking: MovementTracking(
          routePoints: _generateMockRoutePoints(12, 530, 330),
          movementStatistics: const MovementStatistics(
            totalRoutePoints: 12,
            totalDistancePixels: 67.2,
            averageVelocity: 11.2,
            maxVelocity: 18.9,
            timeInFrameSeconds: 6.0,
          ),
        ),
        qualityMetrics: const QualityMetrics(
          averageQuality: 65.3,
          maxQuality: 72.8,
          minQuality: 58.1,
          qualityVariance: 7.2,
        ),
      ),
    ];
  }

  /// Generate mock route points for demo
  List<RoutePoint> _generateMockRoutePoints(int count, double centerX, double centerY) {
    return List.generate(count, (i) {
      final angle = (i / count) * 2 * 3.14159; // Full circle
      final radius = 20.0; // Movement radius
      final x = centerX + radius * (i / count - 0.5) * 2; // Linear movement
      final y = centerY + radius * 0.3 * (i % 2 == 0 ? 1 : -1); // Slight vertical variation
      
      return RoutePoint(
        sequenceNumber: i + 1,
        frameNumber: i * 10,
        timestamp: i * 0.33,
        centerX: x,
        centerY: y,
        distanceFromCamera: 15.26 + (i * 0.1), // Gradually increasing distance
        velocityX: i > 0 ? (x - (centerX + radius * ((i-1) / count - 0.5) * 2)) / 0.33 : 0,
        velocityY: i > 0 ? (y - (centerY + radius * 0.3 * ((i-1) % 2 == 0 ? 1 : -1))) / 0.33 : 0,
        velocityMagnitude: i > 0 ? 15.0 + (i * 2.0) : 0, // Increasing velocity
      );
    });
  }

  /// Build color legend chip
  Widget _buildColorLegendChip(String label, Color color) {
    return Chip(
      label: Text(
        label,
        style: const TextStyle(fontSize: 12),
      ),
      avatar: CircleAvatar(
        backgroundColor: color,
        radius: 8,
      ),
      backgroundColor: color.withOpacity(0.1),
      side: BorderSide(color: color.withOpacity(0.3)),
    );
  }
}
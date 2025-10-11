/// PPL Meta Frontend - Person Group Detail View
/// 
/// Comprehensive drill-down view for detailed person analytics including
/// overview, representative faces, movement analysis, and quality metrics.

import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../models/person_group_models.dart';

class PersonGroupDetailView extends StatefulWidget {
  final PersonObjectGroup group;

  const PersonGroupDetailView({
    Key? key,
    required this.group,
  }) : super(key: key);

  @override
  State<PersonGroupDetailView> createState() => _PersonGroupDetailViewState();
}

class _PersonGroupDetailViewState extends State<PersonGroupDetailView>
    with TickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.group.personId} Analytics'),
        backgroundColor: widget.group.distanceColor,
        foregroundColor: Colors.white,
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white70,
          tabs: const [
            Tab(icon: Icon(Icons.analytics_outlined), text: 'Overview'),
            Tab(icon: Icon(Icons.face), text: 'Faces'),
            Tab(icon: Icon(Icons.timeline), text: 'Movement'),
            Tab(icon: Icon(Icons.assessment), text: 'Quality'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildOverviewTab(),
          _buildFacesTab(),
          _buildMovementTab(),
          _buildQualityTab(),
        ],
      ),
    );
  }

  /// Overview Tab: Key statistics and summary
  Widget _buildOverviewTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Header card with key metrics
          _buildHeaderCard(),
          const SizedBox(height: 16),
          
          // Person Information
          _buildInfoCard(
            'Person Information',
            Icons.person,
            [
              _buildInfoRow('UUID', widget.group.personUuid),
              _buildInfoRow('Person ID', widget.group.personId),
              _buildInfoRow('Total Faces', '${widget.group.faceCount}'),
              _buildInfoRow('Avg Confidence', '${(widget.group.averageConfidence * 100).toStringAsFixed(1)}%'),
              _buildInfoRow('Duration', '${widget.group.temporalSpan.durationSeconds.toStringAsFixed(1)}s'),
              _buildInfoRow('Distance Category', getDistanceCategoryName(widget.group.closestDistance)),
            ],
          ),
          const SizedBox(height: 16),
          
          // Spatial Analysis
          _buildInfoCard(
            'Spatial Analysis',
            Icons.map,
            [
              _buildInfoRow('Movement Area', '${widget.group.spatialBounds.width.toStringAsFixed(1)} × ${widget.group.spatialBounds.height.toStringAsFixed(1)} px'),
              _buildInfoRow('Center Position', '(${widget.group.spatialBounds.centerX.toStringAsFixed(1)}, ${widget.group.spatialBounds.centerY.toStringAsFixed(1)})'),
              _buildInfoRow('Bounds', 'X: ${widget.group.spatialBounds.minX.toStringAsFixed(1)}-${widget.group.spatialBounds.maxX.toStringAsFixed(1)}, Y: ${widget.group.spatialBounds.minY.toStringAsFixed(1)}-${widget.group.spatialBounds.maxY.toStringAsFixed(1)}'),
              _buildInfoRow('Area Coverage', '${widget.group.spatialBounds.area.toStringAsFixed(0)} px²'),
            ],
          ),
          const SizedBox(height: 16),
          
          // Movement Summary
          _buildInfoCard(
            'Movement Summary',
            Icons.directions_run,
            [
              _buildInfoRow('Route Points', '${widget.group.movementTracking.movementStatistics.totalRoutePoints}'),
              _buildInfoRow('Total Distance', '${widget.group.movementTracking.movementStatistics.totalDistancePixels.toStringAsFixed(1)} px'),
              _buildInfoRow('Average Speed', '${widget.group.movementTracking.movementStatistics.averageVelocity.toStringAsFixed(1)} px/s'),
              _buildInfoRow('Max Speed', '${widget.group.movementTracking.movementStatistics.maxVelocity.toStringAsFixed(1)} px/s'),
              _buildInfoRow('Frame Rate', '${widget.group.temporalSpan.framesPerSecond.toStringAsFixed(1)} fps'),
            ],
          ),
        ],
      ),
    );
  }

  /// Header card with key metrics and visual indicators
  Widget _buildHeaderCard() {
    return Card(
      elevation: 4,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          gradient: LinearGradient(
            colors: [
              widget.group.distanceColor.withOpacity(0.1),
              widget.group.distanceColor.withOpacity(0.05),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: Column(
          children: [
            // Person icon and ID
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: widget.group.distanceColor,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.person, color: Colors.white, size: 24),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.group.personId,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        getDistanceCategoryName(widget.group.closestDistance),
                        style: TextStyle(
                          fontSize: 14,
                          color: widget.group.distanceColor,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                Text(
                  '${widget.group.closestDistance.toStringAsFixed(1)}m',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: widget.group.distanceColor,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            
            // Key metrics row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildMetricColumn('Faces', '${widget.group.faceCount}', Icons.face),
                _buildMetricColumn('Quality', '${widget.group.qualityMetrics.averageQuality.toStringAsFixed(0)}', Icons.star),
                _buildMetricColumn('Duration', '${widget.group.temporalSpan.durationSeconds.toStringAsFixed(1)}s', Icons.timer),
                _buildMetricColumn('Movement', '${widget.group.movementTracking.movementStatistics.totalDistancePixels.toStringAsFixed(0)}px', Icons.timeline),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Representative Faces Tab: Visual gallery with quality information
  Widget _buildFacesTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with face count
          Row(
            children: [
              const Icon(Icons.face, size: 24),
              const SizedBox(width: 8),
              Text(
                'Representative Faces (${widget.group.representativeFaces.length})',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Faces grid
          Expanded(
            child: widget.group.representativeFaces.isEmpty
                ? const Center(
                    child: Text(
                      'No representative faces available',
                      style: TextStyle(fontSize: 16, color: Colors.grey),
                    ),
                  )
                : GridView.builder(
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      childAspectRatio: 0.8,
                      crossAxisSpacing: 16,
                      mainAxisSpacing: 16,
                    ),
                    itemCount: widget.group.representativeFaces.length,
                    itemBuilder: (context, index) {
                      final face = widget.group.representativeFaces[index];
                      return _buildRepresentativeFaceCard(face);
                    },
                  ),
          ),
        ],
      ),
    );
  }

  /// Movement Analysis Tab: Route visualization and statistics
  Widget _buildMovementTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(Icons.timeline, size: 24),
              const SizedBox(width: 8),
              const Text(
                'Movement Analysis',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Movement statistics card
          _buildMovementStatisticsCard(),
          const SizedBox(height: 16),
          
          // Route visualization placeholder
          Expanded(
            child: Card(
              child: Container(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.map, size: 20),
                        const SizedBox(width: 8),
                        const Text(
                          'Route Visualization',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    Expanded(
                      child: widget.group.movementTracking.routePoints.isEmpty
                          ? const Center(
                              child: Text(
                                'No route data available',
                                style: TextStyle(fontSize: 16, color: Colors.grey),
                              ),
                            )
                          : _buildRouteVisualization(),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Quality Analysis Tab: Quality metrics and scoring details
  Widget _buildQualityTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(Icons.assessment, size: 24),
              const SizedBox(width: 8),
              const Text(
                'Quality Analysis',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Quality metrics overview
          _buildInfoCard(
            'Quality Metrics',
            Icons.star,
            [
              _buildInfoRow('Average Quality', '${widget.group.qualityMetrics.averageQuality.toStringAsFixed(1)} (${getQualityLevelName(widget.group.qualityMetrics.averageQuality)})'),
              _buildInfoRow('Best Quality', '${widget.group.qualityMetrics.maxQuality.toStringAsFixed(1)}'),
              _buildInfoRow('Lowest Quality', '${widget.group.qualityMetrics.minQuality.toStringAsFixed(1)}'),
              _buildInfoRow('Quality Range', '${(widget.group.qualityMetrics.maxQuality - widget.group.qualityMetrics.minQuality).toStringAsFixed(1)} points'),
              _buildInfoRow('Consistency', '${widget.group.qualityMetrics.qualityConsistency.toStringAsFixed(1)}%'),
            ],
          ),
          const SizedBox(height: 16),
          
          // Selection criteria
          if (widget.group.representativeFaces.isNotEmpty)
            _buildSelectionCriteriaCard(),
          const SizedBox(height: 16),
          
          // Face quality breakdown
          _buildFaceQualityBreakdown(),
        ],
      ),
    );
  }

  /// Build info card with title and rows
  Widget _buildInfoCard(String title, IconData icon, List<Widget> children) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...children,
          ],
        ),
      ),
    );
  }

  /// Build info row with label and value
  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: const TextStyle(
                fontWeight: FontWeight.w500,
                color: Colors.grey,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w400),
            ),
          ),
        ],
      ),
    );
  }

  /// Build metric column for header card
  Widget _buildMetricColumn(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, size: 24, color: Colors.grey[600]),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }

  /// Build representative face card
  Widget _buildRepresentativeFaceCard(RepresentativeFace face) {
    return Card(
      elevation: 3,
      child: Column(
        children: [
          // Face placeholder (in real implementation, would show actual face image)
          Expanded(
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: getDistanceColor(face.distance).withOpacity(0.1),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.face,
                    size: 48,
                    color: getDistanceColor(face.distance),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '#${face.selectionRank}',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: getDistanceColor(face.distance),
                    ),
                  ),
                ],
              ),
            ),
          ),
          
          // Face details
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Quality: ${face.qualityScore.toStringAsFixed(1)}',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    Text(
                      '${face.distance.toStringAsFixed(1)}m',
                      style: TextStyle(
                        color: getDistanceColor(face.distance),
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Conf: ${(face.confidence * 100).toStringAsFixed(0)}%',
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                    Text(
                      'Area: ${face.faceArea.toStringAsFixed(0)}px²',
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Build movement statistics card
  Widget _buildMovementStatisticsCard() {
    final stats = widget.group.movementTracking.movementStatistics;
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.analytics, size: 20),
                SizedBox(width: 8),
                Text(
                  'Movement Statistics',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            // Statistics grid
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              childAspectRatio: 3,
              crossAxisSpacing: 16,
              mainAxisSpacing: 8,
              children: [
                _buildStatItem('Route Points', '${stats.totalRoutePoints}', Icons.place),
                _buildStatItem('Total Distance', '${stats.totalDistancePixels.toStringAsFixed(0)}px', Icons.straighten),
                _buildStatItem('Avg Velocity', '${stats.averageVelocity.toStringAsFixed(1)}px/s', Icons.speed),
                _buildStatItem('Max Velocity', '${stats.maxVelocity.toStringAsFixed(1)}px/s', Icons.fast_forward),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Build individual stat item
  Widget _buildStatItem(String label, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.grey[100],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: Colors.grey[600]),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 10,
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Build route visualization (simplified)
  Widget _buildRouteVisualization() {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey[300]!),
        borderRadius: BorderRadius.circular(8),
      ),
      child: CustomPaint(
        painter: RouteVisualizationPainter(widget.group.movementTracking.routePoints),
        child: const SizedBox.expand(),
      ),
    );
  }

  /// Build selection criteria card
  Widget _buildSelectionCriteriaCard() {
    final criteria = widget.group.representativeFaces.first.selectionCriteria;
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.tune, size: 20),
                SizedBox(width: 8),
                Text(
                  'Selection Criteria',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            _buildCriteriaBar('Distance Weight', criteria.distanceWeight),
            _buildCriteriaBar('Confidence Weight', criteria.confidenceWeight),
            _buildCriteriaBar('Area Weight', criteria.areaWeight),
            _buildCriteriaBar('Position Weight', criteria.positionWeight),
          ],
        ),
      ),
    );
  }

  /// Build criteria weight bar
  Widget _buildCriteriaBar(String label, double weight) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: const TextStyle(fontSize: 14)),
              Text('${(weight * 100).toStringAsFixed(0)}%', 
                   style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: weight,
            backgroundColor: Colors.grey[300],
            valueColor: AlwaysStoppedAnimation<Color>(widget.group.distanceColor),
          ),
        ],
      ),
    );
  }

  /// Build face quality breakdown
  Widget _buildFaceQualityBreakdown() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.bar_chart, size: 20),
                SizedBox(width: 8),
                Text(
                  'Face Quality Breakdown',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            ...widget.group.representativeFaces.map((face) => 
              _buildQualityItem(face)).toList(),
            
            if (widget.group.representativeFaces.isEmpty)
              const Text(
                'No quality data available',
                style: TextStyle(color: Colors.grey),
              ),
          ],
        ),
      ),
    );
  }

  /// Build individual quality item
  Widget _buildQualityItem(RepresentativeFace face) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: getDistanceColor(face.distance),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                '${face.selectionRank}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Rank ${face.selectionRank} - Quality: ${face.qualityScore.toStringAsFixed(1)}',
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
                Text(
                  'Distance: ${face.distance.toStringAsFixed(1)}m, Confidence: ${(face.confidence * 100).toStringAsFixed(0)}%',
                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                ),
              ],
            ),
          ),
          Text(
            getQualityLevelName(face.qualityScore),
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: getDistanceColor(face.distance),
            ),
          ),
        ],
      ),
    );
  }
}

/// Custom painter for route visualization
class RouteVisualizationPainter extends CustomPainter {
  final List<RoutePoint> routePoints;

  RouteVisualizationPainter(this.routePoints);

  @override
  void paint(Canvas canvas, Size size) {
    if (routePoints.length < 2) {
      // Draw "No route data" message
      final textPainter = TextPainter(
        text: const TextSpan(
          text: 'No route data available',
          style: TextStyle(color: Colors.grey, fontSize: 16),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(
        canvas, 
        Offset(
          (size.width - textPainter.width) / 2,
          (size.height - textPainter.height) / 2,
        ),
      );
      return;
    }

    // Calculate bounds for scaling
    double minX = routePoints.map((p) => p.centerX).reduce(math.min);
    double maxX = routePoints.map((p) => p.centerX).reduce(math.max);
    double minY = routePoints.map((p) => p.centerY).reduce(math.min);
    double maxY = routePoints.map((p) => p.centerY).reduce(math.max);

    // Add padding
    const padding = 20.0;
    double scaleX = (size.width - 2 * padding) / (maxX - minX);
    double scaleY = (size.height - 2 * padding) / (maxY - minY);
    double scale = math.min(scaleX, scaleY);

    // Draw route path
    final routePaint = Paint()
      ..color = Colors.blue.withOpacity(0.7)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    final path = Path();
    for (int i = 0; i < routePoints.length; i++) {
      final point = routePoints[i];
      final x = padding + (point.centerX - minX) * scale;
      final y = padding + (point.centerY - minY) * scale;

      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.drawPath(path, routePaint);

    // Draw start point (green)
    final startPoint = routePoints.first;
    final startX = padding + (startPoint.centerX - minX) * scale;
    final startY = padding + (startPoint.centerY - minY) * scale;
    canvas.drawCircle(
      Offset(startX, startY),
      6.0,
      Paint()..color = Colors.green,
    );

    // Draw end point (red)
    final endPoint = routePoints.last;
    final endX = padding + (endPoint.centerX - minX) * scale;
    final endY = padding + (endPoint.centerY - minY) * scale;
    canvas.drawCircle(
      Offset(endX, endY),
      6.0,
      Paint()..color = Colors.red,
    );

    // Draw intermediate points
    for (int i = 1; i < routePoints.length - 1; i++) {
      final point = routePoints[i];
      final x = padding + (point.centerX - minX) * scale;
      final y = padding + (point.centerY - minY) * scale;
      
      canvas.drawCircle(
        Offset(x, y),
        3.0,
        Paint()..color = Colors.blue.withOpacity(0.5),
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
import 'package:flutter/material.dart';
import '../services/vision_processing_service.dart';
import '../core/theme/app_theme.dart';
import '../screens/person_objects_detail_screen.dart';
import '../models/cross_video_analysis_models.dart';

/// Dialog showing vision processing results with MVR people count
class VisionResultsDialog extends StatelessWidget {
  final VisionProcessingResult result;
  
  const VisionResultsDialog({
    Key? key,
    required this.result,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      title: Row(
        children: [
          Icon(
            result.success ? Icons.check_circle : Icons.error,
            color: result.success ? AppColors.success : AppColors.error,
            size: 32,
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(
              result.success 
                  ? 'Vision Processing Complete' 
                  : 'Processing Completed with Errors',
              style: AppTextStyles.h4,
            ),
          ),
        ],
      ),
      content: Container(
        width: double.maxFinite,
        constraints: const BoxConstraints(maxWidth: 600),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Summary card
              _buildSummaryCard(context),
              
              const SizedBox(height: AppSpacing.lg),
              
              // MVR People count (highlighted)
              _buildMVRCountCard(context),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Processing breakdown
              _buildProcessingBreakdown(context),
              
              // Failures section (if any)
              if (result.failedMedia > 0) ...[
                const SizedBox(height: AppSpacing.lg),
                _buildFailuresSection(context),
              ],
              
              const SizedBox(height: AppSpacing.lg),
              
              // Additional statistics
              _buildStatisticsSection(context),
            ],
          ),
        ),
      ),
      actions: [
        if (result.failedMedia > 0)
          TextButton(
            onPressed: () => _showDetailedFailures(context),
            child: const Text('View Failed Items'),
          ),
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Dismiss'),
        ),
        ElevatedButton.icon(
          onPressed: result.mvrPeopleCount > 0
              ? () => _navigateToMVRAnalysis(context)
              : null,
          icon: const Icon(Icons.people),
          label: const Text('View MVR People'),
        ),
      ],
    );
  }
  
  Widget _buildSummaryCard(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.primary.withOpacity(0.1),
            AppColors.primary.withOpacity(0.05),
          ],
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AppColors.primary.withOpacity(0.3),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStatItem(
            context,
            icon: Icons.photo_library,
            label: 'Processed',
            value: '${result.processedMedia}',
            color: AppColors.success,
          ),
          _buildStatItem(
            context,
            icon: Icons.error_outline,
            label: 'Failed',
            value: '${result.failedMedia}',
            color: AppColors.error,
          ),
          _buildStatItem(
            context,
            icon: Icons.face,
            label: 'Total Faces',
            value: _getTotalFaces().toString(),
            color: AppColors.info,
          ),
        ],
      ),
    );
  }
  
  Widget _buildMVRCountCard(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xl),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.success.withOpacity(0.9),
            AppColors.success,
          ],
        ),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: AppColors.success.withOpacity(0.3),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.people,
            color: Colors.white,
            size: 56,
          ),
          const SizedBox(width: AppSpacing.lg),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'MVR People Created',
                style: AppTextStyles.h6.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                '${result.mvrPeopleCount}',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 56,
                  fontWeight: FontWeight.bold,
                  height: 1.0,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildProcessingBreakdown(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Processing Breakdown',
          style: AppTextStyles.h6.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Details for each media item:',
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        ...result.results.take(10).map((r) => _buildMediaResultTile(context, r)),
        if (result.results.length > 10)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: Text(
              'and ${result.results.length - 10} more...',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
      ],
    );
  }
  
  Widget _buildMediaResultTile(BuildContext context, MediaProcessingResult media) {
    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: ListTile(
        leading: Icon(
          media.isSuccess ? Icons.check_circle : Icons.error,
          color: media.isSuccess ? AppColors.success : AppColors.error,
        ),
        title: Text(
          'Media ${_truncateUuid(media.mediaUuid)}... (${media.mediaType})',
          style: AppTextStyles.bodyMedium,
        ),
        subtitle: Text(
          media.isSuccess
              ? '${media.mvrPeopleCount} MVR people • ${media.totalFacesDetected} faces detected'
              : media.error ?? 'Processing failed',
          style: AppTextStyles.bodySmall.copyWith(
            color: media.isSuccess ? AppColors.textSecondary : AppColors.error,
          ),
        ),
        trailing: media.isSuccess
            ? Icon(Icons.face, color: AppColors.textSecondary)
            : Icon(Icons.warning, color: AppColors.error),
      ),
    );
  }
  
  Widget _buildFailuresSection(BuildContext context) {
    final failedResults = result.results.where((r) => r.isFailed).toList();
    
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.error.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.error.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning, color: AppColors.error, size: 20),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'Failed Items (${failedResults.length})',
                style: AppTextStyles.subtitle2.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppColors.error,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          ...failedResults.take(3).map((r) => Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text(
              '• ${_truncateUuid(r.mediaUuid)}: ${r.error ?? "Unknown error"}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.error,
              ),
            ),
          )),
          if (failedResults.length > 3)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: TextButton(
                onPressed: () => _showDetailedFailures(context),
                child: Text('View all ${failedResults.length} failed items'),
              ),
            ),
        ],
      ),
    );
  }
  
  Widget _buildStatisticsSection(BuildContext context) {
    final stats = result.aggregateStatistics;
    final avgProcessingMs = stats['avg_processing_ms']?.toDouble() ?? 0.0;
    final totalProcessingMs = stats['total_processing_ms']?.toDouble() ?? 0.0;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Statistics',
          style: AppTextStyles.h6.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.surfaceVariant,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              _buildStatRow(
                'Total Individuals Detected',
                '${stats['total_individuals_detected'] ?? 0}',
              ),
              _buildStatRow(
                'Avg Processing Time',
                avgProcessingMs > 0 
                    ? '${(avgProcessingMs / 1000).toStringAsFixed(1)}s'
                    : '${result.processingTimeSeconds.toStringAsFixed(1)}s',
              ),
              _buildStatRow(
                'Total Processing Time',
                totalProcessingMs > 0
                    ? '${(totalProcessingMs / 1000).toStringAsFixed(1)}s'
                    : '${result.processingTimeSeconds.toStringAsFixed(1)}s',
              ),
            ],
          ),
        ),
      ],
    );
  }
  
  Widget _buildStatItem(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        const SizedBox(height: AppSpacing.xs),
        Text(
          value,
          style: AppTextStyles.h5.copyWith(
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: AppTextStyles.caption.copyWith(
            color: AppColors.textSecondary,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
  
  Widget _buildStatRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          Text(
            value,
            style: AppTextStyles.bodyMedium.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
  
  int _getTotalFaces() {
    return result.results.fold<int>(
      0,
      (sum, r) => sum + r.totalFacesDetected,
    );
  }
  
  String _truncateUuid(String uuid) {
    if (uuid.isEmpty) return 'unknown';
    return uuid.length > 8 ? uuid.substring(0, 8) : uuid;
  }
  
  void _showDetailedFailures(BuildContext context) {
    final failedResults = result.results.where((r) => r.isFailed).toList();
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Failed Items Detail'),
        content: Container(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: failedResults.length,
            itemBuilder: (context, index) {
              final item = failedResults[index];
              return ListTile(
                leading: Icon(Icons.error, color: AppColors.error),
                title: Text(item.mediaUuid),
                subtitle: Text(item.error ?? 'Unknown error'),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
  
  void _navigateToMVRAnalysis(BuildContext context) {
    // Close the dialog first
    Navigator.pop(context);
    
    // Collect all MVR people from results
    final List<Map<String, dynamic>> allMvrPeople = [];
    for (final mediaResult in result.results) {
      if (mediaResult.isSuccess && mediaResult.mvrPeople.isNotEmpty) {
        allMvrPeople.addAll(mediaResult.mvrPeople);
      }
    }
    
    if (allMvrPeople.isEmpty) {
      // Show error - shouldn't happen if button is properly disabled
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No MVR people data available'),
          backgroundColor: AppColors.error,
        ),
      );
      return;
    }
    
    // Extract MVR person UUIDs
    final List<String> mvrPersonUuids = allMvrPeople
        .map((mvr) => mvr['mvr_people_uuid'] as String?)
        .whereType<String>()
        .toList();
    
    print('📊 Navigating to Cross-Video Analysis with ${mvrPersonUuids.length} MVR people');
    
    // Create session data with search results format
    final sessionData = {
      'search_results': allMvrPeople,
      'total_mvr_people': allMvrPeople.length,
      'total_appearances': allMvrPeople.fold<int>(
        0,
        (sum, mvr) => sum + ((mvr['total_appearances'] as int?) ?? 0),
      ),
      'search_parameters': {
        'source': 'vision_processing',
        'media_count': result.processedMedia,
        'processing_time': result.processingTimeSeconds,
      },
      'collection_name': 'Vision Processed Media',
      'processing_timestamp': DateTime.now().toIso8601String(),
    };
    
    // Create context for Cross-Video Analysis screen
    final analysisContext = CrossVideoAnalysisContext(
      individualUuids: mvrPersonUuids,
      sessionUuid: 'vision_${DateTime.now().millisecondsSinceEpoch}',
      sessionData: sessionData,
    );
    
    // Navigate to PersonObjectsDetailScreen
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (ctx) => PersonObjectsDetailScreen(
          crossVideoContext: analysisContext,
        ),
      ),
    );
  }
}

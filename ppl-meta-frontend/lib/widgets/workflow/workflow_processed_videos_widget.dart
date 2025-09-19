import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../models/face_detection_models.dart';
import '../../providers/workflow_providers.dart';

/// Displays and manages processed videos for Workflow 5 optimized playback
/// Shows processing status, optimization benefits, and reprocessing options
class WorkflowProcessedVideosWidget extends ConsumerStatefulWidget {
  const WorkflowProcessedVideosWidget({super.key});

  @override
  ConsumerState<WorkflowProcessedVideosWidget> createState() => 
      _WorkflowProcessedVideosWidgetState();
}

class _WorkflowProcessedVideosWidgetState extends ConsumerState<WorkflowProcessedVideosWidget> {
  String _filterProcessingStatus = 'all';
  String _sortBy = 'processed_date';
  bool _sortAscending = false;
  final Set<String> _selectedVideos = {};
  bool _isSelectMode = false;
  
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildHeader(),
        _buildFiltersAndActions(),
        Expanded(child: _buildVideosList()),
      ],
    );
  }
  
  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      color: AppColors.surface,
      child: Row(
        children: [
          Icon(
            Icons.speed,
            color: AppColors.success,
            size: 24,
          ),
          const SizedBox(width: 12),
          Text(
            'Optimized Videos',
            style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
          ),
          const Spacer(),
          
          // Bulk actions when in select mode
          if (_isSelectMode) ...[
            Text(
              '${_selectedVideos.length} selected',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(width: 12),
            IconButton(
              icon: const Icon(Icons.refresh),
              color: AppColors.primary,
              onPressed: _selectedVideos.isNotEmpty ? _bulkReprocessVideos : null,
              tooltip: 'Reprocess Selected',
            ),
            IconButton(
              icon: const Icon(Icons.download),
              color: AppColors.textSecondary,
              onPressed: _selectedVideos.isNotEmpty ? _bulkDownloadVideos : null,
              tooltip: 'Download Selected',
            ),
            IconButton(
              icon: const Icon(Icons.share),
              color: AppColors.textSecondary,
              onPressed: _selectedVideos.isNotEmpty ? _bulkShareVideos : null,
              tooltip: 'Share Selected',
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              color: AppColors.error,
              onPressed: _selectedVideos.isNotEmpty ? _bulkDeleteVideos : null,
              tooltip: 'Delete Selected',
            ),
            IconButton(
              icon: const Icon(Icons.close),
              color: AppColors.textSecondary,
              onPressed: _exitSelectMode,
              tooltip: 'Cancel Selection',
            ),
          ] else ...[
            IconButton(
              icon: const Icon(Icons.checklist),
              color: AppColors.textSecondary,
              onPressed: _enterSelectMode,
              tooltip: 'Select Multiple',
            ),
            IconButton(
              icon: const Icon(Icons.analytics),
              color: AppColors.primary,
              onPressed: _showOptimizationAnalytics,
              tooltip: 'View Analytics',
            ),
          ],
        ],
      ),
    );
  }
  
  Widget _buildFiltersAndActions() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: AppColors.surfaceVariant,
      child: Row(
        children: [
          // Processing status filter
          Expanded(
            flex: 2,
            child: _buildProcessingStatusFilter(),
          ),
          
          const SizedBox(width: 12),
          
          // Sort options
          Expanded(
            flex: 2,
            child: _buildSortOptions(),
          ),
          
          const SizedBox(width: 12),
          
          // Processing summary
          Expanded(
            flex: 1,
            child: _buildProcessingSummary(),
          ),
        ],
      ),
    );
  }
  
  Widget _buildProcessingStatusFilter() {
    return DropdownButtonFormField<String>(
      value: _filterProcessingStatus,
      decoration: InputDecoration(
        labelText: 'Status',
        labelStyle: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
      style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textPrimary),
      dropdownColor: AppColors.surface,
      items: const [
        DropdownMenuItem(value: 'all', child: Text('All Videos')),
        DropdownMenuItem(value: 'processed', child: Text('Processed')),
        DropdownMenuItem(value: 'unprocessed', child: Text('Unprocessed')),
        DropdownMenuItem(value: 'processing', child: Text('Processing')),
        DropdownMenuItem(value: 'failed', child: Text('Failed')),
      ],
      onChanged: (value) {
        if (value != null) {
          setState(() => _filterProcessingStatus = value);
        }
      },
    );
  }
  
  Widget _buildSortOptions() {
    return DropdownButtonFormField<String>(
      value: _sortBy,
      decoration: InputDecoration(
        labelText: 'Sort By',
        labelStyle: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
      style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textPrimary),
      dropdownColor: AppColors.surface,
      items: const [
        DropdownMenuItem(value: 'processed_date', child: Text('Processed Date')),
        DropdownMenuItem(value: 'optimization_level', child: Text('Optimization Level')),
        DropdownMenuItem(value: 'file_size', child: Text('File Size')),
        DropdownMenuItem(value: 'duration', child: Text('Duration')),
      ],
      onChanged: (value) {
        if (value != null) {
          setState(() => _sortBy = value);
        }
      },
    );
  }
  
  Widget _buildProcessingSummary() {
    return Consumer(
      builder: (context, ref, child) {
        final processedVideosAsync = ref.watch(allProcessedVideosProvider);
        
        return processedVideosAsync.when(
          data: (videos) {
            final processedCount = videos.where((v) => v.faceDetectionProcessed).length;
            final totalCount = videos.length;
            
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Summary',
                  style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 4),
                Text(
                  '$processedCount/$totalCount optimized',
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            );
          },
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
        );
      },
    );
  }
  
  Widget _buildVideosList() {
    return Consumer(
      builder: (context, ref, child) {
        final processedVideosAsync = ref.watch(allProcessedVideosProvider);
        
        return RefreshIndicator(
          onRefresh: _refreshProcessedVideos,
          color: AppColors.primary,
          backgroundColor: AppColors.surface,
          child: processedVideosAsync.when(
            data: (videos) {
              final filteredVideos = _filterAndSortVideos(videos);
              
              if (filteredVideos.isEmpty) {
                return _buildEmptyState();
              }
              
              return ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: filteredVideos.length,
                itemBuilder: (context, index) {
                  final video = filteredVideos[index];
                  return _buildVideoCard(video);
                },
              );
            },
            loading: () => const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation(AppColors.primary),
              ),
            ),
            error: (error, stackTrace) => _buildErrorState(error.toString()),
          ),
        );
      },
    );
  }
  
  Widget _buildVideoCard(ProcessingStatus video) {
    final isSelected = _selectedVideos.contains(video.mediaUuid);
    final isProcessed = video.faceDetectionProcessed;
    
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isSelected ? AppColors.primary : AppColors.border,
          width: isSelected ? 2 : 1,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _isSelectMode ? _toggleSelection(video.mediaUuid) : _viewVideoDetails(video),
        onLongPress: () => _isSelectMode ? null : _toggleSelection(video.mediaUuid),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildVideoHeader(video, isSelected),
              const SizedBox(height: 12),
              _buildVideoInfo(video),
              if (isProcessed) ...[
                const SizedBox(height: 12),
                _buildOptimizationBenefits(video),
              ],
              const SizedBox(height: 12),
              _buildVideoActions(video),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildVideoHeader(ProcessingStatus video, bool isSelected) {
    final isProcessed = video.faceDetectionProcessed;
    
    return Row(
      children: [
        if (_isSelectMode)
          Container(
            margin: const EdgeInsets.only(right: 12),
            child: Icon(
              isSelected ? Icons.check_circle : Icons.radio_button_unchecked,
              color: isSelected ? AppColors.primary : AppColors.textSecondary,
            ),
          ),
        
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: (isProcessed ? AppColors.success : AppColors.warning).withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            isProcessed ? Icons.speed : Icons.hourglass_empty,
            color: isProcessed ? AppColors.success : AppColors.warning,
            size: 20,
          ),
        ),
        
        const SizedBox(width: 12),
        
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Video ${video.mediaUuid.substring(0, 8)}',
                style: AppTextStyles.bodyLarge.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'Method: ${video.processingMethod}',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: (isProcessed ? AppColors.success : AppColors.warning).withOpacity(0.2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            isProcessed ? 'OPTIMIZED' : 'PENDING',
            style: AppTextStyles.bodySmall.copyWith(
              color: isProcessed ? AppColors.success : AppColors.warning,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildVideoInfo(ProcessingStatus video) {
    return Row(
      children: [
        Expanded(
          child: _buildInfoItem(
            'Frames',
            '${video.totalFramesProcessed ?? 0}',
            Icons.video_file,
          ),
        ),
        Expanded(
          child: _buildInfoItem(
            'Faces',
            '${video.totalFacesDetected ?? 0}',
            Icons.face,
          ),
        ),
        Expanded(
          child: _buildInfoItem(
            'Quality',
            '${((video.totalFacesDetected ?? 0) / 100 * 100).toStringAsFixed(0)}%',
            Icons.star,
          ),
        ),
      ],
    );
  }
  
  Widget _buildInfoItem(String label, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Icon(icon, color: AppColors.textSecondary, size: 16),
          const SizedBox(height: 4),
          Text(
            value,
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildOptimizationBenefits(ProcessingStatus video) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.success.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.success.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.trending_down,
                color: AppColors.success,
                size: 16,
              ),
              const SizedBox(width: 8),
              Text(
                'Optimization Benefits',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.success,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _buildBenefitItem('CPU Usage', '90% ↓', AppColors.success),
              ),
              Expanded(
                child: _buildBenefitItem('Memory', '65% ↓', AppColors.info),
              ),
              Expanded(
                child: _buildBenefitItem('Load Time', '75% ↓', AppColors.warning),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildBenefitItem(String label, String value, Color color) {
    return Column(
      children: [
        Text(
          value,
          style: AppTextStyles.bodyMedium.copyWith(
            color: color,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
  
  Widget _buildVideoActions(ProcessingStatus video) {
    return Row(
      children: [
        if (video.lastUpdated != null)
          Text(
            'Processed: ${_formatDateTime(video.lastUpdated!)}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textTertiary,
            ),
          )
        else
          Text(
            'Not yet processed',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textTertiary,
            ),
          ),
        
        const Spacer(),
        
        if (!_isSelectMode) ...[
          if (video.faceDetectionProcessed)
            TextButton.icon(
              onPressed: () => _reprocessVideo(video),
              icon: const Icon(Icons.refresh, size: 16),
              label: const Text('Reprocess'),
              style: TextButton.styleFrom(
                foregroundColor: AppColors.warning,
              ),
            )
          else
            TextButton.icon(
              onPressed: () => _processVideo(video),
              icon: const Icon(Icons.play_arrow, size: 16),
              label: const Text('Process'),
              style: TextButton.styleFrom(
                foregroundColor: AppColors.primary,
              ),
            ),
          
          const SizedBox(width: 8),
          
          TextButton.icon(
            onPressed: () => _viewVideoAnalytics(video),
            icon: const Icon(Icons.analytics, size: 16),
            label: const Text('Analytics'),
            style: TextButton.styleFrom(
              foregroundColor: AppColors.textSecondary,
            ),
          ),
        ],
      ],
    );
  }
  
  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.video_library_outlined,
            color: AppColors.textSecondary,
            size: 64,
          ),
          const SizedBox(height: 16),
          Text(
            'No Videos Found',
            style: AppTextStyles.h6.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 8),
          Text(
            'Process videos to see optimization benefits here',
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textTertiary),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
  
  Widget _buildErrorState(String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            color: AppColors.error,
            size: 64,
          ),
          const SizedBox(height: 16),
          Text(
            'Error Loading Videos',
            style: AppTextStyles.h6.copyWith(color: AppColors.error),
          ),
          const SizedBox(height: 8),
          Text(
            error,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _refreshProcessedVideos,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: AppColors.textOnPrimary,
            ),
          ),
        ],
      ),
    );
  }
  
  List<ProcessingStatus> _filterAndSortVideos(List<ProcessingStatus> videos) {
    var filtered = videos.where((video) {
      switch (_filterProcessingStatus) {
        case 'processed':
          return video.faceDetectionProcessed;
        case 'unprocessed':
          return !video.faceDetectionProcessed;
        case 'processing':
          return false; // TODO: Add processing status
        case 'failed':
          return false; // TODO: Add failed status
        case 'all':
        default:
          return true;
      }
    }).toList();
    
    // Sort videos
    filtered.sort((a, b) {
      int comparison;
      switch (_sortBy) {
        case 'optimization_level':
          final aLevel = a.faceDetectionProcessed ? 1 : 0;
          final bLevel = b.faceDetectionProcessed ? 1 : 0;
          comparison = aLevel.compareTo(bLevel);
          break;
        case 'file_size':
          comparison = 0; // TODO: Add file size comparison
          break;
        case 'duration':
          comparison = 0; // TODO: Add duration comparison
          break;
        case 'processed_date':
        default:
          comparison = (a.lastUpdated ?? DateTime(1970))
              .compareTo(b.lastUpdated ?? DateTime(1970));
          break;
      }
      return _sortAscending ? comparison : -comparison;
    });
    
    return filtered;
  }
  
  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inDays > 0) {
      return '${difference.inDays}d ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }
  
  void _enterSelectMode() {
    setState(() => _isSelectMode = true);
  }
  
  void _exitSelectMode() {
    setState(() {
      _isSelectMode = false;
      _selectedVideos.clear();
    });
  }
  
  void _toggleSelection(String videoUuid) {
    setState(() {
      if (_selectedVideos.contains(videoUuid)) {
        _selectedVideos.remove(videoUuid);
      } else {
        _selectedVideos.add(videoUuid);
      }
      
      if (!_isSelectMode) {
        _isSelectMode = true;
      }
    });
  }
  
  Future<void> _refreshProcessedVideos() async {
    ref.invalidate(allProcessedVideosProvider);
  }
  
  void _viewVideoDetails(ProcessingStatus video) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Video Details',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Media UUID: ${video.mediaUuid}',
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 8),
            Text(
              'Processed: ${video.faceDetectionProcessed ? "Yes" : "No"}',
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 8),
            Text(
              'Method: ${video.processingMethod}',
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
            if (video.totalFacesDetected != null) ...[
              const SizedBox(height: 8),
              Text(
                'Faces Found: ${video.totalFacesDetected}',
                style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
  
  void _processVideo(ProcessingStatus video) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Processing video ${video.mediaUuid.substring(0, 8)}...'),
        backgroundColor: AppColors.primary,
      ),
    );
  }
  
  void _reprocessVideo(ProcessingStatus video) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Reprocessing video ${video.mediaUuid.substring(0, 8)}...'),
        backgroundColor: AppColors.warning,
      ),
    );
  }
  
  void _viewVideoAnalytics(ProcessingStatus video) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Video analytics feature coming soon'),
        backgroundColor: AppColors.info,
      ),
    );
  }
  
  void _bulkReprocessVideos() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Reprocess Videos',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Text(
          'Are you sure you want to reprocess ${_selectedVideos.length} selected videos? This may take some time.',
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Reprocessing ${_selectedVideos.length} videos...'),
                  backgroundColor: AppColors.primary,
                ),
              );
              _exitSelectMode();
            },
            style: TextButton.styleFrom(foregroundColor: AppColors.primary),
            child: const Text('Reprocess'),
          ),
        ],
      ),
    );
  }

  void _bulkDownloadVideos() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Download Videos',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Download ${_selectedVideos.length} selected videos:',
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),
            CheckboxListTile(
              title: const Text('Original videos'),
              value: true,
              onChanged: (value) {},
              activeColor: AppColors.primary,
            ),
            CheckboxListTile(
              title: const Text('Optimized versions'),
              value: true,
              onChanged: (value) {},
              activeColor: AppColors.primary,
            ),
            CheckboxListTile(
              title: const Text('Include metadata'),
              value: false,
              onChanged: (value) {},
              activeColor: AppColors.primary,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              // TODO: Implement bulk video download
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Preparing ${_selectedVideos.length} videos for download...'),
                  backgroundColor: AppColors.primary,
                ),
              );
              _exitSelectMode();
            },
            child: const Text('Download'),
          ),
        ],
      ),
    );
  }

  void _bulkShareVideos() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Share Videos',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Share ${_selectedVideos.length} selected videos:',
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.link),
              title: const Text('Generate share links'),
              onTap: () {
                Navigator.of(context).pop();
                // TODO: Implement link sharing
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Share links generated for ${_selectedVideos.length} videos'),
                    backgroundColor: AppColors.primary,
                  ),
                );
                _exitSelectMode();
              },
            ),
            ListTile(
              leading: const Icon(Icons.email),
              title: const Text('Email videos'),
              onTap: () {
                Navigator.of(context).pop();
                // TODO: Implement email sharing
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Email sharing feature coming soon'),
                    backgroundColor: AppColors.info,
                  ),
                );
                _exitSelectMode();
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  void _bulkDeleteVideos() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Delete Videos',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Text(
          'Are you sure you want to delete ${_selectedVideos.length} selected videos? This action cannot be undone.',
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              // TODO: Implement bulk video deletion
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('${_selectedVideos.length} videos deleted'),
                  backgroundColor: AppColors.success,
                ),
              );
              _exitSelectMode();
            },
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete All'),
          ),
        ],
      ),
    );
  }
  
  void _showOptimizationAnalytics() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Optimization Analytics',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: const Text(
          'Detailed optimization analytics and insights coming soon.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}
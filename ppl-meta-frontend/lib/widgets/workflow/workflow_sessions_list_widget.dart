import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../models/face_detection_models.dart';
import '../../providers/workflow_providers.dart';

/// Displays and manages face detection sessions for Workflow 4
/// Provides session list, management actions, filtering, and bulk operations
class WorkflowSessionsListWidget extends ConsumerStatefulWidget {
  const WorkflowSessionsListWidget({super.key});

  @override
  ConsumerState<WorkflowSessionsListWidget> createState() => 
      _WorkflowSessionsListWidgetState();
}

class _WorkflowSessionsListWidgetState extends ConsumerState<WorkflowSessionsListWidget> {
  // UI State Variables
  String _selectedFilter = 'all';
  final Set<String> _selectedSessions = <String>{};
  bool _isSelectMode = false;
  String _filterStatus = 'all';
  String _sortBy = 'created_date'; // Fixed: was 'newest' which doesn't exist in dropdown
  bool _sortAscending = false;
  
  @override
  Widget build(BuildContext context) {
    final allSessionsAsync = ref.watch(allActiveSessionsProvider);
    
    return Column(
      children: [
        _buildHeader(),
        _buildFiltersAndActions(),
        Expanded(
          child: allSessionsAsync.when(
            data: (sessions) => _buildSessionsList(sessions),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stack) => Center(
              child: Text('Error loading sessions: $error'),
            ),
          ),
        ),
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
            Icons.play_circle_outline,
            color: AppColors.primary,
            size: 24,
          ),
          const SizedBox(width: 12),
          Text(
            'Face Detection Sessions',
            style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
          ),
          const Spacer(),
          
          // Bulk actions when in select mode
          if (_isSelectMode) ...[
            Text(
              '${_selectedSessions.length} selected',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(width: 12),
            IconButton(
              icon: const Icon(Icons.refresh),
              color: AppColors.primary,
              onPressed: _selectedSessions.isNotEmpty ? _bulkReprocessSessions : null,
              tooltip: 'Reprocess Selected',
            ),
            IconButton(
              icon: const Icon(Icons.archive_outlined),
              color: AppColors.textSecondary,
              onPressed: _selectedSessions.isNotEmpty ? _bulkArchiveSessions : null,
              tooltip: 'Archive Selected',
            ),
            IconButton(
              icon: const Icon(Icons.download),
              color: AppColors.textSecondary,
              onPressed: _selectedSessions.isNotEmpty ? _bulkExportSessions : null,
              tooltip: 'Export Selected',
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              color: AppColors.error,
              onPressed: _selectedSessions.isNotEmpty ? _bulkDeleteSessions : null,
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
              icon: const Icon(Icons.add),
              color: AppColors.primary,
              onPressed: _createNewSession,
              tooltip: 'New Session',
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
          // Status filter
          Expanded(
            flex: 2,
            child: _buildStatusFilter(),
          ),
          
          const SizedBox(width: 12),
          
          // Sort options
          Expanded(
            flex: 2,
            child: _buildSortOptions(),
          ),
          
          const SizedBox(width: 12),
          
          // Refresh button
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            color: AppColors.textSecondary,
            onPressed: _refreshSessions,
            tooltip: 'Refresh',
          ),
        ],
      ),
    );
  }
  
  Widget _buildStatusFilter() {
    return DropdownButtonFormField<String>(
      value: _filterStatus,
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
        DropdownMenuItem(value: 'all', child: Text('All Status')),
        DropdownMenuItem(value: 'active', child: Text('Active')),
        DropdownMenuItem(value: 'completed', child: Text('Completed')),
        DropdownMenuItem(value: 'failed', child: Text('Failed')),
        DropdownMenuItem(value: 'pending', child: Text('Pending')),
      ],
      onChanged: (value) {
        if (value != null) {
          setState(() => _filterStatus = value);
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
        DropdownMenuItem(value: 'created_date', child: Text('Created Date')),
        DropdownMenuItem(value: 'status', child: Text('Status')),
        DropdownMenuItem(value: 'frames_processed', child: Text('Frames Processed')),
        DropdownMenuItem(value: 'faces_detected', child: Text('Faces Detected')),
      ],
      onChanged: (value) {
        if (value != null) {
          setState(() => _sortBy = value);
        }
      },
    );
  }
  
  Widget _buildSessionsList(List<FaceDetectionSession> allSessions) {
    final filteredSessions = _filterAndSortSessions(allSessions);
    
    return RefreshIndicator(
      onRefresh: _refreshSessions,
      color: AppColors.primary,
      backgroundColor: AppColors.surface,
      child: filteredSessions.isEmpty
        ? _buildEmptyState()
        : ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: filteredSessions.length,
            itemBuilder: (context, index) {
              final session = filteredSessions[index];
              return _buildSessionCard(session);
            },
          ),
    );
  }
  
  Widget _buildSessionCard(FaceDetectionSession session) {
    final isSelected = _selectedSessions.contains(session.sessionUuid);
    
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
        onTap: () => _isSelectMode ? _toggleSelection(session.sessionUuid) : _viewSessionDetails(session),
        onLongPress: () => _isSelectMode ? null : _toggleSelection(session.sessionUuid),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildSessionHeader(session, isSelected),
              const SizedBox(height: 12),
              _buildSessionInfo(session),
              const SizedBox(height: 12),
              _buildSessionProgress(session),
              const SizedBox(height: 12),
              _buildSessionActions(session),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildSessionHeader(FaceDetectionSession session, bool isSelected) {
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
            color: _getSessionStatusColor(session.status).withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            _getSessionStatusIcon(session.status),
            color: _getSessionStatusColor(session.status),
            size: 20,
          ),
        ),
        
        const SizedBox(width: 12),
        
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Session ${session.sessionUuid.substring(0, 8)}',
                style: AppTextStyles.bodyLarge.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'Media: ${session.mediaUuid.substring(0, 8)}',
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
            color: _getSessionStatusColor(session.status).withOpacity(0.2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            session.status.toUpperCase(),
            style: AppTextStyles.bodySmall.copyWith(
              color: _getSessionStatusColor(session.status),
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildSessionInfo(FaceDetectionSession session) {
    return Row(
      children: [
        Expanded(
          child: _buildInfoItem(
            'Frames',
            '${session.totalFramesProcessed ?? 0}',
            Icons.video_file,
          ),
        ),
        Expanded(
          child: _buildInfoItem(
            'Faces',
            '${session.totalFacesDetected ?? 0}',
            Icons.face,
          ),
        ),
        Expanded(
          child: _buildInfoItem(
            'Confidence',
            '${((session.confidenceThreshold ?? 0.0) * 100).toStringAsFixed(0)}%',
            Icons.percent,
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
  
  Widget _buildSessionProgress(FaceDetectionSession session) {
    if (session.status != 'active') {
      return const SizedBox.shrink();
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Processing Progress',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const Spacer(),
            Text(
              'Running...',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.primary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        LinearProgressIndicator(
          backgroundColor: AppColors.gray800,
          valueColor: const AlwaysStoppedAnimation(AppColors.primary),
        ),
      ],
    );
  }
  
  Widget _buildSessionActions(FaceDetectionSession session) {
    return Row(
      children: [
        Text(
          'Created: ${_formatDateTime(session.createdAt)}',
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textTertiary,
          ),
        ),
        
        const Spacer(),
        
        if (!_isSelectMode) ...[
          if (session.status == 'active')
            TextButton.icon(
              onPressed: () => _stopSession(session),
              icon: const Icon(Icons.stop, size: 16),
              label: const Text('Stop'),
              style: TextButton.styleFrom(
                foregroundColor: AppColors.error,
              ),
            ),
          
          const SizedBox(width: 8),
          
          TextButton.icon(
            onPressed: () => _deleteSession(session),
            icon: const Icon(Icons.delete_outline, size: 16),
            label: const Text('Delete'),
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
            Icons.play_circle_outline,
            color: AppColors.textSecondary,
            size: 64,
          ),
          const SizedBox(height: 16),
          Text(
            'No Sessions Found',
            style: AppTextStyles.h6.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 8),
          Text(
            'Create a new face detection session to get started',
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textTertiary),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _createNewSession,
            icon: const Icon(Icons.add),
            label: const Text('Create Session'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: AppColors.textOnPrimary,
            ),
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
            'Error Loading Sessions',
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
            onPressed: _refreshSessions,
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
  
  List<FaceDetectionSession> _filterAndSortSessions(List<FaceDetectionSession> sessions) {
    var filtered = sessions.where((session) {
      if (_filterStatus == 'all') return true;
      return session.status.toLowerCase() == _filterStatus.toLowerCase();
    }).toList();
    
    // Sort sessions
    filtered.sort((a, b) {
      int comparison;
      switch (_sortBy) {
        case 'status':
          comparison = a.status.compareTo(b.status);
          break;
        case 'frames_processed':
          comparison = (a.totalFramesProcessed ?? 0).compareTo(b.totalFramesProcessed ?? 0);
          break;
        case 'faces_detected':
          comparison = (a.totalFacesDetected ?? 0).compareTo(b.totalFacesDetected ?? 0);
          break;
        case 'created_date':
        default:
          comparison = a.createdAt.compareTo(b.createdAt);
          break;
      }
      return _sortAscending ? comparison : -comparison;
    });
    
    return filtered;
  }
  
  Color _getSessionStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'active':
      case 'running':
        return AppColors.primary;
      case 'completed':
        return AppColors.success;
      case 'failed':
      case 'error':
        return AppColors.error;
      case 'pending':
        return AppColors.warning;
      default:
        return AppColors.textSecondary;
    }
  }
  
  IconData _getSessionStatusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'active':
      case 'running':
        return Icons.play_circle;
      case 'completed':
        return Icons.check_circle;
      case 'failed':
      case 'error':
        return Icons.error;
      case 'pending':
        return Icons.hourglass_empty;
      default:
        return Icons.help;
    }
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
      _selectedSessions.clear();
    });
  }
  
  void _toggleSelection(String sessionUuid) {
    setState(() {
      if (_selectedSessions.contains(sessionUuid)) {
        _selectedSessions.remove(sessionUuid);
      } else {
        _selectedSessions.add(sessionUuid);
      }
      
      if (!_isSelectMode) {
        _isSelectMode = true;
      }
    });
  }
  
  Future<void> _refreshSessions() async {
    ref.invalidate(allActiveSessionsProvider);
  }
  
  void _createNewSession() {
    // TODO: Implement session creation dialog
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Session creation feature coming soon'),
        backgroundColor: AppColors.info,
      ),
    );
  }
  
  void _viewSessionDetails(FaceDetectionSession session) {
    // TODO: Implement session details view
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Session Details',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Text(
          'Session UUID: ${session.sessionUuid}\n'
          'Status: ${session.status}\n'
          'Frames: ${session.totalFramesProcessed ?? 0}\n'
          'Faces: ${session.totalFacesDetected ?? 0}',
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
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
  
  void _stopSession(FaceDetectionSession session) {
    // TODO: Implement session stopping
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Stopping session ${session.sessionUuid.substring(0, 8)}...'),
        backgroundColor: AppColors.warning,
      ),
    );
  }
  
  void _deleteSession(FaceDetectionSession session) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Delete Session',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Text(
          'Are you sure you want to delete this session? This action cannot be undone.',
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
              // TODO: Implement session deletion
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Session ${session.sessionUuid.substring(0, 8)} deleted'),
                  backgroundColor: AppColors.success,
                ),
              );
            },
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
  
  void _bulkDeleteSessions() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Delete Sessions',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Text(
          'Are you sure you want to delete ${_selectedSessions.length} selected sessions? This action cannot be undone.',
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
              // TODO: Implement bulk session deletion
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('${_selectedSessions.length} sessions deleted'),
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

  void _bulkReprocessSessions() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Reprocess Sessions',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Text(
          'Reprocess ${_selectedSessions.length} selected sessions? This will restart video analysis and may take some time.',
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
              // TODO: Implement bulk session reprocessing
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('${_selectedSessions.length} sessions queued for reprocessing'),
                  backgroundColor: AppColors.primary,
                ),
              );
              _exitSelectMode();
            },
            child: const Text('Reprocess'),
          ),
        ],
      ),
    );
  }

  void _bulkArchiveSessions() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Archive Sessions',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Text(
          'Archive ${_selectedSessions.length} selected sessions? Archived sessions can be restored later.',
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
              // TODO: Implement bulk session archiving
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('${_selectedSessions.length} sessions archived'),
                  backgroundColor: AppColors.warning,
                ),
              );
              _exitSelectMode();
            },
            child: const Text('Archive'),
          ),
        ],
      ),
    );
  }

  void _bulkExportSessions() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Export Sessions',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Export ${_selectedSessions.length} selected sessions data:',
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),
            CheckboxListTile(
              title: const Text('Session metadata'),
              value: true,
              onChanged: (value) {},
              activeColor: AppColors.primary,
            ),
            CheckboxListTile(
              title: const Text('Detection results'),
              value: true,
              onChanged: (value) {},
              activeColor: AppColors.primary,
            ),
            CheckboxListTile(
              title: const Text('Video files'),
              value: false,
              onChanged: (value) {},
              activeColor: AppColors.primary,
            ),
            CheckboxListTile(
              title: const Text('Analytics data'),
              value: true,
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
              // TODO: Implement bulk session export
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Exporting ${_selectedSessions.length} sessions...'),
                  backgroundColor: AppColors.primary,
                ),
              );
              _exitSelectMode();
            },
            child: const Text('Export'),
          ),
        ],
      ),
    );
  }
}
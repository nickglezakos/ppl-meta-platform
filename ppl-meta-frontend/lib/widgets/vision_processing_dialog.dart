import 'package:flutter/material.dart';
import '../services/vision_processing_service.dart';
import '../core/theme/app_theme.dart';

/// Dialog shown during vision processing with progress indicator
class VisionProcessingDialog extends StatefulWidget {
  final List<String> mediaIds;
  final VisionProcessingService visionService;
  
  const VisionProcessingDialog({
    Key? key,
    required this.mediaIds,
    required this.visionService,
  }) : super(key: key);
  
  @override
  State<VisionProcessingDialog> createState() => _VisionProcessingDialogState();
}

class _VisionProcessingDialogState extends State<VisionProcessingDialog> {
  @override
  void initState() {
    super.initState();
    // Listen to service updates
    widget.visionService.addListener(_onServiceUpdate);
  }
  
  @override
  void dispose() {
    widget.visionService.removeListener(_onServiceUpdate);
    super.dispose();
  }
  
  void _onServiceUpdate() {
    if (mounted) {
      setState(() {});
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      // Prevent closing during processing
      onWillPop: () async => !widget.visionService.isProcessing,
      child: AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        content: Container(
          width: 320,
          constraints: const BoxConstraints(maxWidth: 400),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Icon
              Icon(
                Icons.visibility,
                size: 56,
                color: AppColors.primary,
              ),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Title
              Text(
                'Processing with Vision AI',
                style: AppTextStyles.h4.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              
              const SizedBox(height: AppSpacing.md),
              
              // Subtitle
              Text(
                'Detecting faces and creating MVR people...',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
              
              const SizedBox(height: AppSpacing.xl),
              
              // Progress bar
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: widget.visionService.progressPercent,
                  minHeight: 8,
                  backgroundColor: AppColors.surfaceVariant,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    AppColors.primary,
                  ),
                ),
              ),
              
              const SizedBox(height: AppSpacing.md),
              
              // Progress text
              Text(
                '${widget.visionService.currentProgress} / ${widget.visionService.totalItems} media processed',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              
              const SizedBox(height: AppSpacing.xs),
              
              // Percentage
              Text(
                '${(widget.visionService.progressPercent * 100).toStringAsFixed(0)}%',
                style: AppTextStyles.h3.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppColors.primary,
                ),
              ),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Status messages
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.info.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AppColors.info.withOpacity(0.3),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              AppColors.info,
                            ),
                          ),
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        Expanded(
                          child: Text(
                            'Processing in progress...',
                            style: AppTextStyles.bodySmall.copyWith(
                              color: AppColors.info,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    _buildStatusItem('Face Detection V2 processing'),
                    _buildStatusItem('Generating embeddings'),
                    _buildStatusItem('Extracting demographics'),
                    _buildStatusItem('Creating MVR people'),
                  ],
                ),
              ),
              
              const SizedBox(height: AppSpacing.md),
              
              // Info text
              Row(
                children: [
                  Icon(
                    Icons.info_outline,
                    size: 16,
                    color: AppColors.textSecondary,
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Expanded(
                    child: Text(
                      'This may take a few seconds per media item',
                      style: AppTextStyles.caption.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildStatusItem(String text) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Row(
        children: [
          Text(
            '• ',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          Expanded(
            child: Text(
              text,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../widgets/device_aware_upload_widget.dart';
import '../models/media_models.dart';
import '../widgets/custom_app_bar.dart';

/// Upload screen with device-aware upload interface
class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Upload Media',
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Page header
            Text(
              'Upload Your Media',
              style: AppTextStyles.h3,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Share photos, videos, and documents with your team',
              style: AppTextStyles.bodyLarge.copyWith(
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            
            const SizedBox(height: AppSpacing.xxl),
            
            // Upload widget
            DeviceAwareUploadWidget(
              enableBatchUpload: true,
              showPreview: true,
              maxFileSizeBytes: 100 * 1024 * 1024, // 100MB
              onUploadComplete: (mediaItem) {
                final snackBarText = mediaItem.isDuplicate
                    ? 'File already exists in the media library as ${mediaItem.filename}'
                    : 'Upload completed: ${mediaItem.filename}';
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(mediaItem.isDuplicate ? 'ℹ️ $snackBarText' : '✅ $snackBarText'),
                    backgroundColor: mediaItem.isDuplicate ? AppColors.warning : AppColors.success,
                    duration: const Duration(seconds: 4),
                  ),
                );
              },
              onUploadError: (error) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('❌ Upload failed: $error'),
                    backgroundColor: AppColors.error,
                    duration: const Duration(seconds: 6),
                  ),
                );
              },
            ),
            
            const SizedBox(height: AppSpacing.xxl),
            
            // Upload tips
            _buildUploadTips(),
          ],
        ),
      ),
    );
  }

  /// Build upload tips section
  Widget _buildUploadTips() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.lightbulb_outline,
                  color: AppColors.accent,
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  'Upload Tips',
                  style: AppTextStyles.h6,
                ),
              ],
            ),
            
            const SizedBox(height: AppSpacing.md),
            
            _TipItem(
              icon: Icons.file_upload,
              title: 'Supported Formats',
              description: 'Images (JPG, PNG, GIF), Videos (MP4, MOV), Audio (MP3, WAV), Documents (PDF, DOC)',
            ),
            
            _TipItem(
              icon: Icons.storage,
              title: 'File Size Limit',
              description: 'Maximum file size is 100MB per file',
            ),
            
            _TipItem(
              icon: Icons.batch_prediction,
              title: 'Batch Upload',
              description: 'Select multiple files at once for faster uploading',
            ),
            
            _TipItem(
              icon: Icons.devices,
              title: 'Cross-Platform',
              description: 'Works seamlessly across mobile, tablet, and desktop devices',
            ),
          ],
        ),
      ),
    );
  }
}

/// Individual tip item
class _TipItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;

  const _TipItem({
    required this.icon,
    required this.title,
    required this.description,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(AppSpacing.sm),
            decoration: BoxDecoration(
              color: AppColors.accent.withOpacity(0.1),
              borderRadius: BorderRadius.circular(AppRadius.sm),
            ),
            child: Icon(
              icon,
              size: 20,
              color: AppColors.accent,
            ),
          ),
          
          const SizedBox(width: AppSpacing.md),
          
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTextStyles.labelLarge,
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  description,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

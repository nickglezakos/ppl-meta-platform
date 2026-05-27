import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../core/models/api_response.dart';
import '../services/media_api_client.dart';
import '../models/device_info.dart';
import '../models/media_models.dart';
import '../core/api/api_client.dart';

/// Device-aware upload widget that adapts UI based on platform capabilities
class DeviceAwareUploadWidget extends ConsumerStatefulWidget {
  final Function(MediaItem)? onUploadComplete;
  final Function(String)? onUploadError;
  final List<String>? allowedExtensions;
  final int? maxFileSizeBytes;
  final bool enableBatchUpload;
  final bool showPreview;

  const DeviceAwareUploadWidget({
    super.key,
    this.onUploadComplete,
    this.onUploadError,
    this.allowedExtensions,
    this.maxFileSizeBytes,
    this.enableBatchUpload = true,
    this.showPreview = true,
  });

  @override
  ConsumerState<DeviceAwareUploadWidget> createState() => _DeviceAwareUploadWidgetState();
}

class _DeviceAwareUploadWidgetState extends ConsumerState<DeviceAwareUploadWidget>
    with TickerProviderStateMixin {
  final ImagePicker _imagePicker = ImagePicker();
  late MediaApiClient _apiClient;
  late DeviceInfo _deviceInfo;
  
  List<PlatformFile> _selectedFiles = [];
  Map<String, double> _uploadProgress = {};
  Map<String, UploadStatus> _uploadStatus = {};
  bool _isUploading = false;
  bool _forceSeparateUpload = false;
  
  late AnimationController _dragAnimationController;
  late Animation<double> _dragOpacityAnimation;
  late Animation<Color?> _dragColorAnimation;
  
  bool _isDragOver = false;

  @override
  void initState() {
    super.initState();
    _deviceInfo = DeviceInfo.current();
    
    _dragAnimationController = AnimationController(
      duration: AppDurations.fast,
      vsync: this,
    );
    
    _dragOpacityAnimation = Tween<double>(
      begin: 1.0,
      end: 0.8,
    ).animate(CurvedAnimation(
      parent: _dragAnimationController,
      curve: AppCurves.easeInOut,
    ));
    
    _dragColorAnimation = ColorTween(
      begin: AppColors.border,
      end: AppColors.primary,
    ).animate(CurvedAnimation(
      parent: _dragAnimationController,
      curve: AppCurves.easeInOut,
    ));
  }

  @override
  void dispose() {
    _dragAnimationController.dispose();
    super.dispose();
  }

  /// Pick files using platform-appropriate method
  Future<void> _pickFiles() async {
    try {
      if (_deviceInfo.isMobile) {
        await _pickFilesFromCamera();
      } else {
        await _pickFilesFromStorage();
      }
    } catch (e) {
      _showError('Failed to pick files: $e');
    }
  }

  /// Pick files from camera (mobile)
  Future<void> _pickFilesFromCamera() async {
    final source = await _showImageSourceDialog();
    if (source == null) return;

    final XFile? file = await _imagePicker.pickImage(source: source);
    if (file != null) {
      final platformFile = PlatformFile(
        name: file.name,
        path: file.path,
        size: await file.length(),
        bytes: kIsWeb ? await file.readAsBytes() : null,
      );
      
      setState(() {
        if (widget.enableBatchUpload) {
          _selectedFiles.add(platformFile);
        } else {
          _selectedFiles = [platformFile];
        }
      });
    }
  }

  /// Pick files from storage
  Future<void> _pickFilesFromStorage() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: widget.enableBatchUpload,
      allowedExtensions: widget.allowedExtensions,
      type: widget.allowedExtensions != null 
          ? FileType.custom 
          : FileType.media,
      withData: kIsWeb,
    );

    if (result != null) {
      setState(() {
        if (widget.enableBatchUpload) {
          _selectedFiles.addAll(result.files);
        } else {
          _selectedFiles = [result.files.first];
        }
      });
    }
  }

  /// Show image source selection dialog
  Future<ImageSource?> _showImageSourceDialog() async {
    return showDialog<ImageSource>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Select Image Source'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Camera'),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Gallery'),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );
  }

  /// Upload selected files
  Future<void> _uploadFiles() async {
    if (_selectedFiles.isEmpty) {
      _showError('No files selected');
      return;
    }

    setState(() {
      _isUploading = true;
      _uploadProgress.clear();
      _uploadStatus.clear();
    });

    for (final file in _selectedFiles) {
      await _uploadSingleFile(file);
    }

    setState(() {
      _isUploading = false;
    });
  }

  /// Upload a single file with progress tracking
  Future<void> _uploadSingleFile(PlatformFile file) async {
    final fileId = file.name;
    
    setState(() {
      _uploadProgress[fileId] = 0.0;
      _uploadStatus[fileId] = UploadStatus.inProgress;
    });

    try {
      // Validate file size
      if (widget.maxFileSizeBytes != null && 
          file.size > widget.maxFileSizeBytes!) {
        throw Exception('File size exceeds limit');
      }

      // Get file data
      List<int> fileBytes;
      if (kIsWeb) {
        fileBytes = file.bytes!;
      } else {
        fileBytes = await File(file.path!).readAsBytes();
      }

      // Upload with progress tracking
      final result = await _apiClient.uploadMedia(
        fileBytes: fileBytes,
        fileName: file.name,
        mimeType: _getMimeType(file.name),
        forceSeparateUpload: _forceSeparateUpload,
        deviceInfo: _deviceInfo,
        onProgressPercent: (progress) {
          setState(() {
            _uploadProgress[fileId] = progress;
          });
        },
      );

      if (result.success && result.data != null) {
        setState(() {
          _uploadStatus[fileId] = UploadStatus.completed;
          _uploadProgress[fileId] = 1.0;
        });

        // Create a simple upload response object for the callback
        final uploadResponse = {
          'mediaId': result.data!.id,
          'filePath': result.data!.filePath, 
          'filename': result.data!.filename,
          'status': 'success',
          'message': 'Upload completed successfully',
        };
        
        // Call success callback with the MediaItem data
        widget.onUploadComplete?.call(result.data!);
        
        // Clear the uploaded file from selection after success
        setState(() {
          _selectedFiles.removeWhere((f) => f.name == file.name);
          _uploadProgress.remove(fileId);
          _uploadStatus.remove(fileId);
        });
      } else {
        setState(() {
          _uploadStatus[fileId] = UploadStatus.failed;
        });
        widget.onUploadError?.call('Upload failed: ${result.error}');
      }
      
    } catch (e) {
      setState(() {
        _uploadStatus[fileId] = UploadStatus.failed;
      });
      
      widget.onUploadError?.call('Failed to upload ${file.name}: $e');
    }
  }

  /// Get MIME type from file extension
  String _getMimeType(String fileName) {
    final extension = fileName.split('.').last.toLowerCase();
    switch (extension) {
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      case 'png':
        return 'image/png';
      case 'gif':
        return 'image/gif';
      case 'mp4':
        return 'video/mp4';
      case 'mov':
        return 'video/quicktime';
      case 'mp3':
        return 'audio/mpeg';
      case 'wav':
        return 'audio/wav';
      default:
        return 'application/octet-stream';
    }
  }

  /// Remove file from selection
  void _removeFile(int index) {
    setState(() {
      final file = _selectedFiles[index];
      _selectedFiles.removeAt(index);
      _uploadProgress.remove(file.name);
      _uploadStatus.remove(file.name);
    });
  }

  /// Clear all selected files
  void _clearFiles() {
    setState(() {
      _selectedFiles.clear();
      _uploadProgress.clear();
      _uploadStatus.clear();
    });
  }

  /// Show error message
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: AppColors.error,
      ),
    );
  }

  /// Handle drag enter
  void _onDragEnter() {
    if (!_deviceInfo.supportsDragDrop) return;
    
    setState(() {
      _isDragOver = true;
    });
    _dragAnimationController.forward();
  }

  /// Handle drag leave
  void _onDragLeave() {
    if (!_deviceInfo.supportsDragDrop) return;
    
    setState(() {
      _isDragOver = false;
    });
    _dragAnimationController.reverse();
  }

  /// Handle drag accept
  void _onDragAccept(List<PlatformFile> files) {
    if (!_deviceInfo.supportsDragDrop) return;
    
    setState(() {
      _isDragOver = false;
      if (widget.enableBatchUpload) {
        _selectedFiles.addAll(files);
      } else {
        _selectedFiles = [files.first];
      }
    });
    _dragAnimationController.reverse();
  }

  @override
  Widget build(BuildContext context) {
    // Initialize MediaApiClient with authenticated ApiClient from Riverpod
    final apiClient = ref.watch(apiClientProvider);
    _apiClient = MediaApiClient(apiClient);
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Row(
              children: [
                Icon(
                  _deviceInfo.isMobile ? Icons.camera_alt : Icons.upload,
                  color: AppColors.primary,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    'Upload Media',
                    style: AppTextStyles.h5,
                  ),
                ),
                if (_selectedFiles.isNotEmpty)
                  IconButton(
                    onPressed: _clearFiles,
                    icon: const Icon(Icons.clear_all),
                    tooltip: 'Clear all files',
                  ),
              ],
            ),
            
            const SizedBox(height: AppSpacing.md),
            
            // Device info
            Container(
              padding: const EdgeInsets.all(AppSpacing.sm),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: Row(
                children: [
                  Icon(
                    _deviceInfo.platformIcon,
                    size: 16,
                    color: AppColors.textSecondary,
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Text(
                    _deviceInfo.displayName,
                    style: AppTextStyles.caption,
                  ),
                  const Spacer(),
                  if (_deviceInfo.isMobile)
                    const Icon(
                      Icons.touch_app,
                      size: 16,
                      color: AppColors.textSecondary,
                    ),
                  if (_deviceInfo.supportsDragDrop)
                    const Icon(
                      Icons.drag_indicator,
                      size: 16,
                      color: AppColors.textSecondary,
                    ),
                ],
              ),
            ),
            
            const SizedBox(height: AppSpacing.md),

            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text('Create separate item even if file already exists'),
              subtitle: const Text('Turn this on before uploading when you want a new library entry instead of deduplication.'),
              value: _forceSeparateUpload,
              onChanged: _isUploading
                  ? null
                  : (value) {
                      setState(() {
                        _forceSeparateUpload = value;
                      });
                    },
              activeColor: AppColors.primary,
            ),

            const SizedBox(height: AppSpacing.md),
            
            // Upload area
            AnimatedBuilder(
              animation: _dragAnimationController,
              builder: (context, child) {
                return GestureDetector(
                  onTap: _pickFiles,
                  child: Container(
                    height: 120,
                    decoration: BoxDecoration(
                      border: Border.all(
                        color: _dragColorAnimation.value ?? AppColors.border,
                        width: 2,
                        style: BorderStyle.solid,
                      ),
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      color: AppColors.surfaceVariant.withOpacity(
                        _dragOpacityAnimation.value,
                      ),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          _isDragOver
                              ? Icons.file_download
                              : (_deviceInfo.isMobile 
                                  ? Icons.add_photo_alternate 
                                  : Icons.cloud_upload),
                          size: 48,
                          color: _isDragOver 
                              ? AppColors.primary 
                              : AppColors.textSecondary,
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        Text(
                          _isDragOver
                              ? 'Drop files here'
                              : (_deviceInfo.isMobile 
                                  ? 'Tap to select photos' 
                                  : 'Click to browse or drag files here'),
                          style: AppTextStyles.bodyMedium.copyWith(
                            color: _isDragOver 
                                ? AppColors.primary 
                                : AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
            
            const SizedBox(height: AppSpacing.md),
            
            // Selected files list
            if (_selectedFiles.isNotEmpty) ...[
              Text(
                'Selected Files (${_selectedFiles.length})',
                style: AppTextStyles.labelLarge,
              ),
              const SizedBox(height: AppSpacing.sm),
              ...List.generate(_selectedFiles.length, (index) {
                final file = _selectedFiles[index];
                final status = _uploadStatus[file.name] ?? UploadStatus.pending;
                final progress = _uploadProgress[file.name] ?? 0.0;
                
                return _FileListItem(
                  file: file,
                  status: status,
                  progress: progress,
                  showPreview: widget.showPreview,
                  onRemove: () => _removeFile(index),
                );
              }),
              
              const SizedBox(height: AppSpacing.md),
              
              // Upload button
              ElevatedButton(
                onPressed: _isUploading ? null : _uploadFiles,
                child: _isUploading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Upload Files'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Upload status enum
enum UploadStatus {
  pending,
  inProgress,
  completed,
  failed,
}

/// File list item widget
class _FileListItem extends StatelessWidget {
  final PlatformFile file;
  final UploadStatus status;
  final double progress;
  final bool showPreview;
  final VoidCallback onRemove;

  const _FileListItem({
    required this.file,
    required this.status,
    required this.progress,
    required this.showPreview,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.sm),
        child: Row(
          children: [
            // File preview/icon
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: _getFileTypeColor(),
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: showPreview && _isImageFile()
                  ? _buildImagePreview()
                  : Icon(
                      _getFileTypeIcon(),
                      color: AppColors.white,
                    ),
            ),
            
            const SizedBox(width: AppSpacing.sm),
            
            // File info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    file.name,
                    style: AppTextStyles.bodyMedium,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    '${(file.size / 1024 / 1024).toStringAsFixed(1)} MB',
                    style: AppTextStyles.caption,
                  ),
                  if (status == UploadStatus.inProgress) ...[
                    const SizedBox(height: AppSpacing.xs),
                    LinearProgressIndicator(
                      value: progress,
                      backgroundColor: AppColors.gray200,
                      valueColor: AlwaysStoppedAnimation(AppColors.primary),
                    ),
                  ],
                ],
              ),
            ),
            
            // Status icon
            _buildStatusIcon(),
            
            const SizedBox(width: AppSpacing.sm),
            
            // Remove button
            IconButton(
              onPressed: status == UploadStatus.inProgress ? null : onRemove,
              icon: const Icon(Icons.close),
              iconSize: 20,
            ),
          ],
        ),
      ),
    );
  }

  /// Build image preview
  Widget _buildImagePreview() {
    if (kIsWeb && file.bytes != null) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: Image.memory(
          file.bytes!,
          fit: BoxFit.cover,
          width: 48,
          height: 48,
        ),
      );
    } else if (file.path != null) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: Image.file(
          File(file.path!),
          fit: BoxFit.cover,
          width: 48,
          height: 48,
        ),
      );
    }
    
    return Icon(
      Icons.image,
      color: AppColors.white,
    );
  }

  /// Build status icon
  Widget _buildStatusIcon() {
    switch (status) {
      case UploadStatus.pending:
        return Icon(
          Icons.schedule,
          color: AppColors.uploadPending,
          size: 20,
        );
      case UploadStatus.inProgress:
        return SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            value: progress,
            valueColor: AlwaysStoppedAnimation(AppColors.uploadInProgress),
          ),
        );
      case UploadStatus.completed:
        return Icon(
          Icons.check_circle,
          color: AppColors.uploadCompleted,
          size: 20,
        );
      case UploadStatus.failed:
        return Icon(
          Icons.error,
          color: AppColors.uploadFailed,
          size: 20,
        );
    }
  }

  /// Check if file is an image
  bool _isImageFile() {
    final extension = file.name.split('.').last.toLowerCase();
    return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].contains(extension);
  }

  /// Get file type icon
  IconData _getFileTypeIcon() {
    final extension = file.name.split('.').last.toLowerCase();
    
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].contains(extension)) {
      return Icons.image;
    } else if (['mp4', 'mov', 'avi', 'mkv'].contains(extension)) {
      return Icons.video_file;
    } else if (['mp3', 'wav', 'aac', 'flac'].contains(extension)) {
      return Icons.audio_file;
    } else if (['pdf', 'doc', 'docx', 'txt'].contains(extension)) {
      return Icons.description;
    }
    
    return Icons.insert_drive_file;
  }

  /// Get file type color
  Color _getFileTypeColor() {
    final extension = file.name.split('.').last.toLowerCase();
    
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].contains(extension)) {
      return AppColors.imageColor;
    } else if (['mp4', 'mov', 'avi', 'mkv'].contains(extension)) {
      return AppColors.videoColor;
    } else if (['mp3', 'wav', 'aac', 'flac'].contains(extension)) {
      return AppColors.audioColor;
    } else if (['pdf', 'doc', 'docx', 'txt'].contains(extension)) {
      return AppColors.documentColor;
    }
    
    return AppColors.gray500;
  }
}

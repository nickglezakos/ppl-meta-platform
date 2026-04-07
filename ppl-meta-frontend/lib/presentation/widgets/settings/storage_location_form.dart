import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../models/storage_location.dart';
import '../../../services/storage_service.dart';
import '../../../core/theme/app_theme.dart';

/// Dialog for creating or editing a storage location.
class StorageLocationFormDialog extends ConsumerStatefulWidget {
  final StorageLocation? existing;

  const StorageLocationFormDialog({super.key, this.existing});

  @override
  ConsumerState<StorageLocationFormDialog> createState() =>
      _StorageLocationFormDialogState();
}

class _StorageLocationFormDialogState
    extends ConsumerState<StorageLocationFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _pathController;
  String _locationType = 'local_disk';
  String _tier = 'active';
  bool _isDefault = false;
  bool _saving = false;

  // Cloud config fields
  late TextEditingController _bucketController;
  late TextEditingController _regionController;
  late TextEditingController _accessKeyController;
  late TextEditingController _secretKeyController;

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    _nameController = TextEditingController(text: e?.name ?? '');
    _pathController = TextEditingController(text: e?.basePath ?? '');
    _locationType = e?.locationType ?? 'local_disk';
    _tier = e?.tier ?? 'active';
    _isDefault = e?.isDefault ?? false;
    _bucketController = TextEditingController();
    _regionController = TextEditingController(text: 'us-east-1');
    _accessKeyController = TextEditingController();
    _secretKeyController = TextEditingController();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _pathController.dispose();
    _bucketController.dispose();
    _regionController.dispose();
    _accessKeyController.dispose();
    _secretKeyController.dispose();
    super.dispose();
  }

  bool get _isCloud =>
      _locationType == 'cloud_s3' ||
      _locationType == 'cloud_azure' ||
      _locationType == 'cloud_gcp';

  bool get _isEditing => widget.existing != null;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEditing ? 'Edit Storage Location' : 'Add Storage Location'),
      content: SizedBox(
        width: 480,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Name
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Name',
                    hintText: 'e.g. Main SSD, NAS Backup',
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Name is required' : null,
                ),
                const SizedBox(height: 16),

                // Location type (not editable after creation)
                if (!_isEditing) ...[
                  DropdownButtonFormField<String>(
                    value: _locationType,
                    decoration: const InputDecoration(labelText: 'Type'),
                    items: const [
                      DropdownMenuItem(
                          value: 'local_disk', child: Text('💾 Local Disk')),
                      DropdownMenuItem(
                          value: 'external_drive',
                          child: Text('🔌 External Drive')),
                      DropdownMenuItem(
                          value: 'cloud_s3', child: Text('☁️ AWS S3')),
                      DropdownMenuItem(
                          value: 'cloud_azure', child: Text('☁️ Azure Blob')),
                      DropdownMenuItem(
                          value: 'cloud_gcp',
                          child: Text('☁️ Google Cloud')),
                    ],
                    onChanged: (v) {
                      if (v != null) setState(() => _locationType = v);
                    },
                  ),
                  const SizedBox(height: 16),
                ],

                // Path
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _pathController,
                        decoration: InputDecoration(
                          labelText: _isCloud ? 'Bucket URI' : 'Path',
                          hintText: _isCloud
                              ? 's3://my-bucket/ppl-meta'
                              : '/Volumes/MediaDrive/ppl-meta',
                        ),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Path is required'
                            : null,
                      ),
                    ),
                    if (!_isCloud) ...[                      const SizedBox(width: 8),
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: IconButton(
                          icon: const Icon(Icons.folder_open),
                          tooltip: 'Browse…',
                          onPressed: _pickDirectory,
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 16),

                // Tier
                DropdownButtonFormField<String>(
                  value: _tier,
                  decoration: const InputDecoration(labelText: 'Tier'),
                  items: const [
                    DropdownMenuItem(
                        value: 'active', child: Text('Active (daily use)')),
                    DropdownMenuItem(
                        value: 'archive',
                        child: Text('Archive (long-term storage)')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => _tier = v);
                  },
                ),
                const SizedBox(height: 12),

                // Default toggle
                SwitchListTile(
                  title: const Text('Set as default'),
                  subtitle: const Text(
                      'New uploads will go to this location'),
                  value: _isDefault,
                  onChanged: (v) => setState(() => _isDefault = v),
                  contentPadding: EdgeInsets.zero,
                ),

                // Cloud config
                if (_isCloud && !_isEditing) ...[
                  const Divider(height: 32),
                  Text('Cloud Configuration',
                      style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _bucketController,
                    decoration:
                        const InputDecoration(labelText: 'Bucket Name'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _regionController,
                    decoration: const InputDecoration(labelText: 'Region'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _accessKeyController,
                    decoration:
                        const InputDecoration(labelText: 'Access Key ID'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _secretKeyController,
                    decoration:
                        const InputDecoration(labelText: 'Secret Access Key'),
                    obscureText: true,
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _saving ? null : _save,
          child: _saving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(_isEditing ? 'Save' : 'Add Location'),
        ),
      ],
    );
  }

  Future<void> _pickDirectory() async {
    try {
      final result = await FilePicker.platform.getDirectoryPath(
        dialogTitle: 'Select storage directory',
      );
      if (result != null) {
        _pathController.text = result;
      }
    } on UnimplementedError {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Directory browsing is not available on web. '
              'Please type the path manually.',
            ),
          ),
        );
      }
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _saving = true);

    try {
      final service = ref.read(storageServiceProvider);

      if (_isEditing) {
        final updates = <String, dynamic>{
          'name': _nameController.text.trim(),
          'base_path': _pathController.text.trim(),
          'tier': _tier,
          'is_default': _isDefault,
        };
        await service.updateStorageLocation(widget.existing!.uuid, updates);
      } else {
        Map<String, dynamic>? cloudConfig;
        if (_isCloud &&
            _bucketController.text.trim().isNotEmpty) {
          cloudConfig = {
            'provider': _locationType.replaceFirst('cloud_', ''),
            'bucket': _bucketController.text.trim(),
            'region': _regionController.text.trim(),
            'access_key_id': _accessKeyController.text.trim(),
            'secret_access_key': _secretKeyController.text.trim(),
          };
        }

        await service.createStorageLocation(StorageLocationRequest(
          name: _nameController.text.trim(),
          locationType: _locationType,
          basePath: _pathController.text.trim(),
          tier: _tier,
          isDefault: _isDefault,
          cloudConfig: cloudConfig,
        ));
      }

      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save location: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}

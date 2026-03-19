import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/mvr_api_client.dart';
import '../core/api/api_client.dart';

/// A widget that displays and allows editing of an MVR person's gender.
/// 
/// Shows the gender as text or icon. When clicked, shows a dropdown to select
/// male or female. Supports save/cancel operations and displays loading/error states.
class EditableMVRGender extends ConsumerStatefulWidget {
  final String? initialGender;
  final String mvrPersonUuid;
  final bool propagate;
  final Function(String? gender)? onGenderUpdated;
  final TextStyle? textStyle;
  final TextStyle? placeholderStyle;
  final bool showEditIcon;
  final bool enabled;
  final bool showIcon;

  const EditableMVRGender({
    Key? key,
    this.initialGender,
    required this.mvrPersonUuid,
    this.propagate = true,
    this.onGenderUpdated,
    this.textStyle,
    this.placeholderStyle,
    this.showEditIcon = true,
    this.enabled = true,
    this.showIcon = true,
  }) : super(key: key);

  @override
  ConsumerState<EditableMVRGender> createState() => _EditableMVRGenderState();
}

class _EditableMVRGenderState extends ConsumerState<EditableMVRGender> {
  bool _isEditing = false;
  bool _isSaving = false;
  String? _error;
  String? _selectedGender;

  @override
  void initState() {
    super.initState();
    _selectedGender = _normalizeGender(widget.initialGender);
  }

  @override
  void didUpdateWidget(EditableMVRGender oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialGender != oldWidget.initialGender) {
      _selectedGender = _normalizeGender(widget.initialGender);
    }
  }

  String? _normalizeGender(String? gender) {
    if (gender == null) return null;
    final normalized = gender.toLowerCase().trim();
    if (normalized == 'male' || normalized == 'm' || normalized == 'man') {
      return 'male';
    } else if (normalized == 'female' || normalized == 'f' || normalized == 'woman') {
      return 'female';
    }
    return null;
  }

  void _startEditing() {
    if (!widget.enabled) return;
    
    setState(() {
      _isEditing = true;
      _error = null;
      _selectedGender = _normalizeGender(widget.initialGender);
    });
  }

  void _cancelEditing() {
    setState(() {
      _isEditing = false;
      _error = null;
      _selectedGender = _normalizeGender(widget.initialGender);
    });
  }

  Future<void> _saveGender(String? newGender) async {
    setState(() {
      _isSaving = true;
      _error = null;
      _selectedGender = newGender;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      final mvrClient = MVRApiClient(apiClient);
      final response = await mvrClient.updateMVRPersonGender(
        widget.mvrPersonUuid,
        newGender ?? '',
        propagate: widget.propagate,
      );

      if (response.success && response.data != null) {
        setState(() {
          _isEditing = false;
          _isSaving = false;
        });
        
        widget.onGenderUpdated?.call(newGender);
        
        if (response.data!.propagatedTo.isNotEmpty && mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Gender updated and propagated to ${response.data!.propagatedTo.length} related records',
              ),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        setState(() {
          _isSaving = false;
          _error = response.error ?? 'Failed to update gender';
        });
      }
    } catch (e) {
      setState(() {
        _isSaving = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isEditing) {
      return _buildEditingView();
    } else {
      return _buildViewingView();
    }
  }

  Widget _buildViewingView() {
    final normalizedGender = _normalizeGender(widget.initialGender);
    final displayText = normalizedGender == null 
        ? 'Click to set gender'
        : normalizedGender == 'male' 
            ? 'Male' 
            : 'Female';
    final isPlaceholder = normalizedGender == null;

    return InkWell(
      onTap: widget.enabled ? _startEditing : null,
      borderRadius: BorderRadius.circular(4),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.showIcon && normalizedGender != null) ...[
              Icon(
                normalizedGender == 'male' ? Icons.male : Icons.female,
                size: 18,
                color: normalizedGender == 'male' 
                    ? Colors.blue[700] 
                    : Colors.pink[700],
              ),
              const SizedBox(width: 4),
            ],
            Text(
              displayText,
              style: isPlaceholder
                  ? (widget.placeholderStyle ?? 
                     TextStyle(
                       color: Colors.grey[600],
                       fontStyle: FontStyle.italic,
                     ))
                  : (widget.textStyle ?? const TextStyle()),
            ),
            if (widget.showEditIcon && widget.enabled) ...[
              const SizedBox(width: 4),
              Icon(
                Icons.edit,
                size: 16,
                color: Colors.grey[600],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEditingView() {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Select Gender',
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildGenderButton('male', 'Male', Icons.male, Colors.blue),
                const SizedBox(width: 12),
                _buildGenderButton('female', 'Female', Icons.female, Colors.pink),
                const SizedBox(width: 12),
                _buildGenderButton(null, 'Clear', Icons.clear, Colors.grey),
              ],
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(
                _error!,
                style: const TextStyle(
                  color: Colors.red,
                  fontSize: 12,
                ),
              ),
            ],
            const SizedBox(height: 12),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextButton(
                  onPressed: _isSaving ? null : _cancelEditing,
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 8),
                if (_isSaving)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGenderButton(
    String? value,
    String label,
    IconData icon,
    MaterialColor color,
  ) {
    final isSelected = _selectedGender == value;
    
    return ElevatedButton.icon(
      onPressed: _isSaving ? null : () => _saveGender(value),
      icon: Icon(icon, size: 20),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: isSelected ? color[700] : Colors.grey[300],
        foregroundColor: isSelected ? Colors.white : Colors.black87,
        elevation: isSelected ? 4 : 1,
      ),
    );
  }
}

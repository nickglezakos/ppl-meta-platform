import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/mvr_api_client.dart';
import '../core/api/api_client.dart';

/// A widget that displays and allows editing of an MVR person's name.
/// 
/// Shows the name in a viewing state. When clicked, switches to an editing
/// state with a text field. Supports save/cancel operations and displays
/// loading and error states.
class EditableMVRName extends ConsumerStatefulWidget {
  final String? initialName;
  final String mvrPersonUuid;
  final bool propagate;
  final Function(String? name)? onNameUpdated;
  final TextStyle? textStyle;
  final TextStyle? placeholderStyle;
  final bool showEditIcon;
  final bool enabled;

  const EditableMVRName({
    Key? key,
    this.initialName,
    required this.mvrPersonUuid,
    this.propagate = true,
    this.onNameUpdated,
    this.textStyle,
    this.placeholderStyle,
    this.showEditIcon = true,
    this.enabled = true,
  }) : super(key: key);

  @override
  ConsumerState<EditableMVRName> createState() => _EditableMVRNameState();
}

class _EditableMVRNameState extends ConsumerState<EditableMVRName> {
  bool _isEditing = false;
  bool _isSaving = false;
  String? _error;
  late TextEditingController _controller;
  late FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialName);
    _focusNode = FocusNode();
  }

  @override
  void didUpdateWidget(EditableMVRName oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Update controller if initialName changed
    if (widget.initialName != oldWidget.initialName) {
      _controller.text = widget.initialName ?? '';
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _startEditing() {
    if (!widget.enabled) return;
    
    setState(() {
      _isEditing = true;
      _error = null;
    });
    
    // Focus the text field
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
      _controller.selection = TextSelection(
        baseOffset: 0,
        extentOffset: _controller.text.length,
      );
    });
  }

  void _cancelEditing() {
    setState(() {
      _isEditing = false;
      _error = null;
      _controller.text = widget.initialName ?? '';
    });
  }

  Future<void> _saveName() async {
    final newName = _controller.text.trim();
    
    // Validate
    if (newName.isEmpty) {
      setState(() {
        _error = 'Name cannot be empty';
      });
      return;
    }
    
    if (newName.length > 255) {
      setState(() {
        _error = 'Name too long (max 255 characters)';
      });
      return;
    }

    setState(() {
      _isSaving = true;
      _error = null;
    });

    try {
      // Get authenticated API client from provider
      final apiClient = ref.read(apiClientProvider);
      final mvrClient = MVRApiClient(apiClient);
      final response = await mvrClient.updateMVRPersonName(
        widget.mvrPersonUuid,
        newName,
        propagate: widget.propagate,
      );

      if (response.success && response.data != null) {
        setState(() {
          _isEditing = false;
          _isSaving = false;
        });
        
        widget.onNameUpdated?.call(newName);
        
        // Show success message if propagation occurred
        if (response.data!.propagatedTo.isNotEmpty && 
            mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Name updated and propagated to ${response.data!.propagatedTo.length} related records',
              ),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        setState(() {
          _isSaving = false;
          _error = response.error ?? 'Failed to update name';
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
    final displayName = widget.initialName ?? 'Click to add name';
    final isPlaceholder = widget.initialName == null;

    return InkWell(
      onTap: widget.enabled ? _startEditing : null,
      borderRadius: BorderRadius.circular(4),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              displayName,
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _controller,
                focusNode: _focusNode,
                enabled: !_isSaving,
                decoration: InputDecoration(
                  hintText: 'Enter name',
                  errorText: _error,
                  isDense: true,
                  border: const OutlineInputBorder(),
                ),
                onSubmitted: (_) => _saveName(),
              ),
            ),
            const SizedBox(width: 8),
            if (_isSaving)
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else ...[
              IconButton(
                icon: const Icon(Icons.check, color: Colors.green),
                onPressed: _saveName,
                tooltip: 'Save',
                iconSize: 20,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.close, color: Colors.red),
                onPressed: _cancelEditing,
                tooltip: 'Cancel',
                iconSize: 20,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            ],
          ],
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              _error!,
              style: TextStyle(
                color: Theme.of(context).colorScheme.error,
                fontSize: 12,
              ),
            ),
          ),
      ],
    );
  }
}

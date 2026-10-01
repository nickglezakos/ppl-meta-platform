import 'package:flutter/material.dart';
import '../../models/signage_models.dart';
import '../../providers/signage_provider.dart';

/// Simple form editor for rich message overlay templates.
class RichMessageTemplateEditor extends StatefulWidget {
  final SignageProvider signageProvider;
  final RichMessageTemplate? template;
  final VoidCallback? onSaved;
  final VoidCallback? onCancel;
  final bool inline;

  const RichMessageTemplateEditor({
    Key? key,
    required this.signageProvider,
    this.template,
    this.onSaved,
    this.onCancel,
    this.inline = false,
  }) : super(key: key);

  @override
  State<RichMessageTemplateEditor> createState() =>
      _RichMessageTemplateEditorState();
}

class _RichMessageTemplateEditorState extends State<RichMessageTemplateEditor> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _titleController;
  late TextEditingController _messageController;
  late TextEditingController _mediaUuidController;
  late TextEditingController _soundUuidController;
  late TextEditingController _durationController;
  late TextEditingController _titleFontController;
  late TextEditingController _messageFontController;
  late TextEditingController _titleColorController;
  late TextEditingController _messageColorController;
  late TextEditingController _backgroundColorController;

  double _opacity = 80;
  String _layout = 'card';
  bool _saving = false;

  static const _presets = [
    '#FFFFFF',
    '#F0F0F0',
    '#000000',
    '#111827',
    '#1D4ED8',
    '#DC2626',
    '#16A34A',
    '#F59E0B',
  ];

  @override
  void initState() {
    super.initState();
    final t = widget.template;
    _nameController = TextEditingController(text: t?.name ?? '');
    _titleController = TextEditingController(text: t?.title ?? '');
    _messageController = TextEditingController(text: t?.message ?? '');
    _mediaUuidController = TextEditingController(text: t?.mediaUuid ?? '');
    _soundUuidController = TextEditingController(text: t?.soundMediaUuid ?? '');
    _durationController = TextEditingController(
      text: (t?.defaultDurationMs ?? 15000).toString(),
    );
    _titleFontController =
        TextEditingController(text: (t?.titleFontSize ?? 48).toString());
    _messageFontController =
        TextEditingController(text: (t?.messageFontSize ?? 28).toString());
    _titleColorController =
        TextEditingController(text: t?.titleColor ?? '#FFFFFF');
    _messageColorController =
        TextEditingController(text: t?.messageColor ?? '#F0F0F0');
    _backgroundColorController =
        TextEditingController(text: t?.backgroundColor ?? '#000000');
    _opacity = (t?.opacity ?? 80).toDouble();
    _layout = t?.layout ?? 'card';
  }

  @override
  void dispose() {
    _nameController.dispose();
    _titleController.dispose();
    _messageController.dispose();
    _mediaUuidController.dispose();
    _soundUuidController.dispose();
    _durationController.dispose();
    _titleFontController.dispose();
    _messageFontController.dispose();
    _titleColorController.dispose();
    _messageColorController.dispose();
    _backgroundColorController.dispose();
    super.dispose();
  }

  Color _parseColor(String hex) {
    var raw = hex.trim().replaceFirst('#', '');
    if (raw.length == 3) {
      raw = raw.split('').map((c) => '$c$c').join();
    }
    if (raw.length == 6) raw = 'FF$raw';
    final value = int.tryParse(raw, radix: 16);
    return value == null ? Colors.white : Color(value);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);

    final request = CreateRichMessageTemplateRequest(
      name: _nameController.text.trim(),
      title: _titleController.text.trim(),
      message: _messageController.text.trim().isEmpty
          ? null
          : _messageController.text.trim(),
      titleFontSize: int.tryParse(_titleFontController.text) ?? 48,
      messageFontSize: int.tryParse(_messageFontController.text) ?? 28,
      titleColor: _titleColorController.text.trim(),
      messageColor: _messageColorController.text.trim(),
      backgroundColor: _backgroundColorController.text.trim(),
      opacity: _opacity.round().clamp(0, 100),
      layout: _layout,
      mediaUuid: _mediaUuidController.text.trim().isEmpty
          ? null
          : _mediaUuidController.text.trim(),
      soundMediaUuid: _soundUuidController.text.trim().isEmpty
          ? null
          : _soundUuidController.text.trim(),
      defaultDurationMs: int.tryParse(_durationController.text) ?? 15000,
    );

    final clearMedia =
        widget.template?.mediaUuid != null && _mediaUuidController.text.trim().isEmpty;
    final clearSound = widget.template?.soundMediaUuid != null &&
        _soundUuidController.text.trim().isEmpty;

    RichMessageTemplate? result;
    if (widget.template == null) {
      result = await widget.signageProvider.createRichMessage(request);
    } else {
      result = await widget.signageProvider.updateRichMessage(
        widget.template!.uuid,
        request,
        clearMedia: clearMedia,
        clearSound: clearSound,
      );
    }

    if (!mounted) return;
    setState(() => _saving = false);

    if (result != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(widget.template == null
              ? 'Rich message created'
              : 'Rich message updated'),
        ),
      );
      widget.onSaved?.call();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            widget.signageProvider.richMessagesError ?? 'Save failed',
          ),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final form = Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextFormField(
            controller: _nameController,
            decoration: const InputDecoration(
              labelText: 'Template Name *',
              border: OutlineInputBorder(),
            ),
            validator: (v) =>
                (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _titleController,
            decoration: const InputDecoration(
              labelText: 'Title',
              hintText: 'e.g. Welcome {matched_member_name}',
              helperText:
                  'Supports {trigger_name}, {reason}, {match_reason}, {similarity_score}, {matched_member_name}, …',
              border: OutlineInputBorder(),
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _messageController,
            decoration: const InputDecoration(
              labelText: 'Message',
              hintText: 'e.g. Score {similarity_score} — {match_reason}',
              helperText:
                  'Same magic tags as automation actions; filled when a trigger fires this template',
              border: OutlineInputBorder(),
            ),
            maxLines: 4,
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _titleFontController,
                  decoration: const InputDecoration(
                    labelText: 'Title font size',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.number,
                  onChanged: (_) => setState(() {}),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextFormField(
                  controller: _messageFontController,
                  decoration: const InputDecoration(
                    labelText: 'Message font size',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.number,
                  onChanged: (_) => setState(() {}),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _colorField('Title color', _titleColorController),
          _colorField('Message color', _messageColorController),
          _colorField('Background color', _backgroundColorController),
          const SizedBox(height: 8),
          Text('Opacity: ${_opacity.round()}%'),
          Slider(
            value: _opacity,
            min: 0,
            max: 100,
            divisions: 20,
            label: '${_opacity.round()}%',
            onChanged: (v) => setState(() => _opacity = v),
          ),
          DropdownButtonFormField<String>(
            value: _layout,
            decoration: const InputDecoration(
              labelText: 'Layout',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(value: 'card', child: Text('Card')),
              DropdownMenuItem(value: 'banner', child: Text('Banner')),
              DropdownMenuItem(value: 'fullscreen', child: Text('Fullscreen')),
            ],
            onChanged: (v) => setState(() => _layout = v ?? 'card'),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _mediaUuidController,
            decoration: const InputDecoration(
              labelText: 'Media UUID (optional video/image)',
              hintText: 'Paste media UUID from Media library',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _soundUuidController,
            decoration: const InputDecoration(
              labelText: 'Sound media UUID (optional)',
              hintText: 'Paste sound media UUID',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _durationController,
            decoration: const InputDecoration(
              labelText: 'Default duration (ms)',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 16),
          _buildPreview(),
          const SizedBox(height: 16),
          Row(
            children: [
              if (widget.onCancel != null)
                TextButton(onPressed: widget.onCancel, child: const Text('Cancel')),
              const Spacer(),
              ElevatedButton(
                onPressed: _saving ? null : _save,
                child: _saving
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(widget.template == null ? 'Create' : 'Save'),
              ),
            ],
          ),
        ],
      ),
    );

    if (widget.inline) return form;
    return SizedBox(width: 520, height: 640, child: form);
  }

  Widget _colorField(String label, TextEditingController controller) {
    final color = _parseColor(controller.text);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Expanded(
            child: TextFormField(
              controller: controller,
              decoration: InputDecoration(
                labelText: label,
                border: const OutlineInputBorder(),
              ),
              onChanged: (_) => setState(() {}),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: color,
              border: Border.all(color: Colors.grey),
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          const SizedBox(width: 8),
          PopupMenuButton<String>(
            tooltip: 'Presets',
            onSelected: (v) {
              controller.text = v;
              setState(() {});
            },
            itemBuilder: (_) => _presets
                .map(
                  (p) => PopupMenuItem(
                    value: p,
                    child: Row(
                      children: [
                        Container(
                          width: 18,
                          height: 18,
                          color: _parseColor(p),
                        ),
                        const SizedBox(width: 8),
                        Text(p),
                      ],
                    ),
                  ),
                )
                .toList(),
            child: const Icon(Icons.palette_outlined),
          ),
        ],
      ),
    );
  }

  Widget _buildPreview() {
    final bg = _parseColor(_backgroundColorController.text)
        .withValues(alpha: _opacity / 100);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(_layout == 'card' ? 16 : 0),
        border: Border.all(color: Colors.grey.shade400),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Preview',
            style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
          ),
          const SizedBox(height: 8),
          Text(
            _titleController.text.isEmpty ? 'Title' : _titleController.text,
            style: TextStyle(
              color: _parseColor(_titleColorController.text),
              fontSize: (int.tryParse(_titleFontController.text) ?? 48)
                  .clamp(12, 64)
                  .toDouble(),
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _messageController.text.isEmpty
                ? 'Message body'
                : _messageController.text,
            style: TextStyle(
              color: _parseColor(_messageColorController.text),
              fontSize: (int.tryParse(_messageFontController.text) ?? 28)
                  .clamp(10, 48)
                  .toDouble(),
            ),
          ),
        ],
      ),
    );
  }
}

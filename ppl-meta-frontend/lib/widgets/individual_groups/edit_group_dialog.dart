/// Edit Group Dialog
/// Dialog for editing an existing individual group
library;

import 'package:flutter/material.dart';
import '../../models/individual_group_models.dart';

class EditGroupDialog extends StatefulWidget {
  final IndividualGroup group;

  const EditGroupDialog({
    super.key,
    required this.group,
  });

  @override
  State<EditGroupDialog> createState() => _EditGroupDialogState();
}

class _EditGroupDialogState extends State<EditGroupDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _descriptionController;
  
  late GroupVisibility _visibility;
  late List<String> _tags;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.group.name);
    _descriptionController = TextEditingController(text: widget.group.description ?? '');
    _visibility = widget.group.visibility;
    _tags = List.from(widget.group.tags);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  void _removeTag(String tag) {
    setState(() {
      _tags.remove(tag);
    });
  }

  void _submit() {
    if (_formKey.currentState!.validate()) {
      final request = UpdateGroupRequest(
        name: _nameController.text.trim(),
        description: _descriptionController.text.trim().isEmpty
            ? null
            : _descriptionController.text.trim(),
        visibility: _visibility,
        tags: _tags,
      );
      Navigator.of(context).pop(request);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: 500,
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Row(
                  children: [
                    const Icon(Icons.edit, size: 28),
                    const SizedBox(width: 12),
                    Text(
                      'Edit Group',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                // Name field
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Group Name',
                    hintText: 'Enter group name',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.label),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Please enter a group name';
                    }
                    if (value.trim().length < 3) {
                      return 'Name must be at least 3 characters';
                    }
                    return null;
                  },
                  textInputAction: TextInputAction.next,
                ),
                const SizedBox(height: 16),

                // Description field
                TextFormField(
                  controller: _descriptionController,
                  decoration: const InputDecoration(
                    labelText: 'Description (optional)',
                    hintText: 'Enter group description',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.description),
                  ),
                  maxLines: 3,
                  textInputAction: TextInputAction.newline,
                ),
                const SizedBox(height: 16),

                // Visibility selector
                Text(
                  'Visibility',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                SegmentedButton<GroupVisibility>(
                  segments: const [
                    ButtonSegment(
                      value: GroupVisibility.private,
                      label: Text('Private'),
                      icon: Icon(Icons.lock_outline, size: 16),
                    ),
                    ButtonSegment(
                      value: GroupVisibility.shared,
                      label: Text('Shared'),
                      icon: Icon(Icons.people_outline, size: 16),
                    ),
                    ButtonSegment(
                      value: GroupVisibility.public,
                      label: Text('Public'),
                      icon: Icon(Icons.public, size: 16),
                    ),
                  ],
                  selected: {_visibility},
                  onSelectionChanged: (Set<GroupVisibility> selected) {
                    setState(() {
                      _visibility = selected.first;
                    });
                  },
                ),
                const SizedBox(height: 16),

                // Tags
                Text(
                  'Tags',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    ..._tags.map((tag) => Chip(
                          label: Text(tag),
                          deleteIcon: const Icon(Icons.close, size: 16),
                          onDeleted: () => _removeTag(tag),
                        )),
                    ActionChip(
                      avatar: const Icon(Icons.add, size: 16),
                      label: const Text('Add Tag'),
                      onPressed: () {
                        showDialog(
                          context: context,
                          builder: (context) => _AddTagDialog(
                            onAdd: (tag) {
                              if (!_tags.contains(tag)) {
                                setState(() => _tags.add(tag));
                              }
                            },
                          ),
                        );
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                // Action buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text('Cancel'),
                    ),
                    const SizedBox(width: 12),
                    FilledButton(
                      onPressed: _submit,
                      child: const Text('Save Changes'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _AddTagDialog extends StatefulWidget {
  final Function(String) onAdd;

  const _AddTagDialog({required this.onAdd});

  @override
  State<_AddTagDialog> createState() => _AddTagDialogState();
}

class _AddTagDialogState extends State<_AddTagDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add Tag'),
      content: TextField(
        controller: _controller,
        decoration: const InputDecoration(
          hintText: 'Enter tag name',
          border: OutlineInputBorder(),
        ),
        autofocus: true,
        onSubmitted: (value) {
          if (value.trim().isNotEmpty) {
            widget.onAdd(value.trim());
            Navigator.of(context).pop();
          }
        },
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (_controller.text.trim().isNotEmpty) {
              widget.onAdd(_controller.text.trim());
              Navigator.of(context).pop();
            }
          },
          child: const Text('Add'),
        ),
      ],
    );
  }
}

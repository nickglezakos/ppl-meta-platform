/// Add Members Dialog
/// Dialog for adding individuals to a group
library;

import 'package:flutter/material.dart';
import '../../services/individual_groups_api_client.dart';
import '../../models/individual_group_models.dart';

class AddMembersDialog extends StatefulWidget {
  final String groupId;
  final IndividualGroupsApiClient apiClient;

  const AddMembersDialog({
    super.key,
    required this.groupId,
    required this.apiClient,
  });

  @override
  State<AddMembersDialog> createState() => _AddMembersDialogState();
}

class _AddMembersDialogState extends State<AddMembersDialog> {
  final _searchController = TextEditingController();
  final List<String> _selectedIds = [];
  List<IndividualSummary> _availableIndividuals = [];
  List<IndividualSummary> _filteredIndividuals = [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadAvailableIndividuals();
    _searchController.addListener(_filterIndividuals);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadAvailableIndividuals() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    // Load all individuals not in this group
    // For now, this is a placeholder - you'd need to add an endpoint
    // to get individuals not in a specific group
    
    // Temporary: Show empty state with manual ID entry
    setState(() {
      _isLoading = false;
      _availableIndividuals = [];
      _filteredIndividuals = [];
    });
  }

  void _filterIndividuals() {
    final query = _searchController.text.toLowerCase();
    setState(() {
      _filteredIndividuals = _availableIndividuals.where((individual) {
        return individual.id.toLowerCase().contains(query);
      }).toList();
    });
  }

  void _toggleSelection(String individualId) {
    setState(() {
      if (_selectedIds.contains(individualId)) {
        _selectedIds.remove(individualId);
      } else {
        _selectedIds.add(individualId);
      }
    });
  }

  void _addMembers() {
    if (_selectedIds.isNotEmpty) {
      Navigator.of(context).pop(_selectedIds);
    }
  }

  void _showManualIdDialog() {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Individual by ID'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'Individual UUID',
                hintText: 'Enter individual UUID',
                border: OutlineInputBorder(),
              ),
              autofocus: true,
            ),
            const SizedBox(height: 8),
            Text(
              'Enter one or more UUIDs, separated by commas',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final text = controller.text.trim();
              if (text.isNotEmpty) {
                // Split by comma and add all valid UUIDs
                final ids = text
                    .split(',')
                    .map((id) => id.trim())
                    .where((id) => id.isNotEmpty)
                    .toList();
                
                setState(() {
                  for (final id in ids) {
                    if (!_selectedIds.contains(id)) {
                      _selectedIds.add(id);
                    }
                  }
                });
                Navigator.of(context).pop();
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: 600,
        height: 700,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.person_add, size: 28),
                const SizedBox(width: 12),
                Text(
                  'Add Members',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Search bar
            TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search individuals...',
                prefixIcon: const Icon(Icons.search),
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.add_circle),
                  tooltip: 'Add by ID',
                  onPressed: _showManualIdDialog,
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Selected count
            if (_selectedIds.isNotEmpty)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.check_circle,
                      size: 16,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${_selectedIds.length} selected',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const Spacer(),
                    TextButton(
                      onPressed: () => setState(() => _selectedIds.clear()),
                      child: const Text('Clear'),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 16),

            // Content
            Expanded(
              child: _buildContent(),
            ),

            // Action buttons
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 12),
                FilledButton.icon(
                  onPressed: _selectedIds.isEmpty ? null : _addMembers,
                  icon: const Icon(Icons.add),
                  label: Text('Add ${_selectedIds.length} Members'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error: $_errorMessage'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadAvailableIndividuals,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    // Show manual entry option when no search results
    if (_availableIndividuals.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.info_outline, size: 64),
            const SizedBox(height: 16),
            Text(
              'Add Members by ID',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Click the + button above to add individuals by UUID',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            if (_selectedIds.isNotEmpty) ...[
              const Divider(),
              const SizedBox(height: 16),
              Text(
                'Selected IDs:',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Expanded(
                child: ListView.builder(
                  itemCount: _selectedIds.length,
                  itemBuilder: (context, index) {
                    final id = _selectedIds[index];
                    return ListTile(
                      leading: const Icon(Icons.person),
                      title: Text(
                        id.length > 30 ? '${id.substring(0, 30)}...' : id,
                        style: const TextStyle(fontFamily: 'monospace'),
                      ),
                      trailing: IconButton(
                        icon: const Icon(Icons.delete),
                        onPressed: () => _toggleSelection(id),
                      ),
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: _filteredIndividuals.length,
      itemBuilder: (context, index) {
        final individual = _filteredIndividuals[index];
        final isSelected = _selectedIds.contains(individual.id);

        return CheckboxListTile(
          value: isSelected,
          onChanged: (_) => _toggleSelection(individual.id),
          title: Text('ID: ${individual.id.substring(0, 8)}...'),
          subtitle: Text('${individual.totalAppearances} appearances'),
          secondary: individual.thumbnailUrl != null
              ? CircleAvatar(
                  backgroundImage: NetworkImage(
                    widget.apiClient.getThumbnailUrl(individual.id, size: 'small'),
                  ),
                )
              : const CircleAvatar(
                  child: Icon(Icons.person),
                ),
        );
      },
    );
  }
}

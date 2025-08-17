import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

/// Demo widget showing CAM-FLUTTER-004D Collection Organization features
class CollectionOrganizationDemo extends StatefulWidget {
  const CollectionOrganizationDemo({super.key});

  @override
  State<CollectionOrganizationDemo> createState() => _CollectionOrganizationDemoState();
}

class _CollectionOrganizationDemoState extends State<CollectionOrganizationDemo> {
  bool _showOrganizationPanel = false;
  int _selectedItemsCount = 0;
  String _selectedAction = 'move';
  String _statusMessage = '';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('CAM-FLUTTER-004D Demo'),
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.white,
        actions: [
          if (_selectedItemsCount > 0)
            IconButton(
              onPressed: () {
                setState(() {
                  _showOrganizationPanel = !_showOrganizationPanel;
                });
              },
              icon: Icon(
                _showOrganizationPanel 
                    ? Icons.keyboard_arrow_up 
                    : Icons.drive_file_move,
              ),
              tooltip: 'Organize Items',
            ),
        ],
      ),
      body: Column(
        children: [
          // Demo media grid
          Expanded(
            child: GridView.builder(
              padding: const EdgeInsets.all(AppSpacing.md),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                crossAxisSpacing: AppSpacing.sm,
                mainAxisSpacing: AppSpacing.sm,
              ),
              itemCount: 12,
              itemBuilder: (context, index) {
                return _DemoMediaItem(
                  index: index,
                  isSelected: index < _selectedItemsCount,
                  onTap: () {
                    setState(() {
                      if (index < _selectedItemsCount) {
                        _selectedItemsCount = index;
                      } else {
                        _selectedItemsCount = index + 1;
                      }
                    });
                  },
                );
              },
            ),
          ),
          
          // Organization panel
          if (_showOrganizationPanel)
            _buildOrganizationPanel(),
          
          // Status bar
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: const BoxDecoration(
              color: AppColors.surface,
              border: Border(
                top: BorderSide(color: AppColors.border),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${_selectedItemsCount} items selected',
                  style: AppTextStyles.bodyMedium.copyWith(
                    fontWeight: FontWeight.w600,
                    color: _selectedItemsCount > 0 
                        ? AppColors.primary 
                        : AppColors.textSecondary,
                  ),
                ),
                if (_statusMessage.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    _statusMessage,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.success,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
      floatingActionButton: _selectedItemsCount > 0 && !_showOrganizationPanel
          ? FloatingActionButton.extended(
              onPressed: () {
                setState(() {
                  _showOrganizationPanel = true;
                });
              },
              icon: const Icon(Icons.drive_file_move),
              label: const Text('Organize'),
              backgroundColor: AppColors.primary,
            )
          : null,
    );
  }

  Widget _buildOrganizationPanel() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(AppRadius.lg),
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.black.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(
                Icons.drive_file_move,
                color: AppColors.primary,
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'Organize ${_selectedItemsCount} item${_selectedItemsCount == 1 ? '' : 's'}',
                style: AppTextStyles.h6.copyWith(
                  color: AppColors.primary,
                ),
              ),
              const Spacer(),
              IconButton(
                onPressed: () {
                  setState(() {
                    _showOrganizationPanel = false;
                  });
                },
                icon: const Icon(Icons.close),
                tooltip: 'Close',
              ),
            ],
          ),
          
          const SizedBox(height: AppSpacing.lg),
          
          // Action selection
          Text(
            'Choose Action',
            style: AppTextStyles.bodyMedium.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          
          Row(
            children: [
              _ActionChip(
                label: 'Move',
                icon: Icons.drive_file_move,
                isSelected: _selectedAction == 'move',
                onTap: () => setState(() => _selectedAction = 'move'),
              ),
              const SizedBox(width: AppSpacing.sm),
              _ActionChip(
                label: 'Copy',
                icon: Icons.copy,
                isSelected: _selectedAction == 'copy',
                onTap: () => setState(() => _selectedAction = 'copy'),
              ),
              const SizedBox(width: AppSpacing.sm),
              _ActionChip(
                label: 'Create New',
                icon: Icons.create_new_folder,
                isSelected: _selectedAction == 'create',
                onTap: () => setState(() => _selectedAction = 'create'),
              ),
            ],
          ),
          
          const SizedBox(height: AppSpacing.lg),
          
          // Demo collections
          Text(
            'Available Collections',
            style: AppTextStyles.bodyMedium.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          
          SizedBox(
            height: 120,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                _DemoCollectionCard(
                  name: 'Security Events',
                  itemCount: 45,
                  icon: Icons.security,
                  onTap: () => _performAction('Security Events'),
                ),
                _DemoCollectionCard(
                  name: 'Daily Photos',
                  itemCount: 128,
                  icon: Icons.photo_camera,
                  onTap: () => _performAction('Daily Photos'),
                ),
                _DemoCollectionCard(
                  name: 'Favorites',
                  itemCount: 23,
                  icon: Icons.favorite,
                  onTap: () => _performAction('Favorites'),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: AppSpacing.lg),
          
          // Action button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => _performAction('Demo Collection'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                padding: const EdgeInsets.all(AppSpacing.md),
              ),
              child: Text(
                _getActionButtonText(),
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.white,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _getActionButtonText() {
    switch (_selectedAction) {
      case 'move':
        return 'Move to Collection';
      case 'copy':
        return 'Copy to Collection';
      case 'create':
        return 'Create New Collection';
      default:
        return 'Organize Items';
    }
  }

  void _performAction(String collectionName) {
    setState(() {
      _showOrganizationPanel = false;
      _statusMessage = '${_selectedItemsCount} items ${_selectedAction}d to "$collectionName"';
      _selectedItemsCount = 0;
    });
    
    // Clear status after 3 seconds
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        setState(() {
          _statusMessage = '';
        });
      }
    });
  }
}

class _DemoMediaItem extends StatelessWidget {
  final int index;
  final bool isSelected;
  final VoidCallback onTap;

  const _DemoMediaItem({
    required this.index,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(
            color: isSelected ? AppColors.primary : AppColors.border,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Stack(
          children: [
            // Media preview
            Container(
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Center(
                child: Icon(
                  index % 3 == 0 ? Icons.image : 
                  index % 3 == 1 ? Icons.videocam : Icons.music_note,
                  size: 32,
                  color: AppColors.primary,
                ),
              ),
            ),
            
            // Selection indicator
            if (isSelected)
              Positioned(
                top: 4,
                right: 4,
                child: Container(
                  width: 24,
                  height: 24,
                  decoration: const BoxDecoration(
                    color: AppColors.primary,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.check,
                    size: 16,
                    color: AppColors.white,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ActionChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _ActionChip({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.primary : AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(
            color: isSelected ? AppColors.primary : AppColors.border,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 16,
              color: isSelected ? AppColors.white : AppColors.textSecondary,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              label,
              style: AppTextStyles.bodySmall.copyWith(
                color: isSelected ? AppColors.white : AppColors.textSecondary,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DemoCollectionCard extends StatelessWidget {
  final String name;
  final int itemCount;
  final IconData icon;
  final VoidCallback onTap;

  const _DemoCollectionCard({
    required this.name,
    required this.itemCount,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 140,
        margin: const EdgeInsets.only(right: AppSpacing.md),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  color: AppColors.primary,
                  size: 20,
                ),
                const Spacer(),
                Text(
                  '$itemCount',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              name,
              style: AppTextStyles.bodyMedium.copyWith(
                fontWeight: FontWeight.w600,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const Spacer(),
            Text(
              'items',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

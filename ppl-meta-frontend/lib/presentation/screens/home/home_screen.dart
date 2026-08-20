import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/providers/auth_provider.dart';
import '../../../core/theme/app_theme.dart';
import '../../../widgets/app_logo.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authNotifier = ref.read(authNotifierProvider.notifier);
    final currentUser = ref.watch(currentUserProvider);

    return Scaffold(
      appBar: AppBar(
        title: const AppLogo(height: 32),
        actions: [
          PopupMenuButton<String>(
            color: AppColors.widgetFill,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: Theme.of(context).colorScheme.outline),
            ),
            elevation: 0,
            onSelected: (value) async {
              switch (value) {
                case 'profile':
                  context.go('/profile');
                  break;
                case 'settings':
                  context.go('/settings');
                  break;
                case 'users':
                  context.go('/users');
                  break;
                case 'roles':
                  context.go('/roles');
                  break;
                case 'logout':
                  await authNotifier.logout();
                  if (context.mounted) {
                    context.go('/login');
                  }
                  break;
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'profile',
                padding: EdgeInsets.zero,
                child: Container(
                  decoration: const BoxDecoration(),
                  child: const ListTile(
                    leading: Icon(Icons.person),
                    title: Text('Profile'),
                    contentPadding: EdgeInsets.symmetric(horizontal: 16),
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              ),
              PopupMenuItem(
                value: 'settings',
                padding: EdgeInsets.zero,
                child: Container(
                  decoration: const BoxDecoration(),
                  child: const ListTile(
                    leading: Icon(Icons.settings),
                    title: Text('Settings'),
                    contentPadding: EdgeInsets.symmetric(horizontal: 16),
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              ),
              PopupMenuItem(
                value: 'users',
                padding: EdgeInsets.zero,
                child: Container(
                  decoration: const BoxDecoration(),
                  child: const ListTile(
                    leading: Icon(Icons.people),
                    title: Text('Users'),
                    contentPadding: EdgeInsets.symmetric(horizontal: 16),
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              ),
              if (currentUser != null && currentUser.canManageRoles)
                PopupMenuItem(
                  value: 'roles',
                  padding: EdgeInsets.zero,
                  child: Container(
                    decoration: const BoxDecoration(),
                    child: ListTile(
                      leading: const Icon(Icons.badge),
                      title: const Text('Roles'),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                      visualDensity: VisualDensity.compact,
                    ),
                  ),
                ),
              PopupMenuItem(
                value: 'logout',
                padding: EdgeInsets.zero,
                child: Container(
                  decoration: const BoxDecoration(),
                  child: const ListTile(
                    leading: Icon(Icons.logout),
                    title: Text('Logout'),
                    contentPadding: EdgeInsets.symmetric(horizontal: 16),
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              ),
            ],
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircleAvatar(
                  radius: 16,
                  backgroundColor: Theme.of(context).primaryColor.withValues(alpha: 0.2),
                  child: Icon(
                    Icons.person,
                    color: Theme.of(context).colorScheme.onSurface, // Match dropdown icons
                    size: 20,
                  ),
                ),
                const SizedBox(width: 8),
                const Icon(Icons.arrow_drop_down),
              ],
            ),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // (welcome bar and quick actions title removed)
            // Action cards
            Expanded(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  // Responsive grid columns based on screen width
                  int crossAxisCount;
                  double childAspectRatio;
                  
                  if (constraints.maxWidth < 600) {
                    // Mobile: 2 buttons per row
                    crossAxisCount = 2;
                    childAspectRatio = 1.0;
                  } else if (constraints.maxWidth < 900) {
                    // Tablet: 3 buttons per row
                    crossAxisCount = 3;
                    childAspectRatio = 1.1;
                  } else {
                    // Desktop: 4 buttons per row
                    crossAxisCount = 4;
                    childAspectRatio = 1.2;
                  }
                  
                  return GridView.count(
                    crossAxisCount: crossAxisCount,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                    childAspectRatio: childAspectRatio,
                    children: [
                      _ActionCard(
                        icon: Icons.videocam,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Cameras',
                        subtitle: 'Manage live cameras',
                        onTap: () {
                          context.go('/cameras');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.collections,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Collections',
                        subtitle: 'Organize your media',
                        onTap: () {
                          context.go('/collections');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.precision_manufacturing,
                        iconColor: AppColors.secondary,
                        title: 'Automation',
                        subtitle: 'Manage automated triggers & actions',
                        onTap: () {
                          context.go('/triggers');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.groups,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Individual Groups',
                        subtitle: 'Organize people by groups',
                        onTap: () {
                          context.go('/individual-groups');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.analytics,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Analytics',
                        subtitle: 'View statistics',
                        onTap: () {
                          context.go('/analytics');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.how_to_reg,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Presence',
                        subtitle: 'Presence flows and assurance analytics',
                        onTap: () {
                          context.go('/presence');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.display_settings,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Signage Management',
                        subtitle: 'Manage digital signage playlists',
                        onTap: () {
                          context.go('/signage');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.photo_library,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'My Media',
                        subtitle: 'View your uploads',
                        onTap: () {
                          context.go('/gallery');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.cloud_upload,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Upload Media',
                        subtitle: 'Upload photos and videos',
                        onTap: () {
                          context.go('/upload');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.monitor_heart,
                        iconColor: AppColors.secondary,
                        title: 'Camera Ops',
                        subtitle: 'Live status, health, and aggregates',
                        isHighlighted: false,
                        onTap: () {
                          context.go('/camera-operations');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.storage,
                        iconColor: AppColors.secondary,
                        title: 'Storage',
                        subtitle: 'Manage storage locations & usage',
                        isHighlighted: false,
                        onTap: () {
                          context.go('/storage');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.auto_awesome,
                        iconColor: AppColors.secondary,
                        title: 'Monitoring',
                        subtitle: 'System & workflow monitoring',
                        isHighlighted: false,
                        onTap: () {
                          context.go('/workflows');
                        },
                      ),
                      _ActionCard(
                        icon: Icons.dns,
                        iconColor: AppColors.secondary,
                        title: 'Network',
                        subtitle: 'Network & service connections',
                        isHighlighted: false,
                        onTap: () {
                          context.go('/network');
                        },
                      ),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final bool isHighlighted;
  final VoidCallback onTap;

  const _ActionCard({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    this.isHighlighted = true,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    // Get screen width for responsive sizing
    final screenWidth = MediaQuery.of(context).size.width;
    final isCompact = screenWidth < 600; // Mobile
    
    final theme = Theme.of(context);
    final resolvedBackgroundColor = isHighlighted
      ? const Color(0x1622D3EE)
      : null;
    final resolvedBorderColor = isHighlighted
      ? const Color(0x4022D3EE)
      : theme.colorScheme.outline;

    return Card(
      color: resolvedBackgroundColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: resolvedBorderColor,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: EdgeInsets.all(isCompact ? 12 : 16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: isCompact ? 36 : 48,
                color: iconColor, // Use the contextual color
              ),
              SizedBox(height: isCompact ? 8 : 12),
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  fontSize: isCompact ? 14 : null,
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              SizedBox(height: isCompact ? 2 : 4),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontSize: isCompact ? 11 : null,
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

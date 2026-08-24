import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/providers/auth_provider.dart';
import '../../../core/theme/theme_kit.dart';
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
              borderRadius: BorderRadius.circular(AppRadius.lg),
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
                    leading: Icon(AppIcons.person),
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
                    leading: Icon(AppIcons.settings),
                    title: Text('Settings'),
                    contentPadding: EdgeInsets.symmetric(horizontal: AppSpacing.md),
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
                    leading: Icon(AppIcons.people),
                    title: Text('Users'),
                    contentPadding: EdgeInsets.symmetric(horizontal: AppSpacing.md),
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
                      leading: const Icon(AppIcons.badge),
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
                    leading: Icon(AppIcons.logout),
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
                const Icon(AppIcons.arrowDropDown),
              ],
            ),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
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
                  
                  if (constraints.maxWidth < AppBreakpoints.mobile) {
                    // Mobile: 2 buttons per row
                    crossAxisCount = 2;
                    childAspectRatio = 0.9;
                  } else if (constraints.maxWidth < AppBreakpoints.tablet) {
                    // Tablet: 3 buttons per row
                    crossAxisCount = 3;
                    childAspectRatio = 1.0;
                  } else {
                    // Desktop: 4 buttons per row
                    crossAxisCount = 4;
                    childAspectRatio = 1.1;
                  }
                  
                  return GridView.count(
                    crossAxisCount: crossAxisCount,
                    crossAxisSpacing: AppSpacing.lg,
                    mainAxisSpacing: AppSpacing.lg,
                    childAspectRatio: childAspectRatio,
                    children: [
                      _ActionCard(
                        icon: AppIcons.cameras,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Cameras',
                        subtitle: 'Manage live cameras',
                        onTap: () {
                          context.go('/cameras');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.collections,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Collections',
                        subtitle: 'Organize your media',
                        onTap: () {
                          context.go('/collections');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.triggers,
                        iconColor: AppColors.secondary,
                        title: 'Automation',
                        subtitle: 'Manage automated triggers & actions',
                        onTap: () {
                          context.go('/triggers');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.groups,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Individual Groups',
                        subtitle: 'Organize people by groups',
                        onTap: () {
                          context.go('/individual-groups');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.analytics,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Analytics',
                        subtitle: 'View statistics',
                        onTap: () {
                          context.go('/analytics');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.presence,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Presence',
                        subtitle: 'Presence flows and assurance analytics',
                        onTap: () {
                          context.go('/presence');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.signage,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Signage Management',
                        subtitle: 'Manage digital signage playlists',
                        onTap: () {
                          context.go('/signage');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.media,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'My Media',
                        subtitle: 'View your uploads',
                        onTap: () {
                          context.go('/gallery');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.upload,
                        iconColor: AppColors.secondary, // Unified cyan color
                        title: 'Upload Media',
                        subtitle: 'Upload photos and videos',
                        onTap: () {
                          context.go('/upload');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.cameraOps,
                        iconColor: AppColors.secondary,
                        title: 'Camera Ops',
                        subtitle: 'Live status, health, and aggregates',
                        isHighlighted: false,
                        onTap: () {
                          context.go('/camera-operations');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.storage,
                        iconColor: AppColors.secondary,
                        title: 'Storage',
                        subtitle: 'Manage storage locations & usage',
                        isHighlighted: false,
                        onTap: () {
                          context.go('/storage');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.workflows,
                        iconColor: AppColors.secondary,
                        title: 'Monitoring',
                        subtitle: 'System & workflow monitoring',
                        isHighlighted: false,
                        onTap: () {
                          context.go('/workflows');
                        },
                      ),
                      _ActionCard(
                        icon: AppIcons.network,
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
    final screenWidth = MediaQuery.of(context).size.width;
    final isCompact = screenWidth < AppBreakpoints.mobile;

    final theme = Theme.of(context);
    final resolvedBackgroundColor = isHighlighted
      ? AppColors.selectedBg
      : null;
    final resolvedBorderColor = isHighlighted
      ? AppColors.selectedBorder
      : theme.colorScheme.outline;

    return Card(
      color: resolvedBackgroundColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(
          color: resolvedBorderColor,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        child: Padding(
          padding: EdgeInsets.all(isCompact ? AppSpacing.sm : AppSpacing.lg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: isCompact ? AppIconSize.cardCompact : AppIconSize.cardExpanded,
                color: iconColor,
              ),
              SizedBox(height: isCompact ? AppSpacing.xsm : AppSpacing.md),
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
              SizedBox(height: isCompact ? AppSpacing.xs : AppSpacing.sm),
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

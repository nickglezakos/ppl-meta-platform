import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/theme/app_theme.dart';

/// Custom AppBar with consistent navigation (back button + home icon)
class CustomAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final List<Widget>? actions;
  final bool showBackButton;
  final bool showHomeButton;
  final Color? backgroundColor;
  final Color? foregroundColor;
  final double? elevation;
  final VoidCallback? onBackPressed;
  final VoidCallback? onHomePressed;
  final PreferredSizeWidget? bottom;

  const CustomAppBar({
    super.key,
    required this.title,
    this.actions,
    this.showBackButton = true,
    this.showHomeButton = true,
    this.backgroundColor,
    this.foregroundColor,
    this.elevation,
    this.onBackPressed,
    this.onHomePressed,
    this.bottom,
  });

  @override
  Widget build(BuildContext context) {
    return AppBar(
      title: Text(
        title,
        style: AppTextStyles.h6.copyWith(
          color: foregroundColor ?? AppColors.textPrimary,
        ),
      ),
      centerTitle: true, // Center the title
      backgroundColor: backgroundColor ?? AppColors.surface,
      foregroundColor: foregroundColor ?? AppColors.textPrimary,
      elevation: elevation ?? 0,
      leading: showBackButton ? _buildLeadingWidget(context) : null,
      actions: [
        if (showHomeButton) _buildHomeButton(context),
        if (actions != null) ...actions!,
      ],
      bottom: bottom,
    );
  }

  Widget _buildLeadingWidget(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Back button
        IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: onBackPressed ?? () => _handleBackPress(context),
          tooltip: 'Back',
        ),
      ],
    );
  }

  Widget _buildHomeButton(BuildContext context) {
    return IconButton(
      icon: const Icon(Icons.home),
      onPressed: onHomePressed ?? () => _handleHomePress(context),
      tooltip: 'Home',
    );
  }

  void _handleBackPress(BuildContext context) {
    if (context.canPop()) {
      context.pop();
    } else {
      // If no route to pop, go to home
      context.go('/');
    }
  }

  void _handleHomePress(BuildContext context) {
    context.go('/');
  }

  @override
  Size get preferredSize => Size.fromHeight(
        kToolbarHeight + (bottom?.preferredSize.height ?? 0.0),
      );
}

/// Specialized AppBar for full-screen media preview with dark theme
class DarkCustomAppBar extends CustomAppBar {
  const DarkCustomAppBar({
    super.key,
    required super.title,
    super.actions,
    super.showBackButton = true,
    super.showHomeButton = true,
    super.onBackPressed,
    super.onHomePressed,
  }) : super(
          backgroundColor: Colors.black,
          foregroundColor: Colors.white,
          elevation: 0,
        );
}

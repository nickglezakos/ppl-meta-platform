import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/providers/auth_provider.dart';
import '../core/theme/app_theme.dart';
import '../providers/authority_status_providers.dart';
import '../services/authority_status_client.dart';

class AuthorityLifecycleBanner extends ConsumerStatefulWidget {
  final Widget child;

  const AuthorityLifecycleBanner({
    super.key,
    required this.child,
  });

  @override
  ConsumerState<AuthorityLifecycleBanner> createState() => _AuthorityLifecycleBannerState();
}

class _AuthorityLifecycleBannerState extends ConsumerState<AuthorityLifecycleBanner> {
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(const Duration(minutes: 1), (_) {
      ref.invalidate(authorityStatusProvider);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);
    if (!authState.isAuthenticated) {
      return widget.child;
    }

    final authorityStatus = ref.watch(authorityStatusProvider);
    final banner = authorityStatus.maybeWhen(
      data: _buildBanner,
      orElse: () => null,
    );

    if (banner == null) {
      return widget.child;
    }

    return Column(
      children: [
        banner,
        Expanded(child: widget.child),
      ],
    );
  }

  Widget? _buildBanner(AuthorityStatus status) {
    if (status.isSafeguardActive) {
      return _BannerShell(
        color: const Color(0xFF7F1D1D),
        borderColor: const Color(0xFFDC2626),
        icon: Icons.gpp_bad,
        message: 'Safeguard active. This installation is blocked until the licence state is resolved in Authority.',
      );
    }

    if (status.isWarningActive) {
      final countdown = status.warningDaysRemaining != null
          ? ' ${status.warningDaysRemaining} day(s) remaining before safeguard.'
          : ' Resolve it before the warning period elapses.';
      return _BannerShell(
        color: const Color(0xFF78350F),
        borderColor: AppColors.warning,
        icon: Icons.warning_amber_rounded,
        message: 'Licence warning active. Update the licence in Authority.$countdown',
      );
    }

    if (status.runtimeState == 'offline_grace') {
      return _BannerShell(
        color: const Color(0xFF0C4A6E),
        borderColor: AppColors.info,
        icon: Icons.cloud_off,
        message: 'Authority is unreachable. The node is currently operating within offline grace.',
      );
    }

    return null;
  }
}

class _BannerShell extends StatelessWidget {
  final Color color;
  final Color borderColor;
  final IconData icon;
  final String message;

  const _BannerShell({
    required this.color,
    required this.borderColor,
    required this.icon,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: color,
      child: SafeArea(
        bottom: false,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            border: Border(bottom: BorderSide(color: borderColor, width: 1)),
          ),
          child: Row(
            children: [
              Icon(icon, color: Colors.white),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  message,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
/// Content-first pane scaffold (UX mockup, `lib/screens/resource_home_screen.dart`).
///
/// The wide master/detail layout keeps the LIST on the left and renders the
/// ACTIVE item's CONTENT on the right — not a settings form. Settings live
/// behind a single [onSettings] affordance in the header bar; closing returns
/// to the content.
///
/// Purely presentational — no data/logic.
library;

import 'package:flutter/material.dart';

/// Slim header row for a content pane: title (or subtitle) + settings icon.
class ContentBar extends StatelessWidget {
  const ContentBar({
    super.key,
    this.title,
    this.subtitle,
    this.onSettings,
    this.trailing,
  });

  final String? title;
  final String? subtitle;
  final VoidCallback? onSettings;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: scheme.surfaceContainerHighest,
      child: Row(
        children: [
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (title != null)
                  Text(
                    title!,
                    style: Theme.of(context).textTheme.titleMedium,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    style: Theme.of(context).textTheme.bodySmall,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
          if (trailing != null) trailing!,
          if (onSettings != null)
            IconButton(
              tooltip: 'Settings',
              onPressed: onSettings,
              icon: const Icon(Icons.settings_outlined),
              color: scheme.primary,
            ),
        ],
      ),
    );
  }
}

/// Right-side content pane in the master/detail split: a [ContentBar] above a
/// scrollable [child]. Takes the available height provided by its parent.
class ContentPane extends StatelessWidget {
  const ContentPane({
    super.key,
    this.title,
    this.subtitle,
    this.onSettings,
    this.trailing,
    required this.child,
    this.padding = const EdgeInsets.all(12),
  });

  final String? title;
  final String? subtitle;
  final VoidCallback? onSettings;
  final Widget? trailing;
  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ContentBar(
          title: title,
          subtitle: subtitle,
          onSettings: onSettings,
          trailing: trailing,
        ),
        const SizedBox(height: 8),
        Expanded(
          child: Padding(padding: padding, child: child),
        ),
      ],
    );
  }
}
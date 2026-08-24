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
    this.leading,
    this.showModePill = false,
    this.showSettings = false,
    this.onToggleMode,
  });

  final String? title;
  final String? subtitle;
  final VoidCallback? onSettings;
  final Widget? trailing;

  /// Widget rendered before (left of) the title, e.g. action icons.
  final Widget? leading;

  /// When true, renders the content-list ⇄ settings toggle pill aligned
  /// right of the title instead of a lone settings icon.
  final bool showModePill;

  /// Current pane mode when [showModePill] is true: true = settings view.
  final bool showSettings;

  /// Called when the user taps the toggle pill (only when [showModePill]).
  final VoidCallback? onToggleMode;

  /// Compact pill that toggles between two views.
  static Widget modePill({
    required bool showSettings,
    required VoidCallback onTap,
    required ColorScheme scheme,
    IconData firstIcon = Icons.format_list_bulleted,
    IconData secondIcon = Icons.settings_outlined,
  }) {
    return Tooltip(
      message: showSettings ? 'Show overview' : 'Show details',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            height: 32,
            padding: const EdgeInsets.symmetric(horizontal: 4),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: scheme.outlineVariant),
              color: scheme.surface,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _pillIcon(
                  scheme: scheme,
                  icon: firstIcon,
                  selected: !showSettings,
                ),
                _pillIcon(
                  scheme: scheme,
                  icon: secondIcon,
                  selected: showSettings,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  static Widget _pillIcon({
    required ColorScheme scheme,
    required IconData icon,
    required bool selected,
  }) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: selected ? scheme.primary : Colors.transparent,
      ),
      child: Icon(
        icon,
        size: 18,
        color: selected ? scheme.onPrimary : scheme.onSurfaceVariant,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: scheme.surfaceContainerHighest,
      child: Row(
        children: [
          if (leading != null) ...[leading!, const SizedBox(width: 8)],
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
          if (showModePill)
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: modePill(
                showSettings: showSettings,
                onTap: () => onToggleMode?.call(),
                scheme: scheme,
              ),
            )
          else if (onSettings != null)
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
///
/// When [modeToggle] is true, the header shows a toggle pill (right of the
/// title) that switches between a content-list view (empty pane by default)
/// and the settings view ([child]). Defaults to the content-list view.
class ContentPane extends StatefulWidget {
  const ContentPane({
    super.key,
    this.title,
    this.subtitle,
    this.onSettings,
    this.trailing,
    required this.child,
    this.padding = const EdgeInsets.all(12),
    this.modeToggle = false,
    this.emptyPlaceholder,
  });

  final String? title;
  final String? subtitle;
  final VoidCallback? onSettings;
  final Widget? trailing;
  final Widget child;
  final EdgeInsetsGeometry padding;

  /// Enables the content-list ⇄ settings toggle pill in the header.
  final bool modeToggle;

  /// Widget shown in content-list mode when [modeToggle] is true.
  final Widget? emptyPlaceholder;

  @override
  State<ContentPane> createState() => _ContentPaneState();
}

class _ContentPaneState extends State<ContentPane> {
  /// false = content-list view (default), true = settings view.
  bool _showSettings = false;

  @override
  Widget build(BuildContext context) {
    final body = widget.modeToggle && !_showSettings
        ? widget.emptyPlaceholder ??
            Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.format_list_bulleted,
                    size: 40,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Nothing here yet',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                  ),
                ],
              ),
            )
        : widget.child;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ContentBar(
          title: widget.title,
          subtitle: widget.subtitle,
          onSettings: widget.onSettings,
          trailing: widget.trailing,
          showModePill: widget.modeToggle,
          showSettings: _showSettings,
          onToggleMode: () => setState(() => _showSettings = !_showSettings),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: Padding(padding: widget.padding, child: body),
        ),
      ],
    );
  }
}
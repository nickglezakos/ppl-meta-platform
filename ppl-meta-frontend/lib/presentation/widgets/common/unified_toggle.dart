/// The single unified toggle control used for every on/off in the app.
///
/// Ported from the UX mockup (`autonomous/mockups/ppl_meta_mockup`,
/// `lib/ux/unified_toggle.dart`). Behaviours:
///  * optimistic flip with an in-flight indicator,
///  * revert + snackbar on failure (the caller's [onToggle] returns success),
///  * a confirmation step for "dangerous" toggles,
///  * a consistent ≥44–48px tap target.
///
/// Purely presentational — the caller owns state via [onToggle].
library;

import 'package:flutter/material.dart';
import 'ux_breakpoints.dart';

typedef ToggleCommit = Future<bool> Function(bool next);

class UnifiedToggle extends StatefulWidget {
  const UnifiedToggle({
    super.key,
    required this.value,
    required this.onToggle,
    this.label,
    this.helper,
    this.showLabel = true,
    this.dangerous = false,
    this.confirmTitle,
    this.confirmBody,
    this.revertMessage = 'Could not update — reverted.',
  });

  final bool value;
  final ToggleCommit onToggle;
  final String? label;
  final String? helper;
  final bool showLabel;
  final bool dangerous;
  final String? confirmTitle;
  final String? confirmBody;
  final String revertMessage;

  @override
  State<UnifiedToggle> createState() => _UnifiedToggleState();
}

class _UnifiedToggleState extends State<UnifiedToggle> {
  late bool _current = widget.value;
  bool _busy = false;

  @override
  void didUpdateWidget(covariant UnifiedToggle oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!_busy && oldWidget.value != widget.value) {
      _current = widget.value;
    }
  }

  Future<void> _handle(bool next) async {
    if (_busy) return;

    if (widget.dangerous) {
      final confirmed = await _confirm();
      if (confirmed != true || !mounted) return;
    }

    setState(() {
      _busy = true;
      _current = next; // optimistic flip
    });

    final ok = await widget.onToggle(next);

    if (!mounted) return;
    setState(() {
      _busy = false;
      if (!ok) _current = widget.value; // revert on failure
    });

    if (!ok) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(widget.revertMessage)));
    }
  }

  Future<bool?> _confirm() {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(widget.confirmTitle ?? 'Confirm change?'),
        content: Text(
          widget.confirmBody ?? 'This action may have side effects. Continue?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final content = ConstrainedBox(
      constraints: const BoxConstraints(minHeight: kMinTapTarget),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (_busy)
            Padding(
              padding: EdgeInsets.only(right: widget.showLabel ? 8 : 0),
              child: SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: scheme.primary,
                ),
              ),
            )
          else
            Switch(
              value: _current,
              onChanged: _handle,
              activeThumbColor: scheme.primary,
            ),
        ],
      ),
    );

    if (!widget.showLabel) return content;

    return InkWell(
      onTap: () => _handle(!_current),
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Expanded(child: content),
            const SizedBox(width: 12),
            Expanded(
              flex: 3,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(widget.label ?? ''),
                  if (widget.helper != null)
                    Text(
                      widget.helper!,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: scheme.onSurfaceVariant),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
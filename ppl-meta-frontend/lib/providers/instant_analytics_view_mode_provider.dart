import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Instant Detection analytics view: immutable flush logs vs derived spans.
enum InstantAnalyticsViewMode {
  raw,
  normalised,
}

extension InstantAnalyticsViewModeX on InstantAnalyticsViewMode {
  bool get isNormalised => this == InstantAnalyticsViewMode.normalised;

  String get label {
    switch (this) {
      case InstantAnalyticsViewMode.raw:
        return 'Raw';
      case InstantAnalyticsViewMode.normalised:
        return 'Normalised';
    }
  }
}

/// Shared across Cameras-embedded Analytics + Instant Detection logs pane.
final instantAnalyticsViewModeProvider =
    StateProvider<InstantAnalyticsViewMode>(
  (ref) => InstantAnalyticsViewMode.raw,
);

/// Compact Raw | Normalised segmented control for Instant analytics headers.
class InstantAnalyticsViewModeToggle extends ConsumerWidget {
  const InstantAnalyticsViewModeToggle({
    super.key,
    this.onChanged,
  });

  /// Optional side-effect after the provider updates (e.g. reload lists).
  final ValueChanged<InstantAnalyticsViewMode>? onChanged;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(instantAnalyticsViewModeProvider);
    return SegmentedButton<InstantAnalyticsViewMode>(
      segments: const [
        ButtonSegment<InstantAnalyticsViewMode>(
          value: InstantAnalyticsViewMode.raw,
          label: Text('Raw'),
          icon: Icon(Icons.receipt_long, size: 16),
        ),
        ButtonSegment<InstantAnalyticsViewMode>(
          value: InstantAnalyticsViewMode.normalised,
          label: Text('Normalised'),
          icon: Icon(Icons.merge_type, size: 16),
        ),
      ],
      selected: {mode},
      onSelectionChanged: (selected) {
        if (selected.isEmpty) return;
        final next = selected.first;
        ref.read(instantAnalyticsViewModeProvider.notifier).state = next;
        onChanged?.call(next);
      },
      style: ButtonStyle(
        visualDensity: VisualDensity.compact,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        textStyle: WidgetStateProperty.all(
          const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
        ),
      ),
      showSelectedIcon: false,
    );
  }
}

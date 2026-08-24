// Theme Kit Lab - visual reference for tokens in theme_kit.dart
import 'package:flutter/material.dart';
import 'package:ppl_meta_frontend/core/theme/theme_kit.dart';
void main() {

  runApp(MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: AppTheme.darkTheme,
    home: ThemeKitPreviewScreen(),
  ));
}

class ThemeKitPreviewScreen extends StatelessWidget {
  const ThemeKitPreviewScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Theme Kit Lab')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const _Colors(), const _H(), const _Typo(), const _H(),
          const _Tokens(), const _H(), const _Icons(), const _H(),
          _Components(), const _H(), _CardTemplate(), const _H(),
          _Inputs(), const _H(),
          _Badges(), const _H(), _ActionBar(), const _H(),
          _ThemeInfo(), const SizedBox(height: 32),
        ]),
      ),
    );
  }
}

class _H extends StatelessWidget {
  const _H();
  @override Widget build(BuildContext context) => const Padding(
    padding: EdgeInsets.symmetric(vertical: AppSpacing.lg),
    child: Divider(color: AppColors.border, thickness: 1),
  );
}

class _Ttl extends StatelessWidget {
  final String t; const _Ttl(this.t);
  @override Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.md),
    child: Text(t, style: AppTextStyles.h4.copyWith(color: AppColors.textPrimary)),
  );
}

class _Sw extends StatelessWidget {
  final Color c; final String n; const _Sw({required this.c, required this.n});
  @override
  Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [
    Container(width: 56, height: 56,
      decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: AppColors.gray700))),
    const SizedBox(height: 4),
    Text(n, style: AppTextStyles.caption.copyWith(color: AppColors.textTertiary)),
  ]);
}

class _Colors extends StatelessWidget {
  const _Colors();
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    const _Ttl('Colors'),
    Wrap(spacing: 8, runSpacing: 8, children: const [
      _Sw(c: AppColors.primary, n: 'primary'), _Sw(c: AppColors.secondary, n: 'secondary'),
      _Sw(c: AppColors.accent, n: 'accent'), _Sw(c: AppColors.success, n: 'success'),
      _Sw(c: AppColors.warning, n: 'warning'), _Sw(c: AppColors.error, n: 'error'),
      _Sw(c: AppColors.surface, n: 'surface'), _Sw(c: AppColors.widgetFill, n: 'widgetFill'),
      _Sw(c: AppColors.textPrimary, n: 'textPrimary'), _Sw(c: AppColors.textSecondary, n: 'textSecondary'),
      _Sw(c: AppColors.selectedBg, n: 'selectedBg'), _Sw(c: AppColors.selectedBorder, n: 'selectedBorder'),
      _Sw(c: AppColors.gray500, n: 'gray500'), _Sw(c: AppColors.gray700, n: 'gray700'),
    ]),
  ]);
}

class _Typo extends StatelessWidget {
  const _Typo();
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    const _Ttl('Typography'),
    Text('h1', style: AppTextStyles.h1), Text('h2', style: AppTextStyles.h2),
    Text('h3', style: AppTextStyles.h3), Text('h4', style: AppTextStyles.h4),
    Text('h5', style: AppTextStyles.h5), Text('h6', style: AppTextStyles.h6),
    SizedBox(height: 8),
    Text('bodyLarge', style: AppTextStyles.bodyLarge), Text('bodyMedium', style: AppTextStyles.bodyMedium),
    Text('bodySmall', style: AppTextStyles.bodySmall),
    SizedBox(height: 8),
    Text('labelLarge', style: AppTextStyles.labelLarge), Text('labelMedium', style: AppTextStyles.labelMedium),
    Text('labelSmall', style: AppTextStyles.labelSmall),
    SizedBox(height: 8),
    Text('caption', style: AppTextStyles.caption), Text('OVERLINE', style: AppTextStyles.overline),
  ]);
}

class _Tokens extends StatelessWidget {
  const _Tokens();
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    const _Ttl('Tokens'),
    Text('Spacing: xs=${AppSpacing.xs} sm=${AppSpacing.sm} xsm=${AppSpacing.xsm} md=${AppSpacing.md} lg=${AppSpacing.lg} xl=${AppSpacing.xl}'),
    Text('Radius: xs=${AppRadius.xs} sm=${AppRadius.sm} md=${AppRadius.md} lg=${AppRadius.lg} xl=${AppRadius.xl}'),
    Text('IconSize: sm=${AppIconSize.sm} md=${AppIconSize.md} lg=${AppIconSize.lg} xl=${AppIconSize.xl} comp=${AppIconSize.cardCompact} exp=${AppIconSize.cardExpanded}'),
    Text('BP: mobile=${AppBreakpoints.mobile} tablet=${AppBreakpoints.tablet} desktop=${AppBreakpoints.desktop}'),
  ]);
}

class _Icn extends StatelessWidget {
  final IconData i; final String n; const _Icn(this.i, this.n);
  @override Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [
    Icon(i, color: AppColors.secondary, size: 26),
    Text(n, style: AppTextStyles.caption.copyWith(color: AppColors.textTertiary, fontSize: 9)),
  ]);
}

class _Icons extends StatelessWidget {
  const _Icons();
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    const _Ttl('Icons'),
    Wrap(spacing: 12, runSpacing: 12, children: const [
      _Icn(AppIcons.home,'home'), _Icn(AppIcons.settings,'settings'), _Icn(AppIcons.search,'search'),
      _Icn(AppIcons.cameras,'cameras'), _Icn(AppIcons.upload,'upload'), _Icn(AppIcons.triggers,'triggers'),
      _Icn(AppIcons.actions,'actions'), _Icn(AppIcons.storage,'storage'), _Icn(AppIcons.network,'network'),
      _Icn(AppIcons.groups,'groups'), _Icn(AppIcons.add,'add'), _Icn(AppIcons.edit,'edit'),
      _Icn(AppIcons.delete,'delete'), _Icn(AppIcons.filter,'filter'), _Icn(AppIcons.refresh,'refresh'),
      _Icn(AppIcons.close,'close'), _Icn(AppIcons.check,'check'),
    ]),
  ]);
}
class _StatusChip extends StatelessWidget {
  final String l; final Color c; const _StatusChip(this.l, this.c);
  @override Widget build(BuildContext context) => Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
    decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(2),
      border: Border.all(color: c.withValues(alpha: 0.3))),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(l=='Active'?Icons.check_circle:Icons.remove_circle, size: 12, color: c),
      const SizedBox(width: 4),
      Text(l, style: AppTextStyles.caption.copyWith(color: c, fontWeight: FontWeight.w500)),
    ]),
  );
}

class _Components extends StatelessWidget {
  const _Components();
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    const _Ttl('Components'),
    Wrap(spacing: 8, runSpacing: 8, children: [
      FilledButton(onPressed: () {}, child: const Text('Filled')),
      OutlinedButton(onPressed: () {}, child: const Text('Outlined')),
      TextButton(onPressed: () {}, child: const Text('Text')),
      IconButton(onPressed: () {}, icon: const Icon(AppIcons.add, color: AppColors.secondary),
        style: IconButton.styleFrom(backgroundColor: AppColors.secondary.withValues(alpha: 0.1))),
    ]),
    SizedBox(height: 8),
    const Chip(label: Text('Chip'), backgroundColor: AppColors.widgetFill),
    const Chip(label: Text('Selected'), backgroundColor: AppColors.selectedBg,
      side: BorderSide(color: AppColors.selectedBorder)),
    _StatusChip('Active', AppColors.success), _StatusChip('Inactive', AppColors.error),
    SizedBox(height: 8),
    Card(color: AppColors.surface, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.md),
      side: BorderSide(color: AppColors.border)),
      child: Padding(padding: EdgeInsets.all(AppSpacing.md), child: Row(children: [
        Container(width: 48, height: 48,
          decoration: BoxDecoration(color: AppColors.secondary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(AppRadius.sm)),
          child: const Icon(Icons.collections, color: AppColors.secondary)),
        SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Card', style: AppTextStyles.bodyLarge),
          SizedBox(height: 4),
          Container(padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(color: AppColors.secondary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(2),
              border: Border.all(color: AppColors.secondary.withValues(alpha: 0.3))),
            child: Text('Badge', style: AppTextStyles.caption.copyWith(color: AppColors.secondary))),
        ])),
      ])),
    ),
    SizedBox(height: 8),
    Row(children: const [Switch(value: true, onChanged: null), SizedBox(width: 16),
      Switch(value: false, onChanged: null)]),
    Row(children: const [Checkbox(value: true, onChanged: null), Checkbox(value: false, onChanged: null),
      SizedBox(width: 16), Radio(value: true, groupValue: true, onChanged: null),
      Radio(value: false, groupValue: true, onChanged: null)]),
  ]);
}
class _CardTemplate extends StatelessWidget {
  const _CardTemplate();

  Widget _infoRow(IconData icon, String text) => AppInfoRowStyle.build(icon: icon, text: text);

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const _Ttl('ListableCard Template'),
      Text('Natural-height card — no scroll, no overflow. Content pushes the '
          'footer chips down.', style: AppTextStyles.caption),
      const SizedBox(height: AppSpacing.sm),
      ListableCard(
        isSelected: true,
        onTap: () {},
        leadingIcon: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: AppColors.secondary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(Icons.bolt, color: AppColors.secondary, size: 24),
        ),
        title: const Text('Sample Trigger', style: TextStyle(fontWeight: FontWeight.w500)),
        titleBadge: Container(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
          decoration: BoxDecoration(
            color: AppColors.secondary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(AppRadius.xs),
            border: Border.all(color: AppColors.secondary.withValues(alpha: 0.3)),
          ),
          child: Text('Instant', style: AppTextStyles.caption.copyWith(color: AppColors.secondary)),
        ),
        statusBadge: Container(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs, vertical: AppSpacing.xs),
          decoration: BoxDecoration(
            color: AppColors.success.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(AppRadius.xs),
            border: Border.all(color: AppColors.success.withValues(alpha: 0.3)),
          ),
          child: Text('Active', style: AppTextStyles.caption.copyWith(color: AppColors.success)),
        ),
        body: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _infoRow(Icons.videocam_outlined, 'Main Entrance Camera'),
          const SizedBox(height: 4),
          _infoRow(Icons.rule_outlined, 'People count ≥ 1'),
          const SizedBox(height: 4),
          _infoRow(Icons.schedule_outlined, 'any time'),
        ]),
        footer: Wrap(spacing: 6, runSpacing: 6, children: const [
          Chip(label: Text('Send Alert', style: TextStyle(color: AppColors.white, fontSize: 11)),
            backgroundColor: AppColors.widgetFill),
          Chip(label: Text('Email', style: TextStyle(color: AppColors.white, fontSize: 11)),
            backgroundColor: AppColors.widgetFill),
        ]),
      ),
      const SizedBox(height: AppSpacing.sm),
      // Second card without status badge (longer body to show natural growth)
      ListableCard(
        onTap: () {},
        leadingIcon: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: AppColors.secondary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(Icons.play_circle_outline, color: AppColors.secondary, size: 24),
        ),
        title: const Text('Sample Action', style: TextStyle(fontWeight: FontWeight.w500)),
        titleBadge: Container(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
          decoration: BoxDecoration(
            color: AppColors.secondary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(AppRadius.xs),
            border: Border.all(color: AppColors.secondary.withValues(alpha: 0.3)),
          ),
          child: Text('Webhook', style: AppTextStyles.caption.copyWith(color: AppColors.secondary)),
        ),
        body: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _infoRow(Icons.notes_outlined, 'Send notification to operations channel'),
          const SizedBox(height: 4),
          _infoRow(Icons.tune_outlined, 'POST https://hooks.example.com/alert'),
        ]),
        footer: const Align(
          alignment: Alignment.centerRight,
          child: Text('Read-only', style: TextStyle(fontSize: 10, fontStyle: FontStyle.italic)),
        ),
      ),
    ]);
  }
}

class _Inputs extends StatelessWidget {
  const _Inputs();
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    const _Ttl('Inputs'),
    const TextField(decoration: InputDecoration(hintText: 'Default')),
    SizedBox(height: 8),
    const TextField(decoration: InputDecoration(hintText: 'Error', errorText: 'Sample error')),
    SizedBox(height: 8),
    SizedBox(width: 200, child: DropdownButtonFormField<String>(
      value: 'a', items: const [DropdownMenuItem(value: 'a', child: Text('A'))],
      onChanged: null, decoration: InputDecoration(labelText: 'Dropdown'))),
  ]);
}

class _Badges extends StatelessWidget {
  const _Badges();
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    const _Ttl('Badges'),
    Wrap(spacing: 8, runSpacing: 8, children: [
      Container(padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2), decoration: AppBadgeStyles.active(),
        child: const Text('Active', style: TextStyle(color: AppColors.success, fontSize: 11))),
      Container(padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2), decoration: AppBadgeStyles.inactive(),
        child: const Text('Inactive', style: TextStyle(color: AppColors.textDisabled, fontSize: 11))),
      Container(padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2), decoration: AppBadgeStyles.warning(),
        child: const Text('Warning', style: TextStyle(color: AppColors.warning, fontSize: 11))),
      Container(padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2), decoration: AppBadgeStyles.error(),
        child: const Text('Error', style: TextStyle(color: AppColors.error, fontSize: 11))),
    ]),
  ]);
}

class _ActionBar extends StatelessWidget {
  const _ActionBar();
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    const _Ttl('ListableItemsActionBar'),
    ListableItemsActionBar(searchController: TextEditingController(), onCreate: () {},
      filterContent: Center(child: ToggleButtons(
        isSelected: const [true, false, false], onPressed: null,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        constraints: const BoxConstraints(minHeight: 32),
        children: const [
          Padding(padding: EdgeInsets.symmetric(horizontal: 12), child: Text('All')),
          Padding(padding: EdgeInsets.symmetric(horizontal: 12), child: Text('Active')),
          Padding(padding: EdgeInsets.symmetric(horizontal: 12), child: Text('Inactive')),
        ],
      )),
    ),
    SizedBox(height: 12),
    const _Ttl('FilterPill'),
    Wrap(spacing: 8, children: [
      FilterPill(label: 'Date Range', icon: Icons.calendar_today, onTap: () {}),
      FilterPill(label: 'Status', icon: Icons.filter_alt, active: true, onTap: () {}),
      FilterPill(label: 'Category', icon: Icons.category, onTap: () {}),
    ]),
  ]);
}

class _ThemeInfo extends StatelessWidget {
  const _ThemeInfo();
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    const _Ttl('ThemeData'),
    Text('AppTheme.darkTheme applied', style: AppTextStyles.bodyMedium),
    Text('accent: ${AppColors.accent}', style: AppTextStyles.caption),
    Text('primary: ${AppColors.primary}', style: AppTextStyles.caption),
  ]);
}

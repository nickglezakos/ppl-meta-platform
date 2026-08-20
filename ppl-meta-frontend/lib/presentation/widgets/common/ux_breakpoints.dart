/// Shared responsive breakpoints for the PPL Meta frontend.
///
/// Ported from the UX mockup (`autonomous/mockups/ppl_meta_mockup`,
/// `lib/ux/breakpoints.dart`) so every screen derives its layout from ONE
/// source of truth instead of ad-hoc `MediaQuery`/`LayoutBuilder` widths.
///
/// This is a UX-only foundation — it does NOT touch any data/logic.
library;

import 'package:flutter/widgets.dart';

/// Breakpoint buckets used across the app.
enum UxBp { mobile, tablet, desktop }

/// Mirror the plan doc's responsive table: <600 mobile, 600–1024 tablet, ≥1024 desktop.
UxBp uxBpFromWidth(double width) {
  if (width < 600) return UxBp.mobile;
  if (width < 1024) return UxBp.tablet;
  return UxBp.desktop;
}

/// Breakpoint of the current [context].
UxBp uxBpOf(BuildContext context) {
  return uxBpFromWidth(MediaQuery.sizeOf(context).width);
}

/// Wide enough for a master/detail split (desktop).
bool isWide(BuildContext context) => uxBpOf(context) == UxBp.desktop;

/// Narrow (phone) — single column, full-screen editors.
bool isMobile(BuildContext context) => uxBpOf(context) == UxBp.mobile;

/// Tablet — dialog-based editors become available.
bool isTablet(BuildContext context) => uxBpOf(context) == UxBp.tablet;

/// Preferred width of the persistent master (list) pane on desktop.
const double kMasterPaneWidth = 380;

/// Minimum comfortable tap target (44–48dp) for touch controls.
const double kMinTapTarget = 48;
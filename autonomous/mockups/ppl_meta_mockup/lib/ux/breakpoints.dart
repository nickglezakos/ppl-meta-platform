/// Shared responsive breakpoint utility.
///
/// One utility drives the whole prototype so no screen computes its own widths.
library;

import 'package:flutter/widgets.dart';

enum UxBp { mobile, tablet, desktop }

/// Breakpoints mirror the plan doc's table (§6).
UxBp uxBpFromWidth(double width) {
  if (width < 600) return UxBp.mobile;
  if (width < 1024) return UxBp.tablet;
  return UxBp.desktop;
}

UxBp uxBpOf(BuildContext context) =>
    uxBpFromWidth(MediaQuery.sizeOf(context).width);

/// Desktop = wide enough for the master/detail split.
bool isWide(BuildContext context) => uxBpOf(context) == UxBp.desktop;

/// Tablet shows the editor in a dialog instead of full-screen.
bool isTablet(BuildContext context) => uxBpOf(context) == UxBp.tablet;

/// Mobile shows the editor full-screen.
bool isMobile(BuildContext context) => uxBpOf(context) == UxBp.mobile;

/// Width of the persistent master (list) pane on desktop.
const double kMasterPaneWidth = 380;

/// Minimum comfortable tap-target for the unified toggle (44–48dp).
const double kMinTapTarget = 48;
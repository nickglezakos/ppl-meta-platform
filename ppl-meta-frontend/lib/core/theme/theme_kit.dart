// =============================================================================
// PPL Meta — Theme Kit
// =============================================================================
// Single source of truth for ALL design tokens, component styles, icon
// constants, and full ThemeData builders.  Import this file everywhere you
// need theme/UX values:
//
//   import '../core/theme/theme_kit.dart';
//
// Sections:
//   1.  Raw palette             — _Palette (private, never used directly)
//   2.  Semantic colors          — AppColors
//   3.  Icon map                 — AppIcons
//   4.  Typography               — AppTextStyles
//   5.  Spacing / Radii / …      — AppSpacing, AppRadius, AppShadows, …
//   6.  Component style presets  — AppButtonStyles, AppInputTheme, …
//   7.  Full ThemeData builders  — AppTheme
//   8.  BuildContext helpers      — ThemeKitX
// =============================================================================

import 'package:flutter/material.dart';
import '../../utils/offline_fonts.dart';

// ---------------------------------------------------------------------------
// 1.  Raw palette
// ---------------------------------------------------------------------------

class _Palette {
  // Brand core
  static const Color cyan400   = Color(0xFF22D3EE);
  static const Color blue700   = Color(0xFF1976D2);

  // Surfaces (dark theme defaults)
  static const Color nearBlack     = Color(0xFF0A0A0F);
  static const Color surfaceDark   = Color(0xFF0F0F14);
  static const Color widgetFill    = Color(0xFF050509);

  // Semantic state colours
  static const Color green500  = Color(0xFF4CAF50);
  static const Color amber500  = Color(0xFFFFC107);
  static const Color red300    = Color(0xFFCF6679);
  static const Color blue500   = Color(0xFF2196F3);

  // Media type colours
  static const Color greenMD   = Color(0xFF4CAF50);
  static const Color blueMD    = Color(0xFF2196F3);
  static const Color purple500 = Color(0xFF9C27B0);
  static const Color brown500  = Color(0xFF795548);

  // Neutral scale
  static const Color white      = Color(0xFFFFFFFF);
  static const Color black      = Color(0xFF000000);
  static const Color gray50     = Color(0xFFFAFAFA);
  static const Color gray100    = Color(0xFFF5F5F5);
  static const Color gray200    = Color(0xFFEEEEEE);
  static const Color gray300    = Color(0xFFE0E0E0);
  static const Color gray400    = Color(0xFFBDBDBD);
  static const Color gray500    = Color(0xFF9E9E9E);
  static const Color gray600    = Color(0xFF757575);
  static const Color gray700    = Color(0xFF616161);
  static const Color gray800    = Color(0xFF424242);
  static const Color gray900    = Color(0xFF212121);

  // Text colours (dark theme)
  static const Color textWhite      = Color(0xFFFFFFFF);
  static const Color textSecondary  = Color(0xFFBBBBBB);
  static const Color textTertiary   = Color(0xFF888888);
}
// ---------------------------------------------------------------------------
// 2.  Semantic colour tokens
// ---------------------------------------------------------------------------

/// Semantic colour tokens for the PPL Meta platform.
/// Every screen should use these constants — never hard-coded Color(0xFF…)
/// or Colors.orange.  Changing the palette app-wide is then a single edit
/// in [_Palette].
class AppColors {
  // ——— Surfaces ———
  static const Color background      = _Palette.nearBlack;
  static const Color surface         = _Palette.nearBlack;
  static const Color surfaceVariant  = _Palette.surfaceDark;
  static const Color widgetFill      = _Palette.widgetFill;
  static const Color cardBackground  = _Palette.surfaceDark;

  // ——— Brand ———
  static const Color primary   = _Palette.blue700;
  static const Color secondary = _Palette.cyan400;
  static const Color accent    = _Palette.cyan400;

  // ——— Interactive states ———
  static const Color selected       = _Palette.cyan400;
  static const Color selectedBg     = Color(0x1622D3EE);
  static const Color selectedBorder = Color(0x4022D3EE);

  // ——— Semantic states ———
  static const Color success = _Palette.green500;
  static const Color warning = _Palette.amber500;
  static const Color error   = _Palette.red300;
  static const Color info    = _Palette.blue500;

  // ——— Text ———
  static const Color textPrimary   = _Palette.textWhite;
  static const Color textSecondary = _Palette.textSecondary;
  static const Color textTertiary  = _Palette.textTertiary;
  static const Color textOnPrimary = _Palette.textWhite;
  static const Color textDisabled  = _Palette.gray600;

  // ——— Media type ———
  static const Color imageColor    = _Palette.greenMD;
  static const Color videoColor    = _Palette.blueMD;
  static const Color audioColor    = _Palette.purple500;
  static const Color documentColor = _Palette.brown500;

  // ——— Upload state ———
  static const Color uploadPending    = _Palette.amber500;
  static const Color uploadInProgress = _Palette.blue500;
  static const Color uploadCompleted  = _Palette.green500;
  static const Color uploadFailed     = _Palette.red300;

  // ——— Grey / border ———
  static const Color white    = _Palette.white;
  static const Color black    = _Palette.black;
  static const Color gray50   = _Palette.gray50;
  static const Color gray100  = _Palette.gray100;
  static const Color gray200  = _Palette.gray200;
  static const Color gray300  = _Palette.gray300;
  static const Color gray400  = _Palette.gray400;
  static const Color gray500  = _Palette.gray500;
  static const Color gray600  = _Palette.gray600;
  static const Color gray700  = _Palette.gray700;
  static const Color gray800  = _Palette.gray800;
  static const Color gray900  = _Palette.gray900;
  static const Color border   = _Palette.surfaceDark;
  static const Color divider  = _Palette.surfaceDark;
}
// ---------------------------------------------------------------------------
// 3.  Icon map
// ---------------------------------------------------------------------------

/// Named icon constants — change an icon app‑wide by editing it once here.
class AppIcons {
  // ——— Navigation ———
  static const IconData home       = Icons.home;
  static const IconData back       = Icons.arrow_back;
  static const IconData settings   = Icons.settings;
  static const IconData refresh    = Icons.refresh;
  static const IconData help       = Icons.help_outline;
  static const IconData close      = Icons.close;
  static const IconData logout     = Icons.logout;
  static const IconData search     = Icons.search;
  static const IconData menu       = Icons.menu;
  static const IconData moreVert   = Icons.more_vert;
  static const IconData arrowDropDown = Icons.arrow_drop_down;

  // ——— Feature modules ———
  static const IconData cameras       = Icons.videocam_outlined;
  static const IconData collections   = Icons.collections_bookmark_outlined;
  static const IconData media         = Icons.photo_library_outlined;
  static const IconData upload        = Icons.cloud_upload_outlined;
  static const IconData triggers      = Icons.bolt;
  static const IconData actions       = Icons.play_circle_outline;
  static const IconData presence      = Icons.verified_user_outlined;
  static const IconData signage       = Icons.tv_outlined;
  static const IconData monitoring    = Icons.auto_awesome_outlined;
  static const IconData storage       = Icons.storage_outlined;
  static const IconData network       = Icons.lan_outlined;
  static const IconData groups        = Icons.groups_outlined;
  static const IconData analytics     = Icons.analytics_outlined;
  static const IconData gallery       = Icons.photo_library_outlined;
  static const IconData workflows     = Icons.auto_awesome_outlined;
  static const IconData cameraOps     = Icons.monitor_heart_outlined;
  static const IconData people        = Icons.people_outlined;
  static const IconData person        = Icons.person_outline;
  static const IconData badge         = Icons.badge_outlined;
  static const IconData roles         = Icons.admin_panel_settings_outlined;
  static const IconData users         = Icons.people_outlined;
  static const IconData profile       = Icons.person_outline;

  // ——— CRUD actions ———
  static const IconData add         = Icons.add;
  static const IconData addCircle   = Icons.add_circle;
  static const IconData create      = Icons.add;
  static const IconData edit        = Icons.edit;
  static const IconData delete      = Icons.delete;
  static const IconData deleteOutline = Icons.delete_outline;
  static const IconData save        = Icons.save;
  static const IconData cancel      = Icons.cancel;
  static const IconData copy        = Icons.copy;
  static const IconData share       = Icons.share;
  static const IconData download    = Icons.download;
  static const IconData uploadFile  = Icons.upload_file;

  // ——— Filter & sort ———
  static const IconData filter    = Icons.filter_alt;
  static const IconData sort      = Icons.sort;
  static const IconData clear     = Icons.clear;
  static const IconData clearAll  = Icons.clear_all;

  // ——— States ———
  static const IconData active    = Icons.check_circle;
  static const IconData inactive  = Icons.remove_circle_outline;
  static const IconData error     = Icons.error_outline;
  static const IconData warning   = Icons.warning;
  static const IconData success   = Icons.check_circle;
  static const IconData info      = Icons.info_outline;
  static const IconData check     = Icons.check;
  static const IconData clock     = Icons.access_time;
  static const IconData lock      = Icons.lock;
  static const IconData visibility     = Icons.visibility;
  static const IconData visibilityOff  = Icons.visibility_off;

  // ——— Expand / collapse ———
  static const IconData expandLess    = Icons.expand_less;
  static const IconData expandMore    = Icons.expand_more;
  static const IconData chevronLeft   = Icons.chevron_left;
  static const IconData chevronRight  = Icons.chevron_right;

  // ——— Misc ———
  static const IconData dashboard  = Icons.dashboard_outlined;
  static const IconData list       = Icons.list_alt_outlined;
  static const IconData play       = Icons.play_arrow;
  static const IconData stop       = Icons.stop;
  static const IconData sync       = Icons.sync;
  static const IconData star       = Icons.star;
  static const IconData qrCode     = Icons.qr_code_scanner;
  static const IconData cameraAlt  = Icons.camera_alt;
  static const IconData photo      = Icons.photo;
  static const IconData videoFile  = Icons.video_file;
  static const IconData attachment = Icons.attachment;
  static const IconData link       = Icons.link;
  static const IconData email      = Icons.email_outlined;
  static const IconData phone      = Icons.phone;
  static const IconData calendar   = Icons.calendar_today;
  static const IconData playlist   = Icons.playlist_play;
  static const IconData devices    = Icons.devices;
  static const IconData tune       = Icons.tune;
  static const IconData timeline   = Icons.timeline;
  static const IconData security   = Icons.security;
  static const IconData bolt       = Icons.bolt;
  static const IconData verified   = Icons.verified_user;
  static const IconData description = Icons.description;
  static const IconData schedule   = Icons.schedule;
  static const IconData send       = Icons.send;
  static const IconData chat       = Icons.chat_bubble;
  static const IconData psychology = Icons.psychology;
}
// ---------------------------------------------------------------------------
// 4.  Typography
// ---------------------------------------------------------------------------

/// Predefined text styles built from [OfflineFonts].
class AppTextStyles {
  // Headings
  static final h1 = OfflineFonts.roboto(fontSize: 32, fontWeight: FontWeight.bold);
  static final h2 = OfflineFonts.roboto(fontSize: 28, fontWeight: FontWeight.bold);
  static final h3 = OfflineFonts.roboto(fontSize: 24, fontWeight: FontWeight.bold);
  static final h4 = OfflineFonts.roboto(fontSize: 20, fontWeight: FontWeight.bold);
  static final h5 = OfflineFonts.roboto(fontSize: 18, fontWeight: FontWeight.bold);
  static final h6 = OfflineFonts.roboto(fontSize: 16, fontWeight: FontWeight.bold);

  // Body
  static final bodyLarge  = OfflineFonts.roboto(fontSize: 16);
  static final bodyMedium = OfflineFonts.roboto(fontSize: 14);
  static final bodySmall  = OfflineFonts.roboto(fontSize: 12);

  // Subtitle (compatibility)
  static final subtitle1 = OfflineFonts.roboto(fontSize: 16, fontWeight: FontWeight.w500);
  static final subtitle2 = OfflineFonts.roboto(fontSize: 14, fontWeight: FontWeight.w500);

  // Labels
  static final labelLarge  = OfflineFonts.roboto(fontSize: 14, fontWeight: FontWeight.w500);
  static final labelMedium = OfflineFonts.roboto(fontSize: 12, fontWeight: FontWeight.w500);
  static final labelSmall  = OfflineFonts.roboto(fontSize: 11, fontWeight: FontWeight.w500);

  // Utility
  static final caption  = OfflineFonts.roboto(fontSize: 12);
  static final overline = OfflineFonts.roboto(
    fontSize: 10,
    letterSpacing: 1.2,
    fontWeight: FontWeight.w500,
  );
}

// ---------------------------------------------------------------------------
// 5.  Spacing / Radii / Shadows / Durations / Curves
// ---------------------------------------------------------------------------

/// Consistent spacing scale.
class AppSpacing {
  static const double xs    = 4.0;
  static const double xsm   = 12.0; // between sm and md
  static const double sm    = 8.0;
  static const double md    = 16.0;
  static const double lg    = 24.0;
  static const double xl    = 32.0;
  static const double xxl   = 48.0;

  static const double padding      = 16.0;
  static const double margin       = 16.0;
  static const double cardPadding  = 16.0;
  static const double buttonHeight    = 48.0;
  static const double listItemHeight  = 56.0;
  static const double minTapTarget    = 48.0;
  static const double gridSpacing    = 16.0;
  static const double sectionSpacing = 24.0;

  /// Card inset used in cards: fromLTRB(14, 16, 14, 16).
  static const EdgeInsets cardInset = EdgeInsets.fromLTRB(14, 16, 14, 16);

  /// Vertical gap between info rows inside a card.
  static const double cardInfoRowGap = 6.0;
}

/// Consistent border-radius scale.
class AppRadius {
  static const double xs  = 2.0;
  static const double sm  = 4.0;
  static const double md  = 8.0;
  static const double lg  = 12.0;
  static const double xl  = 16.0;
  static const double xxl = 24.0;

  /// Specific radii used in chips and badges.
  static const double chip = 6.0;
  static const double chipBadge = 4.0;
}

/// Icon sizing tokens.
class AppIconSize {
  static const double sm   = 16.0;
  static const double md   = 18.0;
  static const double lg   = 20.0;
  static const double xl   = 24.0;
  static const double cardCompact  = 40.0;
  static const double cardExpanded = 52.0;
  static const double tabIcon = 22.0;
  static const double cardInfoRow  = 14.0; // icon in card info rows
  static const double chipIcon     = 16.0;
}

/// Responsive breakpoint tokens.
class AppBreakpoints {
  static const double mobile = 600.0;
  static const double tablet = 900.0;
  static const double desktop = 1024.0;
  static const double masterPaneWidth = 380.0;
}

/// Elevation shadow presets.
class AppShadows {
  static const BoxShadow sm = BoxShadow(
    color: Color(0x1A000000), blurRadius: 2, offset: Offset(0, 1),
  );
  static const BoxShadow md = BoxShadow(
    color: Color(0x1A000000), blurRadius: 4, offset: Offset(0, 2),
  );
  static const BoxShadow lg = BoxShadow(
    color: Color(0x1A000000), blurRadius: 8, offset: Offset(0, 4),
  );
}

/// Animation durations.
class AppDurations {
  static const Duration fast   = Duration(milliseconds: 150);
  static const Duration normal = Duration(milliseconds: 300);
  static const Duration slow   = Duration(milliseconds: 500);
}

/// Animation curves.
class AppCurves {
  static const Curve easeInOut = Curves.easeInOut;
  static const Curve easeIn    = Curves.easeIn;
  static const Curve easeOut   = Curves.easeOut;
  static const Curve bounce    = Curves.bounceOut;
}
// ---------------------------------------------------------------------------
// 6.  Component style presets
// ---------------------------------------------------------------------------

/// Button style factories for the app's three button tiers.
class AppButtonStyles {
  /// Primary filled button — dark fill, outline border.
  static ButtonStyle primary(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return FilledButton.styleFrom(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(color: scheme.outline),
      ),
      backgroundColor: AppColors.widgetFill,
      foregroundColor: scheme.onSurface,
      elevation: 0,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
    );
  }

  /// Outlined button.
  static ButtonStyle outlined(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return OutlinedButton.styleFrom(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      side: BorderSide(color: scheme.outline),
      foregroundColor: scheme.onSurface,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    );
  }

  /// Text button (no border, subtle hover).
  static ButtonStyle text(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return TextButton.styleFrom(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(color: scheme.outline.withValues(alpha: 0.5)),
      ),
      foregroundColor: scheme.onSurface,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    );
  }

  /// Danger-styled outlined button (e.g. delete).
  static ButtonStyle danger(BuildContext context) {
    return OutlinedButton.styleFrom(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      side: const BorderSide(color: AppColors.error),
      foregroundColor: AppColors.error,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    );
  }

  /// Icon-only button.
  static ButtonStyle icon(BuildContext context) {
    return IconButton.styleFrom(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
    );
  }
}
/// Input decoration theme presets.
class AppInputTheme {
  /// Dark mode input theme used across the app.
  static InputDecorationTheme dark(ColorScheme scheme) {
    return InputDecorationTheme(
      filled: true,
      fillColor: AppColors.widgetFill,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        borderSide: BorderSide(color: scheme.outline),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        borderSide: BorderSide(color: scheme.outline),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        borderSide: BorderSide(color: scheme.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        borderSide: const BorderSide(color: AppColors.error),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      labelStyle: TextStyle(color: scheme.onSurfaceVariant),
      hintStyle: TextStyle(color: scheme.onSurfaceVariant.withValues(alpha: 0.6)),
    );
  }

  /// Light mode input theme.
  static InputDecorationTheme light(ColorScheme scheme) {
    return InputDecorationTheme(
      filled: true,
      fillColor: scheme.surfaceContainer,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        borderSide: BorderSide(color: scheme.outline),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        borderSide: BorderSide(color: scheme.outline),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        borderSide: BorderSide(color: scheme.primary, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      labelStyle: TextStyle(color: scheme.onSurfaceVariant),
      hintStyle: TextStyle(color: scheme.onSurfaceVariant.withValues(alpha: 0.6)),
    );
  }
}

/// Card theme presets.
class AppCardTheme {
  static CardThemeData dark(ColorScheme scheme) {
    return CardThemeData(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(color: scheme.outline),
      ),
      elevation: 0,
      color: AppColors.widgetFill,
    );
  }

  static CardThemeData light(ColorScheme scheme) {
    return CardThemeData(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(color: scheme.outline),
      ),
      elevation: 0,
    );
  }

  static CardThemeData highlighted() {
    return CardThemeData(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: const BorderSide(color: AppColors.selectedBorder),
      ),
      color: AppColors.selectedBg,
      elevation: 0,
    );
  }
}

/// Tab bar theme presets.
class AppTabTheme {
  static TabBarTheme dark() {
    return TabBarTheme(
      indicatorColor: AppColors.accent,
      labelColor: AppColors.accent,
      unselectedLabelColor: AppColors.textDisabled,
      labelStyle: AppTextStyles.labelMedium,
      unselectedLabelStyle: AppTextStyles.labelMedium,
      indicatorSize: TabBarIndicatorSize.tab,
      dividerColor: Colors.transparent,
    );
  }

  static TabBar tabBar({
    required TabController controller,
    required List<Widget> tabs,
    bool isScrollable = false,
  }) {
    return TabBar(
      controller: controller,
      tabs: tabs,
      isScrollable: isScrollable,
      indicatorColor: AppColors.accent,
      labelColor: AppColors.accent,
      unselectedLabelColor: AppColors.textDisabled,
    );
  }
}
// ---------------------------------------------------------------------------

/// Shared info-row style for card info grids (trigger & action cards).
class AppInfoRowStyle {
  /// Builds a consistent info row: [icon] + [text] with kit tokens.
  static Widget build({
    required IconData icon,
    required String text,
    Color? color,
  }) {
    final textColor = color ?? Colors.white.withValues(alpha: 0.8);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: AppIconSize.cardInfoRow, color: textColor),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            text,
            style: TextStyle(fontSize: 12.5, color: textColor),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

/// Chip theme presets.
class AppChipTheme {
  static ChipThemeData dark(ColorScheme scheme) {
    return ChipThemeData(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        side: BorderSide(color: scheme.outline),
      ),
      backgroundColor: AppColors.widgetFill,
      labelStyle: TextStyle(color: scheme.onSurface),
      secondaryLabelStyle: TextStyle(color: scheme.onSurface),
      selectedColor: AppColors.selectedBg,
      deleteIconColor: scheme.onSurfaceVariant,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    );
  }
}

/// Dialog theme presets.
class AppDialogTheme {
  static DialogThemeData dark(ColorScheme scheme) {
    return DialogThemeData(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(color: scheme.outline),
      ),
      backgroundColor: AppColors.widgetFill,
      elevation: 0,
    );
  }
}

/// Badge-style constants for status chips / badges.
class AppBadgeStyles {
  static BoxDecoration active({double borderRadius = AppRadius.md}) {
    return BoxDecoration(
      color: AppColors.success.withValues(alpha: 0.15),
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: AppColors.success.withValues(alpha: 0.4)),
    );
  }

  static BoxDecoration inactive({double borderRadius = AppRadius.md}) {
    return BoxDecoration(
      color: AppColors.textDisabled.withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: AppColors.textDisabled.withValues(alpha: 0.3)),
    );
  }

  static BoxDecoration warning({double borderRadius = AppRadius.md}) {
    return BoxDecoration(
      color: AppColors.warning.withValues(alpha: 0.15),
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: AppColors.warning.withValues(alpha: 0.4)),
    );
  }

  static BoxDecoration error({double borderRadius = AppRadius.md}) {
    return BoxDecoration(
      color: AppColors.error.withValues(alpha: 0.15),
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: AppColors.error.withValues(alpha: 0.4)),
    );
  }
}

/// Divider theme presets.
class AppDividerTheme {
  static DividerThemeData dark(ColorScheme scheme) {
    return DividerThemeData(
      color: scheme.outline,
      thickness: 1,
      space: 1,
    );
  }
}
/// Popup menu theme presets.
class AppPopupTheme {
  static PopupMenuThemeData dark(ColorScheme scheme) {
    return PopupMenuThemeData(
      color: AppColors.widgetFill,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(color: scheme.outline),
      ),
      elevation: 0,
      textStyle: TextStyle(color: scheme.onSurface),
      menuPadding: EdgeInsets.zero,
    );
  }
}

/// Menu (dropdown) theme presets.
class AppMenuTheme {
  static MenuThemeData dark(ColorScheme scheme) {
    return MenuThemeData(
      style: MenuStyle(
        backgroundColor: WidgetStateProperty.all(AppColors.widgetFill),
        shape: WidgetStateProperty.all(
          RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.lg),
            side: BorderSide(color: scheme.outline),
          ),
        ),
        elevation: WidgetStateProperty.all(0),
      ),
    );
  }
}

/// List tile theme presets.
class AppListTileTheme {
  static ListTileThemeData dark(ColorScheme scheme) {
    return ListTileThemeData(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(color: scheme.outline.withValues(alpha: 0.3)),
      ),
      tileColor: AppColors.widgetFill,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 0),
    );
  }
}

/// Floating action button theme presets.
class AppFabTheme {
  static FloatingActionButtonThemeData dark(ColorScheme scheme) {
    return FloatingActionButtonThemeData(
      backgroundColor: AppColors.widgetFill,
      foregroundColor: scheme.onSurface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.xl),
        side: BorderSide(color: scheme.outline),
      ),
    );
  }
}
// ---------------------------------------------------------------------------
// 7.  Full ThemeData builders
// ---------------------------------------------------------------------------

/// Complete Material 3 [ThemeData] builders that wire every component preset
/// together so screens and widgets render consistently.
class AppTheme {
  AppTheme._();

  static final ColorScheme _darkColorScheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    brightness: Brightness.dark,
  ).copyWith(
    surface: AppColors.background,
    surfaceContainerHighest: AppColors.surfaceVariant,
  );

  static final ColorScheme _lightColorScheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    brightness: Brightness.light,
  );

  /// Dark theme.
  static ThemeData get darkTheme {
    final scheme = _darkColorScheme;
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      textTheme: OfflineFonts.robotoTextTheme(ThemeData.dark().textTheme),

      inputDecorationTheme: AppInputTheme.dark(scheme),
      cardTheme: AppCardTheme.dark(scheme),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.lg),
            side: BorderSide(color: scheme.outline),
          ),
          backgroundColor: AppColors.widgetFill,
          foregroundColor: scheme.onSurface,
          elevation: 0,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.lg),
          ),
          side: BorderSide(color: scheme.outline),
          foregroundColor: scheme.onSurface,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.lg),
            side: BorderSide(color: scheme.outline.withValues(alpha: 0.5)),
          ),
          foregroundColor: scheme.onSurface,
        ),
      ),
      floatingActionButtonTheme: AppFabTheme.dark(scheme),

      dividerTheme: AppDividerTheme.dark(scheme),
      dialogTheme: AppDialogTheme.dark(scheme),
      popupMenuTheme: AppPopupTheme.dark(scheme),
      menuTheme: AppMenuTheme.dark(scheme),

      dropdownMenuTheme: DropdownMenuThemeData(
        menuStyle: MenuStyle(
          backgroundColor: WidgetStateProperty.all(AppColors.widgetFill),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.lg),
              side: BorderSide(color: scheme.outline),
            ),
          ),
          elevation: WidgetStateProperty.all(0),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: AppColors.widgetFill,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.lg),
            borderSide: BorderSide(color: scheme.outline),
          ),
        ),
      ),

      listTileTheme: AppListTileTheme.dark(scheme),

      tabBarTheme: TabBarThemeData(
        indicatorColor: AppColors.accent,
        labelColor: AppColors.accent,
        unselectedLabelColor: AppColors.textDisabled,
        labelStyle: AppTextStyles.labelMedium,
        unselectedLabelStyle: AppTextStyles.labelMedium,
        indicatorSize: TabBarIndicatorSize.tab,
        dividerColor: Colors.transparent,
      ),

      appBarTheme: AppBarTheme(
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        elevation: 0,
        centerTitle: true,
      ),

      bottomSheetTheme: BottomSheetThemeData(
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
          side: BorderSide(color: AppColors.border),
        ),
        backgroundColor: AppColors.widgetFill,
        elevation: 0,
      ),

      chipTheme: AppChipTheme.dark(scheme),

      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: scheme.primary,
        linearTrackColor: scheme.surfaceContainerHighest,
      ),

      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return scheme.primary;
          return scheme.onSurfaceVariant;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return scheme.primary.withValues(alpha: 0.5);
          }
          return scheme.surfaceContainerHighest;
        }),
      ),

      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return scheme.primary;
          return null;
        }),
        checkColor: WidgetStateProperty.all(scheme.onPrimary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
      ),

      radioTheme: RadioThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return scheme.primary;
          return scheme.onSurfaceVariant;
        }),
      ),
    );
  }
/// Light theme.
  static ThemeData get lightTheme {
    final scheme = _lightColorScheme;
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: scheme,
      textTheme: OfflineFonts.robotoTextTheme(ThemeData.light().textTheme),
      inputDecorationTheme: AppInputTheme.light(scheme),
      cardTheme: AppCardTheme.light(scheme),
      dividerTheme: DividerThemeData(color: scheme.outline, thickness: 1),
      appBarTheme: AppBarTheme(
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        elevation: 0,
        centerTitle: true,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.lg),
          ),
          elevation: 0,
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// 8.  BuildContext extension helpers
// ---------------------------------------------------------------------------

/// Convenience extensions for common theme queries.
extension ThemeKitX on BuildContext {
  /// Current [ColorScheme] from the Material theme.
  ColorScheme get colorScheme => Theme.of(this).colorScheme;

  /// Whether the screen is narrow enough for mobile layout (< 600 dp).
  bool get isMobile => MediaQuery.sizeOf(this).width < 600;

  /// Whether the screen is tablet width (600–1024 dp).
  bool get isTablet {
    final w = MediaQuery.sizeOf(this).width;
    return w >= 600 && w < 1024;
  }

  /// Whether the screen is desktop width (>= 1024 dp).
  bool get isDesktop => MediaQuery.sizeOf(this).width >= 1024;
}

// =============================================================================
// ---------------------------------------------------------------------------
//  Shared reusable widgets
// ---------------------------------------------------------------------------

/// A compact action bar for list screens: search + create icon + filter area.
///
/// Layout:
///   Row 1: [ Search field (flex) ][ + create icon ]
///   Row 2: [ filter toggles / filter placeholder slots ]
///
/// Every screen with a list can import this from the kit for consistent UX.
class ListableItemsActionBar extends StatelessWidget {
  const ListableItemsActionBar({
    super.key,
    required this.searchController,
    this.onSearchChanged,
    this.onCreate,
    this.onCreateLabel,
    this.filterContent,
    this.filterPlaceholder1,
    this.filterPlaceholder2,
    this.filterPlaceholder3,
    this.countLabel,
  });

  final TextEditingController searchController;
  final ValueChanged<String>? onSearchChanged;
  final VoidCallback? onCreate;
  final String? onCreateLabel;
  final Widget? filterContent;
  final Widget? filterPlaceholder1;
  final Widget? filterPlaceholder2;
  final Widget? filterPlaceholder3;
  final Widget? countLabel;

  @override
  Widget build(BuildContext context) {
    final isCompact = MediaQuery.sizeOf(context).width < AppBreakpoints.mobile;

    return Container(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Row 1: Search + Create
          Padding(
            padding: EdgeInsets.fromLTRB(
              AppSpacing.md,
              isCompact ? AppSpacing.sm : AppSpacing.md,
              AppSpacing.sm,
              0,
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: searchController,
                    onChanged: onSearchChanged,
                    decoration: InputDecoration(
                      hintText: 'Search...',
                      prefixIcon: const Icon(AppIcons.search, size: 20),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(AppRadius.sm),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.sm, vertical: AppSpacing.sm,
                      ),
                      isDense: true,
                    ),
                  ),
                ),
                if (onCreate != null) ...[
                  const SizedBox(width: AppSpacing.sm),
                  IconButton(
                    onPressed: onCreate,
                    icon: const Icon(AppIcons.add, color: AppColors.secondary),
                    tooltip: onCreateLabel ?? 'Create',
                    style: IconButton.styleFrom(
                      backgroundColor: AppColors.secondary.withValues(alpha: 0.1),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.sm),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          // Row 2: Filters
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.sm,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (filterContent != null) filterContent!,
                if (filterPlaceholder1 != null ||
                    filterPlaceholder2 != null ||
                    filterPlaceholder3 != null) ...[
                  const SizedBox(height: AppSpacing.sm),
                  isCompact
                      ? SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: _buildFilterPlaceholdersRow(),
                        )
                      : _buildFilterPlaceholdersRow(),
                ],
                if (countLabel != null) ...[
                  const SizedBox(height: AppSpacing.xs),
                  countLabel!,
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterPlaceholdersRow() {
    return Row(
      children: [
        if (filterPlaceholder1 != null) ...[filterPlaceholder1!, const SizedBox(width: AppSpacing.sm)],
        if (filterPlaceholder2 != null) ...[filterPlaceholder2!, const SizedBox(width: AppSpacing.sm)],
        if (filterPlaceholder3 != null) filterPlaceholder3!,
      ],
    );
  }
}
/// A pill-shaped filter chip for use inside [ListableItemsActionBar] placeholders.
class FilterPill extends StatelessWidget {
  const FilterPill({
    super.key,
    required this.label,
    required this.icon,
    this.onTap,
    this.active = false,
    this.activeColor,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final bool active;
  final Color? activeColor;

  @override
  Widget build(BuildContext context) {
    final color = active ? (activeColor ?? AppColors.secondary) : AppColors.gray400;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm, vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: active ? color.withValues(alpha: 0.12) : AppColors.widgetFill,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(
            color: active ? color.withValues(alpha: 0.4) : AppColors.gray700,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: AppIconSize.sm, color: color),
            const SizedBox(width: AppSpacing.xs),
            Text(label, style: AppTextStyles.caption.copyWith(color: color)),
            if (active) ...[
              const SizedBox(width: AppSpacing.xs),
              Icon(Icons.close, size: 12, color: color),
            ],
          ],
        ),
      ),
    );
  }
}
// ---------------------------------------------------------------------------

/// A stable list card template with natural height — no overflow, no scroll.
///
/// Structure:
///   ┌──────────────────────────────────┐
///   │ [48×48 icon]  [title]  [badge]  │
///   │                [type badge]      │
///   ├──────────────────────────────────┤
///   │            body / info rows       │  ← pushes chips down naturally
///   ├──────────────────────────────────┤
///   │            footer / chips        │
///   └──────────────────────────────────┘
///
/// The card Column has NO Flexible/Expanded children — it grows to fit
/// content. Use this inside a parent that allows natural heights
/// (ListView.builder without fixed extent, Wrap, etc.) — NEVER inside
/// a GridView that enforces fixed cell heights.
///
class ListableCard extends StatelessWidget {
  const ListableCard({
    super.key,
    required this.leadingIcon,
    required this.title,
    this.titleBadge,
    this.statusBadge,
    required this.body,
    this.footer,
    this.isSelected = false,
    this.onTap,
  });

  final Widget leadingIcon;
  final Widget title;
  final Widget? titleBadge;
  final Widget? statusBadge;
  final Widget body;
  final Widget? footer;
  final bool isSelected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        side: BorderSide(
          color: isSelected ? AppColors.primary : AppColors.border,
          width: isSelected ? 2 : 1,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.md),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header: icon + title + badges
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  leadingIcon,
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        title,
                        if (titleBadge != null) ...[
                          const SizedBox(height: AppSpacing.xs),
                          titleBadge!,
                        ],
                      ],
                    ),
                  ),
                  if (statusBadge != null) ...[
                    const SizedBox(width: AppSpacing.sm),
                    // Badge keeps natural width; Expanded title fills the rest,
                    // pinning the badge to the far right of the card.
                    Align(
                      alignment: Alignment.centerRight,
                      child: statusBadge!,
                    ),
                  ],
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              const Divider(height: 1, thickness: 1),
              const SizedBox(height: AppSpacing.md),
              // Body — stretches to card width, no scroll
              body,
              if (footer != null) ...[
                const SizedBox(height: AppSpacing.sm),
                footer!,
              ],
            ],
          ),
        ),
      ),
    );
  }
}
// End of Theme Kit
// =============================================================================
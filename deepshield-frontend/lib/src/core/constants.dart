import 'package:flutter/material.dart';
import 'theme.dart';

/// -------------------------------
/// APP DIMENSIONS & SPACING
/// -------------------------------
class AppSpacing {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;

  static const EdgeInsets screenPadding =
      EdgeInsets.symmetric(horizontal: md, vertical: lg);

  static const SizedBox gapXs = SizedBox(height: xs);
  static const SizedBox gapSm = SizedBox(height: sm);
  static const SizedBox gapMd = SizedBox(height: md);
  static const SizedBox gapLg = SizedBox(height: lg);
  static const SizedBox gapXl = SizedBox(height: xl);
}

/// -------------------------------
/// APP RADIUS & ELEVATION
/// -------------------------------
class AppRadii {
  static const double small = 8.0;
  static const double medium = 8.0;
  static const double large = 12.0;

  static const BorderRadius card =
      BorderRadius.all(Radius.circular(medium));
  static const BorderRadius button =
      BorderRadius.all(Radius.circular(medium));
}

/// -------------------------------
/// APP SHADOWS
/// -------------------------------
class AppShadows {
  static const BoxShadow soft = BoxShadow(
    color: Colors.black26,
    blurRadius: 6,
    offset: Offset(0, 2),
  );

  static const BoxShadow medium = BoxShadow(
    color: Colors.black38,
    blurRadius: 10,
    offset: Offset(0, 4),
  );

  static const BoxShadow glow = BoxShadow(
    color: AppColors.primary,
    blurRadius: 12,
    offset: Offset(0, 0),
  );
}

/// -------------------------------
/// APP ANIMATION DURATIONS
/// -------------------------------
class AppDurations {
  static const Duration fast = Duration(milliseconds: 150);
  static const Duration normal = Duration(milliseconds: 300);
  static const Duration slow = Duration(milliseconds: 600);
}

/// -------------------------------
/// APP STRINGS / LABELS
/// -------------------------------
class AppStrings {
  static const String appName = 'DeepShield';
  static const String tagline = 'Unmasking AI-generated deception';
  static const String slogan = 'Securing Tomorrow, Today';
  static const String version = 'v1.0.0';
}

/// -------------------------------
/// APP ICONS (can be extended later)
/// -------------------------------
class AppIcons {
  static const IconData upload = Icons.cloud_upload_rounded;
  static const IconData analyze = Icons.search_rounded;
  static const IconData report = Icons.picture_as_pdf_rounded;
  static const IconData verified = Icons.verified_rounded;
  static const IconData settings = Icons.settings_rounded;
  static const IconData history = Icons.history_rounded;
  static const IconData logout = Icons.logout_rounded;
}

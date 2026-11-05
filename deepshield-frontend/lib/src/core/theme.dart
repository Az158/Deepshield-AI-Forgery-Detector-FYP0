import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// -------------------------------
/// APP COLOR PALETTE
/// -------------------------------
class AppColors {
  static const Color primary = Color(0xFF1E6DE0); // DeepShield Blue
  static const Color secondary = Color(0xFF0C3C68); // Navy accent
  static const Color background = Color(0xFF0A0F1E); // App background (Dark)
  static const Color surface = Color(0xFF121826); // Card / Container color
  static const Color textPrimary = Color(0xFFE0E6F2); // Main text
  static const Color textSecondary = Color(0xFF9BA4B5); // Muted text
  static const Color success = Color(0xFF00C48C); // Upload/Check indicators
  static const Color warning = Color(0xFFFFC107); // Warnings
  static const Color error = Color(0xFFEB5757); // Fake/Manipulated color
  static const Color border = Color(0xFF1F2A3C); // Border & outline color
  static const Color cardOverlay = Color(0xFF101624);
  static const Color subtle = Color(0x331F2A3C);
}

/// -------------------------------
/// APP TYPOGRAPHY
/// -------------------------------
class AppTextStyles {
  static TextTheme textTheme = TextTheme(
    displayLarge: GoogleFonts.poppins(
      fontSize: 48,
      fontWeight: FontWeight.w700,
      letterSpacing: 0,
      height: 1.05,
    ),
    displayMedium: GoogleFonts.poppins(
      fontSize: 40,
      fontWeight: FontWeight.w700,
      letterSpacing: 0,
      height: 1.08,
    ),
    displaySmall: GoogleFonts.poppins(
      fontSize: 34,
      fontWeight: FontWeight.w700,
      letterSpacing: 0,
      height: 1.1,
    ),
    headlineLarge: GoogleFonts.poppins(
      fontSize: 30,
      fontWeight: FontWeight.w700,
      letterSpacing: 0,
      height: 1.12,
    ),
    headlineMedium: GoogleFonts.poppins(
      fontSize: 26,
      fontWeight: FontWeight.w700,
      letterSpacing: 0,
      height: 1.18,
    ),
    headlineSmall: GoogleFonts.poppins(
      fontSize: 22,
      fontWeight: FontWeight.w600,
      letterSpacing: 0,
      height: 1.2,
    ),
    titleLarge: GoogleFonts.poppins(
      fontSize: 20,
      fontWeight: FontWeight.w600,
      height: 1.24,
    ),
    titleMedium: GoogleFonts.poppins(
      fontSize: 18,
      fontWeight: FontWeight.w500,
      height: 1.3,
    ),
    titleSmall: GoogleFonts.poppins(
      fontSize: 16,
      fontWeight: FontWeight.w600,
      height: 1.32,
    ),
    bodyLarge: GoogleFonts.poppins(
      fontSize: 16,
      fontWeight: FontWeight.w400,
      height: 1.5,
    ),
    bodyMedium: GoogleFonts.poppins(
      fontSize: 14,
      fontWeight: FontWeight.w400,
      height: 1.46,
    ),
    bodySmall: GoogleFonts.poppins(
      fontSize: 12,
      fontWeight: FontWeight.w400,
      height: 1.4,
    ),
    labelLarge: GoogleFonts.poppins(
      fontSize: 15,
      fontWeight: FontWeight.w600,
      letterSpacing: 0,
    ),
    labelMedium: GoogleFonts.poppins(
      fontSize: 13,
      fontWeight: FontWeight.w600,
      letterSpacing: 0,
    ),
    labelSmall: GoogleFonts.poppins(
      fontSize: 11,
      fontWeight: FontWeight.w600,
      letterSpacing: 0,
    ),
  );
}

/// -------------------------------
/// THEME CONFIGURATION
/// -------------------------------
class AppTheme {
  static ThemeData darkTheme = ThemeData(
    brightness: Brightness.dark,
    primaryColor: AppColors.primary,
    scaffoldBackgroundColor: AppColors.background,
    textTheme: AppTextStyles.textTheme.apply(
      bodyColor: AppColors.textPrimary,
      displayColor: AppColors.textPrimary,
    ),
    iconTheme: const IconThemeData(color: AppColors.textPrimary),

    /// AppBar
    appBarTheme: AppBarTheme(
      backgroundColor: AppColors.background,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: AppTextStyles.textTheme.titleMedium,
      iconTheme: const IconThemeData(color: AppColors.textPrimary),
    ),

    /// Buttons
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 24),
        textStyle: AppTextStyles.textTheme.labelLarge,
      ),
    ),

    /// Text Fields
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      hintStyle: AppTextStyles.textTheme.bodyMedium?.copyWith(
        color: AppColors.textSecondary,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),

    /// Card / Surface
    cardColor: AppColors.surface,

    /// Bottom Navigation Bar
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.background,
      selectedItemColor: AppColors.primary,
      unselectedItemColor: AppColors.textSecondary,
      type: BottomNavigationBarType.fixed,
    ),

    /// Divider / Border
    dividerColor: AppColors.border,
  );
}

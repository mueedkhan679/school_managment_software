import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Brand palette for the School Portal app.
///
/// Deep Navy Blue is the primary identity colour (authority, academia) and
/// Emerald Green is the accent (growth, success). Gold is used sparingly for
/// highlights (tassel on the crest, premium badges).
class BrandColors {
  BrandColors._();

  // Deep Navy family
  static const Color navy = Color(0xFF0F1E3D);
  static const Color navy800 = Color(0xFF16294F);
  static const Color navy600 = Color(0xFF1E3A6E);
  static const Color navy400 = Color(0xFF2E4E8F);

  // Emerald family
  static const Color emerald = Color(0xFF10B981);
  static const Color emeraldDark = Color(0xFF059669);
  static const Color emeraldSoft = Color(0xFFD1FAE5);

  // Highlights
  static const Color gold = Color(0xFFF5B301);
  static const Color skyBlue = Color(0xFF3B82F6);
  static const Color coral = Color(0xFFEF4444);
  static const Color amber = Color(0xFFF59E0B);

  /// Signature brand gradient (navy → deep navy).
  static const LinearGradient navyGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [navy600, navy, Color(0xFF0A1730)],
  );

  /// Soft surface gradient for light screens (very subtle navy wash).
  static const LinearGradient lightBackdrop = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFFEEF2FB), Color(0xFFF8FAFD)],
  );

  /// Emerald accent gradient for primary buttons / success banners.
  static const LinearGradient emeraldGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [emerald, emeraldDark],
  );

  /// Rounded card shadow used across the app (soft, low-opacity navy).
  static List<BoxShadow> get cardShadow => [
        BoxShadow(
          color: navy.withValues(alpha: 0.08),
          blurRadius: 18,
          offset: const Offset(0, 8),
        ),
      ];

  /// Alias used by the shared widgets for the soft card shadow.
  static List<BoxShadow> get softShadow => cardShadow;
}

/// Alias so widgets can reference the palette as `SchoolPalette`.
typedef SchoolPalette = BrandColors;
/// The app-wide [ThemeData] factory. Material 3, Poppins typography,
/// rounded shapes and soft elevations everywhere.
class AppTheme {
  AppTheme._();

  static ThemeData light() => _build(Brightness.light);

  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final ColorScheme scheme = ColorScheme.fromSeed(
      seedColor: BrandColors.navy,
      brightness: brightness,
      primary: BrandColors.navy,
      secondary: BrandColors.emerald,
    );

    final bool isDark = brightness == Brightness.dark;
    final Color surface = isDark ? const Color(0xFF121A2E) : Colors.white;
    final Color scaffold = isDark ? const Color(0xFF0B1222) : const Color(0xFFF4F6FB);
    final Color outline = isDark ? const Color(0xFF33405C) : const Color(0xFFDFE5F0);

    final TextTheme textTheme = GoogleFonts.poppinsTextTheme(
      isDark ? ThemeData.dark().textTheme : ThemeData.light().textTheme,
    ).apply(bodyColor: isDark ? const Color(0xFFE6EAF2) : const Color(0xFF1C2540));

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme.copyWith(
        surface: surface,
        primaryContainer: isDark ? BrandColors.navy800 : const Color(0xFFE3EAF8),
        secondaryContainer: BrandColors.emeraldSoft,
      ),
      scaffoldBackgroundColor: scaffold,
      textTheme: textTheme,
      splashFactory: InkSparkle.splashFactory,
      appBarTheme: AppBarTheme(
        elevation: 0,
        centerTitle: false,
        backgroundColor: isDark ? const Color(0xFF121A2E) : Colors.white,
        foregroundColor: isDark ? Colors.white : BrandColors.navy,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: textTheme.titleLarge?.copyWith(
          fontWeight: FontWeight.w700,
          color: isDark ? Colors.white : BrandColors.navy,
        ),
        shape: const Border(bottom: BorderSide(color: Color(0x1410244A))),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(color: outline.withValues(alpha: 0.7)),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        titleTextStyle: textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? const Color(0xFF1A2440) : const Color(0xFFF7F9FD),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: outline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: outline.withValues(alpha: 0.8)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: BrandColors.emerald, width: 1.6),
        ),
        labelStyle: textTheme.bodyMedium,
        hintStyle: textTheme.bodyMedium?.copyWith(color: outline),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: BrandColors.emeraldDark,
          foregroundColor: Colors.white,
          minimumSize: const Size(72, 48),
          textStyle: textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ).copyWith(
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) {
              return BrandColors.emerald.withValues(alpha: 0.4);
            }
            return BrandColors.emeraldDark;
          }),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: BrandColors.navy,
          foregroundColor: Colors.white,
          minimumSize: const Size(72, 48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: BrandColors.emeraldDark,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: isDark ? const Color(0xFF1A2440) : const Color(0xFFF0F3FA),
        selectedColor: BrandColors.emeraldSoft,
        side: BorderSide(color: outline.withValues(alpha: 0.8)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        labelStyle: textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        indicatorColor: BrandColors.emeraldSoft,
        height: 68,
        elevation: 0,
        labelTextStyle: WidgetStatePropertyAll(
          textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: isDark ? const Color(0xFF1A2440) : BrandColors.navy,
        contentTextStyle: textTheme.bodyMedium?.copyWith(color: Colors.white),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      dividerTheme: DividerThemeData(color: outline.withValues(alpha: 0.6), space: 1),
    );
  }
}


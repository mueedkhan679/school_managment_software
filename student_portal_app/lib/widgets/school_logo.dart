import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// ===============================================================
/// SCHOOL LOGO
/// ===============================================================
///
/// Global branded school logo widget.
///
/// Resolution order:
/// 1. Network logo — dynamic school branding
/// 2. Local asset — bundled school logo
/// 3. Premium vector fallback — always available
///
/// Existing usage remains compatible:
///
/// SchoolLogo()
///
/// SchoolLogo(
///   size: 80,
/// )
///
/// SchoolLogo(
///   networkUrl: 'https://example.com/logo.png',
/// )
class SchoolLogo extends StatelessWidget {
  const SchoolLogo({
    super.key,
    this.size = 64,
    this.networkUrl,
    this.assetPath = defaultAssetPath,
  });

  static const String defaultAssetPath = 'assets/images/school_logo.png';

  final double size;
  final String? networkUrl;
  final String? assetPath;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final url = networkUrl;

    // =============================================================
    // NETWORK LOGO
    // =============================================================

    if (url != null && url.trim().isNotEmpty) {
      return SizedBox(
        width: size,
        height: size,
        child: _LogoFrame(
          size: size,
          child: Image.network(
            url,
            fit: BoxFit.contain,
            loadingBuilder: (
              context,
              child,
              loadingProgress,
            ) {
              if (loadingProgress == null) {
                return child;
              }

              return _LoadingLogo(
                size: size,
                color: colorScheme.primary,
              );
            },
            errorBuilder: (
              context,
              error,
              stackTrace,
            ) {
              return _VectorBadge(
                size: size,
              );
            },
          ),
        ),
      );
    }

    // =============================================================
    // LOCAL ASSET LOGO
    // =============================================================

    final asset = assetPath;

    if (asset != null && asset.trim().isNotEmpty) {
      return SizedBox(
        width: size,
        height: size,
        child: _LogoFrame(
          size: size,
          child: Image.asset(
            asset,
            fit: BoxFit.contain,
            errorBuilder: (
              context,
              error,
              stackTrace,
            ) {
              return _VectorBadge(
                size: size,
              );
            },
          ),
        ),
      );
    }

    // =============================================================
    // VECTOR FALLBACK
    // =============================================================

    return SizedBox(
      width: size,
      height: size,
      child: _LogoFrame(
        size: size,
        child: _VectorBadge(
          size: size,
        ),
      ),
    );
  }
}

/// ===============================================================
/// LOGO FRAME
/// ===============================================================
///
/// Provides a clean premium surface around the school logo.

class _LogoFrame extends StatelessWidget {
  const _LogoFrame({
    required this.size,
    required this.child,
  });

  final double size;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final isDark = theme.brightness == Brightness.dark;

    final radius = (size * 0.25).clamp(8.0, 24.0);

    return Container(
      width: size,
      height: size,
      padding: size >= 45
          ? EdgeInsets.all(
              (size * 0.075).clamp(
                3.0,
                7.0,
              ),
            )
          : EdgeInsets.all(
              (size * 0.05).clamp(
                2.0,
                4.0,
              ),
            ),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isDark
              ? [
                  const Color(0xFF1B2638),
                  const Color(0xFF111827),
                ]
              : [
                  Colors.white,
                  const Color(0xFFF5F8FC),
                ],
        ),
        border: Border.all(
          color: colorScheme.outline.withValues(
            alpha: isDark ? 0.18 : 0.10,
          ),
        ),
        boxShadow: [
          BoxShadow(
            color: colorScheme.primary.withValues(
              alpha: isDark ? 0.12 : 0.07,
            ),
            blurRadius: (size * 0.28).clamp(
              8.0,
              20.0,
            ),
            offset: Offset(
              0,
              (size * 0.08).clamp(
                2.0,
                6.0,
              ),
            ),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(
          (radius * 0.72).clamp(
            5.0,
            18.0,
          ),
        ),
        child: child,
      ),
    );
  }
}

/// ===============================================================
/// VECTOR FALLBACK BADGE
/// ===============================================================
///
/// Used whenever no logo asset is available or an image fails.
/// This means the app always has a valid school brand mark.

class _VectorBadge extends StatelessWidget {
  const _VectorBadge({
    required this.size,
  });

  final double size;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final isDark = theme.brightness == Brightness.dark;

    final emerald = SchoolPalette.emerald;

    final navy = SchoolPalette.navy;

    final borderWidth = (size * 0.045).clamp(
      1.4,
      4.5,
    );

    return Container(
      alignment: Alignment.center,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isDark
              ? [
                  const Color(0xFF24344B),
                  const Color(0xFF162235),
                ]
              : [
                  Colors.white,
                  const Color(0xFFEAF2FF),
                ],
        ),
        borderRadius: BorderRadius.circular(
          (size * 0.24).clamp(
            7.0,
            22.0,
          ),
        ),
        border: Border.all(
          color: emerald.withValues(
            alpha: 0.80,
          ),
          width: borderWidth,
        ),
        boxShadow: [
          BoxShadow(
            color: emerald.withValues(
              alpha: isDark ? 0.20 : 0.16,
            ),
            blurRadius: (size * 0.28).clamp(
              8.0,
              20.0,
            ),
            offset: Offset(
              0,
              (size * 0.08).clamp(
                2.0,
                6.0,
              ),
            ),
          ),
        ],
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // -------------------------------------------------------
          // Soft inner glow
          // -------------------------------------------------------

          Container(
            width: size * 0.72,
            height: size * 0.72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  emerald.withValues(
                    alpha: isDark ? 0.14 : 0.08,
                  ),
                  Colors.transparent,
                ],
              ),
            ),
          ),

          // -------------------------------------------------------
          // School Icon
          // -------------------------------------------------------

          Icon(
            Icons.school_rounded,
            size: size * 0.52,
            color: isDark ? Colors.white : navy,
          ),

          // -------------------------------------------------------
          // Small brand accent
          // -------------------------------------------------------

          if (size >= 55)
            Positioned(
              right: size * 0.15,
              bottom: size * 0.13,
              child: Container(
                width: size * 0.13,
                height: size * 0.13,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: emerald,
                  border: Border.all(
                    color: isDark
                        ? const Color(
                            0xFF1B2638,
                          )
                        : Colors.white,
                    width: 1.5,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// ===============================================================
/// LOGO LOADING STATE
/// ===============================================================

class _LoadingLogo extends StatelessWidget {
  const _LoadingLogo({
    required this.size,
    required this.color,
  });

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SizedBox(
        width: size * 0.30,
        height: size * 0.30,
        child: CircularProgressIndicator(
          strokeWidth: (size * 0.035).clamp(
            1.5,
            3.0,
          ),
          valueColor: AlwaysStoppedAnimation<Color>(
            color,
          ),
        ),
      ),
    );
  }
}

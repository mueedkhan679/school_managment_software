import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../services/api_service.dart';
import 'modern_loader.dart';

/// ===============================================================
/// STUDENT AVATAR
/// ===============================================================
///
/// Premium circular student profile image.
///
/// Resolution:
/// 1. Absolute HTTP/HTTPS URL
/// 2. Backend-relative /media/ or /static/ path
/// 3. Cached network image
/// 4. Animated loading state
/// 5. Elegant person placeholder on failure
///
/// Existing constructor/API remains compatible.
class StudentAvatar extends StatelessWidget {
  const StudentAvatar({
    super.key,
    required this.imageUrl,
    this.radius = 36,
    this.backgroundColor,
    this.iconColor,
    this.iconSize = 40,
    this.innerPadding = 0,
  });

  /// Raw photo URL returned by the API.
  final String? imageUrl;

  /// Total outer avatar radius.
  final double radius;

  final Color? backgroundColor;

  final Color? iconColor;

  final double iconSize;

  /// Space between the decorative outer ring and photo.
  final double innerPadding;

  /// =============================================================
  /// ABSOLUTE URL RESOLVER
  /// =============================================================
  ///
  /// Converts backend-relative media paths into absolute URLs.
  static String? absoluteUrl(String? raw) {
    if (raw == null) return null;

    final url = raw.trim();

    if (url.isEmpty) return null;

    // Already absolute.
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }

    // /media/... or /static/...
    if (url.startsWith('/media/') || url.startsWith('/static/')) {
      return '${ApiService.baseUrl}$url';
    }

    // media/... or static/...
    if (url.startsWith('media/') || url.startsWith('static/')) {
      return '${ApiService.baseUrl}/$url';
    }

    // Leave unknown URLs untouched.
    return url;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final isDark = theme.brightness == Brightness.dark;

    final effectiveBackground =
        backgroundColor ?? colorScheme.surfaceContainerHighest;

    final effectiveIconColor = iconColor ?? colorScheme.onSurfaceVariant;

    final photoRadius = (radius - innerPadding).clamp(1.0, radius);

    final resolved = absoluteUrl(imageUrl);

    final avatar = _AvatarContent(
      radius: photoRadius,
      imageUrl: resolved,
      backgroundColor: effectiveBackground,
      iconColor: effectiveIconColor,
      iconSize: iconSize,
    );

    // ===========================================================
    // DECORATIVE OUTER RING
    // ===========================================================

    if (innerPadding > 0) {
      return Container(
        width: radius * 2,
        height: radius * 2,
        padding: EdgeInsets.all(
          innerPadding,
        ),
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              colorScheme.primary.withValues(
                alpha: isDark ? 0.65 : 0.85,
              ),
              colorScheme.secondary.withValues(
                alpha: isDark ? 0.45 : 0.65,
              ),
            ],
          ),
          boxShadow: [
            BoxShadow(
              color: colorScheme.primary.withValues(
                alpha: isDark ? 0.18 : 0.12,
              ),
              blurRadius: 16,
              offset: const Offset(
                0,
                5,
              ),
            ),
          ],
        ),
        child: avatar,
      );
    }

    return avatar;
  }
}

/// ===============================================================
/// AVATAR CONTENT
/// ===============================================================

class _AvatarContent extends StatelessWidget {
  const _AvatarContent({
    required this.radius,
    required this.imageUrl,
    required this.backgroundColor,
    required this.iconColor,
    required this.iconSize,
  });

  final double radius;
  final String? imageUrl;
  final Color backgroundColor;
  final Color iconColor;
  final double iconSize;

  @override
  Widget build(BuildContext context) {
    final diameter = radius * 2;

    // ===========================================================
    // NO IMAGE
    // ===========================================================

    if (imageUrl == null) {
      return _PlaceholderAvatar(
        radius: radius,
        backgroundColor: backgroundColor,
        iconColor: iconColor,
        iconSize: iconSize,
      );
    }

    // ===========================================================
    // NETWORK IMAGE
    // ===========================================================

    return Container(
      width: diameter,
      height: diameter,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: backgroundColor,
        border: Border.all(
          color: Colors.white.withValues(
            alpha: 0.55,
          ),
          width: radius >= 30 ? 1.5 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(
              alpha: 0.08,
            ),
            blurRadius: 10,
            offset: const Offset(
              0,
              4,
            ),
          ),
        ],
      ),
      child: ClipOval(
        child: CachedNetworkImage(
          imageUrl: imageUrl!,

          width: diameter,
          height: diameter,

          fit: BoxFit.cover,

          fadeInDuration: const Duration(
            milliseconds: 300,
          ),

          fadeOutDuration: const Duration(
            milliseconds: 150,
          ),

          // -----------------------------------------------------
          // Loading
          // -----------------------------------------------------

          placeholder: (
            context,
            url,
          ) {
            return _AvatarLoading(
              color: Theme.of(context).colorScheme.primary,
              radius: radius,
            );
          },

          // -----------------------------------------------------
          // Error / 404
          // -----------------------------------------------------

          errorWidget: (
            context,
            url,
            error,
          ) {
            return _PlaceholderAvatar(
              radius: radius,
              backgroundColor: backgroundColor,
              iconColor: iconColor,
              iconSize: iconSize,
            );
          },
        ),
      ),
    );
  }
}

/// ===============================================================
/// PLACEHOLDER AVATAR
/// ===============================================================

class _PlaceholderAvatar extends StatelessWidget {
  const _PlaceholderAvatar({
    required this.radius,
    required this.backgroundColor,
    required this.iconColor,
    required this.iconSize,
  });

  final double radius;
  final Color backgroundColor;
  final Color iconColor;
  final double iconSize;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final diameter = radius * 2;

    return Container(
      width: diameter,
      height: diameter,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            backgroundColor,
            colorScheme.surfaceContainer,
          ],
        ),
        border: Border.all(
          color: colorScheme.outline.withValues(
            alpha: 0.10,
          ),
          width: 1,
        ),
      ),
      child: Center(
        child: Container(
          width: radius * 1.35,
          height: radius * 1.35,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: colorScheme.primary.withValues(
              alpha: 0.07,
            ),
          ),
          child: Icon(
            Icons.person_rounded,
            size: iconSize.clamp(
              18,
              radius * 1.15,
            ),
            color: iconColor,
          ),
        ),
      ),
    );
  }
}

/// ===============================================================
/// AVATAR LOADING
/// ===============================================================

class _AvatarLoading extends StatelessWidget {
  const _AvatarLoading({
    required this.color,
    required this.radius,
  });

  final Color color;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            color.withValues(
              alpha: 0.10,
            ),
            color.withValues(
              alpha: 0.035,
            ),
          ],
        ),
      ),
      child: Center(
        child: ButtonSpinner(
          size: (radius * 0.55).clamp(12.0, 24.0),
          color: color,
        ),
      ),
    );
  }
}

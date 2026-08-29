import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../services/api_service.dart';
import 'modern_loader.dart';

/// Circular avatar that loads the student's profile photo and degrades
/// gracefully:
///
///  * missing / empty URL                → person placeholder icon
///  * backend-relative path (`/media/…`) → absolutised against the API host
///  * network or 404 failure             → person placeholder icon
///  * while loading                      → subtle spinner inside the circle
///
/// Photos are cached on disk by `cached_network_image`, so avatars render
/// instantly on subsequent launches.
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

  /// Raw photo URL from the API. May be null/empty or backend-relative.
  final String? imageUrl;

  final double radius;
  final Color? backgroundColor;
  final Color? iconColor;
  final double iconSize;

  /// Gap between the outer decorative ring and the photo itself.
  final double innerPadding;

  /// Ensures [raw] is an absolute, loadable URL.
  ///
  /// The backend serialises `photo_url` as `/media/...`, which the app cannot
  /// load on its own. Backend-relative `/media/` and `/static/` paths are
  /// prefixed with the API host; absolute http(s) URLs are returned unchanged.
  static String? absoluteUrl(String? raw) {
    if (raw == null) return null;
    final url = raw.trim();
    if (url.isEmpty) return null;
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    if (url.startsWith('/media/') || url.startsWith('/static/')) {
      return '${ApiService.baseUrl}$url';
    }
    if (url.startsWith('media/') || url.startsWith('static/')) {
      return '${ApiService.baseUrl}/$url';
    }
    return url;
  }

  @override
  Widget build(BuildContext context) {
    final Color effectiveBackground = backgroundColor ??
        Theme.of(context).colorScheme.surfaceContainerHighest;
    final Color effectiveIconColor =
        iconColor ?? Theme.of(context).colorScheme.onSurfaceVariant;

    final double photoRadius = radius - innerPadding;
    final String? resolved = absoluteUrl(imageUrl);

    final Widget photoCircle = CircleAvatar(
      radius: photoRadius,
      backgroundColor: effectiveBackground,
      child: resolved == null
          ? Icon(
              Icons.person_rounded,
              size: iconSize,
              color: effectiveIconColor,
            )
          : ClipOval(
              child: CachedNetworkImage(
                imageUrl: resolved,
                width: photoRadius * 2,
                height: photoRadius * 2,
                fit: BoxFit.cover,
                fadeInDuration: const Duration(milliseconds: 200),
                                placeholder: (_, __) => Center(
                  child: ButtonSpinner(
                    size: iconSize * 0.55,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ),
                errorWidget: (_, __, ___) => Icon(
                  Icons.person_rounded,
                  size: iconSize,
                  color: effectiveIconColor,
                ),
              ),
            ),
    );

    if (innerPadding > 0) {
      return CircleAvatar(
        radius: radius,
        backgroundColor: effectiveBackground,
        child: photoCircle,
      );
    }
    return photoCircle;
  }
}

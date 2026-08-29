import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// The school's brand mark.
///
/// Resolution order:
/// 1. [networkUrl] — when provided, the logo is loaded dynamically from the
///    network (lets the school rebrand without shipping a new build).
/// 2. [assetPath] — a bundled image. Drop `assets/images/school_logo.png`
///    into the project to override the vector badge with the real logo.
/// 3. A crisp built-in vector badge (gradient rounded square + graduation
///    cap) used as the graceful fallback whenever no image can be loaded.
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
    final url = networkUrl;
    if (url != null && url.isNotEmpty) {
      return SizedBox(
        width: size,
        height: size,
        child: Image.network(
          url,
          fit: BoxFit.contain,
          errorBuilder: (_, __, ___) => _vectorBadge(),
        ),
      );
    }
    return SizedBox(
      width: size,
      height: size,
      child: Image.asset(
        assetPath!,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) => _vectorBadge(),
      ),
    );
  }

  /// Built-in badge: emerald-ringed rounded square with a graduation cap.
  Widget _vectorBadge() {
    return Container(
      alignment: Alignment.center,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Colors.white, Color(0xFFE8F0FE)],
        ),
        borderRadius: BorderRadius.circular(size * 0.28),
        border: Border.all(
          color: SchoolPalette.emerald.withValues(alpha: 0.85),
          width: (size * 0.045).clamp(1.5, 5.0),
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x3310B981),
            blurRadius: 18,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Icon(
        Icons.school_rounded,
        size: size * 0.54,
        color: SchoolPalette.navy,
      ),
    );
  }
}

import 'package:flutter/material.dart';

/// Circular avatar that loads the student's profile photo from [imageUrl] and
/// degrades gracefully:
///
///  * missing / empty URL      → person placeholder icon
///  * network or 404 failure   → person placeholder icon (via
///                               `onBackgroundImageError`)
///  * while loading            → background colour shows through
///
/// An optional [innerPadding] reproduces the ID-card "white ring" style by
/// drawing a solid outer circle behind the photo circle.
class StudentAvatar extends StatefulWidget {
  const StudentAvatar({
    super.key,
    required this.imageUrl,
    this.radius = 36,
    this.backgroundColor,
    this.iconColor,
    this.iconSize = 40,
    this.innerPadding = 0,
  });

  /// Absolute (or backend-normalised) photo URL. May be null/empty.
  final String? imageUrl;

  final double radius;
  final Color? backgroundColor;
  final Color? iconColor;
  final double iconSize;

  /// Gap between the outer decorative ring and the photo itself.
  final double innerPadding;

  @override
  State<StudentAvatar> createState() => _StudentAvatarState();
}

class _StudentAvatarState extends State<StudentAvatar> {
  bool _loadFailed = false;

  @override
  void didUpdateWidget(covariant StudentAvatar oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Allow a retry when the profile (and its photo URL) changes.
    if (oldWidget.imageUrl != widget.imageUrl && _loadFailed) {
      _loadFailed = false;
    }
  }

  bool get _hasUsableUrl =>
      !_loadFailed &&
      widget.imageUrl != null &&
      widget.imageUrl!.trim().isNotEmpty;

  @override
  Widget build(BuildContext context) {
    final Color effectiveBackground =
        widget.backgroundColor ?? Theme.of(context).colorScheme.surfaceContainerHighest;

    final Widget photoCircle = CircleAvatar(
      radius: widget.radius - widget.innerPadding,
      backgroundColor: effectiveBackground,
      backgroundImage:
          _hasUsableUrl ? NetworkImage(widget.imageUrl!.trim()) : null,
      onBackgroundImageError: _hasUsableUrl
          ? (Object exception, StackTrace? stackTrace) {
              // NetworkImage failed (offline, 404, bad host...) → fall back
              // to the placeholder icon.
              if (mounted && !_loadFailed) {
                setState(() => _loadFailed = true);
              }
            }
          : null,
      child: _hasUsableUrl
          ? null
          : Icon(
              Icons.person_rounded,
              size: widget.iconSize,
              color: widget.iconColor ?? Theme.of(context).colorScheme.onSurfaceVariant,
            ),
    );

    if (widget.innerPadding > 0) {
      return CircleAvatar(
        radius: widget.radius,
        backgroundColor: effectiveBackground,
        child: photoCircle,
      );
    }
    return photoCircle;
  }
}
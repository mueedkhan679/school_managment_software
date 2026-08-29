import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';

/// Global branded loading indicator (replaces plain
/// [CircularProgressIndicator] instances app-wide).
class ModernLoader extends StatelessWidget {
  const ModernLoader({
    super.key,
    this.message,
    this.size = 46,
    this.color,
  });

  final String? message;
  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SpinKitFadingCircle(
            color: color ?? theme.colorScheme.secondary,
            size: size,
          ),
          if (message != null) ...[
            const SizedBox(height: 16),
            Text(
              message!,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    ).animate().fadeIn(duration: 250.ms);
  }
}

/// Compact white spinner for use inside filled buttons and dialogs.
class ButtonSpinner extends StatelessWidget {
  const ButtonSpinner({
    super.key,
    this.size = 20,
    this.color = Colors.white,
  });

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: SpinKitFadingCircle(color: color, size: size),
    );
  }
}

/// Small bouncing-dots loader for inline rows (filters, chips, footers).
class InlineDotsLoader extends StatelessWidget {
  const InlineDotsLoader({
    super.key,
    this.size = 14,
    this.color,
    this.alignment = MainAxisAlignment.start,
  });

  final double size;
  final Color? color;
  final MainAxisAlignment alignment;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: alignment,
      children: [
        SpinKitThreeBounce(
          color: color ?? Theme.of(context).colorScheme.secondary,
          size: size,
        ),
      ],
    );
  }
}

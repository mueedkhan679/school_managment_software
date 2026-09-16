import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';

/// ===============================================================
/// MODERN LOADER
/// ===============================================================
///
/// Global branded loading indicator.
///
/// Features:
/// • Premium animated loader
/// • Optional loading message
/// • Theme-aware colors
/// • Soft glow effect
/// • Smooth entrance animation
/// • Works in light and dark mode
///
/// Usage:
/// ModernLoader()
///
/// ModernLoader(
///   message: 'Loading student data...',
/// )
///
/// ModernLoader(
///   size: 54,
///   color: Colors.blue,
/// )
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
    final colorScheme = theme.colorScheme;

    final loaderColor = color ?? colorScheme.primary;

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // -------------------------------------------------------
          // Loader Container
          // -------------------------------------------------------

          Container(
            width: size + 30,
            height: size + 30,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: loaderColor.withValues(
                alpha: 0.07,
              ),
              border: Border.all(
                color: loaderColor.withValues(
                  alpha: 0.10,
                ),
              ),
              boxShadow: [
                BoxShadow(
                  color: loaderColor.withValues(
                    alpha: 0.12,
                  ),
                  blurRadius: 22,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: SpinKitFadingCircle(
              color: loaderColor,
              size: size,
            ),
          )
              .animate(
                onPlay: (controller) => controller.repeat(),
              )
              .scale(
                begin: const Offset(
                  0.92,
                  0.92,
                ),
                end: const Offset(
                  1.04,
                  1.04,
                ),
                duration: 1100.ms,
                curve: Curves.easeInOut,
              ),

          // -------------------------------------------------------
          // Loading Message
          // -------------------------------------------------------

          if (message != null && message!.trim().isNotEmpty) ...[
            const SizedBox(height: 18),
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: 28,
              ),
              child: Text(
                message!,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                  letterSpacing: 0.1,
                ),
              ),
            ),
          ],
        ],
      ),
    )
        .animate()
        .fadeIn(
          duration: 300.ms,
          curve: Curves.easeOut,
        )
        .slideY(
          begin: 0.06,
          end: 0,
          duration: 350.ms,
          curve: Curves.easeOutCubic,
        );
  }
}

/// ===============================================================
/// BUTTON SPINNER
/// ===============================================================
///
/// Compact premium white spinner for:
/// • Filled buttons
/// • Login buttons
/// • Submit buttons
/// • Dialog actions
///
/// Example:
///
/// ElevatedButton(
///   onPressed: loading ? null : submit,
///   child: loading
///       ? const ButtonSpinner()
///       : const Text('Submit'),
/// )
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
      child: SpinKitFadingCircle(
        color: color,
        size: size,
      ),
    )
        .animate()
        .fadeIn(
          duration: 180.ms,
        )
        .scale(
          begin: const Offset(
            0.75,
            0.75,
          ),
          end: const Offset(
            1,
            1,
          ),
          duration: 220.ms,
          curve: Curves.easeOutBack,
        );
  }
}

/// ===============================================================
/// INLINE DOTS LOADER
/// ===============================================================
///
/// Small animated three-dot loader.
///
/// Useful for:
/// • Filters
/// • Chips
/// • Small rows
/// • Refresh states
/// • Footer loading
/// • Inline API requests
///
/// Example:
///
/// InlineDotsLoader()
///
/// InlineDotsLoader(
///   size: 16,
///   color: Colors.blue,
/// )
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
    final theme = Theme.of(context);

    final loaderColor = color ?? theme.colorScheme.primary;

    return Row(
      mainAxisAlignment: alignment,
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: 8,
            vertical: 5,
          ),
          decoration: BoxDecoration(
            color: loaderColor.withValues(
              alpha: 0.07,
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: loaderColor.withValues(
                alpha: 0.08,
              ),
            ),
          ),
          child: SpinKitThreeBounce(
            color: loaderColor,
            size: size,
          ),
        ),
      ],
    ).animate().fadeIn(
          duration: 200.ms,
        );
  }
}

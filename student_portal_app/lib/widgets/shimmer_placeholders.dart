import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

import '../theme/app_theme.dart';

/// ===============================================================
/// SHIMMER PLACEHOLDER
/// ===============================================================
///
/// Reusable animated skeleton block used throughout the app.
///
/// Example:
/// ShimmerPlaceholder(
///   width: 120,
///   height: 14,
/// )
class ShimmerPlaceholder extends StatelessWidget {
  const ShimmerPlaceholder({
    super.key,
    this.width = double.infinity,
    this.height = 14,
    this.radius = 8,
  });

  final double? width;
  final double height;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final baseColor =
        isDark ? const Color(0xFF1A2740) : const Color(0xFFE5EBF4);

    final highlightColor =
        isDark ? const Color(0xFF304467) : const Color(0xFFF9FBFF);

    return Shimmer.fromColors(
      baseColor: baseColor,
      highlightColor: highlightColor,
      period: const Duration(
        milliseconds: 1250,
      ),
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1C2A40) : Colors.white,
          borderRadius: BorderRadius.circular(radius),
        ),
      ),
    );
  }
}

/// ===============================================================
/// SKELETON LIST
/// ===============================================================
///
/// Premium animated skeleton list for:
/// • Student rosters
/// • Fee schedules
/// • Payment history
/// • Attendance records
/// • Notifications
///
/// Existing parameters are preserved.
class SkeletonList extends StatelessWidget {
  const SkeletonList({
    super.key,
    this.itemCount = 6,
    this.shrinkWrap = false,
    this.padding = const EdgeInsets.symmetric(
      horizontal: 16,
      vertical: 8,
    ),
    this.horizontalPadding = 16,
  });

  final int itemCount;
  final bool shrinkWrap;
  final EdgeInsetsGeometry padding;
  final double horizontalPadding;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return ListView.separated(
      shrinkWrap: shrinkWrap,
      padding: padding,
      physics: shrinkWrap ? const NeverScrollableScrollPhysics() : null,
      itemCount: itemCount,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        return _SkeletonListItem(
          colorScheme: colorScheme,
          index: index,
        );
      },
    );
  }
}

/// ===============================================================
/// SKELETON LIST ITEM
/// ===============================================================

class _SkeletonListItem extends StatelessWidget {
  const _SkeletonListItem({
    required this.colorScheme,
    required this.index,
  });

  final ColorScheme colorScheme;
  final int index;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: colorScheme.outline.withValues(
            alpha: isDark ? 0.10 : 0.07,
          ),
        ),
        boxShadow: [
          ...SchoolPalette.softShadow,
        ],
      ),
      child: Row(
        children: [
          // -------------------------------------------------------
          // Avatar
          // -------------------------------------------------------

          const ShimmerPlaceholder(
            width: 48,
            height: 48,
            radius: 16,
          ),

          const SizedBox(width: 14),

          // -------------------------------------------------------
          // Main content
          // -------------------------------------------------------

          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ShimmerPlaceholder(
                  width: double.infinity,
                  height: 13,
                  radius: 7,
                ),
                SizedBox(height: 9),
                ShimmerPlaceholder(
                  width: 135,
                  height: 10,
                  radius: 6,
                ),
                SizedBox(height: 7),
                ShimmerPlaceholder(
                  width: 90,
                  height: 8,
                  radius: 5,
                ),
              ],
            ),
          ),

          const SizedBox(width: 12),

          // -------------------------------------------------------
          // Status badge
          // -------------------------------------------------------

          const ShimmerPlaceholder(
            width: 58,
            height: 24,
            radius: 12,
          ),
        ],
      ),
    );
  }
}

/// ===============================================================
/// SUMMARY CARDS SKELETON
/// ===============================================================
///
/// Skeleton layout for dashboard summary cards.
class SummaryCardsSkeleton extends StatelessWidget {
  const SummaryCardsSkeleton({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 6,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: _SummarySkeletonCard(),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _SummarySkeletonCard(
              compact: true,
            ),
          ),
        ],
      ),
    );
  }
}

/// ===============================================================
/// SUMMARY SKELETON CARD
/// ===============================================================

class _SummarySkeletonCard extends StatelessWidget {
  const _SummarySkeletonCard({
    this.compact = false,
  });

  final bool compact;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      height: 140,
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: colorScheme.outline.withValues(
            alpha: isDark ? 0.10 : 0.07,
          ),
        ),
        boxShadow: [
          ...SchoolPalette.softShadow,
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Small title
          ShimmerPlaceholder(
            width: compact ? 72 : 88,
            height: 11,
            radius: 6,
          ),

          const Spacer(),

          // Main number
          ShimmerPlaceholder(
            width: compact ? 105 : 125,
            height: 27,
            radius: 8,
          ),

          const SizedBox(height: 12),

          // Bottom text
          ShimmerPlaceholder(
            width: compact ? 62 : 76,
            height: 10,
            radius: 6,
          ),
        ],
      ),
    );
  }
}

/// ===============================================================
/// HERO BANNER SKELETON
/// ===============================================================
///
/// Skeleton for dashboard welcome/hero sections.
class HeroBannerSkeleton extends StatelessWidget {
  const HeroBannerSkeleton({
    super.key,
    this.height = 140,
  });

  final double height;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      height: height,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: colorScheme.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: colorScheme.outline.withValues(
            alpha: isDark ? 0.10 : 0.07,
          ),
        ),
        boxShadow: [
          ...SchoolPalette.softShadow,
        ],
      ),
      child: Stack(
        children: [
          // -------------------------------------------------------
          // Content skeleton
          // -------------------------------------------------------

          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ShimmerPlaceholder(
                width: 105,
                height: 11,
                radius: 6,
              ),
              SizedBox(height: 14),
              ShimmerPlaceholder(
                width: 205,
                height: 21,
                radius: 8,
              ),
              SizedBox(height: 14),
              ShimmerPlaceholder(
                width: 170,
                height: 11,
                radius: 6,
              ),
              SizedBox(height: 10),
              ShimmerPlaceholder(
                width: 125,
                height: 9,
                radius: 5,
              ),
            ],
          ),

          // -------------------------------------------------------
          // Decorative right-side circle
          // -------------------------------------------------------

          Positioned(
            right: 0,
            top: 2,
            child: ShimmerPlaceholder(
              width: 58,
              height: 58,
              radius: 29,
            ),
          ),
        ],
      ),
    );
  }
}

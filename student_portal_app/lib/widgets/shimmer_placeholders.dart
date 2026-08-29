import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

import '../theme/app_theme.dart';

/// A single shimmering rectangle used to compose skeleton layouts.
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Shimmer.fromColors(
      baseColor: isDark ? const Color(0xFF1C2A47) : const Color(0xFFE3EAF5),
      highlightColor:
          isDark ? const Color(0xFF283A60) : const Color(0xFFF8FBFF),
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(radius),
        ),
      ),
    );
  }
}

/// Animated skeleton list for student rosters, fee schedules and history
/// ledgers while data is being fetched.
class SkeletonList extends StatelessWidget {
  const SkeletonList({
    super.key,
    this.itemCount = 6,
    this.shrinkWrap = false,
    this.padding = const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
    this.horizontalPadding = 16,
  });

  final int itemCount;
  final bool shrinkWrap;
  final EdgeInsetsGeometry padding;
  final double horizontalPadding;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      shrinkWrap: shrinkWrap,
      padding: padding,
      physics:
          shrinkWrap ? const NeverScrollableScrollPhysics() : null,
      itemCount: itemCount,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, __) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(16),
          boxShadow: SchoolPalette.softShadow,
        ),
        child: const Row(
          children: [
            ShimmerPlaceholder(width: 44, height: 44, radius: 22),
            SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ShimmerPlaceholder(
                    width: double.infinity,
                    height: 13,
                  ),
                  SizedBox(height: 8),
                  ShimmerPlaceholder(width: 130, height: 10, radius: 6),
                ],
              ),
            ),
            SizedBox(width: 12),
            ShimmerPlaceholder(width: 54, height: 22, radius: 11),
          ],
        ),
      ),
    );
  }
}

/// Skeleton for the dashboard's attendance/fee summary card row.
class SummaryCardsSkeleton extends StatelessWidget {
  const SummaryCardsSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    Widget card() => Container(
          height: 132,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(18),
            boxShadow: SchoolPalette.softShadow,
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ShimmerPlaceholder(width: 84, height: 12, radius: 6),
              Spacer(),
              ShimmerPlaceholder(width: 130, height: 24, radius: 8),
              SizedBox(height: 12),
              ShimmerPlaceholder(width: 70, height: 11, radius: 6),
            ],
          ),
        );

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          Expanded(child: card()),
          const SizedBox(width: 14),
          Expanded(child: card()),
        ],
      ),
    );
  }
}

/// Skeleton for a highlighted welcome/hero banner.
class HeroBannerSkeleton extends StatelessWidget {
  const HeroBannerSkeleton({super.key, this.height = 140});

  final double height;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(22),
        boxShadow: SchoolPalette.softShadow,
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ShimmerPlaceholder(width: 110, height: 12, radius: 6),
          SizedBox(height: 14),
          ShimmerPlaceholder(width: 190, height: 20, radius: 8),
          SizedBox(height: 14),
          ShimmerPlaceholder(width: 160, height: 12, radius: 6),
        ],
      ),
    );
  }
}

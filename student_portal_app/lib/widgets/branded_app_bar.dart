import 'package:flutter/material.dart';

import 'school_logo.dart';

/// ===============================================================
/// BRANDED APP BAR
/// ===============================================================
///
/// Premium reusable AppBar for the School Management App.
///
/// Features:
/// • School logo badge
/// • Modern gradient branding
/// • Screen title + school portal subtitle
/// • Optional leading widget
/// • Optional actions
/// • Optional bottom widget
/// • Network logo support
/// • Light/Dark theme friendly
/// • Safe handling of long titles
///
class BrandedAppBar extends StatelessWidget implements PreferredSizeWidget {
  const BrandedAppBar({
    super.key,
    required this.title,
    this.actions,
    this.leading,
    this.bottom,
    this.networkLogoUrl,
    this.subtitle = 'School Management System',
    this.showSubtitle = true,
    this.showLogo = true,
    this.centerTitle = false,
  });

  final String title;

  final String subtitle;

  final List<Widget>? actions;

  final Widget? leading;

  final PreferredSizeWidget? bottom;

  final String? networkLogoUrl;

  final bool showSubtitle;

  final bool showLogo;

  final bool centerTitle;

  @override
  Size get preferredSize {
    return Size.fromHeight(
      kToolbarHeight + (bottom?.preferredSize.height ?? 0),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final isDark = theme.brightness == Brightness.dark;

    return AppBar(
      automaticallyImplyLeading: true,
      leading: leading,
      centerTitle: centerTitle,
      elevation: 0,
      scrolledUnderElevation: 0,
      surfaceTintColor: Colors.transparent,
      backgroundColor: Colors.transparent,
      foregroundColor: colorScheme.onSurface,
      shadowColor: Colors.transparent,
      toolbarHeight: kToolbarHeight,
      titleSpacing: leading == null ? 18 : 0,
      flexibleSpace: _buildBackground(
        context,
        isDark,
      ),
      title: _buildTitle(
        context,
        isDark,
      ),
      actions: actions == null
          ? null
          : _buildActions(
              context,
              actions!,
            ),
      bottom: bottom,
    );
  }

  // =============================================================
  // BACKGROUND
  // =============================================================

  Widget _buildBackground(
    BuildContext context,
    bool isDark,
  ) {
    final colorScheme = Theme.of(context).colorScheme;

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isDark
              ? [
                  const Color(0xFF101827),
                  const Color(0xFF16233A),
                  const Color(0xFF101827),
                ]
              : [
                  colorScheme.surface,
                  const Color(0xFFF7F9FC),
                  colorScheme.surface,
                ],
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(
              alpha: isDark ? 0.18 : 0.06,
            ),
            blurRadius: 18,
            offset: const Offset(
              0,
              5,
            ),
          ),
        ],
        border: Border(
          bottom: BorderSide(
            color: colorScheme.outline.withValues(
              alpha: isDark ? 0.16 : 0.08,
            ),
          ),
        ),
      ),
      child: Stack(
        children: [
          // -------------------------------------------------------
          // Decorative glow - top right
          // -------------------------------------------------------

          Positioned(
            top: -35,
            right: -25,
            child: IgnorePointer(
              child: Container(
                width: 130,
                height: 130,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      colorScheme.primary.withValues(
                        alpha: isDark ? 0.15 : 0.07,
                      ),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
          ),

          // -------------------------------------------------------
          // Decorative glow - bottom left
          // -------------------------------------------------------

          Positioned(
            bottom: -50,
            left: -30,
            child: IgnorePointer(
              child: Container(
                width: 120,
                height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      colorScheme.secondary.withValues(
                        alpha: isDark ? 0.10 : 0.045,
                      ),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // =============================================================
  // TITLE
  // =============================================================

  Widget _buildTitle(
    BuildContext context,
    bool isDark,
  ) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final titleWidget = Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ---------------------------------------------------------
        // Main title
        // ---------------------------------------------------------

        Text(
          title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 17,
            height: 1.1,
            fontWeight: FontWeight.w800,
            letterSpacing: -0.25,
            color: colorScheme.onSurface,
          ),
        ),

        if (showSubtitle) ...[
          const SizedBox(height: 3),
          Text(
            subtitle,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 10.5,
              height: 1,
              fontWeight: FontWeight.w500,
              letterSpacing: 0.15,
              color: colorScheme.onSurface.withValues(
                alpha: 0.50,
              ),
            ),
          ),
        ],
      ],
    );

    // ===========================================================
    // WITHOUT LOGO
    // ===========================================================

    if (!showLogo) {
      return titleWidget;
    }

    // ===========================================================
    // LOGO + TITLE
    // ===========================================================

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // -------------------------------------------------------
        // Logo container
        // -------------------------------------------------------

        Container(
          width: 42,
          height: 42,
          padding: const EdgeInsets.all(5),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(13),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: isDark
                  ? [
                      Colors.white.withValues(
                        alpha: 0.13,
                      ),
                      Colors.white.withValues(
                        alpha: 0.05,
                      ),
                    ]
                  : [
                      Colors.white,
                      const Color(0xFFF1F5F9),
                    ],
            ),
            border: Border.all(
              color: isDark
                  ? Colors.white.withValues(
                      alpha: 0.12,
                    )
                  : colorScheme.outline.withValues(
                      alpha: 0.10,
                    ),
            ),
            boxShadow: [
              BoxShadow(
                color: colorScheme.primary.withValues(
                  alpha: isDark ? 0.16 : 0.08,
                ),
                blurRadius: 12,
                offset: const Offset(
                  0,
                  4,
                ),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(9),
            child: SchoolLogo(
              size: 32,
              networkUrl: networkLogoUrl,
            ),
          ),
        ),

        const SizedBox(width: 11),

        // -------------------------------------------------------
        // Title
        // -------------------------------------------------------

        Flexible(
          child: titleWidget,
        ),
      ],
    );
  }

  // =============================================================
  // ACTIONS
  // =============================================================

  List<Widget> _buildActions(
    BuildContext context,
    List<Widget> actions,
  ) {
    return [
      ...List.generate(
        actions.length,
        (index) {
          final action = actions[index];

          return Padding(
            padding: EdgeInsets.only(
              right: index == actions.length - 1 ? 10 : 2,
            ),
            child: _ActionWrapper(
              child: action,
            ),
          );
        },
      ),
    ];
  }
}

/// ===============================================================
/// ACTION WRAPPER
/// ===============================================================
///
/// Gives AppBar action buttons a consistent premium appearance
/// without requiring changes to the individual action widgets.

class _ActionWrapper extends StatelessWidget {
  const _ActionWrapper({
    required this.child,
  });

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      constraints: const BoxConstraints(
        minWidth: 42,
        minHeight: 42,
      ),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(13),
        color: colorScheme.onSurface.withValues(
          alpha: Theme.of(context).brightness == Brightness.dark ? 0.07 : 0.045,
        ),
        border: Border.all(
          color: colorScheme.outline.withValues(
            alpha: 0.08,
          ),
        ),
      ),
      child: child,
    );
  }
}

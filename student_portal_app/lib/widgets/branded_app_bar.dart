import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import 'school_logo.dart';

/// App bar that carries the school brand: the logo badge sits beside the
/// screen title. Falls back to the vector badge until a logo asset or
/// network image is configured.
class BrandedAppBar extends StatelessWidget implements PreferredSizeWidget {
  const BrandedAppBar({
    super.key,
    required this.title,
    this.actions,
    this.leading,
    this.bottom,
    this.networkLogoUrl,
  });

  final String title;
  final List<Widget>? actions;
  final Widget? leading;
  final PreferredSizeWidget? bottom;
  final String? networkLogoUrl;

  @override
  Size get preferredSize => Size.fromHeight(
        kToolbarHeight + (bottom?.preferredSize.height ?? 0),
      );

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return AppBar(
      leading: leading,
      bottom: bottom,
      title: Row(
        children: [
          SchoolLogo(size: 30, networkUrl: networkLogoUrl),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.appBarTheme.titleTextStyle,
            ),
          ),
        ],
      ),
      actions: actions,
    );
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/auth_controller.dart';
import '../controllers/student_controller.dart';
import 'attendance_view.dart';
import 'dashboard_view.dart';
import 'digital_id_card_view.dart';
import 'fee_view.dart';
import 'login_view.dart';
import 'notification_center_view.dart';
import 'change_password_view.dart';
import 'contact_school_view.dart';

class MainScaffoldView extends StatefulWidget {
  const MainScaffoldView({super.key});

  @override
  State<MainScaffoldView> createState() => _MainScaffoldViewState();
}

class _MainScaffoldViewState extends State<MainScaffoldView> {
  int _currentIndex = 0;

  final List<Widget> _pages = const [
    DashboardView(),
    AttendanceView(),
    FeeView(),
    DigitalIdCardView(),
  ];

  final List<String> _titles = const [
    'Dashboard',
    'Attendance Overview',
    'Fee Management',
    'Digital Student ID',
  ];

  final List<String> _subtitles = const [
    'Welcome back to your student portal',
    'Track your attendance records',
    'Manage your fee & payments',
    'Your official digital identity',
  ];

  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<StudentController>().fetchAllData();
    });
  }

  void _handleLogout() async {
    final auth = context.read<AuthController>();

    context.read<StudentController>().clearAllData();

    await auth.logout();

    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => const LoginView(),
        ),
      );
    }
  }

  void _openNotifications() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => const NotificationCenterView(),
      ),
    );
  }

  void _openChangePassword() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => const ChangePasswordView(),
      ),
    );
  }

  void _showProfileMenu() {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          decoration: BoxDecoration(
            color: colors.surface,
            borderRadius: const BorderRadius.vertical(
              top: Radius.circular(28),
            ),
          ),
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 30),
          child: SafeArea(
            top: false,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Handle
                Container(
                  width: 42,
                  height: 4,
                  decoration: BoxDecoration(
                    color: colors.onSurfaceVariant.withValues(
                      alpha: 0.25,
                    ),
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),

                const SizedBox(height: 22),

                Row(
                  children: [
                    Container(
                      height: 50,
                      width: 50,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            colors.primary,
                            colors.primaryContainer,
                          ],
                        ),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: const Icon(
                        Icons.person_rounded,
                        color: Colors.white,
                        size: 26,
                      ),
                    ),
                    const SizedBox(width: 13),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Account Settings',
                            style: theme.textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            'Manage your student account',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: colors.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 18),

                _bottomSheetItem(
                  context: context,
                  icon: Icons.lock_outline_rounded,
                  title: 'Change Password',
                  subtitle: 'Update your account password',
                  iconColor: colors.primary,
                  onTap: () {
                    Navigator.pop(context);
                    _openChangePassword();
                  },
                ),

                const SizedBox(height: 8),

                _bottomSheetItem(
                  context: context,
                  icon: Icons.logout_rounded,
                  title: 'Sign Out',
                  subtitle: 'Sign out from this device',
                  iconColor: colors.error,
                  onTap: () {
                    Navigator.pop(context);
                    _handleLogout();
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _bottomSheetItem({
    required BuildContext context,
    required IconData icon,
    required String title,
    required String subtitle,
    required Color iconColor,
    required VoidCallback onTap,
  }) {
    final colors = Theme.of(context).colorScheme;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: colors.surfaceContainerHighest.withValues(
            alpha: 0.45,
          ),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(
          children: [
            Container(
              height: 44,
              width: 44,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(13),
              ),
              child: Icon(
                icon,
                color: iconColor,
                size: 21,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 11,
                      color: colors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: colors.onSurfaceVariant.withValues(
                alpha: 0.55,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;

    return Scaffold(
      backgroundColor: colors.surface,

      // ================================================================
      // APP BAR
      // ================================================================

      appBar: AppBar(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: colors.surface,
        toolbarHeight: 76,
        titleSpacing: 20,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _titles[_currentIndex],
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w900,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              _subtitles[_currentIndex],
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colors.onSurfaceVariant,
                fontSize: 11,
              ),
            ),
          ],
        ),
        actions: [
          // ============================================================
          // NOTIFICATIONS
          // ============================================================

          Padding(
            padding: const EdgeInsets.only(right: 4),
            child: Container(
              height: 42,
              width: 42,
              decoration: BoxDecoration(
                color: colors.surfaceContainerHighest.withValues(
                  alpha: 0.65,
                ),
                shape: BoxShape.circle,
              ),
              child: IconButton(
                tooltip: 'Notifications',
                onPressed: _openNotifications,
                icon: Icon(
                  Icons.notifications_none_rounded,
                  color: colors.onSurface,
                  size: 22,
                ),
              ),
            ),
          ),

          // ============================================================
          // PROFILE / MENU
          // ============================================================

          Padding(
            padding: const EdgeInsets.only(
              right: 16,
            ),
            child: InkWell(
              onTap: _showProfileMenu,
              borderRadius: BorderRadius.circular(15),
              child: Container(
                height: 42,
                width: 42,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      colors.primary,
                      colors.primaryContainer,
                    ],
                  ),
                  borderRadius: BorderRadius.circular(15),
                  boxShadow: [
                    BoxShadow(
                      color: colors.primary.withValues(
                        alpha: 0.18,
                      ),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.person_rounded,
                  color: Colors.white,
                  size: 21,
                ),
              ),
            ),
          ),
        ],
      ),

      // ================================================================
      // PAGE CONTENT
      // ================================================================

      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),

      // ================================================================
      // BOTTOM NAVIGATION
      // ================================================================

      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: colors.surface,
          border: Border(
            top: BorderSide(
              color: colors.outlineVariant.withValues(
                alpha: 0.30,
              ),
            ),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(
                alpha: 0.045,
              ),
              blurRadius: 18,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        child: NavigationBarTheme(
          data: NavigationBarThemeData(
            height: 76,
            backgroundColor: Colors.transparent,
            elevation: 0,
            indicatorColor: colors.primary.withValues(
              alpha: 0.13,
            ),
            labelTextStyle: WidgetStateProperty.resolveWith(
              (states) {
                final selected = states.contains(
                  WidgetState.selected,
                );

                return TextStyle(
                  fontSize: 10.5,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                  letterSpacing: 0.1,
                  color: selected ? colors.primary : colors.onSurfaceVariant,
                );
              },
            ),
            iconTheme: WidgetStateProperty.resolveWith(
              (states) {
                final selected = states.contains(
                  WidgetState.selected,
                );

                return IconThemeData(
                  size: selected ? 23 : 21,
                  color: selected ? colors.primary : colors.onSurfaceVariant,
                );
              },
            ),
          ),
          child: NavigationBar(
            selectedIndex: _currentIndex,
            labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
            onDestinationSelected: (index) {
              if (_currentIndex == index) return;

              setState(() {
                _currentIndex = index;
              });
            },
            destinations: const [
              NavigationDestination(
                icon: Icon(
                  Icons.dashboard_outlined,
                ),
                selectedIcon: Icon(
                  Icons.dashboard_rounded,
                ),
                label: 'Home',
              ),
              NavigationDestination(
                icon: Icon(
                  Icons.calendar_month_outlined,
                ),
                selectedIcon: Icon(
                  Icons.calendar_month_rounded,
                ),
                label: 'Attendance',
              ),
              NavigationDestination(
                icon: Icon(
                  Icons.account_balance_wallet_outlined,
                ),
                selectedIcon: Icon(
                  Icons.account_balance_wallet_rounded,
                ),
                label: 'Fees',
              ),
              NavigationDestination(
                icon: Icon(
                  Icons.badge_outlined,
                ),
                selectedIcon: Icon(
                  Icons.badge_rounded,
                ),
                label: 'Digital ID',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

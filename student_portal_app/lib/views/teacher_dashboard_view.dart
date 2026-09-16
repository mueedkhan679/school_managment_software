import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../controllers/auth_controller.dart';
import '../controllers/teacher_controller.dart';
import 'login_view.dart';
import 'qr_scan_view.dart';
import '../widgets/modern_loader.dart';
import '../widgets/shimmer_placeholders.dart';
import 'package:intl/intl.dart';
import 'notification_center_view.dart';
import 'change_password_view.dart';

class TeacherDashboardView extends StatefulWidget {
  const TeacherDashboardView({super.key});

  @override
  State<TeacherDashboardView> createState() => _TeacherDashboardViewState();
}

class _TeacherDashboardViewState extends State<TeacherDashboardView>
    with SingleTickerProviderStateMixin {
  int _currentIndex = 0;
  int _selectedSalaryYear = DateTime.now().year;

  late AnimationController _pageAnimationController;

  @override
  void initState() {
    super.initState();

    _pageAnimationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 450),
    );

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final tc = context.read<TeacherController>();
      tc.fetchAvailableClasses();
      tc.fetchTeacherAttendance();
      tc.fetchTeacherSalary(year: _selectedSalaryYear);

      _pageAnimationController.forward();
    });
  }

  @override
  void dispose() {
    _pageAnimationController.dispose();
    super.dispose();
  }

  void _onLogout() {
    context.read<TeacherController>().clearAllData();
    context.read<AuthController>().logout();

    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => const LoginView(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tc = context.watch<TeacherController>();

    final screens = [
      _buildAttendanceScreen(context, tc),
      _buildSalaryScreen(context, tc),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFF6F8FC),
      extendBody: true,
      appBar: _buildAppBar(context, tc),
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 300),
        switchInCurve: Curves.easeOutCubic,
        child: KeyedSubtree(
          key: ValueKey(_currentIndex),
          child: screens[_currentIndex],
        ),
      ),
      bottomNavigationBar: _buildBottomNavigation(),
    );
  }

  // ============================================================
  // APP BAR
  // ============================================================

  PreferredSizeWidget _buildAppBar(
    BuildContext context,
    TeacherController tc,
  ) {
    return AppBar(
      elevation: 0,
      backgroundColor: const Color(0xFFF6F8FC),
      surfaceTintColor: Colors.transparent,
      toolbarHeight: 76,
      automaticallyImplyLeading: false,
      titleSpacing: 20,
      title: Row(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [
                  Color(0xFF2563EB),
                  Color(0xFF4F46E5),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(15),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF2563EB).withOpacity(.22),
                  blurRadius: 18,
                  offset: const Offset(0, 7),
                ),
              ],
            ),
            child: const Icon(
              Icons.school_rounded,
              color: Colors.white,
              size: 23,
            ),
          ),
          const SizedBox(width: 13),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _currentIndex == 0 ? 'Attendance' : 'Salary',
                style: const TextStyle(
                  fontSize: 21,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF111827),
                  letterSpacing: -.4,
                ),
              ),
              Text(
                _currentIndex == 0
                    ? 'Manage your class attendance'
                    : 'View your salary records',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: Colors.blueGrey.shade500,
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        _appBarIcon(
          icon: Icons.qr_code_scanner_rounded,
          tooltip: 'Scan Attendance QR',
          onTap: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const QrScanView(),
              ),
            );
          },
        ),
        const SizedBox(width: 5),
        _appBarIcon(
          icon: Icons.person_add_alt_1_rounded,
          tooltip: 'Add Student',
          onTap: () => _openAddStudentDialog(context),
        ),
        const SizedBox(width: 5),
        _appBarIcon(
          icon: Icons.notifications_none_rounded,
          tooltip: 'Notifications',
          onTap: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const NotificationCenterView(),
              ),
            );
          },
        ),
        const SizedBox(width: 3),
        _buildProfileMenu(context),
        const SizedBox(width: 10),
      ],
    );
  }

  Widget _appBarIcon({
    required IconData icon,
    required String tooltip,
    required VoidCallback onTap,
  }) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(13),
        child: InkWell(
          borderRadius: BorderRadius.circular(13),
          onTap: onTap,
          child: Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(13),
              border: Border.all(
                color: const Color(0xFFE6EAF1),
              ),
            ),
            child: Icon(
              icon,
              size: 20,
              color: const Color(0xFF334155),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildProfileMenu(BuildContext context) {
    return PopupMenuButton<String>(
      tooltip: 'Account',
      offset: const Offset(0, 52),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      elevation: 8,
      onSelected: (value) {
        if (value == 'password') {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => const ChangePasswordView(),
            ),
          );
        } else if (value == 'logout') {
          _onLogout();
        }
      },
      itemBuilder: (context) => [
        const PopupMenuItem(
          value: 'password',
          child: Row(
            children: [
              Icon(
                Icons.lock_outline_rounded,
                size: 20,
              ),
              SizedBox(width: 12),
              Text('Change Password'),
            ],
          ),
        ),
        const PopupMenuDivider(),
        const PopupMenuItem(
          value: 'logout',
          child: Row(
            children: [
              Icon(
                Icons.logout_rounded,
                size: 20,
                color: Colors.red,
              ),
              SizedBox(width: 12),
              Text(
                'Logout',
                style: TextStyle(
                  color: Colors.red,
                ),
              ),
            ],
          ),
        ),
      ],
      child: Container(
        width: 43,
        height: 43,
        margin: const EdgeInsets.only(left: 4),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [
              Color(0xFFEEF4FF),
              Color(0xFFE8ECFF),
            ],
          ),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: const Color(0xFFDCE5FA),
          ),
        ),
        child: const Icon(
          Icons.person_rounded,
          color: Color(0xFF3157C8),
          size: 22,
        ),
      ),
    );
  }

  // ============================================================
  // BOTTOM NAVIGATION
  // ============================================================

  Widget _buildBottomNavigation() {
    return SafeArea(
      minimum: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: Container(
        height: 72,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: const Color(0xFFE7EAF0),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(.07),
              blurRadius: 30,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Row(
          children: [
            _navItem(
              index: 0,
              icon: Icons.fact_check_outlined,
              activeIcon: Icons.fact_check_rounded,
              label: 'Attendance',
            ),
            _navItem(
              index: 1,
              icon: Icons.payments_outlined,
              activeIcon: Icons.payments_rounded,
              label: 'Salary',
            ),
          ],
        ),
      ),
    );
  }

  Widget _navItem({
    required int index,
    required IconData icon,
    required IconData activeIcon,
    required String label,
  }) {
    final selected = _currentIndex == index;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          if (_currentIndex == index) return;

          setState(() {
            _currentIndex = index;
          });
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOutCubic,
          margin: const EdgeInsets.all(7),
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            gradient: selected
                ? const LinearGradient(
                    colors: [
                      Color(0xFF2563EB),
                      Color(0xFF4F46E5),
                    ],
                  )
                : null,
            borderRadius: BorderRadius.circular(18),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                selected ? activeIcon : icon,
                size: 21,
                color: selected ? Colors.white : const Color(0xFF64748B),
              ),
              const SizedBox(width: 8),
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                  color: selected ? Colors.white : const Color(0xFF64748B),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ============================================================
  // ATTENDANCE SCREEN
  // ============================================================

  Widget _buildAttendanceScreen(
    BuildContext context,
    TeacherController tc,
  ) {
    return Column(
      children: [
        _buildAttendanceHeader(context, tc),
        if (tc.isLoadingClasses)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: const LinearProgressIndicator(
                minHeight: 3,
              ),
            ),
          )
        else if (tc.classesError != null)
          _buildErrorBanner(
            tc.classesError!,
            () => tc.fetchAvailableClasses(),
          )
        else if (tc.availableClasses.isNotEmpty)
          _buildClassSelector(tc),
        _buildClassSummaryCard(tc),
        if (!tc.isLoadingAttendance && tc.attendanceRoster.isNotEmpty)
          _buildBulkActions(tc),
        Expanded(
          child: tc.isLoadingAttendance
              ? const SkeletonList(itemCount: 8)
              : tc.attendanceError != null
                  ? _buildCenteredError(
                      tc.attendanceError!,
                      () => tc.fetchTeacherAttendance(),
                    )
                  : tc.selectedClassIsEmpty
                      ? _buildEmptyClassState()
                      : tc.attendanceRoster.isEmpty
                          ? _buildNoStudentsState()
                          : _buildRoster(tc),
        ),
      ],
    );
  }

  Widget _buildAttendanceHeader(
    BuildContext context,
    TeacherController tc,
  ) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 2, 20, 14),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              onTap: () async {
                final date = await showDatePicker(
                  context: context,
                  initialDate: tc.selectedDate,
                  firstDate: DateTime.now().subtract(
                    const Duration(days: 365),
                  ),
                  lastDate: DateTime.now(),
                  builder: (context, child) {
                    return Theme(
                      data: Theme.of(context).copyWith(
                        colorScheme: const ColorScheme.light(
                          primary: Color(0xFF2563EB),
                        ),
                      ),
                      child: child!,
                    );
                  },
                );

                if (date != null) {
                  tc.setSelectedDate(date);
                }
              },
              child: Container(
                height: 66,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                    color: const Color(0xFFE5EAF2),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(.035),
                      blurRadius: 15,
                      offset: const Offset(0, 5),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: const Color(0xFFEFF5FF),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(
                        Icons.calendar_month_rounded,
                        color: Color(0xFF2563EB),
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Attendance Date',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: Colors.blueGrey.shade400,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            DateFormat('dd MMM yyyy').format(tc.selectedDate),
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF172033),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(
                      Icons.keyboard_arrow_down_rounded,
                      color: Color(0xFF94A3B8),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          SizedBox(
            height: 66,
            child: FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF2563EB),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 18),
                elevation: 0,
              ),
              onPressed: tc.isLoadingAttendance
                  ? null
                  : () async {
                      final success = await tc.submitAttendance();

                      if (!context.mounted) return;

                      if (success) {
                        await showDialog<void>(
                          context: context,
                          builder: (dialogContext) {
                            return _buildSuccessDialog(
                              dialogContext,
                            );
                          },
                        );

                        if (!context.mounted) return;

                        tc.fetchTeacherAttendance();
                      } else {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              tc.attendanceError ?? 'Failed to submit',
                            ),
                            backgroundColor: const Color(0xFFDC2626),
                            behavior: SnackBarBehavior.floating,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
                          ),
                        );
                      }
                    },
              child: tc.isLoadingAttendance
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.cloud_upload_rounded,
                          size: 20,
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Submit',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSuccessDialog(BuildContext dialogContext) {
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(28),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 28, 24, 22),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 76,
              height: 76,
              decoration: BoxDecoration(
                color: const Color(0xFFE9F9F0),
                shape: BoxShape.circle,
                border: Border.all(
                  color: const Color(0xFFBCEBD0),
                ),
              ),
              child: const Icon(
                Icons.check_rounded,
                color: Color(0xFF16A34A),
                size: 42,
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'Attendance Submitted',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 21,
                fontWeight: FontWeight.w800,
                color: Color(0xFF111827),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Your attendance has been submitted successfully.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                height: 1.5,
                color: Colors.blueGrey.shade500,
              ),
            ),
            const SizedBox(height: 22),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: FilledButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF2563EB),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(15),
                  ),
                ),
                child: const Text(
                  'Done',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // CLASS SELECTOR
  // ============================================================

  Widget _buildClassSelector(TeacherController tc) {
    return SizedBox(
      height: 57,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
        itemCount: tc.availableClasses.length + 1,
        separatorBuilder: (_, __) => const SizedBox(width: 9),
        itemBuilder: (context, index) {
          if (index == 0) {
            final selected = tc.selectedClassId == null;

            return _classChip(
              title: 'All Classes',
              icon: Icons.grid_view_rounded,
              selected: selected,
              onTap: () => tc.selectClass(null),
            );
          }

          final schoolClass = tc.availableClasses[index - 1];

          final selected = tc.selectedClassId == schoolClass.id;

          return _classChip(
            title: '${schoolClass.name} (${schoolClass.studentCount})',
            icon: Icons.class_rounded,
            selected: selected,
            onTap: () => tc.selectClass(schoolClass.id),
          );
        },
      ),
    );
  }

  Widget _classChip({
    required String title,
    required IconData icon,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        padding: const EdgeInsets.symmetric(
          horizontal: 14,
        ),
        decoration: BoxDecoration(
          gradient: selected
              ? const LinearGradient(
                  colors: [
                    Color(0xFF2563EB),
                    Color(0xFF4F46E5),
                  ],
                )
              : null,
          color: selected ? null : Colors.white,
          borderRadius: BorderRadius.circular(15),
          border: Border.all(
            color: selected ? Colors.transparent : const Color(0xFFE4E9F1),
          ),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: const Color(0xFF2563EB).withOpacity(.20),
                    blurRadius: 14,
                    offset: const Offset(0, 6),
                  ),
                ]
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 16,
              color: selected ? Colors.white : const Color(0xFF64748B),
            ),
            const SizedBox(width: 7),
            Text(
              title,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                color: selected ? Colors.white : const Color(0xFF475569),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // SUMMARY
  // ============================================================

  Widget _buildClassSummaryCard(
    TeacherController tc,
  ) {
    return Container(
      margin: const EdgeInsets.fromLTRB(20, 3, 20, 12),
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            Color(0xFF111D35),
            Color(0xFF172A4B),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(23),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF111D35).withOpacity(.18),
            blurRadius: 22,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 35,
                height: 35,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(.10),
                  borderRadius: BorderRadius.circular(11),
                ),
                child: const Icon(
                  Icons.analytics_rounded,
                  color: Colors.white,
                  size: 19,
                ),
              ),
              const SizedBox(width: 11),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Today\'s Overview',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Live attendance summary',
                      style: TextStyle(
                        color: Colors.white54,
                        fontSize: 10,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 9,
                  vertical: 5,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(.08),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Row(
                  children: [
                    Icon(
                      Icons.circle,
                      color: Color(0xFF34D399),
                      size: 7,
                    ),
                    SizedBox(width: 5),
                    Text(
                      'LIVE',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 17),
          Row(
            children: [
              _summaryItem(
                'Total',
                '${tc.totalStudents}',
                Icons.groups_rounded,
                const Color(0xFF60A5FA),
              ),
              _summaryDivider(),
              _summaryItem(
                'Present',
                '${tc.presentCount}',
                Icons.check_circle_rounded,
                const Color(0xFF34D399),
              ),
              _summaryDivider(),
              _summaryItem(
                'Absent',
                '${tc.absentCount}',
                Icons.cancel_rounded,
                const Color(0xFFF87171),
              ),
              _summaryDivider(),
              _summaryItem(
                'Leave',
                '${tc.leaveCount}',
                Icons.event_busy_rounded,
                const Color(0xFFFBBF24),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _summaryItem(
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Expanded(
      child: Column(
        children: [
          Icon(
            icon,
            color: color,
            size: 19,
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(
              color: Colors.white54,
              fontSize: 9,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _summaryDivider() {
    return Container(
      height: 40,
      width: 1,
      color: Colors.white.withOpacity(.08),
    );
  }

  // ============================================================
  // BULK ACTIONS
  // ============================================================

  Widget _buildBulkActions(TeacherController tc) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 9),
      child: Row(
        children: [
          const Expanded(
            child: Text(
              'Student Roster',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w800,
                color: Color(0xFF172033),
              ),
            ),
          ),
          _bulkButton(
            icon: Icons.check_rounded,
            label: 'All Present',
            color: const Color(0xFF16A34A),
            onTap: () => tc.markAllAttendance('PRESENT'),
          ),
          const SizedBox(width: 7),
          _bulkButton(
            icon: Icons.close_rounded,
            label: 'All Absent',
            color: const Color(0xFFDC2626),
            onTap: () => tc.markAllAttendance('ABSENT'),
          ),
        ],
      ),
    );
  }

  Widget _bulkButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Material(
      color: color.withOpacity(.08),
      borderRadius: BorderRadius.circular(11),
      child: InkWell(
        borderRadius: BorderRadius.circular(11),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: 9,
            vertical: 7,
          ),
          child: Row(
            children: [
              Icon(
                icon,
                size: 15,
                color: color,
              ),
              const SizedBox(width: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.w800,
                  color: color,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ============================================================
  // ROSTER
  // ============================================================

  Widget _buildRoster(TeacherController tc) {
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(20, 3, 20, 115),
      itemCount: tc.attendanceRoster.length,
      itemBuilder: (context, index) {
        final student = tc.attendanceRoster[index];

        final currentStatus =
            tc.attendanceSubmissions[student.id.toString()] ?? student.status;

        final isLocked =
            student.isMarked && !tc.isEditingAttendance(student.id);

        return _buildStudentCard(
          tc: tc,
          student: student,
          currentStatus: currentStatus,
          isLocked: isLocked,
        );
      },
    );
  }

  Widget _buildStudentCard({
    required TeacherController tc,
    required dynamic student,
    required String currentStatus,
    required bool isLocked,
  }) {
    final statusColor = _statusColor(currentStatus);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: const Color(0xFFE8ECF2),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(.025),
            blurRadius: 16,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [
                  Color(0xFFEFF5FF),
                  Color(0xFFE8EDFF),
                ],
              ),
              borderRadius: BorderRadius.circular(15),
            ),
            child: Center(
              child: Text(
                student.name.isNotEmpty ? student.name[0].toUpperCase() : '?',
                style: const TextStyle(
                  color: Color(0xFF3157C8),
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  student.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF172033),
                  ),
                ),
                const SizedBox(height: 5),
                Row(
                  children: [
                    const Icon(
                      Icons.badge_outlined,
                      size: 12,
                      color: Color(0xFF94A3B8),
                    ),
                    const SizedBox(width: 4),
                    Flexible(
                      child: Text(
                        '${student.studentId} • ${student.schoolClassName}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 9.5,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF94A3B8),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 7),
          if (isLocked)
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _statusBadge(
                  currentStatus,
                  statusColor,
                ),
                const SizedBox(width: 5),
                Material(
                  color: const Color(0xFFF4F6F9),
                  borderRadius: BorderRadius.circular(10),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(10),
                    onTap: () => tc.setEditingAttendance(
                      student.id,
                    ),
                    child: const Padding(
                      padding: EdgeInsets.all(8),
                      child: Icon(
                        Icons.edit_rounded,
                        size: 15,
                        color: Color(0xFF64748B),
                      ),
                    ),
                  ),
                ),
              ],
            )
          else
            _attendanceSelector(
              tc,
              student.id,
              currentStatus,
            ),
        ],
      ),
    );
  }

  Widget _statusBadge(
    String status,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 9,
        vertical: 7,
      ),
      decoration: BoxDecoration(
        color: color.withOpacity(.09),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        status,
        style: TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.w900,
          color: color,
        ),
      ),
    );
  }

  Widget _attendanceSelector(
    TeacherController tc,
    int studentId,
    String currentStatus,
  ) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _miniStatus(
          tc: tc,
          studentId: studentId,
          label: 'P',
          value: 'PRESENT',
          currentStatus: currentStatus,
          color: const Color(0xFF16A34A),
        ),
        const SizedBox(width: 4),
        _miniStatus(
          tc: tc,
          studentId: studentId,
          label: 'A',
          value: 'ABSENT',
          currentStatus: currentStatus,
          color: const Color(0xFFDC2626),
        ),
        const SizedBox(width: 4),
        _miniStatus(
          tc: tc,
          studentId: studentId,
          label: 'L',
          value: 'LEAVE',
          currentStatus: currentStatus,
          color: const Color(0xFFD97706),
        ),
      ],
    );
  }

  Widget _miniStatus({
    required TeacherController tc,
    required int studentId,
    required String label,
    required String value,
    required String currentStatus,
    required Color color,
  }) {
    final selected = currentStatus == value;

    return GestureDetector(
      onTap: () {
        tc.updateAttendanceStatus(
          studentId,
          value,
        );
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        width: 31,
        height: 31,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? color.withOpacity(.12) : const Color(0xFFF5F7FA),
          borderRadius: BorderRadius.circular(9),
          border: Border.all(
            color: selected ? color.withOpacity(.35) : const Color(0xFFE8ECF1),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w900,
            color: selected ? color : const Color(0xFF94A3B8),
          ),
        ),
      ),
    );
  }

  Color _statusColor(String status) {
    switch (status.toUpperCase()) {
      case 'PRESENT':
        return const Color(0xFF16A34A);
      case 'ABSENT':
        return const Color(0xFFDC2626);
      case 'LEAVE':
        return const Color(0xFFD97706);
      default:
        return const Color(0xFF64748B);
    }
  }

  // ============================================================
  // SALARY
  // ============================================================

  Widget _buildSalaryScreen(
    BuildContext context,
    TeacherController tc,
  ) {
    final currentYear = DateTime.now().year;

    final availableYears = [
      currentYear + 1,
      currentYear,
      currentYear - 1,
      currentYear - 2,
    ];

    return Column(
      children: [
        _buildSalaryHeader(
          tc,
          availableYears,
        ),
        Expanded(
          child: tc.isLoadingSalary
              ? const ModernLoader(
                  message: 'Loading salary details…',
                )
              : tc.salaryError != null
                  ? _buildCenteredError(
                      tc.salaryError!,
                      () => tc.fetchTeacherSalary(
                        year: _selectedSalaryYear,
                      ),
                    )
                  : tc.salaryData == null
                      ? _buildNoSalaryState()
                      : _buildSalaryDetails(
                          tc.salaryData!,
                        ),
        ),
      ],
    );
  }

  Widget _buildSalaryHeader(
    TeacherController tc,
    List<int> availableYears,
  ) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        20,
        3,
        20,
        14,
      ),
      child: Row(
        children: [
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Salary Records',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF172033),
                  ),
                ),
                SizedBox(height: 3),
                Text(
                  'Track monthly payments',
                  style: TextStyle(
                    fontSize: 10,
                    color: Color(0xFF94A3B8),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          Container(
            height: 45,
            padding: const EdgeInsets.symmetric(
              horizontal: 12,
            ),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: const Color(0xFFE4E9F1),
              ),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<int>(
                value: _selectedSalaryYear,
                isDense: true,
                icon: const Icon(
                  Icons.keyboard_arrow_down_rounded,
                  size: 19,
                ),
                items: availableYears.map((year) {
                  return DropdownMenuItem<int>(
                    value: year,
                    child: Text(
                      '$year',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  );
                }).toList(),
                onChanged: (newYear) {
                  if (newYear != null && newYear != _selectedSalaryYear) {
                    setState(() {
                      _selectedSalaryYear = newYear;
                    });

                    tc.fetchTeacherSalary(
                      year: newYear,
                    );
                  }
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSalaryDetails(
    dynamic data,
  ) {
    final paidCount =
        (data.monthlyStatuses as List).where((m) => m.isPaid).length;

    final totalCount = (data.monthlyStatuses as List).length;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        20,
        0,
        20,
        115,
      ),
      child: Column(
        children: [
          _buildSalaryHero(
            data,
            paidCount,
            totalCount,
          ),
          const SizedBox(height: 15),
          _buildSalaryStats(
            data,
            paidCount,
            totalCount,
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Monthly Breakdown',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF172033),
                  ),
                ),
              ),
              Text(
                '$_selectedSalaryYear',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF64748B),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ...List.generate(
            data.monthlyStatuses.length,
            (index) {
              final month = data.monthlyStatuses[index];

              return _buildMonthCard(month);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildSalaryHero(
    dynamic data,
    int paidCount,
    int totalCount,
  ) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            Color(0xFF111D35),
            Color(0xFF243E70),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(25),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF111D35).withOpacity(.18),
            blurRadius: 24,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(.10),
                  borderRadius: BorderRadius.circular(17),
                  border: Border.all(
                    color: Colors.white.withOpacity(.10),
                  ),
                ),
                child: const Icon(
                  Icons.person_rounded,
                  color: Colors.white,
                  size: 25,
                ),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      data.name.toString().isNotEmpty
                          ? data.name.toString()
                          : 'Teacher',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      data.teacherId.toString().isNotEmpty
                          ? data.teacherId.toString()
                          : 'Teacher ID',
                      style: const TextStyle(
                        color: Colors.white54,
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 7,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFF34D399).withOpacity(.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Row(
                  children: [
                    Icon(
                      Icons.verified_rounded,
                      size: 14,
                      color: Color(0xFF34D399),
                    ),
                    SizedBox(width: 4),
                    Text(
                      'ACTIVE',
                      style: TextStyle(
                        color: Color(0xFF6EE7B7),
                        fontSize: 8,
                        fontWeight: FontWeight.w900,
                        letterSpacing: .5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(15),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(.07),
              borderRadius: BorderRadius.circular(17),
            ),
            child: Row(
              children: [
                Expanded(
                  child: _heroSalaryValue(
                    'Monthly Salary',
                    'Rs ${data.monthlySalary}',
                    const Color(0xFF60A5FA),
                  ),
                ),
                Container(
                  height: 42,
                  width: 1,
                  color: Colors.white.withOpacity(.10),
                ),
                Expanded(
                  child: _heroSalaryValue(
                    'Yearly Salary',
                    'Rs ${data.yearlySalary}',
                    const Color(0xFF34D399),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              const Icon(
                Icons.calendar_month_rounded,
                color: Colors.white54,
                size: 15,
              ),
              const SizedBox(width: 6),
              Text(
                '$_selectedSalaryYear disbursements',
                style: const TextStyle(
                  color: Colors.white60,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              Text(
                '$paidCount / $totalCount Paid',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _heroSalaryValue(
    String label,
    String value,
    Color color,
  ) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: 5,
      ),
      child: Column(
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Colors.white54,
              fontSize: 9,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            value,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: color,
              fontSize: 15,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSalaryStats(
    dynamic data,
    int paidCount,
    int totalCount,
  ) {
    final pendingCount = totalCount - paidCount;

    return Row(
      children: [
        Expanded(
          child: _salaryStatCard(
            icon: Icons.check_circle_rounded,
            label: 'Paid',
            value: '$paidCount',
            color: const Color(0xFF16A34A),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _salaryStatCard(
            icon: Icons.pending_actions_rounded,
            label: 'Pending',
            value: '$pendingCount',
            color: const Color(0xFFD97706),
          ),
        ),
      ],
    );
  }

  Widget _salaryStatCard({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: const Color(0xFFE8ECF2),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(.025),
            blurRadius: 15,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 39,
            height: 39,
            decoration: BoxDecoration(
              color: color.withOpacity(.09),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              icon,
              color: color,
              size: 20,
            ),
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 9,
                  color: Color(0xFF94A3B8),
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w900,
                  color: Color(0xFF172033),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMonthCard(dynamic month) {
    final isPaid = month.isPaid;

    final color = isPaid ? const Color(0xFF16A34A) : const Color(0xFFD97706);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(19),
        border: Border.all(
          color: isPaid ? const Color(0xFFD8F1E2) : const Color(0xFFF7E7C7),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(.025),
            blurRadius: 15,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 45,
            height: 45,
            decoration: BoxDecoration(
              color: color.withOpacity(.08),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              isPaid ? Icons.check_circle_rounded : Icons.schedule_rounded,
              color: color,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  month.monthName,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF172033),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  isPaid && month.paymentDate != null
                      ? 'Paid on ${month.paymentDate}'
                      : 'Payment pending',
                  style: const TextStyle(
                    fontSize: 9.5,
                    color: Color(0xFF94A3B8),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                'Rs ${month.amount}',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                  color: Color(0xFF172033),
                ),
              ),
              const SizedBox(height: 5),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: color.withOpacity(.08),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  month.status,
                  style: TextStyle(
                    fontSize: 8,
                    fontWeight: FontWeight.w900,
                    color: color,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ============================================================
  // ADD STUDENT
  // ============================================================

  Future<void> _openAddStudentDialog(
    BuildContext context,
  ) async {
    final tc = context.read<TeacherController>();

    if (tc.availableClasses.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text(
            'No classes available yet.',
          ),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      );
      return;
    }

    final nameCtrl = TextEditingController();
    final rollCtrl = TextEditingController();
    final fatherCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();

    var selectedClassId = tc.selectedClassId ?? tc.availableClasses.first.id;

    var submitting = false;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (dCtx, setDialogState) {
            return Dialog(
              insetPadding: const EdgeInsets.symmetric(
                horizontal: 20,
                vertical: 24,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(27),
              ),
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(23),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [
                                Color(0xFF2563EB),
                                Color(0xFF4F46E5),
                              ],
                            ),
                            borderRadius: BorderRadius.circular(15),
                          ),
                          child: const Icon(
                            Icons.person_add_rounded,
                            color: Colors.white,
                            size: 23,
                          ),
                        ),
                        const SizedBox(width: 13),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Add New Student',
                                style: TextStyle(
                                  fontSize: 19,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              SizedBox(height: 3),
                              Text(
                                'Create student portal account',
                                style: TextStyle(
                                  fontSize: 10,
                                  color: Color(0xFF94A3B8),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    _dialogField(
                      controller: nameCtrl,
                      label: 'Student Name *',
                      icon: Icons.person_outline_rounded,
                    ),
                    const SizedBox(height: 12),
                    _dialogField(
                      controller: rollCtrl,
                      label: 'Roll Number',
                      icon: Icons.confirmation_number_outlined,
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      initialValue: selectedClassId,
                      decoration: _dialogDecoration(
                        'Class *',
                        Icons.class_outlined,
                      ),
                      items: tc.availableClasses
                          .map(
                            (c) => DropdownMenuItem<int>(
                              value: c.id,
                              child: Text(
                                c.name,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(
                            () => selectedClassId = value,
                          );
                        }
                      },
                    ),
                    const SizedBox(height: 12),
                    _dialogField(
                      controller: fatherCtrl,
                      label: 'Father Name *',
                      icon: Icons.family_restroom_rounded,
                    ),
                    const SizedBox(height: 12),
                    _dialogField(
                      controller: phoneCtrl,
                      label: 'Contact Phone (optional)',
                      icon: Icons.phone_outlined,
                      keyboardType: TextInputType.phone,
                    ),
                    const SizedBox(height: 23),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: submitting
                                ? null
                                : () => Navigator.of(
                                      dialogContext,
                                    ).pop(),
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size.fromHeight(
                                50,
                              ),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(
                                  14,
                                ),
                              ),
                            ),
                            child: const Text(
                              'Cancel',
                              style: TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: FilledButton(
                            onPressed: submitting
                                ? null
                                : () async {
                                    final name = nameCtrl.text.trim();
                                    final father = fatherCtrl.text.trim();

                                    if (name.isEmpty || father.isEmpty) {
                                      ScaffoldMessenger.of(
                                        dialogContext,
                                      ).showSnackBar(
                                        const SnackBar(
                                          content: Text(
                                            'Name and father name are required.',
                                          ),
                                          backgroundColor: Colors.red,
                                        ),
                                      );
                                      return;
                                    }

                                    setDialogState(
                                      () => submitting = true,
                                    );

                                    final res = await tc.addStudent(
                                      fullName: name,
                                      rollNumber: rollCtrl.text.trim(),
                                      classId: selectedClassId,
                                      fatherName: father,
                                      phone: phoneCtrl.text.trim(),
                                    );

                                    if (!dialogContext.mounted) {
                                      return;
                                    }

                                    Navigator.of(
                                      dialogContext,
                                    ).pop();

                                    if (!context.mounted) {
                                      return;
                                    }

                                    if (res['status'] != 'error') {
                                      final payload =
                                          res['payload'] is Map<String, dynamic>
                                              ? res['payload']
                                                  as Map<String, dynamic>
                                              : <String, dynamic>{};

                                      final username = (payload['username'] ??
                                              res['username'] ??
                                              '')
                                          .toString();

                                      final defaultPassword =
                                          (payload['default_password'] ??
                                                  res['default_password'] ??
                                                  '')
                                              .toString();

                                      await _showAccountCreatedDialog(
                                        context,
                                        username: username,
                                        defaultPassword: defaultPassword,
                                      );
                                    } else {
                                      ScaffoldMessenger.of(
                                        context,
                                      ).showSnackBar(
                                        SnackBar(
                                          content: Text(
                                            res['message']?.toString() ??
                                                'Failed to add student',
                                          ),
                                          backgroundColor: Colors.red,
                                          behavior: SnackBarBehavior.floating,
                                        ),
                                      );
                                    }
                                  },
                            style: FilledButton.styleFrom(
                              minimumSize: const Size.fromHeight(
                                50,
                              ),
                              backgroundColor: const Color(0xFF2563EB),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(
                                  14,
                                ),
                              ),
                            ),
                            child: submitting
                                ? const SizedBox(
                                    width: 19,
                                    height: 19,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Text(
                                    'Add Student',
                                    style: TextStyle(
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    nameCtrl.dispose();
    rollCtrl.dispose();
    fatherCtrl.dispose();
    phoneCtrl.dispose();
  }

  InputDecoration _dialogDecoration(
    String label,
    IconData icon,
  ) {
    return InputDecoration(
      labelText: label,
      prefixIcon: Icon(
        icon,
        size: 19,
      ),
      filled: true,
      fillColor: const Color(0xFFF8FAFC),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide.none,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(
          color: Color(0xFFE8ECF2),
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(
          color: Color(0xFF2563EB),
          width: 1.4,
        ),
      ),
    );
  }

  Widget _dialogField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    TextInputType? keyboardType,
  }) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      decoration: _dialogDecoration(
        label,
        icon,
      ),
    );
  }

  // ============================================================
  // ACCOUNT CREATED
  // ============================================================

  Future<void> _showAccountCreatedDialog(
    BuildContext context, {
    required String username,
    required String defaultPassword,
  }) async {
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (sCtx) {
        return Dialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(27),
          ),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 74,
                  height: 74,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE9F9F0),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.check_circle_rounded,
                    color: Color(0xFF16A34A),
                    size: 43,
                  ),
                ),
                const SizedBox(height: 18),
                const Text(
                  'Account Created!',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 21,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 7),
                Text(
                  'Save these login details for the student.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.blueGrey.shade500,
                  ),
                ),
                const SizedBox(height: 20),
                _credentialRow(
                  sCtx,
                  'Username',
                  username,
                ),
                const SizedBox(height: 10),
                _credentialRow(
                  sCtx,
                  'Default Password',
                  defaultPassword,
                ),
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: OutlinedButton.icon(
                    onPressed: () {
                      Clipboard.setData(
                        ClipboardData(
                          text:
                              'Username: $username\nDefault Password: $defaultPassword',
                        ),
                      );

                      ScaffoldMessenger.of(
                        sCtx,
                      ).showSnackBar(
                        const SnackBar(
                          content: Text(
                            'Login details copied.',
                          ),
                        ),
                      );
                    },
                    icon: const Icon(
                      Icons.copy_rounded,
                      size: 17,
                    ),
                    label: const Text(
                      'Copy Login Details',
                    ),
                    style: OutlinedButton.styleFrom(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 9),
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: FilledButton(
                    onPressed: () => Navigator.of(sCtx).pop(),
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF2563EB),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                    child: const Text(
                      'Done',
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _credentialRow(
    BuildContext context,
    String label,
    String value,
  ) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: const Color(0xFFF7F9FC),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: const Color(0xFFE7EBF2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 9,
              color: Color(0xFF94A3B8),
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          SelectableText(
            value.isNotEmpty ? value : '—',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w900,
              color: Color(0xFF172033),
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // EMPTY / ERROR STATES
  // ============================================================

  Widget _buildErrorBanner(
    String message,
    VoidCallback retry,
  ) {
    return Container(
      margin: const EdgeInsets.fromLTRB(
        20,
        0,
        20,
        10,
      ),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF1F2),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: const Color(0xFFFECACA),
        ),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.error_outline_rounded,
            color: Color(0xFFDC2626),
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 10,
                color: Color(0xFFB91C1C),
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          TextButton(
            onPressed: retry,
            child: const Text(
              'Retry',
              style: TextStyle(
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCenteredError(
    String message,
    VoidCallback retry,
  ) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 70,
              height: 70,
              decoration: BoxDecoration(
                color: const Color(0xFFFFF1F2),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.cloud_off_rounded,
                color: Color(0xFFDC2626),
                size: 31,
              ),
            ),
            const SizedBox(height: 15),
            const Text(
              'Something went wrong',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 7),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 11,
                color: Color(0xFF94A3B8),
              ),
            ),
            const SizedBox(height: 17),
            FilledButton.icon(
              onPressed: retry,
              icon: const Icon(
                Icons.refresh_rounded,
                size: 17,
              ),
              label: const Text('Try Again'),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF2563EB),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyClassState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _emptyIcon(Icons.school_outlined),
            const SizedBox(height: 18),
            const Text(
              'No Students in This Class',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: Color(0xFF172033),
              ),
            ),
            const SizedBox(height: 7),
            const Text(
              'This class currently has no enrolled students. Try selecting another class.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 11,
                height: 1.5,
                color: Color(0xFF94A3B8),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNoStudentsState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _emptyIcon(Icons.groups_outlined),
            const SizedBox(height: 18),
            const Text(
              'No Students Found',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 7),
            const Text(
              'No students are currently assigned or loaded.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 11,
                color: Color(0xFF94A3B8),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNoSalaryState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _emptyIcon(Icons.payments_outlined),
            const SizedBox(height: 18),
            const Text(
              'No Salary Data',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 7),
            const Text(
              'No salary records are available for this year.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 11,
                color: Color(0xFF94A3B8),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _emptyIcon(IconData icon) {
    return Container(
      width: 82,
      height: 82,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            Color(0xFFEFF5FF),
            Color(0xFFE8EDFF),
          ],
        ),
        shape: BoxShape.circle,
      ),
      child: Icon(
        icon,
        size: 37,
        color: const Color(0xFF4F67B9),
      ),
    );
  }
}

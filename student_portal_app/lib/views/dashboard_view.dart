import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import '../controllers/student_controller.dart';
import '../utils/formatters.dart';
import '../widgets/student_avatar.dart';

class DashboardView extends StatelessWidget {
  const DashboardView({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final studentCtrl = context.watch<StudentController>();
    final profile = studentCtrl.profile;
    final attendance = studentCtrl.attendanceData;
    final fees = studentCtrl.feeData;

    return RefreshIndicator(
      onRefresh: () async {
        await studentCtrl.fetchAllData();
      },
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Student Profile Welcome Header Banner
            Card(
              elevation: 4,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              color: theme.colorScheme.primary,
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: Row(
                  children: [
                    // Photo falls back to a placeholder icon when missing or
                    // when the network image fails to load.
                    StudentAvatar(
                      imageUrl: profile?.photoUrl,
                      radius: 36,
                      backgroundColor: theme.colorScheme.onPrimary.withValues(alpha: 0.2),
                      iconColor: theme.colorScheme.onPrimary,
                      iconSize: 40,
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Welcome Back,',
                            style: TextStyle(
                              color: theme.colorScheme.onPrimary.withValues(alpha: 0.8),
                              fontSize: 14,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            profile?.fullName ?? 'Student',
                            style: TextStyle(
                              color: theme.colorScheme.onPrimary,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 4),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: theme.colorScheme.onPrimary.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            // FittedBox: long ID/class combinations scale
                            // down inside the chip instead of overflowing
                            // the welcome banner on small screens.
                            child: FittedBox(
                              fit: BoxFit.scaleDown,
                              alignment: Alignment.centerLeft,
                              child: Text(
                                'ID: ${profile?.studentId ?? '---'} | Class: ${profile?.className ?? '---'}',
                                maxLines: 1,
                                softWrap: false,
                                style: TextStyle(
                                  color: theme.colorScheme.onPrimary,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ).animate().fadeIn(duration: 400.ms).slideY(begin: -0.1, end: 0),

            const SizedBox(height: 20),

            // Attendance & Fee Quick Overview Row
            // IntrinsicHeight + stretch keeps the Attendance and Fee Status
            // cards exactly the same height regardless of content.
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Attendance Circular Indicator Card
                  Expanded(
                  child: Card(
                    elevation: 2,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    child: Padding(
                      // Symmetric padding keeps the twin overview cards
                      // comfortable on small screens.
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 16,
                      ),
                      child: Column(
                        children: [
                          // FittedBox: the section title always renders on a
                          // single line, scaling down on narrow devices.
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            child: Text(
                              'Attendance',
                              style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                            ),
                          ),
                          const SizedBox(height: 12),
                          SizedBox(
                            height: 90,
                            width: 90,
                            child: Stack(
                              alignment: Alignment.center,
                              children: [
                                CircularProgressIndicator(
                                  value: (attendance?.attendanceRate ?? 0.0) / 100.0,
                                  strokeWidth: 8,
                                  backgroundColor: theme.colorScheme.surfaceContainerHighest,
                                  color: (attendance?.attendanceRate ?? 0) >= 75
                                      ? Colors.green
                                      : Colors.orange,
                                ),
                                Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Text(
                                      '${attendance?.attendanceRate ?? 0.0}%',
                                      style: theme.textTheme.titleMedium?.copyWith(
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    Text(
                                      'Rate',
                                      style: theme.textTheme.bodySmall?.copyWith(fontSize: 10),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                          Column(
                            children: [
                              Text(
                                '✅ Present: ${attendance?.presentCount ?? 0}',
                                style: const TextStyle(color: Colors.green, fontSize: 12, fontWeight: FontWeight.bold),
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '❌ Absent: ${attendance?.absentCount ?? 0}',
                                style: const TextStyle(color: Colors.red, fontSize: 12, fontWeight: FontWeight.bold),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ).animate().fadeIn(delay: 200.ms).scale(),
                ),

                const SizedBox(width: 12),

                // Quick Fee Status Card
                Expanded(
                  child: Card(
                    elevation: 2,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 16,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // FittedBox: the title stays on a single line on
                          // any screen width instead of wrapping/clipping.
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              'Fee Status',
                              style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                            ),
                          ),
                          const SizedBox(height: 12),
                          // Status badge – wrapped so it can scale down on
                          // very narrow cards instead of overflowing.
                          Align(
                            alignment: Alignment.centerLeft,
                            child: FittedBox(
                              fit: BoxFit.scaleDown,
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                decoration: BoxDecoration(
                                  color: (fees?.overallStatus == 'PAID')
                                      ? Colors.green.withValues(alpha: 0.15)
                                      : Colors.red.withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      (fees?.overallStatus == 'PAID')
                                          ? Icons.check_circle_rounded
                                          : Icons.pending_actions_rounded,
                                      size: 16,
                                      color: (fees?.overallStatus == 'PAID') ? Colors.green : Colors.red,
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      fees?.overallStatus ?? 'PENDING',
                                      style: TextStyle(
                                        color: (fees?.overallStatus == 'PAID') ? Colors.green : Colors.red,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 14),
                          Text(
                            'Pending Balance:',
                            style: theme.textTheme.bodySmall,
                          ),
                          // Large amount scales down instead of wrapping or
                          // breaking out of the card ("RIGHT OVERFLOWED").
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              Format.rupees(fees?.yearlyPending),
                              style: theme.textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: (fees?.yearlyPending != '0.00' && fees?.yearlyPending != '0')
                                    ? Colors.red
                                    : Colors.green,
                              ),
                            ),
                          ),
                          const Divider(height: 20),
                          // Stacked vertically inside Columns — never rigid
                          // inline rows — removing the horizontal overflow.
                          Text(
                            'Total Paid:',
                            style: theme.textTheme.bodySmall,
                          ),
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              Format.rupees(fees?.totalPaidFees),
                              style: theme.textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Colors.green,
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            'Monthly Tuition:',
                            style: theme.textTheme.bodySmall,
                          ),
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              Format.rupees(fees?.effectiveMonthlyFee),
                              maxLines: 1,
                              style: theme.textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ).animate().fadeIn(delay: 300.ms).scale(),
                ),
              ],
            ),
            ),

            const SizedBox(height: 20),

            // School Announcements / Notice Card
            Text(
              'Notice & Announcements',
              style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ).animate().fadeIn(delay: 400.ms),
            const SizedBox(height: 10),
            Card(
              elevation: 1,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primaryContainer,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.campaign_rounded, color: theme.colorScheme.primary),
                ),
                title: const Text(
                  'Academic Term Notice',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                subtitle: const Text(
                  'Monthly fees and attendance records have been updated for the current academic session. Check details in your portal.',
                ),
                trailing: const Icon(Icons.chevron_right_rounded),
              ),
            ).animate().fadeIn(delay: 500.ms).slideX(begin: 0.1, end: 0),
          ],
        ),
      ),
    );
  }
}

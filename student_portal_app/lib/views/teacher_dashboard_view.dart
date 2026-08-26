import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/auth_controller.dart';
import '../controllers/teacher_controller.dart';
import 'login_view.dart';
import 'qr_scan_view.dart';
import 'package:intl/intl.dart';

class TeacherDashboardView extends StatefulWidget {
  const TeacherDashboardView({super.key});

  @override
  State<TeacherDashboardView> createState() => _TeacherDashboardViewState();
}

class _TeacherDashboardViewState extends State<TeacherDashboardView> {
  int _currentIndex = 0;
  int _selectedSalaryYear = DateTime.now().year;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final tc = context.read<TeacherController>();
      tc.fetchAvailableClasses();
      tc.fetchTeacherAttendance();
      tc.fetchTeacherSalary(year: _selectedSalaryYear);
    });
  }

  void _onLogout() {
    context.read<TeacherController>().clearAllData();
    context.read<AuthController>().logout();
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const LoginView()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final tc = context.watch<TeacherController>();

    final screens = [
      _buildAttendanceScreen(context, tc, theme),
      _buildSalaryScreen(context, tc, theme),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Teacher Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner_rounded),
            tooltip: 'Scan Attendance QR',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const QrScanView()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _onLogout,
            tooltip: 'Logout',
          ),
        ],
      ),
      body: screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (idx) {
          setState(() {
            _currentIndex = idx;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.fact_check_outlined),
            selectedIcon: Icon(Icons.fact_check),
            label: 'Attendance',
          ),
          NavigationDestination(
            icon: Icon(Icons.payments_outlined),
            selectedIcon: Icon(Icons.payments),
            label: 'Salary',
          ),
        ],
      ),
    );
  }

  Widget _buildAttendanceScreen(BuildContext context, TeacherController tc, ThemeData theme) {
    return Column(
      children: [
        // Date Selector & Submit Button
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Expanded(
                child: InkWell(
                  onTap: () async {
                    final date = await showDatePicker(
                      context: context,
                      initialDate: tc.selectedDate,
                      firstDate: DateTime.now().subtract(const Duration(days: 365)),
                      lastDate: DateTime.now(),
                    );
                    if (date != null) {
                      tc.setSelectedDate(date);
                    }
                  },
                  child: InputDecorator(
                    decoration: InputDecoration(
                      labelText: 'Attendance Date',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(DateFormat('yyyy-MM-dd').format(tc.selectedDate)),
                        const Icon(Icons.calendar_today, size: 20),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              FilledButton.icon(
                onPressed: tc.isLoadingAttendance
                    ? null
                    : () async {
                        final success = await tc.submitAttendance();
                        if (!context.mounted) return;
                        if (success) {
                          // Clear confirmation dialog on successful submission.
                          await showDialog<void>(
                            context: context,
                            builder: (dialogContext) => AlertDialog(
                              icon: Icon(
                                Icons.check_circle_rounded,
                                color: Colors.green.shade600,
                                size: 48,
                              ),
                              title: const Text('Success'),
                              content: const Text(
                                'Attendance submitted successfully!',
                                textAlign: TextAlign.center,
                              ),
                              actionsAlignment: MainAxisAlignment.center,
                              actions: [
                                FilledButton(
                                  onPressed: () =>
                                      Navigator.of(dialogContext).pop(),
                                  child: const Text('Okay'),
                                ),
                              ],
                            ),
                          );
                          if (!context.mounted) return;
                          tc.fetchTeacherAttendance();
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                  tc.attendanceError ?? 'Failed to submit'),
                              backgroundColor: Colors.red,
                            ),
                          );
                        }
                      },
                icon: const Icon(Icons.save),
                label: const Text('Submit'),
              ),
            ],
          ),
        ),

        // Class Selector — every active school class, tap one to open it.
        if (tc.isLoadingClasses)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: LinearProgressIndicator(minHeight: 2),
          )
        else if (tc.classesError != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Row(
              children: [
                Icon(Icons.error_outline, size: 16, color: theme.colorScheme.error),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    tc.classesError!,
                    style: TextStyle(color: theme.colorScheme.error, fontSize: 12),
                  ),
                ),
                TextButton(
                  onPressed: () => tc.fetchAvailableClasses(),
                  child: const Text('Retry'),
                ),
              ],
            ),
          )
        else if (tc.availableClasses.isNotEmpty)
          SizedBox(
            height: 44,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: tc.availableClasses.length + 1,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, index) {
                // Leading "All" chip clears the filter.
                if (index == 0) {
                  final isSelected = tc.selectedClassId == null;
                  return ChoiceChip(
                    label: const Text('All Classes'),
                    selected: isSelected,
                    onSelected: (_) => tc.selectClass(null),
                  );
                }
                final schoolClass = tc.availableClasses[index - 1];
                final isSelected = tc.selectedClassId == schoolClass.id;
                return ChoiceChip(
                  label: Text('${schoolClass.name} (${schoolClass.studentCount})'),
                  selected: isSelected,
                  onSelected: (_) => tc.selectClass(schoolClass.id),
                );
              },
            ),
          ),

        // Today's class-wise attendance summary (live counts).
        _buildClassSummaryCard(tc, theme),

        // Roster List
        Expanded(
          child: tc.isLoadingAttendance
              ? const Center(child: CircularProgressIndicator())
              : tc.attendanceError != null
                  ? Center(child: Text(tc.attendanceError!, style: TextStyle(color: theme.colorScheme.error)))
                  : tc.selectedClassIsEmpty
                      ? _buildEmptyClassState(theme)
                      : tc.attendanceRoster.isEmpty
                          ? const Center(child: Text('No students assigned or loaded.'))
                          : ListView.builder(
                          itemCount: tc.attendanceRoster.length,
                          itemBuilder: (context, index) {
                            final student = tc.attendanceRoster[index];
                            final currentStatus = tc.attendanceSubmissions[student.id.toString()] ?? student.status;
                            return Card(
                              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                              child: ListTile(
                                leading: CircleAvatar(
                                  child: Text(student.name.isNotEmpty ? student.name[0] : '?'),
                                ),
                                title: Text(
                                  student.name,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                subtitle: Text(
                                  '${student.studentId} • ${student.schoolClassName}',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                // FittedBox guarantees the three toggles can
                                // never trigger a RenderFlex overflow on
                                // narrow screens — they shrink instead.
                                trailing: FittedBox(
                                  fit: BoxFit.scaleDown,
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      _statusChip(
                                        tc,
                                        student.id,
                                        label: 'P',
                                        value: 'PRESENT',
                                        currentStatus: currentStatus,
                                        activeColor: Colors.green,
                                      ),
                                      const SizedBox(width: 6),
                                      _statusChip(
                                        tc,
                                        student.id,
                                        label: 'A',
                                        value: 'ABSENT',
                                        currentStatus: currentStatus,
                                        activeColor: Colors.red,
                                      ),
                                      const SizedBox(width: 6),
                                      _statusChip(
                                        tc,
                                        student.id,
                                        label: 'L',
                                        value: 'LEAVE',
                                        currentStatus: currentStatus,
                                        activeColor: Colors.orange,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
        ),
      ],
    );
  }

  /// Friendly empty state shown when the opened class has no enrolled students.
  Widget _buildEmptyClassState(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.school_outlined,
              size: 56,
              color: theme.colorScheme.outlineVariant,
            ),
            const SizedBox(height: 12),
            Text(
              'Is class mein filhal koi student enrolled nahi hai.',
              textAlign: TextAlign.center,
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Please select another class from the list above.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Compact Present/Absent/Leave toggle for one student.
  Widget _statusChip(
    TeacherController tc,
    int studentId, {
    required String label,
    required String value,
    required String currentStatus,
    required MaterialColor activeColor,
  }) {
    return ChoiceChip(
      label: Text(label),
      selected: currentStatus == value,
      selectedColor: activeColor.withValues(alpha: 0.35),
      labelStyle: TextStyle(
        fontWeight: FontWeight.bold,
        color: currentStatus == value ? activeColor.shade900 : null,
      ),
      visualDensity: VisualDensity.compact,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      onSelected: (val) {
        if (val) tc.updateAttendanceStatus(studentId, value);
      },
    );
  }

  /// Today's quick stats card for the currently open class roster:
  /// Total / Present / Absent / Leave — updates live as statuses toggle.
  Widget _buildClassSummaryCard(TeacherController tc, ThemeData theme) {
    Widget stat(String label, String value, Color color) => Expanded(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                value,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
            ],
          ),
        );

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 4, 16, 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Row(
        children: [
          stat('Total', '${tc.totalStudents}', theme.colorScheme.primary),
          stat('Present', '${tc.presentCount}', Colors.green.shade700),
          stat('Absent', '${tc.absentCount}', Colors.red.shade700),
          stat('Leave', '${tc.leaveCount}', Colors.orange.shade800),
        ],
      ),
    );
  }

  Widget _buildSalaryScreen(BuildContext context, TeacherController tc, ThemeData theme) {
    final currentYear = DateTime.now().year;
    final availableYears = [currentYear + 1, currentYear, currentYear - 1, currentYear - 2];

    return Column(
      children: [
        // Year Filter Header Row
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Salary Records',
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                decoration: BoxDecoration(
                  border: Border.all(color: theme.colorScheme.outlineVariant),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<int>(
                    value: _selectedSalaryYear,
                    isDense: true,
                    icon: const Icon(Icons.arrow_drop_down),
                    items: availableYears.map((y) {
                      return DropdownMenuItem<int>(
                        value: y,
                        child: Text('Year $y', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                      );
                    }).toList(),
                    onChanged: (newYear) {
                      if (newYear != null && newYear != _selectedSalaryYear) {
                        setState(() {
                          _selectedSalaryYear = newYear;
                        });
                        tc.fetchTeacherSalary(year: newYear);
                      }
                    },
                  ),
                ),
              ),
            ],
          ),
        ),

        // Body Content
        Expanded(
          child: tc.isLoadingSalary
              ? const Center(child: CircularProgressIndicator())
              : tc.salaryError != null
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(tc.salaryError!, style: TextStyle(color: theme.colorScheme.error)),
                          const SizedBox(height: 16),
                          ElevatedButton(
                            onPressed: () => tc.fetchTeacherSalary(year: _selectedSalaryYear),
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    )
                  : tc.salaryData == null
                      ? const Center(child: Text('No salary data available.'))
                      : _buildSalaryDetails(tc.salaryData!, theme),
        ),
      ],
    );
  }

  Widget _buildSalaryDetails(dynamic data, ThemeData theme) {
    final paidCount = (data.monthlyStatuses as List).where((m) => m.isPaid).length;
    final totalCount = (data.monthlyStatuses as List).length;

    return SingleChildScrollView(
      child: Column(
        children: [
          // Teacher Profile & Summary Header Card
          Container(
            width: double.infinity,
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            padding: const EdgeInsets.all(16.0),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  theme.colorScheme.primaryContainer.withValues(alpha: 0.8),
                  theme.colorScheme.primaryContainer.withValues(alpha: 0.4),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: theme.colorScheme.primary.withValues(alpha: 0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    // Expanded keeps long teacher names from overflowing.
                    Expanded(
                      child: Text(
                        data.name.toString().isNotEmpty ? data.name.toString() : 'Teacher',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (data.teacherId.toString().isNotEmpty)
                      Chip(
                        label: Text(
                          data.teacherId.toString(),
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                        ),
                        visualDensity: VisualDensity.compact,
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Base Monthly Salary', style: theme.textTheme.bodySmall),
                          Text('Rs ${data.monthlySalary}', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold, color: Colors.green.shade800)),
                        ],
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Yearly Salary', style: theme.textTheme.bodySmall),
                          Text('Rs ${data.yearlySalary}', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                  ],
                ),
                const Divider(height: 20),
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        'Disbursements for Year $_selectedSalaryYear:',
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                        style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '$paidCount of $totalCount Paid',
                      style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green.shade800),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Monthly Breakdown Cards
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: data.monthlyStatuses.length,
            itemBuilder: (context, index) {
              final m = data.monthlyStatuses[index];
              final isPaid = m.isPaid;
              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
                shape: RoundedRectangleBorder(
                  side: BorderSide(
                    color: isPaid ? Colors.green.withValues(alpha: 0.5) : Colors.orange.withValues(alpha: 0.5),
                    width: 1.2,
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: isPaid ? Colors.green.shade50 : Colors.orange.shade50,
                    child: Icon(
                      isPaid ? Icons.check_circle : Icons.pending,
                      color: isPaid ? Colors.green.shade700 : Colors.orange.shade700,
                      size: 22,
                    ),
                  ),
                  title: Text(m.monthName, style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text(
                    isPaid && m.paymentDate != null
                        ? 'Paid on ${m.paymentDate} • Rs ${m.amount}'
                        : 'Amount: Rs ${m.amount} (Pending)',
                  ),
                  trailing: Chip(
                    label: Text(
                      m.status,
                      style: TextStyle(
                        color: isPaid ? Colors.green.shade900 : Colors.orange.shade900,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                    backgroundColor: isPaid ? Colors.green.shade100 : Colors.orange.shade100,
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}

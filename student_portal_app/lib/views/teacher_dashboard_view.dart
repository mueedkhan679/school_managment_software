import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/auth_controller.dart';
import '../controllers/teacher_controller.dart';
import 'login_view.dart';
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
      tc.fetchTeacherAttendance();
      tc.fetchTeacherSalary(year: _selectedSalaryYear);
    });
  }

  void _onLogout() {
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
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(success ? 'Attendance submitted successfully' : (tc.attendanceError ?? 'Failed to submit')),
                            backgroundColor: success ? Colors.green : Colors.red,
                          ),
                        );
                      },
                icon: const Icon(Icons.save),
                label: const Text('Submit'),
              ),
            ],
          ),
        ),

        // Roster List
        Expanded(
          child: tc.isLoadingAttendance
              ? const Center(child: CircularProgressIndicator())
              : tc.attendanceError != null
                  ? Center(child: Text(tc.attendanceError!, style: TextStyle(color: theme.colorScheme.error)))
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
                                title: Text(student.name),
                                subtitle: Text('${student.studentId} • ${student.schoolClassName}'),
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    ChoiceChip(
                                      label: const Text('P'),
                                      selected: currentStatus == 'PRESENT',
                                      selectedColor: Colors.green.withValues(alpha: 0.3),
                                      onSelected: (val) {
                                        if (val) tc.updateAttendanceStatus(student.id, 'PRESENT');
                                      },
                                    ),
                                    const SizedBox(width: 8),
                                    ChoiceChip(
                                      label: const Text('A'),
                                      selected: currentStatus == 'ABSENT',
                                      selectedColor: Colors.red.withValues(alpha: 0.3),
                                      onSelected: (val) {
                                        if (val) tc.updateAttendanceStatus(student.id, 'ABSENT');
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
        ),
      ],
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
                  children: [
                    Text(
                      data.name.toString().isNotEmpty ? data.name.toString() : 'Teacher',
                      style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                    ),
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
                    Text(
                      'Disbursements for Year $_selectedSalaryYear: ',
                      style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600),
                    ),
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

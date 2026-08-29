import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import 'package:table_calendar/table_calendar.dart';
import '../controllers/student_controller.dart';
import '../models/attendance_model.dart';

class AttendanceView extends StatefulWidget {
  const AttendanceView({super.key});

  @override
  State<AttendanceView> createState() => _AttendanceViewState();
}

class _AttendanceViewState extends State<AttendanceView> {
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final studentCtrl = context.watch<StudentController>();
    final attendanceData = studentCtrl.attendanceData;
    final records = attendanceData?.results ?? [];

    // Map records by DateTime key for calendar highlighting
    final Map<DateTime, AttendanceRecord> recordMap = {};
    for (var r in records) {
      try {
        final dt = DateTime.parse(r.date);
        final dateKey = DateTime(dt.year, dt.month, dt.day);
        recordMap[dateKey] = r;
      } catch (_) {}
    }

    return RefreshIndicator(
      onRefresh: () async {
        await studentCtrl.fetchAttendance();
      },
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Stats summary banner
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildStatColumn('Total Days', '${attendanceData?.totalDays ?? 0}', theme.colorScheme.primary),
                    _buildStatColumn('Present', '${attendanceData?.presentCount ?? 0}', Colors.green),
                    _buildStatColumn('Absent', '${attendanceData?.absentCount ?? 0}', Colors.red),
                    _buildStatColumn('Rate', '${attendanceData?.attendanceRate ?? 0}%', Colors.orange),
                  ],
                ),
              ),
            ).animate().fadeIn().scale(),

            const SizedBox(height: 16),

            // Interactive Calendar View
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: TableCalendar(
                  firstDay: DateTime.utc(2020, 1, 1),
                  lastDay: DateTime.utc(2030, 12, 31),
                  focusedDay: _focusedDay,
                  selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
                  onDaySelected: (selectedDay, focusedDay) {
                    setState(() {
                      _selectedDay = selectedDay;
                      _focusedDay = focusedDay;
                    });
                  },
                  onPageChanged: (focusedDay) {
                    _focusedDay = focusedDay;
                    studentCtrl.fetchAttendance(month: focusedDay.month, year: focusedDay.year);
                  },
                  calendarBuilders: CalendarBuilders(
                    markerBuilder: (context, date, events) {
                      final dayKey = DateTime(date.year, date.month, date.day);
                      final record = recordMap[dayKey];
                      if (record != null) {
                        final isPresent = record.status.toUpperCase() == 'PRESENT';
                        return Positioned(
                          bottom: 2,
                          child: Container(
                            width: 7,
                            height: 7,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: isPresent ? Colors.green : Colors.red,
                            ),
                          ),
                        );
                      }
                      return null;
                    },
                  ),
                  calendarStyle: CalendarStyle(
                    todayDecoration: BoxDecoration(
                      color: theme.colorScheme.primary.withValues(alpha: 0.5),
                      shape: BoxShape.circle,
                    ),
                    selectedDecoration: BoxDecoration(
                      color: theme.colorScheme.primary,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              ),
            ).animate().fadeIn(delay: 200.ms),

            const SizedBox(height: 20),

            // Log Header
            Text(
              'Attendance History',
              style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),

            if (studentCtrl.isLoadingAttendance)
              const Padding(
                padding: EdgeInsets.all(24.0),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (records.isEmpty)
              const Padding(
                padding: EdgeInsets.all(24.0),
                child: Center(child: Text('No attendance records found.')),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: records.length,
                itemBuilder: (context, index) {
                  final item = records[index];
                  final isPresent = item.status.toUpperCase() == 'PRESENT';

                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: isPresent ? Colors.green.withValues(alpha: 0.15) : Colors.red.withValues(alpha: 0.15),
                        child: Icon(
                          isPresent ? Icons.check_circle_rounded : Icons.cancel_rounded,
                          color: isPresent ? Colors.green : Colors.red,
                        ),
                      ),
                      title: Text(
                        item.date,
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      subtitle: Text('Marked by: ${item.markedByName}'),
                      trailing: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: isPresent ? Colors.green.withValues(alpha: 0.15) : Colors.red.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          item.statusDisplay,
                          style: TextStyle(
                            color: isPresent ? Colors.green : Colors.red,
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                  ).animate().fadeIn(delay: Duration(milliseconds: 100 * (index % 5)));
                },
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatColumn(String label, String value, Color color) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: Colors.grey),
        ),
      ],
    );
  }
}

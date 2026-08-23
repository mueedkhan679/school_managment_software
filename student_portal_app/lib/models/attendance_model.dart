class AttendanceRecord {
  final int id;
  final String date;
  final String status;
  final String statusDisplay;
  final String markedByName;

  AttendanceRecord({
    required this.id,
    required this.date,
    required this.status,
    required this.statusDisplay,
    required this.markedByName,
  });

  factory AttendanceRecord.fromJson(Map<String, dynamic> json) {
    return AttendanceRecord(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      date: json['date']?.toString() ?? '',
      status: json['status']?.toString() ?? 'PRESENT',
      statusDisplay: json['status_display']?.toString() ?? 'Present',
      markedByName: json['marked_by_name']?.toString() ?? '',
    );
  }
}

class AttendanceData {
  final int totalDays;
  final int presentCount;
  final int absentCount;
  final double attendanceRate;
  final int count;
  final String? next;
  final String? previous;
  final List<AttendanceRecord> results;

  AttendanceData({
    required this.totalDays,
    required this.presentCount,
    required this.absentCount,
    required this.attendanceRate,
    required this.count,
    this.next,
    this.previous,
    required this.results,
  });

  factory AttendanceData.fromJson(Map<String, dynamic> json) {
    final list = (json['results'] ?? json['attendance_records'] ?? json['records']) as List? ?? [];
    return AttendanceData(
      totalDays: int.tryParse(json['total_days']?.toString() ?? '') ?? 0,
      presentCount: int.tryParse(json['present_count']?.toString() ?? json['present']?.toString() ?? '') ?? 0,
      absentCount: int.tryParse(json['absent_count']?.toString() ?? json['absent']?.toString() ?? '') ?? 0,
      attendanceRate: double.tryParse(
        json['attendance_rate']?.toString() ??
        json['attendance_percentage']?.toString() ??
        json['percentage']?.toString() ??
        '0',
      ) ?? 0.0,
      count: int.tryParse(json['count']?.toString() ?? '') ?? 0,
      next: json['next']?.toString(),
      previous: json['previous']?.toString(),
      results: list.map((item) => AttendanceRecord.fromJson(item as Map<String, dynamic>)).toList(),
    );
  }
}

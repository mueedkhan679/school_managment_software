class TeacherAttendanceStudent {
  final int id;
  final String studentId;
  final String name;
  final String dateOfBirth;
  final String genderDisplay;
  final String schoolClassName;
  final String status;
  final bool isMarked;

  TeacherAttendanceStudent({
    required this.id,
    required this.studentId,
    required this.name,
    required this.dateOfBirth,
    required this.genderDisplay,
    required this.schoolClassName,
    required this.status,
    required this.isMarked,
  });

  factory TeacherAttendanceStudent.fromJson(Map<String, dynamic> json) {
    return TeacherAttendanceStudent(
      id: json['id'] as int? ?? 0,
      studentId: json['student_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      dateOfBirth: json['date_of_birth']?.toString() ?? '',
      genderDisplay: json['gender_display']?.toString() ?? '',
      schoolClassName: json['school_class_name']?.toString() ?? '',
      status: json['status']?.toString() ?? 'PRESENT',
      isMarked: json['is_marked'] as bool? ?? false,
    );
  }

  bool get isPresent => status == 'PRESENT';
  bool get isAbsent => status == 'ABSENT';
}

class TeacherSalaryMonth {
  final int monthNum;
  final String monthName;
  final String amount;
  final String status;
  final String? paymentDate;

  TeacherSalaryMonth({
    required this.monthNum,
    required this.monthName,
    required this.amount,
    required this.status,
    this.paymentDate,
  });

  factory TeacherSalaryMonth.fromJson(Map<String, dynamic> json) {
    final monthNum = json['month_num'] as int? ?? 1;
    return TeacherSalaryMonth(
      monthNum: monthNum,
      monthName: json['month_name']?.toString() ?? _monthName(monthNum),
      amount: json['amount']?.toString() ?? '0.00',
      status: json['status']?.toString() ?? 'PENDING',
      paymentDate: json['payment_date']?.toString(),
    );
  }

  static String _monthName(int num) {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December',
    ];
    final idx = (num - 1).clamp(0, months.length - 1);
    return months[idx];
  }

  bool get isPaid => status == 'PAID';
  bool get isPending => status == 'PENDING';
}

class TeacherSalaryData {
  final String teacherId;
  final String name;
  final String monthlySalary;
  final String yearlySalary;
  final List<TeacherSalaryMonth> monthlyStatuses;

  TeacherSalaryData({
    required this.teacherId,
    required this.name,
    required this.monthlySalary,
    required this.yearlySalary,
    required this.monthlyStatuses,
  });

  factory TeacherSalaryData.fromJson(Map<String, dynamic> json) {
    final statuses = (json['monthly_statuses'] as List? ?? [])
        .map((e) => TeacherSalaryMonth.fromJson(e as Map<String, dynamic>))
        .toList();
    return TeacherSalaryData(
      teacherId: json['teacher_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      monthlySalary: json['monthly_salary']?.toString() ?? '0.00',
      yearlySalary: json['yearly_salary']?.toString() ?? '0.00',
      monthlyStatuses: statuses,
    );
  }
}

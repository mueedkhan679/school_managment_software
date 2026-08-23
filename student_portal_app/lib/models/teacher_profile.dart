
class TeacherProfile {
  final int id;
  final String teacherId;
  final String name;
  final String phone;
  final String address;
  final String? photoUrl;
  final String monthlySalary;
  final String yearlySalary;
  final List<TeacherClass> assignedClasses;

  TeacherProfile({
    required this.id,
    required this.teacherId,
    required this.name,
    required this.phone,
    required this.address,
    this.photoUrl,
    required this.monthlySalary,
    required this.yearlySalary,
    required this.assignedClasses,
  });

  String get displayName => name.isNotEmpty ? name : (teacherId.isNotEmpty ? teacherId : 'Teacher');
}

class TeacherClass {
  final int id;
  final String name;

  TeacherClass({required this.id, required this.name});

  factory TeacherClass.fromJson(Map<String, dynamic> json) {
    return TeacherClass(
      id: json['id'] as int? ?? 0,
      name: json['name']?.toString() ?? '',
    );
  }
}

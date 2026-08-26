
class TeacherProfile {
  final int id;
  final String teacherId;
  final String name;
  final String designation;
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
    this.designation = 'Teacher',
    required this.phone,
    required this.address,
    this.photoUrl,
    required this.monthlySalary,
    required this.yearlySalary,
    required this.assignedClasses,
  });

  String get displayName => name.isNotEmpty ? name : (teacherId.isNotEmpty ? teacherId : 'Teacher');

  /// Builds a profile from GET /api/v1/teacher/profile/ (Digital ID Card data).
  factory TeacherProfile.fromProfileApi(Map<String, dynamic> json) {
    return TeacherProfile(
      id: json['id'] as int? ?? 0,
      teacherId: json['teacher_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      designation: json['designation']?.toString() ?? 'Teacher',
      phone: json['phone']?.toString() ?? '',
      address: json['address']?.toString() ?? '',
      photoUrl: json['photo_url']?.toString(),
      monthlySalary: '0.00',
      yearlySalary: '0.00',
      assignedClasses: (json['assigned_classes'] as List? ?? [])
          .map((e) => TeacherClass.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
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

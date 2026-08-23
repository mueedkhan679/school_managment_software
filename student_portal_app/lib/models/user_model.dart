class UserSession {
  final String accessToken;
  final String refreshToken;
  final int userId;
  final String username;
  final String role;
  final String studentId;
  final String studentName;
  final String teacherId;
  final String teacherName;

  UserSession({
    required this.accessToken,
    required this.refreshToken,
    required this.userId,
    required this.username,
    required this.role,
    required this.studentId,
    required this.studentName,
    this.teacherId = '',
    this.teacherName = '',
  });

  factory UserSession.fromJson(Map<String, dynamic> json) {
    final user = json['user'] as Map<String, dynamic>? ?? {};
    return UserSession(
      accessToken: json['access'] as String? ?? '',
      refreshToken: json['refresh'] as String? ?? '',
      userId: user['id'] as int? ?? 0,
      username: user['username'] as String? ?? '',
      role: user['role'] as String? ?? 'STUDENT',
      studentId: user['student_id'] as String? ?? '',
      studentName: user['student_name'] as String? ?? '',
      teacherId: user['teacher_id'] as String? ?? '',
      teacherName: user['teacher_name'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'access': accessToken,
      'refresh': refreshToken,
      'user': {
        'id': userId,
        'username': username,
        'role': role,
        'student_id': studentId,
        'student_name': studentName,
        'teacher_id': teacherId,
        'teacher_name': teacherName,
      },
    };
  }
}


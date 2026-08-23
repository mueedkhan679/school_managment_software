import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class StorageService {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

    static const String _keyAccessToken = 'access_token';
  static const String _keyRefreshToken = 'refresh_token';
  static const String _keyStudentId = 'student_id';
  static const String _keyStudentName = 'student_name';
  static const String _keyTeacherId = 'teacher_id';
  static const String _keyTeacherName = 'teacher_name';
  static const String _keyRole = 'role';
  static const String _keyRememberMe = 'remember_me';

  static const String _keySessionCookie = 'session_cookie';

  Future<void> saveTokens({required String access, required String refresh}) async {
    await _storage.write(key: _keyAccessToken, value: access);
    await _storage.write(key: _keyRefreshToken, value: refresh);
  }

  Future<void> saveSessionCookie(String cookie) async {
    await _storage.write(key: _keySessionCookie, value: cookie);
  }

  Future<String?> getSessionCookie() async {
    return await _storage.read(key: _keySessionCookie);
  }

  Future<String?> getAccessToken() async {
    return await _storage.read(key: _keyAccessToken);
  }

  Future<String?> getRefreshToken() async {
    return await _storage.read(key: _keyRefreshToken);
  }

    Future<void> saveStudentInfo({
    required String studentId,
    required String name,
    String role = 'STUDENT',
    String? teacherId,
    String? teacherName,
  }) async {
    await _storage.write(key: _keyStudentId, value: studentId);
    await _storage.write(key: _keyStudentName, value: name);
    await _storage.write(key: _keyRole, value: role);
    if (teacherId != null) {
      await _storage.write(key: _keyTeacherId, value: teacherId);
    }
    if (teacherName != null) {
      await _storage.write(key: _keyTeacherName, value: teacherName);
    }
  }

  Future<Map<String, String?>> getStudentInfo() async {
    final studentId = await _storage.read(key: _keyStudentId);
    final name = await _storage.read(key: _keyStudentName);
    final role = await _storage.read(key: _keyRole);
    final teacherId = await _storage.read(key: _keyTeacherId);
    final teacherName = await _storage.read(key: _keyTeacherName);
    return {
      'student_id': studentId,
      'name': name,
      'role': role ?? 'STUDENT',
      'teacher_id': teacherId,
      'teacher_name': teacherName,
    };
  }

  Future<void> setRememberMe(bool value) async {
    await _storage.write(key: _keyRememberMe, value: value.toString());
  }

  Future<bool> getRememberMe() async {
    final val = await _storage.read(key: _keyRememberMe);
    return val == 'true';
  }

  Future<void> clearAll() async {
    await _storage.delete(key: _keyAccessToken);
    await _storage.delete(key: _keyRefreshToken);
    await _storage.delete(key: _keyStudentId);
    await _storage.delete(key: _keyStudentName);
    await _storage.delete(key: _keyTeacherId);
    await _storage.delete(key: _keyTeacherName);
    await _storage.delete(key: _keyRole);
    await _storage.delete(key: _keySessionCookie);
    await _storage.deleteAll(); // Fallback to wipe any remaining keys
  }
}

import 'package:flutter/material.dart';
import '../models/teacher_attendance_model.dart';
import '../models/teacher_profile.dart';
import '../models/teacher_scan_result.dart';
import '../models/user_model.dart';
import '../services/api_service.dart';

/// A school class shown on the teacher's attendance screen.
class TeacherAvailableClass {
  final int id;
  final String name;
  final int studentCount;

  TeacherAvailableClass({
    required this.id,
    required this.name,
    required this.studentCount,
  });

  factory TeacherAvailableClass.fromJson(Map<String, dynamic> json) {
    return TeacherAvailableClass(
      id: json['id'] as int? ?? 0,
      name: json['name']?.toString() ?? '',
      studentCount: (json['student_count'] as num?)?.toInt() ?? 0,
    );
  }
}

class TeacherController extends ChangeNotifier {
  final ApiService _apiService = ApiService();

  TeacherProfile? _profile;
  final bool _isLoadingProfile = false;
  String? _profileError;

  List<TeacherAttendanceStudent> _attendanceRoster = [];
  bool _isLoadingAttendance = false;
  String? _attendanceError;
  DateTime _selectedDate = DateTime.now();

  // All school classes the teacher can pick from.
  List<TeacherAvailableClass> _availableClasses = [];
  bool _isLoadingClasses = false;
  String? _classesError;
  int? _selectedClassId;

  TeacherSalaryData? _salaryData;
  bool _isLoadingSalary = false;
  String? _salaryError;

  bool _isScanningSelf = false;
  String? _selfScanMessage;
  TeacherScanResult _selfScan = const TeacherScanResult(
    success: false,
    duplicate: false,
    message: '',
  );

  // In-progress attendance submissions (studentId -> status)
  final Map<String, String> _attendanceSubmissions = {};

  TeacherProfile? get profile => _profile;
  bool get isLoadingProfile => _isLoadingProfile;
  String? get profileError => _profileError;

  List<TeacherAttendanceStudent> get attendanceRoster => _attendanceRoster;
  bool get isLoadingAttendance => _isLoadingAttendance;
  String? get attendanceError => _attendanceError;
  DateTime get selectedDate => _selectedDate;
  Map<String, String> get attendanceSubmissions => Map.unmodifiable(_attendanceSubmissions);

  List<TeacherAvailableClass> get availableClasses => _availableClasses;
  bool get isLoadingClasses => _isLoadingClasses;
  String? get classesError => _classesError;
  int? get selectedClassId => _selectedClassId;

  /// The currently selected class object, or null when "All classes".
  TeacherAvailableClass? get selectedClass {
    if (_selectedClassId == null) return null;
    for (final c in _availableClasses) {
      if (c.id == _selectedClassId) return c;
    }
    return null;
  }

  /// True when a class is selected and it has no enrolled students.
  bool get selectedClassIsEmpty =>
      _selectedClassId != null && !_isLoadingAttendance && _attendanceRoster.isEmpty;

  TeacherSalaryData? get salaryData => _salaryData;
  bool get isLoadingSalary => _isLoadingSalary;
  String? get salaryError => _salaryError;

  bool get isScanningSelf => _isScanningSelf;
  String? get selfScanMessage => _selfScanMessage;
  TeacherScanResult get selfScan => _selfScan;

  /// Sends a scanned dashboard QR token to check this teacher in as Present.
  ///
  /// Returns `true` when the backend reports success (including the
  /// idempotent "Attendance Already Marked" case). The full result — teacher
  /// details, photo, check-in time and duplicate flag — is exposed via
  /// [selfScan] and [selfScanMessage].
  Future<bool> markOwnAttendanceViaQr(String token) async {
    _isScanningSelf = true;
    notifyListeners();

    final res = await _apiService.scanTeacherAttendance(token);
    final ok = res['status'] == 'success';
    _selfScan = TeacherScanResult.fromResponse(res);
    _isScanningSelf = false;
    _selfScanMessage = _selfScan.message.isNotEmpty
        ? _selfScan.message
        : (res['message'] ?? (ok ? 'Attendance marked.' : 'Scan failed.'))
            .toString();
    notifyListeners();
    return ok;
  }

  void clearSelfScanMessage() {
    _selfScanMessage = null;
    _selfScan = const TeacherScanResult(
      success: false,
      duplicate: false,
      message: '',
    );
    notifyListeners();
  }

  void clearAllData() {
    _profile = null;
    _attendanceRoster = [];
    _attendanceSubmissions.clear();
    _salaryData = null;
    _attendanceError = null;
    _salaryError = null;
    _availableClasses = [];
    _classesError = null;
    _selectedClassId = null;
    notifyListeners();
  }

  void setProfileFromSession(UserSession session) {
    // Session is typically a UserSession object containing teacherId, teacherName, etc.
    _profile = TeacherProfile(
      id: 0,
      teacherId: session.teacherId,
      name: session.teacherName.isNotEmpty ? session.teacherName : session.studentName,
      phone: '',
      address: '',
      monthlySalary: '0.00',
      yearlySalary: '0.00',
      assignedClasses: [],
    );
    notifyListeners();
  }

  /// Loads every active school class so the teacher can pick any of them.
  Future<void> fetchAvailableClasses() async {
    _isLoadingClasses = true;
    _classesError = null;
    notifyListeners();

    final res = await _apiService.getTeacherClasses();
    if (res['status'] == 'error') {
      _classesError = res['message'] ?? 'Failed to load classes';
      _availableClasses = [];
    } else {
      final payload = res['payload'] != null
          ? res['payload'] as Map<String, dynamic>
          : <String, dynamic>{};
      final classList = payload['classes'] as List? ?? [];
      _availableClasses = classList
          .map((e) => TeacherAvailableClass.fromJson(e as Map<String, dynamic>))
          .toList();
      // Drop the selection if the chosen class no longer exists.
      if (_selectedClassId != null &&
          !_availableClasses.any((c) => c.id == _selectedClassId)) {
        _selectedClassId = null;
      }
    }
    _isLoadingClasses = false;
    notifyListeners();
  }

  /// Picks a class (null = all students from every class) and reloads its roster.
  void selectClass(int? classId) {
    if (_selectedClassId == classId) return;
    _selectedClassId = classId;
    notifyListeners();
    fetchTeacherAttendance(classId: classId);
  }

  String get _formattedSelectedDate {
    final d = _selectedDate.toLocal();
    final mm = d.month.toString().padLeft(2, '0');
    final dd = d.day.toString().padLeft(2, '0');
    return '${d.year}-$mm-$dd';
  }

  Future<void> fetchTeacherAttendance({DateTime? date, int? classId}) async {
    _isLoadingAttendance = true;
    _attendanceError = null;
    if (date != null) _selectedDate = date;

    final effectiveClassId = classId ?? _selectedClassId;
    final dateStr = _formattedSelectedDate;
    notifyListeners();

    final res = await _apiService.getTeacherAttendance(
      date: dateStr,
      classId: effectiveClassId,
    );
    if (res['status'] == 'error') {
      _attendanceError = res['message'] ?? 'Failed to load attendance roster';
      _attendanceRoster = [];
    } else {
      final payload = res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
      final rosterList = payload['roster'] as List? ?? [];
      // Keep any classes list returned inline in sync (defensive; the
      // dedicated /teacher/classes/ endpoint is normally used instead).
      if (effectiveClassId == null &&
          _availableClasses.isEmpty &&
          payload['classes'] is List) {
        _availableClasses = (payload['classes'] as List)
            .map((e) => TeacherAvailableClass.fromJson(e as Map<String, dynamic>))
            .toList();
      }
      _attendanceRoster = rosterList
          .map((e) => TeacherAttendanceStudent.fromJson(e as Map<String, dynamic>))
          .toList();
      // Initialize submissions from loaded data
      _attendanceSubmissions.clear();
      for (final student in _attendanceRoster) {
        _attendanceSubmissions[student.id.toString()] = student.status;
      }
    }
    _isLoadingAttendance = false;
    notifyListeners();
  }

  void setSelectedDate(DateTime date) {
    _selectedDate = date;
    fetchTeacherAttendance(date: date);
  }

  void updateAttendanceStatus(int id, String status) {
    _attendanceSubmissions[id.toString()] = status;
    // Update the UI roster in-memory
    for (int i = 0; i < _attendanceRoster.length; i++) {
      if (_attendanceRoster[i].id == id) {
        _attendanceRoster[i] = TeacherAttendanceStudent(
          id: _attendanceRoster[i].id,
          studentId: _attendanceRoster[i].studentId,
          name: _attendanceRoster[i].name,
          dateOfBirth: _attendanceRoster[i].dateOfBirth,
          genderDisplay: _attendanceRoster[i].genderDisplay,
          schoolClassName: _attendanceRoster[i].schoolClassName,
          status: status,
        );
      }
    }
    notifyListeners();
  }

  Future<bool> submitAttendance() async {
    if (_attendanceRoster.isEmpty) return false;
    final dateStr = _formattedSelectedDate;
    final res = await _apiService.submitTeacherAttendance(
      date: dateStr,
      submissions: _attendanceSubmissions,
      // When a specific class is open, scope the save to it.
      classId: _selectedClassId?.toString(),
    );
    if (res['status'] == 'error') {
      _attendanceError = res['message'] ?? 'Failed to submit attendance';
      notifyListeners();
      return false;
    }
    return true;
  }

  Future<void> fetchTeacherSalary({int? year}) async {
    _isLoadingSalary = true;
    _salaryError = null;
    notifyListeners();
    final res = await _apiService.getTeacherSalary(year: year);
    if (res['status'] == 'error') {
      _salaryError = res['message'] ?? 'Failed to load salary data';
      _salaryData = null;
    } else {
      final payload = res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
      _salaryData = TeacherSalaryData.fromJson(payload);
    }
    _isLoadingSalary = false;
    notifyListeners();
  }
}

import 'package:flutter/material.dart';
import '../models/teacher_attendance_model.dart';
import '../models/teacher_profile.dart';
import '../models/user_model.dart';
import '../services/api_service.dart';

class TeacherController extends ChangeNotifier {
  final ApiService _apiService = ApiService();

  TeacherProfile? _profile;
  final bool _isLoadingProfile = false;
  String? _profileError;

  List<TeacherAttendanceStudent> _attendanceRoster = [];
  bool _isLoadingAttendance = false;
  String? _attendanceError;
  DateTime _selectedDate = DateTime.now();

  TeacherSalaryData? _salaryData;
  bool _isLoadingSalary = false;
  String? _salaryError;

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

  TeacherSalaryData? get salaryData => _salaryData;
  bool get isLoadingSalary => _isLoadingSalary;
  String? get salaryError => _salaryError;

  void clearAllData() {
    _profile = null;
    _attendanceRoster = [];
    _attendanceSubmissions.clear();
    _salaryData = null;
    _attendanceError = null;
    _salaryError = null;
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

  Future<void> fetchTeacherAttendance({DateTime? date}) async {
    _isLoadingAttendance = true;
    _attendanceError = null;
    notifyListeners();

    final selectedDateStr = (date ?? _selectedDate).toLocal();
    final dateStr = '${selectedDateStr.year}-${selectedDateStr.month.toString().padLeft(2, '0')}-${selectedDateStr.day.toString().padLeft(2, '0')}';
    final res = await _apiService.getTeacherAttendance(date: dateStr);
    if (res['status'] == 'error') {
      _attendanceError = res['message'] ?? 'Failed to load attendance roster';
      _attendanceRoster = [];
    } else {
      final payload = res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
      final rosterList = payload['roster'] as List? ?? [];
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
    final selectedDateStr = _selectedDate.toLocal();
    final dateStr = '${selectedDateStr.year}-${selectedDateStr.month.toString().padLeft(2, '0')}-${selectedDateStr.day.toString().padLeft(2, '0')}';
    final res = await _apiService.submitTeacherAttendance(
      date: dateStr,
      submissions: _attendanceSubmissions,
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

import 'package:flutter/material.dart';
import '../models/attendance_model.dart';
import '../models/fee_model.dart';
import '../models/student_profile.dart';
import '../services/api_service.dart';

class StudentController extends ChangeNotifier {
  final ApiService _apiService = ApiService();

  StudentProfile? _profile;
  AttendanceData? _attendanceData;
  FeeData? _feeData;

  bool _isLoadingProfile = false;
  bool _isLoadingAttendance = false;
  bool _isLoadingFees = false;

  String? _profileError;
  String? _attendanceError;
  String? _feeError;

  StudentProfile? get profile => _profile;
  AttendanceData? get attendanceData => _attendanceData;
  FeeData? get feeData => _feeData;

  bool get isLoadingProfile => _isLoadingProfile;
  bool get isLoadingAttendance => _isLoadingAttendance;
  bool get isLoadingFees => _isLoadingFees;

  String? get profileError => _profileError;
  String? get attendanceError => _attendanceError;
  String? get feeError => _feeError;

  Future<void> fetchAllData() async {
    await Future.wait([
      fetchProfile(),
      fetchAttendance(),
      fetchFees(),
    ]);
  }

  Future<void> fetchProfile() async {
    _isLoadingProfile = true;
    _profileError = null;
    notifyListeners();

    final res = await _apiService.getStudentProfile();
    if (res['status'] == 'error') {
      _profileError = res['message'] ?? 'Failed to load profile';
    } else {
      final payload = res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
      _profile = StudentProfile.fromJson(payload);
    }

    _isLoadingProfile = false;
    notifyListeners();
  }

  Future<void> fetchAttendance({int? month, int? year}) async {
    _isLoadingAttendance = true;
    _attendanceError = null;
    notifyListeners();

    final res = await _apiService.getAttendance(month: month, year: year);
    if (res['status'] == 'error') {
      _attendanceError = res['message'] ?? 'Failed to load attendance';
    } else {
      final payload = res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
      _attendanceData = AttendanceData.fromJson(payload);
    }

    _isLoadingAttendance = false;
    notifyListeners();
  }

  Future<void> fetchFees() async {
    _isLoadingFees = true;
    _feeError = null;
    notifyListeners();

    final res = await _apiService.getFees();
    if (res['status'] == 'error') {
      _feeError = res['message'] ?? 'Failed to load fee information';
    } else {
      final payload = res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
      _feeData = FeeData.fromJson(payload);
    }

    _isLoadingFees = false;
    notifyListeners();
  }
}

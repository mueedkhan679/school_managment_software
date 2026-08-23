import 'package:flutter/material.dart';
import '../models/user_model.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

enum AuthStatus { unauthenticated, authenticating, authenticated, error }

class AuthController extends ChangeNotifier {
  final ApiService _apiService = ApiService();
  final StorageService _storageService = StorageService();

  AuthStatus _status = AuthStatus.unauthenticated;
  UserSession? _session;
  String? _errorMessage;
  bool _rememberMe = true;

  AuthStatus get status => _status;
  UserSession? get session => _session;
  String? get errorMessage => _errorMessage;
  bool get rememberMe => _rememberMe;
  bool get isAuthenticated => _status == AuthStatus.authenticated;

  AuthController() {
    _initSession();
  }

    Future<void> _initSession() async {
    _rememberMe = await _storageService.getRememberMe();
    final token = await _storageService.getAccessToken();
    if (token != null && token.isNotEmpty) {
      final info = await _storageService.getStudentInfo();
      _session = UserSession(
        accessToken: token,
        refreshToken: (await _storageService.getRefreshToken()) ?? '',
        userId: 0,
        username: info['student_id'] ?? '',
        role: info['role'] ?? 'STUDENT',
        studentId: info['student_id'] ?? '',
        studentName: info['name'] ?? 'Student',
        teacherId: info['teacher_id'] ?? '',
        teacherName: info['teacher_name'] ?? '',
      );
      _status = AuthStatus.authenticated;
      notifyListeners();
    }
  }

  void toggleRememberMe(bool? val) {
    _rememberMe = val ?? false;
    _storageService.setRememberMe(_rememberMe);
    notifyListeners();
  }

  Future<bool> login(String username, String password) async {
    _status = AuthStatus.authenticating;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _apiService.login(username, password);
      if (res['status'] == 'success' || res['status'] != 'error') {
        final payload = res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
        _session = UserSession.fromJson(payload);

        // Clear old storage values before saving new ones to prevent data leakage between users
        await _storageService.clearAll();

        await _storageService.saveTokens(
          access: _session!.accessToken,
          refresh: _session!.refreshToken,
        );
                await _storageService.saveStudentInfo(
          studentId: _session!.studentId,
          name: _session!.studentName,
          role: _session!.role,
          teacherId: _session!.teacherId,
          teacherName: _session!.teacherName,
        );
        await _storageService.setRememberMe(_rememberMe);

        _status = AuthStatus.authenticated;
        notifyListeners();
        return true;
      } else {
        _errorMessage = res['message'] ?? 'Login failed';
        _status = AuthStatus.error;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _errorMessage = 'An error occurred: ${e.toString()}';
      _status = AuthStatus.error;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _storageService.clearAll();
    _session = null;
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}

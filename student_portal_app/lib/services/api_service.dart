import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'storage_service.dart';

class ApiService {
  static const String baseUrl = 'https://mueed563.pythonanywhere.com';
  final StorageService _storageService = StorageService();

  Future<Map<String, String>> _getHeaders({bool requireAuth = true}) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    };
    
    final cookie = await _storageService.getSessionCookie();
    if (cookie != null && cookie.isNotEmpty) {
      headers['Cookie'] = cookie;
    }

    if (requireAuth) {
      final token = await _storageService.getAccessToken();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    return headers;
  }

  Future<Map<String, dynamic>> login(String username, String password) async {
    const endpoint = '$baseUrl/api/v1/auth/login/';
    final url = Uri.parse(endpoint);
    try {
      final response = await http.post(
        url,
        headers: await _getHeaders(requireAuth: false),
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      );
      
      debugPrint('LOGIN RESPONSE HEADERS: ${response.headers}');
      
      final rawCookie = response.headers['set-cookie'];
      if (rawCookie != null) {
        await _storageService.saveSessionCookie(rawCookie);
      }
      
      debugPrint('Login Status Code ($endpoint): ${response.statusCode}');
      debugPrint('Login Response Body ($endpoint): ${response.body}');
      
      if (response.body.trim().toLowerCase().startsWith('<!doctype html>') || response.body.trim().toLowerCase().startsWith('<html')) {
        return {
          'status': 'error',
          'message': 'Server returned an HTML error page (Status ${response.statusCode}).',
        };
      }
      if (response.statusCode >= 200 && response.statusCode < 300) {
        debugPrint('Login successful on exact URL: $endpoint');
      }
      return _processResponse(response);
    } catch (e) {
      debugPrint('Network error on $endpoint: $e');
      return {
        'status': 'error',
        'message': 'Network or server error: $e',
      };
    }
  }

  Future<bool> refreshToken() async {
    final refresh = await _storageService.getRefreshToken();
    if (refresh == null || refresh.isEmpty) return false;

    final url = Uri.parse('$baseUrl/api/v1/auth/token/refresh/');
    try {
      final response = await http.post(
        url,
        headers: await _getHeaders(requireAuth: false),
        body: jsonEncode({'refresh': refresh}),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final newAccess = data['access'] as String?;
        final newRefresh = data['refresh'] as String? ?? refresh;
        if (newAccess != null) {
          await _storageService.saveTokens(access: newAccess, refresh: newRefresh);
          return true;
        }
      }
    } catch (_) {}
    return false;
  }

  Future<Map<String, dynamic>> getStudentProfile() async {
    return _authenticatedGet('$baseUrl/api/v1/students/profile/');
  }

  Future<Map<String, dynamic>> getAttendance({int? month, int? year}) async {
    var endpoint = '$baseUrl/api/v1/students/attendance/';
    final params = <String>[];
    if (month != null) params.add('month=$month');
    if (year != null) params.add('year=$year');
    if (params.isNotEmpty) {
      endpoint += '?${params.join('&')}';
    }
    return _authenticatedGet(endpoint);
  }

    Future<Map<String, dynamic>> getFees() async {
    return _authenticatedGet('$baseUrl/api/v1/students/fees/');
  }

  Future<Map<String, dynamic>> getTeacherAttendance({int? month, int? year, String? date}) async {
    var endpoint = '$baseUrl/api/v1/teacher/attendance/';
    final params = <String>[];
    if (date != null) params.add('date=$date');
    if (year != null) params.add('year=$year');
    if (params.isNotEmpty) {
      endpoint += '?${params.join('&')}';
    }
    return _authenticatedGet(endpoint);
  }

  Future<Map<String, dynamic>> submitTeacherAttendance({
    required String date,
    required Map<String, String> submissions,
    String? classId,
  }) async {
    final url = Uri.parse('$baseUrl/api/v1/teacher/attendance/');
    final body = <String, dynamic>{
      'date': date,
      'attendance': submissions,
    };
    if (classId != null) {
      body['class_id'] = classId;
    }
    final response = await http.post(
      url,
      headers: await _getHeaders(requireAuth: true),
      body: jsonEncode(body),
    );
    return _processResponse(response);
  }

  Future<Map<String, dynamic>> getTeacherSalary({int? year}) async {
    var endpoint = '$baseUrl/api/v1/teacher/salary/';
    if (year != null) {
      endpoint += '?year=$year';
    }
    return _authenticatedGet(endpoint);
  }

  Future<Map<String, dynamic>> _authenticatedGet(String urlStr) async {
    final url = Uri.parse(urlStr);
    var response = await http.get(url, headers: await _getHeaders(requireAuth: true));

    if (response.statusCode == 401) {
      final refreshed = await refreshToken();
      if (refreshed) {
        response = await http.get(url, headers: await _getHeaders(requireAuth: true));
      }
    }
    
    if (urlStr.contains('/api/data/') && !urlStr.contains('attendance') && !urlStr.contains('fees')) {
      debugPrint('PROFILE RESPONSE CODE: ${response.statusCode}');
      debugPrint('PROFILE RESPONSE BODY: ${response.body}');
    } else {
      debugPrint('GET $urlStr Status Code: ${response.statusCode}');
      debugPrint('GET $urlStr Response Body: ${response.body}');
    }
    
    return _processResponse(response);
  }

  Map<String, dynamic> _processResponse(http.Response response) {
    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return body;
      } else {
        final msg = body['message'] ?? body['detail'] ?? 'Request failed with status ${response.statusCode}';
        return {
          'status': 'error',
          'message': msg,
          'errors': body['errors'] ?? body,
        };
      }
    } catch (e) {
      return {
        'status': 'error',
        'message': 'Failed to parse server response: ${e.toString()}',
      };
    }
  }
}

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'storage_service.dart';

class ApiService {
  // Use https://mueed563.pythonanywhere.com for live server
  // (Local testing IP previously used here was removed — always connect to live DB)
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
    
    debugPrint('====================================');
    debugPrint('LOGIN URL: $url');
    debugPrint('====================================');
    
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
      
      // Process response with robust error handling
      final result = _processResponse(response);
      
      if (result['status'] != 'error' && response.statusCode >= 200 && response.statusCode < 300) {
        debugPrint('✓ Login successful on exact URL: $endpoint');
      }
      
      return result;
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

  Future<Map<String, dynamic>> getTeacherClasses() async {
    return _authenticatedGet('$baseUrl/api/v1/teacher/classes/');
  }

  /// Full profile of the logged-in teacher (Digital ID Card data).
  Future<Map<String, dynamic>> getTeacherProfile() async {
    return _authenticatedGet('$baseUrl/api/v1/teacher/profile/');
  }

  /// Registers a new student on behalf of a teacher.
  Future<Map<String, dynamic>> addTeacherStudent({
    required String fullName,
    required String rollNumber,
    required int classId,
    required String fatherName,
    String phone = '',
    String? admissionDate,
  }) async {
    final url = Uri.parse('$baseUrl/api/v1/teacher/students/add/');
    final body = <String, dynamic>{
      'full_name': fullName,
      'roll_number': rollNumber,
      'classroom_id': classId,
      'father_name': fatherName,
      'phone_number': phone,
      if (admissionDate != null) 'admission_date': admissionDate,
    };
    final response = await http.post(
      url,
      headers: await _getHeaders(requireAuth: true),
      body: jsonEncode(body),
    );
    return _processResponse(response);
  }

  Future<Map<String, dynamic>> getTeacherAttendance({int? month, int? year, String? date, int? classId}) async {
    var endpoint = '$baseUrl/api/v1/teacher/attendance/';
    final params = <String>[];
    if (date != null) params.add('date=$date');
    if (year != null) params.add('year=$year');
    if (classId != null) params.add('class_id=$classId');
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

  /// POSTs a scanned dashboard QR token to check the logged-in teacher in.
  Future<Map<String, dynamic>> scanTeacherAttendance(String qrToken) async {
    final url = Uri.parse('$baseUrl/api/v1/teacher/attendance/scan/');
    final response = await http.post(
      url,
      headers: await _getHeaders(requireAuth: true),
      body: jsonEncode({'token': qrToken}),
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
    // Log response details for debugging
    debugPrint('Response Status Code: ${response.statusCode}');
    debugPrint('Response Content-Type: ${response.headers['content-type']}');
    final bodyPreview = response.body.length > 500 
        ? '${response.body.substring(0, 500)}...' 
        : response.body;
    debugPrint('Response Body (first 500 chars): $bodyPreview');
    
    // Check if response is HTML (common for error pages, redirects, or server issues)
    final trimmedBody = response.body.trim().toLowerCase();
    if (trimmedBody.startsWith('<!doctype html>') || 
        trimmedBody.startsWith('<html') || 
        trimmedBody.startsWith('<?xml')) {
      debugPrint('⚠️ Server returned HTML instead of JSON');
      return {
        'status': 'error',
        'message': 'Server returned an HTML page (Status ${response.statusCode}). This usually indicates a server error, incorrect endpoint, or maintenance mode.',
        'statusCode': response.statusCode,
        'rawBody': response.body,
        'isHtmlResponse': true,
      };
    }
    
    // Check content-type header to verify JSON response
    final contentType = response.headers['content-type'] ?? '';
    if (!contentType.contains('application/json') && !contentType.contains('text/json')) {
      debugPrint('⚠️ Response Content-Type is not JSON: $contentType');
      // If it's not JSON content-type, try to parse anyway but with warning
      if (!contentType.contains('text/') && !contentType.contains('application/')) {
        return {
          'status': 'error',
          'message': 'Unexpected content type: $contentType (Status ${response.statusCode})',
          'statusCode': response.statusCode,
          'rawBody': response.body,
        };
      }
    }
    
    // Attempt to parse JSON
    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      
      if (response.statusCode >= 200 && response.statusCode < 300) {
        debugPrint('✓ Request successful with status ${response.statusCode}');
        return body;
      } else {
        // Extract error message from response
        final msg = body['message'] ?? 
                   body['detail'] ?? 
                   body['error'] ?? 
                   'Request failed with status ${response.statusCode}';
        
        debugPrint('✗ Request failed: $msg');
        return {
          'status': 'error',
          'message': msg,
          'statusCode': response.statusCode,
          'errors': body['errors'] ?? body,
        };
      }
    } on FormatException catch (e) {
      // JSON parsing failed - response is not valid JSON
      debugPrint('✗ JSON parsing failed: ${e.toString()}');
      debugPrint('Response body: ${response.body}');
      
      return {
        'status': 'error',
        'message': 'Server returned invalid JSON (Status ${response.statusCode}). ${e.toString()}',
        'statusCode': response.statusCode,
        'rawBody': response.body,
        'parseError': e.toString(),
      };
    } catch (e) {
      // Other unexpected errors during parsing
      debugPrint('✗ Unexpected error processing response: ${e.toString()}');
      return {
        'status': 'error',
        'message': 'Failed to process server response: ${e.toString()}',
        'statusCode': response.statusCode,
        'rawBody': response.body,
      };
    }
  }
}

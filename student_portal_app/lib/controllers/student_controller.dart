import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:open_filex/open_filex.dart';

import '../models/attendance_model.dart';
import '../models/fee_model.dart';
import '../models/student_profile.dart';
import '../services/api_service.dart';

/// Student-side state: profile, attendance and fees.
///
/// Data strategy (fast + robust):
///  1. On first access the controller hydrates models from a JSON cache on
///    disk (via path_provider's getApplicationDocumentsDirectory) - the UI
///    renders instantly with the last known content, even fully offline.
///  2. Network fetches then run as a background sync: when cached data is
///    already showing, no full-screen loaders are raised; the UI silently
///    updates (and re-caches) once fresh data arrives.
///  3. Loading flags are only raised when there is nothing cached to show
///    (first-ever launch), which drives the skeleton screens.

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

  bool _hydrated = false;

  // --- Cache keys -----------------------------------------------------------
  static const String _kProfile = 'student_profile';
  static const String _kAttendance = 'student_attendance';
  static const String _kFees = 'student_fees';

  StudentProfile? get profile => _profile;
  AttendanceData? get attendanceData => _attendanceData;
  FeeData? get feeData => _feeData;

  bool get isLoadingProfile => _isLoadingProfile;
  bool get isLoadingAttendance => _isLoadingAttendance;
  bool get isLoadingFees => _isLoadingFees;

  String? get profileError => _profileError;
  String? get attendanceError => _attendanceError;
  String? get feeError => _feeError;

  /// True when at least one section has cached data to render immediately.
  bool get hasCachedData =>
      _profile != null || _attendanceData != null || _feeData != null;

  /// Loads the last-known payloads from disk cache into memory (once per
  /// session) so screens can paint instantly before any network call.
  Future<void> hydrateFromCache() async {
    if (_hydrated) return;
    _hydrated = true;
    try {
      final dir = await getApplicationDocumentsDirectory();
      _profile ??=
          await _readJson(dir, _kProfile, StudentProfile.fromJson);
      _attendanceData ??=
          await _readJson(dir, _kAttendance, AttendanceData.fromJson);
      _feeData ??= await _readJson(dir, _kFees, FeeData.fromJson);
    } catch (_) {
      // Corrupt/legacy cache — silently ignore; the background sync will
      // repopulate everything fresh.
    }
    notifyListeners();
  }

  /// Reads & decodes a cached JSON file into a model via [fromJson].
  /// Returns `null` when the file is missing or unreadable.
  Future<T?> _readJson<T>(
    Directory dir,
    String key,
    T Function(Map<String, dynamic> json) fromJson,
  ) async {
    final file = File('${dir.path}/cache_$key.json');
    if (!await file.exists()) return null;
    final raw = await file.readAsString();
    if (raw.isEmpty) return null;
    final Map<String, dynamic> json =
        jsonDecode(raw) as Map<String, dynamic>;
    return fromJson(json);
  }


  /// Hydrates from cache, then refreshes every section in parallel.
  ///
  /// Sections that already have cached data sync *silently* (no loading
  /// spinners) — screens keep showing cached content and update in place.
  Future<void> fetchAllData() async {
    await hydrateFromCache();
    await Future.wait([
      fetchProfile(),
      fetchAttendance(),
      fetchFees(),
    ]);
  }

  void clearAllData() {
    _profile = null;
    _attendanceData = null;
    _feeData = null;
    _profileError = null;
    _attendanceError = null;
    _feeError = null;
    _isLoadingProfile = false;
    _isLoadingAttendance = false;
    _isLoadingFees = false;
    _hydrated = false;
    notifyListeners();
    _wipeCache();
  }

  Future<void> _wipeCache() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      await for (final entity in dir.list()) {
        if (entity is File &&
            entity.path.contains('cache_') &&
            entity.path.endsWith('.json')) {
          await entity.delete();
        }
      }
    } catch (_) {}
  }

  Future<void> fetchProfile() async {
    // Background sync when cached content is already on screen.
    final showSpinner = _profile == null;
    if (showSpinner) _isLoadingProfile = true;
    _profileError = null;
    notifyListeners();

    final res = await _apiService.getStudentProfile();
    if (res['status'] == 'error') {
      // Keep cached data visible; don't surface background-sync noise.
      if (_profile == null) {
        _profileError = res['message'] ?? 'Failed to load profile';
      }
    } else {
      final payload =
          res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
      _profile = StudentProfile.fromJson(payload);
      _profileError = null;
      _writeCache(_kProfile, payload);
    }

    _isLoadingProfile = false;
    notifyListeners();
  }

  Future<void> fetchAttendance({int? month, int? year}) async {
    final showSpinner = _attendanceData == null;
    if (showSpinner) _isLoadingAttendance = true;
    _attendanceError = null;
    notifyListeners();

    final res = await _apiService.getAttendance(month: month, year: year);
    if (res['status'] == 'error') {
      if (_attendanceData == null) {
        _attendanceError = res['message'] ?? 'Failed to load attendance';
      }
    } else {
      final payload =
          res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
      _attendanceData = AttendanceData.fromJson(payload);
      _attendanceError = null;
      // Only the default (unfiltered) payload is reused as cold-start cache.
      if (month == null && year == null) {
        _writeCache(_kAttendance, payload);
      }
    }

    _isLoadingAttendance = false;
    notifyListeners();
  }

  Future<void> fetchFees() async {
    final showSpinner = _feeData == null;
    if (showSpinner) _isLoadingFees = true;
    _feeError = null;
    notifyListeners();

    final res = await _apiService.getFees();
    if (res['status'] == 'error') {
      if (_feeData == null) {
        _feeError = res['message'] ?? 'Failed to load fee information';
      }
    } else {
      final payload =
          res['payload'] != null ? res['payload'] as Map<String, dynamic> : res;
      _feeData = FeeData.fromJson(payload);
      _feeError = null;
      _writeCache(_kFees, payload);
    }

    _isLoadingFees = false;
    notifyListeners();
  }

  bool _isDownloadingStatement = false;
  bool get isDownloadingStatement => _isDownloadingStatement;

  Future<void> downloadFeeStatement(BuildContext context) async {
    _isDownloadingStatement = true;
    notifyListeners();
    try {
      final response = await _apiService.downloadFeeStatement();
      if (response.statusCode == 200) {
        final dir = await getApplicationDocumentsDirectory();
        final file = File('${dir.path}/fee_statement.pdf');
        await file.writeAsBytes(response.bodyBytes);
        
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Fee Statement downloaded successfully')),
          );
        }
        
        await OpenFilex.open(file.path);
      } else {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to download Fee Statement')),
          );
        }
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      _isDownloadingStatement = false;
      notifyListeners();
    }
  }

  /// Persists a raw payload map as JSON for instant cold-start hydration.
  Future<void> _writeCache(String key, Map<String, dynamic> payload) async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/cache_$key.json');
      await file.create(recursive: true);
      await file.writeAsString(jsonEncode(payload), flush: true);
    } catch (_) {}
  }
}

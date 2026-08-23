import '../services/api_service.dart';

class StudentProfile {
  final int id;
  final String studentId;
  final String name;
  final String fatherName;
  final int schoolClassId;
  final String schoolClassName;
  final String dateOfBirth;
  final String gender;
  final String genderDisplay;
  final String formBNumber;
  final String email;
  final String phone;
  final String address;
  final String? photoUrl;
  final String admissionDate;
  final String? customMonthlyFee;
  final String effectiveMonthlyFee;
  final String yearlyFee;
  final String qrCodeData;
  final String totalPaid;
  final String attendancePercentage;

  StudentProfile({
    required this.id,
    required this.studentId,
    required this.name,
    required this.fatherName,
    required this.schoolClassId,
    required this.schoolClassName,
    required this.dateOfBirth,
    required this.gender,
    required this.genderDisplay,
    required this.formBNumber,
    required this.email,
    required this.phone,
    required this.address,
    this.photoUrl,
    required this.admissionDate,
    this.customMonthlyFee,
    required this.effectiveMonthlyFee,
    required this.yearlyFee,
    required this.qrCodeData,
    this.totalPaid = '0.00',
    this.attendancePercentage = '0.0',
  });

  /// Returns [v] as a trimmed non-empty string, otherwise null.
  static String? _nonEmpty(dynamic v) {
    final s = v?.toString().trim();
    return (s == null || s.isEmpty) ? null : s;
  }

  static String? _parsePhotoUrl(dynamic url) {
    if (url == null) return null;
    final String raw = url.toString().trim();
    if (raw.isEmpty) return null;

    // Already an absolute URL – use it as-is.
    if (raw.startsWith('http://') || raw.startsWith('https://')) {
      return raw;
    }

    // Relative backend media path (e.g. "/media/student_photos/x.jpg" or
    // "media/student_photos/x.jpg") – resolve it against the API origin so
    // uploaded student photos always render.
    String base = ApiService.baseUrl;
    if (base.endsWith('/')) {
      base = base.substring(0, base.length - 1);
    }
    return raw.startsWith('/') ? '$base$raw' : '$base/$raw';
  }

  factory StudentProfile.fromJson(Map<String, dynamic> json) {
    String parsedName = json['full_name']?.toString() ?? json['name']?.toString() ?? '';
    if (parsedName.isEmpty && json['first_name'] != null) {
      parsedName = '${json['first_name']} ${json['last_name'] ?? ''}'.trim();
    }
    return StudentProfile(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      studentId: json['student_id']?.toString() ?? json['registration_number']?.toString() ?? json['username']?.toString() ?? '',
      name: parsedName,
      fatherName: json['father_name']?.toString() ?? '',
      schoolClassId: int.tryParse(json['school_class_id']?.toString() ?? '') ?? 0,
      schoolClassName: json['class_name']?.toString() ?? json['classroom']?.toString() ?? json['grade']?.toString() ?? json['school_class_name']?.toString() ?? '',
      dateOfBirth:
          _nonEmpty(json['dob']) ?? _nonEmpty(json['date_of_birth']) ?? _nonEmpty(json['birth_date']) ?? 'N/A',
      gender: _nonEmpty(json['gender']) ?? _nonEmpty(json['sex']) ?? 'N/A',
      genderDisplay: _nonEmpty(json['gender_display']) ?? '',
      formBNumber: json['form_b']?.toString() ?? json['cnic']?.toString() ?? json['form_b_number']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      phone: json['contact']?.toString() ?? json['phone']?.toString() ?? '',
      address: json['residential_address']?.toString() ?? json['address']?.toString() ?? '',
      photoUrl: _parsePhotoUrl(
        json['photo'] ??
            json['student_photo'] ??
            json['profile_photo'] ??
            json['photo_url'] ??
            json['photo_path'] ??
            json['avatar'] ??
            json['image'],
      ),
      admissionDate: json['admission_date']?.toString() ?? '',
      customMonthlyFee: json['custom_monthly_fee']?.toString(),
      effectiveMonthlyFee: json['effective_tuition']?.toString() ?? json['monthly_tuition']?.toString() ?? json['tuition_fee']?.toString() ?? json['effective_monthly_fee']?.toString() ?? '0.00',
      yearlyFee: json['yearly_fee']?.toString() ?? '0.00',
      qrCodeData: json['qr_code_data']?.toString() ?? '',
      totalPaid: json['total_paid']?.toString() ?? json['paid_amount']?.toString() ?? '0.00',
      attendancePercentage: json['attendance_percentage']?.toString() ?? '0.0',
    );
  }

  /// The student's complete display name (e.g. "Ahmed Khan").
  ///
  /// Falls back to a friendly placeholder derived from the student ID so UI
  /// bindings never render empty text while data is loading.
  String get fullName {
    final trimmed = name.trim();
    if (trimmed.isNotEmpty) return trimmed;
    if (studentId.isNotEmpty) return 'Student $studentId';
    return 'Student';
  }

  /// Alias matching the API field naming (`class_name`), e.g. "Playgroup".
  ///
  /// Falls back to `'N/A'` when the class is unknown so ID-card bindings
  /// never render a blank value.
  String get className => schoolClassName.trim().isNotEmpty ? schoolClassName.trim() : 'N/A';

  /// Gender ready for display.
  ///
  /// Preference order: API-provided `gender_display` → raw `gender`
  /// (expanding single-letter codes M/F) → `'N/A'`.
  String get genderLabel {
    final display = genderDisplay.trim();
    if (display.isNotEmpty) return display;

    final raw = gender.trim();
    if (raw.isEmpty || raw.toUpperCase() == 'N/A') return 'N/A';

    switch (raw.toUpperCase()) {
      case 'M':
      case 'MALE':
        return 'Male';
      case 'F':
      case 'FEMALE':
        return 'Female';
      default:
        return raw;
    }
  }

  /// Date of birth ready for display (`'N/A'` when unknown).
  String get dobLabel {
    final dob = dateOfBirth.trim();
    return dob.isEmpty || dob.toUpperCase() == 'N/A' ? 'N/A' : dob;
  }

  /// Raw date-of-birth alias (matches the API field naming).
  String get dob => dateOfBirth;

  /// Whether a usable profile photo URL is available.
  bool get hasPhoto => photoUrl != null && photoUrl!.trim().isNotEmpty;
}

/// Result of a teacher QR self check-in scan.
///
/// Wraps the full teacher details and attendance info returned by the backend
/// scan endpoint so the confirmation dialog can render the teacher's photo,
/// name, ID, contact details, status, and check-in time.
class TeacherScanResult {
  final bool success;
  final bool duplicate;
  final String message;
  final String teacherId;
  final String name;
  final String phone;
  final String address;
  final String? photoUrl;
  final String status;
  final String timeIn; // HH:MM:SS
  final String timeInLabel; // e.g. 08:45 AM

  const TeacherScanResult({
    required this.success,
    required this.duplicate,
    required this.message,
    this.teacherId = '',
    this.name = '',
    this.phone = '',
    this.address = '',
    this.photoUrl,
    this.status = '',
    this.timeIn = '',
    this.timeInLabel = '',
  });

  factory TeacherScanResult.fromResponse(Map<String, dynamic> res) {
    final payload = res['payload'] is Map<String, dynamic>
        ? res['payload'] as Map<String, dynamic>
        : <String, dynamic>{};
    return TeacherScanResult(
      success: res['status'] == 'success',
      duplicate: payload['duplicate'] == true,
      message: res['message']?.toString() ?? '',
      teacherId: payload['teacher_id']?.toString() ?? '',
      name: payload['name']?.toString() ?? '',
      phone: payload['phone']?.toString() ?? '',
      address: payload['address']?.toString() ?? '',
      photoUrl: payload['photo_url']?.toString(),
      status: payload['status']?.toString() ?? '',
      timeIn: payload['time_in']?.toString() ?? '',
      timeInLabel: payload['time_in_label']?.toString() ?? '',
    );
  }

  bool get isPresent => status == 'PRESENT';
}

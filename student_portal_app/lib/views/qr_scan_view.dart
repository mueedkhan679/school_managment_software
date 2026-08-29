import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import '../controllers/teacher_controller.dart';
import '../widgets/modern_loader.dart';

/// Full-screen camera scanner that reads the Teacher Attendance QR code
/// displayed on the admin web dashboard and checks the teacher in.
class QrScanView extends StatefulWidget {
  const QrScanView({super.key});

  @override
  State<QrScanView> createState() => _QrScanViewState();
}

class _QrScanViewState extends State<QrScanView> {
  final MobileScannerController _cameraController = MobileScannerController(
    detectionTimeoutMs: 1500,
  );
  bool _handled = false;

  @override
  void dispose() {
    _cameraController.dispose();
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_handled) return;
    final code = capture.barcodes.isNotEmpty
        ? capture.barcodes.first.rawValue
        : null;
    if (code == null || code.trim().isEmpty) return;

    _handled = true;
    final tc = context.read<TeacherController>();
    final ok = await tc.markOwnAttendanceViaQr(code.trim());
    if (!mounted) return;

    final result = tc.selfScan;

    // Play a short confirmation sound on a successful (or already-marked)
    // scan, so the teacher gets instant audio feedback.
    if (ok) {
      unawaited(SystemSound.play(SystemSoundType.alert));
    }

    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        final iconColor = ok ? Colors.green : Colors.redAccent;
        final icon = ok
            ? (result.duplicate
                ? Icons.verified_user_rounded
                : Icons.check_circle_rounded)
            : Icons.error_rounded;
        final title = ok
            ? (result.duplicate
                ? 'Attendance Already Marked'
                : 'Attendance Marked Successfully')
            : 'Invalid QR Code';

        return AlertDialog(
          icon: Icon(icon, color: iconColor, size: 44),
          title: Text(title, textAlign: TextAlign.center),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                if (ok && result.name.isNotEmpty) ...[
                  // Teacher photo (or initials placeholder)
                  ClipOval(
                    child: result.photoUrl != null && result.photoUrl!.isNotEmpty
                        ? Image.network(
                            result.photoUrl!,
                            width: 72,
                            height: 72,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => _initialCircle(result),
                          )
                        : _initialCircle(result),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    result.name,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                    ),
                  ),
                  Text(
                    '@${result.teacherId}',
                    style: const TextStyle(color: Colors.black54),
                  ),
                  if (result.phone.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text('📞 ${result.phone}'),
                  ],
                  if (result.address.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text('📍 ${result.address}'),
                  ],
                  const Divider(height: 24),
                  _statusRow(
                    'Attendance Status',
                    result.isPresent ? 'Present' : result.status,
                    result.isPresent ? Colors.green : Colors.orange,
                  ),
                  if (result.timeInLabel.isNotEmpty)
                    _statusRow('Check-in Time', result.timeInLabel, Colors.black87),
                ] else ...[
                  Text(
                    tc.selfScanMessage ?? '',
                    textAlign: TextAlign.center,
                  ),
                ],
              ],
            ),
          ),
          actionsAlignment: MainAxisAlignment.center,
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Okay'),
            ),
          ],
        );
      },
    );
    if (!mounted) return;
    // Success closes the scanner and returns to the dashboard; failures let
    // the teacher retry immediately.
    if (ok) {
      Navigator.of(context).pop();
    } else {
      setState(() => _handled = false);
    }
  }

  Widget _statusRow(String label, String value, Color valueColor) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.black54)),
          Text(
            value,
            style: TextStyle(fontWeight: FontWeight.w600, color: valueColor),
          ),
        ],
      ),
    );
  }

  Widget _initialCircle(dynamic result) {
    final name = result.name is String ? result.name as String : '';
    return Container(
      width: 72,
      height: 72,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: Colors.green.shade100, shape: BoxShape.circle),
      child: Text(
        name.isEmpty ? '?' : name.substring(0, 1).toUpperCase(),
        style: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.bold,
          color: Colors.green.shade800,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tc = context.watch<TeacherController>();
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Attendance QR')),
      body: Stack(
        children: [
          MobileScanner(
            controller: _cameraController,
            onDetect: _onDetect,
          ),
          // Viewfinder frame
          Center(
            child: Container(
              width: 260,
              height: 260,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 3),
                borderRadius: BorderRadius.circular(20),
              ),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 32,
            child: Column(
              children: [
                if (tc.isScanningSelf)
                  const ButtonSpinner(size: 28),
                const SizedBox(height: 12),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.black54,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Text(
                    'Point the camera at the QR code on the school dashboard',
                    style: TextStyle(color: Colors.white),
                    textAlign: TextAlign.center,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
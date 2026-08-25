import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import '../controllers/teacher_controller.dart';

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

    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        icon: Icon(
          ok ? Icons.check_circle_rounded : Icons.error_rounded,
          color: ok ? Colors.green : Colors.redAccent,
          size: 48,
        ),
        title: Text(ok ? 'Check-in Successful' : 'Scan Failed'),
        content: Text(
          tc.selfScanMessage ?? '',
          textAlign: TextAlign.center,
        ),
        actionsAlignment: MainAxisAlignment.center,
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Okay'),
          ),
        ],
      ),
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
                  const CircularProgressIndicator(color: Colors.white),
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
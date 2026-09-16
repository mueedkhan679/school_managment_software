import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import '../controllers/teacher_controller.dart';
import '../widgets/modern_loader.dart';
import '../widgets/student_avatar.dart';

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

    final code =
        capture.barcodes.isNotEmpty ? capture.barcodes.first.rawValue : null;

    if (code == null || code.trim().isEmpty) return;

    _handled = true;

    final tc = context.read<TeacherController>();

    final ok = await tc.markOwnAttendanceViaQr(code.trim());

    if (!mounted) return;

    final result = tc.selfScan;

    // Play a short confirmation sound on a successful
    // (or already-marked) scan.
    if (ok) {
      unawaited(
        SystemSound.play(SystemSoundType.alert),
      );
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

        return Dialog(
          backgroundColor: Colors.transparent,
          insetPadding: const EdgeInsets.symmetric(
            horizontal: 20,
            vertical: 24,
          ),
          child: Container(
            constraints: const BoxConstraints(
              maxWidth: 430,
            ),
            padding: const EdgeInsets.fromLTRB(
              22,
              24,
              22,
              18,
            ),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              borderRadius: BorderRadius.circular(28),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.18),
                  blurRadius: 35,
                  offset: const Offset(0, 15),
                ),
              ],
            ),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Result icon
                  Container(
                    width: 76,
                    height: 76,
                    decoration: BoxDecoration(
                      color: iconColor.withValues(alpha: 0.10),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      icon,
                      color: iconColor,
                      size: 42,
                    ),
                  ),

                  const SizedBox(height: 18),

                  Text(
                    title,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      height: 1.25,
                    ),
                  ),

                  const SizedBox(height: 20),

                  if (ok && result.name.isNotEmpty) ...[
                    // Teacher avatar
                    Container(
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: iconColor.withValues(alpha: 0.25),
                          width: 2,
                        ),
                      ),
                      child: StudentAvatar(
                        imageUrl: result.photoUrl,
                        radius: 42,
                        iconSize: 38,
                      ),
                    ),

                    const SizedBox(height: 14),

                    Text(
                      result.name,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 19,
                        fontWeight: FontWeight.w800,
                      ),
                    ),

                    const SizedBox(height: 5),

                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .primary
                            .withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        '@${result.teacherId}',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.primary,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),

                    const SizedBox(height: 18),

                    if (result.phone.isNotEmpty)
                      _infoTile(
                        icon: Icons.phone_rounded,
                        label: 'Phone',
                        value: result.phone,
                      ),

                    if (result.address.isNotEmpty)
                      _infoTile(
                        icon: Icons.location_on_rounded,
                        label: 'Address',
                        value: result.address,
                      ),

                    const SizedBox(height: 6),

                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .primary
                            .withValues(alpha: 0.055),
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(
                          color: Theme.of(context)
                              .colorScheme
                              .primary
                              .withValues(alpha: 0.08),
                        ),
                      ),
                      child: Column(
                        children: [
                          _statusRow(
                            'Attendance Status',
                            result.isPresent ? 'Present' : result.status,
                            result.isPresent ? Colors.green : Colors.orange,
                          ),
                          if (result.timeInLabel.isNotEmpty) ...[
                            const SizedBox(height: 10),
                            _statusRow(
                              'Check-in Time',
                              result.timeInLabel,
                              Colors.black87,
                            ),
                          ],
                        ],
                      ),
                    ),
                  ] else ...[
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.redAccent.withValues(alpha: 0.06),
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Text(
                        tc.selfScanMessage ?? '',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 14,
                          height: 1.5,
                          color: Theme.of(context)
                              .textTheme
                              .bodyMedium
                              ?.color
                              ?.withValues(alpha: 0.7),
                        ),
                      ),
                    ),
                  ],

                  const SizedBox(height: 22),

                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: FilledButton(
                      onPressed: () {
                        Navigator.of(dialogContext).pop();
                      },
                      style: FilledButton.styleFrom(
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: const Text(
                        'Okay',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );

    if (!mounted) return;

    // Success closes the scanner and returns to dashboard.
    // Failures allow the teacher to retry immediately.
    if (ok) {
      Navigator.of(context).pop();
    } else {
      setState(() => _handled = false);
    }
  }

  Widget _infoTile({
    required IconData icon,
    required String label,
    required String value,
  }) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(
        horizontal: 13,
        vertical: 11,
      ),
      decoration: BoxDecoration(
        color:
            theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            icon,
            size: 18,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    color: theme.textTheme.bodySmall?.color
                        ?.withValues(alpha: 0.5),
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _statusRow(
    String label,
    String value,
    Color valueColor,
  ) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: Colors.black.withValues(alpha: 0.5),
            ),
          ),
        ),
        Flexible(
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 9,
              vertical: 5,
            ),
            decoration: BoxDecoration(
              color: valueColor.withValues(alpha: 0.09),
              borderRadius: BorderRadius.circular(9),
            ),
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: valueColor,
              ),
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final tc = context.watch<TeacherController>();
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: Colors.black,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.white,
        elevation: 0,
        scrolledUnderElevation: 0,
        leading: Padding(
          padding: const EdgeInsets.all(8),
          child: Material(
            color: Colors.black.withValues(alpha: 0.40),
            shape: const CircleBorder(),
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: () => Navigator.of(context).pop(),
              child: const Icon(
                Icons.arrow_back_rounded,
                size: 21,
              ),
            ),
          ),
        ),
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Scan Attendance',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
              ),
            ),
            Text(
              'Teacher QR Verification',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: Colors.white70,
              ),
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Material(
              color: Colors.black.withValues(alpha: 0.40),
              borderRadius: BorderRadius.circular(14),
              child: InkWell(
                borderRadius: BorderRadius.circular(14),
                onTap: () {
                  _cameraController.toggleTorch();
                },
                child: Padding(
                  padding: const EdgeInsets.all(11),
                  child: ValueListenableBuilder<MobileScannerState>(
                    valueListenable: _cameraController,
                    builder: (context, state, child) {
                      return Icon(
                        state.torchState == TorchState.on
                            ? Icons.flash_on_rounded
                            : Icons.flash_off_rounded,
                        size: 21,
                        color: Colors.white,
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      body: Stack(
        fit: StackFit.expand,
        children: [
          MobileScanner(
            controller: _cameraController,
            onDetect: _onDetect,
          ),

          // Dark overlay around scanner area
          IgnorePointer(
            child: CustomPaint(
              painter: _ScannerOverlayPainter(),
            ),
          ),

          // Scanner frame
          Center(
            child: SizedBox(
              width: 285,
              height: 285,
              child: Stack(
                children: [
                  // Corner brackets
                  const Positioned(
                    left: 0,
                    top: 0,
                    child: _ScannerCorner(
                      alignment: Alignment.topLeft,
                    ),
                  ),
                  const Positioned(
                    right: 0,
                    top: 0,
                    child: _ScannerCorner(
                      alignment: Alignment.topRight,
                    ),
                  ),
                  const Positioned(
                    left: 0,
                    bottom: 0,
                    child: _ScannerCorner(
                      alignment: Alignment.bottomLeft,
                    ),
                  ),
                  const Positioned(
                    right: 0,
                    bottom: 0,
                    child: _ScannerCorner(
                      alignment: Alignment.bottomRight,
                    ),
                  ),

                  // Animated-looking scanning line
                  Align(
                    alignment: Alignment.center,
                    child: Container(
                      height: 2,
                      margin: const EdgeInsets.symmetric(
                        horizontal: 10,
                      ),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary,
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: [
                          BoxShadow(
                            color: theme.colorScheme.primary
                                .withValues(alpha: 0.65),
                            blurRadius: 10,
                            spreadRadius: 2,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Center instruction
          Positioned(
            left: 24,
            right: 24,
            bottom: 135,
            child: Column(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 18,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.58),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.12),
                    ),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.qr_code_scanner_rounded,
                        color: Colors.white,
                        size: 20,
                      ),
                      SizedBox(width: 10),
                      Flexible(
                        child: Text(
                          'Align the QR code inside the frame',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 9),
                const Text(
                  'Scan the attendance QR displayed on the school dashboard',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 11.5,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),

          // Loading indicator
          if (tc.isScanningSelf)
            Positioned(
              left: 0,
              right: 0,
              bottom: 52,
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 18,
                    vertical: 11,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.62),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ButtonSpinner(size: 24),
                      SizedBox(width: 10),
                      Text(
                        'Checking attendance...',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ScannerCorner extends StatelessWidget {
  final Alignment alignment;

  const _ScannerCorner({
    required this.alignment,
  });

  @override
  Widget build(BuildContext context) {
    const length = 34.0;
    const thickness = 4.0;

    final isLeft = alignment.x < 0;
    final isTop = alignment.y < 0;

    return SizedBox(
      width: length,
      height: length,
      child: Stack(
        children: [
          Positioned(
            left: isLeft ? 0 : null,
            right: isLeft ? null : 0,
            top: isTop ? 0 : null,
            bottom: isTop ? null : 0,
            child: Container(
              width: length,
              height: thickness,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(5),
              ),
            ),
          ),
          Positioned(
            left: isLeft ? 0 : null,
            right: isLeft ? null : 0,
            top: isTop ? 0 : null,
            bottom: isTop ? null : 0,
            child: Container(
              width: thickness,
              height: length,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(5),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ScannerOverlayPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.black.withValues(alpha: 0.52)
      ..style = PaintingStyle.fill;

    final center = Offset(
      size.width / 2,
      size.height / 2 - 20,
    );

    const scanSize = 285.0;

    final scanRect = RRect.fromRectAndRadius(
      Rect.fromCenter(
        center: center,
        width: scanSize,
        height: scanSize,
      ),
      const Radius.circular(22),
    );

    final path = Path()
      ..addRect(
        Rect.fromLTWH(
          0,
          0,
          size.width,
          size.height,
        ),
      )
      ..addRRect(scanRect);

    canvas.drawPath(
      Path.combine(
        PathOperation.difference,
        path,
        Path()..addRRect(scanRect),
      ),
      paint,
    );
  }

  @override
  bool shouldRepaint(
    covariant CustomPainter oldDelegate,
  ) {
    return false;
  }
}

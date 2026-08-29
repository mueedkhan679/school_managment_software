import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../controllers/student_controller.dart';
import '../widgets/student_avatar.dart';

class DigitalIdCardView extends StatefulWidget {
  const DigitalIdCardView({super.key});

  @override
  State<DigitalIdCardView> createState() => _DigitalIdCardViewState();
}

class _DigitalIdCardViewState extends State<DigitalIdCardView> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  bool _showFront = true;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _flipCard() {
    if (_showFront) {
      _controller.forward();
    } else {
      _controller.reverse();
    }
    setState(() {
      _showFront = !_showFront;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final studentCtrl = context.watch<StudentController>();
    final profile = studentCtrl.profile;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        children: [
          Text(
            'Digital Student ID Card',
            style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            'Tap card to flip for QR Code verification',
            style: theme.textTheme.bodyMedium?.copyWith(color: Colors.grey),
          ),
          const SizedBox(height: 28),

          // 3D Flip Card Container
          GestureDetector(
            onTap: _flipCard,
            child: AnimatedBuilder(
              animation: _controller,
              builder: (context, child) {
                final angle = _controller.value * pi;
                final isBack = angle >= (pi / 2);

                return Transform(
                  transform: Matrix4.identity()
                    ..setEntry(3, 2, 0.001)
                    ..rotateY(angle),
                  alignment: Alignment.center,
                  child: isBack
                      ? Transform(
                          transform: Matrix4.identity()..rotateY(pi),
                          alignment: Alignment.center,
                          child: _buildCardBack(context, profile, theme),
                        )
                      : _buildCardFront(context, profile, theme),
                );
              },
            ),
          ).animate().fadeIn().scale(),

          const SizedBox(height: 32),

          // Flip hint button
          ElevatedButton.icon(
            onPressed: _flipCard,
            icon: const Icon(Icons.flip_rounded),
            label: Text(_showFront ? 'Flip to View QR Code' : 'Flip to View Details'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCardFront(BuildContext context, profile, ThemeData theme) {
    return Container(
      width: double.infinity,
      height: 440,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            theme.colorScheme.primary,
            theme.colorScheme.primaryContainer,
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.primary.withValues(alpha: 0.3),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            // School Header
            const Row(
              children: [
                Icon(Icons.school_rounded, color: Colors.white, size: 36),
                SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'EXCELLENCE ACADEMY',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.1,
                        ),
                      ),
                      Text(
                        'Official Student Identity Card',
                        style: TextStyle(color: Colors.white70, fontSize: 11),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(color: Colors.white30, height: 28),

            // Profile Photo – falls back to the placeholder icon when the
            // URL is missing or the network image fails to load.
            StudentAvatar(
              imageUrl: profile?.photoUrl,
              radius: 46,
              innerPadding: 3,
              backgroundColor: Colors.white,
              iconColor: theme.colorScheme.primary,
              iconSize: 50,
            ),
            const SizedBox(height: 14),

            // Name — auto-shrinks to a single line so long names can never
            // push the card contents past its fixed height (bottom overflow).
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  profile?.fullName ?? 'Student Name',
                  maxLines: 1,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            Text(
              'Reg ID: ${profile?.studentId ?? 'N/A'}',
              style: const TextStyle(
                color: Colors.amberAccent,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            const Spacer(),

            // Bio Details Grid
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(14),
              ),
              // Bio Details Grid – three equal columns so Class / Gender /
              // DOB each get the same width and never overflow the card.
              child: Row(
                children: [
                  Expanded(
                    child: _buildInfoColumn(
                      'Class',
                      (profile?.className.isNotEmpty ?? false) ? profile!.className : 'N/A',
                    ),
                  ),
                  Expanded(
                    child: _buildInfoColumn(
                      'Gender',
                      (profile?.genderLabel.isNotEmpty ?? false) ? profile!.genderLabel : 'N/A',
                    ),
                  ),
                  Expanded(
                    child: _buildInfoColumn(
                      'DOB',
                      (profile?.dob.isNotEmpty ?? false) ? profile!.dob : 'N/A',
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCardBack(BuildContext context, profile, ThemeData theme) {
    final qrData = profile?.qrCodeData ?? 'STUDENT_ID:${profile?.studentId}';

    return Container(
      width: double.infinity,
      height: 440,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: LinearGradient(
          begin: Alignment.bottomRight,
          end: Alignment.topLeft,
          colors: [
            theme.colorScheme.surfaceContainerHighest,
            theme.colorScheme.surface,
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Digital Verification QR',
              style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),

            // Auto Generated QR Code
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: const [
                  BoxShadow(color: Colors.black12, blurRadius: 8),
                ],
              ),
              child: QrImageView(
                data: qrData,
                version: QrVersions.auto,
                size: 180.0,
                backgroundColor: Colors.white,
              ),
            ),
            const SizedBox(height: 18),

            Text(
              'Scan for instant attendance & ID check',
              style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey),
            ),
            const SizedBox(height: 12),
            Text(
              'Emergency Contact: ${profile?.phone.isNotEmpty == true ? profile?.phone : 'School Admin'}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  /// One labelled value column inside the ID-card bio grid
  /// (Class / Gender / DOB). Text is centered and ellipsized so long values
  /// can never push outside their equal-width column.
  Widget _buildInfoColumn(String label, String value) {
    return Column(
      children: [
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(color: Colors.white70, fontSize: 11),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.center,
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
        ),
      ],
    );
  }
}

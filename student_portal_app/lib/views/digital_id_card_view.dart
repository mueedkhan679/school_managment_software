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

class _DigitalIdCardViewState extends State<DigitalIdCardView>
    with SingleTickerProviderStateMixin {
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
    final colors = theme.colorScheme;
    final studentCtrl = context.watch<StudentController>();
    final profile = studentCtrl.profile;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 32),
      child: Column(
        children: [
          // ---------------------------------------------------------
          // PAGE HEADER
          // ---------------------------------------------------------
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(11),
                decoration: BoxDecoration(
                  color: colors.primary.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  Icons.badge_rounded,
                  color: colors.primary,
                  size: 24,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Digital Student ID',
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.4,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      'Your official digital identity card',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: colors.onSurface.withValues(alpha: 0.55),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ).animate().fadeIn().slideX(
                begin: -0.05,
                end: 0,
              ),

          const SizedBox(height: 26),

          // ---------------------------------------------------------
          // FLIP CARD
          // ---------------------------------------------------------
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
                          child: _buildCardBack(
                            context,
                            profile,
                            theme,
                          ),
                        )
                      : _buildCardFront(
                          context,
                          profile,
                          theme,
                        ),
                );
              },
            ),
          ).animate().fadeIn(delay: 150.ms).scale(),

          const SizedBox(height: 22),

          // ---------------------------------------------------------
          // FLIP HINT
          // ---------------------------------------------------------
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 15,
              vertical: 10,
            ),
            decoration: BoxDecoration(
              color: colors.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: colors.outline.withValues(alpha: 0.10),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.touch_app_rounded,
                  size: 17,
                  color: colors.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  _showFront
                      ? 'Tap card to view QR verification'
                      : 'Tap card to view student details',
                  style: TextStyle(
                    color: colors.onSurface.withValues(alpha: 0.65),
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ).animate().fadeIn(delay: 300.ms),

          const SizedBox(height: 15),

          // Button
          SizedBox(
            height: 52,
            child: ElevatedButton.icon(
              onPressed: _flipCard,
              icon: const Icon(
                Icons.flip_rounded,
                size: 20,
              ),
              label: Text(
                _showFront ? 'View QR Code' : 'View Student Details',
              ),
              style: ElevatedButton.styleFrom(
                elevation: 0,
                backgroundColor: colors.primary,
                foregroundColor: colors.onPrimary,
                padding: const EdgeInsets.symmetric(
                  horizontal: 22,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
            ),
          ).animate().fadeIn(delay: 350.ms),
        ],
      ),
    );
  }

  // ===============================================================
  // FRONT OF ID CARD
  // ===============================================================

  Widget _buildCardFront(
    BuildContext context,
    profile,
    ThemeData theme,
  ) {
    final colors = theme.colorScheme;

    return Container(
      width: double.infinity,
      height: 450,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            colors.primary,
            colors.primary.withValues(alpha: 0.72),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: colors.primary.withValues(alpha: 0.25),
            blurRadius: 30,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Stack(
        children: [
          // Decorative circles
          Positioned(
            top: -70,
            right: -50,
            child: Container(
              width: 190,
              height: 190,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.06),
              ),
            ),
          ),

          Positioned(
            bottom: -90,
            left: -60,
            child: Container(
              width: 210,
              height: 210,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.05),
              ),
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(22),
            child: Column(
              children: [
                // ---------------------------------------------------
                // SCHOOL HEADER
                // ---------------------------------------------------
                Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.13),
                        borderRadius: BorderRadius.circular(15),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.12),
                        ),
                      ),
                      child: const Icon(
                        Icons.school_rounded,
                        color: Colors.white,
                        size: 27,
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'EXCELLENCE ACADEMY',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1,
                            ),
                          ),
                          SizedBox(height: 4),
                          Text(
                            'OFFICIAL STUDENT IDENTITY',
                            style: TextStyle(
                              color: Colors.white70,
                              fontSize: 9,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.7,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(9),
                      ),
                      child: const Icon(
                        Icons.verified_rounded,
                        color: Colors.white,
                        size: 17,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 17),

                Container(
                  height: 1,
                  color: Colors.white.withValues(alpha: 0.12),
                ),

                const SizedBox(height: 19),

                // ---------------------------------------------------
                // PROFILE PHOTO
                // ---------------------------------------------------
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white.withValues(alpha: 0.18),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.25),
                      width: 1.5,
                    ),
                  ),
                  child: StudentAvatar(
                    imageUrl: profile?.photoUrl,
                    radius: 47,
                    innerPadding: 3,
                    backgroundColor: Colors.white,
                    iconColor: colors.primary,
                    iconSize: 50,
                  ),
                ),

                const SizedBox(height: 13),

                // ---------------------------------------------------
                // NAME
                // ---------------------------------------------------
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 15),
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      profile?.fullName ?? 'Student Name',
                      maxLines: 1,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.3,
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 5),

                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 11,
                    vertical: 5,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(9),
                  ),
                  child: Text(
                    'REG ID: ${profile?.studentId ?? 'N/A'}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),

                const Spacer(),

                // ---------------------------------------------------
                // STUDENT INFORMATION
                // ---------------------------------------------------
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 14,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.13),
                    borderRadius: BorderRadius.circular(17),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.08),
                    ),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: _buildInfoColumn(
                          'CLASS',
                          (profile?.className.isNotEmpty ?? false)
                              ? profile!.className
                              : 'N/A',
                        ),
                      ),
                      Container(
                        height: 30,
                        width: 1,
                        color: Colors.white.withValues(alpha: 0.15),
                      ),
                      Expanded(
                        child: _buildInfoColumn(
                          'GENDER',
                          (profile?.genderLabel.isNotEmpty ?? false)
                              ? profile!.genderLabel
                              : 'N/A',
                        ),
                      ),
                      Container(
                        height: 30,
                        width: 1,
                        color: Colors.white.withValues(alpha: 0.15),
                      ),
                      Expanded(
                        child: _buildInfoColumn(
                          'DATE OF BIRTH',
                          (profile?.dob.isNotEmpty ?? false)
                              ? profile!.dob
                              : 'N/A',
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 10),

                const Text(
                  'VALID STUDENT IDENTIFICATION',
                  style: TextStyle(
                    color: Colors.white54,
                    fontSize: 8,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ===============================================================
  // BACK OF ID CARD
  // ===============================================================

  Widget _buildCardBack(
    BuildContext context,
    profile,
    ThemeData theme,
  ) {
    final colors = theme.colorScheme;
    final qrData = profile?.qrCodeData ?? 'STUDENT_ID:${profile?.studentId}';

    return Container(
      width: double.infinity,
      height: 450,
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(
          color: colors.outline.withValues(alpha: 0.10),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 28,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Stack(
        children: [
          // Top decoration
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
              height: 8,
              decoration: BoxDecoration(
                color: colors.primary,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(28),
                  topRight: Radius.circular(28),
                ),
              ),
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // QR Header
                Container(
                  padding: const EdgeInsets.all(11),
                  decoration: BoxDecoration(
                    color: colors.primary.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(13),
                  ),
                  child: Icon(
                    Icons.qr_code_2_rounded,
                    color: colors.primary,
                    size: 25,
                  ),
                ),

                const SizedBox(height: 11),

                Text(
                  'Digital Verification',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.3,
                  ),
                ),

                const SizedBox(height: 4),

                Text(
                  'Scan this QR code to verify student identity',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colors.onSurface.withValues(alpha: 0.52),
                  ),
                ),

                const SizedBox(height: 18),

                // QR Code
                Container(
                  padding: const EdgeInsets.all(15),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: colors.outline.withValues(alpha: 0.10),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.07),
                        blurRadius: 18,
                        offset: const Offset(0, 7),
                      ),
                    ],
                  ),
                  child: QrImageView(
                    data: qrData,
                    version: QrVersions.auto,
                    size: 178,
                    backgroundColor: Colors.white,
                  ),
                ),

                const SizedBox(height: 17),

                // Verification Badge
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 13,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: colors.primary.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.verified_rounded,
                        size: 16,
                        color: colors.primary,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Secure Digital ID',
                        style: TextStyle(
                          color: colors.primary,
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 13),

                // Emergency Contact
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 9,
                  ),
                  decoration: BoxDecoration(
                    color:
                        colors.surfaceContainerHighest.withValues(alpha: 0.55),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.phone_rounded,
                        size: 16,
                        color: colors.primary,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Emergency Contact: ${profile?.phone.isNotEmpty == true ? profile?.phone : 'School Admin'}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: colors.onSurface.withValues(alpha: 0.65),
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ===============================================================
  // INFO COLUMN
  // ===============================================================

  Widget _buildInfoColumn(
    String label,
    String value,
  ) {
    return Column(
      children: [
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: Colors.white54,
            fontSize: 8,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 5),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 3),
          child: Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ],
    );
  }
}

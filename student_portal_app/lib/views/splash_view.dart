import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import 'package:video_player/video_player.dart';

import '../controllers/auth_controller.dart';
import '../theme/app_theme.dart';
import '../widgets/modern_loader.dart';
import 'login_view.dart';
import 'main_scaffold_view.dart';
import 'teacher_dashboard_view.dart';

/// Professional 3D brand intro splash.
///
/// Launch contract:
///  * The screen is immediately branded (navy + gradient) so the user never sees
///    a white/blank flash, even if assets are still decoding.
///  * The 3D logo (`assets/images/logo.png`) is shown instantly with a cinematic
///    scale + glow + fade entrance, and the app name + developer credit fade in
///    beneath it.
///  * The intro video (`assets/videos/intro.mp4`) is buffered in the background.
///    If it becomes ready within the cutoff it cross-fades on top; if not, the
///    animated-logo intro continues and still transitions on timer — no hang.
///  * Tap anywhere (or the top-right "Skip" chip) skips immediately.
///  * After ~3.5s the restored session is inspected and the app navigates to the
///    dashboard (teacher shell / student main scaffold) or to [LoginView] with the
///    School ID pre-filled.
class SplashView extends StatefulWidget {
  const SplashView({super.key});

  @override
  State<SplashView> createState() => _SplashViewState();
}

class _SplashViewState extends State<SplashView> {
  static const String _videoAsset = 'assets/videos/intro.mp4';
  static const String _logoAsset = 'assets/images/logo.png';

  /// How long we wait for the video to become playable before keeping only the
  /// animated-logo intro (which still finishes on its own).
  static const Duration _videoCutoff = Duration(milliseconds: 1500);

  /// Total branded intro time before navigation (gives the logo animation room
  /// to finish and feels smooth rather than abrupt).
  static const Duration _introDuration = Duration(milliseconds: 3500);

  VideoPlayerController? _controller;
  bool _showVideo = false;
  bool _navigated = false;
  Timer? _introTimer;
  Future<void>? _authReady;

  @override
  void initState() {
    super.initState();

    // 1) Brand the chrome immediately (no white flash) and keep it immersive.
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);

    // 2) Restore session in the background (never blocks the intro UI).
    _authReady = _waitUntilAuthReady();

    // 3) Prime the 3D logo asset on the first frame so the first paint is instant.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      precacheImage(const AssetImage(_logoAsset), context);
    });

    // 4) Try to buffer the intro video; if it is ready in time it takes over.
    unawaited(_tryPlayVideo());

    // 5) The intro always ends on its own (video or logo), then we route.
    _introTimer = Timer(_introDuration, _goNext);
  }

  /// Restores auth state in the background and resolves when the controller is
  /// initialized. If it takes too long we still navigate (unauthenticated path).
  Future<void> _waitUntilAuthReady() async {
    final auth = context.read<AuthController>();
    final deadline = DateTime.now().add(const Duration(seconds: 6));
    while (!auth.isInitialized) {
      if (!mounted) return;
      if (DateTime.now().isAfter(deadline)) return;
      await Future<void>.delayed(const Duration(milliseconds: 60));
    }
  }

  /// Background-only: attempt to initialize + play the intro video. If anything
  /// goes wrong (missing asset, decoder issue, or too slow) we simply keep the
  /// animated-logo intro — never crash or hang.
  Future<void> _tryPlayVideo() async {
    final controller = VideoPlayerController.asset(_videoAsset);
    _controller = controller;
    final stopwatch = Stopwatch()..start();
    try {
      await controller.initialize();
      final elapsed = stopwatch.elapsed;
      if (!mounted ||
          !controller.value.isInitialized ||
          elapsed > _videoCutoff) {
        throw StateError('video not ready in time');
      }
      if (!mounted) return;
      controller.addListener(_onVideoTick);
      setState(() {
        _showVideo = true;
      });
      await controller.play();
    } catch (_) {
      if (mounted) {
        setState(() {
          _controller = null;
        });
      }
      try {
        await controller.dispose();
      } catch (_) {
        // ignore double-dispose on failed init
      }
    }
  }

  void _onVideoTick() {
    final controller = _controller;
    if (controller == null || _navigated) return;
    final value = controller.value;
    if (value.hasError) {
      controller.removeListener(_onVideoTick);
      _controller = null;
      try {
        controller.dispose();
      } catch (_) {}
      return;
    }
    if (value.duration > Duration.zero &&
        !value.isPlaying &&
        value.position >= value.duration) {
      _goNext();
    }
  }

  /// Navigate to the screen that matches the restored session.
  Future<void> _goNext() async {
    if (_navigated || !mounted) return;
    _navigated = true;
    _introTimer?.cancel();
    _controller?.removeListener(_onVideoTick);
    final c = _controller;
    _controller = null;
    if (c != null) {
      try {
        c.dispose();
      } catch (_) {}
    }

    await _authReady;
    if (!mounted) return;

    final auth = context.read<AuthController>();
    final destination = auth.isAuthenticated
        ? (auth.session?.role == 'TEACHER'
            ? const TeacherDashboardView()
            : const MainScaffoldView())
        : const LoginView();

    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => destination,
        transitionsBuilder: (_, animation, __, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 450),
      ),
    );
  }

  @override
  void dispose() {
    _introTimer?.cancel();
    final c = _controller;
    _controller = null;
    if (c != null) {
      c.removeListener(_onVideoTick);
      try {
        c.dispose();
      } catch (_) {}
    }
    super.dispose();
  }

  /// 3D logo with modern fade + scale + glowing pulse.
  Widget _buildLogo(ThemeData theme) {
    return Image.asset(
      _logoAsset,
      width: 156,
      height: 156,
      filterQuality: FilterQuality.high,
    ).animate()
        .fadeIn(delay: 80.ms, duration: 700.ms)
        .scale(
          begin: const Offset(0.72, 0.72),
          end: const Offset(1, 1),
          duration: 950.ms,
          curve: Curves.easeOutBack,
        );
  }

  /// App name with subtle upward slide + fade.
  Widget _buildAppName(ThemeData theme) {
    return Text(
      'School Student Portal',
      textAlign: TextAlign.center,
      style: theme.textTheme.headlineSmall?.copyWith(
        fontWeight: FontWeight.w700,
        color: Colors.white,
        letterSpacing: 0.6,
      ),
    ).animate().fadeIn(delay: 260.ms, duration: 700.ms).slideY(begin: 0.22, end: 0);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasVideo = _showVideo && _controller != null &&
        _controller!.value.isInitialized;

    return Scaffold(
      backgroundColor: BrandColors.navy,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // Branded underlay — guarantees no white flash at any point.
          SafeArea(
            bottom: false,
            child: Container(
              decoration: const BoxDecoration(
                gradient: BrandColors.navyGradient,
              ),
            ),
          ),

          // Subtle animated vignette so the brand frame feels alive.
          Positioned.fill(
            child: IgnorePointer(
              child: _buildVignette(theme),
            ),
          ),

          // ---- Foreground branding (logo + text + footer + optional video) ----
          SafeArea(
            child: Column(
              children: [
                const Spacer(flex: 4),
                Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 340),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // 3D logo — always present, cinematic entrance.
                        _buildLogo(theme),
                        const SizedBox(height: 34),
                        // App name.
                        _buildAppName(theme),
                        const SizedBox(height: 10),
                        // Developer credit footer.
                        _buildFooter(theme),
                      ],
                    ),
                  ),
                ),
                const Spacer(flex: 2),
                // Subtle branded pulse while the intro runs.
                const ButtonSpinner(size: 28)
                    .animate(onPlay: (c) => c.repeat())
                    .fade(
                      begin: 0.3,
                      end: 1,
                      duration: 1100.ms,
                      curve: Curves.easeInOut,
                    ),
                const SizedBox(height: 22),
              ],
            ),
          ),

          // Video layer — cross-fades in on top when ready.
          if (hasVideo)
            FittedBox(
              fit: BoxFit.cover,
              child: SizedBox(
                width: _controller!.value.size.width,
                height: _controller!.value.size.height,
                child: VideoPlayer(_controller!),
              ),
            ).animate().fadeIn(duration: 500.ms, curve: Curves.easeOut),

          // Skip affordance (tap-anywhere via GestureDetector on the root also skips).
          Align(
            alignment: Alignment.topRight,
            child: Padding(
              padding: const EdgeInsets.only(top: 18, right: 18),
              child: TextButton(
                onPressed: _goNext,
                style: TextButton.styleFrom(
                  foregroundColor: Colors.white.withValues(alpha: 0.9),
                  backgroundColor: Colors.black.withValues(alpha: 0.25),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(30),
                  ),
                ),
                child: const Text(
                  'Skip',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.6,
                  ),
                ),
              ),
            ).animate().fadeIn(delay: 700.ms, duration: 500.ms),
          ),

          // Tap-anywhere skip.
          Positioned.fill(
            child: GestureDetector(
              behavior: HitTestBehavior.translucent,
              onTap: _goNext,
            ),
          ),
        ],
      ),
    );
  }
  /// Footer line: product name + developer credit.
  Widget _buildFooter(ThemeData theme) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 340),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'School Management System',
            textAlign: TextAlign.center,
            style: theme.textTheme.titleMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.92),
              fontWeight: FontWeight.w600,
              letterSpacing: 0.8,
            ),
          ).animate().fadeIn(delay: 420.ms, duration: 700.ms).slideY(begin: 0.18, end: 0),
          const SizedBox(height: 6),
          Text(
            'Developed by Abdul Mueed Khan',
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.78),
              fontStyle: FontStyle.italic,
              letterSpacing: 1.0,
            ),
          ).animate().fadeIn(delay: 620.ms, duration: 700.ms).slideY(begin: 0.14, end: 0),
        ],
      ),
    );
  }

  /// Soft radial vignette so the branded frame feels cinematic, not flat.
  Widget _buildVignette(ThemeData theme) {
    return Container(
      decoration: BoxDecoration(
        gradient: RadialGradient(
          center: Alignment.topCenter,
          radius: 1.15,
          colors: [
            Colors.white.withValues(alpha: 0.05),
            Colors.transparent,
            BrandColors.navy.withValues(alpha: 0.25),
          ],
          stops: const [0.0, 0.45, 1.0],
        ),
      ),
    );
  }
}

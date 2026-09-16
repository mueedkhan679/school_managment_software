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

class SplashView extends StatefulWidget {
  const SplashView({super.key});

  @override
  State<SplashView> createState() => _SplashViewState();
}

class _SplashViewState extends State<SplashView> {
  static const String _videoAsset = 'assets/videos/intro.mp4';
  static const String _logoAsset = 'assets/images/logo.png';

  static const Duration _videoCutoff = Duration(milliseconds: 1500);
  static const Duration _introDuration = Duration(milliseconds: 3500);

  VideoPlayerController? _controller;

  bool _showVideo = false;
  bool _navigated = false;
  bool _authReady = false;

  Timer? _timer;

  @override
  void initState() {
    super.initState();

    SystemChrome.setEnabledSystemUIMode(
      SystemUiMode.immersiveSticky,
    );

    _waitUntilAuthReady();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _precacheLogo();
      _tryPlayVideo();
    });

    _timer = Timer(_introDuration, _goNext);
  }

  Future<void> _precacheLogo() async {
    if (!mounted) return;

    try {
      await precacheImage(
        const AssetImage(_logoAsset),
        context,
      );
    } catch (_) {}
  }

  Future<void> _waitUntilAuthReady() async {
    try {
      final auth = context.read<AuthController>();

      const maxWait = Duration(seconds: 6);
      const interval = Duration(milliseconds: 100);

      final started = DateTime.now();

      while (mounted &&
          !auth.isInitialized &&
          DateTime.now().difference(started) < maxWait) {
        await Future.delayed(interval);
      }

      if (mounted) {
        setState(() {
          _authReady = auth.isInitialized;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _authReady = true;
        });
      }
    }
  }

  Future<void> _tryPlayVideo() async {
    VideoPlayerController? controller;

    try {
      controller = VideoPlayerController.asset(_videoAsset);

      _controller = controller;

      await controller.initialize().timeout(_videoCutoff);

      if (!mounted || _navigated) {
        await controller.dispose();
        return;
      }

      controller.setLooping(false);
      controller.setVolume(0);

      controller.addListener(_videoListener);

      setState(() {
        _showVideo = true;
      });

      await controller.play();
    } catch (_) {
      if (controller != null) {
        controller.removeListener(_videoListener);
        await controller.dispose();
      }

      if (_controller == controller) {
        _controller = null;
      }

      if (mounted) {
        setState(() {
          _showVideo = false;
        });
      }
    }
  }

  void _videoListener() {
    final controller = _controller;

    if (controller == null) return;

    if (controller.value.hasError) {
      _disposeVideo();
      return;
    }

    if (controller.value.isInitialized &&
        controller.value.position >= controller.value.duration &&
        controller.value.duration > Duration.zero) {
      _goNext();
    }
  }

  void _disposeVideo() {
    final controller = _controller;

    _controller = null;

    if (controller != null) {
      controller.removeListener(_videoListener);
      controller.dispose();
    }

    if (mounted) {
      setState(() {
        _showVideo = false;
      });
    }
  }

  Future<void> _goNext() async {
    if (_navigated || !mounted) return;

    _navigated = true;

    _timer?.cancel();
    _timer = null;

    _disposeVideo();

    final auth = context.read<AuthController>();

    if (!_authReady && !auth.isInitialized) {
      const maxWait = Duration(seconds: 3);
      const interval = Duration(milliseconds: 100);

      final started = DateTime.now();

      while (mounted &&
          !auth.isInitialized &&
          DateTime.now().difference(started) < maxWait) {
        await Future.delayed(interval);
      }
    }

    if (!mounted) return;

    Widget destination;

    if (auth.isAuthenticated) {
      final role = (auth.session?.role ?? '').toUpperCase();

      if (role == 'TEACHER') {
        destination = TeacherDashboardView();
      } else {
        destination = const MainScaffoldView();
      }
    } else {
      destination = const LoginView();
    }

    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => destination,
        transitionDuration: const Duration(milliseconds: 650),
        reverseTransitionDuration: const Duration(milliseconds: 400),
        transitionsBuilder: (_, animation, __, child) {
          return FadeTransition(
            opacity: CurvedAnimation(
              parent: animation,
              curve: Curves.easeOutCubic,
            ),
            child: child,
          );
        },
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    _timer = null;

    final controller = _controller;

    if (controller != null) {
      controller.removeListener(_videoListener);
      controller.dispose();
    }

    _controller = null;

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);

    return Scaffold(
      backgroundColor: const Color(0xFF07111F),
      body: Stack(
        fit: StackFit.expand,
        children: [
          _buildBackground(),
          if (_showVideo && _controller != null) _buildVideoBackground(),
          _buildGradientOverlay(),
          _buildDecorations(size),
          SafeArea(
            child: Column(
              children: [
                _buildTopBranding(),
                const Spacer(),
                _buildMainBrand(),
                const SizedBox(height: 42),
                _buildLoadingIndicator(),
                const SizedBox(height: 28),
                _buildBottomBranding(),
                const SizedBox(height: 22),
              ],
            ),
          ),
          _buildSkipButton(),
          Positioned.fill(
            child: GestureDetector(
              behavior: HitTestBehavior.translucent,
              onTap: _goNext,
              child: const SizedBox.expand(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBackground() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF07111F),
            Color(0xFF0A1830),
            Color(0xFF10294A),
            Color(0xFF06101D),
          ],
        ),
      ),
    );
  }

  Widget _buildVideoBackground() {
    final controller = _controller!;

    return AnimatedOpacity(
      duration: const Duration(milliseconds: 800),
      opacity: _showVideo ? 1 : 0,
      child: FittedBox(
        fit: BoxFit.cover,
        child: SizedBox(
          width: controller.value.size.width,
          height: controller.value.size.height,
          child: VideoPlayer(controller),
        ),
      ),
    );
  }

  Widget _buildGradientOverlay() {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFF020817).withOpacity(.82),
            const Color(0xFF07111F).withOpacity(.55),
            const Color(0xFF07111F).withOpacity(.78),
            const Color(0xFF020817).withOpacity(.96),
          ],
          stops: const [
            0.0,
            0.38,
            0.68,
            1.0,
          ],
        ),
      ),
    );
  }

  Widget _buildDecorations(Size size) {
    return IgnorePointer(
      child: Stack(
        children: [
          Positioned(
            top: -120,
            right: -90,
            child: _glowCircle(
              size: 300,
              color: const Color(0xFF3B82F6),
            ),
          ),
          Positioned(
            top: size.height * .30,
            left: -170,
            child: _glowCircle(
              size: 320,
              color: const Color(0xFF06B6D4),
            ),
          ),
          Positioned(
            bottom: -160,
            right: -100,
            child: _glowCircle(
              size: 360,
              color: const Color(0xFF6366F1),
            ),
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
              height: 1,
              color: Colors.white.withOpacity(.08),
            ),
          ),
        ],
      ),
    );
  }

  Widget _glowCircle({
    required double size,
    required Color color,
  }) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            color.withOpacity(.18),
            color.withOpacity(.05),
            Colors.transparent,
          ],
        ),
      ),
    );
  }

  Widget _buildTopBranding() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 22, 24, 0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _glassIcon(
            icon: Icons.school_rounded,
          ),
          Row(
            children: [
              Container(
                width: 7,
                height: 7,
                decoration: const BoxDecoration(
                  color: Color(0xFF34D399),
                  shape: BoxShape.circle,
                ),
              )
                  .animate(
                    onPlay: (controller) => controller.repeat(
                      reverse: true,
                    ),
                  )
                  .fade(
                    begin: .35,
                    end: 1,
                    duration: const Duration(milliseconds: 900),
                  ),
              const SizedBox(width: 8),
              Text(
                'SYSTEM READY',
                style: TextStyle(
                  color: Colors.white.withOpacity(.62),
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _glassIcon({
    required IconData icon,
  }) {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(.07),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Colors.white.withOpacity(.10),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(.18),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Icon(
        icon,
        color: Colors.white.withOpacity(.88),
        size: 21,
      ),
    );
  }

  Widget _buildMainBrand() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: Column(
        children: [
          _buildLogo(),
          const SizedBox(height: 30),
          Text(
            'SCHOOL',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(.62),
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: 5,
            ),
          )
              .animate()
              .fadeIn(
                duration: const Duration(milliseconds: 700),
                delay: const Duration(milliseconds: 150),
              )
              .slideY(
                begin: .25,
                end: 0,
                duration: const Duration(milliseconds: 700),
              ),
          const SizedBox(height: 7),
          const Text(
            'Management App',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: 34,
              height: 1.05,
              fontWeight: FontWeight.w800,
              letterSpacing: -.8,
            ),
          )
              .animate()
              .fadeIn(
                duration: const Duration(milliseconds: 800),
                delay: const Duration(milliseconds: 250),
              )
              .slideY(
                begin: .22,
                end: 0,
                duration: const Duration(milliseconds: 800),
                curve: Curves.easeOutCubic,
              ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 15,
              vertical: 8,
            ),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(.06),
              borderRadius: BorderRadius.circular(30),
              border: Border.all(
                color: Colors.white.withOpacity(.10),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.auto_awesome_rounded,
                  color: Color(0xFF60A5FA),
                  size: 15,
                ),
                const SizedBox(width: 7),
                Text(
                  'Smart • Simple • Powerful',
                  style: TextStyle(
                    color: Colors.white.withOpacity(.72),
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    letterSpacing: .3,
                  ),
                ),
              ],
            ),
          )
              .animate()
              .fadeIn(
                duration: const Duration(milliseconds: 700),
                delay: const Duration(milliseconds: 450),
              )
              .scale(
                begin: const Offset(.92, .92),
                end: const Offset(1, 1),
                duration: const Duration(milliseconds: 700),
              ),
        ],
      ),
    );
  }

  Widget _buildLogo() {
    return Stack(
      alignment: Alignment.center,
      children: [
        Container(
          width: 184,
          height: 184,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                const Color(0xFF3B82F6).withOpacity(.28),
                const Color(0xFF2563EB).withOpacity(.08),
                Colors.transparent,
              ],
            ),
          ),
        )
            .animate(
              onPlay: (controller) => controller.repeat(
                reverse: true,
              ),
            )
            .scale(
              begin: const Offset(.88, .88),
              end: const Offset(1.08, 1.08),
              duration: const Duration(milliseconds: 1800),
              curve: Curves.easeInOut,
            ),
        Container(
          width: 132,
          height: 132,
          padding: const EdgeInsets.all(17),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(.075),
            shape: BoxShape.circle,
            border: Border.all(
              color: Colors.white.withOpacity(.16),
              width: 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF3B82F6).withOpacity(.20),
                blurRadius: 35,
                spreadRadius: 4,
              ),
              BoxShadow(
                color: Colors.black.withOpacity(.25),
                blurRadius: 25,
                offset: const Offset(0, 15),
              ),
            ],
          ),
          child: ClipOval(
            child: Image.asset(
              _logoAsset,
              fit: BoxFit.contain,
              errorBuilder: (_, __, ___) {
                return Container(
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [
                        Color(0xFF2563EB),
                        Color(0xFF06B6D4),
                      ],
                    ),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.school_rounded,
                    color: Colors.white,
                    size: 52,
                  ),
                );
              },
            ),
          ),
        )
            .animate()
            .fadeIn(
              duration: const Duration(milliseconds: 850),
            )
            .scale(
              begin: const Offset(.55, .55),
              end: const Offset(1, 1),
              duration: const Duration(milliseconds: 900),
              curve: Curves.easeOutBack,
            )
            .rotate(
              begin: -.025,
              end: 0,
              duration: const Duration(milliseconds: 900),
            ),
      ],
    );
  }

  Widget _buildLoadingIndicator() {
    return Column(
      children: [
        SizedBox(
          width: 42,
          height: 42,
          child: Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 38,
                height: 38,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    Colors.white.withOpacity(.20),
                  ),
                ),
              ),
              SizedBox(
                width: 38,
                height: 38,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  valueColor: const AlwaysStoppedAnimation<Color>(
                    Color(0xFF60A5FA),
                  ),
                ),
              )
                  .animate(
                    onPlay: (controller) => controller.repeat(),
                  )
                  .rotate(
                    duration: const Duration(milliseconds: 1100),
                  ),
              const Icon(
                Icons.arrow_forward_rounded,
                color: Colors.white,
                size: 16,
              ),
            ],
          ),
        ),
        const SizedBox(height: 13),
        Text(
          'Preparing your portal...',
          style: TextStyle(
            color: Colors.white.withOpacity(.50),
            fontSize: 11,
            fontWeight: FontWeight.w500,
            letterSpacing: .4,
          ),
        ),
      ],
    ).animate().fadeIn(
          duration: const Duration(milliseconds: 700),
          delay: const Duration(milliseconds: 650),
        );
  }

  Widget _buildBottomBranding() {
    return Column(
      children: [
        Text(
          'School Management System',
          style: TextStyle(
            color: Colors.white.withOpacity(.48),
            fontSize: 11,
            fontWeight: FontWeight.w500,
            letterSpacing: .7,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 22,
              height: 1,
              color: Colors.white.withOpacity(.12),
            ),
            const SizedBox(width: 10),
            Text(
              'Developed by',
              style: TextStyle(
                color: Colors.white.withOpacity(.38),
                fontSize: 9,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(width: 5),
            const Text(
              'Abdul Mueed Khan',
              style: TextStyle(
                color: Color(0xFF93C5FD),
                fontSize: 10,
                fontWeight: FontWeight.w700,
                letterSpacing: .3,
              ),
            ),
            const SizedBox(width: 10),
            Container(
              width: 22,
              height: 1,
              color: Colors.white.withOpacity(.12),
            ),
          ],
        ),
      ],
    )
        .animate()
        .fadeIn(
          duration: const Duration(milliseconds: 800),
          delay: const Duration(milliseconds: 800),
        )
        .slideY(
          begin: .15,
          end: 0,
          duration: const Duration(milliseconds: 700),
        );
  }

  Widget _buildSkipButton() {
    return Positioned(
      top: MediaQuery.paddingOf(context).top + 20,
      right: 22,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(30),
          onTap: _goNext,
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 14,
              vertical: 9,
            ),
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(.20),
              borderRadius: BorderRadius.circular(30),
              border: Border.all(
                color: Colors.white.withOpacity(.10),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Skip',
                  style: TextStyle(
                    color: Colors.white.withOpacity(.72),
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(width: 5),
                Icon(
                  Icons.arrow_forward_ios_rounded,
                  color: Colors.white.withOpacity(.55),
                  size: 10,
                ),
              ],
            ),
          ),
        ),
      ),
    )
        .animate()
        .fadeIn(
          duration: const Duration(milliseconds: 600),
          delay: const Duration(milliseconds: 500),
        )
        .slideX(
          begin: .2,
          end: 0,
          duration: const Duration(milliseconds: 600),
        );
  }
}

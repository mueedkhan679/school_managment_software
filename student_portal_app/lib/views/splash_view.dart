import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import '../controllers/auth_controller.dart';
import '../theme/app_theme.dart';
import '../widgets/modern_loader.dart';
import '../widgets/school_logo.dart';
import 'login_view.dart';
import 'main_scaffold_view.dart';
import 'teacher_dashboard_view.dart';

/// Branded app-startup screen.
///
/// Shows the school logo (dynamic asset/network image with a crisp vector
/// badge fallback), the app name and the "Developed by Mueed" credit with a
/// smooth fade-in, then routes to the correct screen based on the restored
/// auth session.
class SplashView extends StatefulWidget {
  const SplashView({super.key});

  @override
  State<SplashView> createState() => _SplashViewState();
}

class _SplashViewState extends State<SplashView> {
  static const Duration _splashDuration = Duration(milliseconds: 2600);

  @override
  void initState() {
    super.initState();
    Future.delayed(_splashDuration, _goNext);
  }

  /// Route to whichever screen matches the (possibly restored) session.
  void _goNext() {
    if (!mounted) return;
    Widget target = const LoginView();
    // Session restore happens asynchronously in AuthController; whatever its
    // state is at the end of the splash window decides the destination.
    // (Silently imported through the provider tree — no watch here, we only
    // need a one-shot read.)
    final auth = context.read<AuthController>();
    if (auth.isAuthenticated && auth.session != null) {
      target = auth.session!.role == 'TEACHER'
          ? const TeacherDashboardView()
          : const MainScaffoldView();
    }
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => target,
        transitionsBuilder: (_, animation, __, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 450),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: BrandColors.navyGradient),
        child: SafeArea(
          child: SizedBox(
            width: double.infinity,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Spacer(flex: 5),

                // School logo — tries a network image, then a bundled asset,
                // and finally falls back to the built-in vector badge.
                const SchoolLogo(
                  size: 118,
                  networkUrl: String.fromEnvironment(
                    'SCHOOL_LOGO_URL',
                    defaultValue: '',
                  ),
                ).animate().fadeIn(
                      duration: 900.ms,
                      curve: Curves.easeOut,
                    ).scale(
                      begin: const Offset(0.85, 0.85),
                      end: const Offset(1, 1),
                      duration: 900.ms,
                      curve: Curves.easeOutBack,
                    ),

                const SizedBox(height: 28),

                // App name.
                Text(
                  'School Student Portal',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                        letterSpacing: 0.4,
                      ),
                ).animate().fadeIn(
                      delay: 350.ms,
                      duration: 700.ms,
                    ).slideY(begin: 0.25, end: 0),

                const SizedBox(height: 10),

                // Stylish developer credit.
                Text(
                  'Developed by Mueed',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white.withValues(alpha: 0.72),
                        fontStyle: FontStyle.italic,
                        letterSpacing: 1.2,
                      ),
                ).animate().fadeIn(
                      delay: 700.ms,
                      duration: 700.ms,
                    ).slideY(begin: 0.2, end: 0),

                const Spacer(flex: 4),

                // Subtle loading pulse while the session is restored.
                const ButtonSpinner(size: 26).animate(onPlay: (c) => c.repeat()).fade(
                      begin: 0.35,
                      end: 1,
                      duration: 900.ms,
                      curve: Curves.easeInOut,
                    ),

                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

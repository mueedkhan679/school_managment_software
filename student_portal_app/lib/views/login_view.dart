import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import '../controllers/auth_controller.dart';
import '../controllers/student_controller.dart';
import '../controllers/teacher_controller.dart';
import 'main_scaffold_view.dart';
import 'teacher_dashboard_view.dart';

class LoginView extends StatefulWidget {
  const LoginView({super.key});

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    ScaffoldMessenger.of(context).clearSnackBars();

    final auth = context.read<AuthController>();
    final success = await auth.login(
      _usernameController.text.trim(),
      _passwordController.text,
    );

                       if (success && mounted) {
      ScaffoldMessenger.of(context).clearSnackBars();
      final session = auth.session;
      if (session != null && session.role == 'TEACHER') {
        final tc = context.read<TeacherController>();
        tc.clearAllData();
        tc.setProfileFromSession(session);
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const TeacherDashboardView()),
        );
      } else {
        context.read<StudentController>().fetchAllData();
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const MainScaffoldView()),
        );
      }
    } else if (mounted && auth.errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(auth.errorMessage!),
          backgroundColor: Theme.of(context).colorScheme.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final auth = context.watch<AuthController>();

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              theme.colorScheme.primaryContainer.withValues(alpha: 0.4),
              theme.colorScheme.surface,
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 28.0, vertical: 20.0),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // School Logo / Header
                    Icon(
                      Icons.school_rounded,
                      size: 80,
                      color: theme.colorScheme.primary,
                    )
                        .animate()
                        .scale(duration: 500.ms, curve: Curves.easeOutBack)
                        .fade(duration: 400.ms),
                    const SizedBox(height: 16),
                    Text(
                      'School Student Portal',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.onSurface,
                      ),
                    ).animate().fadeIn(delay: 200.ms).slideY(begin: 0.2, end: 0),
                    const SizedBox(height: 8),
                    Text(
                      'Sign in with your Student ID or Username',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ).animate().fadeIn(delay: 300.ms),
                    const SizedBox(height: 36),

                    // Username / Student ID Input
                    TextFormField(
                      controller: _usernameController,
                      keyboardType: TextInputType.text,
                      decoration: InputDecoration(
                        labelText: 'Username or Student Registration ID',
                        hintText: 'e.g. STU-000001',
                        prefixIcon: const Icon(Icons.person_outline_rounded),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                        filled: true,
                        fillColor: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.3),
                      ),
                      validator: (val) {
                        if (val == null || val.trim().isEmpty) {
                          return 'Please enter your username or Student ID';
                        }
                        return null;
                      },
                    ).animate().fadeIn(delay: 400.ms).slideY(begin: 0.1, end: 0),
                    const SizedBox(height: 18),

                    // Password Input
                    TextFormField(
                      controller: _passwordController,
                      obscureText: _obscurePassword,
                      decoration: InputDecoration(
                        labelText: 'Password',
                        prefixIcon: const Icon(Icons.lock_outline_rounded),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePassword ? Icons.visibility_off : Icons.visibility,
                          ),
                          onPressed: () {
                            setState(() {
                              _obscurePassword = !_obscurePassword;
                            });
                          },
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                        filled: true,
                        fillColor: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.3),
                      ),
                      validator: (val) {
                        if (val == null || val.isEmpty) {
                          return 'Please enter your password';
                        }
                        return null;
                      },
                    ).animate().fadeIn(delay: 500.ms).slideY(begin: 0.1, end: 0),
                    const SizedBox(height: 12),

                    // Remember Me Checkbox
                    Row(
                      children: [
                        Checkbox(
                          value: auth.rememberMe,
                          onChanged: auth.toggleRememberMe,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                        const Text('Remember Me'),
                        const Spacer(),
                        Flexible(
                          child: TextButton(
                            onPressed: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Contact school administration for password reset.'),
                                ),
                              );
                            },
                            child: const Text(
                              'Forgot Password?',
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ),
                      ],
                    ).animate().fadeIn(delay: 600.ms),
                    const SizedBox(height: 24),

                    // Login Button
                    SizedBox(
                      height: 54,
                      child: FilledButton(
                        onPressed: auth.status == AuthStatus.authenticating ? null : _handleLogin,
                        style: FilledButton.styleFrom(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                        ),
                        child: auth.status == AuthStatus.authenticating
                            ? const SizedBox(
                                height: 24,
                                width: 24,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2.5,
                                  color: Colors.white,
                                ),
                              )
                            : const Text(
                                'Sign In',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                      ),
                    ).animate().fadeIn(delay: 700.ms).scale(),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

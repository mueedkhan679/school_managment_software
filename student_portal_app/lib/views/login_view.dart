import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import '../controllers/auth_controller.dart';
import '../controllers/student_controller.dart';
import '../controllers/teacher_controller.dart';
import '../services/storage_service.dart';
import 'main_scaffold_view.dart';
import 'teacher_dashboard_view.dart';
import '../widgets/modern_loader.dart';

class LoginView extends StatefulWidget {
  const LoginView({super.key});

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _schoolController = TextEditingController();

  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    _loadSavedSchool();
  }

  Future<void> _loadSavedSchool() async {
    final slug = await StorageService().getTenantSlug();

    if (slug != null && slug.isNotEmpty && mounted) {
      setState(() {
        _schoolController.text = slug;
      });
    }
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _schoolController.dispose();
    super.dispose();
  }

  void _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    ScaffoldMessenger.of(context).clearSnackBars();

    final auth = context.read<AuthController>();

    final success = await auth.login(
      _usernameController.text.trim(),
      _passwordController.text,
      schoolSlug: _schoolController.text.trim().isNotEmpty
          ? _schoolController.text.trim()
          : null,
    );

    if (success && mounted) {
      ScaffoldMessenger.of(context).clearSnackBars();

      final session = auth.session;

      if (session != null && session.role == 'TEACHER') {
        final tc = context.read<TeacherController>();

        tc.clearAllData();
        tc.setProfileFromSession(session);

        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => const TeacherDashboardView(),
          ),
        );
      } else {
        final sc = context.read<StudentController>();

        sc.clearAllData();
        sc.fetchAllData();

        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => const MainScaffoldView(),
          ),
        );
      }
    } else if (mounted && auth.errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(
                Icons.error_outline_rounded,
                color: Colors.white,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(auth.errorMessage!),
              ),
            ],
          ),
          backgroundColor: Theme.of(context).colorScheme.error,
          behavior: SnackBarBehavior.floating,
          margin: const EdgeInsets.all(16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final auth = context.watch<AuthController>();

    final isLoading = auth.status == AuthStatus.authenticating;

    return Scaffold(
      backgroundColor: colors.surface,
      body: Stack(
        children: [
          // =============================================================
          // BACKGROUND
          // =============================================================

          Positioned.fill(
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    colors.primary.withValues(alpha: 0.12),
                    colors.surface,
                    colors.primaryContainer.withValues(alpha: 0.18),
                  ],
                ),
              ),
            ),
          ),

          // Decorative top-right circle
          Positioned(
            top: -120,
            right: -100,
            child: Container(
              height: 280,
              width: 280,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: colors.primary.withValues(alpha: 0.08),
              ),
            ),
          ),

          // Decorative bottom-left circle
          Positioned(
            bottom: -150,
            left: -120,
            child: Container(
              height: 300,
              width: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: colors.primaryContainer.withValues(alpha: 0.18),
              ),
            ),
          ),

          // =============================================================
          // CONTENT
          // =============================================================

          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 28,
                ),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxWidth: 480,
                  ),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // =================================================
                        // BRAND / LOGO
                        // =================================================

                        Center(
                          child: Container(
                            height: 92,
                            width: 92,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  colors.primary,
                                  colors.primaryContainer,
                                ],
                              ),
                              borderRadius: BorderRadius.circular(28),
                              boxShadow: [
                                BoxShadow(
                                  color: colors.primary.withValues(alpha: 0.25),
                                  blurRadius: 25,
                                  offset: const Offset(0, 12),
                                ),
                              ],
                            ),
                            child: const Icon(
                              Icons.school_rounded,
                              size: 48,
                              color: Colors.white,
                            ),
                          ),
                        )
                            .animate()
                            .scale(
                              duration: 600.ms,
                              curve: Curves.easeOutBack,
                            )
                            .fadeIn(duration: 400.ms),

                        const SizedBox(height: 22),

                        // =================================================
                        // TITLE
                        // =================================================

                        Text(
                          'School Portal',
                          textAlign: TextAlign.center,
                          style: theme.textTheme.headlineMedium?.copyWith(
                            fontWeight: FontWeight.w900,
                            letterSpacing: -0.7,
                            color: colors.onSurface,
                          ),
                        ).animate().fadeIn(delay: 150.ms).slideY(
                              begin: 0.15,
                              end: 0,
                            ),

                        const SizedBox(height: 7),

                        Text(
                          'Sign in to access your academic dashboard',
                          textAlign: TextAlign.center,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: colors.onSurfaceVariant,
                            fontSize: 13,
                          ),
                        ).animate().fadeIn(delay: 250.ms),

                        const SizedBox(height: 30),

                        // =================================================
                        // LOGIN CARD
                        // =================================================

                        Container(
                          padding: const EdgeInsets.fromLTRB(
                            20,
                            22,
                            20,
                            20,
                          ),
                          decoration: BoxDecoration(
                            color: colors.surface.withValues(
                              alpha: 0.94,
                            ),
                            borderRadius: BorderRadius.circular(28),
                            border: Border.all(
                              color:
                                  colors.outlineVariant.withValues(alpha: 0.45),
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(
                                  alpha: 0.06,
                                ),
                                blurRadius: 30,
                                offset: const Offset(0, 12),
                              ),
                            ],
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              // Card heading
                              Row(
                                children: [
                                  Container(
                                    height: 38,
                                    width: 38,
                                    decoration: BoxDecoration(
                                      color: colors.primary
                                          .withValues(alpha: 0.10),
                                      borderRadius: BorderRadius.circular(11),
                                    ),
                                    child: Icon(
                                      Icons.lock_open_rounded,
                                      color: colors.primary,
                                      size: 20,
                                    ),
                                  ),
                                  const SizedBox(width: 11),
                                  Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'Welcome Back',
                                        style: theme.textTheme.titleMedium
                                            ?.copyWith(
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                      Text(
                                        'Enter your account details',
                                        style:
                                            theme.textTheme.bodySmall?.copyWith(
                                          color: colors.onSurfaceVariant,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),

                              const SizedBox(height: 24),

                              // =================================================
                              // SCHOOL ID
                              // =================================================

                              _buildField(
                                controller: _schoolController,
                                label: 'School ID',
                                hint: 'e.g. demo-school',
                                icon: Icons.apartment_rounded,
                                colors: colors,
                                keyboardType: TextInputType.text,
                                validator: (val) {
                                  if (val == null || val.trim().isEmpty) {
                                    return 'Please enter your School ID';
                                  }

                                  return null;
                                },
                              ).animate().fadeIn(delay: 300.ms).slideY(
                                    begin: 0.08,
                                    end: 0,
                                  ),

                              const SizedBox(height: 16),

                              // =================================================
                              // USERNAME
                              // =================================================

                              _buildField(
                                controller: _usernameController,
                                label: 'Username / Student ID',
                                hint: 'e.g. STU-000001',
                                icon: Icons.person_outline_rounded,
                                colors: colors,
                                keyboardType: TextInputType.text,
                                validator: (val) {
                                  if (val == null || val.trim().isEmpty) {
                                    return 'Please enter your username or Student ID';
                                  }

                                  return null;
                                },
                              ).animate().fadeIn(delay: 400.ms).slideY(
                                    begin: 0.08,
                                    end: 0,
                                  ),

                              const SizedBox(height: 16),

                              // =================================================
                              // PASSWORD
                              // =================================================

                              _buildField(
                                controller: _passwordController,
                                label: 'Password',
                                hint: 'Enter your password',
                                icon: Icons.lock_outline_rounded,
                                colors: colors,
                                obscureText: _obscurePassword,
                                suffixIcon: IconButton(
                                  tooltip: _obscurePassword
                                      ? 'Show password'
                                      : 'Hide password',
                                  icon: Icon(
                                    _obscurePassword
                                        ? Icons.visibility_off_rounded
                                        : Icons.visibility_rounded,
                                    color: colors.onSurfaceVariant,
                                  ),
                                  onPressed: () {
                                    setState(() {
                                      _obscurePassword = !_obscurePassword;
                                    });
                                  },
                                ),
                                validator: (val) {
                                  if (val == null || val.isEmpty) {
                                    return 'Please enter your password';
                                  }

                                  return null;
                                },
                              ).animate().fadeIn(delay: 500.ms).slideY(
                                    begin: 0.08,
                                    end: 0,
                                  ),

                              const SizedBox(height: 8),

                              // =================================================
                              // REMEMBER ME + FORGOT
                              // =================================================

                              Row(
                                children: [
                                  Transform.scale(
                                    scale: 0.9,
                                    child: Checkbox(
                                      value: auth.rememberMe,
                                      onChanged: isLoading
                                          ? null
                                          : auth.toggleRememberMe,
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(5),
                                      ),
                                      activeColor: colors.primary,
                                    ),
                                  ),
                                  const Flexible(
                                    child: Text(
                                      'Remember me',
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                      ),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  const Spacer(),
                                  Flexible(
                                    child: TextButton(
                                      onPressed: isLoading
                                          ? null
                                          : () {
                                              ScaffoldMessenger.of(
                                                context,
                                              ).showSnackBar(
                                                SnackBar(
                                                  content: const Row(
                                                    children: [
                                                      Icon(
                                                        Icons
                                                            .info_outline_rounded,
                                                        color: Colors.white,
                                                      ),
                                                      SizedBox(width: 10),
                                                      Expanded(
                                                        child: Text(
                                                          'Contact school administration for password reset.',
                                                        ),
                                                      ),
                                                    ],
                                                  ),
                                                  behavior:
                                                      SnackBarBehavior.floating,
                                                  margin: const EdgeInsets.all(
                                                    16,
                                                  ),
                                                  shape: RoundedRectangleBorder(
                                                    borderRadius:
                                                        BorderRadius.circular(
                                                      14,
                                                    ),
                                                  ),
                                                ),
                                              );
                                            },
                                      child: const Text(
                                        'Forgot Password?',
                                        style: TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.w700,
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                  ),
                                ],
                              ).animate().fadeIn(delay: 600.ms),

                              const SizedBox(height: 12),

                              // =================================================
                              // SIGN IN BUTTON
                              // =================================================

                              SizedBox(
                                height: 56,
                                child: FilledButton(
                                  onPressed: isLoading ? null : _handleLogin,
                                  style: FilledButton.styleFrom(
                                    elevation: 0,
                                    backgroundColor: colors.primary,
                                    disabledBackgroundColor:
                                        colors.primary.withValues(
                                      alpha: 0.55,
                                    ),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(
                                        17,
                                      ),
                                    ),
                                  ),
                                  child: AnimatedSwitcher(
                                    duration: const Duration(
                                      milliseconds: 200,
                                    ),
                                    child: isLoading
                                        ? const ButtonSpinner(
                                            key: ValueKey(
                                              'loading',
                                            ),
                                            size: 23,
                                          )
                                        : const Row(
                                            key: ValueKey(
                                              'login',
                                            ),
                                            mainAxisAlignment:
                                                MainAxisAlignment.center,
                                            children: [
                                              Icon(
                                                Icons.login_rounded,
                                                size: 20,
                                              ),
                                              SizedBox(width: 9),
                                              Text(
                                                'Sign In',
                                                style: TextStyle(
                                                  fontSize: 15,
                                                  fontWeight: FontWeight.w800,
                                                ),
                                              ),
                                            ],
                                          ),
                                  ),
                                ),
                              ).animate().fadeIn(delay: 700.ms).slideY(
                                    begin: 0.08,
                                    end: 0,
                                  ),
                            ],
                          ),
                        ).animate().fadeIn(delay: 250.ms).slideY(
                              begin: 0.05,
                              end: 0,
                            ),

                        const SizedBox(height: 22),

                        // =================================================
                        // SECURITY INFO
                        // =================================================

                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.verified_user_rounded,
                              size: 15,
                              color: colors.primary.withValues(alpha: 0.70),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Secure school portal',
                              style: TextStyle(
                                fontSize: 11,
                                color: colors.onSurfaceVariant
                                    .withValues(alpha: 0.75),
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ).animate().fadeIn(delay: 850.ms),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ======================================================================
  // MODERN INPUT FIELD
  // ======================================================================

  Widget _buildField({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData icon,
    required ColorScheme colors,
    required String? Function(String?) validator,
    TextInputType? keyboardType,
    bool obscureText = false,
    Widget? suffixIcon,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      obscureText: obscureText,
      autocorrect: false,
      textCapitalization: TextCapitalization.none,
      style: const TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.w600,
      ),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: Container(
          margin: const EdgeInsets.only(
            left: 7,
            right: 5,
          ),
          child: Icon(
            icon,
            size: 21,
          ),
        ),
        prefixIconColor: colors.primary,
        suffixIcon: suffixIcon,
        filled: true,
        fillColor: colors.surfaceContainerHighest.withValues(alpha: 0.42),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 17,
        ),
        labelStyle: TextStyle(
          fontSize: 13,
          color: colors.onSurfaceVariant,
        ),
        hintStyle: TextStyle(
          fontSize: 12,
          color: colors.onSurfaceVariant.withValues(alpha: 0.50),
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
            color: colors.outlineVariant.withValues(alpha: 0.55),
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
            color: colors.outlineVariant.withValues(alpha: 0.55),
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
            color: colors.primary,
            width: 1.8,
          ),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
            color: colors.error.withValues(alpha: 0.75),
          ),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
            color: colors.error,
            width: 1.8,
          ),
        ),
        floatingLabelBehavior: FloatingLabelBehavior.auto,
      ),
      validator: validator,
    );
  }
}

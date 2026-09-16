import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'controllers/auth_controller.dart';
import 'controllers/student_controller.dart';
import 'controllers/teacher_controller.dart';
import 'services/fcm_service.dart';
import 'theme/app_theme.dart';
import 'views/splash_view.dart';

/// ===============================================================
/// FIREBASE BACKGROUND MESSAGE HANDLER
/// ===============================================================
///
/// This must remain a top-level function because Firebase Messaging
/// runs background messages in a separate isolate.
///
/// Keep @pragma so release builds can locate this function.
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(
  RemoteMessage message,
) async {
  try {
    await Firebase.initializeApp();

    debugPrint(
      'FCM Background Message: ${message.messageId}',
    );
  } catch (e) {
    debugPrint(
      'FCM Background Handler Error: $e',
    );
  }
}

/// ===============================================================
/// APP ENTRY POINT
/// ===============================================================

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Register Firebase background message handler BEFORE runApp.
  FirebaseMessaging.onBackgroundMessage(
    _firebaseMessagingBackgroundHandler,
  );

  // ---------------------------------------------------------------
  // Firebase + FCM Initialization
  // ---------------------------------------------------------------
  //
  // If Firebase configuration is missing or invalid, the application
  // will still open normally. Only push notification functionality
  // will be unavailable.
  //
  try {
    await Firebase.initializeApp();

    await FcmService.instance.initialize();

    debugPrint('Firebase & FCM initialized successfully.');
  } catch (e) {
    debugPrint(
      'Firebase/FCM initialization skipped: $e',
    );
  }

  // ---------------------------------------------------------------
  // Launch Application
  // ---------------------------------------------------------------

  runApp(
    const StudentPortalApp(),
  );
}

/// ===============================================================
/// STUDENT PORTAL APPLICATION
/// ===============================================================

class StudentPortalApp extends StatelessWidget {
  const StudentPortalApp({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // ---------------------------------------------------------
        // Authentication
        // ---------------------------------------------------------
        ChangeNotifierProvider<AuthController>(
          create: (_) => AuthController(),
        ),

        // ---------------------------------------------------------
        // Student
        // ---------------------------------------------------------
        ChangeNotifierProvider<StudentController>(
          create: (_) => StudentController(),
        ),

        // ---------------------------------------------------------
        // Teacher
        // ---------------------------------------------------------
        ChangeNotifierProvider<TeacherController>(
          create: (_) => TeacherController(),
        ),
      ],
      child: MaterialApp(
        // ---------------------------------------------------------
        // Application Metadata
        // ---------------------------------------------------------

        title: 'School Management App',

        debugShowCheckedModeBanner: false,

        // ---------------------------------------------------------
        // Theme
        // ---------------------------------------------------------

        theme: AppTheme.light(),

        darkTheme: AppTheme.dark(),

        themeMode: ThemeMode.system,

        // ---------------------------------------------------------
        // Global Application Builder
        // ---------------------------------------------------------
        //
        // This allows us to listen for FCM foreground notifications
        // globally without changing individual screens.
        //
        builder: (
          context,
          child,
        ) {
          return _FcmForegroundListener(
            child: child,
          );
        },

        // ---------------------------------------------------------
        // Initial Screen
        // ---------------------------------------------------------
        //
        // SplashView is responsible for:
        // - Restoring the login session
        // - Checking the authenticated user
        // - Detecting student/teacher role
        // - Navigating to the correct dashboard
        //
        home: const SplashView(),
      ),
    );
  }
}

/// ===============================================================
/// FCM FOREGROUND LISTENER
/// ===============================================================
///
/// Firebase does not automatically display a system notification
/// while the application is open.
///
/// This widget listens to FcmService and displays a beautiful
/// in-app notification instead.

class _FcmForegroundListener extends StatefulWidget {
  const _FcmForegroundListener({
    required this.child,
  });

  final Widget? child;

  @override
  State<_FcmForegroundListener> createState() => _FcmForegroundListenerState();
}

class _FcmForegroundListenerState extends State<_FcmForegroundListener> {
  StreamSubscription<(String?, String?)>? _subscription;

  @override
  void initState() {
    super.initState();

    // -------------------------------------------------------------
    // Listen for foreground FCM notifications
    // -------------------------------------------------------------

    _subscription = FcmService.instance.onForegroundMessage.listen(
      _showForegroundNotification,
    );
  }

  /// =============================================================
  /// SHOW FOREGROUND NOTIFICATION
  /// =============================================================

  void _showForegroundNotification(
    (String?, String?) data,
  ) {
    if (!mounted) return;

    final (
      title,
      body,
    ) = data;

    final notificationTitle = (title == null || title.trim().isEmpty)
        ? 'New Notification'
        : title.trim();

    final notificationBody = (body == null || body.trim().isEmpty)
        ? 'You have received a new notification.'
        : body.trim();

    final messenger = ScaffoldMessenger.maybeOf(context);

    if (messenger == null) return;

    // Remove currently visible SnackBar first so multiple
    // notifications don't create a long queue.
    messenger.hideCurrentSnackBar();

    messenger.showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        duration: const Duration(
          seconds: 5,
        ),
        margin: const EdgeInsets.fromLTRB(
          16,
          0,
          16,
          20,
        ),
        padding: EdgeInsets.zero,
        backgroundColor: Colors.transparent,
        elevation: 0,
        content: _NotificationCard(
          title: notificationTitle,
          body: notificationBody,
        ),
      ),
    );
  }

  @override
  void dispose() {
    _subscription?.cancel();

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return widget.child ?? const SizedBox.shrink();
  }
}

/// ===============================================================
/// MODERN FOREGROUND NOTIFICATION CARD
/// ===============================================================

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({
    required this.title,
    required this.body,
  });

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF172554),
            Color(0xFF1E3A8A),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(
              alpha: 0.22,
            ),
            blurRadius: 24,
            offset: const Offset(
              0,
              10,
            ),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // -----------------------------------------------------
            // Notification Icon
            // -----------------------------------------------------

            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: Colors.white.withValues(
                  alpha: 0.14,
                ),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.white.withValues(
                    alpha: 0.12,
                  ),
                ),
              ),
              child: const Icon(
                Icons.notifications_rounded,
                color: Colors.white,
                size: 25,
              ),
            ),

            const SizedBox(width: 13),

            // -----------------------------------------------------
            // Notification Content
            // -----------------------------------------------------

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 15.5,
                      fontWeight: FontWeight.w700,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    body,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: Colors.white.withValues(
                        alpha: 0.78,
                      ),
                      fontSize: 13,
                      height: 1.4,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(width: 8),

            // -----------------------------------------------------
            // Close Icon
            // -----------------------------------------------------

            GestureDetector(
              onTap: () {
                ScaffoldMessenger.of(
                  context,
                ).hideCurrentSnackBar();
              },
              child: Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(
                    alpha: 0.10,
                  ),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.close_rounded,
                  color: Colors.white70,
                  size: 17,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

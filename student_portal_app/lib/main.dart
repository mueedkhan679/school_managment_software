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

/// Top-level background message handler for FCM.
/// Must be a top-level function (not a class method) so the background
/// isolate can locate it. Registered before runApp via
/// FirebaseMessaging.onBackgroundMessage.
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  debugPrint("Background message received: ${message.messageId}");
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Register background handler BEFORE runApp — FCM requires this.
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  // Firebase/FCM init. Wrapped in try/catch so a missing/misconfigured
  // google-services.json can never keep the whole portal offline — push
  // notifications simply stay unavailable.
  try {
    await Firebase.initializeApp();
    await FcmService.instance.initialize();
  } catch (e) {
    debugPrint('Firebase/FCM init skipped: $e');
  }

  runApp(const StudentPortalApp());
}

class StudentPortalApp extends StatelessWidget {
  const StudentPortalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthController()),
        ChangeNotifierProvider(create: (_) => StudentController()),
        ChangeNotifierProvider(create: (_) => TeacherController()),
      ],
      child: MaterialApp(
        title: 'School Portal',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        themeMode: ThemeMode.system,
        // Surface FCM messages that arrive while the app is open.
        builder: (context, child) => _FcmForegroundListener(child: child),
        // The branded splash handles session restore and routes to the
        // right home screen (student shell, teacher dashboard or login).
        home: const SplashView(),
      ),
    );
  }
}

/// Listens to [FcmService.onForegroundMessage] and shows a SnackBar for each
/// message received while the app is in the foreground (FCM does not display
/// system-tray notifications for foregrounded apps on its own).
class _FcmForegroundListener extends StatefulWidget {
  const _FcmForegroundListener({required this.child});

  final Widget? child;

  @override
  State<_FcmForegroundListener> createState() => _FcmForegroundListenerState();
}

class _FcmForegroundListenerState extends State<_FcmForegroundListener> {
  StreamSubscription<(String?, String?)>? _subscription;

  @override
  void initState() {
    super.initState();
    _subscription = FcmService.instance.onForegroundMessage.listen((data) {
      final (title, body) = data;
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${title ?? 'Notification'}: ${body ?? ''}'),
        ),
      );
    });
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child ?? const SizedBox.shrink();
}

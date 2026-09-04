import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'api_service.dart';
import 'storage_service.dart';

/// Top-level background-message handler. Firebase requires a global function
/// annotated with @pragma('vm:entry-point') so the Android/iOS engine can
/// locate it from the background isolate (also in AOT/release builds).
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  debugPrint(
    'FCM background message: ${message.messageId} '
    '(${message.notification?.title ?? message.data['title']})',
  );
}

/// Singleton owning every Firebase Cloud Messaging concern:
///  - initialization + notification permission,
///  - notification channel creation via flutter_local_notifications,
///  - token lifecycle (fetch -> persist -> upload to the Django backend),
///  - foreground message stream consumed by the UI,
///  - background message handling (see [firebaseMessagingBackgroundHandler]).
class FcmService {
  FcmService._();

  static final FcmService instance = FcmService._();

  final ApiService _api = ApiService();
  final StorageService _storage = StorageService();

  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  /// Android notification channel — id must match the meta-data value in
  /// AndroidManifest.xml (com.google.firebase.messaging.default_notification_channel_id).
  static const AndroidNotificationChannel _channel = AndroidNotificationChannel(
    'high_importance_channel',
    'High Importance Notifications',
    description: 'This channel is used for important school notifications.',
    importance: Importance.max,
    playSound: true,
    enableVibration: true,
  );

  final StreamController<(String?, String?)> _foregroundMessages =
      StreamController<(String?, String?)>.broadcast();

  /// Emits (title, body) for messages received while the app is open.
  Stream<(String?, String?)> get onForegroundMessage =>
      _foregroundMessages.stream;

  bool _initialized = false;

  /// Call once from main() after [Firebase.initializeApp]. Safe to call when
  /// Firebase config is missing — callers wrap it in try/catch.
  ///
  /// NOTE: The background handler is registered in main() before this method
  /// is called, so we do NOT register it again here to avoid duplicates.
  Future<void> initialize() async {
    if (_initialized) return;
    _initialized = true;

    // Required on iOS and Android 13+ (POST_NOTIFICATIONS runtime permission).
    await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    // Set up local notifications plugin and create the Android channel.
    await _setupLocalNotifications();

    // Configure foreground presentation options for iOS/Android.
    await FirebaseMessaging.instance
        .setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );

    // Foreground messages never show a system tray by default — surface them
    // to the UI through [onForegroundMessage] and show a heads-up notification.
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint(
        'FCM foreground: ${message.notification?.title} / '
        '${message.notification?.body}',
      );

      final notification = message.notification;
      final android = message.notification?.android;

      // Show local heads-up notification when app is in foreground.
      if (notification != null && android != null && !kIsWeb) {
        _localNotifications.show(
          notification.hashCode,
          notification.title,
          notification.body,
          NotificationDetails(
            android: AndroidNotificationDetails(
              _channel.id,
              _channel.name,
              channelDescription: _channel.description,
              icon: '@mipmap/ic_launcher',
              importance: Importance.max,
              priority: Priority.high,
            ),
          ),
        );
      }

      _foregroundMessages.add((
        message.notification?.title,
        message.notification?.body,
      ));
    });

    // Tokens rotate (app restores, key rotation). Persist and re-upload.
    FirebaseMessaging.instance.onTokenRefresh.listen(_onNewToken);

    // Fetch the current token, cache it, and try to sync it to the backend.
    // The sync is a no-op while unauthenticated (no stored session); the
    // AuthController retries it right after login.
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null && token.isNotEmpty) {
      debugPrint("================ FCM TOKEN ================");
      debugPrint(token);
      debugPrint("===========================================");
      await _storage.saveFcmToken(token);
      await syncTokenWithBackend();
    }
  }

  /// Initialize flutter_local_notifications and create the high-importance
  /// Android notification channel so heads-up notifications work.
  Future<void> _setupLocalNotifications() async {
    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidSettings);

    await _localNotifications.initialize(initSettings);

    // Create high priority notification channel in Android system.
    await _localNotifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(_channel);
  }

  /// Uploads the device token to POST /api/v1/update-fcm-token/. Called by
  /// the AuthController after login and after session restore (app launch),
  /// and internally whenever FCM rotates the token.
  Future<void> syncTokenWithBackend() async {
    try {
      final token = await _storage.getFcmToken() ??
          await FirebaseMessaging.instance.getToken();
      if (token == null || token.isEmpty) return;
      final res = await _api.updateFcmToken(token);
      debugPrint('FCM token sync: ${res['status']}');
    } catch (e) {
      // Never let a push-token sync failure break login or startup.
      debugPrint('FCM token sync failed: $e');
    }
  }

  Future<void> _onNewToken(String token) async {
    await _storage.saveFcmToken(token);
    await syncTokenWithBackend();
  }
}

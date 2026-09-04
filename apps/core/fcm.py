"""Firebase Cloud Messaging (FCM) push-notification helper.

Architecture notes
------------------
* Push delivery is deliberately *best-effort*: the caller (e.g. the teacher
  attendance flow) always persists the in-app ``Notification`` row first;
  the in-app inbox never depends on FCM succeeding.
* ``firebase_admin`` is imported lazily and every failure path is swallowed
  (and logged), so environments without the package installed, without
  ``FIREBASE_CREDENTIALS_PATH`` configured, or with an expired device token
  keep working without ever crashing a request.
* Configuration: set ``FIREBASE_CREDENTIALS_PATH`` in Django settings (or
  the environment) to the downloaded Firebase service-account JSON file.
  The default Firebase app is initialised once per process, lazily, on the
  first successful push.
"""

import logging

logger = logging.getLogger(__name__)


def send_fcm_notification(user, title, body) -> bool:
    """Send one FCM push to ``user.fcm_token``. Returns ``True`` when sent.

    Never raises — any problem (package missing, credentials missing,
    invalid/expired token, network error) is logged and reported as
    ``False`` so callers (attendance submission, etc.) are never disrupted.
    Users without a registered ``fcm_token`` are silently skipped.
    """
    token = getattr(user, "fcm_token", None)
    if not token:
        return False

    try:
        import firebase_admin
        from django.conf import settings
        from firebase_admin import credentials, messaging

        try:
            # Reuse the process-wide default app when it already exists
            # (e.g. an earlier request in this gunicorn worker).
            app = firebase_admin.get_app()
        except ValueError:
            cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
            if not cred_path:
                logger.info(
                    "FCM push skipped: FIREBASE_CREDENTIALS_PATH is not configured."
                )
                return False
            app = firebase_admin.initialize_app(credentials.Certificate(cred_path))

        messaging.send(
            messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=token,
            ),
            app=app,
        )
        return True
    except ImportError:
        logger.debug("firebase-admin is not installed — FCM push skipped.")
        return False
    except Exception:  # noqa: BLE001 — a push failure must never break the caller
        logger.warning(
            "FCM push failed for user %s.",
            getattr(user, "pk", "?"),
            exc_info=True,
        )
        return False

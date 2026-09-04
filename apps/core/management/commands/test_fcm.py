import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.fcm import send_fcm_notification

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Test FCM push notification delivery"

    def handle(self, *args, **options):
        # 1. Fetch a student who has an fcm_token
        target_user = User.objects.exclude(fcm_token__isnull=True).exclude(fcm_token="").first()
        
        if not target_user:
            self.stdout.write(self.style.WARNING("No user found with a valid fcm_token."))
            self.stdout.write("Listing all users and their FCM token status:")
            for user in User.objects.all():
                token_status = "SET" if user.fcm_token else "NOT SET"
                self.stdout.write(f"- {user.username} (ID: {user.id}) -> {token_status}")
            return
            
        self.stdout.write(self.style.SUCCESS(f"Found target user: {target_user.username} (ID: {target_user.id})"))
        self.stdout.write(f"Token: {target_user.fcm_token}")
        
        # 2. Call send_fcm_notification
        title = "Test Title"
        body = "Test Message Body"
        
        self.stdout.write(f"Sending push notification to {target_user.username}...")
        
        # 3. We'll simulate the inner mechanics to print the exact result since 
        # send_fcm_notification catches and swallows exceptions.
        try:
            import firebase_admin
            from django.conf import settings
            from firebase_admin import credentials, messaging
            
            try:
                app = firebase_admin.get_app()
            except ValueError:
                cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
                if not cred_path:
                    self.stdout.write(self.style.ERROR("FIREBASE_CREDENTIALS_PATH is not configured in settings."))
                    return
                app = firebase_admin.initialize_app(credentials.Certificate(cred_path))
                
            response = messaging.send(
                messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    token=target_user.fcm_token,
                ),
                app=app,
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully sent message! Response: {response}"))
            
        except ImportError:
            self.stdout.write(self.style.ERROR("firebase-admin package is not installed."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send push notification! Error: {type(e).__name__}: {str(e)}"))

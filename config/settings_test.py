"""Test-only settings: use the fast (insecure) MD5 hasher for speed.

Production stays on PBKDF2 (see ``settings.py``); this module is used only by
``manage.py test --settings=config.settings_test`` so the automated suite runs
quickly without weakening the real application.
"""
from .settings import *  # noqa: F401, F403

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

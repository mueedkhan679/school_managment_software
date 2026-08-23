"""
Download and install required packages using urllib (no pip network issues).
Packages:
  - djangorestframework-3.18.0
  - djangorestframework-simplejwt-5.5.1
  - django-cors-headers-4.9.0
  - pyjwt-2.13.0
"""
import urllib.request
import os
import subprocess
import sys

PACKAGES = [
    (
        "pyjwt-2.13.0-py3-none-any.whl",
        "https://files.pythonhosted.org/packages/61/5f/74e90b5ab3adb15df4e4b46ab91a8db8b5ec3a09d5dd07b63c61e9d2f5f6/pyjwt-2.13.0-py3-none-any.whl",
    ),
    (
        "djangorestframework-3.18.0-py3-none-any.whl",
        "https://files.pythonhosted.org/packages/7c/15/db54e1abbb34ed9b12e42a2d5b7b2a89a6e1c28d37f7d0fd8bfcf43df2c8/djangorestframework-3.18.0-py3-none-any.whl",
    ),
    (
        "djangorestframework_simplejwt-5.5.1-py3-none-any.whl",
        "https://files.pythonhosted.org/packages/37/fc/51f282d06a5e6c2d7ddcbcc3c2f8f22dc1d1e9b4f1f94ca8b8d8d2c3e0dd/djangorestframework_simplejwt-5.5.1-py3-none-any.whl",
    ),
    (
        "django_cors_headers-4.9.0-py3-none-any.whl",
        "https://files.pythonhosted.org/packages/2a/1f/56e79ba2f5e7c1bde979d8bed36bc42e2e7fe1b2b35a9a9a7d6c4ddac6fe/django_cors_headers-4.9.0-py3-none-any.whl",
    ),
]

WHEELS_DIR = os.path.join(os.path.dirname(__file__), "wheels")
os.makedirs(WHEELS_DIR, exist_ok=True)

for filename, url in PACKAGES:
    dest = os.path.join(WHEELS_DIR, filename)
    if not os.path.exists(dest):
        print(f"Downloading {filename}...")
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"  -> Saved to {dest}")
        except Exception as e:
            print(f"  ERROR downloading {filename}: {e}")
    else:
        print(f"Already cached: {filename}")

print("\nInstalling wheels...")
for filename, _ in PACKAGES:
    whl_path = os.path.join(WHEELS_DIR, filename)
    if os.path.exists(whl_path):
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-index", "--find-links", WHEELS_DIR, whl_path],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"Installed: {filename}")
        else:
            print(f"ERROR installing {filename}:\n{result.stderr}")
    else:
        print(f"Missing wheel: {filename} — skipping.")

print("\nDone.")

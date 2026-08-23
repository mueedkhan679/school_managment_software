"""Launch the Django dev server as a detached background process."""
import subprocess
import sys

CMD = [sys.executable, "manage.py", "runserver", "--noreload", "127.0.0.1:8000"]

# CREATE_NO_WINDOW = 0x08000000; detach so it survives this script's exit.
proc = subprocess.Popen(
    CMD,
    creationflags=subprocess.CREATE_NO_WINDOW,
    cwd=r"c:\Users\ytmoi\Desktop\school_project",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
# Good hygiene with the opened handle.
print("launched PID", proc.pid)
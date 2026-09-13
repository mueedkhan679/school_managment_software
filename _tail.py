import sys

path = sys.argv[1] if len(sys.argv) > 1 else "_test_out.txt"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
try:
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
except FileNotFoundError:
    print("(missing)")
    sys.exit(0)
print(text[-n:] if text.strip() else "(empty)")

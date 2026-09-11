"""Validate intro.mp4: faststart (moov before mdat), size, boxes."""
from pathlib import Path

mp4 = Path(
    r"c:\Users\ytmoi\Desktop\school_project\student_portal_app\assets\videos\intro.mp4"
)
data = mp4.read_bytes()
print("size:", len(data))
print("starts with ftyp:", data[4:8] == b"ftyp")
print("has moov:", b"moov" in data[:2000], "| moov at:", data.find(b"moov"))
print("has mdat:", b"mdat" in data, "| mdat at:", data.find(b"mdat"))
print("faststart (moov < mdat):", 0 < data.find(b"moov") < data.find(b"mdat"))

# find avcC (H.264) + track dimensions (tkhd width/height as 16.16 fixed)
print("has avcC (H.264):", b"avcC" in data)
i = data.find(b"tkhd")
if i > 0:
    w = int.from_bytes(data[i + 74:i + 78], "big") / 65536
    h = int.from_bytes(data[i + 78:i + 82], "big") / 65536
    print("tkhd dims:", w, "x", h)

# smoke file cleanup
smoke = mp4.parent / "_smoke.mp4"
if smoke.exists():
    smoke.unlink()
    print("smoke file removed")

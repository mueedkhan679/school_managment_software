"""Download Django + dependencies wheels from the Aliyun mirror with resume & SHA-256 verify."""
import hashlib
import os
import sys
import time

os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

import requests  # noqa: E402

BASE = "https://mirrors.aliyun.com/pypi/packages"

FILES = [
    (
        "django-6.1-py3-none-any.whl",
        f"{BASE}/91/9c/ce847620134cfab903e75690c498af73b46abbede2912ea89bd76d5c1e76/django-6.1-py3-none-any.whl",
        "6c132cd980c9392b06807d4ca52d72530d631dc65a85d9dacede00a780cefbbe",
        8800000,
    ),
    (
        "asgiref-3.9.2-py3-none-any.whl",
        f"{BASE}/c7/d1/69d02ce34caddb0a7ae088b84c356a625a93cd4ff57b2f97644c03fad905/asgiref-3.9.2-py3-none-any.whl",
        "0b61526596219d70396548fc003635056856dba5d0d086f86476f10b33c75960",
        115000,
    ),
    (
        "sqlparse-0.6.0-py3-none-any.whl",
        f"{BASE}/d9/50/f00935da0ec7cbf325f8dc4f772ae46fbc7b672dd62876e73f0a94adda57/sqlparse-0.6.0-py3-none-any.whl",
        "b861c0288ce2fa56209a9a6412d2e066ac664b3873b89c26c9d8415e8e32996f",
        40000,
    ),
]


def sha256_of(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def download(name, url, want_hash, min_size):
    path = os.path.join("wheels", name)
    os.makedirs("wheels", exist_ok=True)
    last = 0
    for attempt in range(400):
        if sha256_of(path) == want_hash:
            print(f"{name}: VERIFIED ({os.path.getsize(path)} bytes)", flush=True)
            return True
        cur = os.path.getsize(path) if os.path.exists(path) else 0
        if cur >= min_size:
            print(f"{name}: size ok but hash mismatch ({cur} bytes) - retrying full", flush=True)
            os.remove(path)
            cur = 0
        if cur != last:
            print(f"{name}: progress {cur} bytes", flush=True)
            last = cur
        headers = {"Range": f"bytes={cur}-"} if cur else {}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=(25, 25)) as r:
                if r.status_code not in (200, 206):
                    print(f"{name}: HTTP {r.status_code} attempt {attempt}", flush=True)
                    time.sleep(2)
                    continue
                with open(path, "ab") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
        except Exception as exc:  # noqa: BLE001
            print(f"{name}: attempt {attempt} failed: {exc!r}", flush=True)
            time.sleep(1)
    print(f"{name}: FAILED", flush=True)
    return False


ok = all(download(n, u, h, s) for n, u, h, s in FILES)
print("ALL_DONE_OK" if ok else "ALL_DONE_FAILED", flush=True)
sys.exit(0 if ok else 1)

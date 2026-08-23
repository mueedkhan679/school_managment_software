"""Simulate a real browser login: fetch login page (capture CSRF cookie),
then POST credentials with the matching token, reusing the same cookie jar."""
import http.cookiejar
import re
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
LOGIN = BASE + "/accounts/login/"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def csrf_token_from(page):
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page)
    if not m:
        return None
    return m.group(1)


# Step 1: GET the login page -> server sets csrftoken cookie & renders token.
page = opener.open(LOGIN).read().decode("utf-8", "replace")
token = csrf_token_from(page)
print("GET login status:", "OK", "| token found:", bool(token))

# Step 2: POST login with admin/admin123.
data = urllib.parse.urlencode({
    "csrfmiddlewaretoken": token,
    "username": "admin",
    "password": "admin123",
}).encode()
req = urllib.request.Request(
    LOGIN, data=data,
    headers={
        "Referer": LOGIN,
        "Content-Type": "application/x-www-form-urlencoded",
    },
)
resp = opener.open(req)
final = resp.geturl()
print("POST login final URL:", final)
print("Login result:", "SUCCESS (redirect to dashboard)" if "dashboard" in final else "see URL above")
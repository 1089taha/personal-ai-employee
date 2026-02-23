"""
LinkedIn OAuth Setup — run once to authenticate and save a token.

Usage:
    uv run python src/linkedin_auth_setup.py
"""

import json
import os
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

REDIRECT_URI = "http://localhost:8080/callback"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
SCOPE = "openid email w_member_social"
TOKEN_PATH = Path("secrets/linkedin_token.json")
CALLBACK_TIMEOUT = 120  # seconds


# ---------------------------------------------------------------------------
# Callback server
# ---------------------------------------------------------------------------

class _CallbackHandler(BaseHTTPRequestHandler):
    """Captures the ?code= or ?error= query param from LinkedIn's redirect."""

    auth_code: str | None = None
    error: str | None = None

    def do_GET(self) -> None:
        params = parse_qs(urlparse(self.path).query)

        if "error" in params:
            _CallbackHandler.error = params["error"][0]
            body = b"<h2>Authorization denied.</h2><p>You can close this tab.</p>"
        elif "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            body = b"<h2>Authorization successful!</h2><p>You can close this tab.</p>"
        else:
            body = b"<h2>Unexpected callback.</h2>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # silence request logs
        pass


def _wait_for_code(timeout: int) -> str:
    """
    Starts an HTTPServer on port 8080, blocks until a code arrives or timeout
    expires, then returns the code.

    Raises RuntimeError on error or timeout.
    """
    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    server.timeout = timeout

    received = threading.Event()

    def _serve() -> None:
        while not received.is_set():
            server.handle_request()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    server.server_close()

    if _CallbackHandler.error:
        raise RuntimeError(f"LinkedIn denied access: {_CallbackHandler.error}")
    if not _CallbackHandler.auth_code:
        raise RuntimeError(
            f"No authorization code received within {timeout} seconds. "
            "Make sure you completed the login in the browser."
        )
    return _CallbackHandler.auth_code


# ---------------------------------------------------------------------------
# OAuth steps
# ---------------------------------------------------------------------------

def _build_auth_url(client_id: str) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _exchange_code(code: str, client_id: str, client_secret: str) -> dict:
    """POST to LinkedIn token endpoint and return the token response dict."""
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"Token exchange failed ({response.status_code}): {response.text}"
        )
    return response.json()


def _get_person_id(access_token: str) -> str:
    """Call /v2/userinfo and return the 'sub' field (person URN)."""
    response = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"Failed to fetch user info ({response.status_code}): {response.text}"
        )
    data = response.json()
    person_id = data.get("sub")
    if not person_id:
        raise RuntimeError(f"'sub' field missing from userinfo response: {data}")
    return person_id


def _save_token(access_token: str, person_id: str, expires_in: int) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "access_token": access_token,
        "person_id": person_id,
        "expires_in": expires_in,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    TOKEN_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Token saved to {TOKEN_PATH}")


def _test_connection(access_token: str) -> None:
    """Print basic profile info to confirm the token works."""
    response = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if not response.ok:
        print(f"Warning: profile fetch failed ({response.status_code}): {response.text}")
        return
    data = response.json()
    name = data.get("name") or f"{data.get('given_name', '')} {data.get('family_name', '')}".strip()
    email = data.get("email", "(no email in scope)")
    print(f"Profile check: name={name!r}, email={email!r}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "ERROR: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env\n\n"
            "Steps to get them:\n"
            "  1. Go to https://www.linkedin.com/developers/apps\n"
            "  2. Create an app (or open an existing one)\n"
            "  3. Under 'Auth', copy the Client ID and Client Secret\n"
            "  4. Add http://localhost:8080/callback as an Authorized Redirect URL\n"
            "  5. Add the values to your .env file:\n"
            "       LINKEDIN_CLIENT_ID=your_client_id\n"
            "       LINKEDIN_CLIENT_SECRET=your_client_secret\n"
        )
        return

    auth_url = _build_auth_url(client_id)
    print(f"Opening browser for LinkedIn login...\n{auth_url}\n")
    webbrowser.open(auth_url)

    print(f"Waiting up to {CALLBACK_TIMEOUT}s for you to complete the login...")
    code = _wait_for_code(CALLBACK_TIMEOUT)
    print("Authorization code received.")

    print("Exchanging code for access token...")
    token_data = _exchange_code(code, client_id, client_secret)
    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 5184000)

    print("Fetching LinkedIn person ID...")
    person_id = _get_person_id(access_token)

    _save_token(access_token, person_id, expires_in)

    print(f"\nLinkedIn authentication successful! Person ID: {person_id}")

    _test_connection(access_token)


if __name__ == "__main__":
    main()

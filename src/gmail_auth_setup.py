"""
Gmail OAuth Setup — run once to authenticate and save a token.

Usage:
    uv run python src/gmail_auth_setup.py
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = Path("secrets/gmail_token.json")


def load_or_create_credentials() -> Credentials:
    """Load existing token, refresh if expired, or run the OAuth flow."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds.valid:
            print("Loaded existing token from secrets/gmail_token.json")
            return creds
        if creds.expired and creds.refresh_token:
            print("Token expired — refreshing...")
            creds.refresh(Request())
            _save_token(creds)
            print("Token refreshed and saved.")
            return creds

    # No valid token — run the browser OAuth flow
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
    if not credentials_path:
        raise EnvironmentError(
            "GMAIL_CREDENTIALS_PATH is not set in .env\n"
            "Download credentials.json from Google Cloud Console and set the path."
        )
    if not Path(credentials_path).exists():
        raise FileNotFoundError(
            f"credentials.json not found at: {credentials_path}\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials."
        )

    print("Opening browser for Google login...")
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _save_token(creds)
    print(f"Token saved to {TOKEN_PATH}")
    return creds


def _save_token(creds: Credentials) -> None:
    TOKEN_PATH.write_text(creds.to_json())


def test_connection(creds: Credentials) -> None:
    """Fetch the 3 most recent email subjects as a connection test."""
    service = build("gmail", "v1", credentials=creds)

    result = service.users().messages().list(
        userId="me", maxResults=3
    ).execute()

    messages = result.get("messages", [])
    if not messages:
        print("Gmail authentication successful! Inbox appears empty.")
        return

    print(f"\nGmail authentication successful! Found {result.get('resultSizeEstimate', '?')} recent emails.")
    print("Last 3 subjects:")
    for i, msg in enumerate(messages, 1):
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["Subject"]
        ).execute()
        headers = detail.get("payload", {}).get("headers", [])
        subject = next(
            (h["value"] for h in headers if h["name"] == "Subject"),
            "(no subject)"
        )
        print(f"  {i}. {subject}")


def main() -> None:
    creds = load_or_create_credentials()
    test_connection(creds)


if __name__ == "__main__":
    main()

"""
Gmail Send Action — Execution Layer

Called by the orchestrator when an approved file has action: send_gmail.
Reads the approved file, extracts recipient/subject/body, and sends via Gmail API.

Usage:
    uv run python src/actions/send_gmail.py <path-to-approved-file>

Exit codes:
    0  — email sent successfully (prints "SENT" to stdout)
    1  — failure (prints "ERROR: <reason>" to stdout)
"""

import base64
import re
import sys
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

TOKEN_PATH = Path("secrets/gmail_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _load_credentials() -> Credentials:
    if not TOKEN_PATH.exists():
        print(f"ERROR: No token found at {TOKEN_PATH} — run gmail_auth_setup.py first")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            return creds
        except Exception as exc:
            print(f"ERROR: Token refresh failed: {exc}")
            sys.exit(1)

    print("ERROR: Token is invalid — re-run gmail_auth_setup.py")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract key: value pairs from YAML front-matter between --- delimiters."""
    text = text.lstrip("\ufeff")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"')
    return result


def _extract_reply_body(content: str) -> str:
    """Extract text from ## Draft Reply or ## Drafted Reply section."""
    match = re.search(
        r"##\s+Drafted? Reply\s*\n(.*?)(?=\n##\s+|\Z)",
        content,
        re.DOTALL,
    )
    if not match:
        return ""
    return match.group(1).strip()


def _extract_email_address(value: str) -> str:
    """Extract bare email from 'Name <email@domain.com>' or return as-is."""
    m = re.search(r"<([^>]+)>", value)
    return m.group(1) if m else value.strip()


# ---------------------------------------------------------------------------
# Message builder (as specified)
# ---------------------------------------------------------------------------

def create_message(
    to: str, subject: str, body: str, thread_id: str | None = None
) -> dict:
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    msg: dict = {"raw": raw}
    if thread_id:
        msg["threadId"] = thread_id
    return msg


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("ERROR: Usage: send_gmail.py <path-to-approved-file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    content = file_path.read_text(encoding="utf-8")
    meta = _parse_frontmatter(content)

    # Recipient: prefer explicit `to` field, fall back to `from` (reply to sender)
    to_raw = meta.get("to") or meta.get("from", "")
    if not to_raw:
        print("ERROR: No recipient — YAML front-matter missing both 'to' and 'from' fields")
        sys.exit(1)
    to = _extract_email_address(to_raw)

    subject = meta.get("subject", "(no subject)")

    # Thread: prefer explicit `thread_id`, fall back to `original_msg_id`
    thread_id = meta.get("thread_id") or meta.get("original_msg_id") or None

    body = _extract_reply_body(content)
    if not body:
        print(
            "ERROR: No email body — could not find "
            "'## Draft Reply' or '## Drafted Reply' section"
        )
        sys.exit(1)

    creds = _load_credentials()
    service = build("gmail", "v1", credentials=creds)

    msg = create_message(to, subject, body, thread_id)

    try:
        service.users().messages().send(userId="me", body=msg).execute()
    except HttpError as exc:
        print(f"ERROR: Gmail API error: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    print(f"[GmailSend] Sent to {to} — subject: {subject}")
    print("SENT")


if __name__ == "__main__":
    main()

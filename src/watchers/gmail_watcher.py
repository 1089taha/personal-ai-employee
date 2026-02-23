"""
Gmail Watcher — Perception Layer
Polls Gmail every 2 minutes for unread emails and creates action files
in /Needs_Action/ so Claude can draft replies using the classify_message skill.

Usage:
    uv run python src/watchers/gmail_watcher.py
"""

import base64
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

VAULT_PATH = Path(os.environ["VAULT_PATH"])
NEEDS_ACTION = VAULT_PATH / "Needs_Action"

TOKEN_PATH = Path("secrets/gmail_token.json")
PROCESSED_IDS_PATH = Path("secrets/processed_gmail_ids.json")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
POLL_INTERVAL = 120   # seconds between polls
MAX_RESULTS = 10      # emails fetched per poll
BODY_MAX_CHARS = 500  # truncate body beyond this

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gmail_watcher")


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def _load_credentials() -> Credentials:
    """Load Gmail credentials, refreshing if expired. Exits on unrecoverable failure."""
    if not TOKEN_PATH.exists():
        log.error(
            "No token found at %s — run `uv run python src/gmail_auth_setup.py` first.",
            TOKEN_PATH,
        )
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        log.info("Token expired — refreshing...")
        try:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            log.info("Token refreshed and saved.")
            return creds
        except Exception as exc:
            log.error("Token refresh failed: %s — re-run gmail_auth_setup.py to re-authenticate.", exc)
            sys.exit(1)

    log.error("Token is invalid and has no refresh token — re-run gmail_auth_setup.py.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Processed IDs persistence
# ---------------------------------------------------------------------------

def _load_processed_ids() -> set[str]:
    """Load the set of already-processed Gmail message IDs from disk."""
    if not PROCESSED_IDS_PATH.exists():
        return set()
    try:
        return set(json.loads(PROCESSED_IDS_PATH.read_text(encoding="utf-8")))
    except Exception as exc:
        log.warning("Could not load processed IDs (%s) — starting fresh.", exc)
        return set()


def _save_processed_ids(ids: set[str]) -> None:
    PROCESSED_IDS_PATH.write_text(json.dumps(sorted(ids)), encoding="utf-8")


# ---------------------------------------------------------------------------
# Email parsing helpers
# ---------------------------------------------------------------------------

def _get_header(headers: list[dict], name: str, default: str = "") -> str:
    """Case-insensitive header lookup."""
    name_lower = name.lower()
    for h in headers:
        if h["name"].lower() == name_lower:
            return h["value"]
    return default


def _decode_base64url(data: str) -> str:
    """Decode a base64url-encoded string, adding padding as needed."""
    # Gmail omits base64 padding — restore it before decoding
    missing = len(data) % 4
    if missing:
        data += "=" * (4 - missing)
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def _extract_body(payload: dict) -> str:
    """
    Recursively extract the plaintext body from a Gmail message payload.
    Prefers text/plain; falls back to the first readable part in multipart messages.
    """
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return _decode_base64url(data)

    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            result = _extract_body(part)
            if result:
                return result

    return ""


def _truncate(text: str) -> str:
    text = text.strip()
    if len(text) <= BODY_MAX_CHARS:
        return text
    return text[:BODY_MAX_CHARS].rstrip() + "\n\n[... truncated — open Gmail for the full message]"


# ---------------------------------------------------------------------------
# Action file builder
# ---------------------------------------------------------------------------

def _build_action_file(
    msg_id: str,
    headers: list[dict],
    body: str,
    now: datetime,
) -> tuple[str, str]:
    sender  = _get_header(headers, "From",    "(unknown sender)")
    subject = _get_header(headers, "Subject", "No Subject")
    date    = _get_header(headers, "Date",    "(no date)")

    timestamp_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str      = now.strftime("%Y%m%d")

    filename  = f"EMAIL_{msg_id[:8]}_{date_str}.md"
    body_text = _truncate(body) if body.strip() else "(no plain-text body — see snippet in Gmail)"

    content = f"""---
type: email
source: gmail
from: "{sender}"
subject: "{subject}"
msg_id: "{msg_id}"
received: "{date}"
created: {timestamp_iso}
status: pending
---

## Email Content

**From:** {sender}
**Subject:** {subject}
**Date:** {date}

{body_text}

## Instructions for Claude

Read the email above. Use the classify_message skill to:
1. Classify priority (urgent/normal/low/flagged)
2. Draft a reply following Company_Handbook.md tone rules
3. Save the approval request to /Pending_Approval/
"""
    return filename, content


# ---------------------------------------------------------------------------
# Core polling logic
# ---------------------------------------------------------------------------

def _poll(service, processed_ids: set[str]) -> None:
    """
    One poll cycle: fetch unread emails, create action files for new ones.
    Mutates processed_ids in place and saves to disk after each new email.
    """
    # --- Fetch message list ---
    try:
        result = service.users().messages().list(
            userId="me",
            q="is:unread",
            maxResults=MAX_RESULTS,
        ).execute()
    except HttpError as exc:
        if exc.resp.status in (403, 429):
            log.warning("Gmail API rate limit (%s) — waiting 60 s before retrying.", exc.resp.status)
            time.sleep(60)
        else:
            log.warning("Gmail API error during message list: %s", exc)
        return
    except Exception as exc:
        log.warning("Network error during Gmail poll: %s", exc)
        return

    messages = result.get("messages", [])

    for msg in messages:
        msg_id = msg["id"]

        if msg_id in processed_ids:
            continue

        # --- Fetch full message ---
        try:
            detail = service.users().messages().get(
                userId="me",
                id=msg_id,
                format="full",
            ).execute()
        except HttpError as exc:
            if exc.resp.status in (403, 429):
                log.warning("Rate limit fetching message %s (%s) — waiting 60 s.", msg_id, exc.resp.status)
                time.sleep(60)
            else:
                log.warning("Could not fetch message %s: %s — skipping.", msg_id, exc)
            continue
        except Exception as exc:
            log.warning("Network error fetching message %s: %s — skipping.", msg_id, exc)
            continue

        payload = detail.get("payload", {})
        headers = payload.get("headers", [])

        body = _extract_body(payload)
        if not body.strip():
            # Snippet is plain text and always available — use as fallback
            body = detail.get("snippet", "")

        now = datetime.now(timezone.utc)
        filename, content = _build_action_file(msg_id, headers, body, now)

        action_path = NEEDS_ACTION / filename
        action_path.write_text(content, encoding="utf-8")

        processed_ids.add(msg_id)
        _save_processed_ids(processed_ids)

        subject = _get_header(headers, "Subject", "No Subject")
        sender  = _get_header(headers, "From",    "(unknown)")
        log.info("New email detected: %s from %s", subject, sender)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    PROCESSED_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)

    creds = _load_credentials()
    service = build("gmail", "v1", credentials=creds)

    processed_ids = _load_processed_ids()
    log.info("Gmail Watcher started — polling every 2 minutes")

    while True:
        _poll(service, processed_ids)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Gmail Watcher stopped.")

"""
WhatsApp Watcher — Perception Layer
Monitors WhatsApp Web for unread messages and creates action files
in /Needs_Action/ so Claude can draft replies using the classify_message skill.

Usage:
    First time (QR code scan needed):
        uv run python src/watchers/whatsapp_watcher.py --first-run

    All subsequent runs:
        uv run python src/watchers/whatsapp_watcher.py

NOTE: Opening a chat in WhatsApp Web marks it as read on all devices (standard
WhatsApp behaviour). This is unavoidable without the Business API. The watcher
is still read-only — it never writes or sends anything.
"""

import argparse
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import (
    BrowserContext,
    ElementHandle,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

VAULT_PATH   = Path(os.environ["VAULT_PATH"])
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
SESSION_DIR   = Path("secrets/whatsapp_session")
DEBUG_SCREENSHOT  = Path("secrets/whatsapp_debug.png")
HEADER_SCREENSHOT = Path("secrets/whatsapp_header_debug.png")

WHATSAPP_URL  = "https://web.whatsapp.com"
POLL_INTERVAL = 30       # seconds between polls
QR_TIMEOUT_MS = 120_000  # 2 minutes for QR scan
LOAD_TIMEOUT_MS = 30_000 # timeout waiting for chat list on normal start

# WhatsApp Web selectors — multiple fallbacks because the DOM changes regularly
_CHAT_LIST_SELECTORS = [
    '[aria-label="Chat list"]',
    'div[data-testid="chat-list"]',
    '[data-testid="pane-side"]',
]
_UNREAD_BADGE_SELECTOR = '[aria-label*="unread"]'
_CONTACT_HEADER_SELECTORS = [
    '[data-testid="conversation-header"] span[dir="auto"]',
    'header [data-testid="conversation-info-header-chat-title"] span',
    'header span[title]',
    'header [data-testid="conversation-header"] span',
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("whatsapp_watcher")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WhatsApp Web watcher for AI Employee",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  First run (scan QR code):  uv run python src/watchers/whatsapp_watcher.py --first-run\n"
            "  Normal run:                uv run python src/watchers/whatsapp_watcher.py"
        ),
    )
    parser.add_argument(
        "--first-run",
        action="store_true",
        help="Force visible browser window for QR code scanning",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Browser / session management
# ---------------------------------------------------------------------------

def _launch_context(playwright, *, headless: bool) -> BrowserContext:
    """Launch a persistent Chromium context backed by SESSION_DIR."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(SESSION_DIR),
        headless=headless,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
        viewport={"width": 1280, "height": 900},
    )


def _active_page(context: BrowserContext) -> Page:
    """Return the first existing page, or open a new one."""
    return context.pages[0] if context.pages else context.new_page()


def _wait_for_chat_list(page: Page, timeout_ms: int) -> bool:
    """Return True if any chat-list selector becomes visible within timeout_ms."""
    for selector in _CHAT_LIST_SELECTORS:
        try:
            page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            continue
    return False


def _connect(playwright, *, first_run: bool) -> tuple[BrowserContext, Page]:
    """
    Open WhatsApp Web and return (context, page).

    - first_run=True  → visible browser, long QR timeout
    - first_run=False → headless, short timeout; falls back to visible if session expired
    Exits with sys.exit(1) if connection cannot be established.
    """
    headless = not first_run
    context  = _launch_context(playwright, headless=headless)
    page     = _active_page(context)
    page.goto(WHATSAPP_URL)

    if first_run:
        log.info("Waiting for WhatsApp Web QR scan... Please scan with your phone")
        if _wait_for_chat_list(page, QR_TIMEOUT_MS):
            log.info("WhatsApp Web connected successfully!")
            return context, page
        log.error("QR scan timed out after 120 s. Please try --first-run again.")
        context.close()
        sys.exit(1)

    # Normal run — try headless first
    log.info("Loading WhatsApp Web session...")
    if _wait_for_chat_list(page, LOAD_TIMEOUT_MS):
        log.info("WhatsApp Web connected successfully!")
        return context, page

    # Session likely expired — switch to visible browser for re-scan
    log.warning("Session may have expired. Relaunching with visible browser for QR re-scan.")
    context.close()
    context = _launch_context(playwright, headless=False)
    page    = _active_page(context)
    page.goto(WHATSAPP_URL)
    log.info("Waiting for WhatsApp Web QR scan... Please scan with your phone")
    if _wait_for_chat_list(page, QR_TIMEOUT_MS):
        log.info("WhatsApp Web connected successfully!")
        return context, page

    log.error("Could not connect to WhatsApp Web. Run with --first-run to scan the QR code.")
    context.close()
    sys.exit(1)


# ---------------------------------------------------------------------------
# DOM helpers
# ---------------------------------------------------------------------------

def _name_from_chat_row(chat_row: ElementHandle) -> str:
    """
    Extract the contact / group name from a sidebar chat-list row BEFORE
    clicking it.  The list item renders the real name as a span[title] or a
    span[dir="auto"] — neither is polluted by header tooltip text.

    Returns an empty string if nothing useful is found.
    """
    try:
        name: str = chat_row.evaluate(
            """el => {
                // span[title] is most reliable — WhatsApp puts the real name there
                const titled = el.querySelector('span[title]');
                if (titled && titled.title && titled.title.trim()) return titled.title.trim();

                // Fall back to the first dir="auto" span that looks like a name
                const spans = el.querySelectorAll('span[dir="auto"]');
                for (const s of spans) {
                    const t = (s.innerText || '').trim();
                    if (t.length > 0 && t.length < 120) return t;
                }
                return '';
            }"""
        )
        return (name or "").strip()
    except Exception as exc:
        log.warning("Could not extract name from chat row: %s", exc)
        return ""


def _get_contact_name_from_header(page: Page) -> str:
    """
    Extract the contact / group name from the open conversation header.
    Tries targeted selectors scoped to #main, screenshots the header for
    debugging, and dumps the first 1000 chars of header HTML to the log.

    Returns "Unknown" only if every strategy fails.
    """
    # --- Debug: header screenshot ---
    try:
        header_el = page.query_selector("#main header")
        if header_el:
            HEADER_SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
            header_el.screenshot(path=str(HEADER_SCREENSHOT))
            log.info("  [header] Screenshot saved to %s", HEADER_SCREENSHOT)

            raw_html = page.evaluate(
                "el => el.outerHTML", header_el
            )
            log.info("  [header] HTML (first 1000 chars): %s", raw_html[:1000])
        else:
            log.warning("  [header] #main header element not found for screenshot")
    except Exception as exc:
        log.warning("  [header] Screenshot/HTML dump failed: %s", exc)

    # --- Selector probe (scoped to #main to avoid sidebar collisions) ---
    candidates = [
        ('data-testid title span',
         '#main header span[data-testid="conversation-info-header-chat-title"]'),
        ('span[title] in #main header',
         '#main header span[title]'),
        ('span[dir=auto] in #main header',
         '#main header span[dir="auto"]'),
        ('conversation-panel-header span[title]',
         'header [data-testid="conversation-panel-header"] span[title]'),
        ('img[alt] in #main header',   # alt often carries the contact name
         '#main header img[alt]'),
    ]

    for label, selector in candidates:
        try:
            el = page.query_selector(selector)
            if not el:
                log.info("  [header] %-45s → (no element)", label)
                continue

            # For <img>, the name lives in the alt attribute
            if selector.endswith("img[alt]"):
                name = (el.get_attribute("alt") or "").strip()
            else:
                # Prefer .title attribute (avoids tooltip innerText contamination)
                name = (el.get_attribute("title") or "").strip()
                if not name:
                    name = el.inner_text().strip()

            log.info("  [header] %-45s → %r", label, name)
            if name and name.lower() not in ("", "click here for group info", "click here for contact info"):
                return name
        except Exception as exc:
            log.warning("  [header] selector %r raised: %s", label, exc)

    log.warning("  [header] All header selectors failed — returning Unknown")
    return "Unknown"


def _get_unread_count(badge: ElementHandle) -> int:
    """Parse the integer unread count from a badge element, defaulting to 1."""
    try:
        text = badge.inner_text().strip()
        return int(text) if text.isdigit() else 1
    except Exception:
        return 1


def _extract_messages(page: Page, max_messages: int = 5) -> list[dict]:
    """
    Extract up to max_messages recent messages from the currently open chat.

    Returns a list of dicts: {'sender': str, 'text': str, 'timestamp': str}

    Strategy 1 (preferred): data-pre-plain-text attribute on .copyable-text elements.
      Format of the attribute: "[HH:MM, DD/MM/YYYY] Sender Name: "
    Strategy 2 (fallback): message-in / message-out class names.
    """
    messages: list[dict] = []

    # --- Strategy 1: data-pre-plain-text ---
    elements = page.query_selector_all(".copyable-text[data-pre-plain-text]")
    for el in elements:
        try:
            pre = el.get_attribute("data-pre-plain-text") or ""
            # "[12:30, 22/02/2026] Contact Name: "
            match = re.match(r"\[([^\]]+)\]\s*(.*?):\s*$", pre)
            timestamp = match.group(1).strip() if match else ""
            sender    = match.group(2).strip() if match else "Unknown"

            text_el = el.query_selector("span.selectable-text.copyable-text")
            text    = text_el.inner_text().strip() if text_el else el.inner_text().strip()

            if text:
                messages.append({"sender": sender, "text": text, "timestamp": timestamp})
        except Exception:
            continue

    if messages:
        return messages[-max_messages:]

    # --- Strategy 2: message direction classes ---
    try:
        all_text_els = page.query_selector_all(
            "div.message-in .selectable-text, div.message-out .selectable-text"
        )
        for el in all_text_els[-max_messages:]:
            try:
                text   = el.inner_text().strip()
                is_out = el.evaluate('el => !!el.closest("div.message-out")')
                if text:
                    messages.append({
                        "sender":    "You" if is_out else "Contact",
                        "text":      text,
                        "timestamp": "",
                    })
            except Exception:
                continue
    except Exception:
        pass

    return messages[-max_messages:] if messages else []


# ---------------------------------------------------------------------------
# Action file builder
# ---------------------------------------------------------------------------

def _safe_name(contact: str) -> str:
    """Convert a contact name to a filename-safe lowercase slug (max 30 chars)."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", contact.strip())
    return slug.strip("-").lower()[:30]


def _build_action_file(
    contact: str,
    unread_count: int,
    messages: list[dict],
    now: datetime,
) -> tuple[str, str]:
    timestamp_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_file       = now.strftime("%Y%m%d_%H%M")
    filename      = f"WHATSAPP_{_safe_name(contact)}_{ts_file}.md"

    context_lines = []
    for msg in messages:
        ts_prefix = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
        context_lines.append(f"{ts_prefix}**{msg['sender']}**: {msg['text']}")
    context_block = "\n".join(context_lines) if context_lines else "(no message history extracted)"

    latest      = messages[-1] if messages else {}
    latest_text = latest.get("text", "(no text)")
    latest_ts   = latest.get("timestamp", timestamp_iso)

    content = f"""---
type: whatsapp
source: whatsapp
contact: "{contact}"
unread_count: {unread_count}
created: {timestamp_iso}
status: pending
---

## Conversation Context (Last 5 Messages)

{context_block}

## Latest Unread Message

**From:** {contact}
**Message:** {latest_text}
**Received:** {latest_ts}

## Instructions for Claude

Read the conversation above. Use the classify_message skill to:
1. Classify priority (urgent/normal/low/flagged)
2. Draft a reply matching the sender's language and tone
3. If sender used Roman Urdu, reply in Roman Urdu
4. If sender used English, reply in English
5. Read /Company_Handbook.md for tone rules
6. Save the approval request to /Pending_Approval/
"""
    return filename, content


# ---------------------------------------------------------------------------
# Core polling logic
# ---------------------------------------------------------------------------

# Ordered list of JavaScript expressions to find the clickable chat row
# starting from the badge element. Tried top-to-bottom; first non-null wins.
_CHAT_ROW_STRATEGIES = [
    # WhatsApp-specific container (older builds)
    "el => el.closest('[data-testid=\"cell-frame-container\"]')",
    # Semantic list item
    "el => el.closest('[role=\"listitem\"]')",
    # Plain HTML <li>
    "el => el.closest('li')",
    # Focusable div — WhatsApp sets tabindex="0" on clickable chat rows
    "el => el.closest('div[tabindex=\"0\"]')",
    # Walk up 6 parent levels and return the highest reachable ancestor.
    # The badge is usually 5–7 levels deep inside the chat row div.
    ("el => { let n = el;"
     " for (let i = 0; i < 6; i++) { if (n.parentElement) n = n.parentElement; }"
     " return n; }"),
]


def _find_chat_row(badge: ElementHandle, index: int) -> ElementHandle | None:
    """
    Walk up the DOM from a badge element to find its clickable chat row.
    Tries each strategy in _CHAT_ROW_STRATEGIES and returns the first hit.
    Logs the strategy that worked (or failure) so we can tune selectors.
    """
    for i, js in enumerate(_CHAT_ROW_STRATEGIES):
        try:
            el = badge.evaluate_handle(js).as_element()
            if el:
                log.info("  [chat %d] Found chat row via strategy %d", index, i + 1)
                return el
        except Exception as exc:
            log.warning("  [chat %d] Strategy %d raised: %s", index, i + 1, exc)

    log.warning("  [chat %d] All chat-row strategies exhausted — cannot click this chat.", index)
    return None


def _poll(page: Page, processed: set[str]) -> None:
    """
    One poll cycle: find unread chats, extract messages, write action files.
    Mutates processed in place.

    Clicking a chat will mark it as read in WhatsApp (standard WA behaviour).
    The processed set prevents duplicate action files within a session.
    """
    try:
        badges = page.query_selector_all(_UNREAD_BADGE_SELECTOR)
    except Exception as exc:
        log.exception("Could not query unread badges — aborting poll cycle.")
        return

    if not badges:
        return  # Nothing unread — keep terminal clean

    log.info("Found %d unread chat badge(s)", len(badges))

    for i, badge in enumerate(badges, start=1):
        log.info("Processing unread chat %d / %d ...", i, len(badges))
        try:
            unread_count = _get_unread_count(badge)
            log.info("  [chat %d] Unread count: %d", i, unread_count)

            # --- Step 1: grab name from sidebar BEFORE clicking (most reliable) ---
            chat_row = _find_chat_row(badge, i)
            contact_pre = _name_from_chat_row(chat_row) if chat_row else ""
            log.info("  [chat %d] Pre-click name from sidebar: %r", i, contact_pre)

            # --- Step 2: click the chat row to open the conversation ---
            if chat_row:
                chat_row.click()
                log.info("  [chat %d] Clicked chat row successfully", i)
            else:
                # Last-resort: dispatch a click event directly from JS
                clicked = badge.evaluate(
                    "el => {"
                    "  const row = el.closest('[data-testid=\"cell-frame-container\"]')"
                    "          || el.closest('[role=\"listitem\"]')"
                    "          || el.closest('li')"
                    "          || el.closest('div[tabindex]');"
                    "  if (row) { row.click(); return true; }"
                    "  return false;"
                    "}"
                )
                if clicked:
                    log.info("  [chat %d] Clicked via JS fallback", i)
                else:
                    log.warning("  [chat %d] Could not find a clickable ancestor — skipping.", i)
                    continue

            page.wait_for_timeout(1_000)  # let messages render

            # --- Step 3: resolve final contact name ---
            if contact_pre:
                contact = contact_pre
                log.info("  [chat %d] Using sidebar name: %r", i, contact)
            else:
                log.info("  [chat %d] Sidebar name empty — probing header...", i)
                contact = _get_contact_name_from_header(page)
                log.info("  [chat %d] Final contact name: %r", i, contact)

            # --- Step 4: extract message history ---
            messages = _extract_messages(page, max_messages=5)
            log.info("  [chat %d] Extracted %d message(s)", i, len(messages))

            # --- Step 5: dedup check ---
            latest_text = messages[-1]["text"] if messages else ""
            dedup_key   = f"{contact}::{latest_text[:60]}"
            if dedup_key in processed:
                log.info("  [chat %d] Already processed this message — skipping.", i)
                continue

            # --- Step 6: write action file ---
            now = datetime.now(timezone.utc)
            filename, content = _build_action_file(contact, unread_count, messages, now)
            action_path = NEEDS_ACTION / filename
            action_path.write_text(content, encoding="utf-8")
            processed.add(dedup_key)

            log.info("New WhatsApp message from %s: %s", contact, latest_text[:50])

        except PlaywrightTimeoutError:
            log.exception("  [chat %d] Playwright timeout — skipping this chat.", i)
        except Exception:
            log.exception("  [chat %d] Unexpected error — skipping this chat.", i)


# ---------------------------------------------------------------------------
# Selector debug (runs once on startup)
# ---------------------------------------------------------------------------

def _debug_selectors(page: Page) -> None:
    """
    Run once after connecting. Saves a screenshot and probes every candidate
    selector so you can see which ones actually find elements in the live DOM.
    Results appear in the terminal — use them to update _UNREAD_BADGE_SELECTOR.
    """
    DEBUG_SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)

    # Page identity
    title = page.title()
    log.info("[DEBUG] Page title: %r", title)

    # Screenshot for visual confirmation
    try:
        page.screenshot(path=str(DEBUG_SCREENSHOT))
        log.info("[DEBUG] Screenshot saved to %s", DEBUG_SCREENSHOT)
    except Exception as exc:
        log.warning("[DEBUG] Screenshot failed: %s", exc)

    # Selector probe — add / remove candidates here freely
    candidates = [
        '[aria-label*="unread"]',
        'span[data-testid="icon-unread-count"]',
        'span[data-icon="unread-count"]',
        '.x1rg5ohu',
        'span[aria-label*="unread message"]',
    ]

    log.info("[DEBUG] Probing %d unread-badge selector candidates:", len(candidates))
    for selector in candidates:
        try:
            count = len(page.query_selector_all(selector))
        except Exception as exc:
            count = f"ERROR ({exc})"
        log.info("[DEBUG]   %-45s → %s element(s)", selector, count)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)

    # Auto-detect first run: treat as first-run if session dir is missing or empty
    session_exists = SESSION_DIR.exists() and any(SESSION_DIR.iterdir())
    first_run = args.first_run or not session_exists

    if first_run and not args.first_run:
        log.info("No existing session found — running in first-run mode (visible browser).")

    processed: set[str] = set()

    with sync_playwright() as playwright:
        context, page = _connect(playwright, first_run=first_run)
        _debug_selectors(page)
        log.info("WhatsApp Watcher started — polling every 30 seconds")

        try:
            while True:
                try:
                    _poll(page, processed)
                except PlaywrightTimeoutError:
                    log.error("WhatsApp Web timed out during poll — attempting page reload.")
                    try:
                        page.reload(timeout=30_000)
                        if not _wait_for_chat_list(page, LOAD_TIMEOUT_MS):
                            log.error("Chat list did not reappear after reload — exiting.")
                            break
                        log.info("Reconnected after reload.")
                    except Exception as reload_exc:
                        log.error("Reload failed: %s — exiting.", reload_exc)
                        break
                except Exception as exc:
                    log.error("Unexpected error during poll: %s", exc)

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log.info("WhatsApp Watcher stopped.")
        finally:
            context.close()
            log.info("Browser closed. Session data preserved at %s", SESSION_DIR)


if __name__ == "__main__":
    main()

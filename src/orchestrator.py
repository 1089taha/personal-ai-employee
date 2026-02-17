"""
Orchestrator — Execution Layer
Monitors /Approved/ in the Obsidian vault. When Taha moves a file there,
logs the action, moves it to /Done/, and updates the dashboard.
"""

import json
import logging
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

VAULT_PATH = Path(os.environ["VAULT_PATH"])
APPROVED = VAULT_PATH / "Approved"
DONE = VAULT_PATH / "Done"
LOGS_DIR = VAULT_PATH / "Logs"
DASHBOARD = VAULT_PATH / "Dashboard.md"

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("orchestrator")


# ---------------------------------------------------------------------------
# YAML front-matter parser
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract key: value pairs from YAML front-matter between --- delimiters."""
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"')
    return result


# ---------------------------------------------------------------------------
# Log file helper
# ---------------------------------------------------------------------------

def _append_log(entry: dict) -> None:
    """Append a structured entry to today's JSON log file."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = LOGS_DIR / f"{today}.json"

    try:
        data = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    except (json.JSONDecodeError, OSError):
        data = {}

    data.setdefault("date", today)
    data.setdefault("entries", [])
    data["entries"].append(entry)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Dashboard updater
# ---------------------------------------------------------------------------

def _update_dashboard(filename: str, meta: dict, now: datetime) -> None:
    """Patch Dashboard.md after an approved action is completed."""
    if not DASHBOARD.exists():
        return

    ts_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_hm = now.strftime("%H:%M")
    action = meta.get("action", "unknown")
    topic = meta.get("topic", filename)

    text = DASHBOARD.read_text(encoding="utf-8")

    # 1. Update last_updated in YAML front-matter
    text = re.sub(r"(?<=last_updated: )[\d\-T:Z]+", ts_iso, text)

    # 2. Increment "Completed Today" count in the pipeline table
    text = re.sub(
        r"(\| Completed Today \| )(\d+)( \|)",
        lambda m: m.group(1) + str(int(m.group(2)) + 1) + m.group(3),
        text,
    )

    # 3. Prepend activity entry to Today's Activity section
    activity_line = f"- {ts_hm} Approved & completed: {action} — {topic}"
    if "_No activity yet today._" in text:
        text = text.replace(
            "## Today's Activity\n\n_No activity yet today._",
            f"## Today's Activity\n\n{activity_line}",
            1,
        )
    else:
        text = re.sub(
            r"(## Today's Activity\n\n)",
            rf"\1{activity_line}\n",
            text,
        )

    # 4. Update LinkedIn post status in the weekly table (Pending → Posted)
    if action == "linkedin_post":
        text = re.sub(
            rf"(\| [^\|]+ \| {re.escape(topic)} \| )Pending( \|)",
            r"\1Posted\2",
            text,
        )

    # 5. Remove the file entry from Pending Reviews if still listed
    text = re.sub(rf"- 📝 {re.escape(filename)}[^\n]*\n?", "", text)

    # If no 📝 entries remain in the section, add the all-clear placeholder
    pending_match = re.search(
        r"## Pending Reviews\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if pending_match:
        section_body = pending_match.group(1)
        has_entries = any(
            line.strip().startswith("- 📝")
            for line in section_body.splitlines()
        )
        if not has_entries and "_Nothing awaiting review" not in section_body:
            text = re.sub(
                r"(## Pending Reviews\n\n).*?(\n## |\Z)",
                r"\1_Nothing awaiting review. All clear!_\n\2",
                text,
                flags=re.DOTALL,
            )

    # 6. Increment Actions Approved in Weekly Stats
    text = re.sub(
        r"(- Actions Approved: )(\d+)",
        lambda m: m.group(1) + str(int(m.group(2)) + 1),
        text,
    )

    # 7. Update footer timestamp
    text = re.sub(
        r"\*Dashboard auto-updated by AI Employee at [\d\-T:Z]+\*",
        f"*Dashboard auto-updated by AI Employee at {ts_iso}*",
        text,
    )

    DASHBOARD.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Watchdog event handler
# ---------------------------------------------------------------------------

class ApprovalHandler(FileSystemEventHandler):
    def __init__(self) -> None:
        super().__init__()
        self._processed: set[str] = set()

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return

        src = Path(event.src_path)

        if src.suffix.lower() != ".md":
            log.info("Ignored (not .md): %s", src.name)
            return

        # Deduplicate: watchdog fires multiple events for the same file
        if event.src_path in self._processed:
            return
        self._processed.add(event.src_path)

        # Give the OS time to finish moving the file
        time.sleep(0.5)

        # File may already be gone if a duplicate event beat us here
        if not src.exists():
            return

        try:
            content = src.read_text(encoding="utf-8")
            meta = _parse_frontmatter(content)

            action = meta.get("action", "unknown")
            topic = meta.get("topic", src.name)

            # Log intent based on mode
            if DRY_RUN:
                log.info("[DRY RUN] Would execute: %s — %s", action, topic)
            else:
                log.info("Executing: %s — %s", action, topic)

            now = datetime.now(timezone.utc)

            # Append structured entry to today's log
            _append_log({
                "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "component": "orchestrator",
                "level": "info",
                "action": action,
                "topic": topic,
                "source_file": src.name,
                "dry_run": DRY_RUN,
                "result": "completed",
            })

            # Move file from /Approved/ to /Done/
            dest = DONE / src.name
            if dest.exists():
                ts = now.strftime("%Y%m%d_%H%M%S")
                dest = DONE / f"{src.stem}_{ts}{src.suffix}"
            shutil.move(str(src), str(dest))

            # Update the dashboard
            _update_dashboard(src.name, meta, now)

            log.info("Completed: %s → /Done/", src.name)

        except Exception:
            log.exception("Error processing approved file: %s", src.name)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    APPROVED.mkdir(parents=True, exist_ok=True)
    DONE.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    mode = "DRY RUN" if DRY_RUN else "LIVE"
    log.info("Orchestrator running in %s mode — watching /Approved/", mode)

    handler = ApprovalHandler()
    observer = Observer()
    observer.schedule(handler, str(APPROVED), recursive=False)
    observer.start()

    try:
        while observer.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        observer.stop()
        observer.join()
        log.info("Orchestrator stopped.")


if __name__ == "__main__":
    main()

"""
File Drop Watcher — Perception Layer
Monitors /Drop_Here/ in the Obsidian vault and creates action files
in /Needs_Action/ for any .md or .txt file dropped there.
"""

import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

import os

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

VAULT_PATH = Path(os.environ["VAULT_PATH"])
DROP_HERE = VAULT_PATH / "Drop_Here"
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
DONE_ORIGINALS = VAULT_PATH / "Done" / "originals"

ALLOWED_SUFFIXES = {".md", ".txt"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("file_drop_watcher")


# ---------------------------------------------------------------------------
# Action file builder
# ---------------------------------------------------------------------------

def _build_action_file(original_path: Path) -> tuple[str, str]:
    """Return (filename, content) for the new action file."""
    now = datetime.now(timezone.utc)
    timestamp_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    timestamp_short = now.strftime("%Y%m%d_%H%M")

    stem = original_path.stem
    action_filename = f"DROP_{stem}_{timestamp_short}.md"

    raw_content = original_path.read_text(encoding="utf-8")

    content = f"""---
type: thought_drop
source: file_drop
original_file: {original_path.name}
created: {timestamp_iso}
status: pending
---

## Raw Content

{raw_content}

## Instructions for Claude

Read the raw content above. Use the draft_linkedin_post skill to create a polished LinkedIn post.
Read /Company_Handbook.md for tone and identity rules.
Save the approval request to /Pending_Approval/ and wait for human approval.
"""

    return action_filename, content


# ---------------------------------------------------------------------------
# Watchdog event handler
# ---------------------------------------------------------------------------

class DropHandler(FileSystemEventHandler):
    def __init__(self) -> None:
        super().__init__()
        self._processed: set[str] = set()

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return

        src = Path(event.src_path)

        if src.suffix.lower() not in ALLOWED_SUFFIXES:
            log.info("Ignored (not .md/.txt): %s", src.name)
            return

        # Deduplicate: watchdog fires created + modified for the same file
        if event.src_path in self._processed:
            return
        self._processed.add(event.src_path)

        # Give the OS time to finish writing the file
        time.sleep(0.5)

        # File may already be gone if a duplicate event beat us here
        if not src.exists():
            return

        try:
            action_filename, content = _build_action_file(src)

            # Write action file
            action_path = NEEDS_ACTION / action_filename
            action_path.write_text(content, encoding="utf-8")

            # Move original to Done/originals/
            dest = DONE_ORIGINALS / src.name
            # Avoid collisions if a file with the same name was already archived
            if dest.exists():
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                dest = DONE_ORIGINALS / f"{src.stem}_{ts}{src.suffix}"
            shutil.move(str(src), str(dest))

            log.info("Created action file: %s", action_filename)

        except Exception:
            log.exception("Error processing dropped file: %s", src.name)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # Ensure required folders exist
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    DONE_ORIGINALS.mkdir(parents=True, exist_ok=True)
    DROP_HERE.mkdir(parents=True, exist_ok=True)

    log.info("File Drop Watcher started — watching %s", DROP_HERE)

    handler = DropHandler()
    observer = Observer()
    observer.schedule(handler, str(DROP_HERE), recursive=False)
    observer.start()

    try:
        while observer.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        observer.stop()
        observer.join()
        log.info("File Drop Watcher stopped.")


if __name__ == "__main__":
    main()

"""
Weekly Briefing — Weekly Creator Retrospective Trigger
Invoked by PM2 cron every Sunday at 10:00 AM (after content_calendar at 9:00 AM).
Calls Claude Code in non-interactive mode with the weekly_creator_briefing prompt.
Runs once per execution — PM2 handles the schedule.
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

PROJECT_DIR = Path(__file__).parent.parent  # D:\ai-employee-project
VAULT_PATH = Path(os.environ["VAULT_PATH"])

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("weekly_briefing")

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

prompt = """
Read the skill at .claude/skills/weekly_creator_briefing.md and execute it fully.
Generate this week's creator briefing and save it to /Pending_Approval/.
"""

# ---------------------------------------------------------------------------
# Claude executable resolver
# ---------------------------------------------------------------------------

def _find_claude() -> tuple[str, bool]:
    """Return (executable_path, use_shell) for the Claude Code binary.

    Resolution order:
    1. shutil.which("claude")     — works on macOS/Linux; also finds claude.cmd
                                    on Windows when PATHEXT includes .CMD
    2. shutil.which("claude.cmd") — explicit fallback for Windows npm installs
    3. "claude" with shell=True   — last resort: let cmd.exe resolve the PATH
    """
    for name in ("claude", "claude.cmd"):
        path = shutil.which(name)
        if path:
            return path, False

    # Neither found via which — hand off to the OS shell
    return "claude", True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("[WeeklyBriefing] Generating weekly creator briefing...")
    log.info("Project dir : %s", PROJECT_DIR)
    log.info("Vault path  : %s", VAULT_PATH)

    claude_exe, use_shell = _find_claude()
    log.info(
        "Claude executable : %s%s",
        claude_exe,
        " (shell=True fallback)" if use_shell else "",
    )

    try:
        result = subprocess.run(
            [claude_exe, "-p", prompt.strip()],
            capture_output=True,
            text=True,
            timeout=600,
            shell=use_shell,
            cwd=str(PROJECT_DIR),
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        log.error("[WeeklyBriefing] ERROR — Claude Code not installed or not in PATH")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        log.error("[WeeklyBriefing] ERROR — Claude Code timed out after 10 minutes")
        sys.exit(1)
    except Exception as exc:
        log.error("[WeeklyBriefing] ERROR — %s", exc)
        sys.exit(1)

    # Log the tail of Claude's stdout (keep it manageable)
    stdout = result.stdout.strip()
    if stdout:
        tail = stdout[-500:] if len(stdout) > 500 else stdout
        log.info("Claude Code output (last 500 chars):\n%s", tail)
    else:
        log.info("Claude Code produced no stdout output")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        log.error(
            "[WeeklyBriefing] ERROR — Claude Code exited with code %d%s",
            result.returncode,
            f"\nstderr: {stderr}" if stderr else "",
        )
        sys.exit(result.returncode)

    log.info("[WeeklyBriefing] Done — briefing saved to Pending_Approval/")


if __name__ == "__main__":
    main()

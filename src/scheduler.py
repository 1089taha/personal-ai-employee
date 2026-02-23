"""
Scheduler — Reasoning Loop Trigger
Invoked by PM2 cron. Calls Claude Code in non-interactive mode with the
reasoning_loop prompt. Runs once per execution — PM2 handles the schedule.
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
log = logging.getLogger("scheduler")

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(vault_path: Path) -> str:
    return (
        f"Read the skill at .claude/skills/reasoning_loop.md and execute it fully. "
        f"The Obsidian vault is at {vault_path}. "
        f"Survey /Needs_Action/, create a Plan.md, process all tasks using the appropriate skills, "
        f"update Dashboard.md, and log everything to /Logs/. "
        f"If /Needs_Action/ is empty, just update Dashboard.md and exit."
    )

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
    log.info("Scheduler triggered — invoking Claude Code reasoning loop")
    log.info("Project dir : %s", PROJECT_DIR)
    log.info("Vault path  : %s", VAULT_PATH)

    prompt = _build_prompt(VAULT_PATH)

    claude_exe, use_shell = _find_claude()
    log.info(
        "Claude executable : %s%s",
        claude_exe,
        " (shell=True fallback)" if use_shell else "",
    )

    try:
        result = subprocess.run(
            [claude_exe, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=600,
            shell=use_shell,
            cwd=str(PROJECT_DIR),
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        log.error("Claude Code not installed or not in PATH")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        log.error("Claude Code timed out after 10 minutes")
        sys.exit(1)
    except Exception as exc:
        log.exception("Unexpected error invoking Claude Code: %s", exc)
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
            "Claude Code exited with code %d%s",
            result.returncode,
            f"\nstderr: {stderr}" if stderr else "",
        )
        sys.exit(result.returncode)

    log.info("Scheduler complete")


if __name__ == "__main__":
    main()

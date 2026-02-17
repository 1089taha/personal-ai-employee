"""
News Watcher — Perception Layer
Fetches the latest AI/tech news via Tavily and creates action files
in /Needs_Action/ so Claude Code can draft LinkedIn posts about them.

Runs once per execution — schedule daily via PM2 cron.
"""

import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

VAULT_PATH = Path(os.environ["VAULT_PATH"])
NEEDS_ACTION = VAULT_PATH / "Needs_Action"

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_ENDPOINT = "https://api.tavily.com/search"

SEARCH_TOPICS = [
    "AI agents development 2026",
    "Claude AI Anthropic latest",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("news_watcher")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_slug(topic: str) -> str:
    """Convert a topic string to a filename-safe lowercase slug."""
    slug = topic.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _fetch_top_result(topic: str) -> dict | None:
    """Call Tavily and return the top result dict, or None on failure."""
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": topic,
        "max_results": 3,
        "search_depth": "basic",
        "include_answer": False,
    }
    try:
        resp = requests.post(TAVILY_ENDPOINT, json=payload, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
    except requests.RequestException as exc:
        log.error("Tavily API call failed for topic %r: %s", topic, exc)
        return None


def _build_action_file(topic: str, article: dict, now: datetime) -> tuple[str, str]:
    """Return (filename, content) for the news action file."""
    timestamp_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = now.strftime("%Y%m%d")
    slug = _safe_slug(topic)
    filename = f"NEWS_{date_str}_{slug}.md"

    title = article.get("title", "Unknown title")
    url = article.get("url", "")
    published = article.get("published_date", "Not available")
    snippet = article.get("content", "No content available.")

    content = f"""---
type: tech_news
topic: "{topic}"
source: tavily
article_title: "{title}"
article_url: "{url}"
created: {timestamp_iso}
status: pending
---

## Article

**Title**: {title}
**URL**: {url}
**Published**: {published}

## Snippet

{snippet}

## Instructions for Claude

Read the article above. Use the draft_linkedin_post skill to write a LinkedIn post sharing this news with Taha's personal perspective and insights.
This is NOT a summary — it's an opinion piece. What does this mean for builders?
Read /Company_Handbook.md for tone and identity rules.
Save the approval request to /Pending_Approval/ and wait for human approval.
"""
    return filename, content


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("News Watcher started — fetching latest tech news")

    if not TAVILY_API_KEY:
        log.error("TAVILY_API_KEY is not set in .env — exiting")
        sys.exit(1)

    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)

    queued = 0

    for topic in SEARCH_TOPICS:
        log.info("Searching: %r", topic)

        article = _fetch_top_result(topic)
        if article is None:
            log.warning("No result returned for topic %r — skipping", topic)
            continue

        now = datetime.now(timezone.utc)
        filename, content = _build_action_file(topic, article, now)

        action_path = NEEDS_ACTION / filename
        action_path.write_text(content, encoding="utf-8")

        log.info("Created news action: %s", filename)
        queued += 1

    log.info("News fetch complete. %d article(s) queued.", queued)


if __name__ == "__main__":
    main()

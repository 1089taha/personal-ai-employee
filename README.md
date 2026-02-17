
# Personal AI Employee — LinkedIn Brand Builder

> **GIAIC Hackathon 0 | Bronze Tier Submission**
> Built by Taha Khan ([@1089taha](https://github.com/1089taha))

---

## About

A locally-running autonomous agent that helps build a personal LinkedIn brand. It monitors file drops and fetches daily tech news, uses Claude Code to draft polished LinkedIn posts in the owner's voice, and requires explicit human approval before anything is posted. No cloud server, no always-on subscription — runs entirely on your own machine.

The core idea: treat content creation like a software pipeline. Every task is a markdown file. Every stage is a folder. Moving a file between folders **is** the state transition.

---

## Architecture

The system follows a five-stage pipeline:

```
Perception → Memory → Reasoning → Approval → Action
```

| Stage | What Happens |
|-------|-------------|
| **Perception** | Watchers detect new inputs (file drops, news) and write action files |
| **Memory** | Obsidian vault stores every task as a `.md` file; folder = state |
| **Reasoning** | Claude Code reads action files and executes skills to produce drafts |
| **Approval** | Human reviews drafts in Obsidian; moves file to `/Approved/` or `/Rejected/` |
| **Action** | Orchestrator detects approval, logs the action, moves file to `/Done/` |

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        PERCEPTION LAYER                         │
│                                                                 │
│  ┌─────────────────┐        ┌─────────────────┐                │
│  │  File Drop      │        │  News Watcher   │                │
│  │  Watcher        │        │  (daily cron)   │                │
│  │  (continuous)   │        │                 │                │
│  └────────┬────────┘        └────────┬────────┘                │
│           │                          │                          │
└───────────┼──────────────────────────┼──────────────────────────┘
            │ writes .md action files  │
            ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MEMORY LAYER (Vault)                       │
│                                                                 │
│                      /Needs_Action/                             │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │ Claude Code reads & processes
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     REASONING LAYER                             │
│                                                                 │
│   Claude Code runs skills:                                      │
│   • draft_linkedin_post   • classify_message                    │
│   • update_dashboard                                            │
│                                                                 │
│   Output → /Pending_Approval/      Archive → /Plans/            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPROVAL LAYER                              │
│                                                                 │
│   Taha reviews draft in Obsidian                                │
│   Approve → move to /Approved/                                  │
│   Reject  → move to /Rejected/                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Orchestrator detects file
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ACTION LAYER                               │
│                                                                 │
│   Orchestrator logs action, updates Dashboard.md                │
│   Moves file to /Done/       (Silver: executes API call)        │
└─────────────────────────────────────────────────────────────────┘
```

### Folder-Based State Machine

The Obsidian vault **is** the database. No Redis, no PostgreSQL — just folders.

```
/Needs_Action/      <- task exists, waiting to be processed
/Plans/             <- task processed, reasoning archived
/Pending_Approval/  <- draft ready, waiting for human review
/Approved/          <- human approved, waiting for execution
/Done/              <- completed (moved here by Orchestrator)
/Rejected/          <- human rejected (kept for audit trail)
/Drop_Here/         <- drop thought files here
/Logs/              <- daily JSON logs (YYYY-MM-DD.json)
```

A file's location **is** its state. Moving it **is** the transition. No code changes needed to track status — just open Obsidian.

---

## Project Structure

```
ai-employee-project/
├── CLAUDE.md                       # Master instructions for Claude Code sessions
├── README.md                       # This file
├── ecosystem.config.js             # PM2 process manager config
├── pyproject.toml                  # Python dependencies (uv)
├── .env                            # Secrets — never committed
├── .env.example                    # Template for .env
├── main.py                         # Entry point placeholder
├── .claude/
│   └── skills/
│       ├── draft_linkedin_post.md  # Skill: draft LinkedIn posts
│       ├── classify_message.md     # Skill: classify incoming messages
│       └── update_dashboard.md    # Skill: refresh Dashboard.md
└── src/
    ├── orchestrator.py             # Watches /Approved/, executes + logs
    └── watchers/
        ├── filesystem_watcher.py   # Watches /Drop_Here/ for thought drops
        └── news_watcher.py         # Fetches daily AI/tech news via Tavily
```

---

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Reasoning Engine | Claude Code (claude-sonnet-4-5) | Reads skills, drafts content, manages vault files |
| Perception — File Drop | Python + watchdog | Real-time monitoring of `/Drop_Here/` folder |
| Perception — News | Python + Tavily API | Daily search for AI/tech articles |
| Memory / State Machine | Obsidian vault (markdown files) | Stores every task; folder = pipeline stage |
| GUI / Dashboard | Obsidian app | Visual view of vault; used for human approval |
| Execution + Logging | Python + watchdog (Orchestrator) | Detects approvals, logs actions, moves to Done |
| Process Manager | PM2 | Keeps watchers alive; cron-schedules news fetch |
| Package Manager | uv | Fast Python dependency management |

---

## Agent Skills

Skills are markdown spec files in `.claude/skills/`. Claude Code reads them like a job description and executes them step by step.

### `draft_linkedin_post`

Triggered by files in `/Needs_Action/` with type `thought_drop` or `tech_news`. Reads the raw content, applies tone and identity rules from `Company_Handbook.md`, and drafts a LinkedIn post under 1,300 characters in the owner's authentic voice. Saves a structured approval request to `/Pending_Approval/` with expiry timestamp.

For `tech_news` inputs: writes an opinion piece with the owner's personal perspective — not a summary.

### `update_dashboard`

Scans all vault folders, counts files in each pipeline stage, reads today's JSON log, and regenerates `Dashboard.md` with current system status — watcher health, pipeline counts, pending reviews, weekly stats, and today's activity feed. Runs after every skill and on session start.

### `classify_message`

Classifies incoming messages (email, WhatsApp) by priority: `urgent`, `normal`, `low`, or `flagged`. Flags sensitive content — complaints, conflicts, emotional topics — for the owner to handle personally, without generating a draft. Designed for Silver tier when Gmail and WhatsApp watchers are fully wired in.

---

## Setup

### Prerequisites

- **Python 3.11+** with [uv](https://docs.astral.sh/uv/) installed
- **Node.js 18+** with [PM2](https://pm2.keymetrics.io/) installed globally (`npm install -g pm2`)
- **[Claude Code](https://github.com/anthropics/claude-code)** CLI installed and authenticated
- **[Obsidian](https://obsidian.md/)** desktop app
- A **Tavily API key** — free tier at [tavily.com](https://tavily.com)

### 1. Clone the repo

```bash
git clone https://github.com/1089taha/ai-employee-project.git
cd ai-employee-project
```

### 2. Install Python dependencies

```bash
uv sync
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
VAULT_PATH=C:\path\to\your\obsidian_vault
TAVILY_API_KEY=tvly-your-key-here
DRY_RUN=true
```

### 4. Create the Obsidian vault

Open Obsidian, create a new vault pointed at `VAULT_PATH`. Then create these folders inside it:

```
Needs_Action/
Plans/
Pending_Approval/
Approved/
Done/
Done/originals/
Rejected/
Drop_Here/
Logs/
```

Copy `Company_Handbook.md` into the vault root.

### 5. Update the PM2 interpreter path

Find the Python executable inside your project's virtual environment:

```bash
# Windows
where python       # run after: uv run where python

# macOS / Linux
which python       # run inside: uv run which python
```

Update the `interpreter` field in `ecosystem.config.js` to the full path (e.g. `D:\project\.venv\Scripts\python.exe`).

### 6. Start all processes

```bash
pm2 start ecosystem.config.js
pm2 save        # persist across reboots
pm2 startup     # generate the startup hook for your OS
```

Verify everything is running:

```bash
pm2 list
pm2 logs file-watcher
pm2 logs orchestrator
```

---

## How It Works

### Thought Drop Flow

1. Write a thought in any `.md` or `.txt` file
2. Drop it into `/Drop_Here/` in the vault
3. The File Drop Watcher detects it, creates a structured action file in `/Needs_Action/`, and archives the original to `/Done/originals/`
4. Open Claude Code — it reads the action file and runs the `draft_linkedin_post` skill
5. A polished draft appears in `/Pending_Approval/`
6. Review in Obsidian: move to `/Approved/` to accept, `/Rejected/` to decline
7. The Orchestrator detects the approved file, logs it, updates the dashboard, and moves it to `/Done/`

### Daily News Flow

1. PM2 runs `news_watcher.py` at 8:00 AM every day via cron
2. It calls the Tavily API for 2 configured topics and writes action files in `/Needs_Action/`
3. Claude Code processes them with `draft_linkedin_post` — producing opinion pieces, not summaries
4. Drafts land in `/Pending_Approval/` for review, same approval flow as above

---

## Security

| Concern | How It's Handled |
|---------|-----------------|
| API keys | Stored in `.env`, in `.gitignore`, never committed to version control |
| Human approval | Every external action requires a file in `/Approved/` — nothing is auto-posted |
| Dry run mode | `DRY_RUN=true` by default — Orchestrator logs intent but takes no external action |
| Local-first | All processing happens on your machine; no data leaves without your approval |
| Audit trail | Files are never deleted, only moved; full history preserved in `/Logs/` |

---

## Roadmap

| Tier | Status | Goal |
|------|--------|------|
| **Bronze** | Current | File drop watcher, news watcher, orchestrator, Claude Code drafting, Obsidian approval flow |
| Silver | Planned | Gmail watcher, WhatsApp watcher, auto-posting after approval, content calendar |
| Gold | Planned | Twitter/X, Medium, analytics, content repurposing across platforms |
| Platinum | Planned | Learns from engagement, proactive suggestions, relationship tracking |

---

## Hackathon

**Event:** GIAIC Hackathon 0 — Building Autonomous FTEs in 2026

**Tier:** Bronze (Foundation)

**Author:** Built by Taha Khan — a 20-year-old builder from Karachi, Pakistan, obsessed with AI systems and agentic architecture. Currently studying Data Science at UIT and Agentic AI at GIAIC. I don't just learn things — I build them. This project is proof.
**GitHub:** [github.com/1089taha](https://github.com/1089taha)
**LinkedIN:** [www.linkedin.com/in/taha-khan-306750329](www.linkedin.com/in/taha-khan-306750329)
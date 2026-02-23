# Personal AI Employee

An autonomous AI agent that monitors Gmail, WhatsApp, news feeds, and file drops — drafts content, classifies messages, and posts to LinkedIn via official API. Built on a folder-based state machine using Obsidian as the dashboard.

---

## How It Works

Every task is a markdown file. Every folder in the Obsidian vault is a pipeline stage. Moving a file between folders **is** the state transition — no database, no separate backend.

Watchers run continuously as PM2 processes, detecting new inputs and writing structured action files into `/Needs_Action/`. The AI Scheduler triggers Claude Code every 30 minutes to process pending tasks, execute skills, and produce drafts in `/Pending_Approval/`. The human reviews in Obsidian, moves a file to `/Approved/`, and the Orchestrator handles execution.

---

## Architecture

```
Perception → Memory → Reasoning → Approval → Action
```

| Stage | What Happens |
|-------|-------------|
| Perception | Watchers detect new inputs and write `.md` action files |
| Memory | Obsidian vault stores every task; folder = pipeline state |
| Reasoning | Claude Code reads action files and executes skills to produce drafts |
| Approval | Human reviews drafts in Obsidian; moves to `/Approved/` or `/Rejected/` |
| Action | Orchestrator detects approval, posts via LinkedIn API, archives to `/Done/` |

### Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           PERCEPTION LAYER                               │
│                                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ File Drop  │  │   Gmail    │  │  WhatsApp  │  │    News    │         │
│  │  Watcher   │  │  Watcher   │  │  Watcher   │  │  Watcher   │         │
│  │(continuous)│  │(polls 2m)  │  │(on demand) │  │(daily 8AM) │         │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘         │
└────────┼───────────────┼───────────────┼───────────────┼─────────────────┘
         │               │               │               │
         └───────────────┴───────────────┴───────────────┘
                         │ writes .md action files
                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      MEMORY LAYER (Obsidian Vault)                       │
│                                                                          │
│                           /Needs_Action/                                 │
│                                 │                                        │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │ AI Scheduler triggers every 30 min
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          REASONING LAYER                                 │
│                                                                          │
│   Claude Code executes skills:                                           │
│   • draft_linkedin_post   • classify_message                             │
│   • update_dashboard      • reasoning_loop                               │
│                                                                          │
│   Output → /Pending_Approval/              Archive → /Plans/             │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          APPROVAL LAYER                                  │
│                                                                          │
│   Human reviews draft in Obsidian                                        │
│   Approve → move to /Approved/                                           │
│   Reject  → move to /Rejected/                                           │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │ Orchestrator detects file
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           ACTION LAYER                                   │
│                                                                          │
│   Orchestrator posts via LinkedIn API, updates Dashboard.md              │
│   Moves file to /Done/                                                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

The Obsidian vault **is** the database. No Redis, no PostgreSQL — just folders.

```
/Needs_Action/       new inputs from watchers, awaiting processing
/Plans/              reasoning logs and execution plans, archived after processing
/Pending_Approval/   drafts ready for human review
/Approved/           human-approved, queued for execution
/Done/               completed actions (moved here by Orchestrator)
/Done/originals/     original thought drop files, preserved after processing
/Rejected/           rejected drafts, kept for audit trail
/Drop_Here/          drop .md or .txt thought files here to trigger drafting
/Logs/               daily JSON activity logs (YYYY-MM-DD.json)
```

---

## Process Management

| Process | Type | Schedule | Description |
|---------|------|----------|-------------|
| `file-watcher` | Continuous | 24/7 | Monitors `/Drop_Here/` for new files |
| `orchestrator` | Continuous | 24/7 | Detects approved files, executes actions |
| `gmail-watcher` | Continuous | Polls every 2 min | Monitors inbox, creates action files |
| `news-watcher` | Cron | Daily 8 AM | Fetches AI/tech news via Tavily API |
| `ai-scheduler` | Cron | Every 30 min | Triggers Claude Code reasoning loop |
| `whatsapp-watcher` | Manual | On demand | Monitors WhatsApp Web via Playwright |

All processes except `whatsapp-watcher` are managed by PM2 via `ecosystem.config.js`.

---

## Agent Skills

Skills are markdown spec files in `.claude/skills/`. Claude Code reads them and executes them step by step.

- **`draft_linkedin_post`** — Drafts a LinkedIn post from a thought drop or tech news article, in the owner's voice, under 1,300 characters.
- **`classify_message`** — Classifies incoming messages by priority (`urgent`, `normal`, `low`, `flagged`) and surfaces sensitive content for human handling.
- **`update_dashboard`** — Scans all vault folders and regenerates `Dashboard.md` with current pipeline counts, watcher health, and today's activity feed.
- **`reasoning_loop`** — Master orchestration skill; surveys all pending work, builds an execution plan, and delegates to specialist skills in priority order.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Reasoning engine | Claude Code (claude-sonnet-4-6) |
| Language | Python 3.11+ |
| Vault / state machine | Obsidian (markdown files) |
| Process manager | PM2 |
| Email integration | Gmail API (OAuth 2.0, read-only) |
| Social posting | LinkedIn API (official, OAuth 2.0) |
| WhatsApp monitoring | Playwright on WhatsApp Web |
| News search | Tavily API |
| File monitoring | watchdog |
| Package manager | uv |

---

## Setup

### Prerequisites

- Python 3.11+ with [uv](https://docs.astral.sh/uv/) installed
- Node.js 18+ with PM2 installed globally (`npm install -g pm2`)
- [Claude Code](https://github.com/anthropics/claude-code) CLI installed and authenticated
- [Obsidian](https://obsidian.md/) desktop app
- API keys for Tavily, Gmail (Google Cloud project), and LinkedIn (Developer app)

### 1. Clone and install

```bash
git clone https://github.com/1089taha/ai-employee-project.git
cd ai-employee-project
uv sync
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `VAULT_PATH` | Absolute path to your Obsidian vault |
| `TAVILY_API_KEY` | Tavily API key (free tier at tavily.com) |
| `DRY_RUN` | Set `true` to log actions without executing them |
| `GMAIL_CREDENTIALS_PATH` | Path to Google OAuth credentials JSON |
| `LINKEDIN_CLIENT_ID` | LinkedIn app client ID |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn app client secret |

### 3. Create the Obsidian vault

Open Obsidian, create a new vault at `VAULT_PATH`, then create these folders inside it:

```
Needs_Action/  Plans/  Pending_Approval/  Approved/
Done/  Done/originals/  Rejected/  Drop_Here/  Logs/
```

Copy `Company_Handbook.md` into the vault root.

### 4. Set up OAuth

**Gmail:**
```bash
uv run python src/gmail_auth_setup.py
```
Follow the browser prompt. Token is saved locally and reused automatically.

**LinkedIn:**
```bash
uv run python src/linkedin_auth_setup.py
```
Follow the browser prompt. Token is saved locally and reused automatically.

### 5. Update the PM2 interpreter path

Set the `interpreter` field in `ecosystem.config.js` to the full path of your venv Python executable:

```bash
# find it with:
uv run python -c "import sys; print(sys.executable)"
```

### 6. Start all processes

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

Verify:

```bash
pm2 list
pm2 logs file-watcher
pm2 logs orchestrator
```

### 7. WhatsApp first-run

WhatsApp requires a QR scan on first use. Run it manually outside PM2:

```bash
uv run python src/watchers/whatsapp_watcher.py --first-run
```

Scan the QR code in the browser window that opens. Session is saved; subsequent runs use the saved session.

---

## Security

| Concern | How It's Handled |
|---------|-----------------|
| API keys | Stored in `.env`, in `.gitignore`, never committed |
| Human approval | Every external action requires a file in `/Approved/` — nothing is auto-posted |
| Dry run mode | `DRY_RUN=true` by default — logs intent, takes no external action |
| LinkedIn posting | Official LinkedIn API only — no scraping, no unofficial clients |
| Gmail access | Read-only OAuth scope — no write access to inbox |
| WhatsApp access | Read-only session — message detection only, no sending |
| Local-first | All processing runs on your machine; no data leaves without approval |
| Audit trail | Files are never deleted, only moved; full history in `/Done/` and `/Logs/` |

---

## Author

Built by [Taha Khan](https://www.linkedin.com/in/taha-khan-306750329) · tahakhalid317@gmail.com

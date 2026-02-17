# CLAUDE.md — Master Instructions for Personal AI Employee Project

**Last Updated:** 2026-02-16
**Owner:** Taha (@1089taha)
**Hackathon:** Panaversity Hackathon 0 — Building Autonomous FTEs in 2026

> This file is the **single source of truth** for every Claude Code session on this project.
> Read everything below carefully before making any code changes.

---

## PROJECT OVERVIEW

**Project Name:** Personal AI Employee — LinkedIn Brand Builder
**Architecture:** Local-First Agent | Human-in-the-Loop | Folder-Based State Machine
**Current Phase:** Bronze Tier (foundation)

This is a **locally-running autonomous agent system**. It monitors multiple input sources (Gmail, WhatsApp, file drops, tech news), drafts content and replies using Claude Code as the reasoning engine, and requires **explicit human approval** before any external action happens.

The **Obsidian vault** is both the dashboard and the state machine — every task is a markdown file, every folder is a state.

---

## ABOUT THE OWNER

**Name:** Taha, 20 years old, Karachi, Pakistan

**Education:**
- Data Science student at Usman Institute of Technology (UIT) — first semester SGPA 3.84, studying on student loan
- Learning Agentic AI at GIAIC (Governor Initiative for AI, Web 3.0 & Metaverse)

**Current Work:**
Teaching O-Level students. Came back from Hifz, struggled with basics — improved one student from 40% to 70% through concept-based teaching instead of rote memorization.

**Tech Stack:**
Python, TypeScript, Next.js, OpenAI Agent SDK, Claude Code, Spec-Driven Development

**GitHub:** [github.com/1089taha](https://github.com/1089taha)

**Career Goal:**
Become an architect and engineer who designs and builds end-to-end systems — architecture, features, deployment. Not just a coder.

**6-Month Focus:**
System design, Agentic AI, Data Science, building real projects, growing LinkedIn presence

**Dream Project:**
AI-powered research + content platform for YouTube documentary creators (SaaS)

**Background:**
Middle-class family, student loans, earning from tuitions. No rich family, no connections — just ambition and willingness to grind.

---

## LINKEDIN STRATEGY & PERSONAL BRAND

### Positioning
A 20-year-old builder who is learning AI and system design by **actually building things** — sharing the real journey with honesty, not fake guru advice.

### Target Audience
Other students, early-career developers, AI enthusiasts, tech professionals in Pakistan and globally.

### What Taha wants to be known for:
- Building real AI systems
- Learning in public
- Honest takes on tech
- The grind of building from nothing

### Content Pillars (what to post about)
1. **AI & Agentic Development** (Claude Code, agents, MCP, SDKs)
2. **Personal projects** and what I'm building (with technical details)
3. **Learning journey** and honest reflections (failures included)
4. **Tech career tips** from someone actually going through it
5. **Building in public** (hackathon progress, code snippets, architecture decisions)
6. **Teaching experiences** and education insights

### Engagement Strategy
Comment meaningfully on posts by thought leaders. Build trust through real value, not spam. Be the guy who adds something useful in every comment.

### Tone Rules

**Voice:**
- Nerdy but human. Genuinely excited about tech, not performing excitement
- Light humor — not forced jokes, but natural comedy from honesty (like struggling with Introduction to Computing, or breaking things while learning)
- Conversational, NOT corporate. Write like a real 20-year-old talks
- Short punchy lines. Real stories. Honest admissions. Specific details.

**NEVER use:**
- "In today's rapidly evolving landscape"
- "leveraging"
- "synergy"
- "game-changer"
- "thought leader"
- "delighted to announce"
- "humbled"
- "excited to share" (unless genuinely excited about something specific)

**Structure:**
- First line of every post MUST be a scroll-stopper — surprising, funny, or brutally honest
- Paragraphs: 1-2 sentences max (LinkedIn mobile formatting)
- End with a question that actually makes people want to respond
- 3-5 relevant hashtags at the bottom (not generic ones like #success or #motivation)

---

## SYSTEM ARCHITECTURE (ALL TIERS)

The system follows a:
**Perception → Memory → Reasoning → Approval → Action** pipeline

---

### PERCEPTION LAYER (Watchers)

Lightweight Python scripts that run continuously and detect new inputs. They write structured `.md` files into `/Needs_Action/`. Watchers are the AI Employee's sensory system.

All watchers follow a **BaseWatcher** pattern with `check_for_updates()` and `create_action_file()` methods.

#### Types of Watchers:

**1. File Drop Watcher**
- Uses `watchdog` library
- Monitors `/Drop_Here/` folder
- When a `.md` or `.txt` file is dropped, creates action file in `/Needs_Action/` with type `"thought_drop"`

**2. Gmail Watcher**
- Uses Google Gmail API (OAuth)
- Polls every 2 minutes for unread important emails
- Creates action files with type `"email"`

**3. WhatsApp Watcher**
- Uses Playwright on WhatsApp Web
- Monitors for unread messages
- Creates action files with type `"whatsapp"`
- Bronze: read-only detection concept, Silver+: full implementation

**4. Tech News Watcher**
- Uses Tavily API for web search to find latest AI/tech news
- Runs once daily
- Creates action files with type `"tech_news"`

---

### MEMORY LAYER (Obsidian Vault)

**Path:** `D:\obsidian_vault`

The vault is both the **GUI** (via Obsidian app) and the **state machine**. Every task is a `.md` file. The folder the file lives in IS its current state. Moving a file between folders IS the state transition. No database needed.

#### Folder Schema:

<!-- TODO: Complete folder schema section -->
<!-- Expected folders: /Needs_Action/, /In_Review/, /Approved/, /Sent/, /Archive/, etc. -->

---

### REASONING LAYER (Skills)

Claude Code executes predefined **skills** to process tasks from the Obsidian vault. Each skill is a specialized capability with specific triggers, inputs, and outputs.

**Skills Directory:** `D:\ai-employee-project\skills\`

Each skill is documented in its own `.md` file with:
- When to trigger the skill
- Required inputs
- Step-by-step execution process
- Quality checks and validation rules
- Example outputs

**Available Skills:**
- `draft_linkedin_post.md` — Drafts LinkedIn posts from thought drops or tech news

When Claude Code is invoked, it:
1. Scans `/Needs_Action/` for new files
2. Determines which skill(s) to execute based on file type
3. Loads the relevant skill specification from `/skills/`
4. Executes the skill following the documented process
5. Creates output files in appropriate vault folders
6. Updates `/Dashboard.md` with activity logs

---

## DEVELOPMENT PRINCIPLES

### Code Quality
- Write clean, well-documented Python code
- Use type hints where appropriate
- Follow PEP 8 style guidelines
- Prefer explicit over implicit
- Keep functions small and focused

### Architecture Decisions
- Local-first: Everything runs on Taha's machine
- Human-in-the-loop: No external actions without approval
- Folder-based state machine: File location = task state
- Obsidian as GUI: No separate web dashboard needed

### Security
- All API keys in `.env` (never commit)
- OAuth tokens stored securely
- No data sent to external services without approval
- All drafts reviewed before posting

### Testing Strategy
- Manual testing for Bronze tier
- Automated tests for critical paths in Silver+
- Always test watchers with mock data first
- Log everything for debugging

---

## TIER ROADMAP

### Bronze Tier (Current)
**Goal:** Prove the concept works locally
- File drop watcher functional
- Gmail watcher functional
- Basic Obsidian vault structure
- Manual approval via Obsidian
- Draft one LinkedIn post successfully

### Silver Tier
**Goal:** Full automation with human approval
- WhatsApp watcher fully implemented
- Automated posting after approval
- Scheduled content calendar
- Reply drafting for comments

### Gold Tier
**Goal:** Multi-platform expansion
- Twitter/X integration
- Medium/blog integration
- Analytics and insights
- Content repurposing

### Platinum Tier
**Goal:** Full AI employee
- Learning from engagement data
- Proactive content suggestions
- Relationship management
- Revenue tracking

---

## WORKING WITH CLAUDE CODE

### When Starting a Session
1. Read this CLAUDE.md file first
2. Check git status and recent commits
3. Ask Taha what phase/feature we're building
4. Understand the context before writing code

### When Writing Code
- Always read existing code before modifying
- Maintain consistency with existing patterns
- Don't over-engineer Bronze tier features
- Keep it simple and working over perfect and broken

### When Testing
- Test watchers with mock data first
- Verify Obsidian vault structure manually
- Check API credentials are working
- Log outputs for debugging

### When Stuck
- Ask Taha for clarification (don't guess requirements)
- Check if a simpler solution exists
- Document blockers clearly
- Propose alternatives if blocked

---

## PROJECT STRUCTURE

```
D:\ai-employee-project/
├── CLAUDE.md              # This file - master instructions
├── README.md              # Public-facing project description
├── main.py                # Entry point for the system
├── pyproject.toml         # Python dependencies
├── .env                   # API keys and secrets (not committed)
├── skills/                # Skill specifications (reasoning layer)
│   └── draft_linkedin_post.md
├── watchers/              # Perception layer scripts
│   ├── base_watcher.py
│   ├── file_drop_watcher.py
│   ├── gmail_watcher.py
│   ├── whatsapp_watcher.py
│   └── tech_news_watcher.py
├── reasoning/             # Claude Code integration
│   └── draft_generator.py
└── utils/                 # Shared utilities
    ├── obsidian.py        # Vault manipulation
    └── logging.py         # Logging setup

D:\obsidian_vault/
├── Needs_Action/          # New inputs from watchers
├── Pending_Approval/      # Drafts ready for human review
├── Approved/              # Approved, ready to send
├── Sent/                  # Posted/sent actions (archive)
├── Rejected/              # Rejected drafts (archive)
├── Plans/                 # Processed action files & reasoning logs
└── Archive/               # Old completed tasks
```

---

## CONTACT & LINKS

**GitHub:** [github.com/1089taha](https://github.com/1089taha)
**LinkedIn:** [Connect with Taha]
**Hackathon:** Panaversity Hackathon 0

---

**Remember:** This is a real project built by a 20-year-old student with loans and ambition. Every feature should be practical, working, and useful — not just impressive on paper. Build real things that actually work.

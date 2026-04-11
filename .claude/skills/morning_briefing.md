# Skill: morning_briefing

**Type:** Daily Summary & Proactive Reporting Skill
**Triggers:** Scheduler at 7:00 AM daily, or manual file drop of `morning_briefing_now.md` in `Drop_Here/`
**Output:** Morning briefing approval request in `/Pending_Approval/`

---

## Description

This skill generates a single, scannable daily briefing that gives Taha a complete picture of everything he needs to know before starting his day. It reads the vault state, pulls the latest finance pulse, checks system logs for errors, and adds one proactive suggestion based on what it notices.

This skill is **read-only and report-only**. It does not process tasks, run other skills, or move files (other than the briefing it creates). Its only job is to observe, summarize, and surface.

Target reading time: under 60 seconds.

---

## When to Trigger

- **Scheduler:** Called automatically every day at 7:00 AM
- **Manual trigger:** A file named `morning_briefing_now.md` is dropped in `Drop_Here/`, which creates a `morning_briefing_trigger` type action file in `/Needs_Action/`

---

## Input Requirements

Read all of these before generating the briefing:

| Source | What to Extract |
|--------|----------------|
| `/Pending_Approval/` | Count of files; one-line summary of each |
| `/Needs_Action/` | Count of unprocessed files waiting for Claude |
| `/Finance_History/` | Most recent `FINANCE_*.md` — week date, savings rate, key advice line |
| `/Pending_Approval/FINANCE_BRIEFING_*.md` | If a finance briefing is pending approval, prefer this over Finance_History for the finance pulse |
| `/Logs/YYYY-MM-DD.json` | Today's and yesterday's log files — scan for ERROR or WARNING level entries in last 24 hours |
| `/Done/` | Files modified or created in the last 24 hours |
| `/Company_Handbook.md` | Taha's context — used only if needed for the Today's Suggestion |

---

## Step-by-Step Process

### 1. Collect All Data

Work through each source methodically. Collect all data before writing a single line of the briefing.

**1.1 — Pending Approval**

List all `.md` files in `/Pending_Approval/`. For each file:
- Read its YAML front-matter to extract `action`, `type`, and a brief topic description
- Summarize in one line: what it is and what Taha needs to do with it
- Flag any expired files (where `expires` field is in the past)

Map action types to human-readable labels:
- `linkedin_post` → LinkedIn post draft
- `send_gmail` → Gmail reply draft
- `send_whatsapp` → WhatsApp reply draft
- `finance_briefing` → Weekly finance briefing
- `morning_briefing` → Previous morning briefing (can archive)
- Anything else → Use the `action` field value directly

**1.2 — AI Queue**

Count `.md` files in `/Needs_Action/`. No need to read them — just the count.

**1.3 — Finance Pulse**

Check `/Pending_Approval/` first for any `FINANCE_BRIEFING_*.md` file (sorted newest first). If found, read it and extract:
- Week date (from `week:` YAML field)
- Savings rate (from `savings_rate:` YAML field)
- One line from the `## AI Advisor's Take` section — pick the most actionable sentence

If no pending finance briefing, check `/Finance_History/` for the most recent `FINANCE_*.md` file (sort by filename descending — filenames are `FINANCE_YYYYMMDD.md`). Extract:
- Week date (from YAML `week:` field)
- Savings rate (from YAML `savings_rate:` field — note: history files may not have this, fall back to calculating from `income` and `savings` fields if present)

If neither source has data, note that no finance entries exist yet.

Also note how many days ago the last entry was — needed for Today's Suggestion.

**1.4 — Completed Yesterday**

List files in `/Done/` that were moved there in the last 24 hours. Use file modification time to determine recency. For each file, extract a one-line description from the filename or its YAML front-matter `action` field.

If `/Done/` contains a subfolder structure (e.g., `/Done/originals/`), scan the top-level Done folder only for `.md` files — ignore binary or non-markdown files.

> **NOTE FOR WINDOWS:** When listing files by date in the vault, always use `cmd /c dir [path] /T:W /OD` instead of PowerShell `Get-ChildItem` commands — PowerShell has encoding issues in this environment.

**1.5 — System Alerts**

Read the log file for today (`/Logs/YYYY-MM-DD.json`) and yesterday (`/Logs/YYYY-MM-DD.json` for yesterday's date) if they exist.

Scan all entries for `"level": "error"` or `"level": "warning"` where the timestamp is within the last 24 hours.

For each alert found, extract:
- Timestamp
- Component name
- Message

If log files don't exist or are malformed, note "Log files not available" rather than erroring.

### 2. Generate the Briefing

With all data collected, build the briefing file. Write it in one pass — do not write partial drafts.

**File name:** `MORNING_BRIEFING_[YYYYMMDD].md`
Example: `MORNING_BRIEFING_20260301.md`

**Save to:** `/Pending_Approval/`

Use this **exact structure:**

```markdown
---
type: approval_request
action: morning_briefing
created: [ISO 8601 timestamp]
status: pending
---

# ☀️ Morning Briefing — [Weekday, DD Month YYYY]
*Generated at 7:00 AM by your AI Employee*

## 🔔 Needs Your Attention ([N] items)

[If Pending_Approval is empty:]
✅ Nothing pending — inbox zero.

[If files exist, list each with a one-line summary. Sort: finance briefings first, then LinkedIn posts, then Gmail/WhatsApp, then anything else:]
- 💰 [filename] — [one-line: what it is and what action Taha should take]
- 📝 [filename] — [one-line: what it is and what action Taha should take]
- 📧 [filename] — [one-line: what it is and what action Taha should take]

[If any files are expired, add a note:]
⚠️ [N] item(s) above are expired — review and archive or re-process.

## 🤖 AI Queue ([N] items)

[If Needs_Action is empty:]
Queue is clear.

[If files exist:]
[N] file(s) waiting to be processed. Claude will handle these in the next scheduled run.

## 💰 Finance Pulse

[If finance data exists:]
- Last entry: [week date, e.g., "week of 2026-03-01"]
- Savings rate: [X]%
- Key reminder: [one actionable sentence from AI Advisor's Take]

[If no finance data:]
No finance entries yet. Drop a finance_*.md file in Drop_Here/ to start tracking.

## ✅ Completed Yesterday

[If files were completed in last 24 hours:]
- [filename or description] — [what was done]
- [filename or description] — [what was done]

[If nothing:]
Nothing completed yesterday.

## ⚠️ System Alerts

[If no errors or warnings in last 24 hours:]
✅ All systems running normally.

[If alerts exist:]
- [timestamp short form, e.g., "02:15"] [component]: [message]
- [timestamp short form] [component]: [message]

## 💡 Today's Suggestion

[Exactly ONE suggestion — the most relevant one based on what the data shows. Pick the first that applies:]

[Check in this order:]
1. If Pending_Approval count > 5: "You have [N] items waiting for review. Spend 10 minutes in Obsidian today to clear the queue."
2. If finance entry is > 7 days old OR no finance entries exist: "It's been [N] days since your last finance entry. Drop a finance_*.md file in Drop_Here/ to stay on track." (or "No finance entries yet. Start this week." if none)
3. If no LinkedIn post file (LINKEDIN_POST_*) was created in the last 3 days: "No LinkedIn post in [N] days. Drop a thought or paste a news link into Drop_Here/ today."
4. If Needs_Action count > 0 but scheduler hasn't run today: "[N] files are queued but the AI hasn't processed them yet. Trigger a manual run or wait for the next scheduled session."
5. If all clear: "System is healthy and queue is clear. Good day to create something."

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

### 3. Update Dashboard.md

After saving the briefing file, update `/Dashboard.md`:
- Change `last_updated` to the current ISO 8601 timestamp
- Add to Today's Activity (at the top of the list):
  `[HH:MM] Morning briefing generated for [date] — [N] items pending review`

Do **not** rebuild the entire dashboard — just update these two fields. The `update_dashboard` skill handles full rebuilds; this skill only adds its own activity line.

### 4. Stop

Do not process any other files. Do not run any other skills. Do not move files in `/Needs_Action/`. This skill's job ends when the briefing is saved and the dashboard is updated.

---

## Quality Checks

Verify before saving:

- [ ] All data was collected before writing began — no partial drafts
- [ ] Pending_Approval count in the YAML-free header line matches the actual list below it
- [ ] AI Queue count matches actual file count in /Needs_Action/
- [ ] Finance pulse is from the most recent entry (not a stale one)
- [ ] Finance savings rate is taken from YAML field, not recalculated (to avoid drift from the original briefing)
- [ ] "Completed Yesterday" only includes files actually modified in last 24 hours — not all-time Done files
- [ ] System Alerts only shows entries with level "error" or "warning" from last 24 hours
- [ ] Today's Suggestion is exactly ONE item — the most relevant one
- [ ] The suggestion uses real numbers from the data (e.g., actual number of days since last post)
- [ ] Briefing reads in under 60 seconds — if a section is getting long, trim it
- [ ] YAML front-matter is complete and valid
- [ ] Saved as `MORNING_BRIEFING_[YYYYMMDD].md` in `/Pending_Approval/`
- [ ] Dashboard.md `last_updated` and Today's Activity updated
- [ ] No other files were moved or modified

---

## Example Output

**For Reference Only — Do NOT Copy**

```markdown
---
type: approval_request
action: morning_briefing
created: 2026-03-02T07:00:00Z
status: pending
---

# ☀️ Morning Briefing — Monday, 02 March 2026
*Generated at 7:00 AM by your AI Employee*

## 🔔 Needs Your Attention (4 items)

- 💰 FINANCE_BRIEFING_20260301.md — Weekly finance briefing (week of 2026-03-01). Move to /Approved/ to log it.
- 📝 LINKEDIN_POST_ai-agents-framework-vs-scratch_20260221.md — LinkedIn post draft. Review and approve or reject (⚠️ expired 2026-02-22 — still usable if topic is still relevant).
- 📧 GMAIL_REPLY_google-2fa_20260222.md — Gmail reply to Google 2FA confirmation. Low priority — archive if already handled.
- 📧 GMAIL_REPLY_deeplearning-ai-batch_20260222.md — Gmail reply to DeepLearning.AI newsletter. Low priority — archive.

## 🤖 AI Queue (2 items)

2 file(s) waiting to be processed. Claude will handle these in the next scheduled run.

## 💰 Finance Pulse

- Last entry: week of 2026-03-01
- Savings rate: 58.0%
- Key reminder: Move PKR 3,000 out of reach now — the savings number only means something if you put it somewhere separate.

## ✅ Completed Yesterday

- LINKEDIN_POST_silver-tier-achievement_20260301.md — LinkedIn post approved and marked complete.

## ⚠️ System Alerts

✅ All systems running normally.

## 💡 Today's Suggestion

No LinkedIn post in 8 days. Drop a thought or paste a news link into Drop_Here/ today.

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

## Implementation Notes

- This skill is executed by Claude Code within a reasoning session — either by the scheduler or the reasoning_loop
- **Read-only guarantee:** This skill must never modify files in `/Needs_Action/`, `/Finance_History/`, `/Plans/`, or `/Done/`. It creates one file in `/Pending_Approval/` and updates `Dashboard.md` — nothing else
- **Manual trigger routing:** When `morning_briefing_now.md` is dropped in `Drop_Here/`, the filesystem_watcher should create an action file with `type: morning_briefing_trigger`. The reasoning_loop's skill assignment table needs a corresponding entry: `morning_briefing_trigger` → `morning_briefing`. (This requires a small update to reasoning_loop.md when implementing manual triggers.)
- **Scheduler trigger:** When called by the scheduler, it is invoked directly by name — no action file is needed
- **Graceful degradation:** If any input source is missing (no Logs folder, no Finance_History, empty Done folder), the skill should still produce a complete briefing — just with "No data available" for that section. Never error out on a missing folder
- **Duplicate prevention:** If a `MORNING_BRIEFING_[YYYYMMDD].md` already exists in `/Pending_Approval/` for today's date, skip creating a new one and log a warning instead. Do not overwrite an existing briefing that Taha may have already started reviewing
- **Expiry:** Morning briefings do not expire in the traditional sense — they are informational snapshots. However, briefings older than 48 hours in `/Pending_Approval/` should be flagged by the reasoning_loop's stale approval detection
- If `/Logs/` does not exist yet (early Bronze tier), skip the System Alerts section and note "Log files not yet configured"
- The Today's Suggestion logic uses a priority order — only the first matching condition fires. Do not stack multiple suggestions
- Keep the briefing tight: if Pending_Approval has 15 files, do not list all 15 in full detail — group low-priority items ("8 low-priority Gmail replies — archive if already handled") to keep the briefing scannable

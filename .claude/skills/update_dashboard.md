# Skill: update_dashboard

**Type:** System Monitoring & Dashboard Maintenance Skill
**Triggers:** After any skill completes, after file state changes, on session start, or when status check requested
**Output:** Updated `/Dashboard.md` in Obsidian vault

---

## Description

This skill maintains `/Dashboard.md` as the central status dashboard for the AI Employee system. It scans all vault folders, counts tasks in each pipeline stage, checks watcher health, reads recent logs, and generates a clean, scannable dashboard that gives Taha a complete picture of system status in under 30 seconds.

This skill runs frequently and must be fast — it just counts files and reads the latest log, no heavy processing.

---

## When to Trigger

- **After ANY skill completes** (draft_linkedin_post, classify_message, or any future skill)
- **After a file is moved** to `/Approved/`, `/Rejected/`, or `/Done/`
- **When Claude Code is asked to check system status** (user asks "status?", "what's pending?", etc.)
- **At the start of any new Claude Code session** to refresh the dashboard with current state
- **Proactively after making any vault changes** (moving files, creating approval requests, etc.)

---

## Input Requirements

- Current `/Dashboard.md` file (to be replaced)
- Contents of all vault state folders:
  - `/Needs_Action/`
  - `/Plans/`
  - `/Pending_Approval/`
  - `/Approved/`
  - `/Rejected/`
  - `/Done/`
  - `/Logs/`
- Most recent log file from `/Logs/` (today's `YYYY-MM-DD.json`)
- Optional: Weekly log files for calculating weekly stats

---

## Step-by-Step Process

### 1. Scan All Vault Folders

Count files in each state folder:
- `/Needs_Action/` → Number of unprocessed tasks waiting for skill execution
- `/Plans/` → Number of tasks currently being processed or with reasoning logs
- `/Pending_Approval/` → Number of drafts awaiting Taha's review
- `/Approved/` → Number of approved actions not yet executed
- `/Done/` → Total completed (all time) + completed today (modified today)
- `/Rejected/` → Total rejected (all time)

**Important:** Actually count the `.md` files in each folder. Do NOT guess or use cached numbers.

### 2. Determine System Status for Each Watcher

Check the status of each watcher component:

**Status Indicators:**
- 🟢 **Active** — Watcher logged activity in the last 24 hours
- 🟡 **Idle** — Watcher is running but no activity in 24+ hours (expected if no new inputs)
- 🔴 **Error** — Watcher has error entries in recent logs
- ⚪ **Not Configured** — Watcher hasn't been set up yet or never ran

**Check Logic:**
1. Look for today's log file: `/Logs/YYYY-MM-DD.json`
2. If file exists, check for entries from each watcher:
   - `file_drop_watcher`
   - `gmail_watcher`
   - `whatsapp_watcher`
   - `news_watcher`
   - `orchestrator`
3. For each watcher:
   - If logged in last 24 hours → 🟢 Active
   - If logged but 24+ hours ago → 🟡 Idle
   - If has error-level log entries → 🔴 Error
   - If never logged → ⚪ Not Configured

**Last Active Timestamp:**
- If watcher has activity: Show the most recent timestamp
- If watcher never ran: Show "Never"

### 3. Read Today's Activity Log

Read `/Logs/YYYY-MM-DD.json` (today's date) to extract recent activity entries.

**Expected log format:**
```json
{
  "date": "2026-02-16",
  "entries": [
    {
      "timestamp": "2026-02-16T10:30:00Z",
      "component": "gmail_watcher",
      "level": "info",
      "message": "Detected new email from Dr. Ahmed Khan",
      "action": "created_action_file"
    },
    ...
  ]
}
```

Extract the most recent **10 activity entries** for the dashboard's "Today's Activity" section.

### 4. Calculate Weekly Stats

Scan log files from the current week (Monday to Sunday) in `/Logs/`:
- Count entries where `action` = `"drafted_linkedin_post"`
- Count entries where `action` = `"classified_message"`
- Count entries where `action` = `"approved_action"`
- Count entries where `action` = `"rejected_action"`

**Current Week:** Determine the Monday-Sunday range for the current week based on today's date.

### 5. Track LinkedIn Posts This Week

Scan `/Pending_Approval/`, `/Approved/`, and `/Done/` for files matching `LINKEDIN_POST_*.md` created this week.

For each LinkedIn post file:
- Extract date from filename
- Extract topic from YAML front-matter
- Determine status based on folder:
  - In `/Pending_Approval/` → "Pending"
  - In `/Approved/` → "Approved"
  - In `/Done/` → "Posted"
  - In `/Rejected/` → "Rejected"

### 6. List Pending Reviews

List all files in `/Pending_Approval/` with:
- Filename
- Type (extracted from YAML front-matter `action` field)
- Topic/subject (extracted from YAML front-matter)

Sort by creation time (newest first).

### 7. Detect Anomalies

Check for potential issues and add alerts if needed:

**Alert Conditions:**
- Files stuck in `/Needs_Action/` for over 24 hours → "X files stuck in /Needs_Action/ for over 24 hours"
- Any watcher with 🔴 Error status → "Watcher [name] has errors — check /Logs/"
- Any watcher 🟡 Idle for over 48 hours → "Watcher [name] has not logged activity in 48+ hours"
- More than 10 files in `/Pending_Approval/` → "X items awaiting review — review queue is getting long"
- Files in `/Approved/` older than 48 hours → "X approved actions have not been executed in 48+ hours"

### 8. Build the Dashboard

Create the updated `/Dashboard.md` with this EXACT structure:

```markdown
---
last_updated: [ISO 8601 timestamp]
version: "1.0"
---

# 📊 AI Employee Dashboard

[If alerts exist, add this section:]
## ⚠️ Alerts
- [Alert description]
- [Alert description]

## System Status

| Component | Status | Last Active |
|-----------|--------|-------------|
| File Drop Watcher | [🟢/🟡/🔴/⚪] | [timestamp or "Never"] |
| Gmail Watcher | [🟢/🟡/🔴/⚪] | [timestamp or "Never"] |
| WhatsApp Watcher | [🟢/🟡/🔴/⚪] | [timestamp or "Never"] |
| News Watcher | [🟢/🟡/🔴/⚪] | [timestamp or "Never"] |
| Orchestrator | [🟢/🟡/🔴/⚪] | [timestamp or "Never"] |

## Pipeline Overview

| Stage | Count | Folder |
|-------|-------|--------|
| Unprocessed Tasks | [n] | /Needs_Action/ |
| Being Processed | [n] | /Plans/ |
| Awaiting Taha's Review | [n] | /Pending_Approval/ |
| Approved (pending execution) | [n] | /Approved/ |
| Completed Today | [n] | /Done/ |
| Rejected | [n] | /Rejected/ |

## Today's Activity

[List most recent 10 actions from today, newest first]
- [HH:MM] [action description]
- [HH:MM] [action description]

[If no activity today: "_No activity yet today._"]

## LinkedIn Posts This Week

| Date | Topic | Status |
|------|-------|--------|
| [date] | [topic from approval file] | [Pending/Approved/Posted/Rejected] |

[If none: "_No posts this week yet._"]

## Pending Reviews

[List each file in /Pending_Approval/ with its type and topic]
- 📝 [filename] — [type]: [topic/subject]

[If none: "_Nothing awaiting review. All clear!_"]

## Weekly Stats

- Posts Drafted: [count]
- Messages Processed: [count]
- Actions Approved: [count]
- Actions Rejected: [count]

---
*Dashboard auto-updated by AI Employee at [timestamp]*
```

### 9. Write the Dashboard

Write the newly built dashboard to `/Dashboard.md`, completely replacing the previous version.

**Important:** Use the Write tool to overwrite the file. Do NOT append — replace the entire file.

### 10. Log the Update

Add an entry to today's log file (`/Logs/YYYY-MM-DD.json`):
```json
{
  "timestamp": "[ISO 8601 timestamp]",
  "component": "update_dashboard",
  "level": "info",
  "message": "Dashboard updated successfully",
  "action": "updated_dashboard"
}
```

---

## Quality Checks

Verify before saving:

- [ ] All folder counts are accurate (actually counted, not guessed)
- [ ] Timestamps are current and in ISO 8601 format
- [ ] Watcher statuses reflect real log data
- [ ] No stale data from previous dashboard versions
- [ ] LinkedIn post tracking matches actual files in vault
- [ ] Weekly stats are calculated from actual log files
- [ ] Today's activity shows real log entries (newest first)
- [ ] Pending reviews list is complete and accurate
- [ ] Alerts section only appears if there are actual alerts
- [ ] If a folder doesn't exist or is empty, count shows 0 (no errors)
- [ ] Dashboard is clean, scannable, and gives complete status picture
- [ ] All markdown formatting is correct (tables, lists, etc.)

---

## Example Output

**For Reference Only — Do NOT Copy**

```markdown
---
last_updated: 2026-02-16T15:30:00Z
version: "1.0"
---

# 📊 AI Employee Dashboard

## ⚠️ Alerts
- 2 files stuck in /Needs_Action/ for over 24 hours
- WhatsApp Watcher has not logged activity in 48+ hours

## System Status

| Component | Status | Last Active |
|-----------|--------|-------------|
| File Drop Watcher | 🟢 | 2026-02-16T14:00:00Z |
| Gmail Watcher | 🟢 | 2026-02-16T15:15:00Z |
| WhatsApp Watcher | 🟡 | 2026-02-14T10:30:00Z |
| News Watcher | 🟢 | 2026-02-16T06:00:00Z |
| Orchestrator | 🟢 | 2026-02-16T15:20:00Z |

## Pipeline Overview

| Stage | Count | Folder |
|-------|-------|--------|
| Unprocessed Tasks | 2 | /Needs_Action/ |
| Being Processed | 1 | /Plans/ |
| Awaiting Taha's Review | 3 | /Pending_Approval/ |
| Approved (pending execution) | 1 | /Approved/ |
| Completed Today | 4 | /Done/ |
| Rejected | 0 | /Rejected/ |

## Today's Activity

- 15:20 Orchestrator processed 1 task from /Needs_Action/
- 15:15 Gmail Watcher detected new email from Dr. Ahmed Khan
- 14:30 Drafted Gmail reply to Dr. Ahmed Khan (priority: normal)
- 14:00 File Drop Watcher detected new thought drop: "AI Employee Progress"
- 13:45 Drafted LinkedIn post: AI Employee Hackathon Start
- 10:30 Taha approved LinkedIn post: Building with Folder-Based State
- 10:00 Posted to LinkedIn: Building with Folder-Based State
- 08:15 News Watcher found 3 new AI articles
- 08:00 Classified tech news article (priority: normal)
- 06:30 Drafted LinkedIn post: Claude 4.5 Sonnet Release Thoughts

## LinkedIn Posts This Week

| Date | Topic | Status |
|------|-------|--------|
| 2026-02-16 | AI Employee Hackathon Start | Pending |
| 2026-02-16 | Claude 4.5 Sonnet Release Thoughts | Approved |
| 2026-02-15 | Building with Folder-Based State | Posted |
| 2026-02-14 | Learning Agentic AI at GIAIC | Posted |

## Pending Reviews

- 📝 LINKEDIN_POST_ai-employee-hackathon_20260216.md — linkedin_post: AI Employee Hackathon Start
- 📝 GMAIL_REPLY_dr-ahmed_20260216.md — send_gmail: Guest Lecture Confirmation
- 📝 WHATSAPP_REPLY_hamza_20260216.md — send_whatsapp: Class Confirmation

## Weekly Stats

- Posts Drafted: 7
- Messages Processed: 12
- Actions Approved: 9
- Actions Rejected: 1

---
*Dashboard auto-updated by AI Employee at 2026-02-16T15:30:00Z*
```

---

## Implementation Notes

- This skill is executed by Claude Code within a reasoning session
- Must be FAST — only count files and read logs, no heavy processing
- Runs frequently (after every skill, after file moves, on session start)
- The dashboard is the primary UI for Taha to monitor his AI Employee
- All counts must be accurate — reading actual folders, not cached data
- If folders don't exist yet (early Bronze tier), show 0 counts, not errors
- Alerts should be helpful but not alarmist — only flag real issues
- Keep the dashboard scannable — Taha should understand system status in 30 seconds
- The "Today's Activity" section is critical — Taha checks this every morning
- Weekly stats help track productivity and identify patterns
- If log files are missing or malformed, handle gracefully (show "No activity" instead of erroring)

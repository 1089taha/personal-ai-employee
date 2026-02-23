# Skill: reasoning_loop

**Type:** Master Orchestration Skill
**Triggers:** Session start, scheduler invocation, or manual "process the vault" command
**Output:** Plan file in `/Plans/`, updated approval files in `/Pending_Approval/`, refreshed `/Dashboard.md`

---

## Description

This is the **executive function** of the AI Employee. Every other skill is a specialist — this skill is the manager that surveys all pending work, thinks before acting, and delegates to the right specialist in the right order.

Without this skill, Taha must manually tell Claude which file to process. With this skill, Claude behaves like a real employee who checks their desk every morning, builds a work plan, and handles everything systematically — without being told what to do next.

This skill does not generate content itself. It reads the vault state, creates an explicit execution plan, calls the appropriate skills in priority order, handles errors without stopping, and then wraps up by refreshing the dashboard and logging everything.

**Core guarantee:** No task is ever skipped. No action is ever taken without being recorded in a Plan.

---

## When to Trigger

- **Session start:** When Claude Code is invoked on this project with no specific task given
- **Scheduler invocation:** When an automated script calls Claude Code with `--task "process the vault"`
- **Manual command:** When Taha says any of:
  - "process the vault"
  - "check for work"
  - "what needs to be done?"
  - "run the loop"
  - "what's pending?"
  - "start your shift"

---

## Input Requirements

- All `.md` files in `/Needs_Action/` (unprocessed incoming tasks)
- All `.md` files in `/Pending_Approval/` (to check for stale/expired items)
- All `.md` files in `/Approved/` (to flag if not empty — orchestrator may have missed something)
- `/Company_Handbook.md` (behaviour rules, tone, identity)
- `/Dashboard.md` (current system state snapshot)
- All skill files in `.claude/skills/` (to know what actions are available)
- Today's log file `/Logs/YYYY-MM-DD.json` (if it exists — check before reading)

---

## Step-by-Step Process

---

### PHASE 1 — SURVEY: Understand the current state before touching anything

**1.1 Read Dashboard.md**

Read the current `/Dashboard.md` to get a quick snapshot of the system before scanning folders directly. Note the `last_updated` timestamp — if it's more than 2 hours old, the dashboard is stale and will need refreshing.

**1.2 Read Company_Handbook.md**

Read `/Company_Handbook.md` in full. This must be done before processing ANY task. The handbook contains Taha's identity, tone rules, content pillars, and behaviour guidelines. Even if you read it in a previous session — always re-read it. Rules may have been updated.

**1.3 Scan all vault folders**

Count `.md` files in each folder by listing them:

| Folder | Purpose |
|--------|---------|
| `/Needs_Action/` | Unprocessed inputs from watchers — these are the work queue |
| `/Pending_Approval/` | Drafts waiting for Taha to approve or reject |
| `/Approved/` | Approved actions waiting to be executed — should be empty |
| `/Plans/` | Reasoning logs and processed task archives |
| `/Done/` | Completed and executed tasks |
| `/Rejected/` | Rejected drafts (archive) |

For each file found, note its name and — if it has YAML front-matter — read just the front-matter block to extract `type`, `created`, and `expires` fields without reading the full file. This keeps the survey phase fast.

**1.4 Check for expired approvals in /Pending_Approval/**

For each file in `/Pending_Approval/`, compare its `expires` timestamp to the current time.

- If `expires` is in the past → this approval request has expired. Mark it (see Phase 4, Stale Approval Handling).
- If `expires` is still in the future → this is active, no action needed.
- If `expires` field is missing → treat as expired (defensive default).

**1.5 Check /Approved/ for unexecuted actions**

If any files exist in `/Approved/`, this means an action was approved but the execution step (posting to LinkedIn, sending email, etc.) never happened. Log this as an alert. Do NOT automatically execute — just flag it.

**1.6 Early exit if nothing to do**

If ALL of these are true:
- `/Needs_Action/` is empty (no files)
- No expired approvals exist in `/Pending_Approval/`
- No anomalies were detected

Then:
1. Log "System idle — no pending tasks. Survey complete." to today's log file
2. Run the `update_dashboard` skill to refresh the dashboard
3. **Stop. Do not create a Plan file for idle surveys.** Idle state is not worth the noise.

If there IS work to do, continue to Phase 2.

---

### PHASE 2 — PLAN: Think before doing

**This phase must complete before a single file is processed.**

**2.1 Create a Plan file**

Create a new file in `/Plans/` before executing any tasks. The Plan is an audit trail — it records what Claude intended to do, why, and what actually happened. Taha should be able to read this file and fully understand every decision.

**File name format:** `PLAN_[YYYYMMDD]_[HHMM].md`
Example: `PLAN_20260221_0930.md`

**Plan file format:**

```markdown
---
type: reasoning_plan
created: [ISO 8601 timestamp]
status: executing
tasks_found: [number of files in /Needs_Action/]
alerts_found: [number of alerts detected in survey]
---

# Reasoning Loop — Execution Plan

**Created:** [ISO 8601 timestamp]
**Vault scanned at:** [ISO 8601 timestamp]

---

## Vault State Survey

| Folder | Count | Notes |
|--------|-------|-------|
| /Needs_Action/ | [n] | [e.g., "3 tasks pending"] |
| /Pending_Approval/ | [n] | [e.g., "2 active, 1 expired"] |
| /Approved/ | [n] | [e.g., "Empty — expected" or "⚠️ 1 unexecuted action"] |
| /Plans/ | [n] | [e.g., "5 previous plans"] |
| /Done/ | [n] | — |
| /Rejected/ | [n] | — |

---

## Alerts

[One of these:]
- None — system healthy
[Or a list of issues found:]
- ⚠️ Expired approval: [filename] (expired [timestamp])
- ⚠️ Unexecuted approved action: [filename] sitting in /Approved/ since [created timestamp]
- ⚠️ Stale task: [filename] has been in /Needs_Action/ for over 24 hours

---

## Execution Plan

| # | File | Type | Skill | Priority | Status |
|---|------|------|-------|----------|--------|
| 1 | [filename] | [type from YAML] | [skill name] | [urgent/normal/low] | ⏳ Pending |
| 2 | [filename] | [type from YAML] | [skill name] | [urgent/normal/low] | ⏳ Pending |

---

## Execution Log

_Tasks will be recorded here as they complete._
```

**2.2 Priority assignment rules**

Assign a priority to every task in `/Needs_Action/` using these rules:

| Type | Default Priority | Override to Urgent if... |
|------|-----------------|--------------------------|
| `email` | normal | Subject or body contains: "urgent", "ASAP", "deadline", "today", "final notice", "immediately" |
| `whatsapp` | normal | Message contains: time-sensitive question, deadline, or sender's tone suggests urgency |
| `tech_news` | normal | — (news is never urgent; it can wait) |
| `thought_drop` | low | — (Taha's own notes; he knows when he dropped them) |

When priority is ambiguous, **err toward urgent** rather than normal. Missing an urgent task is worse than over-processing a normal one.

**2.3 Sort by priority**

Order the execution plan: `urgent` → `normal` → `low`

Within the same priority level, sort by `created` timestamp, oldest first (FIFO — first in, first out).

**2.4 Skill assignment**

Assign the correct skill to each task:

| Task Type | Skill to Use |
|-----------|-------------|
| `thought_drop` | `draft_linkedin_post` |
| `tech_news` | `draft_linkedin_post` |
| `email` | `classify_message` |
| `whatsapp` | `classify_message` |
| unknown type | Do not process — flag as error in Alerts section |

If a file has no YAML front-matter at all, attempt to infer the type from the filename. If the type still cannot be determined, move the file to `/Plans/` with a `UNCLASSIFIED_` prefix and log the error. Never delete or ignore an unclassified file.

---

### PHASE 3 — EXECUTE: Process each task in order

For each task in the execution plan (strictly in priority order):

**3.1 Load the skill specification**

Read the relevant skill file from `.claude/skills/` before executing. Do not rely on memory — always re-read the skill spec to ensure you're following the current version of the rules.

**3.2 Execute the skill fully**

Follow the skill's Step-by-Step Process exactly. This means:
- Reading the input file from `/Needs_Action/`
- Generating the correct output
- Creating the approval request file in `/Pending_Approval/`
- Moving the processed input from `/Needs_Action/` to `/Plans/`

**3.3 Update the Plan file after each task**

After each task completes (or fails), update the Plan file's Execution Log and the Execution Plan table:

On success, update the task row to:
```
| 1 | [filename] | thought_drop | draft_linkedin_post | low | ✅ Done — created LINKEDIN_POST_xyz_20260221.md |
```

On failure, update the task row to:
```
| 2 | [filename] | email | classify_message | urgent | ❌ Error — [brief error description] |
```

**3.4 Error handling — never stop the loop**

If a skill fails for any reason (unreadable file, missing field, Claude cannot determine the right action):

1. Record the error in the Plan file's Execution Log with enough detail to debug:
   ```
   [timestamp] ERROR processing [filename]: [what went wrong]. File left in /Needs_Action/.
   ```
2. Leave the failed file in `/Needs_Action/` — do NOT move it to `/Plans/`.
3. Continue to the next task. One failure must never block all other work.
4. After all tasks are processed, the error will appear in the Plan file's summary. Taha will see it on Dashboard.

**3.5 One task at a time**

Never process two tasks in parallel. Complete each task fully before moving to the next. This keeps the audit trail clean and prevents overlapping file operations.

---

### PHASE 4 — STALE APPROVAL HANDLING

This runs in parallel with Phase 3 (after the plan is created, handle stale approvals as a separate set of actions).

For each expired approval found in `/Pending_Approval/`:

**4.1 Mark the file as expired**

Read the file, then edit it to add a warning banner as the very first line (before the YAML front-matter block):

```
> ⚠️ EXPIRED — This approval request expired on [expiry timestamp] and was not reviewed in time.
```

**4.2 Update the file's YAML status**

Change the `status` field in the YAML front-matter from `pending` to `expired`.

**4.3 Do NOT auto-reject or auto-move**

Do NOT move the file to `/Rejected/`. Taha still needs to see it and decide. The mark just ensures he knows it's stale when he opens it. He may still want to use the draft — just with updated timing.

**4.4 Log the expiry**

Add an entry to today's log file:
```json
{
  "timestamp": "[ISO 8601 timestamp]",
  "component": "reasoning_loop",
  "level": "warning",
  "message": "Approval request expired without review: [filename]",
  "action": "marked_expired"
}
```

---

### PHASE 5 — WRAP-UP: Close the loop cleanly

**5.1 Finalize the Plan file**

Update the Plan file's front-matter:
- Change `status: executing` to `status: completed`
- Add `completed:` with the ISO 8601 completion timestamp

Add a final summary section at the bottom of the Plan file:

```markdown
---

## Summary

**Completed:** [ISO 8601 timestamp]
**Duration:** [start to finish, e.g., "approx. 4 minutes"]

| Metric | Count |
|--------|-------|
| Tasks found in /Needs_Action/ | [n] |
| Tasks processed successfully | [n] |
| Tasks failed (left in /Needs_Action/) | [n] |
| Approval files created | [n] |
| Expired approvals marked | [n] |
| Alerts raised | [n] |

[If there were errors:]
### Errors Requiring Attention
- [filename]: [error description]
- [filename]: [error description]

[If no errors:]
_No errors. System healthy._
```

**5.2 Run the update_dashboard skill**

Read and execute the `update_dashboard` skill fully. This refreshes `/Dashboard.md` with the accurate post-execution state of all folders. The dashboard must reflect reality, not predictions.

**5.3 Log session completion**

Add a final entry to today's log file (`/Logs/YYYY-MM-DD.json`):

```json
{
  "timestamp": "[ISO 8601 timestamp]",
  "component": "reasoning_loop",
  "level": "info",
  "message": "Reasoning loop completed. Processed [n] tasks, created [n] approvals, [n] errors.",
  "action": "loop_completed",
  "plan_file": "[Plan filename]",
  "tasks_processed": [n],
  "approvals_created": [n],
  "errors": [n]
}
```

---

## Quality Checks

Verify at each phase before proceeding:

**Survey Phase:**
- [ ] Company_Handbook.md was read before any task processing began
- [ ] All vault folders were actually listed (not guessed from dashboard)
- [ ] Expiry timestamps were compared to the current time (not the dashboard's last_updated time)
- [ ] Early exit logic was checked — if nothing to do, no Plan file was created

**Plan Phase:**
- [ ] Plan file was created BEFORE any task was processed
- [ ] Every file in /Needs_Action/ is accounted for in the Execution Plan — no file is missing
- [ ] Priority assignment follows the defined rules
- [ ] Execution plan is sorted: urgent → normal → low
- [ ] Skill assignment matches the task type correctly
- [ ] Unknown types are flagged in Alerts, not silently skipped

**Execute Phase:**
- [ ] Skill spec was re-read from file before executing (not from memory)
- [ ] Each task was processed completely before moving to the next
- [ ] Plan file was updated after every task (success or failure)
- [ ] Failed tasks remain in /Needs_Action/ (not moved or deleted)
- [ ] No task was silently skipped — every file has a status in the Plan

**Stale Approval Phase:**
- [ ] All expired approvals have the ⚠️ EXPIRED banner added
- [ ] Expired files were NOT moved — only marked
- [ ] Expiry event was logged to today's log file

**Wrap-Up Phase:**
- [ ] Plan file status changed from "executing" to "completed"
- [ ] Summary section is accurate (counts match actual events)
- [ ] update_dashboard skill was executed and Dashboard.md reflects current state
- [ ] Session completion was logged to /Logs/YYYY-MM-DD.json
- [ ] No files were left in an intermediate/inconsistent state

---

## Example Output

**For Reference Only — Do NOT Copy**

### Example Plan File: `PLAN_20260221_0930.md`

```markdown
---
type: reasoning_plan
created: 2026-02-21T09:30:00Z
status: completed
completed: 2026-02-21T09:37:00Z
tasks_found: 3
alerts_found: 1
---

# Reasoning Loop — Execution Plan

**Created:** 2026-02-21T09:30:00Z
**Vault scanned at:** 2026-02-21T09:30:15Z

---

## Vault State Survey

| Folder | Count | Notes |
|--------|-------|-------|
| /Needs_Action/ | 3 | 3 tasks pending |
| /Pending_Approval/ | 2 | 1 active, 1 expired |
| /Approved/ | 0 | Empty — expected |
| /Plans/ | 4 | Previous plans |
| /Done/ | 11 | — |
| /Rejected/ | 1 | — |

---

## Alerts

- ⚠️ Expired approval: LINKEDIN_POST_ai-agents-future_20260220.md (expired 2026-02-21T09:00:00Z)

---

## Execution Plan

| # | File | Type | Skill | Priority | Status |
|---|------|------|-------|----------|--------|
| 1 | EMAIL_uit-finance-deadline_20260221.md | email | classify_message | urgent | ✅ Done — created GMAIL_REPLY_uit-finance_20260221.md |
| 2 | NEWS_anthropic-mcp-update_20260221.md | tech_news | draft_linkedin_post | normal | ✅ Done — created LINKEDIN_POST_mcp-update_20260221.md |
| 3 | THOUGHT_building-with-files_20260221.md | thought_drop | draft_linkedin_post | low | ✅ Done — created LINKEDIN_POST_building-with-files_20260221.md |

---

## Execution Log

- 09:31:00 Started: EMAIL_uit-finance-deadline_20260221.md (urgent)
- 09:32:45 Completed: Created GMAIL_REPLY_uit-finance_20260221.md in /Pending_Approval/
- 09:33:00 Started: NEWS_anthropic-mcp-update_20260221.md (normal)
- 09:35:10 Completed: Created LINKEDIN_POST_mcp-update_20260221.md in /Pending_Approval/
- 09:35:20 Started: THOUGHT_building-with-files_20260221.md (low)
- 09:36:55 Completed: Created LINKEDIN_POST_building-with-files_20260221.md in /Pending_Approval/
- 09:37:00 Stale approval marked: LINKEDIN_POST_ai-agents-future_20260220.md

---

## Summary

**Completed:** 2026-02-21T09:37:00Z
**Duration:** approx. 7 minutes

| Metric | Count |
|--------|-------|
| Tasks found in /Needs_Action/ | 3 |
| Tasks processed successfully | 3 |
| Tasks failed (left in /Needs_Action/) | 0 |
| Approval files created | 3 |
| Expired approvals marked | 1 |
| Alerts raised | 1 |

_No errors. System healthy._
```

---

## Implementation Notes

- This skill is the entry point for all automated processing. Think of it as `main()`.
- It calls other skills the same way a senior employee delegates work — by reading their documented process and following it.
- The Plan file is the most important output. Even if all tasks succeed, Taha needs this audit trail to trust the system.
- Never skip the plan phase for "just one file." The discipline of always planning first is what makes this feel like a real employee, not a script.
- If the vault is completely empty and nothing has expired, this skill ends in under 30 seconds with just a log entry and a dashboard update. No noise.
- The log file at `/Logs/YYYY-MM-DD.json` is append-only during a session. Multiple entries will accumulate throughout the day as different components run.
- If `/Logs/` does not exist yet (early Bronze tier), create it before writing the first log entry.
- This skill should feel like opening the office in the morning — check the desk, make a plan, get to work, wrap up cleanly, leave a report.

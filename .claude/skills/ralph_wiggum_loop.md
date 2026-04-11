# Skill: ralph_wiggum_loop

**Type:** Error Recovery & Retry Wrapper
**Triggers:** Called by `reasoning_loop` when a skill execution fails or produces invalid output — never called directly by Taha
**Output:** Either a valid skill output (if a retry succeeds) or an `ERROR_` report file in `/Needs_Action/` + a `FAILED_` prefixed original in `/Rejected/`

---

## Description

This skill is the **safety net** under every other skill. When the reasoning loop executes a skill and something goes wrong — no output file, an empty file, missing YAML front-matter, malformed structure — it doesn't just log the error and move on. It calls this skill first, which retries the task up to **3 times** before giving up.

The name is a reminder that this is the "I'm in danger" handler: the moment something unexpected happens, this loop catches it, logs clearly what went wrong, tries again with fresh context, and only escalates to a human-visible error report if all attempts fail.

**Core guarantee:** Every failed task gets at least 3 honest attempts. Every failure is visible in `retry_log.md`. Nothing is silently dropped.

**Constants:**
- `MAX_ATTEMPTS: 3`
- `RETRY_WAIT: 10 seconds` — Claude cannot literally sleep, but every retry log entry must note the attempt number and elapsed time since first failure. This makes the log honest about what happened.

---

## When to Trigger

The `reasoning_loop` skill calls this skill when, after executing any skill:

- **No output file was created** — the skill ran but nothing appeared in `/Pending_Approval/` or `/Plans/`
- **Output file exists but is empty** — zero bytes or fewer than 10 lines
- **Output file is missing YAML front-matter** — file does not begin with `---`
- **Output file is malformed** — has front-matter but fewer than 3 `##` section headings
- **The skill itself threw a hard error** — unreadable source file, missing required field, unhandled exception

**Do NOT trigger this skill when:**
- The failure is clearly due to a **missing API key** — retrying won't fix a missing credential. Go straight to an error report.
- The failure is clearly due to a **missing source file** — if the action file in `/Needs_Action/` doesn't exist or can't be read, there is nothing to retry.
- The file already has a `FAILED_` prefix — it has already been through this loop and permanently failed.
- The file's YAML front-matter `type` is `error_report` — never retry error reports.

When in doubt about whether to retry: if fixing the failure requires something Claude cannot change on its own (missing credentials, missing file, missing skill spec), skip retries. If the failure is something that *might* succeed on a fresh attempt (transient reasoning error, incomplete generation, interrupted output), retry.

---

## Input Requirements

This skill receives the following from `reasoning_loop` — these must all be provided:

| Field | Description |
|-------|-------------|
| `action_file` | Full path to the original file in `/Needs_Action/` that was being processed |
| `skill_name` | The name of the skill that was attempted (e.g., `draft_linkedin_post`) |
| `failure_reason` | Clear description of what went wrong on the first attempt |
| `attempt_number` | Which attempt is starting now. Starts at `1` on the first retry. |

---

## Step-by-Step Process

---

### STEP 1 — Validate Inputs Before Attempting Retry

Before touching any files:

**1.1 Check skip conditions**

If any of these are true, **do not retry** — go directly to Step 5 (error report):

- `skill_name` is unknown or its `.md` file doesn't exist in `.claude/skills/`
- `failure_reason` contains any of: "API key not found", "file not found", "missing credential", "no such file"
- `action_file` has a `FAILED_` prefix
- The YAML `type` field in `action_file` is `error_report`

Log the skip reason to `retry_log.md` and jump to Step 5.

**1.2 Verify the source file is readable**

Read `action_file`. If it cannot be read (doesn't exist, is empty), skip retries and go to Step 5.

---

### STEP 2 — Log the Attempt

Before each retry, append to `D:\obsidian_vault\Logs\retry_log.md`. If the file doesn't exist, create it.

**Append this block:**

```markdown
## Retry Attempt [N] — [ISO 8601 timestamp]

- **File:** [action_file name only, not full path]
- **Skill:** [skill_name]
- **Reason for retry:** [failure_reason]
- **Attempt:** [N] of 3
- **Status:** Retrying...
```

Replace `[N]` with the current `attempt_number`.

---

### STEP 3 — Re-execute the Skill

**3.1 Re-read the skill spec**

Read `.claude/skills/[skill_name].md` in full before executing. Do **not** rely on any memory of what the skill does from the previous attempt. Start completely fresh.

**3.2 Re-read the source action file**

Read the original `action_file` again from disk. Do not reuse any parsed content from the previous attempt.

**3.3 Execute the skill from scratch**

Follow the skill's documented process exactly as if this were the very first attempt. No shortcuts.

---

### STEP 4 — Validate the Output

After the skill executes, check whether the output is valid:

**Valid output requires ALL of the following:**

| Check | Condition |
|-------|-----------|
| File exists | A new file was created in `/Pending_Approval/` or `/Plans/` |
| File is non-empty | The file has more than 10 lines |
| Has front-matter | File content starts with `---` |
| Has structure | File contains at least 3 lines starting with `## ` |

**If output is valid (all checks pass):**

1. Update the `retry_log.md` entry for this attempt — replace `Status: Retrying...` with:
   ```
   - **Status:** ✅ SUCCESS on attempt [N]
   ```
2. Add a summary line below it:
   ```
   - **Output file:** [name of the created file]
   ```
3. Return to `reasoning_loop` with success. The Plan file should be updated as if the task succeeded normally. Note in the Plan's Execution Log that it succeeded on retry attempt [N].

**If output is invalid and `attempt_number` < 3:**

1. Update `retry_log.md`: replace `Status: Retrying...` with:
   ```
   - **Status:** ❌ FAILED — output invalid ([specific check that failed])
   ```
2. Increment `attempt_number`.
3. Go back to **Step 2** with the updated attempt number and a new `failure_reason` describing what was wrong with this attempt's output.

**If output is invalid and `attempt_number` == 3:**

All 3 attempts have failed. Proceed to Step 5.

---

### STEP 5 — Create Error Report (All Attempts Exhausted)

This step runs when either:
- All 3 retry attempts produced invalid output
- A skip condition was detected in Step 1

**5.1 Update retry_log.md with final status**

Append to `retry_log.md`:

```markdown
## ❌ PERMANENT FAILURE — [ISO 8601 timestamp]

- **File:** [action_file name]
- **Skill:** [skill_name]
- **Total attempts:** [N] (including original attempt from reasoning_loop)
- **Final failure reason:** [what went wrong on the last attempt]
- **Action taken:** Error report created. Original file moved to /Rejected/.
```

**5.2 Create the error report file**

Create a new file in `/Needs_Action/` with the name:
`ERROR_[original-stem]_[YYYYMMDD_HHMM].md`

Where `[original-stem]` is the filename of `action_file` without its extension.

Example: if `action_file` was `THOUGHT_my-idea_20260310.md`, the error report is `ERROR_THOUGHT_my-idea_20260310_20260310_0932.md`.

**Error report file content:**

```markdown
---
type: error_report
original_file: [action_file name]
skill_attempted: [skill_name]
attempts: [total number of attempts including the original]
final_failure_reason: [what went wrong on the last attempt]
created: [ISO 8601 timestamp]
status: needs_human_review
---

# ❌ Task Failed After [N] Attempts

## What Was Attempted

- **File:** [action_file name]
- **Skill:** [skill_name]
- **First attempted:** [timestamp of original reasoning_loop attempt]
- **Last attempted:** [timestamp of final retry]

## What Went Wrong

[Attempt 1 — Original]
[failure_reason from the reasoning_loop's initial attempt]

[Attempt 2 — First Retry]
[failure_reason from retry attempt 1]

[Attempt 3 — Second Retry]
[failure_reason from retry attempt 2]

## What You Should Do

- Check if the source file in `/Plans/` has valid content
- Check if the required API or service is available
- Re-drop the original file in `/Drop_Here/` to retry manually
- If the skill itself is broken, check `.claude/skills/[skill_name].md`

## Retry Log

[Paste the relevant section from retry_log.md covering all attempts for this file]
```

**5.3 Move the original file to /Rejected/**

Move `action_file` from `/Needs_Action/` to `D:\obsidian_vault\Rejected\` and add a `FAILED_` prefix to its filename.

Example: `THOUGHT_my-idea_20260310.md` → `FAILED_THOUGHT_my-idea_20260310.md`

This prevents the `reasoning_loop` from attempting to process it again on the next run.

**5.4 Update Dashboard.md Alerts section**

Read `/Dashboard.md` and append to its **Alerts** section:

```
⚠️ Task failed after [N] attempts: `[skill_name]` on `[action_file name]` — see ERROR_[stem] in /Needs_Action/
```

If a Alerts section does not exist in Dashboard.md, add it before the last section.

---

### STEP 6 — Update Dashboard.md System Health

This step always runs at the end, regardless of whether a retry succeeded or failed.

| Outcome | Dashboard update |
|---------|-----------------|
| Retry succeeded (attempt 2 or 3) | Add to **Today's Activity**: "↩️ 1 task recovered via retry ([skill_name] on [file])" |
| Retry succeeded (attempt 1, i.e., second overall try) | Same as above |
| Permanent failure | Already handled in Step 5.4 |
| Skip conditions triggered (no retry attempted) | Add to **Alerts**: "⚠️ Task skipped — non-retryable failure: [failure_reason] ([file])" |

---

## Quality Checks

Run these checks before considering this skill complete:

**Before retrying:**
- [ ] Skip conditions were evaluated — non-retryable failures were not retried
- [ ] The source `action_file` was confirmed readable before attempting
- [ ] `retry_log.md` was updated before each attempt, not after

**During retries:**
- [ ] The skill spec was re-read from disk before each attempt (not from memory)
- [ ] The source action file was re-read from disk before each attempt
- [ ] Attempt number is accurate and increments correctly (1, 2, 3 — never more)

**Output validation:**
- [ ] All 4 output checks were run (file exists, non-empty, has front-matter, has 3+ sections)
- [ ] A partial pass does not count as success — all 4 checks must pass
- [ ] The retry log accurately records which specific check failed, not just "invalid output"

**On permanent failure:**
- [ ] Error report file was created in `/Needs_Action/` with correct naming format
- [ ] Error report has valid YAML front-matter with `type: error_report`
- [ ] Original file was moved to `/Rejected/` with `FAILED_` prefix
- [ ] Original file no longer exists in `/Needs_Action/`
- [ ] Dashboard.md Alerts section was updated
- [ ] `retry_log.md` has the final PERMANENT FAILURE block

**Never:**
- [ ] Confirm: no file with `FAILED_` prefix was retried
- [ ] Confirm: no file with `type: error_report` was retried
- [ ] Confirm: attempt counter never exceeded 3
- [ ] Confirm: `retry_log.md` has an entry for every attempt, including successful ones

---

## Example: Full Failure Scenario

**Situation:** `reasoning_loop` tried to run `draft_linkedin_post` on `THOUGHT_building-agents_20260310.md`. The skill produced a file in `/Pending_Approval/` but it had no YAML front-matter. The reasoning loop calls `ralph_wiggum_loop`.

**retry_log.md after all attempts:**

```markdown
## Retry Attempt 1 — 2026-03-10T09:32:00Z

- **File:** THOUGHT_building-agents_20260310.md
- **Skill:** draft_linkedin_post
- **Reason for retry:** Output file LINKEDIN_POST_building-agents_20260310.md exists but has no YAML front-matter (does not start with ---)
- **Attempt:** 1 of 3
- **Status:** ❌ FAILED — output file created but still missing YAML front-matter

## Retry Attempt 2 — 2026-03-10T09:33:15Z

- **File:** THOUGHT_building-agents_20260310.md
- **Skill:** draft_linkedin_post
- **Reason for retry:** Output file missing YAML front-matter on attempt 1
- **Attempt:** 2 of 3
- **Status:** ❌ FAILED — no output file created at all

## Retry Attempt 3 — 2026-03-10T09:34:30Z

- **File:** THOUGHT_building-agents_20260310.md
- **Skill:** draft_linkedin_post
- **Reason for retry:** No output file created on attempt 2
- **Attempt:** 3 of 3
- **Status:** ❌ FAILED — output file created but has only 1 section heading (minimum is 3)

## ❌ PERMANENT FAILURE — 2026-03-10T09:35:00Z

- **File:** THOUGHT_building-agents_20260310.md
- **Skill:** draft_linkedin_post
- **Total attempts:** 4 (1 original + 3 retries)
- **Final failure reason:** Output file created but has only 1 section heading (minimum is 3)
- **Action taken:** Error report created. Original file moved to /Rejected/.
```

**Result:**
- `ERROR_THOUGHT_building-agents_20260310_20260310_0935.md` created in `/Needs_Action/`
- `FAILED_THOUGHT_building-agents_20260310.md` moved to `/Rejected/`
- Dashboard Alerts updated

---

## Example: Successful Retry

**Situation:** Same scenario, but attempt 2 produces a valid file.

**retry_log.md:**

```markdown
## Retry Attempt 1 — 2026-03-10T09:32:00Z

- **File:** THOUGHT_building-agents_20260310.md
- **Skill:** draft_linkedin_post
- **Reason for retry:** Output file has no YAML front-matter
- **Attempt:** 1 of 3
- **Status:** ❌ FAILED — output file still missing YAML front-matter

## Retry Attempt 2 — 2026-03-10T09:33:15Z

- **File:** THOUGHT_building-agents_20260310.md
- **Skill:** draft_linkedin_post
- **Reason for retry:** Output file missing YAML front-matter on attempt 1
- **Attempt:** 2 of 3
- **Status:** ✅ SUCCESS on attempt 2
- **Output file:** LINKEDIN_POST_building-agents_20260310.md
```

**Result:**
- `reasoning_loop` Plan file updated: task marked ✅ Done (succeeded on retry 2)
- Dashboard Today's Activity: "↩️ 1 task recovered via retry (draft_linkedin_post on THOUGHT_building-agents_20260310.md)"

---

## Implementation Notes

- The name is deliberate. Ralph Wiggum says "I'm in danger" — this skill runs exactly when something is in danger of being silently lost.
- This skill is a **wrapper**, not a standalone processor. It has no business logic of its own. It re-runs the original skill. All content decisions belong to the original skill.
- The `retry_log.md` is separate from the daily `/Logs/YYYY-MM-DD.json`. The retry log is a persistent human-readable record of every failure this system has ever encountered. The daily log is structured JSON for the system. Both get written.
- Attempt numbering: `reasoning_loop` makes attempt 0 (unnumbered). This skill handles attempts 1, 2, and 3. The error report correctly notes "4 total attempts" in this case to be honest with Taha.
- Never clean up old entries from `retry_log.md`. It is append-only. Taha uses it to track recurring failures — if the same file fails 3 times across 3 different sessions, that's a pattern worth seeing.
- If `retry_log.md` doesn't exist when this skill first runs, create it with a header:
  ```markdown
  # Retry Log

  _Append-only record of every task retry and failure. Created automatically._

  ---
  ```
- This skill has no expiry or cron schedule. It runs synchronously inside the reasoning loop and must complete before the loop continues to the next task.

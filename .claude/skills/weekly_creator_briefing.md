# Skill: weekly_creator_briefing

**Type:** Weekly Performance Review & Creator Retrospective Skill
**Triggers:** Scheduler every Sunday at 10:00 AM (after `content_calendar` runs at 9:00 AM), or when a file named `weekly_briefing_now.md` is dropped in `Drop_Here/`
**Output:** One approval request file in `/Pending_Approval/` — a weekly creator performance review with content summary, finance pulse, system health, next week's plan, and 3 specific recommendations

---

## Description

This skill generates a weekly performance review for Taha as a LinkedIn creator. Unlike the morning briefing (which is a daily snapshot of what needs attention), this is a **retrospective**: it looks back at the whole week — what was posted, how the finance numbers look, what the system did — and pairs it with a forward view: next week's content calendar. It ends with 3 concrete, data-grounded recommendations.

The output is Taha's Sunday debrief. He reads it, approves it (to archive it in `/Done/`), and starts the new week with a clear picture.

Target reading time: under 2 minutes.

---

## When to Trigger

- **Scheduler:** Called automatically every Sunday at 10:00 AM — one hour after `content_calendar` runs so the calendar is available to pull into the briefing
- **Manual trigger:** A file named `weekly_briefing_now.md` is dropped in `Drop_Here/`, which the filesystem_watcher converts to a `weekly_briefing_trigger` action file in `/Needs_Action/`

---

## Input Requirements

Read all of these before generating the briefing:

| Source | What to Extract |
|--------|----------------|
| `D:\obsidian_vault\Done\LINKEDIN_POST_*.md` | Posts published this week — read each file's YAML `created` field to filter by current week |
| `D:\obsidian_vault\Pending_Approval\FINANCE_BRIEFING_*.md` | Preferred finance source — YAML has `week`, `savings_rate`, and `## AI Advisor's Take` section |
| `D:\obsidian_vault\Finance_History\FINANCE_*.md` | Fallback finance source — YAML has `week`, `income`, `savings`; calculate `savings_rate` manually |
| `D:\obsidian_vault\Pending_Approval\CONTENT_CALENDAR_*.md` | Next week's plan — look for a file with `week_starting` matching next Monday's date |
| `D:\obsidian_vault\Logs\YYYY-MM-DD.json` | Log files for each day of the current week — count `"level": "error"` entries and total completed actions |
| `D:\obsidian_vault\Pending_Approval\` | Count of all files currently awaiting review |
| `D:\obsidian_vault\Company_Handbook.md` | Taha's goals, content pillars, and financial context — used to calibrate recommendations |

---

## Step-by-Step Process

---

### STEP 1 — Determine the Current Week

Before reading any data, establish the date boundaries:

- **Week ending:** today's date (Sunday)
- **Week starting:** the Monday 6 days ago (today minus 6 days)
- **Next Monday:** tomorrow (today plus 1 day — used to find the content calendar)

All date filtering in the steps below uses these boundaries. "This week" always means Monday through Sunday of the current week.

---

### STEP 2 — Check for Duplicate

Scan `/Pending_Approval/` for any file matching `WEEKLY_BRIEFING_*.md` whose `week_ending` YAML field matches today's date.

**If a briefing for this week already exists:** do NOT create a new one. Log a warning and stop. Do not overwrite a briefing Taha may have already started reviewing.

**If none exists:** proceed.

---

### STEP 3 — Gather All Data

Work through each source methodically. Collect all data before writing a single line of the briefing.

**3.1 — LinkedIn posts this week**

List all `LINKEDIN_POST_*.md` files in `/Done/`. For each file:
1. Read the YAML front-matter to extract `created` (ISO 8601 timestamp) and `topic`
2. Keep only files where `created` falls within the current week (Monday through Sunday)
3. Fall back to file modification time if `created` is missing

Build a list: one line per post, format `[weekday] — [topic]` (e.g., "Thursday — Silver Tier Achievement").

If the file's `topic` YAML field is missing, parse the filename stem (replace hyphens with spaces, strip the date suffix).

**Post count assessment (record for use in Step 4):**
- 0 posts → `⚠️ No posts published this week.`
- 1–2 posts → `Light week — {N} post(s). Aim for 3–4 next week.`
- 3–4 posts → `Solid week — {N} posts published.`
- 5–6 posts → `Strong week — {N} posts published.`

**3.2 — Finance pulse**

Check `/Pending_Approval/` first for any `FINANCE_BRIEFING_*.md` file (sorted newest first). If found:
- Extract `savings_rate` from YAML
- Extract the first actionable sentence from the `## AI Advisor's Take` section
- Note the `week` field to confirm recency

If no pending finance briefing, check `/Finance_History/` for the most recent `FINANCE_*.md` file (sort by filename descending — filenames are `FINANCE_YYYYMMDD.md`). Extract:
- `income`, `savings` from YAML
- Calculate: `savings_rate = round(savings / income * 100, 1)`
- No advisor's take available from this source — note it as "No advisor note — see full briefing"

Record: savings rate percentage and whether the data is from this week or an older entry (note how many weeks ago).

**3.3 — System health**

*Tasks processed this week:*
Read log files for each day of the current week: `/Logs/YYYY-MM-DD.json` for Monday through Sunday. For each file that exists, count entries where `"result": "completed"`. Sum across all days. If no log files exist for this week, record 0.

*Errors this week:*
In the same log files, count entries where `"level": "error"`. Record the count and — if any exist — the component name(s) that errored (e.g., "orchestrator", "gmail_watcher").

*Pending approvals:*
Count all `.md` files currently in `/Pending_Approval/`. This is a simple file count — no need to read them.

**3.4 — Next week's content calendar**

Scan `/Pending_Approval/` for `CONTENT_CALENDAR_*.md` files. Find one whose `week_starting` YAML field matches next Monday's date.

If found: read the 6 day entries (Monday–Saturday) and extract the topic for each day (the text after the `—` in each `## [Day] [Date] — [Topic]` heading).

If not found: record "Content calendar not yet generated for next week."

**3.5 — Read Company Handbook for recommendations context**

Read `Company_Handbook.md` Section 2 (About Taha) and Section 3 (Content Pillars). Use this to calibrate what the 3 recommendations should say — what are the active goals, what are the content priorities.

---

### STEP 4 — Generate the Briefing

With all data collected, write the briefing in one pass.

**File name:** `WEEKLY_BRIEFING_[YYYYMMDD].md` where `[YYYYMMDD]` is today's date

**Save to:** `D:\obsidian_vault\Pending_Approval\`

Use this **exact structure:**

```markdown
---
type: approval_request
action: weekly_briefing
created: [ISO 8601 timestamp]
week_ending: [today's date as YYYY-MM-DD]
status: pending
---

# 📊 Weekly Creator Briefing — Week Ending [DD Month YYYY]

*Generated by your AI Employee on [today's date]. Review and approve to archive.*

---

## 📝 Content This Week

[If 0 posts:]
⚠️ No posts published this week.

[If 1+ posts, list each:]
- **[Weekday]** — [Topic]
- **[Weekday]** — [Topic]

[Assessment line from 3.1 — always present:]
[E.g., "Light week — 1 post. Aim for 3–4 next week." or "Solid week — 3 posts published."]

---

## 💰 Finance Pulse

[If finance data exists:]
**Week of [date]** — Savings rate: **[X]%** ([income earned / savings saved] in PKR)
[Advisor's Take if available:] [one actionable sentence]
[If no advisor's take:] No advisor note — open the full finance briefing for details.

[If finance data is more than 1 week old:]
⚠️ Most recent finance entry is from [N] week(s) ago. Drop a finance file in Drop_Here/ to update.

[If no finance data at all:]
No finance entries found. Drop a `finance_[week].md` file in `Drop_Here/` to start tracking.

---

## 🖥️ System Health

- **Tasks processed this week:** [N]
- **Errors this week:** [N][if N > 0: " — see /Logs/ for details ([component name(s)])"]
- **Pending approvals:** [N] file(s) awaiting review

---

## 📅 Next Week's Plan

[If calendar exists:]
Content calendar generated for week of [Monday date]:
- **Mon** — [topic]
- **Tue** — [topic]
- **Wed** — [topic]
- **Thu** — [topic]
- **Fri** — [topic]
- **Sat** — [topic]
- **Sun** — Rest

[If no calendar:]
Content calendar not yet generated. Check back after 9 AM or drop `content_calendar_now.md` in Drop_Here/.

---

## 💡 3 Recommendations for Next Week

1. **Content:** [data-driven, specific — see recommendation logic in Implementation Notes]
2. **Finance:** [data-driven, specific — based on savings rate and finance data]
3. **System:** [data-driven, specific — based on error count and pending approvals]

---

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

### STEP 5 — Write the 3 Recommendations

Each recommendation must be grounded in the actual data from Step 3. Apply the first matching rule in each category:

**Recommendation 1 — Content:**

| Condition | Recommendation |
|-----------|---------------|
| 0 posts this week | "No posts this week. Before Monday, drop one thought in Drop_Here/ — even a half-formed idea. One post is better than zero." |
| 1–2 posts | "Light week with [N] post(s). Consistency beats perfection — try dropping one thought per day next week even if it's rough." |
| 3+ posts, but one content type is overrepresented | "Good output this week. Next week, balance the mix — [overrepresented type] appeared [N] times. Try [underrepresented type] on [day]." |
| 3+ posts, good variety | "Strong, consistent week. Keep the momentum. [Upcoming calendar day] has a good engagement post — make it specific to something that actually happened to you this week." |

**Recommendation 2 — Finance:**

| Condition | Recommendation |
|-----------|---------------|
| No finance data | "No finance data found. Spending 5 minutes to log this week's numbers in Drop_Here/ is worth doing — you can't improve what you don't track." |
| Finance data > 2 weeks old | "Last finance entry was [N] weeks ago. Drop a quick finance note in Drop_Here/ — even rough numbers are better than none." |
| savings_rate < 50% | "Savings rate is [X]% this week — below the 50% target. Review the biggest expense category and cut one item next week." |
| 50% ≤ savings_rate < 60% | "Savings rate is [X]%. Solid, but there's room to push to 60%. Consider whether [largest discretionary expense] is necessary next week." |
| savings_rate ≥ 60% | "Savings rate is [X]% — good discipline. If the [savings amount] PKR is sitting in your main account, move it out immediately so it doesn't get absorbed into daily spending." |

**Recommendation 3 — System:**

| Condition | Recommendation |
|-----------|---------------|
| Errors > 0 | "The system logged [N] error(s) this week in [component]. Review /Logs/ and fix before they compound — small system issues get harder to debug over time." |
| Pending approvals > 10 | "You have [N] files waiting in /Pending_Approval/. Spend 15 minutes clearing the queue — stale drafts are harder to approve the longer they sit." |
| 5 < pending approvals ≤ 10 | "You have [N] files in /Pending_Approval/. Pick 2–3 to review this week so the queue doesn't grow." |
| Errors == 0 AND pending ≤ 5 | "System is clean — [N] pending, no errors. No maintenance needed this week." |

---

### STEP 6 — Update Dashboard.md

After saving the briefing file, update `D:\obsidian_vault\Dashboard.md`:
- Add to Today's Activity (at the top of the list):
  `[HH:MM] weekly_briefing: Weekly creator briefing generated for week ending [date] — awaiting approval`

Do **not** rebuild the entire dashboard. Only add the activity line.

---

### STEP 7 — Stop

Do not process any other files. Do not run any other skills. Do not move files in `/Needs_Action/`. This skill's job ends when the briefing is saved and the dashboard is updated.

---

## Quality Checks

Verify before saving:

**Data accuracy:**
- [ ] "This week" is correctly defined as Monday through Sunday of the current week — not all-time, not last 7 days from today
- [ ] Post list in Content This Week only includes posts with `created` date within the current week — not all Done/ posts
- [ ] Finance data is from the most recent available entry — not a stale one from months ago
- [ ] System Health counts are from this week's log files, not cumulative totals
- [ ] Pending approvals count reflects the actual current count in `/Pending_Approval/` at time of generation

**Recommendations quality:**
- [ ] Each recommendation references a real number from the data (not generic advice)
- [ ] Content recommendation reflects the actual post count and variety this week
- [ ] Finance recommendation cites the actual savings rate or explains why data is missing
- [ ] System recommendation cites the actual error count and pending count
- [ ] No recommendation contradicts the data (e.g., don't say "great week" if 0 posts were published)

**File integrity:**
- [ ] YAML front-matter is valid — `type: approval_request`, `action: weekly_briefing`, `week_ending` is today's date
- [ ] Filename is `WEEKLY_BRIEFING_[YYYYMMDD].md` (today's date)
- [ ] File is saved in `/Pending_Approval/`
- [ ] "To Approve / To Reject" section is present

**Process:**
- [ ] Duplicate check ran before generating
- [ ] All 5 data sources were read (Done/, Finance, Calendar, Logs, Handbook)
- [ ] Dashboard.md Today's Activity was updated

---

## Example Output

**For Reference Only — Do NOT Copy**

Scenario: Week ending 2026-03-15. 1 post published (Silver Tier Announcement, last week actually — so 0 posts this week). Finance entry from 2026-03-01 (2 weeks old). Calendar generated at 9 AM today. 0 errors. 18 pending approvals.

```markdown
---
type: approval_request
action: weekly_briefing
created: 2026-03-15T10:00:00Z
week_ending: 2026-03-15
status: pending
---

# 📊 Weekly Creator Briefing — Week Ending 15 March 2026

*Generated by your AI Employee on 15 March 2026. Review and approve to archive.*

---

## 📝 Content This Week

⚠️ No posts published this week.

Before Monday, drop one thought in Drop_Here/ — even a half-formed idea. One post is better than zero.

---

## 💰 Finance Pulse

**Week of 2026-03-01** — Savings rate: **58.0%** (PKR 5,800 saved from PKR 10,000 income)
No advisor note — open the full finance briefing for details.

⚠️ Most recent finance entry is from 2 week(s) ago. Drop a finance file in Drop_Here/ to update.

---

## 🖥️ System Health

- **Tasks processed this week:** 0
- **Errors this week:** 0
- **Pending approvals:** 18 file(s) awaiting review

---

## 📅 Next Week's Plan

Content calendar generated for week of 16 March 2026:
- **Mon** — Python async broke my brain
- **Tue** — The student who went from 40 to 70
- **Wed** — Most AI courses are backwards
- **Thu** — How my AI employee decides what to do
- **Fri** — What I got wrong about "learning in public"
- **Sat** — Spec first or code first?
- **Sun** — Rest

---

## 💡 3 Recommendations for Next Week

1. **Content:** No posts this week. Before Monday, drop one thought in Drop_Here/ — even a half-formed idea. One post is better than zero.
2. **Finance:** Last finance entry was 2 weeks ago. Drop a quick finance note in Drop_Here/ — even rough numbers are better than none.
3. **System:** You have 18 files in /Pending_Approval/. Spend 15 minutes clearing the queue — stale drafts are harder to approve the longer they sit.

---

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

## Implementation Notes

- **Relationship to morning_briefing:** Both skills read vault state and produce a briefing, but they serve different purposes. The morning briefing is operational (what needs doing today). The weekly briefing is strategic (how did the week go, what should change). They should never duplicate each other — the weekly briefing does not re-list individual pending files or act as a second morning briefing.
- **Relationship to content_calendar:** The weekly briefing intentionally runs 1 hour after content_calendar (9 AM vs 10 AM) so the calendar is available to pull into the "Next Week's Plan" section. If the calendar hasn't been generated yet (e.g., manual trigger before 9 AM), the briefing should note "not yet generated" rather than erroring.
- **"This week" boundary:** Always use Monday 00:00 through Sunday 23:59 of the current calendar week. Do NOT use "last 7 days" — this matters when the skill is triggered manually mid-week. If triggered on a Wednesday, "this week" is still Monday through today, not the last 7 days.
- **Manual trigger mid-week:** If triggered before Sunday (e.g., Wednesday), the briefing correctly reflects the partial week so far. The content assessment language will naturally reflect a partial week ("2 posts so far this week" vs "light week — 2 posts"). Do not special-case this — just generate with the data available.
- **Finance data fallback chain:**
  1. `Pending_Approval/FINANCE_BRIEFING_*.md` — richest data, includes advisor's take
  2. `Finance_History/FINANCE_*.md` — basic numbers, calculate savings_rate manually
  3. Neither found → note the gap and recommend logging
- **Log file enumeration:** To find this week's log files, enumerate the 7 dates from Monday to Sunday. For each date, check if `/Logs/YYYY-MM-DD.json` exists. If a day's log file is missing, that day simply had 0 logged activity — do not treat this as an error.
- **Duplicate prevention:** Check for `WEEKLY_BRIEFING_[today's YYYYMMDD].md` in `/Pending_Approval/` before generating. If found, log a warning and stop.
- **The briefing approves into `/Done/`** when Taha moves it to `/Approved/`. The orchestrator does not need to take any external action for `action: weekly_briefing` — it is informational. The orchestrator should log "Weekly briefing approved for week ending [date]" and move to `/Done/` as normal.
- **Never fabricate performance data.** If there are no posts, say so. If finance data is stale, say so. The value of this briefing is honest signal — a fabricated "3 posts this week" when there were 0 is actively harmful.
- **Graceful degradation:** If a data source is missing (no Logs/ folder, no Finance_History/, empty Done/), produce the briefing with "No data available" for that section. Never error out on a missing folder.
- **NOTE FOR WINDOWS:** When reading files by date in the vault, always check the YAML `created` field first. If using file system timestamps as fallback, use `cmd /c dir [path] /T:W /OD` rather than PowerShell `Get-ChildItem` — PowerShell has encoding issues in this environment.

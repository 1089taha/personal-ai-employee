# Skill: content_calendar

**Type:** Weekly Planning & Content Strategy Skill
**Triggers:** Scheduler every Sunday at 9:00 AM, or when a file named `content_calendar_now.md` is dropped in `Drop_Here/`
**Output:** One approval request file in `/Pending_Approval/` — a 7-day LinkedIn content plan for the coming week

---

## Description

This skill generates a 7-day LinkedIn content calendar for the coming week. It reads what Taha has already posted and drafted (to avoid topic repetition), reviews his content pillars and voice rules from the Company Handbook, and produces one focused post idea per day with a concrete hook, angle, and type.

The output is a **plan, not a set of drafts**. Each day gets one idea with enough detail that Taha (or the draft_linkedin_post skill) can turn it into a real post when that day arrives. The calendar sits in `/Pending_Approval/` for Taha to review, adjust, and approve on Sunday before the week starts.

Target review time: under 3 minutes.

---

## When to Trigger

- **Scheduler:** Called automatically every Sunday at 9:00 AM
- **Manual trigger:** A file named `content_calendar_now.md` is dropped in `Drop_Here/`, which the filesystem_watcher converts to a `content_calendar_trigger` action file in `/Needs_Action/`

---

## Input Requirements

Read all of these before generating the calendar:

| Source | What to Extract |
|--------|----------------|
| `D:\obsidian_vault\Company_Handbook.md` | Taha's content pillars, voice rules, banned phrases, topics NOT allowed |
| `D:\obsidian_vault\Done\LINKEDIN_POST_*.md` | Topics and angles already published — extract from YAML `topic` field or filename stem |
| `D:\obsidian_vault\Pending_Approval\LINKEDIN_POST_*.md` | Topics already drafted but not yet posted — avoid creating duplicates |
| `D:\obsidian_vault\Pending_Approval\CONTENT_CALENDAR_*.md` | Check if a calendar for this week already exists — if so, skip (see Implementation Notes) |

---

## Step-by-Step Process

---

### STEP 1 — Gather Context

Work through each source methodically. Collect all data before generating a single calendar entry.

**1.1 — Read the Company Handbook**

Read `Company_Handbook.md` in full. Pay particular attention to:
- Content Pillars (Section 3): the 6 topic areas Taha posts about
- Tone & Voice rules: scroll-stopping hooks, banned phrases, character limits
- Topics NOT Allowed: politics, religion, unverified claims, guru-style advice
- Hard Rules: Never fabricate — every topic idea must be grounded in something Taha is genuinely doing or thinking about

**1.2 — Map recent posts (avoid repetition)**

List all `LINKEDIN_POST_*.md` files in `/Done/` (published) and `/Pending_Approval/` (drafted). For each file, extract a one-line topic description:
1. Try the YAML `topic` field first
2. Fall back to parsing the filename stem (replace hyphens with spaces, strip the date suffix)

Build a **used-topics list**: a short list of the topic areas already covered recently (last 2–3 weeks). This is not a blocklist — it's a signal to diversify. If a topic area was covered twice recently, deprioritize it this week.

**1.3 — Determine the week**

Compute the date of **next Monday** from today's date:
- If today is Sunday: next Monday = tomorrow (the skill runs Sunday morning, planning for the week ahead)
- Otherwise: next Monday = the upcoming Monday

---

### STEP 2 — Check for Duplicate

Before generating anything:

Scan `/Pending_Approval/` for any file matching `CONTENT_CALENDAR_*.md` whose `week_starting` YAML field matches next Monday's date.

**If a calendar for this week already exists:** do NOT create a new one. Log a warning and stop. Do not overwrite a calendar Taha may have already reviewed.

**If no calendar exists for this week:** proceed.

---

### STEP 3 — Generate the 7-Day Plan

Using the gathered context, generate one post idea per day following the day-type assignments below. For each day, produce four fields — **Topic**, **Hook**, **Angle**, and **Type**.

**Day-type assignments:**

| Day | Content Type | Primary Pillar |
|-----|-------------|----------------|
| Monday | Technical / Educational | AI & Agentic Development, Python, Data Science |
| Tuesday | Personal story or lesson learned | Learning journey, teaching experiences |
| Wednesday | Opinion on a tech trend | Tech takes, honest perspective from a builder |
| Thursday | Project update or behind-the-scenes | Building in public, what Taha is currently working on |
| Friday | Weekly reflection or achievement | Honest reflection, real numbers, what changed this week |
| Saturday | Engagement post (question, poll idea, debate) | Any pillar — optimise for starting a conversation |
| Sunday | **Rest** | No post recommended |

**Quality bar for each day:**

- **Topic:** Specific enough to write a real post. Not "AI stuff" — "why I rewrote my agent's state machine after it silently ate 3 tasks."
- **Hook:** The exact first line of the post — 1 sentence, scroll-stopping. Must make the reader think "wait, what?" or "that's me." Apply the hook types from Company_Handbook Section 4 (surprising, brutally honest, bold take, specific question).
- **Angle:** What makes Taha's take unique. Not "here's how Python async works" but "here's what Python async broke for me at 2 AM and what I learned from it." Taha is a 20-year-old student building real things — that specificity IS the angle.
- **Type:** One of: Educational / Story / Opinion / Update / Reflection / Engagement

**Deduplication rules:**
- If a topic in the used-topics list closely matches a proposed day's idea, suggest a different angle on the same pillar or a topic from a different pillar
- Prioritize pillars that haven't appeared in recent posts
- Never suggest the exact same hook as a recent post

**Sunday entry:**

```
## Sunday — Rest
No post recommended. Rest, reflect, plan next week.
```

---

### STEP 4 — Save the Calendar

**File name:** `CONTENT_CALENDAR_[YYYYMMDD].md` where `[YYYYMMDD]` is today's date (the generation date, not the Monday date)

**Save to:** `D:\obsidian_vault\Pending_Approval\`

Use this **exact structure:**

```markdown
---
type: approval_request
action: content_calendar
created: [ISO 8601 timestamp]
week_starting: [next Monday's date as YYYY-MM-DD]
status: pending
---

# 📅 Content Calendar — Week of [Monday Date as "DD Month YYYY"]

*Generated by your AI Employee on [generation date]. Review, adjust, and approve by end of Sunday.*

## Monday [DD Month] — [Topic in 4–6 words]
- **Hook:** [exact first line — the scroll-stopper]
- **Angle:** [what makes Taha's take specific and honest]
- **Type:** Educational
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context. The draft_linkedin_post skill handles the rest.

## Tuesday [DD Month] — [Topic in 4–6 words]
- **Hook:** [exact first line]
- **Angle:** [Taha's specific perspective]
- **Type:** Story
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Wednesday [DD Month] — [Topic in 4–6 words]
- **Hook:** [exact first line]
- **Angle:** [Taha's specific perspective]
- **Type:** Opinion
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Thursday [DD Month] — [Topic in 4–6 words]
- **Hook:** [exact first line]
- **Angle:** [Taha's specific perspective]
- **Type:** Update
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Friday [DD Month] — [Topic in 4–6 words]
- **Hook:** [exact first line]
- **Angle:** [Taha's specific perspective]
- **Type:** Reflection
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Saturday [DD Month] — [Topic in 4–6 words]
- **Hook:** [exact first line — frame as a question or debate opener]
- **Angle:** [what conversation this should start]
- **Type:** Engagement
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Sunday [DD Month] — Rest
No post recommended. Rest, reflect, plan next week.

---

## How to Use This Calendar

1. Review each day's idea — adjust the topic or angle if something feels off
2. Approve this file (move to `/Approved/`) to confirm the week's plan
3. Each day, drop a short note in `Drop_Here/` referencing that day's topic (add any new context from your day)
4. The `draft_linkedin_post` skill will turn it into a full post and save it to `/Pending_Approval/`
5. Review and approve each post before it goes live

**You don't have to follow this exactly.** The calendar is a starting point. If something better happens on Wednesday, post about that instead.

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

### STEP 5 — Update Dashboard.md

After saving the calendar file, update `D:\obsidian_vault\Dashboard.md`:
- Add to Today's Activity (at the top of the list):
  `[HH:MM] content_calendar: Weekly content plan generated for week of [Monday date] — awaiting approval`

Do **not** rebuild the entire dashboard. Only add the activity line.

---

### STEP 6 — Stop

Do not process any other files. Do not run any other skills. Do not move files in `/Needs_Action/`. This skill's job ends when the calendar is saved and the dashboard is updated.

---

## Quality Checks

Verify before saving:

**Content quality:**
- [ ] Every day (Mon–Sat) has all four fields: Topic, Hook, Angle, Type
- [ ] Every Hook is a genuine scroll-stopper — not generic, not starting with "I'm" followed by a corporate statement
- [ ] Every Hook follows Company_Handbook voice rules (no banned phrases)
- [ ] Every Angle is specific to Taha's actual situation (student, builder, teacher) — not generic advice
- [ ] No two days have the same topic or the same type of hook
- [ ] Sunday entry says "Rest" — no post idea
- [ ] None of the six ideas repeat topics from recent Done/ or Pending_Approval/ posts (within the last 2–3 weeks)
- [ ] All 6 content pillars are represented across the week (at minimum 4 of the 6 appear)

**File integrity:**
- [ ] YAML front-matter is complete and valid — `type: approval_request`, `action: content_calendar`, `week_starting` is next Monday's date
- [ ] Filename is `CONTENT_CALENDAR_[YYYYMMDD].md` (today's date, not Monday's)
- [ ] File is saved in `/Pending_Approval/` (not `/Needs_Action/` or `/Plans/`)
- [ ] The "How to Use" and "To Approve / To Reject" sections are present

**Process:**
- [ ] Company_Handbook.md was read before generating (not recalled from memory)
- [ ] Done/ and Pending_Approval/ were scanned before generating
- [ ] No duplicate calendar was created if one already exists for this week
- [ ] Dashboard.md Today's Activity was updated

---

## Example Output

**For Reference Only — Do NOT Copy**

This example is for the week of 2026-03-16. Recent posts covered: folder-based state machines (architecture), Claude Opus 4.6 launches (news/opinion), silver tier announcement (project update). So this week avoids those and rotates to underused pillars.

```markdown
---
type: approval_request
action: content_calendar
created: 2026-03-15T09:00:00Z
week_starting: 2026-03-16
status: pending
---

# 📅 Content Calendar — Week of 16 March 2026

*Generated by your AI Employee on 15 March 2026. Review, adjust, and approve by end of Sunday.*

## Monday 16 March — Python async broke my brain
- **Hook:** My Python code ran perfectly. Then I added `async` and it ran perfectly wrong.
- **Angle:** Specific story about the exact moment async/await made no sense — not a tutorial, a debugging story with a twist ending where the fix was embarrassingly simple.
- **Type:** Educational
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Tuesday 17 March — The student who went from 40 to 70
- **Hook:** I failed to teach one student for 3 weeks. Then I stopped explaining and started asking.
- **Angle:** Real story from Taha's tutoring — the exact shift from "here's the answer" to "why do you think that?" and what happened to the student's grade.
- **Type:** Story
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Wednesday 18 March — Most AI courses are backwards
- **Hook:** Most AI courses teach you tools. None of them teach you what to build.
- **Angle:** Opinion: the gap between "I finished the course" and "I built something real" — and why building a broken thing taught more than 10 hours of lectures.
- **Type:** Opinion
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Thursday 19 March — How my AI employee decides what to do
- **Hook:** My AI employee doesn't have a database. It has folders.
- **Angle:** Behind-the-scenes of the folder-based state machine in plain language — what the Perception → Reasoning → Approval pipeline actually looks like when running live.
- **Type:** Update
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Friday 20 March — What I got wrong about "learning in public"
- **Hook:** I thought learning in public meant posting wins. I was wrong.
- **Angle:** Honest reflection on what learning in public actually means — sharing the broken attempts, not just the working demos. Specific example from this week.
- **Type:** Reflection
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Saturday 21 March — Spec first or code first?
- **Hook:** Do you write the spec before the code, or is spec-driven development just procrastination with extra steps?
- **Angle:** Real debate — Taha uses spec-driven development because Claude Code works better with a spec. But is that always the right move? Invite the audience to weigh in.
- **Type:** Engagement
- **To draft:** Drop a note in `Drop_Here/` with this topic and any extra context.

## Sunday 22 March — Rest
No post recommended. Rest, reflect, plan next week.

---

## How to Use This Calendar

1. Review each day's idea — adjust the topic or angle if something feels off
2. Approve this file (move to `/Approved/`) to confirm the week's plan
3. Each day, drop a short note in `Drop_Here/` referencing that day's topic (add any new context from your day)
4. The `draft_linkedin_post` skill will turn it into a full post and save it to `/Pending_Approval/`
5. Review and approve each post before it goes live

**You don't have to follow this exactly.** The calendar is a starting point. If something better happens on Wednesday, post about that instead.

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

## Implementation Notes

- **This skill generates a plan, not drafts.** The calendar file contains ideas and hooks, not finished posts. Each idea still requires a separate run of `draft_linkedin_post` to become an actual post. The calendar's job is to reduce decision fatigue so Taha always knows what topic to drop each morning.
- **Manual trigger routing:** When `content_calendar_now.md` is dropped in `Drop_Here/`, the filesystem_watcher creates an action file with `type: content_calendar_trigger`. The reasoning_loop's skill assignment table needs a corresponding entry: `content_calendar_trigger` → `content_calendar`.
- **Duplicate prevention:** Check for an existing `CONTENT_CALENDAR_*.md` in `/Pending_Approval/` with a matching `week_starting` date before generating. If found, log a warning and do not overwrite. Taha may have already started editing the existing one.
- **Scheduler runs on Sunday morning at 9 AM.** The skill should always plan for the Monday–Sunday *following* the current Sunday. Never plan for the current week (which is almost over).
- **Graceful degradation:** If `/Done/` is empty or has no `LINKEDIN_POST_*.md` files, generate the calendar without deduplication — just apply pillar rotation from the day-type assignment table. Do not error on an empty history.
- **Week date computation:** Use Python's `datetime` module logic mentally. Sunday = weekday 6. Next Monday = today + (7 - weekday) days if today is not Monday, or today + 7 days if today is Monday.
- **The calendar approves into `/Done/`** when Taha moves it to `/Approved/`. The orchestrator does not need to take any external action for `action: content_calendar` — it is informational. The orchestrator should log "Content calendar approved for week of [date]" and move to `/Done/` as normal.
- **Never fabricate context.** If this is the first week and there are no recent posts to reference, say so in the calendar's intro line: "No recent posts found — suggestions based on content pillars only." Don't invent a post history.
- **Content pillar coverage:** Aim for at least 4 of the 6 pillars across Mon–Sat. The day-type assignments handle this by design, but if recent posts have heavily covered one pillar, deprioritize it even if it's assigned to that day — cross-pillar suggestions within the same day type are acceptable.

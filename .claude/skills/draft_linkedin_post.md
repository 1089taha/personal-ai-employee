# Skill: draft_linkedin_post

**Type:** Content Generation Skill
**Triggers:** Files in `/Needs_Action/` with type `"thought_drop"` or `"tech_news"`
**Output:** Approval request file in `/Pending_Approval/`

---

## Description

This skill is used when a file in `/Needs_Action/` has type `"thought_drop"` or `"tech_news"`. It reads the raw content, drafts a polished LinkedIn post, and creates an approval request file in `/Pending_Approval/`.

---

## When to Trigger

- A file in `/Needs_Action/` has type: `"thought_drop"` (raw note dropped by Taha)
- A file in `/Needs_Action/` has type: `"tech_news"` (article fetched by Tavily news watcher)

---

## Input Requirements

- The `.md` file from `/Needs_Action/` containing raw content or news article
- `/Company_Handbook.md` for tone, identity, and rules

---

## Step-by-Step Process

### 1. Read Input Files
Read the action file from `/Needs_Action/`

### 2. Load Identity & Tone Rules
Read `/Company_Handbook.md` to load Taha's identity, tone rules, and content guidelines

### 3. Determine Source Type
Check the YAML front-matter type:

- **If type is `"thought_drop"`:**
  Polish Taha's raw thought into a professional LinkedIn post. Keep his original idea and voice — just make it clearer and more engaging

- **If type is `"tech_news"`:**
  Write a LinkedIn post that shares the news WITH Taha's personal perspective. Not a summary — an opinion piece. What does this news mean for builders? Why should Taha's audience care?

### 4. Draft the LinkedIn Post

Follow these **EXACT rules:**

#### Structure

**First Line:**
A scroll-stopping hook. Something surprising, a bold take, a question, or a brutally honest statement. This line appears before "...see more" on LinkedIn mobile — it MUST make people click.

**Body:**
3-5 short paragraphs, each 1-2 sentences max. Use line breaks between paragraphs (LinkedIn mobile formatting). Be specific — use real names, real numbers, real details. No vague statements.

**Voice:**
Write as Taha — a 20-year-old builder from Karachi who is genuinely nerdy about AI and shares his real journey. Conversational, not corporate. Light humor where natural.

**Ending:**
A genuine question that invites discussion OR a call to action. Not "What do you think?" — something specific like "Have you tried building agents with file-based state machines? What was your experience?"

**Hashtags:**
3-5 relevant hashtags at the very bottom. Never use generic ones like #success #motivation #leadership. Use specific ones like #AIAgents #ClaudeCode #BuildInPublic #AgenticAI #Python.

#### Banned Phrases

**NEVER use:**
- "In today's rapidly evolving landscape"
- "leveraging"
- "synergy"
- "game-changer"
- "thought leader"
- "delighted to announce"
- "humbled"
- "excited to share" (unless about something genuinely specific)

#### Length

Keep under **1300 characters total** (LinkedIn shows full post without truncation under this limit)

### 5. Create Approval Request File

Save in `/Pending_Approval/` with this EXACT format:

```markdown
---
type: approval_request
action: linkedin_post
source: [thought_drop or tech_news]
topic: "[2-5 word topic summary]"
created: [ISO 8601 timestamp]
expires: [24 hours after creation, ISO 8601]
status: pending
---

## Drafted LinkedIn Post

[The full post text exactly as it should appear on LinkedIn]

## Source
[If tech_news: Article title, source name, and URL]
[If thought_drop: "Personal thought/experience by Taha"]

## Character Count
[Exact character count of the post text]

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

**File Naming:**
`LINKEDIN_POST_[topic]_[YYYYMMDD].md`

### 6. Mark as Processed

Move the processed file from `/Needs_Action/` to `/Plans/` to mark it as processed.

If a Plan file would be useful (multi-step reasoning was needed), create a `PLAN_*.md` in `/Plans/` documenting your reasoning.

### 7. Update Dashboard

Update `/Dashboard.md`:
- Increment "Awaiting Approval" count
- Add entry to "Recent Activity" like:
  `[timestamp] Drafted LinkedIn post: [topic] — awaiting approval`

---

## Quality Checks

Verify before saving:

- [ ] Post is under 1300 characters
- [ ] First line is genuinely attention-grabbing (not generic)
- [ ] Written in Taha's voice (20-year-old builder, not corporate executive)
- [ ] No banned phrases used
- [ ] Has 3-5 specific hashtags
- [ ] Ends with engaging question or CTA
- [ ] If tech_news: includes Taha's personal take, not just a summary
- [ ] If thought_drop: preserves Taha's original idea while making it more polished
- [ ] YAML front-matter is complete and valid
- [ ] File is saved in `/Pending_Approval/` with correct naming

---

## Example Output

**For Reference Only — Do NOT Copy**

```markdown
---
type: approval_request
action: linkedin_post
source: thought_drop
topic: "AI Employee Hackathon Start"
created: 2026-02-16T10:00:00Z
expires: 2026-02-17T10:00:00Z
status: pending
---

## Drafted LinkedIn Post

I'm mass producing employees.

Not hiring them. Building them. With Python scripts and markdown files.

I just started the Panaversity AI Employee Hackathon — the goal is to build an autonomous agent that monitors my Gmail, WhatsApp, and tech news, then drafts LinkedIn posts and replies for me.

The wildest part? The entire "state management" is just moving files between folders. No database. No Redis. Just /Needs_Action → /Pending_Approval → /Approved → /Done.

My AI employee reads a folder, thinks, writes a draft, and waits for me to approve. Like a real employee, except it doesn't take chai breaks.

What's the most unconventional architecture decision you've made in a project?

#AIAgents #BuildInPublic #ClaudeCode #AgenticAI #Hackathon

## Source
Personal thought/experience by Taha

## Character Count
687

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

## Implementation Notes

- This skill is executed by Claude Code within a reasoning session
- The skill reads markdown files, applies Taha's voice/tone rules, and generates new files
- All file operations should be logged for debugging
- Character count must be exact (including spaces, hashtags, everything)
- The expiration timestamp ensures approval requests don't sit forever

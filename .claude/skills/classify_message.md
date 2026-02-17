# Skill: classify_message

**Type:** Message Processing & Reply Drafting Skill
**Triggers:** Files in `/Needs_Action/` with type `"email"` or `"whatsapp"`
**Output:** Approval request file in `/Pending_Approval/`

---

## Description

This skill is used when a file in `/Needs_Action/` has type `"email"` (from Gmail watcher) or `"whatsapp"` (from WhatsApp watcher). It reads the incoming message, classifies its priority level, drafts an appropriate reply (or flags sensitive messages for manual handling), and creates an approval request file in `/Pending_Approval/`.

This skill handles both professional Gmail messages and casual WhatsApp conversations — adjusting tone, language, and formality accordingly.

---

## When to Trigger

- A file in `/Needs_Action/` has type: `"email"` (incoming Gmail message)
- A file in `/Needs_Action/` has type: `"whatsapp"` (incoming WhatsApp message)

---

## Input Requirements

- The `.md` file from `/Needs_Action/` containing message content
- `/Company_Handbook.md` for Taha's identity, tone rules, and reply guidelines

---

## Step-by-Step Process

### 1. Read Input Files

Read the message file from `/Needs_Action/` and extract:
- Message content
- Sender information
- Message type (email or whatsapp)
- Timestamp
- Subject line (if email) or conversation topic (if WhatsApp)

### 2. Load Identity & Tone Rules

Read `/Company_Handbook.md` to load:
- Taha's identity and background
- Professional tone guidelines for Gmail
- Casual tone guidelines for WhatsApp
- Language preferences (English, Roman Urdu)

### 3. Classify Priority Level

Analyze the message and classify into ONE of these priority levels:

**"urgent"** — Needs reply within hours
- Client request or deadline
- Meeting invite requiring confirmation
- Important opportunity (job offer, collaboration request)
- Time-sensitive question from professor/instructor
- Project deadline or submission reminder
- Anything explicitly marked urgent by sender

**"normal"** — Reply within 24 hours
- General professional questions
- Follow-up messages
- Networking messages
- Casual check-ins from colleagues/peers
- Information requests that aren't time-critical
- Standard WhatsApp conversations

**"low"** — FYI only, no reply needed
- Newsletters and automated notifications
- Promotional emails
- Group messages that don't mention Taha or ask for his input
- LinkedIn connection confirmations
- Automated system emails (password resets, receipts)
- Mass-forwarded messages

**"flagged"** — Handle personally, DO NOT auto-draft
- Complaint or criticism
- Conflict or disagreement
- Emotional topic (personal issues, family matters)
- Sensitive situation requiring careful handling
- Request to do something Taha would need to verify first (money, commitments)
- Messages from authority figures that could have consequences if handled poorly

### 4. Draft the Reply

#### For Gmail (Professional Context)

**Tone Rules:**
- Polite, clear, concise
- Match the sender's formality level:
  - University/GIAIC professors/admins → Slightly formal but friendly
  - Peers/classmates → Casual and direct
  - Recruiters/companies → Professional and enthusiastic
  - Unknown senders → Neutral professional

**Structure:**
- Greeting: "Hi [Name]," (if peer) or "Dear [Name]," (if formal)
- First line: Direct response to their main question/point
- Body: 2-4 short sentences max — answer their question or confirm their request
- Closing: "Thanks," or "Best regards," based on formality
- Sign-off: "Taha"

**Voice:**
- Write as Taha in first person
- Be genuine and helpful
- Never over-promise: If unsure, say "Let me check and get back to you"
- No corporate jargon or AI giveaway phrases

#### For WhatsApp (Casual Context)

**Tone Rules:**
- Friendly and direct
- 2-3 sentences max (this is WhatsApp, not an essay)
- Match the sender's language:
  - If they wrote in Roman Urdu → Reply in Roman Urdu
  - If they wrote in English → Reply in English
  - If they used casual slang → Match their energy

**Structure:**
- No formal greeting (WhatsApp is conversational)
- Jump straight to the response
- Keep it natural and brief
- Use casual sign-offs like "👍" or just end the message

**Voice:**
- Write like a 20-year-old texting a friend or peer
- Natural, not performative
- Helpful but not overly formal

### 5. Handle Different Priority Levels

**For "urgent" and "normal" messages:**
Draft a complete reply following the tone rules above.

**For "low" priority messages:**
Create the approval file but mark as:
```
No reply needed. This is for awareness only.
```

**For "flagged" messages:**
Create the approval file but put at the very top:
```
⚠️ FLAGGED: This message involves [reason]. Please review carefully and write your own reply.
```
DO NOT draft a reply. Leave the "Drafted Reply" section with only the flagged warning.

### 6. Create Approval Request File

Save in `/Pending_Approval/` with this EXACT format:

```markdown
---
type: approval_request
action: [send_gmail or send_whatsapp]
source: [email or whatsapp]
from: "[sender name or number]"
subject: "[subject line or conversation topic]"
priority: [urgent/normal/low/flagged]
original_msg_id: "[message ID if available]"
created: [ISO 8601 timestamp]
expires: [24 hours after creation, ISO 8601]
status: pending
---

## Original Message
**From:** [sender]
**Subject/Topic:** [subject]
**Received:** [timestamp]

[Full original message content]

## Priority Classification
**Level:** [urgent/normal/low/flagged]
**Reason:** [1 sentence explaining why this classification]

## Drafted Reply
[The reply text exactly as it should be sent]
[OR for flagged: "⚠️ FLAGGED: [reason]. No auto-draft. Taha must write this reply personally."]
[OR for low: "No reply needed. This is for awareness only."]

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

**File Naming:**
- Gmail: `GMAIL_REPLY_[sender-short]_[YYYYMMDD].md`
- WhatsApp: `WHATSAPP_REPLY_[contact]_[YYYYMMDD].md`

Example file names:
- `GMAIL_REPLY_professor-ali_20260216.md`
- `WHATSAPP_REPLY_hamza_20260216.md`

### 7. Mark as Processed

Move the processed file from `/Needs_Action/` to `/Plans/` to mark it as processed.

### 8. Update Dashboard

Update `/Dashboard.md`:
- Increment "Awaiting Approval" count
- Add entry to "Recent Activity" like:
  - `[timestamp] Drafted Gmail reply to [sender] (priority: urgent) — awaiting approval`
  - `[timestamp] Flagged WhatsApp message from [sender] for manual review`
  - `[timestamp] Classified email from [sender] as low priority (no reply needed)`

---

## Quality Checks

Verify before saving:

- [ ] Priority classification is accurate and has a clear reason
- [ ] Reply matches the language of the original (English vs Roman Urdu)
- [ ] Gmail replies are professional; WhatsApp replies are casual
- [ ] Tone matches the sender's formality level
- [ ] No AI giveaway phrases ("As an AI", "I'd be happy to help", "I'm here to assist")
- [ ] Flagged messages have NO drafted reply — only the flag warning
- [ ] Low priority messages are marked "No reply needed"
- [ ] YAML front-matter is complete and valid
- [ ] File is saved in `/Pending_Approval/` with correct naming
- [ ] Original message is preserved in full (for context)
- [ ] Reply is helpful and doesn't over-promise
- [ ] WhatsApp replies are 2-3 sentences max
- [ ] Gmail replies are clear and concise (not essay-length)

---

## Example Output 1: Gmail Reply (Normal Priority)

**For Reference Only — Do NOT Copy**

```markdown
---
type: approval_request
action: send_gmail
source: email
from: "Dr. Ahmed Khan"
subject: "Guest Lecture on AI Ethics - Confirmation Needed"
priority: normal
original_msg_id: "msg_abc123xyz"
created: 2026-02-16T14:30:00Z
expires: 2026-02-17T14:30:00Z
status: pending
---

## Original Message
**From:** Dr. Ahmed Khan <a.khan@uit.edu.pk>
**Subject/Topic:** Guest Lecture on AI Ethics - Confirmation Needed
**Received:** 2026-02-16 14:15:00

Dear Taha,

I hope this email finds you well. I am organizing a guest lecture series on AI Ethics for our Data Science students next month.

Given your work with Agentic AI and your involvement in the GIAIC program, I thought you might be interested in attending or perhaps sharing your perspective on building ethical AI systems as a student builder.

The lecture is on March 5th at 3 PM in the main auditorium. Would you be available to attend? If you're interested in speaking (even for 10 minutes), that would be valuable for the students.

Please let me know by this Friday.

Best regards,
Dr. Ahmed Khan
Department of Computer Science
UIT

## Priority Classification
**Level:** normal
**Reason:** Request for confirmation with a clear deadline (this Friday), but not immediately urgent.

## Drafted Reply
Hi Dr. Ahmed Khan,

Thank you for thinking of me! I'd love to attend the lecture on March 5th at 3 PM — AI ethics is something I think about a lot while building agents.

I'd also be happy to share a 10-minute perspective on building ethical AI as a student. I can talk about real challenges I've faced with my AI employee project (like ensuring human approval before any action).

Let me know if that works, and I'll prepare accordingly.

Thanks,
Taha

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

## Example Output 2: WhatsApp Reply (Urgent Priority, Roman Urdu)

**For Reference Only — Do NOT Copy**

```markdown
---
type: approval_request
action: send_whatsapp
source: whatsapp
from: "Hamza (Student)"
subject: "Tomorrow's Class Confirmation"
priority: urgent
original_msg_id: "whatsapp_msg_456"
created: 2026-02-16T19:45:00Z
expires: 2026-02-17T19:45:00Z
status: pending
---

## Original Message
**From:** Hamza (Student)
**Subject/Topic:** Tomorrow's Class Confirmation
**Received:** 2026-02-16 19:40:00

Bhai kal class ho rahi hai? Ya cancel hai? Assignment bhi submit karni hai na kal?

## Priority Classification
**Level:** urgent
**Reason:** Student asking about tomorrow's class with assignment deadline — needs immediate response.

## Drafted Reply
Haan bhai, kal class ho rahi hai normal time pe. Assignment bhi kal hi submit karni hai, extension nahi hai. Ready rakhna!

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

## Example Output 3: Flagged Message (Sensitive Situation)

**For Reference Only — Do NOT Copy**

```markdown
---
type: approval_request
action: send_gmail
source: email
from: "University Finance Office"
subject: "Outstanding Fee Payment - Final Notice"
priority: flagged
original_msg_id: "msg_finance_789"
created: 2026-02-16T11:00:00Z
expires: 2026-02-17T11:00:00Z
status: pending
---

## Original Message
**From:** UIT Finance Office <finance@uit.edu.pk>
**Subject/Topic:** Outstanding Fee Payment - Final Notice
**Received:** 2026-02-16 10:45:00

Dear Student,

This is a final notice regarding your outstanding semester fee payment of PKR 45,000. As per university policy, failure to clear dues by February 20th may result in examination access being blocked.

If you have already made the payment, please submit proof to the finance office immediately. If you are facing financial difficulty, please contact the Student Welfare Office to discuss installment options.

Regards,
Finance Office
UIT

## Priority Classification
**Level:** flagged
**Reason:** Involves student loan/financial situation and potential consequences — requires Taha's personal verification and response.

## Drafted Reply
⚠️ FLAGGED: This message involves financial matters and potential examination consequences. Please review carefully and write your own reply.

Check if payment has been made via loan disbursement. If not, contact Student Welfare Office immediately for installment options.

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

## Implementation Notes

- This skill is executed by Claude Code within a reasoning session
- The skill must handle both formal Gmail and casual WhatsApp messages
- Language detection is critical: If sender uses Roman Urdu, reply must be in Roman Urdu
- Flagged messages MUST NOT have auto-drafted replies — only the warning
- Priority classification should err on the side of caution (if uncertain between normal and urgent, choose urgent)
- All file operations should be logged for debugging
- The expiration timestamp ensures approval requests don't sit forever
- For WhatsApp, brevity is key — the AI employee should write like a real 20-year-old texting

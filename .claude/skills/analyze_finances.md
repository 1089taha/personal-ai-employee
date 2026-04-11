# Skill: analyze_finances

**Type:** Personal Finance Analysis Skill
**Triggers:** Files in `/Needs_Action/` with type `"finance_drop"`
**Output:** Finance briefing approval request in `/Pending_Approval/`

---

## Description

This skill is used when a file in `/Needs_Action/` has type `"finance_drop"`. It reads Taha's raw weekly expense/income data (dropped as a file), parses it flexibly (including Roman Urdu), compares against historical data, and generates a concise personal finance briefing written in Taha's voice. The briefing lands in `/Pending_Approval/` for review before anything is stored or acted on.

All amounts are in Pakistani Rupees (PKR). Taha is 20 years old, earns from tutoring (irregular income), and is building savings discipline on a student budget in Karachi.

---

## When to Trigger

- A file in `/Needs_Action/` has type: `"finance_drop"` (raw expense/income data dropped by Taha)

---

## Input Requirements

- The `.md` file from `/Needs_Action/` containing raw finance data (YAML header + `## Raw Finance Data` section)
- `/Finance_History/` folder in the vault — read the most recent previous briefing for week-over-week comparison (may not exist yet)
- `/Company_Handbook.md` for Taha's identity, life context, and tone

---

## Understanding the Input Format

Raw finance data is **flexible, not rigid**. Taha may write it in any style. Examples of valid input:

```
week: 2026-03-01
income: 12000

Fuel: 500
Food: 1400
Transport: 300
Mobile: 200
Snacks: 600
Clothes: 800
Miscellaneous: 400
```

```
earned: 8000
petrol: 400
khana: 1200
chai: 300
safar: 200
mobile recharge: 150
```

**Parsing rules:**

- Lines with `income:`, `earned:`, `salary:`, or `got paid:` → this is **income**
- All other `key: number` lines → these are **expenses**
- Numbers are always **PKR** (no currency conversion needed)
- `week:` field tells you the period; if absent, use the file creation date from the YAML front-matter
- If a field label is in **Roman Urdu or Urdu**, understand it and categorize correctly:
  - `petrol` → Transport
  - `khana` → Food
  - `safar` / `transport` → Transport
  - `chai` → Food
  - `mobile recharge` / `recharge` → Digital
  - `kitab` / `stationery` → Education
  - `dawai` / `dawa` → Health
  - `ghar ka kharcha` → Household
  - When in doubt about a label, categorize as Other and note it
- If income is not mentioned at all, treat it as 0 (expense-only entry)
- Ignore lines that have no number (comments, blank lines, headers)

---

## Step-by-Step Process

### 1. Parse the Raw Data

Read the `## Raw Finance Data` section from the action file. Extract:

- **Income** — sum of all income/earned/salary lines (0 if none)
- **Expenses** — list of all items with their amounts
- **Week** — from `week:` field or file creation date
- **Total expenses** — sum of all expense amounts
- **Net** — income minus total expenses (can be negative)
- **Savings rate** — `(net / income × 100)` only if income > 0; otherwise omit

Double-check your arithmetic before proceeding.

### 2. Categorize Expenses

Map every expense item to one of these buckets. Show only buckets that have spending.

| Bucket | What goes here |
|---|---|
| 🚗 Transport | fuel, petrol, transport, rickshaw, uber, careem, safar, bus |
| 🍽️ Food | food, khana, lunch, dinner, chai, snacks, groceries, naashta |
| 📱 Digital | mobile, internet, recharge, subscription, data |
| 👕 Personal | clothes, shoes, personal items, kapre |
| 📚 Education | books, stationery, fees, university, kitab, copies |
| 🎮 Entertainment | games, cinema, outings, entertainment |
| 💊 Health | medicine, doctor, dawai, dawa |
| 🏠 Household | rent, utilities, household items, ghar ka kharcha |
| 🤷 Other | anything that doesn't clearly fit above (note original label) |

Calculate each bucket's percentage of total expenses.

### 3. Load History for Comparison

- Check the `/Finance_History/` folder in the vault
- Read the most recent `FINANCE_*.md` file (sorted by date descending)
- Extract previous week's: total expenses, per-category amounts
- If `/Finance_History/` is empty or does not exist: note "First entry — no comparison available"
- If history exists, identify:
  - Overall spend change (up/down by PKR amount and %)
  - Category with biggest increase (+ amount)
  - Category with biggest decrease (- amount)
  - Running totals: all-time logged income, last 4 weeks average spend

### 4. Generate the Briefing File

Save in `/Pending_Approval/` using this **exact structure**:

```markdown
---
type: approval_request
action: finance_briefing
source: finance_drop
week: [week date or period]
income: [amount or 0]
total_expenses: [amount]
savings: [amount — can be negative]
savings_rate: [percentage with 1 decimal, or "N/A — no income"]
created: [ISO 8601 timestamp]
status: pending
---

# 💰 Weekly Finance Briefing — [Week Date]

## Summary
| | Amount (PKR) |
|--|--|
| Income | [amount] or "No income this week" |
| Total Spent | [amount] |
| Saved | [amount] |
| Savings Rate | [percentage]% or "N/A" |

[One of these four status lines based on the numbers:]
✅ Good week — you saved over 20% of income.
⚠️ Tight week — you saved [n]% of income.
🔴 Overspent — expenses exceeded income by PKR [amount].
📋 Expense-only entry — no income recorded this week.

## Spending Breakdown
| Category | Amount (PKR) | % of Expenses |
|----------|-------------|---------------|
[One row per category that has spending, sorted highest to lowest amount]

## vs Last Week
[If history exists:]
- Total spending: [up/down] by PKR [amount] ([+/-]% change)
- Biggest increase: [Category] +PKR [amount]
- Biggest decrease: [Category] -PKR [amount]

[If no history:]
First entry — will compare from next week.

## Taha's Financial Snapshot
- **Spending this entry**: PKR [amount]
- **Total logged income (all time)**: PKR [sum from all history files + this week]
- **Average weekly spend (last 4 entries)**: PKR [average or "Not enough data yet"]
- **Estimated monthly burn rate**: PKR [weekly avg × 4 or "Not enough data yet"]

## AI Advisor's Take
[3-5 specific, direct observations based on the actual numbers.
Write as a practical friend who has looked at the spreadsheet and
is giving real talk — not a corporate advisor or motivational coach.
Use actual PKR amounts from the data. Call out patterns honestly.
Examples of the right tone:]

- "You're spending PKR 600 on chai and snacks — that's 5% of income. Small cuts add up."
- "Food is your biggest expense at 25%. Cooking at home twice a week could save PKR 400-600."
- "Transport cost is reasonable for Karachi. Keep it there."
- "No savings this week. If this continues 4 weeks, you'll have zero buffer for emergencies."
- "Income was higher than average this week — good time to set aside PKR 1,000-2,000 before it disappears."

NEVER say "great job" if the numbers don't support it.
NEVER use phrases like "fiscal responsibility", "financial wellness",
"optimize your spending", or "invest in your future".

## Action Items for This Week
[2-3 specific and achievable actions — based on what the data actually shows:]
1. [Most impactful thing to cut or change, with a specific PKR target]
2. [A concrete savings target for next week]
3. [If income was low or zero: one practical suggestion to earn more from tutoring or other means]

## Savings Goal
[Calculate: if Taha saved 15% of his average income per week, what would that build?
Show the arithmetic clearly. Tie the 6-month total to something meaningful in Pakistan.]

Example format:
"Save PKR [15% of avg income] per week → PKR [×4] per month → PKR [×24] in 6 months.
That's enough for [something real and specific: a decent laptop, 3 months emergency fund,
a professional course, etc. Use current PKR values]."

If not enough history for an average: use this week's income as the baseline.
If income was 0 this week: use the most recent income from history.
If no history and no income: skip the savings goal section and note why.

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

**File naming:** `FINANCE_BRIEFING_[YYYYMMDD].md`
Example: `FINANCE_BRIEFING_20260301.md`

### 5. Save to Finance History

Copy the **raw finance data** (the `## Raw Finance Data` section from the action file) to `/Finance_History/` as:

`FINANCE_[YYYYMMDD].md`

Include the week date and raw data only — this folder is the audit trail. Never delete from it.

Example file: `FINANCE_20260301.md`

```markdown
---
week: 2026-03-01
income: 12000
total_expenses: 4200
savings: 7800
---

## Raw Data

week: 2026-03-01
income: 12000

Fuel: 500
Food: 1400
...
```

### 6. Mark as Processed

Move the original action file from `/Needs_Action/` to `/Plans/`.

If the history comparison or categorization required non-obvious decisions (e.g., an ambiguous Urdu label), create a `PLAN_FINANCE_[YYYYMMDD].md` in `/Plans/` noting those decisions for future reference.

### 7. Update Dashboard

Update `/Dashboard.md`:
- Increment "Awaiting Approval" count
- Add entry to "Recent Activity":
  `[timestamp] Finance briefing created for [week] (Income: PKR [x] / Spent: PKR [y]) — awaiting approval`

---

## Quality Checks

Verify before saving:

- [ ] All arithmetic is correct — income, total expenses, net, savings rate all cross-check
- [ ] Percentages in the breakdown table add up to ~100% (allow ±1% for rounding)
- [ ] Savings rate is omitted (shown as "N/A") when income is 0
- [ ] Correct status line used (✅ / ⚠️ / 🔴 / 📋) based on actual savings rate
- [ ] Roman Urdu / Urdu labels were correctly interpreted and categorized
- [ ] Only categories with actual spending appear in the breakdown table
- [ ] AI Advisor's Take uses actual PKR numbers from the data, not generic advice
- [ ] Action items are specific and achievable on a student budget in Karachi
- [ ] Savings Goal math is correct and the 6-month target is meaningful in PKR terms
- [ ] `FINANCE_[YYYYMMDD].md` saved to `/Finance_History/`
- [ ] Action file moved from `/Needs_Action/` to `/Plans/`
- [ ] Dashboard updated
- [ ] YAML front-matter is complete and valid
- [ ] Briefing saved as `FINANCE_BRIEFING_[YYYYMMDD].md` in `/Pending_Approval/`

---

## Example Output

**For Reference Only — Do NOT Copy**

```markdown
---
type: approval_request
action: finance_briefing
source: finance_drop
week: 2026-03-01
income: 12000
total_expenses: 4200
savings: 7800
savings_rate: 65.0
created: 2026-03-01T12:00:00Z
status: pending
---

# 💰 Weekly Finance Briefing — 2026-03-01

## Summary
| | Amount (PKR) |
|--|--|
| Income | 12,000 |
| Total Spent | 4,200 |
| Saved | 7,800 |
| Savings Rate | 65.0% |

✅ Good week — you saved over 20% of income.

## Spending Breakdown
| Category | Amount (PKR) | % of Expenses |
|----------|-------------|---------------|
| 🍽️ Food | 2,000 | 47.6% |
| 👕 Personal | 800 | 19.0% |
| 🚗 Transport | 500 | 11.9% |
| 📱 Digital | 200 | 4.8% |
| 🤷 Other | 400 | 9.5% |
| 🍽️ Food (Snacks) | 300 | 7.1% |

## vs Last Week
First entry — will compare from next week.

## Taha's Financial Snapshot
- **Spending this entry**: PKR 4,200
- **Total logged income (all time)**: PKR 12,000
- **Average weekly spend (last 4 entries)**: Not enough data yet
- **Estimated monthly burn rate**: Not enough data yet

## AI Advisor's Take
- Food is nearly half your spending at PKR 2,000. That's not terrible for a week in Karachi, but if even PKR 400 of that is café runs you could skip, that's worth thinking about.
- You spent PKR 800 on clothes this week. One-off or a habit? Check back next week — if it repeats, it'll quietly eat your savings.
- PKR 300 on snacks on top of PKR 1,400 on food means you're spending PKR 1,700 total on eating. That's 14% of income. Fine for now, but it's the category with the most easy trims.
- This was actually a good week — PKR 7,800 saved from PKR 12,000 earned is a 65% savings rate. The trap is spending it before next week. Put PKR 5,000 somewhere you won't accidentally use it.

## Action Items for This Week
1. Before spending the PKR 7,800 you saved, move PKR 5,000 somewhere separate (savings account, mobile wallet, anywhere with friction).
2. Track food separately next week — split "meals" from "chai/snacks" so you can see which one is the real driver.
3. Income was PKR 12,000 this week. Try to lock in at least one more tutoring session next week to keep income consistent.

## Savings Goal
Save PKR 1,800 per week (15% of PKR 12,000) → PKR 7,200 per month → PKR 43,200 in 6 months.
That's enough for a solid mid-range laptop, or a 2-month emergency fund, or a professional certification course — real optionality built from PKR 1,800/week discipline.

## To Approve
Move this file → /Approved/

## To Reject
Move this file → /Rejected/
```

---

## Implementation Notes

- This skill is executed by Claude Code within a reasoning session
- Parsing must be flexible — Taha's input will never be perfectly formatted
- Roman Urdu label detection is important; when uncertain, make a reasonable guess and note it in the Plans file
- All arithmetic must be verified before writing the briefing — wrong numbers erode trust in the system
- The AI Advisor's Take must reflect the actual data — generic finance tips are useless and will make Taha ignore the briefing
- PKR 1,000 ≈ USD 3.50 for any context in suggestions (e.g., what a 6-month savings total could buy)
- PKR 50,000/month is the benchmark for "comfortable" at Taha's life stage; use this to calibrate whether something is high/low spending
- The Finance History folder is append-only — never delete or modify existing files in it
- If `/Finance_History/` does not exist, create it during this skill's execution

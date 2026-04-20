# DSP Discovery Interview Guide

*Use this before designing any DSP-facing UX. The goal is to understand how DSP owners actually manage driver safety today — not to pitch anything.*

---

## Before the Meeting — Prep Checklist

- [ ] Send a 1-paragraph agenda in advance: "I want to understand how you manage driver safety today, not pitch anything"
- [ ] Know their fleet size and how long they've been a DSP partner
- [ ] Review any existing safety incidents or SNS notifications their drivers have triggered
- [ ] Block 45 min; plan to use 35 and give 10 back
- [ ] Have a doc open to take notes verbatim — capture their exact words, not your interpretation
- [ ] Bring a second person if possible: one talks, one takes notes

---

## Opening — Build Trust (5 min)

The goal here is to make clear you're not selling, auditing, or evaluating them.

- [ ] State your intent explicitly: *"I'm not here to evaluate your drivers or your business. I'm trying to understand what your day-to-day actually looks like so we can build tools that are useful, not just tools that exist."*
- [ ] Tell them what you'll do with their input: *"What I hear today will directly shape what we build — or whether we build it at all."*
- [ ] Ask if it's okay to take notes
- [ ] Start with a low-stakes question about them, not the problem

**Opening question:**
> "Before we get into anything specific — how long have you been running your DSP, and what's your fleet size today?"

---

## Section 1 — Understand Their World (10 min)

Goal: understand their actual workflow before assuming they have a "safety problem."

1. Walk me through a typical week. What does managing your operation actually look like day to day?
2. Who on your team is responsible for driver safety — is that you, or someone else?
3. What does a normal week look like for that person?
4. What tools or systems do you already use to track driver performance or safety? *(Let them list — don't suggest.)*
5. How often do you actually look at those tools?

---

## Section 2 — Current Pain (10 min)

Goal: find out if the problem you're solving is real and how acute it is.

6. When was the last time a driver safety issue caught you off guard? What happened?
7. How do you find out when a driver is having a bad week — before it becomes a bigger problem?
8. What's the hardest part of staying on top of driver safety right now?
9. Are there signals you wish you had but don't? Or signals you get but don't trust?
10. How do you decide which driver to talk to first when you're preparing for a weekly check-in?

---

## Section 3 — Notifications and Alerts (5 min)

Goal: understand how they process information they didn't go looking for.

11. Do you currently get any automated alerts or notifications about driver events? What do you do with them?
12. When you get an alert, what's the first thing you want to know?
13. Have you ever gotten an alert and thought "I already knew about this" — or "this doesn't seem right"?
14. What would make you trust an alert enough to act on it immediately?

---

## Section 4 — Decision and Action (5 min)

Goal: understand what "acting on the information" actually looks like — this is what the UX has to support.

15. When you identify a driver who needs attention, what do you actually do next? Walk me through the steps.
16. Is there anything that slows you down between "I see a problem" and "I've done something about it"?
17. Do you document coaching conversations anywhere? Does Amazon expect you to?
18. What does a good outcome look like after you've flagged a driver?

---

## Section 5 — Access and Constraints (5 min)

Goal: understand the practical UX constraints you'd never guess from the backend.

19. What device do you use most when you're doing this kind of review — laptop, phone, tablet?
20. Is this something you'd do in the office, on the road, or both?
21. How comfortable is your team with new software tools? Has anything failed to get adopted in the past — and do you know why?
22. Is there anything you'd never want a tool like this to do or show?

---

## Close — Leave the Door Open (5 min)

- [ ] Summarize back what you heard: *"What I'm hearing is X and Y — does that sound right?"*
- [ ] Ask: *"Is there anything I didn't ask that you expected me to ask?"*
- [ ] Ask: *"If we built something useful here, would you be willing to look at an early version and tell us what's wrong with it?"*
- [ ] Tell them the next step: *"I'm going to synthesize this across a few DSPs and come back to you before we build anything."*
- [ ] Send a follow-up thank-you within 24 hours that includes your 2–3 key takeaways — this signals you actually listened

---

## After the Meeting — Synthesis Checklist

- [ ] Write up notes within an hour while memory is fresh
- [ ] Highlight exact quotes — these become evidence when you're writing user stories
- [ ] Note what surprised you vs. what confirmed your assumptions
- [ ] Flag any workflow or constraint that would break your current design
- [ ] After 3+ interviews, look for patterns: what did every DSP say? What was unique to one?

---

## Notes

The questions in **Section 4 (Decision and Action)** are the most important ones to get right — that's where you'll find out whether the current architecture is even solving the right step in the DSP's workflow.

After completing interviews, use findings to:
- Write concrete user stories before designing any screens
- Validate or challenge the current data model (driver score, 7-day window, threshold of 9)
- Decide whether multi-tenancy (DSPs seeing only their own drivers) is a v1 or v2 requirement

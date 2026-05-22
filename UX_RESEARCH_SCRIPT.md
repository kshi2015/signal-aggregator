# UX Research Script — Concept Testing & Continued Discovery

*Use this after completing at least one round of problem discovery (DSP_DISCOVERY.md). The goal is to test the V1 product thesis — that a score with a recommended action and a way to log what you did is more useful than a score alone — and surface V2 priorities.*

*If this is a first-time interviewee: run Section 1 of DSP_DISCOVERY.md first (their world, 10 min), then pick up here.*

---

## Before the Meeting — Prep Checklist

- [ ] Open `design/index.html` in a browser (or Figma: https://www.figma.com/design/Z2Pvr8JVFZoyTRYuYtU3iD/Signal-Aggregator) — you'll share your screen in Section 3
- [ ] Know their fleet size and any round-1 notes on how they currently track safety actions
- [ ] Know which signals their drivers have triggered recently (if any) — makes the walkthrough concrete
- [ ] Block 45 min; plan for 40 and give 5 back
- [ ] Capture verbatim quotes — their exact words, not your paraphrase
- [ ] Bring a second person if possible: one talks, one notes

---

## Opening (3 min)

- [ ] Reconnect briefly if you've spoken before: *"Last time you told me [one thing you remember]. I want to pick up from there."*
- [ ] If first time: use DSP_DISCOVERY.md Section 1 opener instead, then come back here
- [ ] Set the frame explicitly:

> "I'm going to show you something we've sketched out. I want your honest reaction — not what you think I want to hear. If something looks wrong or useless, that's exactly what I need to know."

- [ ] Tell them the format: *"I'll walk you through a few screens, ask you to think out loud, and we'll end with what you'd actually want built. About 40 minutes."*

---

## Section 1 — Action Tracking Today (10 min)

*Goal: understand whether the "close the loop" thesis has any basis in reality before showing them anything. Do DSPs actually care about logging actions? Do they do it anywhere today?*

1. After you've talked to a driver about a safety issue — what happens next? Is there anything you write down or track?
2. Do you have any way of knowing, a week later, whether that conversation made a difference?
3. If a driver gets flagged again for the same thing, how do you know you've already talked to them about it?
4. Have you ever been asked by Amazon to show documentation of a coaching conversation? What did you do?
5. Walk me through the last time you followed up on a driver concern — from the moment you decided to act to the moment you considered it handled. What did that actually look like?

*Listen for: spreadsheets, notes apps, memory, shared docs, formal coaching platforms. Any existing system — even a sticky note — tells you this behavior has latent demand. Total absence means you're creating a new habit, which is harder.*

---

## Section 2 — Notifications and Alert Fatigue (8 min)

*Goal: test the 3-tier notification model before showing it visually. Understand what actually gets acted on vs. ignored.*

6. Right now, when you get an alert on your phone about a driver — what goes through your head in the first 5 seconds?
7. Has there ever been a stretch where you started ignoring certain alerts? What caused that?
8. If you get 4 separate alerts about 4 different drivers in one day — what do you actually do with that?
9. Is there a time of day you'd want an urgent alert suppressed — even if a driver just crossed a serious threshold?
10. When you get a weekly summary email from Amazon, do you read it? What do you do with it?
11. What would a message have to say to make you stop what you're doing and act on it right then?

*Listen for: alert fatigue language ("I just delete them"), channel preferences (SMS vs. email vs. in-app), timing sensitivity (end-of-day vs. morning-of-weekly-review). Note any explicit mention of Monday/Tuesday as their review day — that's the digest timing hypothesis.*

---

## Section 3 — Concept Walkthrough (15 min)

*Goal: get unfiltered reactions to the designs. Share your screen — open `design/index.html` or the Figma link above. Do NOT explain what each screen does before they react. Ask them to narrate.*

### Flow 1 — Action Queue (weekly review view)

- [ ] Show the main queue screen (drivers sorted by: Needs Action → Watching → Resolved)

12. Without me explaining anything — what do you think this screen is showing you?
13. Is this what you'd want to see first thing Monday morning, or would you want something different?
14. If you saw a driver in "Needs Action" — what would you do next?

- [ ] Show the driver detail screen (signal history + recommended action text)

15. What's your first reaction to that "Recommended action" line?
16. When you see a suggested action, is that helpful — or does it feel like it's telling you something you already know?
17. Is there anything on this screen you'd want to hide, or anything missing that you'd want to see?

### Flow 2 — Log an Action

- [ ] Show the "Log action" flow (action: in_progress / resolved / snoozed + optional note)

18. If you'd just had a 1:1 with this driver — which of these would you tap?
19. Would you ever write anything in the note field, or would you leave it blank?
20. After logging something here, what would you expect to happen — what would change?

*Listen for: confusion about what "In Progress" vs. "Resolved" means, skepticism about whether logging anything is worth the friction, any instinct to want more statuses (escalated, referred to HR, etc.).*

21. If you had a driver you'd already talked to and were just keeping an eye on — what would you do here? *(They may reach for snooze. If not: "Is there a snooze option you'd want?")*

### Flow 3 — Urgent Alert

*Describe this one verbally rather than showing a mockup:*

> "Imagine it's 9pm and you get a text: 'Driver Maria S. score: 11 — tap to review.' You tap it, and it opens directly to Maria's detail screen."

22. Is that the right channel for that message? Or would you want it somewhere else?
23. Would you act on that tonight, or wait until morning?
24. What would the message need to say for you to act on it immediately vs. deal with it tomorrow?

---

## Section 4 — Playbook Configuration (5 min)

*Goal: test whether DSP owners will actually customize the playbook, or whether defaults will do. Don't oversell customization — let them react.*

- [ ] Show the playbook editor screen (9 rows: signal type × severity → recommended action text)

25. If this was already filled in with defaults — would you change anything, or just leave it?
26. Is there a type of signal where the right action is really different depending on the driver? Or is it usually the same across your fleet?
27. If you had a driver you trusted and a driver you didn't — would you want a different playbook for each, or is fleet-level fine?

*Listen for: whether they see per-driver customization as important — that's a V2 scoping decision. Also listen for whether the 9-combo matrix (3 signal types × 3 severities) matches how they actually think about actions, or whether it feels overly structured.*

---

## Section 5 — V2 Priorities (4 min)

*Goal: force a rank to surface what would actually drive adoption. Don't offer everything — make them choose.*

28. After seeing this — what's the one thing that would make you actually open this before your Monday review instead of going straight to whatever you use today?
29. I'm going to name four things we could build next. Tell me which one matters most to you:
    - Score history for each driver — can you see if they're trending better or worse over time?
    - Multi-user access — your ops manager sees the same queue you do and can log actions too
    - Mobile-first experience — everything works well on your phone, not just a desktop screen
    - SMS/text-based action logging — reply to the alert text to log what you did, no app required

    *If they struggle: "If you could only have one, which one?"*

30. Is there anything about how you work today that this design would break or create friction with?

---

## Close (3 min)

- [ ] Summarize back 2–3 things you heard: *"What I'm taking away is X, Y, Z — does that sound right?"*
- [ ] Ask: *"Is there anything I didn't ask that you expected me to ask?"*
- [ ] Ask: *"If we got this to a point where it was actually useful to you, would you be willing to try it for a week and tell us what's still broken?"*
- [ ] Tell them next step: *"I'll synthesize this with a few other DSP owners and come back before we build anything new."*
- [ ] Send a follow-up thank-you within 24 hours — include your 2–3 key takeaways, so they know you listened

---

## After the Meeting — Synthesis Checklist

- [ ] Write up notes within an hour
- [ ] Flag: did they have any existing system for tracking actions, however informal? (Yes/No + what)
- [ ] Flag: what was their first reaction to "Recommended action" — helpful or condescending?
- [ ] Flag: did they reach for snooze unprompted, or not?
- [ ] Flag: which V2 priority did they pick, and what was their reasoning?
- [ ] Note any quote that directly confirms or challenges a hypothesis from the table below

### Hypothesis tracking — update after each session

| Hypothesis | Status | Key evidence |
|---|---|---|
| DSPs will log actions to close the loop | ? | |
| Weekly rhythm (Monday review) is primary use case | ? | |
| SMS deep link is the right interrupt channel | ? | |
| Batching 3+ alerts into one SMS is better than individual messages | ? | |
| Snooze is a real need, not just a nice-to-have | ? | |
| The playbook customization will be used | ? | |
| Per-driver playbook override needed (vs. fleet-level) | ? | |

*Status options: Confirmed / Challenged / Mixed / No data yet*

---

## Notes

**The questions in Section 1 (action tracking today) are the most important.** If DSP owners have no existing behavior around documenting coaching conversations — not even informal ones — then the action-logging feature is asking them to form a brand new habit. That has major implications for adoption and notification design, and may challenge the core V1 thesis more than any UX detail.

**Section 3, question 16** (helpful vs. telling you something you know) is the single question most likely to surface a strong opinion. Capture the exact words.

After 3+ sessions, use the hypothesis table above to: decide whether to promote the action log to a primary V2 feature, redesign the notification tiers, or descope the playbook editor in favor of shipping smarter defaults.

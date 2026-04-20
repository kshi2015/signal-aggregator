# Product Spec: Signal Aggregator V0 (US)

**Status:** Draft  
**Author:** Kevin Shi  
**Last updated:** April 2026  
**Audience:** Designer + Engineer — one doc, shared source of truth

---

## How to Read This Doc

| If you are... | Start here | Then go to |
|---|---|---|
| Designer | Problem, Users, User Stories, Flows, States | Notification Spec, Open Questions |
| Engineer | Problem, User Stories, Data Model, API Contracts, Notification Spec | WW Config, Open Questions |
| Both | Problem through User Stories | Your relevant sections |

---

## 1. Problem Statement

DSP owners manage driver safety across fragmented signal sources — hard-braking telemetry, customer complaints, on-road observations — each with its own system and notification logic. The result: important signals get buried, owners spend time stitching data instead of acting on it, and interventions happen too late.

Signal Aggregator V0 solves the **last mile of that problem**: not data aggregation (the backend already does that), but **turning aggregated signals into clear next actions** for the DSP owner.

The core insight: a score is not useful. A score with a recommended action and a way to log what you did about it is useful.

---

## 2. Users

**Primary: DSP Owner**
- Small business operator running 15–80 delivery drivers
- Not in front of a screen all day — on the floor, in meetings, sometimes in a van
- Owns driver safety but may delegate day-to-day to an ops manager
- Weekly rhythm: reviews drivers before routes launch Monday or Tuesday
- Receives alerts today but acts on them inconsistently — no system to track what was done

**Secondary: DSP Ops Manager** *(V0 assumption: same person as owner for small DSPs)*
- May handle the weekly review on behalf of the owner
- Needs the same action queue view, potentially with limited ability to change playbook config

**Out of scope for V0:** Amazon Last Mile operations team, multi-user roles with different permissions

---

## 3. Jobs to Be Done

These are hypotheses to validate in DSP discovery interviews. Do not treat as confirmed requirements.

| Job | Frequency | Current solution | Pain |
|---|---|---|---|
| Know which drivers need attention this week | Weekly | Manual review across 3+ tools | Time-consuming, inconsistent |
| Prepare for a weekly driver check-in | Weekly | Memory + spreadsheet | No audit trail, things get missed |
| Act on an urgent alert (threshold crossed) | Rare, unpredictable | Email/SMS from Amazon | Alert arrives, no guidance on what to do |
| Track that a driver issue was addressed | Ad hoc | None | No closed loop — same drivers flagged repeatedly |
| Know if an intervention worked | Rarely done | None | No feedback on whether coaching changed behavior |

---

## 4. User Stories

### Must-have for V0

**US-01** — As a DSP owner, I want to see which of my drivers need attention today so I don't have to check multiple tools to figure out where to start.

**US-02** — As a DSP owner, I want to know the recommended action for each flagged driver so I don't have to decide from scratch what to do.

**US-03** — As a DSP owner, I want to log that I took action on a driver so I have a record and the system knows the issue is being handled.

**US-04** — As a DSP owner, I want to receive an alert when a driver crosses the severity threshold so I can act the same day, not at my next weekly review.

**US-05** — As a DSP owner, I want a weekly digest before my Monday review so I can walk in prepared without opening the app.

### Should-have for V0

**US-06** — As a DSP owner, I want to configure what the recommended action is for each signal type so the app reflects how I actually run my operation.

**US-07** — As a DSP owner, I want to snooze a flagged driver for a few days if I've already spoken to them and am monitoring the situation.

**US-08** — As a DSP owner, I want to see drivers whose scores improved after I took action so I know whether my interventions are working.

### Out of scope for V0

- Multi-user access / role-based permissions
- Dispute workflow (score correction)
- Historical trend charts
- Integration with external coaching or HR systems
- Non-English language support

---

## 5. UX Flows

### Flow 1 — Weekly Review (primary use case)

```
DSP owner opens app Monday morning
  → Lands on Action Queue (default view)
  → Sees drivers sorted by: [Needs Action] → [Watching] → [Resolved this week]
  → Taps a "Needs Action" driver
  → Sees: signal that triggered flag + recommended action from their playbook
  → Taps "Log action"
  → Enters optional note, confirms
  → Driver moves to "In Progress" in the queue
  → At end of week, resolved items roll off into weekly history
```

### Flow 2 — Urgent Alert Response

```
DSP owner receives SMS: "Driver Maria S. score: 11 — tap to review"
  → Taps deep link in SMS
  → App opens directly to Maria's driver detail view
  → Sees: threshold crossed, signals that contributed, recommended action
  → Logs action or snoozes
  → Returns to queue
```

### Flow 3 — Playbook Configuration (onboarding + edit)

```
First login:
  → Prompted to configure Action Playbook before seeing queue
  → For each signal type + severity combo, shown a default recommended action
  → Can edit text or accept default
  → Playbook saved, queue unlocked

Edit later:
  → Settings → Action Playbook
  → Same interface, editable at any time
  → Changes apply to future flagged items, not retroactively
```

---

## 6. Screen States

Every screen needs a defined state for each condition below. Designer owns the visual treatment; engineer needs to know all states exist before building.

### Action Queue

| State | Condition | What to show |
|---|---|---|
| Default | Items exist | Prioritized list: Needs Action → Watching → Resolved |
| Empty — all clear | No items in any state | Positive message: "No drivers need attention this week" + last updated timestamp |
| Empty — no data yet | New DSP, no signals ingested | Onboarding prompt to configure playbook + confirm drivers are mapped |
| Loading | API call in flight | Skeleton loader, not spinner |
| Error | API unreachable | "Unable to load — last updated [timestamp]" with retry option |

### Driver Detail

| State | Condition | What to show |
|---|---|---|
| Default | Driver has signals | Signal history, recommended action, action log |
| No history | Driver exists but no signals in 7-day window | "No signals in the last 7 days" |
| Resolved | Action logged, score below threshold | Summary of what was logged + score trend |

### Notifications (SMS + Email)

Defined in Section 8.

---

## 7. Action Playbook — Configuration Model

The playbook maps signal type + severity to a default recommended action. It is configured per DSP and stored server-side so it persists across devices.

### Default playbook (pre-populated at onboarding)

| Signal type | Severity | Default recommended action |
|---|---|---|
| customer_complaint | high | 1:1 conversation with driver within 24 hours |
| customer_complaint | medium | Address at next weekly check-in |
| customer_complaint | low | Monitor — flag if pattern continues |
| on_road_observation | high | Review incident details + schedule coaching |
| on_road_observation | medium | Discuss at next check-in |
| on_road_observation | low | Log for awareness — no action required |
| hard_braking | high | Review dashcam footage + schedule defensive driving |
| hard_braking | medium | Monitor — no action unless pattern in 7 days |
| hard_braking | low | No action |

DSP can edit any row. Free text field, max 120 characters.

### Playbook behavior rules

- Recommended action shown in queue is determined by the **highest-severity signal** that contributed to the threshold crossing
- If multiple signal types contributed, show the highest-weight signal (customer_complaint > on_road_observation > hard_braking)
- Playbook changes apply to newly flagged items only — do not retroactively change recommended action on items already in queue

---

## 8. Notification Spec

### Three-tier model

**Tier 1 — Interrupt (act now)**

| Property | Value |
|---|---|
| Trigger | Driver score crosses threshold (default: 9) for the first time |
| Channel | SMS (V0 US default) |
| Timing | Immediate, any time of day |
| Quiet hours | None for threshold alerts — urgency overrides quiet hours |
| Suppression | Does not re-fire for same driver until score drops below threshold and crosses again |
| Batching | If 3+ drivers cross threshold same day: one batched SMS, not individual messages |
| Deep link | Links directly to driver detail view in app |

SMS format:
```
[Signal Aggregator] Driver [First name L.] score: [N]
Top signal: [signal_type] ([severity]) — [today/this week]
Review: [deep link]
Reply STOP to unsubscribe
```

**Tier 2 — Nudge (watch this)**

| Property | Value |
|---|---|
| Trigger | Driver score enters warning band (default: 6–8, configurable) |
| Channel | Email |
| Timing | Batched into next morning's send (7:30am local time), not immediate |
| Suppression | Once per driver per entry into warning band. Suppressed if driver already at Tier 1. |
| Batching | All warning-band drivers in one email, never individual emails per driver |

**Tier 3 — Digest (prepare for your review)**

| Property | Value |
|---|---|
| Trigger | Scheduled — Monday 7:30am local time (configurable day + time) |
| Channel | Email |
| Content | Drivers above threshold, drivers in warning band, score improvements, resolved items |
| Opt-out | Independent of Tier 1 and Tier 2 — turning off digest does not affect alerts |

### Notification preference center (minimum viable)

```
Notification preferences

Threshold alerts (SMS)       [ ON / OFF ]
Warning band nudges (email)  [ ON / OFF ]
Weekly digest (email)        [ ON / OFF ]
  Send on:  [ Mon ]  Tue  Wed  Thu  Fri
  Send at:  [ 7:30am ]  ▾  (local time)
Quiet hours                  8:00pm – 7:00am  [ edit ]
```

Default state for new DSP: all ON. User can reduce to any combination.
A single global unsubscribe (Reply STOP to SMS) turns off SMS only, not email.

---

## 9. Data Model Additions

*Additions to existing tables are marked. New tables are new.*

### New: `signal-aggregator-driver-actions` (DynamoDB)

Tracks the lifecycle of a driver safety issue from flag to resolution.

| Attribute | Type | Notes |
|---|---|---|
| `action_id` | String (PK) | UUID v4 |
| `driver_id` | String (SK) | FK to driver summary |
| `dsp_id` | String | Resolved at write time from driver→DSP map |
| `trigger_event_id` | String | FK to the S3 raw event that triggered the flag |
| `recommended_action` | String | From DSP playbook at time of flag — snapshot, not live |
| `status` | String | `needs_action` \| `in_progress` \| `snoozed` \| `resolved` |
| `snoozed_until` | String | ISO 8601, present only when status = snoozed |
| `action_note` | String | Free text logged by DSP owner |
| `logged_by` | String | User ID (V0: dsp_id, V1: individual user) |
| `logged_at` | String | ISO 8601 |
| `created_at` | String | ISO 8601 |

GSI: `dsp_id` + `status` — supports querying "all open items for this DSP"

### New: `signal-aggregator-playbook` (DynamoDB)

Stores per-DSP action playbook.

| Attribute | Type | Notes |
|---|---|---|
| `dsp_id` | String (PK) | |
| `signal_type` | String (SK) | Composite: `{signal_type}#{severity}` |
| `recommended_action` | String | DSP-configured text, max 120 chars |
| `updated_at` | String | ISO 8601 |

### New: `signal-aggregator-notification-prefs` (DynamoDB)

Stores per-DSP notification preferences.

| Attribute | Type | Notes |
|---|---|---|
| `dsp_id` | String (PK) | |
| `tier1_sms_enabled` | Boolean | Default: true |
| `tier2_email_enabled` | Boolean | Default: true |
| `tier3_digest_enabled` | Boolean | Default: true |
| `digest_day` | String | `MON` \| `TUE` \| ... Default: `MON` |
| `digest_time_local` | String | HH:MM, 24h. Default: `07:30` |
| `quiet_hours_start` | String | HH:MM local. Default: `20:00` |
| `quiet_hours_end` | String | HH:MM local. Default: `07:00` |
| `timezone` | String | IANA timezone. Default: inferred from DSP region at onboarding |
| `phone` | String | E.164 format for SMS |
| `email` | String | For digest + nudge |

### Additions to existing: `signal-aggregator-driver-summary`

Add the following attributes to the existing driver summary record:

| Attribute | Type | Notes |
|---|---|---|
| `action_status` | String | Latest action status for this driver — denormalized from driver_actions for fast queue rendering |
| `notified_at` | String | ISO 8601 — timestamp of last Tier 1 notification. Used for suppression logic. |
| `notification_threshold_at` | Number | Score value when last notification fired. Used to detect drop-and-recross. |

---

## 10. API Contract Additions

### Extended: `GET /summary`

Add action state to existing response.

**Response (driver list):**
```json
{
  "drivers": [
    {
      "driver_id": "driver-001",
      "dsp_id": "dsp-123",
      "score": 11,
      "action_status": "needs_action",
      "recommended_action": "1:1 conversation with driver within 24 hours",
      "top_signal": {
        "signal_type": "customer_complaint",
        "severity": "high",
        "timestamp": "2026-04-20T09:00:00Z"
      },
      "last_updated": "2026-04-20T09:01:22Z"
    }
  ]
}
```

### New: `POST /actions`

Log an action taken on a driver.

**Request:**
```json
{
  "driver_id": "driver-001",
  "action": "in_progress",
  "note": "Had 1:1 with Maria — she was aware of the complaint and acknowledged it. Will monitor this week.",
  "snooze_until": null
}
```

**Response:**
```json
{
  "action_id": "uuid-v4",
  "driver_id": "driver-001",
  "status": "in_progress",
  "logged_at": "2026-04-20T11:32:00Z"
}
```

`action` enum: `in_progress` | `resolved` | `snoozed`
`snooze_until` required when action = `snoozed`. ISO 8601. Max 7 days from now.

### New: `GET /playbook`

Returns the DSP's configured action playbook.

**Response:**
```json
{
  "dsp_id": "dsp-123",
  "playbook": [
    {
      "signal_type": "customer_complaint",
      "severity": "high",
      "recommended_action": "1:1 conversation with driver within 24 hours"
    }
  ]
}
```

### New: `PUT /playbook`

Updates one or more playbook entries.

**Request:**
```json
{
  "updates": [
    {
      "signal_type": "customer_complaint",
      "severity": "high",
      "recommended_action": "Call driver same day + log in Mentor"
    }
  ]
}
```

---

## 11. WW Configuration — V0 Isolation Points

These are decisions made now in V0 that prevent rewrites later.

**Notification dispatch abstraction**
The notification layer accepts a typed event (tier, recipient_id, payload) and resolves channel internally. V0 resolves to SMS (US) + SES email. Future regions resolve to WhatsApp, Line, KakaoTalk, etc. without changing the event schema.

**Config hierarchy**
All thresholds, weights, and defaults follow: `global → region → dsp`. The `region` key exists in DynamoDB config from V0 even if only `us-east-1` is populated. Adding a new region is additive.

**Timezone-aware scheduling**
Digest and nudge timing use IANA timezone strings stored per-DSP, not UTC offsets. Daylight saving is handled by the scheduling layer, not by stored offsets.

**Text externalization**
All user-facing strings in notification payloads and playbook defaults are loaded from a locale file, not hardcoded. V0 ships one locale (`en-US`). Adding `pt-BR` or `ja-JP` requires a new locale file, not code changes.

**Opt-in defaults by region**
V0 US defaults all notifications ON (opt-out model). EU region will require opt-in model — the preference center must support per-region default states, configurable at the region level in the config table.

---

## 12. Success Metrics

### Leading indicators (measurable in V0)
- % of Tier 1 alerts that result in a logged action within 48 hours
- Weekly digest open rate
- Playbook configuration rate at onboarding (did DSP customize their defaults?)

### Lagging indicators (require 4+ weeks of data)
- Week-over-week score change for drivers who received logged interventions vs. those who did not
- Repeat threshold crossings per driver (lower = interventions are working)
- Unsubscribe rate from SMS alerts (proxy for notification fatigue)

### Anti-metrics (watch for these going wrong)
- > 2 Tier 1 SMS per DSP per week on average → batching or suppression not working
- < 20% action logging rate → queue is being ignored, not the right UX model
- Playbook abandoned at onboarding → defaults are wrong or flow is too long

---

## 13. Out of Scope — V0

- Auth and multi-tenancy (V0 uses dsp_id as a URL param — no login)
- Multi-user roles within a DSP
- Dispute / score correction workflow
- Historical trend charts
- Integration with external coaching platforms (Mentor, etc.)
- Non-English language support
- Android / iOS native app (PWA only)

---

## 14. Open Questions

These need answers before design or engineering begins work on the relevant section.

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | What device do DSP owners primarily use for this type of review? | Kevin — validate in discovery interviews | Mobile-first vs. desktop-first design decision |
| 2 | Do DSPs want a nudge notification, or does it add noise? | Kevin — validate in discovery interviews | Whether to build Tier 2 at all |
| 3 | What is the right warning band lower bound — 6? Higher? | Kevin — validate threshold sensitivity with DSPs | Tier 2 trigger config |
| 4 | Should snooze be capped at 7 days or configurable? | Kevin | Snooze UX + data model |
| 5 | Does logging an action suppress future Tier 1 alerts on the same driver? | Kevin | Suppression logic in aggregate Lambda |
| 6 | What happens to action records after a driver is no longer associated with a DSP? | Engineering | Data retention + driver_actions table design |

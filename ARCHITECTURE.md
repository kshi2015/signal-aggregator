# Signal Aggregator — Architecture

## Overview

Signal Aggregator is an event-driven, serverless pipeline built on AWS. It ingests driver safety signals, aggregates them into a per-driver severity score over a rolling 7-day window, notifies DSP owners when a score crosses a threshold, and exposes a read API consumed by a Progressive Web App (PWA).

The V0 display model is an **action queue**, not a dashboard. Rather than showing scores, the UI surfaces the recommended action for each flagged driver and tracks whether the DSP owner has responded. The architecture reflects this: three new DynamoDB tables (driver actions, action playbook, notification preferences) sit alongside the existing pipeline and are served by two new API endpoints (`POST /actions`, `GET|PUT /playbook`).

---

## System Diagram

```mermaid
flowchart TD
    subgraph Ingest
        A(["POST /ingest"])
        AG1["API Gateway"]
        IL["Ingest Lambda"]
        A --> AG1 --> IL
    end

    subgraph Storage
        S3[("S3\nRaw Events")]
        DM[("DynamoDB\nDriver → DSP Map")]
        DS[("DynamoDB\nDriver Summary")]
        DC[("DynamoDB\nConfig\n(weights, threshold)")]
        DA[("DynamoDB\nDriver Actions")]
        PB[("DynamoDB\nAction Playbook")]
        NP[("DynamoDB\nNotification Prefs")]
    end

    subgraph Aggregate
        AL["Aggregation Lambda"]
    end

    subgraph Notify
        SNS["SNS Topic"]
        SES["SES\n(digest + nudge email)"]
        DSP(["DSP Owner\nSMS / Email"])
        SNS --> DSP
        SES --> DSP
    end

    subgraph Read
        B(["GET /summary"])
        C(["POST /actions"])
        D(["GET|PUT /playbook"])
        AG2["API Gateway"]
        RL["Read Lambda"]
        AL2["Actions Lambda"]
        B --> AG2 --> RL
        C --> AG2 --> AL2
        D --> AG2 --> AL2
    end

    subgraph UI["UI (PWA)"]
        CF["CloudFront"]
        SS[("S3\nPWA"))"]
        Browser(["DSP Owner\nBrowser / Mobile"])
        Browser --> CF --> SS
        SS --> B
        SS --> C
        SS --> D
    end

    IL -- "1. write raw event" --> S3
    IL -- "2. lookup dsp_id" --> DM
    S3 -- "S3 event notification" --> AL
    AL -- "read weights + threshold" --> DC
    AL -- "update score + action_status" --> DS
    AL -- "score ≥ 9 — check notified_at" --> SNS
    AL -- "score in warning band" --> SES
    RL -- "read summary + action_status" --> DS
    AL2 -- "read/write action lifecycle" --> DA
    AL2 -- "read/write playbook" --> PB
    AL2 -- "read/write prefs" --> NP
    AL -- "read notification prefs" --> NP
```

---

## Flow Descriptions

### 1. Ingest
A caller POSTs a JSON event to the ingest API. The Ingest Lambda writes the raw event to S3 (partitioned by date/hour) and resolves `dsp_id` from `driver_id` via the Driver→DSP mapping table. The raw event includes `event_id` for idempotency.

### 2. Aggregate
The S3 write triggers an S3 event notification that invokes the Aggregation Lambda. It reads signal weights and the notification threshold from the config table, recomputes the driver's rolling 7-day severity score (weighted sum: signal_type weight × severity multiplier), and writes the updated summary to the Driver Summary table.

### 3. Notify
If the recomputed score reaches **9 or above**, the Aggregation Lambda publishes to the SNS topic. SNS delivers a notification to the DSP owner via email or SMS.

### 4. Read
A GET request to the read API invokes the Read Lambda, which fetches the current driver summary from DynamoDB — including action state — and returns it as JSON. The PWA calls this endpoint on load to populate the action queue.

### 5. Actions
`POST /actions` logs a DSP owner's response to a flagged driver (in_progress, resolved, or snoozed). `GET /playbook` and `PUT /playbook` read and update the DSP's configured action playbook — the per-signal-type recommended actions shown in the UI. Both routes are served by an Actions Lambda that reads and writes the driver_actions, playbook, and notification_prefs tables.

### 6. Notify
Three-tier notification model:
- **Tier 1 (Interrupt):** Aggregation Lambda publishes to SNS when a driver score crosses the threshold for the first time. Suppressed if `notified_at` is set and score has not dropped below threshold since. Batched if multiple drivers cross threshold on the same day.
- **Tier 2 (Nudge):** Aggregation Lambda publishes to SES when a driver enters the warning band (score ≥ 6, configurable). Batched into next morning's send — never sent per-driver in real time.
- **Tier 3 (Digest):** Scheduled weekly email via SES. Covers all drivers above threshold, in warning band, and resolved that week.

### 7. UI (PWA)
A Progressive Web App served from S3 via CloudFront. Mobile-first. Renders an action queue — drivers sorted by status (Needs Action → Watching → Resolved) — not a score dashboard. Each item shows the recommended action from the DSP's playbook and a control to log action, snooze, or dispute.

---

## Data Stores

| Store | Type | Contents |
|---|---|---|
| Raw Events | S3 | One JSON file per event: `events/YYYY/MM/DD/HH/{event_id}.json` |
| Driver → DSP Map | DynamoDB | PK: `driver_id` → `dsp_id` |
| Driver Summary | DynamoDB | PK: `driver_id` → severity score, event counts by type, `action_status`, `notified_at`, last updated |
| Config | DynamoDB | Global threshold (9), signal weights, severity multipliers. Key hierarchy: `global → region → dsp` |
| Driver Actions | DynamoDB | PK: `action_id`, SK: `driver_id` → action lifecycle (needs_action / in_progress / snoozed / resolved), notes, timestamps. GSI on `dsp_id + status` for queue queries. |
| Action Playbook | DynamoDB | PK: `dsp_id`, SK: `signal_type#severity` → DSP-configured recommended action text |
| Notification Prefs | DynamoDB | PK: `dsp_id` → per-tier enable flags, digest schedule, quiet hours, timezone, contact info |

---

## Severity Score Formula

```
score = Σ ( signal_type_weight × severity_multiplier )
        for all events in the last 7 days

signal_type_weight:   hard_braking=1, on_road_observation=2, customer_complaint=3
severity_multiplier:  low=1, medium=2, high=3
notification fires when score ≥ 9
```

**Example:** One high-severity customer complaint = 3 × 3 = **9** → notification fires immediately.

---

## Out of Scope (v0)

- Auth on any API endpoint (`dsp_id` passed as URL param — no login)
- Multi-user roles within a DSP
- Per-DSP threshold configuration (single global threshold; config hierarchy is in place but only `global` is populated)
- Score decay within the 7-day window
- Historical trend queries
- Multiple ingest sources
- Dispute / score correction workflow (designed, not built)
- Non-English language support (locale file structure in place; `en-US` only)
- Native mobile app (PWA only)

---

## v1 Candidates

- Auth: Amazon Cognito with per-DSP scoped reads (blocks real DSP access)
- Multi-user roles within a DSP (owner vs. ops manager)
- Per-DSP threshold configuration (config hierarchy already supports it)
- Dispute / score correction workflow
- Idempotency on ingest using `event_id` conditional writes
- SQS between S3 events and Aggregation Lambda (eliminates silent event loss)
- Atomic score increments via DynamoDB `ADD` (eliminates race condition)

## v2 Candidates

- Amazon Managed Grafana for real-time fleet-level view (complements action queue, doesn't replace it)
- Configurable rolling window duration (currently hardcoded at 7 days)
- QuickSight for historical trend analysis once S3 data accumulates
- SAML/SSO for enterprise DSP access
- WhatsApp / regional channel support (notification dispatch abstraction already in place)
- Score decay weighting (recent events weighted more heavily within the window)
- WW region expansion (config hierarchy and locale structure already in place)

---

## Known Gaps at Scale

These are not blockers for v1 (a learning project at low volume), but would need to be addressed before production.

### 1. Race condition on driver summary writes — Critical
The Aggregation Lambda does a read-modify-write on the driver summary. At concurrent volume, multiple Lambda invocations for the same `driver_id` run simultaneously — last write wins and intermediate updates are lost, producing incorrect scores.

**Fix:** Replace read-modify-write with DynamoDB atomic `ADD` operations on score and event count attributes. No read needed; DynamoDB handles the increment atomically.

### 2. SNS notification storm — High
No deduplication on notifications. Once a driver's score crosses 9 and stays there, every subsequent event re-triggers an SNS publish. DSP owners receive repeated alerts for the same driver, turning signal into noise.

**Fix:** Add a `notified_at` timestamp to the driver summary. Suppress re-notification unless the score has dropped below threshold and crossed it again, or a configurable cooldown window has elapsed.

### 3. Silent event loss under load — High
S3 event notifications invoke Lambda asynchronously with 3 retries on failure. If Lambda hits its concurrency limit or DynamoDB throttles, retries exhaust and the event is silently dropped — a safety signal is permanently missed with no record.

**Fix:** Insert an SQS queue between S3 events and the Aggregation Lambda. SQS holds events until capacity is available; nothing is dropped, and the queue depth becomes a visible metric for backpressure.

### 4. Config table read on every invocation — Low
Weights and threshold are read from DynamoDB on every Aggregation Lambda invocation. The config rarely changes; this is unnecessary latency and cost at scale.

**Fix:** Cache config in Lambda memory with a short TTL (e.g., 60 seconds). One read warms the cache; subsequent invocations on the same instance use the cached value.

### 5. Cold start amplification under burst traffic — Low
Burst traffic causes Lambda to scale out rapidly. Simultaneous cold starts add 200–500ms of processing delay per new instance, creating a latency spike at the worst possible moment.

**Fix:** Provisioned concurrency on the Aggregation Lambda eliminates cold starts at the cost of a fixed hourly charge. Acceptable in production; unnecessary for v1.

# Signal Aggregator

A serverless event-driven pipeline that ingests driver safety signals, computes per-driver severity scores, and surfaces them as an action queue for Delivery Service Partner (DSP) owners — so they know not just which drivers need attention, but what to do about it.

Built as a hands-on AWS learning project with a WW-configurable UX design layer on top.

---

## Project Docs

| Doc | What it covers |
|---|---|
| [PRFAQ.md](PRFAQ.md) | Product spec and customer FAQ written before any code |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System diagram, data model, flow descriptions, scale tradeoffs |
| [PRODUCT_SPEC_V0.md](PRODUCT_SPEC_V0.md) | V0 product spec: user stories, UX flows, action playbook, notification tiers, API contracts, WW config |
| [DSP_DISCOVERY.md](DSP_DISCOVERY.md) | Discovery interview guide for DSP customer research |
| [LEARNINGS.md](LEARNINGS.md) | What the build taught me — technical and product |

---

## Architecture

```
POST /ingest    → API Gateway → Ingest Lambda → S3 (raw events)
                                                      ↓ S3 event notification
                                Aggregation Lambda → DynamoDB (driver summary)
                                                   → SNS (Tier 1 alert, score ≥ 9)
                                                   → SES (Tier 2 nudge, warning band)

GET  /summary   → API Gateway → Read Lambda    → DynamoDB → action queue data
POST /actions   → API Gateway → Actions Lambda → DynamoDB (driver_actions)
GET|PUT /playbook              → Actions Lambda → DynamoDB (playbook config)

Scheduled                      → SES (Tier 3 weekly digest)
```

Full architecture with data model and scale tradeoffs: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## AWS Resources

| Resource | Name |
|---|---|
| API Gateway (HTTP) | `signal-aggregator` |
| Lambda — ingest | `signal-aggregator-ingest` |
| Lambda — aggregate | `signal-aggregator-aggregate` |
| Lambda — read | `signal-aggregator-read` |
| S3 — raw events | `signal-aggregator-raw-{account_id}` |
| DynamoDB — driver → DSP map | `signal-aggregator-driver-map` |
| DynamoDB — driver summary | `signal-aggregator-driver-summary` |
| DynamoDB — config | `signal-aggregator-config` |
| DynamoDB — driver actions | `signal-aggregator-driver-actions` *(specced, not yet built)* |
| DynamoDB — action playbook | `signal-aggregator-playbook` *(specced, not yet built)* |
| DynamoDB — notification prefs | `signal-aggregator-notification-prefs` *(specced, not yet built)* |
| SNS topic | `signal-aggregator-notifications` |

---

## Signal Schema

```json
{
  "driver_id":   "string",
  "signal_type": "hard_braking | customer_complaint | on_road_observation",
  "severity":    "low | medium | high",
  "timestamp":   "ISO 8601",
  "source":      "string",
  "event_id":    "uuid (optional — generated if omitted)"
}
```

---

## Severity Score

Scores are computed as a weighted sum over a rolling 7-day window:

| Signal type | Weight |
|---|---|
| `hard_braking` | 1 |
| `on_road_observation` | 2 |
| `customer_complaint` | 3 |

Severity multipliers: `low=1`, `medium=2`, `high=3`

**Notification threshold: score ≥ 9** — a single high-severity customer complaint crosses this immediately (3 × 3 = 9).

---

## Notification Tiers

| Tier | Trigger | Channel | Frequency |
|---|---|---|---|
| Interrupt | Score crosses threshold (≥ 9) | SMS | Once per threshold crossing, batched if multiple drivers |
| Nudge | Score enters warning band (≥ 6) | Email | Once per entry into band, batched next morning |
| Digest | Scheduled | Email | Weekly, configurable day + time |

Full notification spec including suppression logic, preference center, and WW config: [PRODUCT_SPEC_V0.md](PRODUCT_SPEC_V0.md#8-notification-spec)

---

## Try It

**Post a safety event:**
```bash
curl -X POST https://co06fw6bm2.execute-api.us-east-1.amazonaws.com/ \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id":   "driver-001",
    "signal_type": "customer_complaint",
    "severity":    "high",
    "timestamp":   "2026-04-14T05:00:00Z",
    "source":      "customer-feedback-system"
  }'
```

**Read all drivers ranked by severity score:**
```bash
curl https://co06fw6bm2.execute-api.us-east-1.amazonaws.com/summary
```

**Drill into a specific driver:**
```bash
curl "https://co06fw6bm2.execute-api.us-east-1.amazonaws.com/summary?driver_id=driver-001"
```

**Validation — bad signal type returns 400:**
```bash
curl -X POST https://co06fw6bm2.execute-api.us-east-1.amazonaws.com/ \
  -H "Content-Type: application/json" \
  -d '{"driver_id":"d1","signal_type":"made_up","severity":"low","timestamp":"2026-04-14T05:00:00Z","source":"test"}'
```

---

## Source Layout

```
src/
  ingest/    handler.py        — API Gateway → S3 write
  aggregate/ handler.py        — S3 event → DynamoDB score update + SNS/SES
  read/      handler.py        — DynamoDB → action queue data

PRFAQ.md                       — product spec written before any code
ARCHITECTURE.md                — system diagram, data model, scale gaps
PRODUCT_SPEC_V0.md             — full V0 spec: UX flows, data model, API contracts, WW config
DSP_DISCOVERY.md               — customer discovery interview guide
LEARNINGS.md                   — what this build taught me
```

---

## What's Deliberately Missing

No auth, no CI/CD, no tests, no cost optimization. The Actions Lambda, PWA frontend, and three new DynamoDB tables are specced in [PRODUCT_SPEC_V0.md](PRODUCT_SPEC_V0.md) but not yet built — customer discovery interviews ([DSP_DISCOVERY.md](DSP_DISCOVERY.md)) come first. See [LEARNINGS.md](LEARNINGS.md) for what I'd add before putting this in production.

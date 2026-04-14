# Signal Aggregator

A serverless event-driven pipeline that ingests driver safety signals, computes per-driver severity scores, and notifies DSP owners when a driver crosses a threshold.

Built as a hands-on AWS learning project — see [PRFAQ.md](PRFAQ.md) for the product spec and [LEARNINGS.md](LEARNINGS.md) for what the build taught me.

---

## Architecture

```
POST /ingest   → API Gateway → Ingest Lambda → S3 (raw events)
                                                     ↓ S3 event notification
                               Aggregation Lambda → DynamoDB (driver events + summary)
                                                  → SNS if score ≥ 9

GET /summary   → API Gateway → Read Lambda → DynamoDB → ranked driver list
GET /summary?driver_id=X      → summary + recent event history
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
| S3 bucket | `signal-aggregator-raw-{account_id}` |
| DynamoDB — raw events | `signal-aggregator-driver-events` |
| DynamoDB — driver summary | `signal-aggregator-driver-summary` |
| DynamoDB — config | `signal-aggregator-config` |
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

**SNS notification fires when score ≥ 9** — a single high-severity customer complaint crosses this immediately (3 × 3 = 9).

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
  ingest/    handler.py   — API Gateway → S3 write
  aggregate/ handler.py   — S3 event → DynamoDB score update + SNS
  read/      handler.py   — DynamoDB → ranked driver list / driver detail
PRFAQ.md                  — product spec written before any code
ARCHITECTURE.md           — system diagram, data model, scale gaps
LEARNINGS.md              — what this build taught me
```

---

## What's Deliberately Missing

No auth, no CI/CD, no tests, no cost optimization. This is a learning project — see [LEARNINGS.md](LEARNINGS.md) for what I'd add before putting this in production.

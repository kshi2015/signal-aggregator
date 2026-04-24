# Signal Aggregator

A serverless event-driven pipeline that ingests driver safety signals, computes per-driver severity scores, and surfaces them as an action queue for Delivery Service Partner (DSP) owners — so they know not just which drivers need attention, but what to do about it.

Built as a hands-on AWS learning project with a WW-configurable UX design layer on top.

---

## Project Docs

| Doc | What it covers |
|---|---|
| [PRFAQ.md](PRFAQ.md) | Product spec and customer FAQ written before any code |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System diagram, auth architecture, data model, flow descriptions, scale tradeoffs |
| [PRODUCT_SPEC_V0.md](PRODUCT_SPEC_V0.md) | V0 product spec: user stories, UX flows, action playbook, notification tiers, API contracts, WW config |
| [DSP_DISCOVERY.md](DSP_DISCOVERY.md) | Discovery interview guide for DSP customer research |
| [LEARNINGS.md](LEARNINGS.md) | What the build taught me — technical and product |

## Design

| Artifact | Link |
|---|---|
| Figma — screens & flows | [Signal Aggregator on Figma](https://www.figma.com/design/Z2Pvr8JVFZoyTRYuYtU3iD/Signal-Aggregator?node-id=5-168&t=96N2YyFp872MEKYl-1) |
| HTML mockup (local) | [design/index.html](design/index.html) — rendered DSP dashboard with architecture and screen diagrams |
| Architecture diagram | [design/architecture.svg](design/architecture.svg) |
| Screen designs | [design/screens.svg](design/screens.svg) |

---

## Architecture

```
POST /ingest (x-api-key) → API Gateway → Ingest Authorizer Lambda → Secrets Manager
                                       → Ingest Lambda → S3 (raw events)
                                                              ↓ S3 event notification
                                         Aggregation Lambda → DynamoDB (driver summary + dsp_id)
                                                           → SNS (Tier 1 alert, score ≥ 9)
                                                           → SES (Tier 2 nudge, warning band)

GET  /summary    (Bearer JWT) → API Gateway → JWT Authorizer → Cognito
                                           → Read Lambda    → DynamoDB (scoped to dsp_id)
POST /actions    (Bearer JWT) → API Gateway → JWT Authorizer → Cognito
GET|PUT /playbook(Bearer JWT) →            → Actions Lambda → DynamoDB

Scheduled                                  → SES (Tier 3 weekly digest)
```

Full architecture with auth design, data model, and scale tradeoffs: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## AWS Resources

| Resource | Name / ID |
|---|---|
| API Gateway (HTTP API) | `signal-aggregator-api` — `4u3d4nahch.execute-api.us-east-1.amazonaws.com` |
| Cognito User Pool | `signal-aggregator-users` — `us-east-1_fzbbl1fFE` |
| Cognito App Client | `signal-aggregator-pwa` — `2mibhnvakr03n0raa2qvgo3ies` |
| Lambda — ingest | `signal-aggregator-ingest` |
| Lambda — ingest authorizer | `signal-aggregator-ingest-authorizer` |
| Lambda — aggregate | `signal-aggregator-aggregate` |
| Lambda — read | `signal-aggregator-read` |
| Lambda — actions | `signal-aggregator-actions` |
| S3 — raw events | `signal-aggregator-raw-{account_id}` |
| DynamoDB — driver summary | `signal-aggregator-driver-summary` |
| DynamoDB — driver events | `signal-aggregator-driver-events` |
| DynamoDB — config | `signal-aggregator-config` |
| DynamoDB — driver actions | `signal-aggregator-driver-actions` |
| DynamoDB — action playbook | `signal-aggregator-playbook` |
| DynamoDB — notification prefs | `signal-aggregator-notification-prefs` |
| Secrets Manager — ingest key | `signal-aggregator/ingest-api-key` |
| SNS topic | `signal-aggregator-notifications` |

---

## Signal Schema

```json
{
  "driver_id":   "string",
  "dsp_id":      "string",
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

**Step 1 — Get a JWT token (DSP owner auth):**
```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 2mibhnvakr03n0raa2qvgo3ies \
  --auth-parameters USERNAME=dsp001@example.com,PASSWORD="SignalAgg001!"

# Copy the IdToken from the response
TOKEN=<IdToken>
```

**Step 2 — Post a safety event (internal service, requires API key):**
```bash
# Retrieve the key from Secrets Manager
INGEST_KEY=$(aws secretsmanager get-secret-value \
  --secret-id signal-aggregator/ingest-api-key \
  --query 'SecretString' --output text)

curl -X POST https://4u3d4nahch.execute-api.us-east-1.amazonaws.com/prod/ingest \
  -H "x-api-key: $INGEST_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id":   "driver-001",
    "dsp_id":      "dsp-001",
    "signal_type": "customer_complaint",
    "severity":    "high",
    "timestamp":   "2026-04-23T10:00:00Z",
    "source":      "customer-feedback-system"
  }'
```

**Step 3 — Read the action queue (scoped to your DSP):**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://4u3d4nahch.execute-api.us-east-1.amazonaws.com/prod/summary
```

**Step 4 — Log an action on a flagged driver:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"driver_id":"driver-001","action":"in_progress","note":"Had 1:1 — monitoring this week."}' \
  https://4u3d4nahch.execute-api.us-east-1.amazonaws.com/prod/actions
```

**Step 5 — View and customise the action playbook:**
```bash
# View current playbook (defaults if not yet configured)
curl -H "Authorization: Bearer $TOKEN" \
  https://4u3d4nahch.execute-api.us-east-1.amazonaws.com/prod/playbook

# Customise one entry
curl -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"updates":[{"signal_type":"customer_complaint","severity":"high","recommended_action":"Call driver same day + document in Mentor"}]}' \
  https://4u3d4nahch.execute-api.us-east-1.amazonaws.com/prod/playbook
```

**Auth validation — no token returns 401, wrong ingest key returns 403:**
```bash
curl https://4u3d4nahch.execute-api.us-east-1.amazonaws.com/prod/summary
# → {"message":"Unauthorized"}

curl -X POST -H "x-api-key: wrong" \
  https://4u3d4nahch.execute-api.us-east-1.amazonaws.com/prod/ingest \
  -d '{}'
# → {"message":"Forbidden"}
```

---

## Source Layout

```
src/
  ingest/            handler.py   — validates event + writes to S3
  ingest_authorizer/ handler.py   — validates x-api-key against Secrets Manager
  aggregate/         handler.py   — S3 event → score recompute → DynamoDB + SNS/SES
  read/              handler.py   — DynamoDB → DSP-scoped action queue (JWT-gated)
  actions/           handler.py   — action lifecycle + playbook config (JWT-gated)

design/
  index.html         — rendered HTML mockup of the DSP dashboard
  architecture.svg   — visual system architecture diagram
  screens.svg        — UI screen designs

PRFAQ.md            product spec written before any code
ARCHITECTURE.md     system diagram, auth design, data model, scale gaps
PRODUCT_SPEC_V0.md  full V0 spec: UX flows, data model, API contracts, WW config
DSP_DISCOVERY.md    customer discovery interview guide
LEARNINGS.md        what this build taught me
```

---

## What's Deliberately Missing

No CI/CD, no tests, no cost optimization. The PWA frontend is specced in [PRODUCT_SPEC_V0.md](PRODUCT_SPEC_V0.md) and designed in [Figma](https://www.figma.com/design/Z2Pvr8JVFZoyTRYuYtU3iD/Signal-Aggregator?node-id=5-168&t=96N2YyFp872MEKYl-1) / [design/](design/), but not yet built as a deployable app — customer discovery interviews ([DSP_DISCOVERY.md](DSP_DISCOVERY.md)) come first. See [LEARNINGS.md](LEARNINGS.md) for what I'd add before putting this in production.

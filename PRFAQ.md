# PR FAQ: Signal Aggregator

*Internal learning project — Kevin Shi, April 2026*

---

## Press Release

### Amazon Launches Signal Aggregator: A Unified Safety View for Delivery Service Partners

**BELLEVUE, WA — April 2026** — Today, Amazon's Last Mile organization launched Signal Aggregator, a new internal service that ingests safety signals from across the delivery network and distills them into a single, easy-to-understand view for Delivery Service Partner (DSP) owners and operations teams.

DSPs manage safety across fragmented channels — hard-braking telemetry, customer complaints, on-road observations — each with its own dashboard and notification logic. Important signals get buried; owners waste time stitching data instead of acting on it.

Signal Aggregator fixes this with a single ingest layer, unified per-driver severity scores, and threshold-based notifications that surface only what matters. Owners can now answer "which drivers need attention this week?" in seconds.

"Signal Aggregator turns dozens of raw signals into a handful of clear next steps," said the product owner. "And with the agent layer, taking those steps doesn't require opening a new tool — you can act from wherever you already are."

Built on AWS Lambda, S3, DynamoDB, SNS, and Amazon Bedrock, it uses a configurable threshold engine with support for per-region rules and a conversational interface that lets DSP owners log actions, ask questions about their fleet, and close the loop on safety issues without leaving the channel they're already in.

---

## FAQ

### Customer Questions

**Q: Who is the customer?**
A: The primary customer is the DSP owner — the small business operator who runs a fleet of delivery vans for Amazon. The secondary customer is the Amazon Last Mile operations team that supports DSPs.

**Q: What problem does this solve?**
A: DSPs receive safety signals from multiple disconnected systems, each with its own UI, thresholds, and notification logic. This creates three problems: (1) important signals get lost in noise, (2) DSPs spend time aggregating data manually instead of acting on it, and (3) inconsistent thresholds across systems make it hard to know what's actually urgent.

**Q: What is the customer experience?**
A: A DSP owner opens Signal Aggregator and sees a ranked list of drivers needing attention, with the underlying signals that drove the ranking. They can drill into any driver to see raw event history. They receive notifications only when a driver crosses a configured severity threshold — not for every individual event.

**Q: How does a DSP owner access Signal Aggregator?**
A: Signal Aggregator is intended to surface through the DSP's existing portal or dashboard — meeting customers where they already work rather than requiring them to adopt a new tool. The specific integration point with DSP-facing software is TBD; this is an open dependency that needs to be resolved before v1 can be considered customer-ready.

**Q: How is this different from what exists today?**
A: Existing tools surface raw signals one channel at a time. Signal Aggregator lives alongside those dashboards rather than replacing them — it adds a unified, ranked view on top of signals that DSPs can already access elsewhere. The goal is to reduce the time spent stitching data, not to remove existing access.

**Q: What happens if a driver's severity score seems wrong?**
A: A DSP owner can raise a dispute against a score. Disputes are reviewed and resolved by designated admins; not every DSP user can modify scores directly. This governance model prevents score manipulation while giving DSPs a recourse when signals are noisy or incorrectly attributed.

### Product Questions

**Q: What's in scope for v1?**
A:
- Ingest events from a single API endpoint (JSON payloads)
- Store raw events in S3
- Aggregate per-driver counts and severity scores in DynamoDB
- Expose a read API for current driver summaries
- Send SNS notifications when a driver crosses a severity threshold

**Q: What's explicitly out of scope for v1?**
A:
- Multiple ingestion sources (only one API endpoint to start)
- A polished UI (v1 ships a minimal static site on S3 + CloudFront; Grafana comes in v2)
- Per-DSP threshold configuration (single global threshold for v1)
- Historical trend analysis
- Integration with existing safety systems

**Q: What does success look like?**
A: A DSP owner can call the read API and get a current summary of their drivers' safety status with low likelihood of system failure. The system should surface safety signals near real-time, though latency is a known tradeoff given the event-driven architecture. Notifications fire when and only when a driver's score reaches 9 or above.

Engagement signal: DSP owners open the summary before their weekly driver review. Outcome signal: week-over-week decline in severity scores for drivers who received attention after a threshold notification — indicating the tool is driving actual behavior change, not just visibility.

**Q: What's the longer-term vision?**
A: Signal Aggregator is intended to live alongside existing dashboards, not replace them. The longer-term goal is to become the default first stop for a DSP owner starting a safety review — the place that tells them where to look, even if they then drill into existing tools for raw data.

Planned UI progression:
- **v1:** Minimal static site (HTML/JS) hosted on S3 + CloudFront, calling the existing read API. Low lift, real-time data, no new AWS services required.
- **v2:** Amazon Managed Grafana for a polished, real-time dashboard — connects natively to DynamoDB and CloudWatch, supports SAML/SSO for external DSP user access, and produces professional visualizations without custom frontend work. QuickSight may be added alongside Grafana specifically for historical trend analysis once sufficient data accumulates in S3.

Other future investments: per-DSP threshold configuration, historical trend analysis, and deeper integration with upstream signal sources.

**Q: Why introduce an agent when the action queue already tells owners what to do?**
A: The action queue tells owners *what* to do. An agent lets them *do it* — from wherever they are, in whatever interface they're already using.

A DSP owner managing 50 drivers is rarely at a desk. They're on the floor, in a van, or in back-to-back meetings. Opening an app to log an action adds friction that compounds across dozens of drivers per week. The insight behind the agentic layer isn't that DSPs lack information — it's that the last mile between "I know what needs to happen" and "I've recorded that I did it" is where behavior change actually breaks down.

The agent makes that last mile disappear. A DSP owner who receives a Tier 1 SMS alert can reply "snooze 3 days, spoke to her this morning" and the action is logged. They never open the app. The system knows the issue is being handled. The closed loop — signal → recommended action → confirmed response — closes over a text message instead of requiring a separate workflow.

Beyond action logging, the agent serves a second job: synthesis. The action queue shows a score and a recommended action, but DSP owners often want to understand *why* a driver is flagged before deciding what to do. "Explain Maria's situation this week" is a natural question. The answer — which signals contributed, when they arrived, whether there's a pattern — exists in DynamoDB but requires combining three tables and forming a coherent narrative. An agent does this in a single response that would otherwise require the owner to click through several screens.

The architectural position is deliberate: the agent is a sidecar, not a replacement. It reads the same data and calls the same action endpoints as the PWA. A DSP owner who prefers the app uses the app. One who prefers SMS uses SMS. The agent adds an interface; it doesn't change what the system knows or does.

Candidate interaction patterns for V2:

| Trigger | What the owner says | What happens |
|---|---|---|
| Reply to Tier 1 SMS alert | "Snooze 3 days, spoke to her" | Agent calls `POST /actions` with status=snoozed, snooze_until=+3d |
| Reply to Tier 1 SMS alert | "Log resolved, sent to coaching" | Agent calls `POST /actions` with status=resolved, note captured |
| Proactive check-in | "Who needs attention before Monday?" | Agent queries `/summary`, synthesises a ranked list in plain language |
| Drill-down | "Why is driver-003 flagged?" | Agent reads driver summary + recent events, returns a narrative explanation |
| Trend question | "Did my interventions last month actually help?" | Agent queries action history + score history, reports outcome patterns |

The underlying AWS primitive is Amazon Bedrock Agents, with action groups wired to the existing Lambda endpoints. The agent never writes data directly — all mutations go through the same `POST /actions` and `PUT /playbook` endpoints the PWA uses, so audit trails and access controls remain consistent regardless of which interface initiated the action.

### Technical Questions

**Q: What's the architecture?**
A:
1. **Ingest:** API Gateway → Lambda → writes raw event to S3, triggers aggregation
2. **Aggregate:** S3 event → Lambda → updates DynamoDB driver summary
3. **Notify:** Aggregation Lambda checks threshold → publishes to SNS if crossed
4. **Read:** API Gateway → Lambda → reads from DynamoDB → returns driver summary

**Q: Why this architecture?**
A: Serverless minimizes operational overhead for a learning project, the event-driven pattern mirrors real production safety systems, and using all four primitives (Lambda, S3, DynamoDB, SNS) gives me hands-on experience with the AWS services most relevant to my upcoming role.

**Q: How is the severity score calculated?**
A: The severity score is a weighted sum of all signals received for a driver within a rolling 7-day window (hard cutoff — all events in the window count equally regardless of age). Each signal type carries a configurable weight; each event's categorical severity (low=1, medium=2, high=3) is multiplied by that weight and summed. The result is a single numeric score used for ranking and threshold evaluation.

Window duration is hardcoded at 7 days in v1. Configurability is a candidate for v2. Decay-based scoring (weighting recent events more heavily) was considered and deferred — it adds implementation complexity and makes scores harder for DSP owners to interpret.

**Q: What does an ingest event look like?**
A: Events are JSON payloads posted to the ingest API with the following schema:
```json
{
  "event_id":    "uuid-v4 — used for idempotency",
  "driver_id":   "string — used to look up dsp_id server-side",
  "signal_type": "hard_braking | customer_complaint | on_road_observation",
  "severity":    "low | medium | high",
  "timestamp":   "ISO 8601",
  "source":      "string — upstream system that generated the signal",
  "metadata":    {}
}
```
`dsp_id` is not caller-supplied — it is resolved server-side from `driver_id` via a driver→DSP mapping table. `severity` is categorical for human interpretability; the aggregation Lambda translates it to numeric (low=1, medium=2, high=3) using a mapping stored in the config table.

**Q: What's the data model?**
A:
- **S3 raw events:** `s3://signal-aggregator-raw/events/YYYY/MM/DD/HH/{event_id}.json`
- **DynamoDB driver summary:** partition key `driver_id`, attributes for event counts by type, rolling severity score, last event timestamp
- **DynamoDB driver→DSP mapping:** partition key `driver_id`, attribute `dsp_id` — looked up at ingest time to associate events with the correct DSP
- **DynamoDB config table:** global threshold, per-signal-type weights, severity→numeric translation map

**Q: What are the signal weights and notification threshold?**
A: Signal type weights reflect relative safety consequence:

| Signal type | Weight | Rationale |
|---|---|---|
| `hard_braking` | 1 | High-frequency, often environmental — treated as baseline noise |
| `on_road_observation` | 2 | Human judgment call — higher signal quality than telemetry |
| `customer_complaint` | 3 | Direct customer impact with DSP reputational consequence |

Severity multipliers: low=1, medium=2, high=3. A driver's score is the sum of (weight × severity multiplier) for all events in the rolling 7-day window.

SNS notification fires when a driver's score reaches **9 or above**. At these weights, 9 is crossed by a single high-severity customer complaint (3×3=9) — intentionally sensitive, since a direct complaint warrants immediate DSP attention.

**Q: How will I configure thresholds?**
A: Weights, severity multipliers, and the notification threshold are stored in the DynamoDB config table, read by the aggregation Lambda on each invocation. v1 uses a single global threshold of 9; v2 would add per-region overrides and configurable window duration.

### Process Questions

**Q: What am I trying to learn from building this?**
A:
1. The AWS primitives my manager called out — Lambda, S3, DynamoDB — by using them, not reading about them
2. The MCP-mediated workflow of building AWS services through Claude Code rather than the console
3. The discipline of writing requirements before code, and iterating on the spec with AI before building
4. What it feels like to debug a multi-service event-driven system end-to-end

**Q: What's my definition of done?**
A:
- All four flows (ingest, aggregate, notify, read) work end-to-end
- I can demonstrate the system with a curl command that posts events and a second curl that reads the resulting summary
- The repo has a README, this PR FAQ, an architecture diagram, and a LEARNINGS.md
- I've identified at least three things I'd do differently if I were building it for production

**Q: What am I deliberately NOT doing?**
A: I am not optimizing for production-readiness. No CI/CD, no comprehensive tests, no auth on the API, no cost optimization beyond staying in the free tier. The goal is learning, and over-engineering would dilute that.

---

## Open Questions for Iteration

*(Unresolved items to push on with Claude Code — resolved items annotated below)*

1. ~~Should the aggregation Lambda be triggered by S3 events, or should the ingest Lambda call it directly?~~ **Resolved: S3 event trigger.** Decoupling preferred; latency tradeoff accepted and reflected in success criteria.
2. ~~Is DynamoDB the right store for the summary table?~~ **Resolved: DynamoDB confirmed.** Three tables: driver summary, driver→DSP mapping, config.
3. What's the right notification payload? Just "threshold crossed," or should it include context about which signals contributed?
4. How should I handle the case where the same event gets posted twice? (Idempotency — `event_id` field exists in the schema; deduplication logic TBD.)
5. Is there value in a v0 version that's even smaller — say, just ingest + read, no aggregation — to validate the loop before adding complexity?

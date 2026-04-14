# LEARNINGS.md

*Reflections after building Signal Aggregator — Kevin Shi, April 2026*

---

## What I Set Out to Learn

From the PRFAQ:
1. AWS primitives — Lambda, S3, DynamoDB, SNS — by using them, not reading about them
2. The MCP-mediated workflow: building AWS services through Claude Code
3. Writing requirements before code and iterating on the spec with AI
4. What it feels like to debug a multi-service event-driven system end-to-end

---

## What I Actually Learned

### 1. The event-driven mental model is different from request-response

The hardest shift wasn't writing Lambda code — it was accepting that the ingest call returns a 200 before aggregation has run. In a synchronous system, success means the whole operation completed. Here, success means "I accepted your event." The work happens somewhere else, asynchronously.

This showed up concretely in testing: I posted an event, immediately queried DynamoDB, and saw nothing. The instinct is that something is broken. The reality is that S3 → Lambda propagation takes a few seconds. Debugging this taught me to always check CloudWatch Logs first, not re-run the request.

### 2. IAM is the most friction-heavy part of AWS

Every time a service needs to talk to another service, you're writing a policy. The mental model — trust policy (who can assume this role) vs. permission policy (what can the role do) — isn't obvious at first. I got blocked twice: once because I forgot to grant `s3:GetObject` to the aggregation Lambda, and once because API Gateway didn't have `lambda:InvokeFunction`. Both produced silent failures or cryptic 500s that required log-diving.

Lesson: write IAM policies before deploying the function, not after it fails.

### 3. DynamoDB key design is a product decision, not just a technical one

The events table uses `driver_id` as the partition key and `timestamp#event_id` as the sort key. This enables the rolling-window query cheaply — a range query on SK rather than a scan. But I made this work by knowing the access pattern upfront: "give me all events for driver X in the last 7 days." If the access pattern were "give me all events of type hard_braking across all drivers," this schema would require a full table scan or a GSI.

DynamoDB forces you to decide your queries before your schema. That's the opposite of SQL, and getting it wrong is expensive to fix later.

### 4. S3 paths are queryable structure, not just storage addresses

The path `events/YYYY/MM/DD/HH/{event_id}.json` isn't just organization — it's the mechanism by which the rolling window would work if I were scanning S3 directly, and it's the partitioning scheme that keeps S3 performance healthy at scale. Treating object keys as structured data felt like a new primitive.

### 5. Spec-first with AI made the build faster, not slower

Writing the PRFAQ before any code forced decisions that would have otherwise surfaced as bugs: what does the event schema look like? What's the severity score formula? What's the notification threshold? By the time I opened a code editor, the aggregation logic was already fully specified. The Lambda code was almost mechanical to write.

The unexpected benefit: when the build revealed gaps (the driver→DSP mapping table wasn't in the original data model), I had a spec to update rather than tribal knowledge to carry around.

---

## Three Things I'd Do Differently for Production

### 1. Atomic score increments instead of read-modify-write

The aggregation Lambda currently: reads all events for a driver, sums contributions, writes the new score. Under concurrent load, two Lambda invocations for the same driver race — last write wins and events are lost.

The fix is DynamoDB's `ADD` expression: increment the score attribute atomically without reading it first. This requires storing the score as a running total rather than a recomputed value, which means tracking event expiry separately (a DynamoDB TTL-based cleanup job or a streams-based decrement). More complex, but correct.

### 2. SQS between S3 events and the aggregation Lambda

S3 event notifications invoke Lambda asynchronously with 3 retries. If Lambda is throttled or DynamoDB is slow, the retries exhaust and the event is silently dropped — a safety signal disappears with no record. In a safety system, silent data loss is the worst failure mode.

An SQS queue between S3 and Lambda provides unlimited retries, a dead-letter queue for failed events, and a visible backlog metric. It's a one-resource addition that changes the failure mode from "silent drop" to "visible queue depth."

### 3. Notification deduplication

Currently, every event that pushes a driver's score above 9 fires an SNS notification. A driver already at score 15 fires again on every subsequent event. DSP owners would receive dozens of alerts for the same driver and start ignoring them — exactly the problem this product is supposed to solve.

The fix: add a `notified_at` timestamp to the driver summary. Suppress re-notification until the score drops below threshold and crosses it again, or a cooldown window (e.g., 24 hours) elapses.

---

## On the MCP-Mediated Workflow

Building through Claude Code rather than the console changed what I paid attention to. In the console, I click through forms and the resources appear. Here, I had to know — or be reminded — that API Gateway needs explicit Lambda permission via `add-permission`, that S3 event notifications require a separate `put-bucket-notification-configuration` call, that IAM role creation is separate from policy attachment.

The friction was instructive. Every error was a gap in my mental model of how the services connect, not just a misconfigured form field. I'll forget the console navigation. I won't forget why `lambda:InvokeFunction` exists.

---

## What I'd Build Next

- **Idempotency:** use `event_id` to deduplicate double-posted events (a conditional write on the events table)
- **Score decay:** weight events by recency within the 7-day window — a DSP owner should care more about what happened yesterday than six days ago
- **Grafana dashboard:** connect Amazon Managed Grafana to DynamoDB for a real-time visual driver ranking
- **Auth:** even a simple API key on the ingest endpoint before sharing the URL with anyone

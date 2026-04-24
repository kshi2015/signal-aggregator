# LEARNINGS.md

*Reflections after building Signal Aggregator — Kevin Shi, April 2026*

---

## What I Set Out to Learn

From the PRFAQ:
1. AWS primitives — Lambda, S3, DynamoDB, SNS — by using them, not reading about them
2. The MCP-mediated workflow: building AWS services through Claude Code
3. Writing requirements before code and iterating on the spec with AI
4. What it feels like to debug a multi-service event-driven system end-to-end
5. *(Added during build)* How to translate backend signals into an action-oriented UX — and what it means to design for WW configurability from the start

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

### 6. A score is not a product — an action is

The first version of this system surfaced scores. A driver at 11 is bad. But "bad" doesn't tell a DSP owner what to do. The product question is: what happens *after* the alert fires?

Designing the action queue forced a different set of questions than designing the pipeline did. What's the recommended action for a high-severity customer complaint? Who logs that something was done about it? How does the system know an intervention worked? These aren't data questions — they're workflow questions that required a new data model (driver_actions, playbook, notification_prefs) sitting on top of the existing pipeline.

The lesson: backend completeness and UX completeness are independent. The pipeline was complete when events flowed end-to-end. The product wasn't complete until there was a closed loop from signal to action to resolution.

### 7. Notification design is a product decision, not a configuration detail

The original design had one notification: SNS fires when score ≥ 9. That's a complete technical implementation and an incomplete product. A single channel with no suppression, no batching, and no preference model produces fatigue within days.

Thinking through three tiers (interrupt, nudge, digest) — each with a different channel, frequency contract, and suppression rule — revealed that the real design challenge is trust. A DSP owner who receives one well-timed, accurate, actionable alert will act on it. One who receives twelve will start ignoring all of them. The threshold isn't just a number in a config table; it's a promise about when you'll be interrupted.

### 8. WW configurability is a structural decision, not a feature

Adding WW support later would require rewriting the notification dispatch layer, the config hierarchy, the scheduling logic, and every hardcoded string. Doing it upfront meant: a `region` key in the config hierarchy (even with only `us-east-1` populated), IANA timezone strings instead of UTC offsets, externalized locale strings, and a channel-agnostic dispatch interface. None of these added significant complexity to V0, but each would have been expensive to retrofit.

The principle: isolate the things that vary by region (channel, language, threshold, opt-in model) from the things that don't (what a notification means, when it fires, what it links to). That separation is the architecture — not just a nice-to-have.

### 9. Auth isn't a layer you add later — data isolation is

The original V0 used `dsp_id` as a URL parameter. Any caller who knew (or guessed) a DSP ID could read that DSP's driver data. This works for a learning project; it's a data breach in production.

Adding Cognito in V1 wasn't just "adding a login screen." It changed the data model: every Lambda that reads DSP-specific data now gets `dsp_id` from a signed, immutable JWT claim rather than a query parameter the caller controls. The DynamoDB filter in `get_drivers_for_dsp()` was already written; the only change was where the `dsp_id` value came from. That's the right way to think about auth — not as a gate at the front door, but as the mechanism that ensures identity propagates correctly through every data access.

### 10. HTTP API v2 `rawPath` includes the stage prefix

A routing bug that wasn't obvious from the Lambda code: in HTTP API (v2) with a named stage (e.g., `prod`), `event["rawPath"]` is `/prod/playbook`, not `/playbook`. The stage name is prepended. `event["routeKey"]` (e.g., `"GET /playbook"`) does not include the stage and is the right field to use for routing inside a Lambda that handles multiple paths. Diagnosing this required temporarily logging the event structure to CloudWatch and looking at the actual field values — the code looked correct but the assumption about the path format was wrong.

### 11. MCP as a PoC tool changes how you validate architecture

Using the Lambda Tool MCP server to call Lambda functions directly (bypassing API Gateway) made it possible to demonstrate data isolation before Cognito was provisioned: ingest events with different `dsp_id` values, confirm the driver summary records were correctly scoped, then wire up the real auth layer knowing the underlying logic already worked.

This pattern — validate the data model and Lambda logic first via direct invocation, then add the auth layer — is faster than building auth-first and debugging both simultaneously. The MCP tool also exposed a format difference: direct Lambda invocations don't wrap payloads in the API Gateway envelope, so the Lambda must handle both `event.get("body")` (API Gateway) and direct `event` keys differently.

---

## What I'd Do Differently for Production

### 1. Atomic score increments instead of read-modify-write

The aggregation Lambda currently: reads all events for a driver, sums contributions, writes the new score. Under concurrent load, two Lambda invocations for the same driver race — last write wins and events are lost.

The fix is DynamoDB's `ADD` expression: increment the score attribute atomically without reading it first. This requires storing the score as a running total rather than a recomputed value, which means tracking event expiry separately (a DynamoDB TTL-based cleanup job or a streams-based decrement). More complex, but correct.

### 2. SQS between S3 events and the aggregation Lambda

S3 event notifications invoke Lambda asynchronously with 3 retries. If Lambda is throttled or DynamoDB is slow, the retries exhaust and the event is silently dropped — a safety signal disappears with no record. In a safety system, silent data loss is the worst failure mode.

An SQS queue between S3 and Lambda provides unlimited retries, a dead-letter queue for failed events, and a visible backlog metric. It's a one-resource addition that changes the failure mode from "silent drop" to "visible queue depth."

### 3. Notification deduplication and suppression

Currently, every event that pushes a driver's score above 9 fires an SNS notification. A driver already at score 15 fires again on every subsequent event. DSP owners would receive dozens of alerts for the same driver and start ignoring them — exactly the problem this product is supposed to solve.

The fix is already specced in PRODUCT_SPEC_V0.md: add `notified_at` and `notification_threshold_at` to the driver summary. Suppress re-notification until the score drops below threshold and crosses it again.

### 4. Discovery interviews before finalising the UX

The action queue and playbook model are hypotheses. The right recommended action for a high-severity customer complaint might not be "1:1 conversation within 24 hours" for every DSP. Some may have a dedicated safety manager; some may route complaints to Amazon directly. The DSP discovery interview guide (DSP_DISCOVERY.md) should be run with 3–5 real DSPs before any wireframe is finalized — specifically the Section 4 questions about what actually happens between "I see a problem" and "I've done something about it."

---

## On the MCP-Mediated Workflow

Building through Claude Code rather than the console changed what I paid attention to. In the console, I click through forms and the resources appear. Here, I had to know — or be reminded — that API Gateway needs explicit Lambda permission via `add-permission`, that S3 event notifications require a separate `put-bucket-notification-configuration` call, that IAM role creation is separate from policy attachment.

The friction was instructive. Every error was a gap in my mental model of how the services connect, not just a misconfigured form field. I'll forget the console navigation. I won't forget why `lambda:InvokeFunction` exists.

---

## What I'd Build Next

- **PWA frontend:** the action queue UI consuming the now-complete API surface — auth, queue, playbook config, action logging all exist
- **SQS buffer:** insert SQS between S3 and the Aggregation Lambda to eliminate silent event loss under load
- **Idempotency:** use `event_id` to deduplicate double-posted events (a conditional write on the events table)
- **Score decay:** weight events by recency within the 7-day window — a DSP owner should care more about what happened yesterday than six days ago
- **DSP discovery interviews:** run the guide in DSP_DISCOVERY.md with 3–5 real DSPs to validate the action queue model and playbook defaults before building the frontend
- **WAF:** attach AWS WAF to CloudFront and API Gateway to rate-limit and protect against OWASP Top 10 before any real DSP traffic

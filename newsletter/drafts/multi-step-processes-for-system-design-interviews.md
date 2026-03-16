# Multi-step Processes

**TL;DR** - Multi-step processes fail halfway: payment charged but inventory not reserved. Use workflow engines like Temporal or Step Functions for durable execution, automatic retries, and compensation. Start simple with single-server orchestration; escalate to event sourcing or workflows when reliability matters.

>> 30-second elevator pitch: "Multi-step processes fail halfway - payment charged but inventory not reserved. I use workflow engines like Temporal or AWS Step Functions so each step is durable, failures trigger retries or compensation, and the system picks up exactly where it left off after a crash."

---

## What You Will Learn

> **Approaches**
> - Single-server orchestration (simple, no durability)
> - Single-server with state persistence (checkpoints, pub/sub callbacks)
> - Event sourcing (Kafka log, workers react to events: OrderPlaced, PaymentCharged, InventoryReserved)
> - Durable execution (Temporal: workflows, activities, deterministic replay, signals)
> - Managed workflows (Step Functions: declarative state machines, JSON)
>
> **Implementations**
> - Temporal, AWS Step Functions, Durable Functions, Airflow
>
> **Deep Dives**
> - Workflow versioning and migrations when you add new steps
> - Keeping workflow state size manageable
> - Handling external events and signals (user signs document in 5 days)
> - Ensuring activities run exactly once (idempotency)

---

## The Problem

Consider e-commerce order fulfillment: charge payment, reserve inventory, create shipping label, wait for a human to pick up the item, send confirmation, and wait for pickup. Each step calls different services. Any step can fail or timeout. Your server might crash after charging payment but before reserving inventory. Now you have money but no reserved item.

![Order Fulfillment: Multi-step Complexity](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-order-fulfillment.svg)

Distributed systems make even simple sequences of steps surprisingly hard. Manually adding retries, state checkpoints, and compensation logic to each step makes the system brittle. You interweave system-level concerns (crashes, retries, failures) with business-level concerns (what happens if we cannot find the item?). Workflow systems and durable execution solve this by design.

![What Happens When the Server Crashes Mid-Workflow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-crash-mid-workflow.svg)

**2 problems that use this pattern:** Uber, Payment System.

---

## The Solution: From Simple to Durable

The escalation from simple (single-server orchestration) to durable (event sourcing, Temporal, Step Functions). Each step adds reliability: state persistence, fault tolerance, automatic retries, and compensation.

![Decision Tree: Choosing a Multi-step Approach](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-decision-tree.svg)

> **What interviewers want to hear:** "For simple flows I start with single-server orchestration. When I need reliability, I use event sourcing or a workflow engine. Temporal is my default - it gives durable execution, automatic retries, and compensation without building it myself."

---

## Single-Server Orchestration

The simplest approach: one service calls each step in sequence. Your API server receives the order request, calls payment, then inventory, then shipping, and returns the result.

![Naive Approach: Sequential Service Calls](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-naive-approach.svg)

> **Without state** - Fine for low-stakes flows. Crashes mean lost progress. No way to handle long waits (for example, a user signing a document in 5 days) without blocking.

> **With state** - Add database checkpoints between steps and pub/sub for callbacks. You can scale out API servers and resume from state. But this quickly becomes complex: you are manually building a state machine. Who picks up dropped work when multiple servers run? Compensation is still unsolved - if inventory reservation fails after payment, you need to refund.

![State Machine: Manual Orchestration Complexity](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-state-machine.svg)

The architecture becomes a tangled mess of state management, error handling, and compensation logic scattered across your application.

---

## Choreography vs Orchestration

Before diving into specific solutions, understand the two fundamental patterns for coordinating multi-step processes.

![Choreography vs Orchestration](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-choreography-vs-orchestration.svg)

**Choreography** means each service reacts to events independently. No central coordinator. Services emit events and other services listen. Simple to start, but hard to reason about as complexity grows. Debugging "why did the order not ship?" requires tracing events across multiple services.

**Orchestration** means a central coordinator calls each service in sequence, deciding what to do next based on results. Easier to understand and debug but creates a single point of coordination.

> **Interview tip:** Most workflow engines use orchestration. Mention choreography as an alternative when services are truly independent and the flow is simple.

---

## Event Sourcing

**Event sourcing** stores a sequence of events that represent what happened instead of the current state. The event log both records history and orchestrates next steps.

![Event Sourcing Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-event-sourcing.svg)

Here is the flow: the API emits "OrderPlaced" when an order request arrives. The payment worker sees OrderPlaced, charges payment, and emits "PaymentCharged" or "PaymentFailed". The inventory worker sees PaymentCharged, reserves stock, and emits "InventoryReserved" or "InventoryFailed". The shipping worker continues from there.

![Event Log: Append-Only Record](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-event-log.svg)

**Benefits:**

- **Fault tolerance** - If a worker crashes, another picks up the event
- **Scalability** - Add more workers for higher load
- **Observability** - Complete audit trail of all events
- **Flexibility** - Possible to add new steps or modify workflows

> **Note:** You are building significant infrastructure: event stores, message queues, worker orchestration. For complex business processes this becomes its own distributed systems project.

---

## The Saga Pattern and Compensation

When a step fails after previous steps have completed, you need **compensating actions** to undo the work. This is the saga pattern.

![Saga Pattern: Coordinated Steps with Rollback](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-saga-pattern.svg)

Each forward step must have a defined reverse action. If shipping fails after payment was charged and inventory was reserved, the saga runs compensating actions in reverse order: release inventory, then refund payment.

![Compensating Actions: Undoing Completed Steps](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-compensating-actions.svg)

![Saga Compensation Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-saga-compensate.svg)

> **Key rule:** Compensating actions must be idempotent. A refund should be safe to retry if it fails halfway through.

---

## Workflows: Durable Execution vs Managed

What we really want is a **workflow**: a reliable, long-running process that survives failures and continues where it left off.

### Durable Execution Engines (Temporal)

**Durable execution** means long-running code that can move between machines and survive crashes. Instead of losing progress when a server restarts, the engine resumes from the last successful step on a new host.

![Durable Execution: Survive Crashes Automatically](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-durable-execution.svg)

You write a function that represents the workflow. It looks like normal sequential code: call processPayment, then if it succeeds call reserveInventory, then shipOrder and sendConfirmationEmail; if inventory fails, call refundPayment.

![Temporal Workflow: Code-First Durable Execution](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-temporal-workflow.svg)

**Workflows and activities:**

- **Workflows** - The high-level flow. Deterministic: given the same inputs and history, they always make the same decisions. This enables replay-based recovery.
- **Activities** - The individual steps (charge payment, reserve inventory). Must be idempotent: same inputs yield the same result.

Each activity run is recorded in a history database. If a workflow runner crashes, another replays the workflow, uses the history for prior activity results, and does not re-run completed activities.

![Orchestrator Flow: Central Coordination](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-orchestrator-flow.svg)

### Managed Workflow Systems (Step Functions)

**Managed workflow systems** use a declarative approach. You define the workflow as a state machine or DAG in JSON, YAML, or a specialized DSL. The engine handles orchestration.

AWS Step Functions defines workflows as state machines in JSON. You declare states: ProcessPayment (Task, calls a Lambda), then CheckPaymentResult (Choice, branches on success/failure), then ReserveInventory or PaymentFailed.

> **Interview tip:** Both approaches can work for similar purposes. Default to Temporal unless the company is AWS-centric.

---

## Handling External Events and Signals

Your workflow needs to wait for a customer to sign documents. They might take 5 minutes or 5 days. How do you handle this efficiently?

![External Events: Signal-Based Waits](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-external-events.svg)

Workflows excel at waiting without consuming resources. Use **signals** for external events. The workflow sends the document for signing via an activity, then waits for a "document_signed" signal with a timeout. If the signal arrives, process it. If it times out, send a reminder.

![Human-in-the-Loop Workflow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-human-in-loop.svg)

External systems send signals through the workflow engine API. No polling, no resource consumption. This handles human tasks, webhook callbacks, and external integrations.

---

## Reliability Deep Dives

### Retry with Backoff

When an activity fails (network timeout, service unavailable), the workflow engine automatically retries with exponential backoff. Each retry waits longer: 1s, 2s, 4s, 8s. Add jitter to prevent thundering herd when many workflows retry simultaneously.

![Retry with Exponential Backoff](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-retry-with-backoff.svg)

### Exactly-Once Semantics

Most workflow systems ensure an activity runs "exactly once" for a specific definition of "run". If the activity finishes successfully but fails to acknowledge the engine, the engine may retry.

![Exactly-Once Processing](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-exactly-once.svg)

**Make activities idempotent** - The activity can be called multiple times with the same inputs and produce the same result. Store an idempotency key in a database and check if it exists before performing the irreversible action.

![Idempotency: Safe to Retry](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-idempotency.svg)

### Dead Letter Queue

Messages that repeatedly fail processing go to a dead letter queue for inspection. This prevents poison messages from blocking the entire queue.

![Dead Letter Queue: Handle Poison Messages](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-dead-letter-queue.svg)

### Workflow Versioning

You have 10,000 running workflows. You need to add a new compliance check. Workflow versioning lets old workflows continue with old logic while new workflows use updated logic.

![Workflow Versioning: Safe Updates](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-workflow-versioning.svg)

---

## Real-World Interview Scenarios

### Payment System Workflow

Payment systems have lots of state, strong need for graceful failure handling. You do not want a user charged for a product they did not receive.

![Payment System Workflow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-payment-flow.svg)

### Uber Ride Workflow

When a user requests a driver, the driver must accept. The workflow waits for human completion at multiple points: driver acceptance, pickup arrival, and ride completion.

![Uber Ride Workflow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-uber-ride-flow.svg)

---

## When to Use in Interviews

![Interview Scenarios: Multi-step Processes](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-interview-scenarios.svg)

**When NOT to use:**

- **Simple async** - Resize an image, send an email. Use a message queue. Workflows are overkill for single-step operations.
- **Synchronous operations** - Client waits for response, or latency is critical. Workflows are for truly async, multi-step processes.
- **High-frequency, low-value** - Workflows add overhead. For millions of simple operations, cost and complexity are not justified.

> **Interview tip:** Start simple. Only introduce workflows when you identify specific problems they solve: partial failure handling, long-running processes, complex orchestration, or audit requirements.

---

## Summary

![Multi-step Processes: Summary](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/ms-summary.svg)

>> Workflow systems transform fragile manual orchestration into robust, observable solutions. If you find yourself building distributed sagas by hand or state machines in Redis, it is time to consider a workflow engine.

- **Simple flows** - Single-server orchestration. Fine for low-stakes, no long waits.
- **State persistence** - Add checkpoints and pub/sub. Quickly becomes complex.
- **Event sourcing** - Kafka log, workers emit events (OrderPlaced, PaymentCharged, InventoryReserved). Fault tolerant, scalable, full audit trail.
- **Durable execution (Temporal)** - Workflows and activities, deterministic replay, signals for external events. Survives crashes, automatic retries.
- **Managed workflows (Step Functions)** - Declarative state machines in JSON. Good for AWS-heavy environments, less expressive.
- **Listen for** - State machines, partial failures, long waits, compensation logic.

In interviews, demonstrate you know when to introduce workflows and when simpler solutions suffice. Be ready to discuss versioning, state size, external events, and idempotency.

{{SUBSCRIBE}}

{{BUTTON:Read More Articles|https://newsletter.systemdesignlaws.xyz}}
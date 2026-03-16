# Managing Long-Running Tasks

**TL;DR** - When a task takes more than a few seconds, do not make the client wait. Accept the request immediately (return a job ID), process asynchronously with a queue and worker pool, and let the client poll for status or receive a webhook callback. Add retries with exponential backoff, dead letter queues for poison messages, and idempotency for safe retries.

>> 30-second elevator pitch: "For any operation that takes more than a few seconds, I return a job ID immediately and process asynchronously. A message queue decouples submission from processing. Workers pull jobs, execute them, and update status. The client polls for completion or gets a webhook callback. I add exponential backoff for retries and a dead letter queue for poison messages."

---

## What You Will Learn

> **Core Patterns**
> - Synchronous vs asynchronous processing
> - Submit-and-poll pattern (return job_id, client polls status)
> - Message queues (decouple producer from consumer)
> - Worker pools (scale processing independently)
>
> **Reliability**
> - Retry with exponential backoff and jitter
> - Dead letter queues for poison messages
> - Idempotency keys for safe retries
> - Exactly-once processing semantics
>
> **Scaling**
> - Backpressure (queue absorbs burst)
> - Priority queues (paid users first)
> - Rate-limiting workers (protect downstream)
> - Auto-scaling workers on queue depth
>
> **Deep Dives**
> - Progress tracking and notification strategies
> - Webhook callbacks vs polling
> - Job dependencies and DAG execution
> - Implementation choices (Redis, RabbitMQ, SQS, Kafka)

---

## The Problem

A user requests a PDF report. Your server queries multiple databases, generates charts, renders 500 pages, and assembles the document. This takes 3 minutes. But HTTP requests typically timeout after 30 seconds. Even if the connection stays open, the server thread is blocked, unable to serve other requests. On mobile, the connection drops when the user switches apps.

![Synchronous vs Asynchronous Processing](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-sync-vs-async.svg)

The synchronous model breaks for any task that takes more than a few seconds: video transcoding, data export, batch email sending, image processing, or report generation. The solution is the same in every case: accept immediately, process asynchronously.

![Request Timeout Problem](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-request-timeout-problem.svg)

>> Any time an interviewer describes a process that "takes a while" or "processes in the background," they are testing whether you know the async pattern. This comes up in nearly every system design interview.

**6 problems that use this pattern:** YouTube video processing, Dropbox file sync, Stripe payment webhooks, report generation, data export, batch notifications.

---

## The Solution: Submit and Poll

The fundamental pattern is simple. The client submits a request. The server acknowledges immediately with a job ID and HTTP 202 Accepted. The server enqueues the task. A background worker picks it up and processes it. The client polls for status using the job ID.

![Submit and Poll Pattern](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-submit-and-poll.svg)

The API response is fast (50ms). The processing happens independently. The client can navigate away, close the app, and come back later to check status.

> **What interviewers want to hear:** "I would not process this synchronously. I would return a job ID immediately and process in the background. The client polls for status, or I send a webhook when it is done."

---

## Message Queues

The queue is the critical component that decouples submission from processing. It absorbs burst traffic, guarantees delivery, and enables independent scaling of producers and consumers.

![Message Queue Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-message-queue-flow.svg)

The producer (your API server) pushes messages to the queue. Workers (consumers) pull messages, process them, and acknowledge completion. If a worker crashes before acknowledging, the message returns to the queue for another worker.

### Queue Architecture

![Job Queue Architecture](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-job-queue-architecture.svg)

The architecture separates three concerns: the API server handles request validation and enqueueing, the queue provides durable storage and delivery guarantees, and the worker pool handles processing.

---

## Worker Pools

Workers are the processing engines. Each worker pulls a message from the queue, executes the task, updates the status store, and acknowledges the message.

![Worker Pool Architecture](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-worker-pool.svg)

Scale workers independently from your API servers. If the queue depth grows, add more workers. If it shrinks, scale down. This is the core benefit of the async pattern: API throughput and processing throughput scale independently.

### Job States

Every job follows a state machine: queued, processing, completed, failed.

![Job State Machine](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-job-states.svg)

Store the current state and metadata (progress percentage, error message, result URL) in Redis or a database so clients can query it.

---

## Reliability Patterns

### Retry with Exponential Backoff

When a task fails (network error, service unavailable, transient bug), retry it. But do not retry immediately in a tight loop, that will overwhelm the failing service. Use exponential backoff: wait 1 second, then 2, then 4, then 8. Add jitter (random delay) to prevent thundering herd when many workers retry simultaneously.

![Retry with Exponential Backoff](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-retry-with-backoff.svg)

![Exponential Backoff: Increasing Wait Times](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-exponential-backoff.svg)

> Set a maximum retry count (typically 3-5). After exhausting retries, move the message to a dead letter queue.

### Dead Letter Queue

A dead letter queue catches messages that repeatedly fail processing. Instead of blocking the main queue or losing the message, move it aside for inspection. Engineers can examine failed messages, fix the root cause, and replay them.

![Dead Letter Queue](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-dead-letter-queue.svg)

Common causes of DLQ messages: corrupt input data, schema mismatches, downstream service permanently down, or bugs in worker code.

### Idempotency

If a worker processes a job but crashes before acknowledging the queue, the queue will redeliver the message to another worker. Now the job runs twice. For operations like "charge credit card" or "send email," this is a problem.

![Idempotency Key: Safe Retries](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-idempotency-key.svg)

**Make every operation idempotent.** Before performing an irreversible action, check if it has already been done using a unique idempotency key (typically job_id + step_name). If the key exists in your database, skip the action and return the previous result.

### Exactly-Once Processing

True exactly-once delivery is impossible in distributed systems. What you can achieve is "effectively exactly once" through idempotent operations: the message may be delivered more than once, but the side effect happens exactly once.

![Exactly-Once Processing](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-exactly-once.svg)

---

## Scaling Patterns

### Backpressure

When 10,000 users submit reports simultaneously, the queue absorbs the burst. Workers process at their own pace. The queue depth is your pressure gauge: if it grows faster than workers can drain it, you need more workers.

![Backpressure: Queue Absorbs Burst Load](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-backpressure.svg)

### Priority Queues

Not all jobs are equal. Paid users should get their videos transcoded before free users. Priority queues ensure high-priority jobs are processed first.

![Priority Queues](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-priority-queues.svg)

Implement with separate queues per priority level (workers check high-priority first) or a single queue with priority ordering.

### Rate-Limiting Workers

Without rate limits, a burst of 10,000 jobs means 10,000 concurrent calls to your payment API, which causes a cascading failure. Rate-limit workers to protect downstream services.

![Rate-Limiting Workers](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-rate-limiting-workers.svg)

Strategies include concurrency limits (max N workers), token bucket (acquire token before calling downstream), and adaptive rate adjustment based on downstream latency.

---

## Progress Tracking and Notification

### Progress Tracking

For long tasks, users want to know how far along they are. Workers update a progress store (Redis or database) with percentage, current step, and estimated time remaining. The client reads this through your API.

![Progress Tracking for Long-Running Tasks](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-progress-tracking.svg)

### Polling vs Webhook

Two approaches for notifying the client when a task completes.

![Polling vs Webhook Notification](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-polling-vs-webhook.svg)

**Polling** is simple: the client calls GET /jobs/{id} every few seconds. Works with browsers, mobile, and does not require inbound connections. Downside: wasted requests while the job is still running.

**Webhooks** are efficient: the server POSTs to a callback URL when the job completes. Instant notification, no wasted requests. But the receiver must have a public endpoint and handle retries and idempotency.

![Webhook Callback Pattern](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-webhook-callback.svg)

> **Default:** Polling for client-facing applications. Webhooks for server-to-server communication.

---

## Advanced Patterns

### Job Dependencies (DAG)

Some tasks depend on others. A video pipeline must extract audio before transcribing it, but can generate thumbnails in parallel. Model dependencies as a directed acyclic graph (DAG).

![Job Dependencies: DAG Execution](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-job-dependencies-dag.svg)

A job starts when all its dependencies complete. Independent jobs run in parallel. This maximizes throughput while respecting ordering constraints.

---

## Implementation Choices

### Redis Queue (Bull, BullMQ)

Simple and fast. Good for small to medium workloads. Queue lives in Redis memory. Supports priority, delay, and retry. Limitation: not as durable as dedicated message brokers.

![Redis Queue Architecture](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-redis-queue.svg)

### RabbitMQ

Robust message broker with advanced routing. Supports topic exchanges, dead letter queues, and message acknowledgment out of the box. Good for complex routing patterns.

![RabbitMQ Exchange Architecture](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-rabbitmq-exchange.svg)

### SQS + Lambda (Serverless)

Fully managed. No infrastructure to operate. Auto-scales from zero. Pay per message. Best for event-driven workloads on AWS. Limitation: 15-minute execution limit for Lambda.

### Kafka

High-throughput distributed log. Best for streaming workloads with millions of messages per second. Retains messages for replay. More complex to operate than SQS or RabbitMQ.

> **Interview default:** SQS + Lambda for serverless/AWS environments. Redis + Bull for self-managed applications. Kafka for high-throughput streaming.

---

## Real-World Interview Scenarios

![Interview Scenarios: Long-Running Tasks](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-interview-scenarios.svg)

### PDF Report Generation

A classic long-running task example combining every pattern: queue, workers, progress tracking, and notification.

![PDF Generation: Long-Running Task Example](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-pdf-generation-flow.svg)

### Video Transcoding

CPU-intensive with priority queues, auto-scaling workers, and progress tracking through multiple processing stages.

![Video Transcode: Long-Running Task Example](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-video-transcode-flow.svg)

---

## Summary

![Managing Long-Running Tasks: Summary](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lt-scaling-summary.svg)

>> The pattern is always the same: accept immediately, queue the work, process asynchronously, notify on completion. Everything else is reliability and scaling on top of this foundation.

- **Core** - Submit and poll. Return job_id immediately. Queue decouples submission from processing.
- **Reliability** - Retry with exponential backoff. Dead letter queue for poison messages. Idempotency for safe retries.
- **Scaling** - Backpressure via queue. Priority queues for fairness. Auto-scale workers on queue depth. Rate-limit to protect downstream.
- **Notification** - Polling for browsers/mobile. Webhooks for server-to-server. Progress tracking via Redis.
- **Implementation** - Redis + Bull for simple. RabbitMQ for routing. SQS + Lambda for serverless. Kafka for high throughput.

In interviews, start with the submit-and-poll pattern. Layer on reliability (retry, DLQ, idempotency) and scaling (priority, backpressure, auto-scaling) based on the specific requirements.

{{SUBSCRIBE}}

{{BUTTON:Read More Articles|https://newsletter.systemdesignlaws.xyz}}
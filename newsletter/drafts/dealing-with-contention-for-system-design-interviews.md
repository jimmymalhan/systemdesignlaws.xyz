# Dealing with Contention

**TL;DR** - Fix race conditions with atomicity, locks, or optimistic concurrency. Scale to distributed coordination when multiple databases are involved. Start simple. Most applications never need 2PC.

>> 30-second elevator pitch: "Contention happens when two users act on the same data at once, like two people buying the last concert ticket. I fix it by making operations atomic, using locks when conflicts are common, or optimistic concurrency when they are rare. For distributed systems, I use sagas or two-phase commit. I always exhaust single-database solutions first."

---

## What You Will Learn

> **Single-node solutions** (start here)
> - Race conditions and the double-booking problem
> - Atomicity and transactions (the READ COMMITTED gotcha)
> - Pessimistic locking (FOR UPDATE, row locks, lock granularity)
> - Isolation levels (READ UNCOMMITTED through SERIALIZABLE)
> - MVCC (multi-version concurrency control)
> - Optimistic concurrency control (version column, compare-and-swap, ABA problem)
>
> **Multiple nodes**
> - Two-phase commit (prepare phase, blocking, coordinator log)
> - Distributed locks (Redis TTL, ZooKeeper/etcd, fencing tokens, reservations for UX)
> - Saga pattern (compensation, orchestrator, temporary inconsistency)
>
> **Choosing the right approach** - Decision tree from single DB to distributed
>
> **Deep Dives** (what interviewers ask next)
> - Deadlocks and ordered locking
> - ABA problem with optimistic concurrency
> - Write skew anomaly
> - Optimistic vs pessimistic tradeoffs
> - Hot partition and queue-based serialization
> - Interview scenario pattern matching

---

## The Problem: Race Conditions

Consider buying concert tickets online. There is 1 seat left for a popular concert. Alice and Bob both click "Buy Now" at the same moment. Without coordination, both read "1 seat available," both proceed to payment, and both get confirmation emails for the exact same seat. One gets kicked out at the door.

![Race Condition: The Double-Booking Problem](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-race-condition.svg)

The race condition happens because both read the same initial state before either write takes effect. There is a gap between "check the current state" and "update based on that state" where the world can change. In that tiny window (microseconds in memory, milliseconds over a network), things break. This is fundamentally an isolation problem, not an atomicity problem. Each transaction individually succeeds; they interfere because they see the same data concurrently.

### The Double-Booking Problem

The core issue is read-then-write without coordination. Both users read the same snapshot, both make decisions based on that stale read, and both write conflicting updates.

![Double-Booking: What Goes Wrong](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-double-booking.svg)

>> With 10,000 concurrent users hitting the same resource, even small race condition windows create massive conflicts. As you scale, you may need to coordinate across multiple nodes, which adds significant complexity.

**3 problems that use this pattern:** Ticketmaster, Rate Limiter, Online Auction.

---

## The Solution: Escalation Path

Contention handling follows an escalation path: single-database solutions first, then distributed coordination only when necessary. The diagram below shows the escalation from atomicity (single DB) through locks and optimistic concurrency, then to distributed coordination (2PC, sagas, distributed locks) when multiple databases are involved.

![Contention Solutions: Complete Summary](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-scaling-summary.svg)

> **What interviewers want to hear:** "I start with atomic transactions. If contention is high, I use pessimistic locking. If it is low, optimistic concurrency is faster. For distributed systems, I prefer sagas over 2PC when I can tolerate eventual consistency. I do everything possible to keep contended data in a single database."

---

## Single-node Solutions

When all your data exists in a single database, contention solutions are straightforward. Nine times out of ten, keeping contended data together avoids distributed coordination entirely.

### Atomicity

**Atomicity** means a group of operations either all succeed or all fail. No partial completion. **Transactions** provide this: you start a transaction, perform operations (debit one account, credit another), then COMMIT to save or ROLLBACK to undo everything. If anything fails mid-way, the database rolls back all changes in that transaction.

For a concert ticket purchase, you need two operations: decrement the seat count and create a ticket record. Wrap both in one transaction. If the decrement fails (sold out) or the insert fails (constraint violation), both roll back. No orphaned ticket without a seat.

Many databases support transactions: relational (PostgreSQL, MySQL), NoSQL (MongoDB multi-document, DynamoDB), and distributed SQL (CockroachDB, Spanner). Concepts apply regardless of engine; isolation guarantees vary.

>> **The READ COMMITTED gotcha:** Atomicity alone does not prevent double-booking. Under default READ COMMITTED isolation, Alice and Bob can both start transactions, both read "1 seat available," both run their update. The second transaction re-evaluates its WHERE clause against committed state (seats now 0), so its update affects zero rows, but the application may still run the INSERT for the ticket unless it checks the affected row count. Transactions provide atomicity within themselves; they do not prevent concurrent reads. You need coordination mechanisms.

![READ COMMITTED: The Default Gotcha](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-read-committed.svg)

> **Interview tip:** Always mention transactions when multiple related writes must stay consistent. And always check affected row count when your update includes a predicate. Zero rows means someone else won the race.

### Pessimistic Locking

**Pessimistic locking** assumes conflicts will happen and prevents them up front. The name comes from being pessimistic about conflicts. You acquire an exclusive row lock before reading, so no other transaction can read or modify that row until you commit.

The pattern: first run a SELECT with FOR UPDATE on the concert row (this acquires the lock), then decrement seats only if available_seats is greater than zero, check that the update affected one row, then insert the ticket. The second transaction blocks at the SELECT until the first commits. Only one person checks and updates at a time.

![Pessimistic Locking: SELECT FOR UPDATE](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-pessimistic-lock.svg)

A **lock** is a mechanism that prevents other database connections from accessing the same data until the lock is released. PostgreSQL and MySQL handle thousands of concurrent connections; locks ensure only one connection modifies a specific row at a time.

> **Without lock** - Both read seats = 1, both decrement. Result: -1 seats, double sale. **With FOR UPDATE** - First transaction locks row; second waits. Only one sale.

The available_seats greater than zero guard matters. Locking serializes access; the predicate enforces correctness. Without it, two transactions running back-to-back could decrement seats to -1.

### Lock Granularity

The scope of your lock determines how much concurrency you sacrifice. Locking an entire table kills throughput. Locking a single row is precise and fast. The right granularity depends on what your operation touches.

![Lock Granularity: Scope vs Concurrency](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-lock-granularity.svg)

>> Lock as few rows as possible for as short a time as possible. Lock entire tables and you kill concurrency. Hold locks for seconds instead of milliseconds and you create bottlenecks. In the ticket example, lock only the one concert row during the purchase.

### Isolation Levels

**Isolation levels** control how much concurrent transactions see of each other's changes. Instead of explicit FOR UPDATE, you can raise the isolation level and let the database detect conflicts.

![SQL Isolation Levels: Protection Spectrum](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-isolation-levels.svg)

Most databases support four standard levels (different options, not a progression):

### READ UNCOMMITTED

The weakest isolation level. Transactions can see uncommitted changes from other transactions. This is called a "dirty read" because you might read data that gets rolled back and never actually existed.

![READ UNCOMMITTED: Dirty Read Problem](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-read-uncommitted.svg)

Rarely used in production. The tiny performance gain is not worth the data corruption risk. Mentioned in interviews to show you understand the spectrum.

### READ COMMITTED

The default in PostgreSQL. Only committed data is visible to reads. This prevents dirty reads but still allows the double-booking race condition because two transactions can read the same committed state and both proceed.

### REPEATABLE READ

The default in MySQL. Once you read a value within a transaction, re-reading it returns the same result even if another transaction committed a change. The database takes a snapshot at transaction start.

![REPEATABLE READ: Snapshot Isolation](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-repeatable-read.svg)

Prevents non-repeatable reads but still allows phantom reads (new rows appearing in range queries).

### SERIALIZABLE

The strongest isolation level. The database makes transactions appear to run one after another, even though they run concurrently. It detects conflicts between concurrent transactions and aborts one.

![SERIALIZABLE: Automatic Conflict Detection](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-serializable.svg)

>> SERIALIZABLE is more expensive than explicit locks. The database must track all reads and writes to detect conflicts; aborts waste work. Explicit locks give precise control over what gets locked and when. Use SERIALIZABLE when you cannot identify specific locks; use explicit locks when you know exactly which rows need coordination.

### MVCC: How Databases Make It Work

Under the hood, modern databases use **Multi-Version Concurrency Control** to implement isolation levels without readers blocking writers. The database keeps multiple versions of each row and serves the right version to each transaction based on its snapshot.

![MVCC: Multi-Version Concurrency Control](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-mvcc.svg)

MVCC is why PostgreSQL and MySQL achieve high concurrency. Readers never block writers, writers never block readers. Only writer-writer conflicts need locks. Understanding MVCC helps you reason about what your isolation level actually guarantees.

### Optimistic Concurrency Control

**Optimistic concurrency control (OCC)** assumes conflicts are rare. You let transactions proceed and detect conflicts after they occur. When conflicts are infrequent, this eliminates locking overhead.

![Optimistic Concurrency: Version Check](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-optimistic-lock.svg)

**Version column pattern:** Add a version number to your data. On each update, increment the version and include "expected version = X" in your WHERE clause. When Alice updates first, her version goes from 42 to 43. When Bob tries to update with "WHERE version = 42," zero rows match because someone else changed the record. The application must check the affected row count. If zero rows, roll back and do not insert the ticket. The database will not raise an error for a WHERE that matches nothing.

**Business value as version:** You can use existing data as the version when it changes monotonically. For concerts, available_seats itself can serve: "UPDATE ... WHERE available_seats = 1" means only one transaction will match. Again, check affected row count. If zero rows, roll back.

### Compare-And-Swap

The version check pattern is a form of **Compare-And-Swap (CAS)**, a fundamental primitive in concurrent systems. Read a value, compare it with what you expect, and swap atomically only if it matches. This pattern shows up everywhere from SQL to DynamoDB to CPU hardware.

![Compare-And-Swap (CAS): Atomic Check + Update](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-compare-and-swap.svg)

This approach makes sense when conflicts are uncommon. For most e-commerce, the chance of two people buying the exact same item at the exact same moment is low. Occasional retries beat locking overhead.

### The ABA Problem

>> **ABA problem:** Using mutable business values (account balances, stock counts) as the version is risky. A value can go from A to B and back to A. Your optimistic check sees the same value and assumes nothing changed, but important transitions happened.

![ABA Problem: Hidden State Changes](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-aba-problem.svg)

Example: a bank balance goes $100 to $50 to $100. Your check would pass. A dedicated, monotonically increasing version column is safest. Use business values as version only when they change in one direction (e.g. auction bid amounts that only go up).

---

## Multiple Nodes

When you need to coordinate updates across multiple databases, things get complex. If your system needs strong consistency under high contention, do everything possible to keep the contended data in a single database first.

Consider a bank transfer where Alice and Bob have accounts in different databases (e.g. after sharding). Database A debits Alice; Database B credits Bob. Both must succeed or both must fail. If A debits but B fails, money disappears.

### Two-Phase Commit (2PC)

**Two-phase commit** coordinates across participants. Your transfer service acts as the coordinator. Phase one (prepare): ask all participants to prepare the transaction. Each database does the work except the final commit, verifying funds, placing holds, making the prepared state durable. Phase two (commit or abort): if all prepared successfully, tell them to commit; otherwise abort.

![Two-Phase Commit (2PC)](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-two-phase-commit.svg)

Critically, the coordinator must write to a persistent log before sending commit or abort. The log records which participants are involved and the transaction state. Without it, coordinator crashes leave participants unsure whether to commit or abort prepared transactions.

>> **Blocking:** The prepare phase holds locks on the account rows. If the coordinator crashes between prepare and commit, participants wait. This is 2PC's biggest weakness: prepared participants are blocked until the coordinator recovers. Production systems use coordinator failover and recovery. A new coordinator reads the log and completes in-flight transactions. 2PC preserves consistency but at the cost of availability during partitions.

### Distributed Locks

For simpler coordination, **distributed locks** ensure only one process works on a resource at a time across the system. Acquire locks on both Alice's and Bob's account IDs before starting the transfer.

![Distributed Locks: Cross-System Coordination](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-distributed-lock.svg)

**Redis with TTL** is the most common implementation. Use SET with NX (only set if not exists) and expiration. Redis removes the lock after TTL. Fast, simple; Redis is a single point of failure. The NX flag is critical because without it, a second process could overwrite an existing lock.

![Redis Distributed Lock: SET NX EX](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-redis-lock.svg)

**ZooKeeper and etcd** provide consensus-based locks with strong consistency. ZooKeeper uses ephemeral nodes that disappear when the client session ends. These systems maintain consistency through Raft (etcd) and ZAB (ZooKeeper) protocols. More robust under partitions, but more operational complexity.

![ZooKeeper / etcd: Consensus-Based Locks](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-zookeeper-lock.svg)

**Reservations for UX:** Distributed locks improve user experience by shrinking the contention window. For Ticketmaster, when a user selects a seat, move it to "reserved" with a 10-minute TTL instead of "sold." The window shrinks from the full purchase flow (minutes) to the reservation step (milliseconds). Same pattern: Uber's "pending_request" driver status, e-commerce cart "holds," meeting room temporary reservations.

>> **Fencing tokens:** When a lock expires while the holder is still working (GC pause, network delay, slow process), another process can acquire it. Two processes think they hold the lock. Use fencing tokens: a monotonically increasing number per lock acquisition. The storage layer rejects writes with tokens lower than the last one seen, blocking stale writes from expired holders.

### Saga Pattern

The **saga pattern** breaks the operation into steps. Each step is a committed transaction. If a later step fails, run compensating transactions to undo earlier steps.

![Saga Pattern: Compensating Transactions](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-saga-pattern.svg)

For a bank transfer: Step 1 is debit Alice in Database A, commit. Step 2 is credit Bob in Database B, commit. Step 3 is send notifications. If Step 2 fails (Bob's account does not exist), compensate Step 1 by crediting Alice back. No long-running transactions holding locks across network calls.

### Compensating Transactions in Detail

Every forward step in a saga must have a defined compensation before implementation. Compensations are semantic undos, not database rollbacks. The forward step already committed, so the compensation is a new action that reverses the business effect.

![Compensating Transactions in Practice](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-compensating-transactions.svg)

Sagas need a durable orchestrator to track which steps completed. If the coordinator crashes after Step 1, it must resume and either complete remaining steps or run compensations. Workflow engines (Temporal, Cadence) or a state machine backed by a database handle this.

>> **Temporary inconsistency:** During execution, the system is temporarily inconsistent. After Step 1, Alice's balance is lower but Bob's is not yet higher. Design the application to handle intermediate states, such as showing transfers as "pending" until all steps complete. This tradeoff avoids 2PC blocking.

---

## Choosing the Right Approach

Start with: can you keep all contended data in a single database? If yes, use pessimistic or optimistic based on conflict frequency.

![Contention Decision Tree](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-contention-decision-tree.svg)

### Optimistic vs Pessimistic: The Core Tradeoff

The choice between optimistic and pessimistic concurrency control comes down to contention level. Under low contention, optimistic wins because no locks are held and throughput is higher. Under high contention, pessimistic wins because blocked threads waste less work than retried transactions.

![Optimistic vs Pessimistic: When to Use Which](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-optimistic-vs-pessimistic.svg)

**Approach selection:**

> **Pessimistic locking** - Use when: high contention, critical consistency, single database. Avoid when: low contention, high throughput needs. Latency: low (single DB query). Complexity: low.

> **SERIALIZABLE isolation** - Use when: need automatic conflict detection, cannot identify specific locks. Avoid when: performance critical, high contention. Latency: medium (conflict detection overhead). Complexity: low.

> **Optimistic concurrency** - Use when: low contention, high read/write ratio, performance critical. Avoid when: high contention, cannot tolerate retries. Latency: low when no conflicts. Complexity: medium.

> **Distributed transactions (2PC)** - Use when: must have atomicity across systems, can tolerate complexity. Avoid when: high availability requirements, performance critical. Latency: high (network coordination). Complexity: very high.

> **Distributed locks** - Use when: user-facing flows, need reservations, simpler than 2PC. Avoid when: no alternatives, purely technical coordination. Latency: low (simple status updates). Complexity: medium.

>> When in doubt, start with pessimistic locking in a single database. It is simple, predictable, and you can always improve later.

---

## When to Use in Interviews

Do not wait for the interviewer to ask about contention. When you see multiple processes competing for the same resource, call it out and suggest coordination.

### Common Interview Scenarios

![Interview Scenarios: Pattern Matching](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-interview-scenarios.svg)

> **Online Auction** - Optimistic concurrency. Use current high bid as "version" (bids only go up, no ABA). Accept new bids only if higher than expected current bid.

> **Ticketmaster / Event Booking** - Temporary reservations beat pure locking. Reserve seats with 10-minute TTL when selected. Avoids users losing seats after filling payment info.

> **Banking / Payment Systems** - Distributed transactions. Start with sagas for resilience; mention 2PC if interviewer pushes strict consistency.

> **Ride Sharing Dispatch** - Temporary status reservations. Set driver to "pending_request" when sending requests. Use cache with TTL or DB status fields with cleanup jobs.

> **Flash Sale / Inventory** - Mix of optimistic concurrency (version column for inventory) and cart "holds" (distributed locks with TTL).

> **Yelp / Review Systems** - Optimistic concurrency. Dedicated version column for restaurant average rating; update only if version matches to avoid corrupted calculations when reviews arrive simultaneously.

>> Strong candidates identify contention before being asked: "This auction will have multiple bidders competing. I will use optimistic concurrency with the current high bid as my version check." "For ticketing, I will implement seat reservations with a 10-minute timeout to avoid users losing seats after payment." "Since we are sharding accounts, cross-shard transfers need sagas for resilience."

### When NOT to Overcomplicate

Do not reach for distributed locks (Redis, etc.) when a simple database transaction with row locking or OCC is enough.

> Low contention (e.g. admin-only product description edits) - Basic optimistic concurrency with retry.

> Single-user operations (todo lists, private docs, preferences) - No coordination needed.

> Read-heavy with occasional writes - Simple OCC for rare write conflicts.

---

## Common Deep Dives

### How do you prevent deadlocks with pessimistic locking?

Example: Alice transfers $100 to Bob while Bob transfers $50 to Alice. Transaction A locks Alice first, then tries Bob. Transaction B locks Bob first, then tries Alice. Both wait forever.

![Deadlock: Circular Lock Dependency](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-deadlock.svg)

Deadlocks happen when transactions acquire locks in different orders. Use **ordered locking**: always acquire locks in a consistent order (e.g. sort by user ID). For a transfer between users 123 and 456, always lock 123 first regardless of who initiated. The exact scheme does not matter as long as it is globally consistent.

As a fallback: transaction timeouts and database deadlock detection. Set timeouts so deadlocked transactions are killed and can retry with correct ordering.

### What if your coordinator crashes during a distributed transaction?

Classic 2PC failure. Databases hold prepared transactions, waiting for commit or abort. They hold locks and block other operations.

Production systems use coordinator failover and recovery. A new coordinator reads persistent logs, finds in-flight transactions, and completes them. Design for coordinator high availability.

Sagas are more resilient: no locks across network calls. Coordinator failure pauses progress rather than leaving participants blocked.

### How do you handle the ABA problem with optimistic concurrency?

ABA: a value goes from A to B and back to A. Your optimistic check sees the same value and assumes nothing changed.

Example: a restaurant has 4.0 stars and 100 reviews. Two new reviews (5 and 3 stars) arrive. Both see 4.0 and compute new averages. The math might yield 4.0 again with 102 reviews. Using average as "version," both could pass the check and corrupt the count.

Use a **dedicated version column** that increments on every update. Update only if version matches what you read. Do not use business values like review_count as version unless they only increase; if reviews can be deleted, count can go 100 to 99 to 100 (ABA).

### What is write skew and how do you prevent it?

**Write skew** is a subtle anomaly where two transactions read the same data but write to different rows, violating a constraint that spans multiple rows.

![Write Skew: The Subtle Anomaly](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-write-skew.svg)

REPEATABLE READ misses write skew because each transaction consistently sees its own snapshot and they write different rows. There is no row-level conflict for the database to detect. Only SERIALIZABLE isolation or explicit locking of all rows involved in the constraint can prevent it.

### What about performance when everyone wants the same resource?

Hot partition or celebrity problem: everyone hammers one resource. Sharding does not help (you cannot split one Taylor Swift concert). Load balancing just spreads requests to servers that all hit the same DB row. Read replicas do not help because the bottleneck is writes.

First: can you change the problem? Maybe 10 identical items with separate auctions. Maybe eventual consistency for social follows.

For strong consistency on a hot resource, use **queue-based serialization**. Put all requests for that resource into a dedicated queue processed by a single worker. Operations become sequential; contention disappears. The queue absorbs spikes. Tradeoff: higher latency for users.

---

## Summary

![Contention Solutions: Complete Summary](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/dc-scaling-summary.svg)

>> Exhaust every single-database solution before considering distributed coordination. Modern databases handle tens of terabytes and thousands of concurrent connections. The complexity jump to distributed coordination adds overhead and often worse performance.

> **Atomicity** - Transactions for single-DB consistency. Check affected row count; READ COMMITTED alone does not prevent races.

> **Pessimistic** - Lock first (FOR UPDATE) when conflicts are common. Order locks to avoid deadlocks. Keep lock scope narrow.

> **Optimistic** - Version check when conflicts are rare. Dedicated version column avoids ABA. CAS pattern works across SQL, NoSQL, and caches.

> **Isolation levels** - SERIALIZABLE for automatic conflict detection; explicit locks for efficiency. Understand MVCC to reason about what you see.

> **Distributed** - 2PC for strong consistency (coordinator log, blocking tradeoff); sagas for resilience and temporary inconsistency.

> **Distributed locks** - Redis, ZooKeeper/etcd. Use reservations for UX; use fencing tokens when TTL can expire early.

Good system designers keep data together as long as possible and pick the right coordination pattern for their consistency requirements.

{{SUBSCRIBE}}

{{BUTTON:Read More Articles|https://newsletter.systemdesignlaws.xyz}}

# Scaling Writes

**TL;DR** - Scale writes in four tiers: vertical scaling with write-optimized databases, sharding to spread load, queues and load shedding for bursts, batching and hierarchical aggregation to reduce volume. Each tier addresses a different constraint. Start simple, escalate when math proves you need it.

>> 30-second elevator pitch: "Write scaling is harder than read scaling because every write must persist to disk. I exhaust vertical scaling and database tuning first. Then I shard by partition key to spread load linearly. For bursty traffic I add queues and load shedding. For extreme volume I batch writes and use hierarchical aggregation. Each tier builds on the previous one, and I always justify the complexity with back-of-the-envelope math."

---

## The Problem

Consider a social media platform during a major sporting event. Millions of users post reactions simultaneously. Each post triggers multiple writes: the post itself, index updates for search, counter increments for trending topics, and fan-out to follower feeds. A single database handling 1,000 writes per second faces millions of incoming writes.

This is not a software bug you can optimize away. It is physics. Disk I/O has fixed throughput. CPU cores execute a finite number of instructions per second. Network bandwidth is bounded by hardware. When you hit these walls, only architectural solutions work.

The asymmetry between reads and writes makes this harder. Reads can be cached, replicated, and served from memory. Writes must persist to durable storage. You cannot cache a write. Every write must eventually reach disk.

![Write Bottleneck: The Core Problem](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-write-bottleneck.svg)

>> Reads are cacheable. Writes are not. This fundamental asymmetry is why write scaling requires different techniques than read scaling. You cannot replicate your way out of a write bottleneck.

**6 problems that use this pattern:** YouTube Top K, Strava, Rate Limiter, Ad Click Aggregator, Facebook Post Search, Metrics Monitoring.

---

## What You Will Learn

> **Tier 1: Vertical Scaling and Database Choice** (cheapest, start here)
> - Hardware upgrades (200 cores, NVMe SSDs, 10Gbps links)
> - Write-optimized databases (Cassandra, time-series, LevelDB, ClickHouse)
> - Database tuning (disable FK/triggers, batch WAL syncs, reduce indexes)
>
> **Tier 2: Sharding and Partitioning** (when single DB hits ceiling)
> - Horizontal sharding (hash-based, range-based, consistent hashing)
> - Partition key selection (flat distribution, minimize variance)
> - Vertical partitioning (split tables by access pattern)
>
> **Tier 3: Queues and Load Shedding** (for bursty traffic)
> - Write queues (Kafka, SQS) for burst absorption
> - Load shedding (drop low-value writes to survive)
> - Queue-based write leveling
>
> **Tier 4: Batching and Hierarchical Aggregation** (reduce write volume)
> - Batching at app, intermediate, and DB layers
> - Hierarchical aggregation for fan-in/fan-out
> - Counter sharding for high-contention counters
>
> **Deep Dives** (what interviewers ask next)
> - Resharding without downtime (dual-write migration)
> - Hot key problem (split all keys, split hot keys dynamically)
> - Write amplification and compaction

---

## The Solution: Four Strategies

Write scaling follows a progression from simple optimization to distributed architecture. Each tier addresses a different scaling constraint: hardware limits, single-server capacity, traffic bursts, and write volume.

![Scaling Writes: Complete Summary](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-scaling-summary.svg)

> **What interviewers want to hear:** "I exhaust vertical scaling and database tuning first. Then I shard by partition key to spread load linearly. For bursts I use queues. For extreme volume I batch and aggregate to reduce the number of writes hitting the database." Most candidates jump straight to Kafka without doing the math.

---

## Tier 1: Vertical Scaling and Database Choice

Before adding distributed complexity, exhaust what a single server can do. Do back-of-the-envelope math: what is your write throughput versus hardware limits? Many candidates assume 4-8 cores and a spinning disk. In practice, servers with 200 CPU cores, NVMe SSDs, and 10Gbps network interfaces are standard in cloud environments.

### Vertical Scaling

Writes are bottlenecked by three physical resources: disk I/O, CPU, and network bandwidth. Confirm you are hitting those walls before adding infrastructure.

![Vertical Scaling + Write Optimization](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-vertical-scaling.svg)

- **SSDs instead of HDDs** - 10-100x faster random I/O. NVMe SSDs provide 500K+ IOPS versus 200 IOPS for spinning disks.
- **More RAM** - Larger buffer pools mean fewer disk flushes. Hot data stays in memory longer.
- **Faster CPUs, more cores** - Handle more concurrent write transactions. Modern servers offer 200+ cores.
- **10Gbps+ NICs** - Network rarely bottlenecks single-server writes, but matters for replication.

> **Staff-level insight:** Make the case that modern hardware goes further than many assume. A well-tuned PostgreSQL on modern hardware handles 50,000+ writes per second. But interviewers frequently move the goalposts until you must scale architecturally. Show you understand both paths.

### Write-Optimized Databases

Most applications use general-purpose databases optimized for a balance of reads and writes. Write-heavy systems benefit from databases that sacrifice read performance for write throughput.

**Cassandra** achieves superior write throughput through its append-only commit log. Instead of updating data in place (which requires expensive disk seeks to find the right page), Cassandra writes sequentially to disk. This yields 10,000+ writes per second on modest hardware versus roughly 1,000 for a traditional RDBMS updating B-tree indexes in place.

![LSM-Tree vs B-Tree](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-lsm-tree.svg)

The key insight is the difference between B-tree storage and LSM-tree storage. B-trees update data in place, requiring random disk seeks. LSM-trees (used by Cassandra, LevelDB, RocksDB) append all writes sequentially, then merge and sort in the background.

![Append-Only Log Pattern](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-append-only-log.svg)

**Other write-optimized options:**

- **Time-series databases** (InfluxDB, TimescaleDB) - High-volume sequential writes with timestamps. Built-in delta encoding compresses similar values. Ideal for metrics collection where writes are append-only and ordered by time.
- **Log-structured databases** (LevelDB, RocksDB) - Append new data rather than updating in place. Writes are always sequential. Reads may need to check multiple files.
- **Column stores** (ClickHouse) - Batch writes efficiently for analytics workloads. Compress columnar data aggressively. Optimized for bulk inserts, not single-row writes.

### Database Tuning

Before swapping databases, tune what you have. These changes can provide 5-10x improvement:

- **Disable expensive features** - Foreign key constraints, complex triggers, and full-text search indexing all add overhead to every write. Disable during high-write periods or enforce constraints at the application layer.
- **Batch WAL syncs** - PostgreSQL can group multiple transactions into a single fsync call. Instead of one disk sync per transaction, batch 100 transactions into one sync. 10x throughput improvement.
- **Reduce index overhead** - Every index on a table adds a write for every INSERT. A table with 5 indexes means each logical write becomes 6 physical writes. Remove indexes that serve only rare queries.

![Write-Ahead Log (WAL)](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-write-ahead-log.svg)

>> Do not say "use a faster database" in an interview. Explain WHY Cassandra's append-only writes are faster than MySQL's B-tree updates. Explain the trade-off: Cassandra sacrifices read performance because reads must check multiple SSTables and merge results.

### Write Amplification

One logical write often becomes multiple physical disk writes. Understanding write amplification explains why reducing indexes and tuning WAL matters.

![Write Amplification](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-write-amplification.svg)

A single INSERT into a table with two indexes generates: one WAL append, two to three disk writes per index update, and one replication sync. That is 6-8 physical writes for one logical write. With 5 indexes, it can be 15-20x amplification.

> **Interview tip:** When you propose adding an index to speed up reads, acknowledge the write cost. "This index will speed up our search queries from O(n) to O(log n), but each write now has an additional index update. Given our 100:1 read-to-write ratio, this trade-off is clearly worth it."

---

## Tier 2: Sharding and Partitioning

When one server handles 1,000 writes per second, 10 servers should handle 10,000. Sharding spreads write volume across multiple servers so each handles a manageable portion. This is the most common write scaling technique you will use in interviews.

### Horizontal Sharding

The basic idea: hash each record's key to determine which server stores it. All writes for that key go to one server. Add servers to scale linearly.

![Horizontal Sharding](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-horizontal-sharding.svg)

**Redis Cluster** illustrates a straightforward implementation. Each entry has a single string key. Keys are hashed (via CRC16) to determine a slot number from 0-16383. Slot numbers map to cluster nodes. Clients hash the key, look up the responsible server, and send the write there.

**Consistent hashing** provides a more flexible alternative. Instead of modular arithmetic (which requires rehashing everything when you add nodes), consistent hashing maps both keys and nodes onto a ring. Adding a node only remaps roughly 1/N of existing keys.

![Consistent Hashing](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-consistent-hashing.svg)

### Selecting a Partition Key

The most important sharding decision: which field do you hash?

![Shard Key Selection](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-shard-key-selection.svg)

**Good key** - Hashing user_id spreads data evenly across shards. You realize the Nx gain by multiplying servers. Each user's writes concentrate on one shard, which is manageable because individual users produce limited write volume.

**Bad key** - Partitioning by country sends most writes to heavily populated regions. China and the US overloaded. New Zealand and Iceland nearly idle. The variance between shards kills your scaling gains.

> **Principle:** Select a key that minimizes variance in writes per shard. Flat is good. Hash a primary identifier (user_id, post_id, device_id) whenever possible.

Also consider the read path. If every request must hit every shard (scatter-gather), you have traded a write bottleneck for a read bottleneck. Choose a scheme that spreads writes evenly AND groups commonly accessed data together. Ask yourself: "How many shards does this request hit?" and "How often does this request happen?"

### Partitioning Strategies

Three main approaches, each suited to different workloads:

![Partitioning Strategies](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-partitioning-strategies.svg)

### Vertical Partitioning

**Vertical partitioning** splits columns by access pattern. Instead of one massive table where content writes, metric updates, and analytics scans compete for the same locks, split into specialized tables.

**Schema: post_content (write-once, read-many)**

- **post_id** integer, primary key - Post identifier
- **user_id** integer - Author
- **content** text - Post body
- **media_urls** text array - Attachments
- **created_at** timestamp - Publication time

**Schema: post_metrics (high-frequency writes)**

- **post_id** integer, primary key - Post identifier
- **like_count** integer - Like count
- **comment_count** integer - Comment count
- **view_count** integer - View count
- **last_updated** timestamp - Last metric update

**Schema: post_analytics (append-only, time-series)**

- **post_id** integer - Post identifier
- **event_type** varchar - Event type (view, click, share)
- **timestamp** timestamp - Event time
- **user_id** integer - Actor who triggered event

Each table lives on a different database instance. Post content uses traditional B-tree indexes optimized for reads. Post metrics might use in-memory storage or specialized counters. Post analytics uses time-series or column-oriented storage optimized for high-volume appends.

---

## Tier 3: Queues and Load Shedding

Sharding handles steady-state load, but real-world traffic is bursty. What happens when order volume quadruples on Black Friday, or ride requests triple on New Year's Eve? Autoscaling helps but takes minutes. Database scaling often means downtime. You either buffer writes or drop the least valuable ones.

### Write Queues

Add a message queue (Kafka, SQS) between the application and the database. Writes go to the queue instantly. Workers drain the queue at a sustainable rate matched to database capacity.

![Write Queue: Burst Absorption](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-write-queue.svg)

The application only knows the write was recorded in the queue, not that it reached the database. Clients may need a callback or polling mechanism to confirm persistence.

![Queue-Based Write Leveling](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-queue-based-leveling.svg)

**Burst absorption** - The queue buffers spikes. The database processes writes at a steady rate regardless of incoming traffic.

**Unbounded growth risk** - If the application writes faster than the database drains for an extended period, the queue grows without bound. Latency increases continuously. Users wait longer and longer for writes to take effect.

> **Important:** Use queues for short-lived bursts, not to mask a database that cannot handle steady-state load. If your queue depth grows monotonically, you have a capacity problem, not a burst problem. Understand your system's tolerance for delayed writes before introducing queues.

### Load Shedding

When overwhelmed beyond what a queue can absorb, decide which writes to accept and which to reject. **Load shedding** keeps the system running by dropping the least valuable writes.

![Load Shedding](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-load-shedding.svg)

**Uber and Strava** - Users report location at regular intervals (every 3-5 seconds). If the system is overloaded, dropping one update is acceptable because a fresher update arrives moments later. Drop GPS updates that are within seconds of the previous recorded position.

**Analytics** - Drop impression events before click events. Clicks drive revenue. A 5% loss in impression tracking is acceptable; a 5% loss in click tracking is not.

**Metrics Monitoring** - Downsample from per-second to per-minute averages during overload. Approximate monitoring data is far better than no monitoring data.

>> Putting release valves in place shows interviewers you can keep a bad situation (too much load) from becoming a disaster (total failure), even if it means a suboptimal experience for some users. Graceful degradation beats catastrophic failure every time.

---

## Tier 4: Batching and Hierarchical Aggregation

You can also change the structure of writes to make them more efficient. Individual writes carry overhead: network round trips, transaction setup, index updates, disk syncs. Databases process batches far more efficiently than equivalent individual operations.

### Batching

Combine multiple individual writes into a single bulk operation. The savings come from amortizing fixed costs (network round trip, transaction commit, disk sync) across many writes.

![Batching Writes](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-batching.svg)

**Application layer** - Clients buffer writes before sending. Works well when the application is not the source of truth (for example, a Kafka consumer processing events and writing to a database). If the app crashes mid-batch, re-read from Kafka. If the application is the source of truth, batching risks data loss on crash.

**Intermediate processing** - A **Like Batcher** receives like events, accumulates count changes per post over a time window, and forwards aggregated updates. If a post gets 100 likes in one minute, that reduces 100 individual counter increments to a single atomic update of +100.

> **Staff-level nuance:** If most posts receive 1 like per hour, a 1-minute batch window provides zero benefit because the batch contains exactly 1 write. Ensure batching actually matches your workload distribution. Batching helps when multiple writes target the same key within the batch window.

**Database layer** - Redis flushes to disk every 100ms by default (with AOF appendfsync everysec). A burst of 1,000 writes in one batch results in one disk write 100ms after the last write arrives. This is powerful but comes with durability risk: data written to memory but not yet flushed is lost on crash.

### Hierarchical Aggregation

For extreme fan-in/fan-out scenarios (like live video comments), aggregate at intermediate nodes instead of writing every event to every destination.

![Hierarchical Aggregation](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-hierarchical-aggregation.svg)

**Live comments** - Millions of viewers can comment and react. Each event must reach all peers for a shared experience. That means millions of writes from millions of writers - an N-squared problem.

**Broadcast nodes** - Assign viewers to broadcast nodes (via consistent hashing or geographic proximity). Writers send events to a small number of broadcast nodes instead of directly to all viewers. Each broadcast node forwards to its assigned viewers.

**Write processors** - Intermediate aggregation layer. Each write processor accumulates events (for example, like counts) over a time window and forwards batched updates upstream. The root aggregator merges results from all write processors.

> **Result:** By aggregating with write processors (fan-in) and distributing with broadcast nodes (fan-out), you transform an N-squared problem into an N-times-M problem where M is the number of intermediate nodes. Trade-off: added latency from extra hops.

### Counter Sharding

A specific and common application of write scaling: high-contention counters. When millions of users increment the same counter (like counts, view counts, rate limiter counters), the single row becomes a bottleneck.

![Counter Sharding](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-counter-sharding.svg)

Split the counter across N sub-keys. Writers increment a random sub-key. Readers sum all sub-keys to get the total. Write throughput scales linearly with N. Read cost increases linearly with N (scatter-gather). Choose N to balance write throughput against read overhead.

### Fan-Out on Write

A related pattern that converts read-time computation into write-time pre-computation:

![Fan-Out on Write vs Read](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-fanout-on-write.svg)

When a user creates a post, immediately write it to every follower's feed (fan-out on write). Reads become a simple lookup of the pre-computed feed. The trade-off: one post from a celebrity with 10 million followers means 10 million writes. Most production systems use a hybrid: fan-out on write for normal users, fan-out on read for celebrities.

---

## Common Deep Dives

### "How do you handle resharding when you need to add more shards?"

You started with 8 shards and now need 16. Rehashing everything offline creates hours of downtime for large datasets. **Gradual migration** using dual-writes avoids this.

![Resharding Strategy](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-resharding.svg)

Deploy the new shard configuration. All new writes go to both old and new locations (dual-write). A background job copies existing data from old shards to new shards. Once migration completes and data is verified consistent, switch reads to the new shards and decommission the old ones. Zero downtime because the system stays available throughout.

> **Why dual-write:** No data is lost during migration because both locations receive all writes. The new shards accumulate both migrated historical data and real-time writes. When you cut over, they are fully up to date.

### "What happens when a single key is too popular for even one shard?"

A viral tweet gets 100,000 likes per second. Even with perfect hash distribution across shards, ALL writes for this one key route to a single shard. That shard overloads while others sit idle.

![Hot Key Problem](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-hot-key-problem.svg)

![Hot Key Split Strategy](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-hot-key-split.svg)

**Split all keys** - Store post1:likes as post1:likes-0, post1:likes-1, through post1:likes-k-1. Each sub-key routes to a different shard. Write volume per shard drops by k. Downside: dataset size and read overhead multiply by k. Works when a small k brings the hot shard back within capacity.

**Split hot keys dynamically** - Split only keys that become hot. For the viral tweet, dynamically create 100 sub-keys. Normal posts keep a single key. This requires a detection mechanism (monitor write rate per key) and coordination so readers know which keys are split.

**Reader coordination** - Writers and readers must agree on which keys are split. Option 1: readers always check all sub-keys (simple, same read amplification). Option 2: writers announce splits to readers via a metadata service (efficient, more complex). Most production systems use option 1 for simplicity.

### "What about compaction overhead in LSM-tree databases?"

Compaction is the background process that merges and sorts SSTable files in LSM-tree databases. It reclaims space from deleted or overwritten entries and improves read performance by reducing the number of files to check.

![Compaction in LSM Storage](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-compaction.svg)

The trade-off: compaction consumes background I/O that competes with write throughput. During a compaction storm (when many files need merging simultaneously), write latency can spike. Tune compaction concurrency and throttling to match your workload.

---

## When to Use in Interviews

![Write Path: End-to-End Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-write-path-flow.svg)

>> Proactively identify write bottlenecks. When sketching your design, say: "With millions of users posting content, we will quickly hit write bottlenecks. Let me estimate write throughput... At 10 million daily active users posting 2 messages each, that is 230 writes per second average but 2,000+ at peak. A single PostgreSQL instance handles this fine. I will note it as a scaling concern for growth."

![Decision Tree: Scaling Writes](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-decision-tree.svg)

![Interview Scenarios: Write Scaling](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/sw-interview-scenarios.svg)

**Common scenarios with specific advice:**

- **YouTube Top K** - Millions of view/like events per second. Shard counters by video_id. Use hierarchical aggregation: local counters at edge, periodic merge to central store. Top-K computed from pre-aggregated data.
- **Strava** - GPS location updates every 3-5 seconds from millions of active users. Load shed stale updates. Queue for burst absorption during popular events. Time-series database for storage.
- **Rate Limiter** - Counter increment per user per time window. Shard by user_id. Counter sharding for high-traffic users. Redis with atomic INCR for low-latency writes.
- **Ad Click Aggregator** - Click events must be counted accurately (revenue depends on it). Batch clicks per ad_id over short windows. Kafka for durability. Reconciliation jobs for accuracy.
- **Facebook Post Search** - Every new post must be indexed for search. Queue index updates. Batch index writes (Lucene/Elasticsearch segments). Shard index by term or document.
- **Metrics Monitoring** - High-volume time-series writes from thousands of servers. Range partition by timestamp. Batch writes per time window. Downsample old data.

**When NOT to use write scaling techniques:**

- **Read-heavy systems** - If your read-to-write ratio is 100:1, focus on read scaling. Write optimization provides marginal benefit.
- **Modest write volume** - Do back-of-the-envelope math. 100 writes per second does not need Kafka. A single well-tuned database handles thousands of writes per second. Adding distributed complexity for no reason hurts more than it helps.
- **When consistency matters most** - Each write scaling technique introduces trade-offs. Queues mean eventual consistency. Batching adds latency. Sharding complicates transactions. Show you understand the cost before proposing the solution.

---

## Summary

>> Write scaling is about reducing throughput per component. Whether you spread 10,000 writes across 10 shards, smooth bursts through queues, or batch 100 operations into 1 bulk insert, you apply the same principle: make each component handle manageable load. Start with the simplest solution that satisfies your requirements.

- **1. Vertical + DB choice** - Hardware upgrades and write-optimized databases first. Cassandra LSM-trees, time-series DBs, tuned WAL. A single well-configured server handles 50K+ writes per second.
- **2. Sharding** - Partition key with minimal variance. Hash user_id or post_id. Consistent hashing for easy resharding. Vertical partitioning for mixed workloads.
- **3. Queues + load shedding** - Kafka/SQS for short-lived bursts. Load shedding when dropping writes is acceptable (GPS updates, analytics impressions). Never use queues to mask steady-state capacity shortfall.
- **4. Batching + aggregation** - Batch at app, intermediate (Like Batcher), or DB layer. Hierarchical aggregation for fan-in/fan-out. Counter sharding for high-contention incrementing.
- **5. Deep dives** - Resharding via dual-write. Hot keys: sub-key split with scatter-gather reads. Write amplification awareness when proposing indexes.

In interviews, demonstrate that you understand the physics behind write bottlenecks, the trade-offs of each technique, and the progression from simple to complex. Always justify complexity with math.

{{SUBSCRIBE}}

{{BUTTON:Read More Articles|https://newsletter.systemdesignlaws.xyz}}

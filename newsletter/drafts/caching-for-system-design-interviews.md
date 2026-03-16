# Caching for System Design Interviews

**TL;DR** - Caching cuts latency 50x and reduces DB load by 95%+. Cache-aside with Redis is the default. Layer CDN for global users, in-process for ultra-hot keys, and client-side for offline access. Master invalidation and you cover 90% of interview caching questions.

>> 30-second elevator pitch: "Caching stores frequently accessed data in memory so reads skip the database. I start with cache-aside using Redis as the default, add CDN for global static assets, and choose invalidation strategy based on freshness requirements. Cache-aside handles most scenarios, and I layer additional strategies only when the problem demands it."

---

## The Problem

Reading a user profile from PostgreSQL takes 5-50ms. Reading the same profile from Redis takes ~1ms. That is a 50x improvement. Databases hit disk. Caches serve from memory.

Consider a social media feed. When you open the app, it fetches dozens of posts, each with user info, like counts, and comment previews. That is 100+ read operations just to render a feed. Now multiply by millions of concurrent users. Your database cannot handle that load -- but a cache can, because the same popular content gets requested millions of times.

This imbalance is everywhere. For every tweet posted, thousands read it. For every product listed on Amazon, hundreds browse it. Caching exploits this skewed access pattern: a small set of data accounts for the majority of reads.

![Caching Layers Overview](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/caching-layers-overview.svg)

**14 problems that use this pattern:** Distributed Cache, Rate Limiter, URL Shortener, Instagram, Facebook News Feed, YouTube, Ticketmaster, Yelp, Facebook Post Search, Local Delivery, News Aggregator, Metrics Monitoring, Top-K Problem, Notification System.

---

## What You Will Learn

> **Where to Cache** (pick the right layer)
> - External caching (Redis, Memcached)
> - CDN edge caching
> - Client-side caching
> - In-process caching
>
> **Cache Architectures** (how reads and writes flow)
> - Cache-aside (lazy loading) -- the default
> - Write-through, write-behind, read-through
> - Pattern comparison and trade-offs
>
> **Invalidation and Consistency** (keeping cache fresh)
> - TTL, event-driven, versioned keys
> - Consistency models
> - Cache warming
>
> **Deep Dives** (what interviewers ask next)
> - Cache stampede and thundering herd
> - Hot key fanout and request coalescing
> - Eviction policies (LRU, LFU, FIFO)
> - Redis vs Memcached
> - Distributed cache topology

---

## The Solution

Caching follows a progression: start with external cache (Redis), add CDN for global reach, and layer in-process caching only for ultra-hot keys. Each layer adds complexity. Start simple.

![Cache Hit vs Miss - Full Request Lifecycle](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-hit-miss-flow.svg)

> **What interviewers want to hear:** "I would start with cache-aside using Redis for our hot read paths. If we need global distribution, I would add a CDN. The key trade-off is freshness vs complexity -- TTL gives us simplicity, write-through gives us consistency."

---

## Where to Cache

### External Caching (Redis, Memcached)

A standalone cache service shared across application servers. Every app instance talks to the same cache. This is the default caching layer in system design interviews.

**How it works:** Application checks cache first. On hit, return immediately (~1ms). On miss, fetch from DB (5-50ms), store in cache with TTL, return.

**Use when:** High read traffic, shared hot data across instances. This is your baseline answer.

![Cache-Aside Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-aside-flow.svg)

### CDN (Content Delivery Network)

A **CDN** is a network of geographically distributed edge servers that cache content close to users. Cloudflare, Fastly, and Akamai operate hundreds of edge locations worldwide.

Without a CDN, a user in Tokyo requesting an image from a Virginia server experiences 250-300ms of network latency. With a CDN, the Tokyo edge server serves the cached image in 20-40ms.

![CDN Edge Caching Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-cdn-flow.svg)

**Introduce when:** Static assets at global scale -- images, video thumbnails, CSS/JS bundles. CDNs reduce origin load by 90%+. Do not cache user-specific private data at the edge.

### Client-Side Caching

**Client-side caching** stores data on the user's device -- browser localStorage, sessionStorage, IndexedDB, or native app storage. Zero network latency because the data is already local.

Strava keeps run data on-device for offline use, then syncs when connectivity returns. This reduces API calls and enables offline access.

![Client-Side Caching](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-client-side.svg)

**Mention as:** An optimization layer. Limited backend control over invalidation makes it secondary to server-side caching.

### In-Process Caching

**In-process caching** stores data in the application's local memory. No network hop. Faster than Redis for small, frequently accessed data -- feature flags, configuration, rate-limit counters.

The limitation: each app instance maintains its own separate cache. Updates on one instance do not propagate to others. This means short TTLs or broadcast invalidation are necessary.

![In-Process Caching](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-in-process.svg)

**Mention after:** You have already introduced external cache. In-process is a supplementary optimization, not a primary caching strategy.

---

## Cache Architectures

How you read and write cached data determines performance and consistency. Know these four patterns.

![Cache Patterns Comparison](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-write-patterns-comparison.svg)

### Cache-Aside (Lazy Loading)

**The default pattern for interviews.** Application manages both cache and database.

1. App checks cache
2. Hit -- return immediately (~1ms)
3. Miss -- fetch from DB, store in cache with TTL, return

Cache-aside only stores data when it is requested. This keeps the cache lean -- only hot data stays cached. The trade-off is cold start latency: the first request for any key hits the database.

![Cache-Aside Pattern](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-aside-pattern.svg)

### Write-Through

**Write-through** writes to cache and database synchronously. Both must succeed before returning to the caller. The cache is always fresh -- reads never see stale data.

The cost: every write has 2x latency (cache write + DB write). Cache gets polluted with data that may never be read. Redis does not support write-through natively -- you need application logic.

![Write-Through Cache](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-write-through.svg)

**Use when:** Reads must always return the latest data and you can accept slower writes. Financial balances, inventory counts.

### Write-Behind (Write-Back)

**Write-behind** writes to cache first (fast return), then asynchronously batches writes to the database. Writes are fast because the caller only waits for the cache write.

The risk: if the cache dies before flushing to the database, queued writes are lost. This is eventual consistency with a data loss window.

![Write-Behind Cache](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-write-behind.svg)

**Use when:** Write throughput matters more than durability. Analytics ingestion, view counters, metrics.

### Read-Through

**Read-through** puts the cache in front of the database as a data access layer. The application asks the cache, and on a miss, the cache fetches from the database and populates itself. The application never touches the database directly.

![Read-Through Cache](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-read-through.svg)

**Use when:** You want to simplify application code by making the cache the single data access point.

---

## Invalidation and Consistency

**Cache invalidation** is the process of removing or updating cached data when the source changes. Getting this wrong means users see stale data -- or worse, the system acts on outdated information.

![Cache Invalidation Strategies](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-invalidation-strategies.svg)

### TTL (Time-Based Expiration)

**TTL** sets a fixed lifetime on each cached entry. When the timer expires, the entry is evicted and the next request fetches fresh data. Simple to implement. The downside: stale data during the TTL window.

How to set TTL: driven by non-functional requirements. "Search results should be no more than 30 seconds stale" gives you a 30-second TTL.

![TTL Expiration Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-ttl-mechanism.svg)

### Versioned Keys

**Versioned keys** include a version number in the cache key: event:123:v42. On update, increment the version atomically in the database. Write new data as event:123:v43. The old entry (v42) becomes unreachable -- nobody asks for it. No race conditions because version changes are atomic.

Two cache lookups per request (version + data), but no invalidation complexity.

![Cache Versioning](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-versioning.svg)

### Consistency Models

Cache and database can diverge. Accept eventual consistency or pay for synchronous writes.

- **Strong consistency (write-through):** Cache and DB always agree. Slower writes.
- **Eventual consistency (write-behind):** Cache updated first, DB catches up. Fast writes, staleness window.
- **Stale reads (TTL):** DB is truth. Cache may be stale until expiry. Simplest.

![Cache Consistency Models](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-consistency.svg)

---

## Cache Warming

A cold cache after deploy or restart means 100% miss rate. Every request hits the database. Latency spikes. DB may become overloaded.

- **Pre-populate on deploy:** Startup script loads the top N most-accessed keys from the database.
- **Lazy loading:** Cache fills organically as requests come in. Slower ramp-up but no extra logic.
- **Predictive warming:** Analyze access patterns to pre-load keys that will be needed next.

![Cache Warming Strategies](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-warming.svg)

---

## Common Deep Dives (What Interviewers Ask Next)

### "Cache stampede when a popular entry expires"

A **cache stampede** (thundering herd) happens when a popular cache entry expires and thousands of concurrent requests all see a miss simultaneously. Every one queries the database. Your DB, sized for 1,000 QPS during normal operation, gets hit with 100K identical queries. It crashes.

![Cache Stampede](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-stampede.svg)

Solutions:

- **Distributed lock (SETNX):** First request acquires lock and rebuilds cache. Others wait or serve stale data.
- **Probabilistic early refresh:** As cache entry ages, each request has a random chance of triggering a background refresh before expiration.
- **Background refresh:** Dedicated process refreshes critical entries before they expire. Users never trigger rebuilds.

### "Millions of reads for the same hot key"

A celebrity posts. Millions of users read it. Even with data in memory, serializing and sending it 500K times per second overwhelms a single cache node.

**Request coalescing** combines duplicate in-flight requests. If 1000 requests arrive for the same key simultaneously, only one fetches from the backend. The rest wait for that result.

**Cache key fanout** distributes a hot key across multiple entries: feed:celebrity:1 through feed:celebrity:10. Clients randomly pick one. 500K RPS across 10 keys = 50K each.

![Cache Key Fanout](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-key-fanout.svg)

### "What eviction policy should I use?"

**Eviction policies** determine which entry gets removed when the cache is full.

- **LRU (Least Recently Used):** Evict the item accessed longest ago. Default in Redis. Best general-purpose choice.
- **LFU (Least Frequently Used):** Evict the item with the lowest access count. Better for power-law distributions.
- **FIFO (First In, First Out):** Evict the oldest inserted item. Rarely the right answer.

![Cache Eviction Policies](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-eviction-policies.svg)

### "Redis or Memcached?"

**Redis** is the default answer for interviews. It supports rich data structures (strings, lists, sets, sorted sets, hashes), built-in persistence (RDB snapshots + AOF), primary-replica replication, and pub/sub. Single-threaded event loop -- no lock contention.

**Memcached** is simpler: pure key-value strings, multi-threaded, no persistence. Use only when you need maximum simplicity.

![Memcached vs Redis](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-memcached-vs-redis.svg)

### "How does Redis scale?"

Redis Cluster shards data across multiple nodes using 16384 hash slots. Each key maps to a slot via CRC16(key) mod 16384. The client routes directly to the correct shard -- no central coordinator.

Each shard has replicas for failover. If a primary dies, a replica is promoted automatically via gossip protocol. Each shard handles ~100K ops/sec.

![Redis Cluster Architecture](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-redis-architecture.svg)

### "How do you handle distributed cache node failures?"

**Consistent hashing** distributes keys across cache nodes using a hash ring. When a node fails, only its keys (1/N of total) need to remap to the next node clockwise on the ring. Naive hash-mod remaps all keys.

Virtual nodes (100-200 per physical node) ensure even distribution across the ring.

![Distributed Cache Topology](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-distributed-topology.svg)

### "Multiple caching layers?"

A **multi-layer cache hierarchy** puts faster, smaller caches in front of slower, larger ones. L1 (in-process, 0.1ms) catches 80% of requests. L2 (Redis, 1-5ms) catches 15% more. L3 (CDN, 10-40ms) catches 4%. Only 1% reaches the database.

Add layers incrementally. Most systems need only Redis. Add CDN for global users. Add in-process for ultra-hot keys.

![Multi-Layer Cache Hierarchy](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-multi-layer.svg)

---

## When to Use in Interviews

![Caching Interview Scenarios](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-interview-scenarios.svg)

>> A strong candidate identifies caching opportunities proactively. When you sketch your API design, pause at endpoints that will be hammered and say: "This user profile endpoint will get billions of reads per day. Let me add caching here."

**Common scenarios:**

- **Bit.ly / URL Shortener:** Cache short-to-long URL mapping in Redis with no expiration (URLs rarely change). CDN for global traffic.
- **Ticketmaster:** Cache event details and venue info. Seat availability cannot be cached -- stale data causes overselling.
- **News Feed (Facebook/LinkedIn):** Pre-compute feeds for active users. Cache recent posts aggressively with short TTL.
- **YouTube:** Cache video metadata (titles, thumbnails). View counts can be eventually consistent. CDN for thumbnails.

**When NOT to use caching:**

- **Write-heavy systems** (Uber location tracking) -- focus on write scaling instead
- **Small scale** (1000 users) -- a well-indexed database handles the load
- **Strongly consistent** (financial transactions) -- stale data causes real problems
- **Real-time collaborative** (Google Docs) -- caching actively hurts when every keystroke must be visible

![Caching Strategy Decision Tree](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/cache-decision-tree.svg)

---

## Summary

![Caching Layers Overview](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/caching-layers-overview.svg)

>> Most candidates jump straight to Redis without explaining why. Start with the problem: high read traffic, skewed access patterns. Then introduce caching as the solution. Cache-aside with Redis is your default. Layer CDN, in-process, and client-side only when the problem demands it.

- **Cache-aside + Redis** -- default for high read traffic. Simple, effective.
- **CDN** -- static assets, global users. 90%+ origin load reduction.
- **Write-through** -- when freshness is critical. Accept slower writes.
- **Write-behind** -- when write throughput matters. Accept data loss risk.
- **Invalidation** -- TTL for simplicity, versioned keys for race-free updates, event-driven for critical data.
- **Eviction** -- LRU is the default. LFU for power-law access patterns.
- **Stampede protection** -- distributed lock, probabilistic refresh, or background refresh.

In interviews, demonstrate that you understand both the latency benefits and the consistency trade-offs. Show that you know when to cache aggressively and when to skip caching entirely.

{{SUBSCRIBE}}

{{BUTTON:Read More Articles|https://newsletter.systemdesignlaws.xyz}}

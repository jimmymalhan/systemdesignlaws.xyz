# Real-time Updates

**TL;DR** - Real-time systems need two hops: server to client (WebSockets, SSE, long polling) and source to server (Pub/Sub or consistent hashing). Start with simple polling unless you truly need sub-second latency. WebSockets need L4 load balancers for persistent connections.

>> 30-second elevator pitch: "Real-time updates require efficient push channels. I choose based on latency needs: polling for 2-5 second updates, long polling or SSE for near real-time, WebSockets when I need bidirectional low latency. The second hop is Pub/Sub or consistent hashing to fan out updates from the source to servers."

---

## The Problem

Consider a collaborative document editor like Google Docs. When one user types a character, all other users viewing the document need to see that change within milliseconds. In apps like this you cannot have every user constantly polling the server for updates every few milliseconds without crushing your infrastructure.

The core challenge is establishing efficient, persistent communication channels between clients and servers. Standard HTTP follows a request-response model: clients ask for data, servers respond, then the connection closes. This works great for traditional web browsing but breaks down when you need servers to proactively push updates to clients.

These problems are often solved once by a specialized team, so many candidates have never built them. Do not worry. This pattern covers what you need to make great decisions in your interview.

**9 problems that use this pattern:** Ticketmaster, Uber, WhatsApp, Robinhood, Google Docs, Strava, Online Auction, FB Live Comments, and similar collaborative or live systems.

---

## What You Will Learn

> **Hop 1: Client-Server Connection**
> - Networking 101 (OSI layers, TCP/UDP, L4 vs L7 load balancers)
> - Simple polling (baseline)
> - Long polling (latency trade-off)
> - Server-Sent Events (SSE) - chunked streaming, EventSource, last event ID
> - WebSockets - full-duplex, HTTP upgrade, L4 requirement, deployment
> - WebRTC - peer-to-peer, STUN/TURN, signaling
>
> **Hop 2: Source to Server**
> - Pull polling
> - Push via consistent hashing (ZooKeeper)
> - Push via Pub/Sub (Kafka, Redis)
>
> **Deep Dives** (what interviewers ask next)
> - Connection failures and reconnection
> - Celebrity problem (millions of followers)
> - Message ordering across distributed servers

---

## The Solution: Two Hops

Real-time systems require two distinct pieces: how updates get from the server to the client (Hop 1), and how updates get from the source to the server (Hop 2). The diagram below illustrates both hops: clients connect via polling, long polling, SSE, or WebSockets to endpoint servers; those servers receive updates from the source via pull polling, consistent hashing, or Pub/Sub.

![Real-time Updates - Two Hops](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/real-time-updates-overview.svg)

> **What interviewers want to hear:** "I start with the simplest approach that meets the latency requirement. Many problems do not need WebSockets - polling every 2-5 seconds is fine. If we need sub-second updates, I use long polling or SSE for one-way, WebSockets for bidirectional. The second hop is Pub/Sub or consistent hashing to distribute updates from the source."

---

## Networking 101

Before diving into protocols, a quick primer on how networking works. Networks use a layered architecture (the OSI model). Three layers matter most in system design interviews:

**Network Layer (Layer 3)** - IP handles routing and addressing. It breaks data into packets and provides best-effort delivery. No guarantees: packets can be lost, duplicated, or reordered.

**Transport Layer (Layer 4)** - TCP and UDP provide end-to-end communication. TCP is connection-oriented: you establish a connection first, then data is delivered correctly and in order. TCP connections take time to establish and resources to maintain. UDP is connectionless: you can send to any IP without setup, but there are no delivery or ordering guarantees.

**Application Layer (Layer 7)** - HTTP, DNS, WebSockets, WebRTC. These build on TCP to provide application-level abstractions.

![OSI Layers Relevant to Real-Time Communication](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-osi-layers.svg)

**Request lifecycle.** When you type a URL and press Enter: DNS resolves the domain to an IP. The client initiates a TCP connection via a three-way handshake: SYN, SYN-ACK, ACK. Once connected, the client sends an HTTP GET. The server responds. The connection closes via a four-way teardown: FIN, ACK, FIN, ACK. Each round trip adds latency. The TCP connection represents state that both sides must maintain.

![TCP 3-Way Handshake](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-tcp-handshake.svg)

**With load balancers.** In practice, clients talk to load balancers, which distribute to backend servers. Two types matter:

**Layer 4 load balancers** operate at TCP/UDP. They route by IP and port only, without inspecting packet content. Effectively, it is as if the client has a direct TCP connection to one backend. L4 maintains persistent TCP connections. Fast and efficient. Good for protocols that need persistent connections like WebSockets.

**Layer 7 load balancers** operate at the application layer. They understand HTTP. They can route by URL, headers, cookies. They terminate incoming connections and create new ones to backends. More CPU-intensive. The underlying TCP connection to your server is just a transport; L7 does not guarantee the same backend for every request. L7 is better for HTTP-based solutions like long polling.

![L4 vs L7 Load Balancer](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-l4-vs-l7.svg)

The choice between L4 and L7 comes up when discussing real-time features. L4 is better for WebSockets. L7 offers flexibility for HTTP-based approaches.

---

## Hop 1: Client-Server Connection Protocols

We break down each protocol with its trade-offs. As a motivating example: a chat app where users need new messages sent to their room.

### Simple Polling: The Baseline

The simplest approach: the client makes an HTTP request at a regular interval. The server responds with the current state. For chat, the client polls for "what messages have I not received yet?"

![Simple Polling Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-simple-polling.svg)

**How it works (plain English):** The client calls fetch to /api/updates every N seconds (e.g., 2 seconds). It parses the JSON response and updates the UI. No special setup.

**Advantages:** Simple to implement. Stateless. No special infrastructure. Works with any standard networking. Quick to explain in an interview.

**Disadvantages:** Higher latency (up to polling interval plus request processing). Limited update frequency. More bandwidth. Resource-intensive with many clients (new connections, etc.).

**When to use:** If updates every 2-5 seconds are acceptable, simple polling is a great baseline. Also good when the update window is short. Propose it to your interviewer before jumping to WebSockets. Say: "I will start with simple polling to focus on X, but we can switch if we need more sophistication."

**Interview tip:** Use HTTP keep-alive. Setting a keep-alive longer than the polling interval means you establish the TCP connection once, minimizing setup and teardown overhead.

### Long Polling: The Easy Solution

The client makes a request and the server holds it open until new data is available. When data arrives, the server responds, the client immediately makes a new request, and the cycle repeats. For chat, the client requests the next message; if none exists, the server holds the request until one is sent.

![Long Polling Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-long-polling.svg)

**How it works (plain English):** The client enters a loop. It fetches /api/updates. The server blocks until new data or a timeout. The client receives the response, processes it, and immediately fetches again. On error, it waits briefly and retries.

**Latency trade-off:** Assume 100ms round-trip latency. Two updates occur 10ms apart. With long polling, the first update arrives ~100ms after it occurred. The second can arrive up to ~290ms later: 90ms for the first response to return, 100ms for the second request to reach the server, 100ms for the response. High-frequency updates suffer from this call-back latency.

![Long Polling Latency Problem](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-long-poll-latency.svg)

**Advantages:** Builds on standard HTTP. Works everywhere HTTP works. Easy to implement. No special infrastructure. Stateless server-side.

**Disadvantages:** Higher latency than SSE or WebSockets. More HTTP overhead. Resource-intensive with many clients. Not suitable for frequent updates. Makes monitoring harder (long-hanging requests). Browsers limit concurrent connections per domain.

**When to use:** Near real-time with simple implementation. Good when updates are infrequent. Ideal for long async processes like payment processing: long-poll for payment status until the job finishes, then show the success page.

**Interview tip:** Keep timeouts consistent across the stack. If your load balancer times out at 30 seconds, do not configure long-poll for 60 seconds. 15-30 seconds is common and minimizes fuss.

### Server-Sent Events (SSE): The Efficient One-Way Street

SSE extends long polling by letting the server send a stream of data. Normal HTTP uses Content-Length. SSE uses Transfer-Encoding: chunked - the client does not know how many chunks or how big they are until they arrive. The server sends a chunk, keeps the connection open, and sends more as needed. Perfect when servers push to clients but clients rarely need to send back.

![SSE Chunked Streaming](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-sse-flow.svg)

**How it works (plain English):** The client creates an EventSource pointing to /api/updates. When the server has new data, it writes chunks in a specific format. The client's onmessage handler parses the JSON and updates the UI. On the server, you set headers for text/event-stream, no-cache, keep-alive. You write data as formatted lines. When the client disconnects, you remove listeners and clean up.

**Reconnection:** The SSE standard includes a "last event ID." If the client loses the connection, it reconnects and sends the last event ID. The server can send all events that occurred while the client was disconnected. The browser EventSource handles this automatically.

![SSE Reconnection with Last-Event-ID](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-sse-reconnection.svg)

**Advantages:** Built into browsers. Automatic reconnection. Works over HTTP. More efficient than long polling (less connection churn). Simple to implement.

**Disadvantages:** One-way only. Some proxies and load balancers do not support streaming and buffer the response, which blocks the stream and is hard to debug. Browsers limit concurrent connections per domain. Long-lived requests complicate monitoring.

**When to use:** Great upgrade from long polling when you need higher update frequency without call-back latency. Popular for AI chat apps that stream tokens as they are generated. Be aware that some infrastructure does not support streaming.

### WebSockets: The Full-Duplex Champion

WebSockets provide true bidirectional communication. If you have high-frequency reads and writes, WebSockets are the default choice. They build on HTTP through an "upgrade" handshake: an existing TCP connection switches from HTTP to WebSocket. You can reuse cookies and headers for authentication.

![WebSocket HTTP Upgrade](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-websocket-upgrade.svg)

**How it works (plain English):** The client opens a WebSocket to ws://api.example.com/socket. The connection upgrades from HTTP. Both sides send and receive messages (opaque blobs - JSON, Protobuf, whatever). The client's onmessage handler parses and updates. On close, the client implements reconnection (e.g., retry after 1 second). On the server, you create a WebSocket server, accept connections, and forward messages from your data source to each client.

**Infrastructure challenges:** WebSockets need persistent connections. L7 load balancers often do not preserve connection stickiness. L4 load balancers do - the same TCP connection hits the same backend. For WebSockets, prefer L4.

![WebSocket + L4 Load Balancer](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-websocket-l4.svg)

**Deployments:** When servers restart, you either sever old connections and have clients reconnect, or have new servers take over. Prefer severing and reconnecting - simpler. You must handle clients that reconnect and may have missed updates.

**Load balancing:** Long-running connections mean you "stick" to each allocation. A load balancer cannot send a new request to a different server without breaking the WebSocket. Many architectures terminate WebSockets into a WebSocket service early. That service handles connection management and scaling; the rest of the system stays stateless. The WebSocket tier changes less often, so fewer deployments churn connections.

**Advantages:** Full-duplex. Lower latency than HTTP (no per-message headers). Efficient for frequent messages. Wide browser support.

![WebSocket Full-Duplex Communication](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-websocket-bidirectional.svg)

**Disadvantages:** More complex. Requires special infrastructure. Stateful connections complicate load balancing and scaling. Must handle reconnection.

**When to use:** High-frequency bidirectional communication. A common pattern is SSE for updates plus HTTP POST for writes - only use WebSockets when you need both directions at high frequency. Defer to SSE unless you have a clear need for bidirectional.

**Interview tip:** Discuss how you manage connections, handle reconnections, and handle server restarts. For scaling, use "least connections" load balancing. Offload heavy processing to other services so WebSocket servers stay lightweight.

### WebRTC: The Peer-to-Peer Solution

WebRTC enables direct peer-to-peer communication between browsers. Ideal for video/audio calls and some data sharing like document editors. Clients talk to a central "signaling server" that tracks peers and their connection info. Once a client has another peer's info, it tries to establish a direct connection. Most clients block inbound connections (NAT). WebRTC addresses this with:

**STUN** - Session Traversal Utilities for NAT. Techniques like "hole punching" let peers establish publicly routable addresses and ports. Peers create open ports and share them via the signaling server.

**TURN** - Traversal Using Relays around NAT. A relay service bounces traffic through a central server to reach the peer when STUN fails.

![WebRTC STUN/TURN NAT Traversal](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-webrtc-stun.svg)

**How it works (plain English):** A client creates an RTCPeerConnection, gets the local media stream, adds tracks to the connection, creates an offer, sets it as the local description, and sends the offer to the signaling server. The signaling server is lightweight; most traffic flows peer-to-peer.

The signaling server itself is a real-time system - it needs WebSockets, SSE, or similar so clients can find peers and exchange connection info.

![WebRTC Signaling Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-webrtc-signaling.svg)

**Advantages:** Direct peer communication. Lower latency. Reduced server costs. Native audio/video support.

**Disadvantages:** Complex setup. Requires signaling server. NAT/firewall issues. Connection setup delay.

**When to use:** Video/audio calls, screen sharing, gaming. Can reduce server load when clients talk frequently to each other - some collaborative document editors use WebRTC for presence and pointer sharing so participants stream cursor position directly to peers instead of routing through the server.

**When NOT to use:** Overkill for most real-time update use cases. Only use when the problem clearly requires peer-to-peer.

### Protocol Choice Flowchart

- Not latency sensitive: **Simple polling**. Start here unless you have a specific need.
- Do not need bidirectional: **SSE**. Lightweight, works for many use cases.
- Need frequent bidirectional: **WebSocket**.
- Audio/video or peer-to-peer collaboration: **WebRTC**.

![Protocol Selection Decision Tree](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-protocol-decision-tree.svg)

---

## Hop 2: Source to Server

Updates must get from wherever they are produced (other users, drivers, services) to the servers that hold client connections. Three patterns:

### Pulling with Simple Polling

A pull-based model. The server (or clients via the server) polls a database for updates. For chat, clients poll for messages with timestamp greater than the last received. The poll itself is the trigger, even though the update occurred earlier.

![Hop 2: Pull Polling Pattern](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-hop2-pull-polling.svg)

**Advantages:** Dead simple. State lives in the database. No special infrastructure. Quick to explain.

**Disadvantages:** High latency. Excess database load when updates are infrequent but polling is frequent.

**When to use:** When responsiveness matters but real-time is not the main concern. If you need true real-time, this is not the best approach. Watch out: a million clients polling every 10 seconds is 100k TPS of read volume.

### Pushing via Consistent Hashing

With long polling, SSE, or WebSockets, clients have persistent connections to specific servers. To send a message to User C, you must know which server they are on. Hashing solves this: hash the user ID and assign them to one server. A central service (e.g., ZooKeeper or Etcd) tracks server count N and addresses. User u goes to server (u mod N). Clients either connect directly to the right server (if they know the mapping) or connect to any server and get redirected. Once connected, that server holds the connection in a map. When an update arrives for User C, you hash their ID, send to the right server, which looks up the connection and forwards the message.

**Consistent hashing** improves scaling. With simple modulo, changing N forces almost all users to reconnect. Consistent hashing maps servers and users onto a hash ring. Each user connects to the next server clockwise. When you add or remove servers, only users in the affected ring segments move. Minimal connection churn.

![Consistent Hashing Ring for Connection Routing](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-consistent-hashing.svg)

**Advantages:** Predictable server assignment. Minimal disruption when scaling. Works well with stateful connections. Easy to add/remove servers (with consistent hashing).

**Disadvantages:** Complex to implement. Requires coordination service (ZooKeeper, etcd). All servers need routing info. Connection state is lost if a server fails.

**When to use:** When you have persistent connections and significant per-connection state (e.g., Google Docs - document loading, operations, sync). Consistent hashing keeps state on one server and minimizes churn during scaling. If you are just passing small messages without much state, Pub/Sub is simpler.

**Interview tip:** Discuss how scaling works. In practice: (1) Signal the start of a scaling event and record both old and new server assignments. (2) Slowly disconnect clients from old servers and have them reconnect to newly assigned servers. (3) During the transition, send messages to both old and new servers until clients have moved. (4) When done, signal the end of the scaling event and update the coordination service (ZooKeeper, etcd) with the new assignments. The mechanics of discovering initial server assignments matter: clients can connect directly if they know the hash and server list, or connect to any server and get redirected. Redirects add a round-trip; a central lookup can become a bottleneck during scaling.

### Pushing via Pub/Sub

A pub/sub service (Kafka, Redis) collects updates and broadcasts to interested subscribers. Endpoint servers hold lightweight connections to clients and subscribe to topics. They forward updates from the pub/sub service to the right clients. Clients can connect to any endpoint server; the server registers them with pub/sub for the relevant topics. When an update is published, the pub/sub service broadcasts to subscribers; endpoint servers forward to clients.

![Pub/Sub Broadcast to Endpoint Servers](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-pubsub-broadcast.svg)

**Advantages:** Easy load management (e.g., "least connections" load balancer). Efficient broadcast to many clients. Minimal state on endpoint servers.

**Disadvantages:** Do not know subscriber connection status or when they disconnect. Pub/sub can become a bottleneck and single point of failure. Extra hop adds latency (usually under 10ms). Many-to-many connections between pub/sub hosts and endpoint servers.

**When to use:** Broadcasting to many clients with little per-client state. Redis cluster can scale pub/sub by sharding subscriptions. Use "least connections" for inbound load balancing.

### Choosing Your Hop 2 Approach

The right Hop 2 strategy depends on your scale and how much state each connection carries. Pull polling works at small scale with few servers. Consistent hashing shines when connections carry heavy state. Pub/Sub is the default for lightweight fan-out at scale.

![Hop 2 Decision Tree: Pull Polling vs Consistent Hashing vs Pub/Sub](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-hop2-decision-tree.svg)

---

## When to Use in Interviews

Real-time updates appear in most system design interviews involving user interaction or live data. Proactively identify where immediate updates matter. Strong candidates say early: "Messages need to be delivered instantly - I will address that with WebSockets" or "Character-level changes need sub-second propagation."

**Common scenarios:**

**Chat Applications** - Messages must appear instantly. WebSockets for bidirectional; pub/sub to distribute. Consider message ordering, typing indicators, presence.

**Live Comments** - High-volume social interaction during events. Millions commenting creates fan-out problems. Hierarchical aggregation and batching prevent overload.

**Collaborative Document Editing** - Character-level changes, instant propagation. WebSockets plus operational transforms or CRDTs for conflict resolution. Cursors and selection add real-time complexity.

**Live Dashboards and Analytics** - Constantly changing metrics. SSE works well for one-way flow. Consider aggregation intervals and what "real-time enough" means.

**Gaming and Interactive Apps** - Lowest latency. WebRTC for peer-to-peer; WebSockets for server coordination.

**When NOT to use:** If simple polling suffices, use it. Do not over-engineer. Avoid real-time patterns when the problem does not require them.

![Interview Scenarios for Real-Time Updates](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-interview-scenarios.svg)

---

## Common Deep Dives

### "How do you handle connection failures and reconnection?"

Networks are unreliable. Mobile users lose connections. WiFi drops. Servers restart. You need quick disconnect detection and recovery without data loss. WebSocket connections do not always signal breaks - a client may think it is connected while the server has cleaned up.

![Reconnection and Recovery Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-reconnection-recovery.svg)

Heartbeat mechanisms detect "zombie" connections. The client or server sends periodic PING frames; the other side responds with PONG. If no PONG arrives within the timeout window, the connection is declared dead and resources are cleaned up. Without heartbeats, zombie connections leak memory, file descriptors, and pub/sub subscriptions indefinitely.

![Heartbeat / Keep-Alive Mechanism](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-heartbeat-mechanism.svg)

For recovery, track what each client has received. On reconnect, send everything they missed. Maintain a per-user message queue or use sequence numbers. Redis streams are a popular option for this.

### "What happens when a single user has millions of followers who all need the same update?"

The celebrity problem. Naive fan-out crashes the system. Use caching and hierarchical distribution. Cache the update once. Regional servers pull and push to local clients. Reduces load on any single component. See hierarchical aggregation patterns in scaling writes.

![Celebrity Fan-Out Problem](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-celebrity-fanout.svg)

### "How do you maintain message ordering across distributed servers?"

Messages sent milliseconds apart can arrive out of order if they take different paths or hit different servers. Vector clocks or logical timestamps help. Each server maintains a clock; messages carry timestamp info so recipients can order them.

For strict ordering, funnel related messages through a single server or partition. Trades scalability for consistency. For most product-style questions, a single server or partition is enough. If all messages go to one host, stamping with timestamps gives you a total order.

![Message Ordering Across Distributed Servers](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-message-ordering.svg)

---

## Summary

- **Two hops:** Client-server (polling, long polling, SSE, WebSockets, WebRTC) and source-server (pull polling, consistent hashing, Pub/Sub).
- **Start simple:** Polling often suffices. Many problems do not need sub-second latency.
- **Protocol choice:** Polling for 2-5 second updates; long polling or SSE for near real-time; WebSockets for bidirectional high-frequency; WebRTC for video/audio or peer-to-peer.
- **L4 vs L7:** WebSockets need L4 load balancers for persistent connections. L7 works for HTTP-based approaches.
- **Hop 2:** Pub/Sub for lightweight broadcast; consistent hashing when connection state is heavy.
- **Deep dives:** Reconnection and missed updates; celebrity fan-out; message ordering.

![Real-Time Updates Scaling Summary](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/rt-scaling-summary.svg)

{{SUBSCRIBE}}
{{BUTTON:Read More Articles|https://newsletter.systemdesignlaws.xyz}}

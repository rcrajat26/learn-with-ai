# 10 — Networking

Scope: what a backend engineer must be able to explain at a whiteboard and debug on a box.
Every concept below is written as **mechanism first** — what actually happens, in order — because
interviewers probe the mechanism, not the vocabulary.

---

## 1. TCP vs UDP

**Mechanism.** TCP is a *connection-oriented, byte-stream* protocol. Before any data flows, both
sides exchange packets to agree on starting sequence numbers. Every byte sent is numbered; the
receiver acknowledges byte ranges; unacknowledged data is retransmitted after a timeout (RTO) or
after duplicate ACKs trigger fast retransmit. The receiver buffers out-of-order segments and only
hands *in-order* bytes to the application. Sender rate is governed by two windows: the **receive
window** (flow control — "don't overrun my buffer") and the **congestion window** (congestion
control — "don't overrun the network"), which grows on success and collapses on loss.

UDP is a *datagram* protocol. It adds essentially four things to raw IP: source port, destination
port, length, checksum. No handshake, no ordering, no retransmission, no congestion control. A
datagram either arrives whole or does not arrive at all.

| Property | TCP | UDP |
|---|---|---|
| Connection setup | 3-way handshake (1 RTT before data) | none |
| Delivery | reliable, retransmits | best-effort |
| Ordering | in-order byte stream | none; app must reorder |
| Boundaries | none — stream; app must frame | preserved — 1 send = 1 datagram |
| Flow/congestion control | yes | no (app must implement) |
| Head-of-line blocking | yes, within a connection | no |
| Typical use | HTTP/1.1 & /2, DB protocols, gRPC | DNS, QUIC/HTTP3, video, metrics (statsd), gossip |

**The framing point people miss.** TCP has no message boundaries. If you `write()` 100 bytes then
`write()` 100 bytes, the peer may `read()` 200 bytes at once, or 37 then 163. Every TCP protocol
must define framing: length prefix (most binary protocols), delimiter (`\r\n\r\n` in HTTP headers),
or close-of-connection. Hand-rolled socket code that assumes "one read = one message" works in
testing on localhost and fails under load or across a WAN.

> **Trap:** "UDP is faster than TCP" is only half true. UDP avoids handshake latency and
> head-of-line blocking. But raw throughput on a lossy link is often *worse* with naive UDP because
> you have no congestion control and you either flood or under-utilise. QUIC is fast not because
> it's UDP but because it reimplemented reliability *per-stream* on top of UDP.

**When you'd actually pick UDP in backend work:** metrics emission (statsd — losing 1 of 10,000
counters is fine, blocking the request thread is not), service discovery gossip, DNS, and anything
where a late packet is worthless (live audio). Otherwise TCP.

---

## 2. The TCP 3-way handshake (and the 4-way close)

**Open.**

1. Client → Server: **SYN**, with client's initial sequence number (ISN_c). Client enters `SYN_SENT`.
2. Server → Client: **SYN-ACK**, with ISN_s and ack = ISN_c + 1. Server enters `SYN_RCVD`.
3. Client → Server: **ACK**, ack = ISN_s + 1. Both sides `ESTABLISHED`.

Cost: **one full round trip before the first application byte**. On a 100 ms RTT link that's 100 ms
of pure setup. Add TLS (see §4) and you're at 200–300 ms before the first request byte. This is the
entire reason connection pooling and keep-alive exist.

The server maintains a **SYN backlog** (half-open connections in `SYN_RCVD`) and an **accept queue**
(fully established, waiting for the app to call `accept()`). If your application is slow to accept —
blocked threads, GC pause — the accept queue fills and the kernel drops or refuses new SYNs. Symptom:
clients see connection timeouts while the server CPU looks fine. Check with `ss -lnt` (the `Recv-Q`
column on a listening socket is the current accept-queue depth, `Send-Q` is its maximum) and
`netstat -s | grep -i listen` for overflow counters.

**Close** is four packets because each direction closes independently: FIN → ACK, FIN → ACK. The side
that sends the first FIN (the **active closer**) ends up in `TIME_WAIT`. See §8 — this matters
enormously.

> **Trap:** A "connection refused" and a "connection timeout" are different failures. Refused =
> the SYN reached a host and nothing was listening on that port (RST came back) — usually wrong
> port, process down. Timeout = no response at all — usually a firewall/security-group dropping
> packets, wrong IP, or a saturated accept queue. Never treat them as the same symptom.

---

## 3. "What happens when you type a URL and press enter" — the full walkthrough

This is the single most-asked systems question because it touches everything. Answer it as a
pipeline, and at each stage name the cache and the failure mode.

### 3.1 URL parsing
Browser splits scheme (`https`), host (`api.example.com`), port (default 443), path, query, fragment.
Fragment (`#...`) is never sent to the server.

### 3.2 DNS resolution — the chain, with caches at every level
Goal: turn `api.example.com` into an IP address. Checked in order, each level is a cache:

1. **Browser DNS cache** (~60 s, browser-controlled).
2. **OS resolver cache** (`nscd`/`systemd-resolved` on Linux, `dscacheutil` on macOS), plus `/etc/hosts`
   which short-circuits everything.
3. **JVM DNS cache** — *the one backend engineers get bitten by*. The JVM caches resolutions in
   `InetAddress`. Controlled by `networkaddress.cache.ttl` (successful lookups) and
   `networkaddress.cache.negative.ttl` (failures) in `java.security`, overridable with the system
   property `-Dsun.net.inetaddr.ttl=<seconds>`. Historically, with a `SecurityManager` installed the
   default was **cache forever**; modern JDKs default to 30 s positive / 10 s negative. Negative
   caching defaults have also historically been long enough to hurt.
4. **Recursive resolver** (your ISP's, or 8.8.8.8, or the VPC resolver at `169.254.169.253` in AWS)
   — has its own cache honouring the record's TTL.
5. **Root servers** → tell the resolver where `.com` lives.
6. **TLD servers** (`.com`) → tell the resolver the authoritative nameservers for `example.com`.
7. **Authoritative nameserver** → returns the A/AAAA record.

> **Trap (JVM DNS cache):** You fail over an RDS endpoint or an ALB scales and changes IPs. DNS TTL
> is 60 s, so everything *should* recover in a minute. Your Java service keeps hammering the dead IP
> for hours. Cause: JVM-level caching above the OS. Fix: set `-Dsun.net.inetaddr.ttl=30` (or 60),
> and ensure negative TTL is short. This is a genuine production outage pattern, not trivia.

### 3.3 TCP connect
3-way handshake to the resolved IP on port 443. (Or reuse an existing pooled/keep-alive connection —
in which case skip 3.3 and 3.4 entirely. That's the whole point of pooling.)

### 3.4 TLS handshake
See §4. TLS 1.3 = 1 RTT; TLS 1.2 = 2 RTT.

### 3.5 HTTP request
Request line, headers (`Host` — required, this is how one IP serves many sites; `Cookie`;
`Accept-Encoding`; `Authorization`), optional body.

### 3.6 Server side
Load balancer terminates TLS → picks a backend → your app's accept queue → a thread or event-loop
handler → routing → controller → DB/cache/downstream calls → response serialisation.

### 3.7 Response and rendering
Status line, headers (`Cache-Control`, `ETag`, `Content-Encoding`), body. Browser parses HTML,
discovers subresources, repeats the whole pipeline for each (with connection reuse), builds the DOM,
CSSOM, render tree, paints.

**The caches to name, in order:** browser cache → browser DNS → OS DNS → JVM DNS → resolver DNS →
CDN edge → reverse-proxy/nginx cache → application cache (Caffeine/Redis) → DB buffer pool → OS page
cache → disk. Naming this stack unprompted is a strong signal.

---

## 4. TLS

**Three goals, in this order:**

1. **Confidentiality** — nobody on the path can read the bytes.
2. **Integrity** — nobody can modify them undetected (AEAD ciphers give both at once).
3. **Authentication** — you are talking to the server you think you are. *This is the one that
   requires certificates.* Encryption without authentication is useless: you'd have a perfectly
   private conversation with an attacker.

**Mechanism — asymmetric to bootstrap, symmetric to transfer.** Asymmetric crypto (RSA/ECDSA) is
orders of magnitude slower than symmetric (AES). So TLS uses asymmetric operations only during the
handshake to (a) authenticate the server via its certificate signature and (b) agree on a shared
secret — modern TLS uses ephemeral Diffie-Hellman (ECDHE), where both sides contribute key material
and the shared secret is never transmitted. That secret derives symmetric session keys, and all bulk
data is AES-GCM or ChaCha20-Poly1305.

**Ephemeral DH gives forward secrecy:** even if the server's private key leaks tomorrow, yesterday's
captured traffic stays unreadable, because the session secret was never derivable from the long-term
key alone.

**Certificate chain.** The server sends its leaf cert plus intermediates. The client verifies:
signature chain up to a root in its **trust store**, hostname matches CN/SAN, validity dates, and
revocation (CRL/OCSP, often stapled). The root is trusted *a priori* — it's shipped with your OS/JDK.

- In Java the trust store is `$JAVA_HOME/lib/security/cacerts`. Internal/corporate CAs must be
  imported there (or via `-Djavax.net.ssl.trustStore`), which is why `PKIX path building failed:
  unable to find valid certification path to requested target` is the single most common Java TLS
  error. It means: I don't trust the signer, not "the cert is broken."
- **Missing intermediate** is the classic server-side misconfiguration: browsers often paper over it
  via cached intermediates or AIA fetching, so it works in Chrome and fails in curl/Java. Test with
  `openssl s_client -connect host:443 -showcerts`.

**SNI (Server Name Indication).** Chicken-and-egg: the server needs to know which hostname you want
in order to send the right certificate, but `Host:` is inside the encrypted HTTP request. SNI puts
the hostname in the *plaintext* ClientHello so the server (or a shared load balancer / CDN edge) can
select the right cert. Consequence: hostname is visible to network observers even over HTTPS
(Encrypted Client Hello aims to fix that).

**Handshake round trips.** TLS 1.2: 2 RTT. TLS 1.3: 1 RTT (and 0-RTT resumption, which is *not
replay-safe* — never use 0-RTT for non-idempotent requests). **Session resumption** (session tickets)
skips the full handshake on reconnect.

**mTLS** adds client certificates — the client also proves identity. Common for service-to-service
inside a mesh.

> **Trap:** "We use HTTPS internally so we're secure." TLS protects data *in transit between two
> endpoints*. If the load balancer terminates TLS and talks plaintext HTTP to your pods, the segment
> from LB to pod is unencrypted. Know where termination happens (§11) and whether re-encryption is on.

---

## 5. DNS records and operational gotchas

| Record | Maps | Notes |
|---|---|---|
| **A** | name → IPv4 | The workhorse. |
| **AAAA** | name → IPv6 | Dual-stack clients try both (Happy Eyeballs). |
| **CNAME** | name → another name | Cannot coexist with other records at the same name; **cannot exist at the zone apex** (`example.com`). |
| **ALIAS / ANAME** (Route 53 "Alias") | apex → AWS resource | Provider-specific fix for the apex-CNAME restriction; resolves to A records at query time, and is free in Route 53. |
| **MX** | mail | Priority-ordered. |
| **TXT** | arbitrary text | SPF/DKIM/DMARC, domain-ownership proofs. |
| **NS** | delegation | Which nameservers are authoritative. |
| **SRV** | service+port | Used by some discovery systems. |
| **PTR** | IP → name | Reverse DNS. |

**TTL is a promise and a lock-in.** A 3600 s TTL means resolvers may cache the answer for an hour. If
you need to move traffic in a hurry, you cannot — the old answer is out there. Standard practice:
**lower the TTL to 60 s well before a planned migration** (at least old-TTL ahead of time), do the
cutover, then raise it again.

**DNS failover gotchas.**
- DNS is a poor failover mechanism. Health-checked DNS failover (Route 53) still has to wait for
  health-check detection + TTL expiry + client caches (which frequently ignore TTL — see JVM above).
  Real failover uses a load balancer or anycast, with DNS only for coarse region-level routing.
- Some clients resolve once at startup and never again. Long-lived connection pools especially.
- Negative caching: an NXDOMAIN is cached too, per the zone's SOA minimum. Creating a record does not
  make it instantly visible to a resolver that just got NXDOMAIN.
- Round-robin DNS is not load balancing: no health awareness, and clients may pin to the first answer.

---

## 6. HTTP evolution — and why each version exists

### HTTP/1.0
One request per TCP connection. Connection closed after the response. Catastrophic: a handshake per
image.

### HTTP/1.1
- **Keep-alive (persistent connections)** is the headline change: reuse one TCP connection for many
  sequential requests. Amortises handshake + lets the congestion window stay warm.
- **Pipelining** (send request 2 before response 1 arrives) was specified but is effectively dead —
  responses must come back *in order*, so one slow response blocks the rest: **head-of-line blocking
  at the HTTP layer**.
- Practical consequence: browsers open ~6 parallel connections per origin to get concurrency, and
  sites did "domain sharding" to get more. All of it is a workaround for HOL blocking.
- Text protocol, headers repeated verbatim on every request (cookies alone can be kilobytes).

### HTTP/2
- **Binary framing** with **multiplexed streams**: many concurrent requests/responses interleaved on
  *one* TCP connection, responses in any order. Kills HTTP-layer HOL blocking.
- **HPACK header compression** — huge win for repeated headers.
- **Server push** — largely deprecated in practice.
- **Remaining problem: TCP-level head-of-line blocking.** All streams share one TCP connection, and
  TCP guarantees in-order byte delivery. Lose one packet and *every* multiplexed stream stalls until
  it's retransmitted. On a lossy mobile link, HTTP/2 can be *worse* than HTTP/1.1's six connections.
- Backend relevance: gRPC is HTTP/2. A single HTTP/2 connection to a service means an L4 load
  balancer will pin all your traffic to one backend — you need an L7 balancer that load-balances
  *per request*, or client-side load balancing. This surprises people migrating REST→gRPC.

### HTTP/3 (QUIC)
- Runs over **UDP**, reimplementing reliability, congestion control, and ordering **per stream** in
  user space. Packet loss on stream A no longer blocks stream B: TCP-level HOL blocking is gone.
- TLS 1.3 is baked in — **connection establishment is 1 RTT, or 0 RTT on resumption** (handshake and
  transport setup are combined).
- **Connection migration**: the connection is identified by a connection ID, not the 4-tuple, so
  switching Wi-Fi → cellular doesn't drop it.
- Being user-space, it evolves without kernel/middlebox upgrades. Downside: more CPU per byte, and
  some networks block or throttle UDP.

---

## 7. Timeouts — the taxonomy, and Java's dangerous defaults

An HTTP client call has **at least four** distinct timeouts. Being able to enumerate them separates
people who have run services from people who have read about them.

| Timeout | Clock starts | Clock stops | Typical value |
|---|---|---|---|
| **Connection-pool acquisition** | you ask the pool for a connection | you get one | 100–500 ms |
| **Connect (TCP)** | SYN sent | handshake complete | 1–3 s |
| **TLS handshake** | ClientHello | handshake done | 2–5 s (often folded into connect) |
| **Socket read / response** | request written | *each* chunk of response bytes arrives | tuned to the p99.9 of the callee |
| **Total request** (where supported) | call begins | full response | the one that actually bounds latency |

Notes on the read timeout: it is usually an **inactivity** timeout, not a total-duration timeout. A
server dribbling one byte every second keeps a 10 s read timeout alive forever. That's why a total
timeout matters for anything user-facing.

**Java's defaults are infinite.** `java.net.HttpURLConnection`, plain `Socket`, older Apache
HttpClient configurations, and JDBC drivers without an explicit socket timeout will **wait forever**.
A hung downstream then pins one of your request threads permanently. With a 200-thread Tomcat pool
and a hung dependency, you are fully unavailable in the time it takes to accumulate 200 requests —
even though your own process is healthy. This is *the* classic cascading-failure story.

```java
// Java 21 — explicit at every layer
HttpClient client = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(2))          // TCP connect
        .version(HttpClient.Version.HTTP_2)
        .build();

HttpRequest req = HttpRequest.newBuilder(URI.create("https://api.example.com/v1/quote"))
        .timeout(Duration.ofSeconds(5))                 // total request timeout
        .GET()
        .build();
```

**Rules of thumb.**
- Timeout budgets must **shrink as you go deeper**. If the edge allows 3 s, a service two hops in
  cannot have a 5 s timeout — it will still be working on a request nobody is waiting for.
- A timeout that is longer than the caller's timeout is dead code that only burns resources.
- Retries multiply load: a 3-attempt retry at every one of 3 layers is 27× amplification. Retry at
  **one** layer, with jitter, on idempotent operations only, ideally behind a circuit breaker.
- Set the DB pool acquisition timeout *shorter* than the HTTP read timeout so you fail fast with a
  clear "no connection available" instead of an opaque hang.

> **Trap:** Setting a timeout on the HTTP client but not on the **connection pool acquisition**. When
> the pool is exhausted, threads queue at the pool with no bound and your carefully configured 2 s
> read timeout never even starts counting.

---

## 8. TIME_WAIT and ephemeral port exhaustion

**Mechanism.** When a TCP connection closes, the side that sent the first FIN (the **active closer**)
holds the socket in `TIME_WAIT` for **2×MSL** (Linux: a fixed 60 s, `TCP_TIMEWAIT_LEN`, compile-time —
`net.ipv4.tcp_fin_timeout` controls `FIN_WAIT_2`, *not* this). Two reasons:

1. Absorb delayed duplicate segments so they can't be mistaken for data on a new connection reusing
   the same 4-tuple.
2. Ensure the final ACK can be retransmitted if the peer's FIN is repeated.

**Why it bites the client side.** An outbound connection consumes a local **ephemeral port**. The
range is `net.ipv4.ip_local_port_range`, typically 32768–60999 ≈ 28,000 ports. A connection is
identified by the 4-tuple (src IP, src port, dst IP, dst port), so the limit is 28k *per destination
IP:port pair* — but that is easily hit.

Do the arithmetic: 28,000 ports ÷ 60 s of `TIME_WAIT` ≈ **~470 new connections per second sustained**
before you run out. A service making one fresh HTTP connection per request to a single downstream
hits this at ~470 rps. Symptom: `connect()` fails with `EADDRNOTAVAIL` / "Cannot assign requested
address", intermittently, under load, on the *client*, while the server looks fine.

**Diagnose:**
```bash
ss -s                                  # summary incl. timewait count
ss -tan state time-wait | wc -l        # how many
cat /proc/sys/net/ipv4/ip_local_port_range
```

**Fix, in order of correctness:**

1. **Connection pooling / HTTP keep-alive.** The real fix. Reuse connections and you create almost
   none. This is why every HTTP client and JDBC driver has a pool, and why creating a new
   `RestTemplate`/`HttpClient`/`OkHttpClient` per request is a serious bug rather than a style issue.
2. **Make the server the active closer** where possible, so `TIME_WAIT` accumulates on the server —
   which is fine, because the server has one port and the sockets are distinguished by the client's
   4-tuple.
3. `net.ipv4.tcp_tw_reuse=1` — lets the kernel reuse a `TIME_WAIT` socket for a new *outbound*
   connection when timestamps prove safety. Reasonable, targeted.
4. Widen `ip_local_port_range`. Buys a ~2× headroom; a band-aid.
5. **Never `tcp_tw_recycle`.** Removed in Linux 4.12 for good reason — it broke catastrophically
   behind NAT, where many clients share a source IP with unrelated timestamp clocks.

> **Trap:** Confusing `TIME_WAIT` with `CLOSE_WAIT`. `CLOSE_WAIT` on *your* side means the peer sent
> FIN and **your application never called `close()`** — it is an application-level socket/fd leak, and
> it does not time out. Rising `CLOSE_WAIT` = your bug. Rising `TIME_WAIT` = normal churn, possibly
> too much of it.

---

## 9. Keep-alive, idle timeouts, and middleboxes

Keep-alive is an agreement to leave a TCP connection open between requests. Every hop has its own
idea of how long that's allowed:

- Client pool idle timeout (e.g. 60 s)
- Server keep-alive timeout (nginx `keepalive_timeout` 75 s; Tomcat `keepAliveTimeout`)
- Load balancer idle timeout (**AWS ALB defaults to 60 s**)
- NAT gateway / firewall connection-tracking timeout (often 350 s, sometimes much less)

**The mismatch failure.** Suppose the client pool holds connections idle for 90 s but the ALB closes
idle connections at 60 s. At t=70 s the client picks a pooled connection it believes is alive and
writes a request onto a socket the LB has already sent FIN/RST for. Result: sporadic, unreproducible
`Connection reset by peer` / `NoHttpResponseException` at low single-digit percentages, correlated
with *low* traffic (idle connections only accumulate when you're not busy). Retrying makes it vanish,
which is why it gets ignored for months.

**Rule:** the client's idle timeout must be **strictly shorter** than every downstream idle timeout.
Set client idle to ~30 s against a 60 s ALB. Additionally: enable TCP keep-alive probes (kernel
`net.ipv4.tcp_keepalive_time` defaults to a useless **7200 s**; set per-socket to ~30–60 s) so a
silently dropped connection is detected rather than discovered at write time.

Worse variant: a stateful firewall silently *drops* the flow rather than sending RST. Then your write
succeeds into a black hole and you wait for the read timeout on every affected request. TCP
keep-alive probes are the defence.

---

## 10. Sockets and file descriptors

A socket is a file descriptor. Everything the OS gives you — files, pipes, sockets, epoll instances —
is an fd, an integer index into the process's fd table. Limits:

- Per-process soft/hard limit: `ulimit -n` (containers often default to 1024, which is very low).
- System-wide: `fs.file-max`.

A listening server needs roughly: one fd per accepted connection + one per outbound connection + one
per open file + JAR/class files + one per epoll instance. At 10k concurrent connections a 1024 limit
is instantly fatal: `java.net.SocketException: Too many open files`. See topic 11 for `lsof` triage.

A **socket is identified by the 4-tuple**, not by the port. A server on port 443 handles a million
connections on that one port; the ports that are scarce are the *client's* ephemeral ones (§8).

---

## 11. Load balancing: L4 vs L7

| | **L4 (transport)** | **L7 (application)** |
|---|---|---|
| Sees | IP + port, TCP/UDP | full HTTP: method, path, headers, cookies |
| Decision unit | **connection** | **request** |
| Routing | round-robin/hash on 4-tuple | path/host/header-based, canary by header |
| TLS | passes through (or TCP-terminates) | usually terminates |
| Overhead | very low, near line rate | higher — parses and buffers |
| AWS | NLB | ALB |
| Retries/health | TCP health checks | HTTP health checks, retries, circuit breaking |

**The consequence that matters:** an L4 balancer pins a *connection* to a backend. With HTTP/1.1
keep-alive or HTTP/2 multiplexing, one long-lived connection carries thousands of requests, so an L4
balancer effectively load-balances *once*. Add a new backend pod and it receives nothing until
clients reconnect. With HTTP/2 or gRPC this is severe: use an L7 balancer, or client-side load
balancing, or force periodic connection recycling (`max_connection_age`).

**TLS termination** — three arrangements:
- **Terminate at the LB, plaintext behind.** Simplest, cheapest, central cert management. Requires a
  trusted network segment (in AWS, a VPC you control).
- **Terminate and re-encrypt.** LB sees the request (needed for L7 routing/WAF) and re-encrypts to
  the backend. Compliance-friendly.
- **Passthrough.** LB is L4 only; the backend holds the cert. Needed for mTLS to the app or end-to-end
  encryption requirements — but you lose L7 routing entirely.

**Health checks:** shallow (`/healthz` returns 200 if the process is up) vs deep (checks DB, cache,
downstreams). See topic 20 — deep checks on a *liveness* probe cause correlated mass restarts when a
shared dependency wobbles.

**Balancing algorithms:** round-robin (default, fine for uniform requests), least-connections (better
with variable request cost), consistent hashing / IP hash (session or cache affinity — but see topic
15's note on why affinity is a crutch), and power-of-two-choices (near-optimal, cheap).

`X-Forwarded-For` / `X-Forwarded-Proto`: once you terminate TLS at an LB, the app sees the LB's IP
and thinks the scheme is HTTP. Configure the framework to trust these headers (Spring:
`server.forward-headers-strategy=framework|native`) or you'll generate `http://` redirect URLs from
an HTTPS site and log the LB's IP for every client.

---

## 12. NAT, in the amount a backend engineer needs

NAT rewrites source IP (and usually source port) as packets leave a private network, keeping a
translation table so replies find their way back. Consequences worth knowing:

- Many hosts share one public IP → the server sees one IP for thousands of clients. IP-based rate
  limiting punishes whole offices; IP allow-listing is coarse.
- The NAT box holds **per-flow state with an idle timeout**. Idle connections are silently reaped —
  hence §9.
- Inbound connections to a NATed host are impossible without port forwarding. This is why webhooks
  need a public endpoint and why local dev uses tunnels.
- In AWS, a **NAT Gateway** gives private-subnet resources outbound internet. It is charged per hour
  *and per GB processed*, and it also has a **~55,000 simultaneous connections per destination**
  limit — the same ephemeral-port arithmetic as §8, now shared across every instance behind it. Heavy
  S3 traffic through a NAT Gateway is both a cost and a scaling bug; use a VPC Gateway Endpoint (see
  topic 18).

---

## 13. CDN mental model

A CDN is a globally distributed reverse-proxy cache sitting between users and your origin.

**Mechanism.** DNS resolves your hostname to a nearby edge PoP (anycast or geo-DNS). The edge checks
its cache. **Hit** → served in ~10 ms with no origin traffic. **Miss** → the edge fetches from origin
(often over a warm, optimised backbone connection with tiered caching so many edges collapse to one
origin fetch) and caches per `Cache-Control`.

What you get: latency (physics — 100 ms RTT to another continent is not optimisable), origin offload,
TLS termination near the user (handshake RTTs shrink), DDoS absorption, and static-asset compression.

Cache key = host + path + whatever you tell it to vary on (query params, `Vary` headers). **Getting
the cache key wrong is the main CDN bug**: vary on `Cookie` and your hit rate goes to zero; ignore a
meaningful query param and users get each other's content.

Invalidation: purge/invalidate by path (slow, rate-limited) vs **versioned URLs** (`app.a1b2c3.js`
with a 1-year TTL). Versioned URLs are strictly better — always prefer changing the key over purging.

Dynamic content isn't cacheable, but a CDN still helps: TLS terminates at the edge, and the
edge-to-origin leg reuses warm connections.

---

## 14. Real-time delivery: polling, long polling, SSE, WebSocket, webhooks

| Approach | Direction | Transport | Use when |
|---|---|---|---|
| **Short polling** | client pulls on a timer | plain HTTP | simplest; updates can lag by the interval; wasteful at scale |
| **Long polling** | client pulls, server holds open until data or timeout | plain HTTP | near-real-time with zero new infrastructure; ties up a connection per client |
| **SSE** (`text/event-stream`) | server → client only | HTTP, one long response | notifications, live feeds, log tailing; auto-reconnect + `Last-Event-ID` built in; works through most proxies |
| **WebSocket** | full duplex | HTTP `Upgrade` → raw framed TCP | chat, trading, collaborative editing; anything client→server at high frequency |
| **Webhook** | server → *your server* | fresh HTTP POST | third-party integrations (payments, VCS); requires a public endpoint |

**WebSocket mechanism.** Client sends a normal HTTP GET with `Connection: Upgrade`, `Upgrade:
websocket`, and `Sec-WebSocket-Key`. Server replies `101 Switching Protocols`. After that the TCP
connection is no longer HTTP — it carries WebSocket frames in both directions. It starts as HTTP
precisely so it traverses port 443 and existing proxies.

Operational costs of WebSockets: **connections are stateful**, so any instance can be the one holding
a given user's socket. You need sticky routing or a pub/sub backplane (Redis, Kafka) so a message
produced on instance A reaches the socket on instance B. Deploys drop every connection at once —
clients need reconnect with backoff and jitter, or your rolling restart becomes a self-inflicted
thundering herd. Load-balancer idle timeouts kill idle sockets (§9), so you need app-level heartbeat
pings.

**Webhook design (from the receiving side):** must be idempotent (senders retry, and duplicates are
guaranteed), must verify signatures (HMAC over the raw body — verify *before* parsing), must respond
fast (ack in <1 s and process asynchronously via a queue — see topic 14), and must tolerate
out-of-order delivery.

**Default choice:** if it's server→client only, use SSE. Reach for WebSocket only when you genuinely
need bidirectional or low-latency client→server. SSE is dramatically simpler to operate.

---

## 15. epoll, readiness multiplexing, and the C10K problem

**The problem.** Thread-per-connection: each connection gets an OS thread that blocks in `read()`.
Each thread costs ~1 MB of stack (JVM default) plus kernel bookkeeping, and the scheduler must
context-switch between them (~1–5 µs each, plus cache pollution — see topic 11). At 10,000
connections that's ~10 GB of stack and a scheduler thrashing. Yet at any instant most of those
connections are idle. This is **C10K**.

**The old fix: `select`/`poll`.** One thread asks the kernel "which of these fds are ready?" But you
pass the whole fd set on every call and the kernel scans all of them: **O(n) per call**, plus
`select` caps at `FD_SETSIZE` (1024). At 10k fds you rescan 10k entries thousands of times a second.

**`epoll` (Linux; `kqueue` on BSD/macOS; IOCP on Windows).** Mechanism:
- `epoll_create` makes a kernel-side interest set — **persistent**, so you register each fd once
  (`epoll_ctl`) instead of re-passing them.
- The kernel attaches a callback to each registered fd. When an fd becomes ready, it is moved onto a
  **ready list**.
- `epoll_wait` returns just the ready fds: **O(number of ready events)**, not O(total fds).

That turns 10,000 mostly-idle connections into "wake up, handle the 12 that have data, sleep."

**Why Netty / one-thread-many-connections.** Netty (and nginx, Node, Vert.x, Undertow) runs a small
pool of **event-loop threads** — typically 2× cores. Each owns an epoll selector and thousands of
channels. A ready event triggers a handler, which must **never block**: any blocking call on an event
loop stalls every connection that loop owns. Hence the whole reactive/callback/`CompletableFuture`
style, and the rule that blocking work must be offloaded to a separate executor. Memory is now ~a few
KB per connection instead of ~1 MB.

The cost is programming model. Non-blocking code is harder to write, harder to read, and *much*
harder to debug — stack traces are meaningless, `ThreadLocal` (and thus MDC-based correlation IDs, see
topic 20) breaks, and profilers lose causality.

**What virtual threads (Java 21, Project Loom) change.** A virtual thread is scheduled by the JVM
onto a small pool of carrier (platform) threads. When a virtual thread performs a blocking operation
that Loom has instrumented — socket I/O, `Thread.sleep`, most `java.util.concurrent` locks — the JVM
**unmounts** it from its carrier thread, stores its continuation on the heap, and runs something else.
Under the hood the JVM does exactly the epoll multiplexing described above.

The result: you write straightforward blocking code with real stack traces and working `ThreadLocal`,
and get event-loop-class scalability. Stacks are heap-allocated and grow on demand (hundreds of bytes
to a few KB), so a million virtual threads is realistic.

What it does *not* fix:
- **Pinning.** A virtual thread that blocks inside a `synchronized` block or a native/JNI frame cannot
  unmount and holds its carrier hostage. JDK 21 made this a real hazard (`jdk.tracePinnedThreads`
  helps); JDK 24 removed the `synchronized` case, but pinning on native frames remains. Prefer
  `ReentrantLock` in hot paths on 21.
- **CPU-bound work.** Loom addresses I/O concurrency, not parallelism. Ten thousand virtual threads
  doing math is still bounded by your cores.
- **Downstream capacity.** Unbounded virtual threads mean unbounded concurrent DB calls. The
  bottleneck moves to your connection pool, and you must add explicit limits (semaphores,
  `StructuredTaskScope`, bulkheads). "No thread limit" removes an accidental backpressure mechanism —
  see topic 14 on backpressure.

**Positioning:** for new Java services, virtual threads make the blocking style the sensible default,
and reduce the reason to reach for Netty/WebFlux to cases needing genuine streaming semantics or
extreme per-connection efficiency.

---

## Atomic concept checklist

- [ ] TCP is a byte stream with no message boundaries; every protocol on top must define framing.
- [ ] 3-way handshake = SYN, SYN-ACK, ACK; costs one RTT before any data.
- [ ] `SYN` backlog vs accept queue; a slow `accept()` loop causes client-side connect timeouts.
- [ ] Connection *refused* (RST, nothing listening) ≠ connection *timeout* (packets dropped).
- [ ] URL→page: parse, DNS chain, TCP, TLS, HTTP request, server processing, response, render.
- [ ] DNS cache layers: browser, OS/`/etc/hosts`, **JVM (`sun.net.inetaddr.ttl`)**, recursive resolver.
- [ ] JVM DNS caching can pin you to a dead IP after failover — set an explicit TTL.
- [ ] TLS's three goals: confidentiality, integrity, authentication — only the third needs certs.
- [ ] Asymmetric crypto only in the handshake; symmetric (AES-GCM) for bulk data.
- [ ] ECDHE gives forward secrecy: past traffic stays safe if the long-term key leaks.
- [ ] Cert chain validated to a root in the trust store; Java's is `cacerts` → `PKIX path building failed` means untrusted signer.
- [ ] Missing intermediate certs break curl/Java while browsers appear fine.
- [ ] SNI sends the hostname in plaintext so shared LBs can pick a cert.
- [ ] TLS 1.3 = 1 RTT handshake; 0-RTT resumption is replay-unsafe.
- [ ] CNAME cannot exist at the zone apex; Route 53 Alias is the workaround.
- [ ] Lower DNS TTLs *before* a migration; you cannot retroactively shorten a cached answer.
- [ ] DNS failover is slow and unreliable because clients ignore TTLs; use an LB.
- [ ] HTTP/1.1 keep-alive; pipelining is dead due to in-order response HOL blocking.
- [ ] HTTP/2 multiplexes streams over one connection but still suffers **TCP-level** HOL blocking.
- [ ] HTTP/2 + L4 load balancer = traffic pinned to one backend; needs L7 or client-side LB.
- [ ] HTTP/3 = QUIC over UDP: per-stream reliability, integrated TLS 1.3, connection migration.
- [ ] Four timeouts: pool acquisition, connect, TLS, read (inactivity) — plus a total request timeout.
- [ ] Java defaults are **infinite**; a hung downstream exhausts the thread pool and takes you down.
- [ ] Timeout budgets shrink with depth; retries at every layer multiply load.
- [ ] `TIME_WAIT` = 60 s on the **active closer**; ~28k ephemeral ports ÷ 60 s ≈ ~470 conn/s ceiling.
- [ ] Symptom of exhaustion: `EADDRNOTAVAIL` / "Cannot assign requested address" on the client.
- [ ] Fix is **connection pooling**, then `tcp_tw_reuse`; never `tcp_tw_recycle`.
- [ ] `CLOSE_WAIT` piling up = your app never called `close()` — an fd leak, not network churn.
- [ ] Client idle timeout must be shorter than the ALB/NAT idle timeout, or you get random resets.
- [ ] Kernel TCP keep-alive defaults to 7200 s — set it per-socket to detect dead peers.
- [ ] Sockets are fds; `ulimit -n` (often 1024 in containers) causes "Too many open files".
- [ ] Sockets are identified by the 4-tuple, so one server port serves unlimited connections.
- [ ] L4 balances connections, L7 balances requests — that difference is the whole trade-off.
- [ ] Know where TLS terminates: terminate / terminate-and-re-encrypt / passthrough.
- [ ] Trust `X-Forwarded-For`/`-Proto` behind an LB or you log LB IPs and emit `http://` redirects.
- [ ] NAT keeps per-flow state with an idle timeout; AWS NAT Gateway costs per GB and caps connections.
- [ ] CDN = distributed reverse-proxy cache; the cache key is the thing most often misconfigured.
- [ ] Prefer versioned URLs over purge-based invalidation.
- [ ] SSE for server→client; WebSocket only when you need bidirectional.
- [ ] WebSockets are stateful: need a pub/sub backplane, heartbeats, and reconnect-with-jitter.
- [ ] Webhook receivers must be idempotent, signature-verifying, and fast (ack then queue).
- [ ] C10K: thread-per-connection costs ~1 MB stack + context switches while connections sit idle.
- [ ] `select`/`poll` are O(n) per call; `epoll` keeps a persistent interest set and returns only ready fds.
- [ ] Netty-style event loops: few threads, thousands of channels, and **never block the loop**.
- [ ] Virtual threads give epoll-class scalability with blocking-style code, real stack traces, working `ThreadLocal`.
- [ ] Loom caveats: pinning (`synchronized`/native on JDK 21), no help for CPU-bound work, and you must add explicit concurrency limits.
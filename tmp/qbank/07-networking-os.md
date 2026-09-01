# 07 — Networking & OS Fundamentals

**What this decides:** how deep Weeks 3–4 of the prep plan need to go
(refresher vs first-pass learning), and whether hands-on tooling practice
(`curl -v`, `dig`, `ss`) needs adding. These are interview tiebreakers — a
junior-level miss here at interview time reads badly.

---

## Part A — Networking ladder

### Q1 [L1] explain-back — TCP vs UDP
Differences + one real example each where the choice matters.
**Strong answer:** TCP: connection, ordering, retransmission, flow/congestion
control → HTTP/APIs/DBs. UDP: fire-and-forget datagrams → DNS, video/voice,
gaming; also the base of QUIC/HTTP3. Bonus: "reliability is built in the
protocol vs built by you."

### Q2 [L2] discriminator — Type a URL, hit Enter → page renders
Walk through everything that happens. (Score by tier.)
**L1 tier:** "DNS finds the IP, browser sends request, server responds."
**L2 tier (=1.0 here):** DNS resolution chain with caching → TCP 3-way
handshake (name SYN/SYN-ACK/ACK) → TLS handshake → HTTP request/response,
status + headers → connection reuse (keep-alive).
**L4 tier (bonus):** ALPN choosing h2, CDN/edge in the path, connection
pooling, DNS TTL trade-offs, where a load balancer sits.

### Q3 [L2] explain-back — TLS: what does the handshake actually achieve?
**Strong answer:** three goals: authenticate the server (certificate chain →
trusted CA), agree on symmetric session keys (asymmetric crypto only for the
exchange — too slow for bulk data), integrity. Bonus: SNI, why certs expire/
rotate, what "certificate validation failed" in a Java client usually means
(truststore). **Red flags:** "it encrypts traffic" with no how.

### Q4 [L2] explain-back — DNS resolution + caching
Resolver chain for `api.example.com`, and where the answer gets cached.
**Strong answer:** stub → recursive resolver → root → TLD (.com) →
authoritative NS → A/AAAA record; cached at every layer per TTL (OS, JVM!,
resolver). Bonus: knows the JVM caches DNS (`networkaddress.cache.ttl`) —
bites during failover; CNAME vs A.

### Q5 [L3] scenario — Port exhaustion / TIME_WAIT
A service making many short-lived outbound HTTP calls starts failing with
"cannot assign requested address." What's happening and what's the fix?
**Strong answer:** each closed connection sits in TIME_WAIT (~60s); ephemeral
port range exhausts under high connection churn. Fix: connection pooling /
keep-alive reuse (the real fix), not kernel-flag hacks first. Diagnosis:
`ss -s`, count TIME_WAIT. Naming pooling as the structural fix = 1.

### Q6 [L3] scenario — Timeout taxonomy
Your HTTP client "hangs" calling a downstream service. What distinct
timeouts exist, and what does each one's firing tell you?
**Strong answer:** connect timeout (can't establish TCP — network/security
group/dead host), read/socket timeout (connected, but no bytes — slow or
stuck server), pool-acquisition timeout (all pooled connections busy — often
YOUR bug), plus total/request timeout. No default timeout = infinite hang —
knows Java clients often ship with none. Distinguishing connect vs read is
the discriminator.

### Q7 [L3] explain-back — HTTP/1.1 vs HTTP/2 (vs 3, brief)
What problem did each solve?
**Strong answer:** 1.1: keep-alive, but one in-flight request per connection
→ HOL blocking at HTTP level, browsers open ~6 connections; 2: multiplexed
streams over one connection + header compression — but TCP-level HOL remains
(one lost packet stalls all streams); 3/QUIC: UDP-based, per-stream delivery,
faster handshakes. The two different HOL-blockings = full credit.

### Q8 [L4] discriminator — L4 vs L7 load balancing
Difference, when each, and where does TLS terminate?
**Strong answer:** L4 routes on IP/port (fast, content-blind); L7 parses HTTP
(path routing, header-based, retries, auth offload). TLS usually terminates
at the L7 LB (visibility, cert management) with re-encryption or trusted
network behind; sticky sessions and why stateless services avoid needing
them. Bonus: health-check behavior differences, connection draining.

---

## Part B — OS ladder

### Q9 [L2] explain-back — Process vs thread vs context switch
What does a context switch actually cost?
**Strong answer:** save/restore registers + kernel transition + the hidden
cost: cache/TLB pollution; threads switch cheaper than processes (shared
address space). Bonus: this is why thread-per-request caps out and why
epoll/virtual threads exist — connects forward to async I/O.

### Q10 [L3] explain-back — What happens to a thread on `socket.read()`?
And what are file descriptors — what does "Too many open files" mean?
**Strong answer:** blocking syscall → thread moves to waiting state, scheduler
runs others; data arrival wakes it. Everything is an fd (sockets, files,
pipes); per-process fd limit (`ulimit -n`); leaking connections/streams →
`Too many open files` → find with `lsof -p`. Bonus: contrasts with
non-blocking/epoll model (one thread, many fds, readiness notification).

### Q11 [L3] scenario — Box triage
You SSH into a slow prod box. Give the commands to answer: is it CPU? memory?
disk? and "which process is eating it?"
**Strong answer:** `top`/`htop` (load avg — knows what load average means
relative to core count; %us vs %sy vs %wa), `free -h` (available vs free,
page cache confusion), `df -h` / `du`, `iostat`/`%wa` for disk wait,
`ps aux --sort`. Load average > cores + high %wa = disk-bound, etc.
Interpreting, not just naming, the commands = 1.

### Q12 [L4] explain-back — SIGTERM vs SIGKILL and graceful shutdown
What's the difference, and what does a well-behaved service do on SIGTERM?
**Strong answer:** SIGTERM is catchable → stop accepting new work, finish
in-flight requests, close pools, then exit; SIGKILL is not catchable —
immediate death, no cleanup. Ties to deploys: orchestrators send SIGTERM,
wait a grace period, then SIGKILL; LB must deregister first. Bonus: JVM
shutdown hooks, `kill -9` folklore vs reality.

---

## Breadth checklist (rate 0–3)

- [CORE] `curl -v` — used to debug a real problem (read the handshake/headers)?
- [CORE] Reading response headers fluently (Content-Type, Cache-Control, Set-Cookie, Location)
- [CORE] grep/tail/less through a log file under pressure; pipes and `jq`
- [CORE] What a socket is (ip:port pair × 2 + protocol)
- `dig` / `nslookup` — ever used
- `ss` / `netstat` / `lsof` — ever used
- NAT + private IP ranges — why your laptop's IP isn't routable
- CDN mental model (edge caching, cache keys, origin)
- WebSockets — what the Upgrade handshake is (concept)
- gRPC/HTTP2 relationship (heard-of level fine)
- Virtual memory: pages, why "memory used" is ambiguous, what swapping does
- OOM killer (Linux) vs JVM OOM — different things (heard of?)
- cron — read/write a crontab line
- ssh keys, scp/rsync basics
- strace (0–1 fine)
- Epoll/kqueue readiness model (0–1 fine — becomes relevant Day 104 of plan)

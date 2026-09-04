# Syllabus — 10 Networking

**Target version baseline (checked 2026-09-04).** Every constant, sysctl name, default value, header
field, frame code and system property below is stated against this set of specifications and
releases, and every leaf that depends on a version says so:

| Layer | Normative source this file targets |
|---|---|
| TCP | **RFC 9293** (Aug 2022) — the consolidated TCP specification, obsoletes RFC 793/879/6093/6429/6528/6691 and parts of 1011/1122/5961 |
| TCP congestion control | **RFC 5681** (Reno), **RFC 9438** (CUBIC, Aug 2023), **RFC 6298** (RTO), **RFC 8985** (RACK-TLP), **RFC 3168** (ECN), **RFC 7413** (TCP Fast Open); BBRv3 as an IETF draft, not an RFC |
| UDP / IP | **RFC 768**, **RFC 791**/**RFC 8200** (IPv6), **RFC 1191**/**RFC 8899** (PMTUD/PLPMTUD), **RFC 4443** (ICMPv6) |
| Sockets / kernel | **Linux 6.x** `man 7 tcp`, `man 7 socket`, `man 7 ip`, `man 7 epoll`, `Documentation/networking/ip-sysctl.rst` |
| HTTP semantics | **RFC 9110** (June 2022) |
| HTTP caching | **RFC 9111**, plus **RFC 5861** (`stale-while-revalidate`, `stale-if-error`) |
| HTTP/1.1 syntax | **RFC 9112** |
| HTTP/2 | **RFC 9113** (June 2022, obsoletes RFC 7540) + **RFC 7541** (HPACK) |
| HTTP/3 | **RFC 9114** + **RFC 9204** (QPACK) + **RFC 9218** (Extensible Priorities) |
| QUIC | **RFC 8999** (invariants), **RFC 9000** (transport), **RFC 9001** (TLS binding), **RFC 9002** (loss detection and congestion control), **RFC 9221** (unreliable datagrams), **RFC 9298** (CONNECT-UDP) |
| TLS | **RFC 8446** (TLS 1.3), **RFC 5246** (TLS 1.2, historical), **RFC 5280** (PKIX), **RFC 6066** (SNI/OCSP stapling), **RFC 7301** (ALPN), **RFC 8879** (cert compression), **RFC 6962/9162** (Certificate Transparency), **RFC 8555** (ACME) |
| DNS | **RFC 1034/1035**, **RFC 2181** (clarifications, TTL semantics), **RFC 2308** (negative caching), **RFC 6891** (EDNS(0)), **RFC 7766** (DNS over TCP), **RFC 7858** (DoT), **RFC 8484** (DoH), **RFC 9250** (DoQ), **RFC 4033–4035** (DNSSEC), **RFC 9460** (SVCB/HTTPS RRs) |
| Dual stack | **RFC 8305** (Happy Eyeballs v2), **RFC 6724** (address selection) |
| WebSocket | **RFC 6455** + **RFC 7692** (`permessage-deflate`) + **RFC 8441** (WebSocket over HTTP/2 extended CONNECT) |
| SSE | **WHATWG HTML Living Standard**, "Server-sent events" |
| Proxy metadata | **RFC 7239** (`Forwarded`), **HAProxy PROXY protocol v1/v2** |
| gRPC | **grpc/grpc `doc/PROTOCOL-HTTP2.md`** + `keepalive.md` |
| Java runtime | **Java 21 LTS** as the baseline for all code; JDK 24/25 deltas marked `[VERSION-TRAP]` |
| Java HTTP client | `java.net.http.HttpClient` (JDK 21) and its `jdk.httpclient.*` properties, from the JDK 21 `java.net.http` module summary |
| Java network properties | JDK 21 `java/net/doc-files/net-properties.html` |
| Framework | **Spring Boot 3.5.x** (`RestClient`, `WebClient`, `RestTemplate`), Apache HttpClient 5.x, OkHttp 4.x/5.x, Netty 4.1/4.2 |
| Cloud | **AWS ALB/NLB** documented defaults (idle timeout 60 s, client keep-alive 65 s, deregistration delay 300 s), NAT Gateway limits |

## The seventeen deltas that most often produce a stale networking answer

Each is marked `[VERSION-TRAP]` at its leaf.

1. **RFC 793 is obsolete.** The citable TCP specification is **RFC 9293** (Aug 2022). Answers that
   cite 793 are citing a document withdrawn from Standards Track in 2022. `[RESEARCH]`
2. **RFC 7540 is obsolete.** HTTP/2 is **RFC 9113**, and it **deprecates the entire RFC 7540
   priority scheme** (the PRIORITY frame, the dependency tree, weights and exclusive flags).
   Explaining HTTP/2 stream priority as a dependency tree is a 2015 answer; the current mechanism is
   **RFC 9218 Extensible Priorities** with the `Priority` header field and `u=`/`i=` parameters.
   `[RESEARCH]`
3. **RFC 2616 is obsolete twice over.** HTTP semantics is **RFC 9110**, caching **RFC 9111**,
   HTTP/1.1 syntax **RFC 9112**. "RFC 2616 says" dates you by a decade.
4. **HTTP/2 Server Push is dead in practice.** Chrome removed support in 2022; RFC 9113 states a
   server **MUST NOT** set `SETTINGS_ENABLE_PUSH` to 1. The replacement is `103 Early Hints`
   (RFC 8297) with `Link: rel=preload`. `[RESEARCH]`
5. **`net.ipv4.tcp_tw_recycle` no longer exists.** Removed in Linux **4.12** (2017). Any tuning guide
   that recommends it is pre-2017 and was wrong even then behind NAT.
6. **The `TIME_WAIT` duration on Linux is not `tcp_fin_timeout`.** It is a compile-time
   `TCP_TIMEWAIT_LEN` of **60 s**; `tcp_fin_timeout` (default 60 s) bounds `FIN_WAIT_2`. The two are
   conflated in most blog posts.
7. **JDK 21+ virtual threads changed the C10K answer**, and **JEP 491 (JDK 24)** removed
   `synchronized`-block pinning entirely and **removed the `jdk.tracePinnedThreads` system
   property**. "Virtual threads pin on `synchronized`" is true on 21 and false from 24.
   `[RESEARCH]`
8. **The JDK's DNS cache defaults are not "cache forever."** With no Security Manager, JDK 21's
   `networkaddress.cache.ttl` behaviour is a positive TTL of 30 s and
   `networkaddress.cache.negative.ttl` of **10 s**; the "forever" default applied only with a
   Security Manager installed, and the Security Manager is deprecated for removal (JEP 411) and
   **disallowed by default from JDK 24 (JEP 486)**. There is also a newer
   `networkaddress.cache.stale.ttl` knob for serving stale entries during resolution failure.
   `[RESEARCH]`
9. **`HttpURLConnection` is not the modern client.** `java.net.http.HttpClient` (JDK 11+) is, and its
   pool/keep-alive is tuned by `jdk.httpclient.keepalive.timeout` (**30 s**),
   `jdk.httpclient.connectionPoolSize` (**0 = unbounded**), `jdk.httpclient.maxstreams` (**100**),
   `jdk.httpclient.windowsize` (**16 MB**) and `jdk.httpclient.connectionWindowSize` (**2^26**).
   `[RESEARCH]`
10. **`RestTemplate` is in maintenance mode.** Spring Framework 6.1 introduced **`RestClient`** as
    the synchronous fluent replacement; `WebClient` remains the reactive one. Boot 3.4+ ships
    `RestClient.Builder` auto-configuration and `ClientHttpRequestFactorySettings` with explicit
    connect/read timeouts. `[RESEARCH]`
11. **Alt-Svc is no longer the only HTTP/3 discovery mechanism.** The **HTTPS RR (RFC 9460, DNS type
    65)** advertises `alpn="h3"` in DNS, letting a client go straight to QUIC on the first
    connection, and it solves the apex-CNAME problem natively via AliasMode. `[RESEARCH]`
12. **TLS 1.0/1.1 are formally deprecated (RFC 8996)** and disabled by default in JDK 8u291+/11.0.11+
    and all modern JDKs via `jdk.tls.disabledAlgorithms`. Also: TLS 1.3 **removed** renegotiation,
    compression, static RSA key transport and custom DHE groups, so "renegotiate to request a client
    cert" is a TLS 1.2 answer — TLS 1.3 uses post-handshake authentication instead.
13. **CUBIC is the Linux default congestion control, not Reno**, and has been since kernel 2.6.19
    (2006). It is now standardised as **RFC 9438** with `C = 0.4` and `beta_cubic = 0.7`. BBR (v1
    2016, v3 in progress) is the alternative you must be able to contrast, not a default.
    `[RESEARCH]`
14. **`net.core.somaxconn` default changed from 128 to 4096** in Linux 5.4. Guides telling you to
    raise it from 128 are pre-2019. `[RESEARCH]`
15. **ALB supports gRPC and HTTP/2 to targets but not HTTP/3**; HTTP/3 on AWS is CloudFront-only.
    ALB's **client keep-alive default is 65 s** and its **idle timeout default is 60 s** — the pair
    is the source of the classic random-reset incident. `[RESEARCH]`
16. **`X-Forwarded-For` was never standardised; `Forwarded` (RFC 7239) is the standard** with
    `for=`/`by=`/`host=`/`proto=` parameters and obfuscated node identifiers. Spring's
    `server.forward-headers-strategy` handles both.
17. **io_uring is the current high-performance Linux I/O interface**, not epoll, for storage and
    increasingly for networking; and **kTLS** moves TLS record encryption into the kernel enabling
    `sendfile` over TLS. Neither existed when the C10K essay was written. `[RESEARCH]`

## Scope boundary against the sibling guides

This file owns **the wire**: every layer a byte crosses between one process and another, the state
each layer holds, the cost each layer adds, and the failure each layer produces. Owned elsewhere:

- TLS as a **trust** mechanism — what a certificate proves, CA compromise, mTLS as identity, OWASP
  transport failures, HSTS, CSP, cookie attributes and the whole adversary model — lives in
  `13-web-security.md`. This guide owns TLS as a **cost and a handshake**, and the operational
  failure modes (`PKIX path building failed`, missing intermediates, SNI, resumption).
  `[X-REF 13]`
- REST resource modelling, status-code selection as a contract, idempotency keys, pagination,
  versioning, rate-limit headers and gRPC/GraphQL *design* trade-offs live in `12-api-design.md`.
  This guide owns the HTTP **protocol mechanism** those contracts ride on. `[X-REF 12]`
- Processes, scheduling, virtual memory, `ulimit`, the OOM killer, `lsof`/`strace`/`ss` as a general
  toolkit, and cgroup accounting live in `11-operating-systems-linux.md`. This guide owns the
  network-specific subset. `[X-REF 11]`
- Threads, the memory model, `ThreadPoolExecutor`, `CompletableFuture`, `ThreadLocal` and the
  concurrency semantics of virtual threads live in `05-multithreading-concurrency.md` and
  `04-modern-java.md`. This guide owns what those mechanisms do to **connections**. `[X-REF 05]`
  `[X-REF 04]`
- Heap sizing, GC pause interaction with the accept queue, direct/native memory for NIO buffers, and
  heap-dump workflow live in `06-jvm-internals.md`. `[X-REF 06]`
- JDBC pool sizing, statement round-trips and the database's own wire protocol live in
  `09-sql-databases.md`. This guide owns the socket underneath the pool. `[X-REF 09]`
- Kafka's protocol, consumer-group rebalancing, delivery semantics and the outbox live in
  `14-messaging-queues.md`. This guide owns the transport-level reasons a broker connection stalls.
  `[X-REF 14]`
- Redis mechanics, eviction and cache-aside live in `15-caching.md`. This guide owns HTTP caching
  and CDN edge behaviour. `[X-REF 15]`
- VPC, subnets, security groups, NAT Gateway pricing, Route 53 routing policies, ALB/NLB
  configuration surfaces and CloudFront features live in `18-cloud-aws.md`. This guide owns the
  protocol mechanism each of those implements. `[X-REF 18]`
- Container networking as a *Kubernetes object model* (Service, Ingress, NetworkPolicy, CNI choice,
  service mesh install) lives in `19-docker-kubernetes.md`. This guide owns veth/bridge/conntrack
  and what kube-proxy actually programs. `[X-REF 19]`
- Metrics, tracing, context propagation, SLOs and alerting live in
  `20-observability-operations.md`. This guide owns the network-specific signals worth emitting.
  `[X-REF 20]`
- Back-of-envelope capacity arithmetic, CAP/PACELC, multi-region strategy, load shedding as a
  capacity decision and the 45-minute design structure live in `22-system-design.md`. `[X-REF 22]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in one paragraph *before* pointing away — it never sends the reader off empty-handed.

## The example domain

**Every example, endpoint, hostname, service name, status code and number comes from the QuizStakes
domain in `src/scenario/scenario.md`.** The network-relevant surfaces the bible must trace are:
`ApplicationGateway` (TLS termination, the client-token strip, `X-Forwarded-For` handling),
`RouterInt`, `JwtService`, `AccountOpening` (`AO-*`), `AccountMaintenance` (`AA-*`),
`ClientRestrictions` (the 30 ms budget — the tightest network budget in the system),
`PaymentService` → card PSP (p50 240 ms / p99 11 s authorise, p50 180 ms / p99 6 s capture),
the identity-verification vendor (p50 900 ms, **p99 38 s** — the timeout-selection example),
`FundsLedger` (three instances, 12 GB heap, connection-pool-sensitive), `DocumentRequirements`,
`InternalPlatforms`, `ProfileService` (an eight-owner read-model fan-out where latency is the
slowest leg and availability is the *product* of the legs). Never `api.example.com` as the only
framing, never `foo.bar`, never `thread1`.

The load figures that constrain every capacity claim in this guide: **2.4M registered clients**,
**95k card deposits/day at 40/sec**, **2.8M stake reservations/day at 1,200/sec with 3,400/sec
settlement bursts**, **19.8M ledger entries/day at 230 writes/sec sustained and 13,600/sec peak**,
a **30 ms restriction-decision budget**, a **150 ms stake-reservation budget**, a hard **500 ms
self-exclusion budget**, card deposits averaging **300 ms with a p99 of 12 s**, PSP rate limits of
**500/sec** (authorise/capture) and **200/sec** (payout).

The four architectural rules from scenario § 5.1 are network constraints and the bible must say so
at the point of decision: the client token is **stripped at `ApplicationGateway`** (so the edge is a
protocol boundary, not just a router); **no token carries permissions or status** (so every money
path makes a live network call to `ClientRestrictions` inside 30 ms — the latency budget *is* the
security design); `FundsLedger` uses **partition affinity by client id** (which shapes connection
topology and hot-partition behaviour); and **`PaymentRun` is not a client state** (so operator
traffic and client traffic are different network domains with different budgets).

## Tag legend

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real RFC text, kernel source/doc, javadoc or implementation source (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code (or a complete runnable artifact where the artifact is a config file or a shell session) |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in the baseline and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value or byte/latency arithmetic explicitly |
| `[SYSCTL]` | give the exact kernel parameter or socket-option name and its default |
| `[HDR]` | give the exact HTTP field name and an example value |
| `[WIRE]` | show the actual bytes/frames/packets, not a description of them |
| `[SPEC]` | cite the specific RFC/spec section number, not just the document |
| `[FLOW]` | must be rendered as an ordered step-by-step trace |
| `[TABLE]` | must be rendered as a table |
| `[API]` | must state the exact Java/Spring type, method signature or property name |
| `[DIAG]` | must show real diagnostic output — an `ss` line, a `tcpdump` frame, a `dig` answer, a stack trace, an error string — and read it line by line |
| `[CALC]` | must show the arithmetic (RTT budget, BDP, port exhaustion rate, bytes on the wire) |
| `[INCIDENT]` | must be framed as a production failure: symptom, diagnosis path, root cause, fix |

---

# PART 1 — BASICS

Everything a backend engineer must be able to state cold: why each layer exists, what it guarantees,
what its vocabulary means, and what its complete surface is. No leaf here is optional.

## §1.1 Why networking is a backend discipline, not an infrastructure one

1.1.1 The problem statement: a distributed system is a program whose function calls can be **slow,
      reordered, duplicated, silently dropped, or answered by a machine that has already forgotten
      the question**. Every mechanism in this guide exists to convert one of those failures into a
      manageable one. `[PROVE]`
1.1.2 The eight fallacies of distributed computing (Deutsch/Gosling): the network is reliable,
      latency is zero, bandwidth is infinite, the network is secure, topology doesn't change, there
      is one administrator, transport cost is zero, the network is homogeneous. Each fallacy maps to
      a specific section of this guide. `[TABLE]`
1.1.3 Why the interview asks: "what happens when you type a URL" touches DNS, TCP, TLS, HTTP,
      load balancing, caching and rendering in one question, and it is impossible to fake.
1.1.4 The four questions a backend engineer is actually paid to answer about the network: *why is it
      slow*, *why did it fail intermittently*, *why did it fail only under load*, and *where does
      the byte get encrypted*.
1.1.5 The QuizStakes framing: a stake reservation must complete in **150 ms p99** while making a
      **30 ms** restriction call; the network budget is not a background detail, it is the design
      constraint. `[NUM]`
1.1.6 What "the network" is composed of physically: NIC, driver, kernel stack, socket buffer,
      process; then switch, router, firewall, NAT, load balancer, proxy, CDN edge. Every one holds
      state and every one can drop your packet.
1.1.7 The single most useful mental habit: **for every failure, name the layer**. A `connection
      reset` is a TCP event; a `502` is an HTTP-layer report of a TCP or application event beneath
      it; a `SSLHandshakeException` is neither.

*(7 leaves)*

## §1.2 The layered model and encapsulation

1.2.1 The OSI seven layers by name and number (physical, data link, network, transport, session,
      presentation, application) and why layers 5–6 are essentially fictional in TCP/IP. `[TABLE]`
1.2.2 The TCP/IP four-layer model (link, internet, transport, application) as the model that
      actually matches the code, and the mapping between the two. `[TABLE]`
1.2.3 **Encapsulation**, byte by byte: application payload → TCP segment (20-byte minimum header) →
      IP packet (20-byte minimum IPv4 header) → Ethernet frame (14-byte header + 4-byte FCS).
      `[CALC]` `[WIRE]`
1.2.4 The overhead arithmetic: a 1500-byte MTU carries 1500 − 20 (IP) − 20 (TCP) = **1460 bytes** of
      payload with no options; with timestamps enabled it is 1448. Why "1460" appears everywhere.
      `[CALC]` `[NUM]`
1.2.5 Why layering is a *leaky* abstraction and where it leaks in this guide: TCP HOL blocking
      leaking into HTTP/2, MTU leaking into TLS record sizing, NAT leaking into keep-alive design,
      TLS leaking into load-balancer capability.
1.2.6 The "one layer's payload is the next layer's header+payload" rule, and how to read a
      `tcpdump -X` hexdump against it. `[WIRE]` `[DIAG]`
1.2.7 Where the layer boundary sits in Java: `Socket`/`SocketChannel` is the transport boundary;
      everything above it (HTTP, gRPC, JDBC wire protocol) is your problem or your library's.
      `[API]`
1.2.8 Middleboxes as the reason layering is not respected in the wild: NATs read L4, firewalls read
      L4–L7, load balancers rewrite L7, and **protocol ossification** is the consequence — the
      reason QUIC encrypts almost its entire header. `[PROVE]`

*(8 leaves)*

## §1.3 The physics: latency, bandwidth, and what cannot be optimised

1.3.1 Speed of light in fibre ≈ **200,000 km/s** (≈ 2/3 of c). London→New York ≈ 5,600 km ⇒ ~28 ms
      one way, ~56 ms RTT as a theoretical floor; real-world ~70–80 ms. `[CALC]` `[NUM]`
1.3.2 The latency numbers every engineer should know, as an ordered table: L1 cache ~1 ns, main
      memory ~100 ns, SSD random read ~16 µs, datacentre round trip ~0.5 ms, same-region AZ hop
      ~1 ms, cross-region ~50–150 ms, intercontinental ~150–250 ms. `[TABLE]` `[NUM]`
1.3.3 **Latency and bandwidth are independent**. Adding bandwidth does not reduce RTT. This is why
      an extra round trip costs the same on a 1 Gbps link as on a 10 Mbps one. `[PROVE]`
1.3.4 **Bandwidth-delay product (BDP)** = bandwidth × RTT: the bytes in flight required to saturate
      a path. 1 Gbps × 80 ms = 10 MB. If your window is smaller than the BDP you cannot fill the
      pipe regardless of link speed. `[CALC]` `[PROVE]`
1.3.5 Why BDP forces **window scaling** (§1.10): the unscaled TCP window field is 16 bits = 65,535
      bytes, which caps throughput at 65,535 / 0.08 s ≈ **6.5 Mbps** on an 80 ms path. `[CALC]`
      `[NUM]`
1.3.6 Round trips as the unit of cost: DNS (0–1 RTT) + TCP (1 RTT) + TLS 1.3 (1 RTT) + request
      (1 RTT) = **3 RTTs before the first byte** on a cold connection; at 80 ms that is 240 ms of
      pure protocol. `[CALC]` `[FLOW]`
1.3.7 Tail latency: why p99 and p99.9 are the numbers that matter, and why a fan-out of *n*
      independent calls has a p99 governed by the *max* of *n* draws — with 8 owners at p99=100 ms,
      the fan-out p99 is far worse than 100 ms. The QuizStakes `ProfileService` eight-owner fan-out
      is exactly this. `[PROVE]` `[CALC]`
1.3.8 Availability of a serial fan-out is the **product** of the legs: eight dependencies at 99.9%
      each gives 99.2%. Stated in scenario § "read model fan-out". `[CALC]` `[PROVE]`
1.3.9 Jitter and its causes: queueing at routers, bufferbloat, GC pauses, scheduler delay,
      retransmission. Distinguish network jitter from application jitter — they have different
      fixes. `[X-REF 06]`
1.3.10 Throughput vs goodput: goodput excludes headers and retransmissions. On a lossy link with 1%
       loss, goodput can be a small fraction of link rate. `[NUM]`
1.3.11 Why "move the computation to the data" and "co-locate chatty services" are latency
       arguments, and why an N+1 pattern is far more expensive across a network than in-process.
       `[X-REF 09]`

*(11 leaves)*

## §1.4 The link layer, MTU, MSS and path MTU discovery

1.4.1 Ethernet frame format: destination MAC (6), source MAC (6), EtherType (2), payload, FCS (4);
      minimum frame 64 bytes, standard MTU **1500** bytes. `[WIRE]` `[NUM]`
1.4.2 MAC addresses, broadcast domains, switching by MAC learning table, and why a switch is not a
      router.
1.4.3 **ARP** (IPv4) and **NDP/Neighbour Discovery** (IPv6): resolving an IP to a MAC on the local
      segment, the ARP cache (`ip neigh`), and gratuitous ARP as a failover mechanism (how a VIP
      moves between hosts). `[DIAG]`
1.4.4 **MTU** vs **MSS**: MTU is the link's maximum frame payload; MSS is the maximum TCP *segment*
      payload = MTU − IP header − TCP header. MSS is advertised as a TCP option in the SYN.
      `[NUM]` `[SPEC]`
1.4.5 The RFC 9293 default MSS values when nothing is advertised: **536 bytes for IPv4, 1220 bytes
      for IPv6** (§3.7.1). `[NUM]` `[SPEC]` `[RESEARCH]`
1.4.6 **Jumbo frames** (MTU 9000) inside a datacentre: the throughput and CPU win, and why they
      break the moment traffic leaves the segment. AWS supports 9001 within a VPC. `[NUM]`
1.4.7 Tunnelling overhead as an MTU reducer: VXLAN (50 bytes), GRE (24), IPsec (~50–70), WireGuard
      (60), PPPoE (8). A 1500-byte MTU inside a VXLAN overlay is a misconfiguration. `[CALC]`
1.4.8 **IP fragmentation**: how IPv4 fragments (offset, MF flag, identification field), why it is
      pathological (one lost fragment kills the whole datagram; stateful firewalls often drop
      fragments), and why **IPv6 forbids router fragmentation entirely**. `[PROVE]`
1.4.9 **PMTUD (RFC 1191)**: set the DF bit, rely on `ICMP Type 3 Code 4 "fragmentation needed"` to
      learn the path MTU. `[SPEC]`
1.4.10 **The PMTUD black hole** — the classic incident. A firewall drops all ICMP, so the sender
       never learns the MTU is smaller. Symptom: the TCP handshake succeeds and small requests work,
       but any response over ~1400 bytes hangs forever. Diagnosis: `ping -M do -s 1472`,
       `tracepath`. Fix: allow ICMP type 3, or clamp MSS. `[TRAP]` `[INCIDENT]` `[DIAG]`
1.4.11 **MSS clamping** (`iptables ... --clamp-mss-to-pmtu`, `ip route ... advmss`) as the
       operational workaround, and where cloud NAT gateways and VPNs do it for you.
1.4.12 **PLPMTUD (RFC 8899)** as the ICMP-independent replacement, and why QUIC uses it (DPLPMTUD)
       rather than trusting ICMP. `[RESEARCH]`
1.4.13 Reading the MTU on a box: `ip link show`, `ip route get <ip>`, `tracepath <host>`. `[DIAG]`

*(13 leaves)*

## §1.5 IP: addressing, routing, and the fields that matter

1.5.1 The IPv4 header field by field: version, IHL, DSCP/ECN, total length, identification, flags
      (DF/MF), fragment offset, **TTL**, protocol (6=TCP, 17=UDP, 1=ICMP), header checksum, source,
      destination, options. `[WIRE]` `[NUM]`
1.5.2 The IPv6 header: fixed **40 bytes**, no checksum, no fragmentation fields, `Hop Limit`
      instead of TTL, `Next Header` chain for extension headers, flow label. Why the fixed header
      is a routing-performance decision. `[WIRE]` `[PROVE]`
1.5.3 **CIDR notation** and subnet arithmetic: `/24` = 256 addresses (254 usable), `/16` = 65,536,
      `/32` = a single host. Network address, broadcast address, and AWS's reservation of **5
      addresses per subnet**. `[CALC]` `[X-REF 18]`
1.5.4 Private address ranges (RFC 1918): `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`; loopback
      `127.0.0.0/8`; link-local `169.254.0.0/16` (and why `169.254.169.254` is the cloud metadata
      endpoint, and `169.254.169.253` the AWS VPC DNS resolver). `[NUM]`
1.5.5 **CGNAT** range `100.64.0.0/10` and why seeing it as a client IP means the client is behind a
      carrier NAT.
1.5.6 Routing: the routing table, longest-prefix match, default gateway, `ip route get` as the way
      to ask the kernel which route it will actually use. `[DIAG]`
1.5.7 **TTL/Hop Limit** as a loop-prevention counter, decremented per hop, and how `traceroute`
      abuses it (send TTL=1, 2, 3… and read the `ICMP Time Exceeded` from each hop). `[PROVE]`
1.5.8 **ICMP** message types worth knowing: Echo Request/Reply (8/0), Destination Unreachable
      (type 3 — codes 0 net, 1 host, 3 **port unreachable**, 4 **fragmentation needed**), Time
      Exceeded (11), Redirect (5). Port-unreachable is how a UDP "connection refused" is reported.
      `[NUM]` `[SPEC]`
1.5.9 **Trap:** treating `ping` failure as "the host is down". ICMP is frequently blocked by policy;
      a host can serve 50k rps and not answer a ping. Use `tcping`/`nc -vz`/`curl` against the
      actual port. `[TRAP]`
1.5.10 IPv6 essentials for a backend engineer: address notation and `::` compression, `/64` subnets,
       link-local `fe80::/10`, SLAAC vs DHCPv6, dual-stack, and **why `localhost` may resolve to
       `::1` and break a service bound only to `0.0.0.0`**. `[TRAP]`
1.5.11 `java.net.preferIPv4Stack` (default `false`) and `java.net.preferIPv6Addresses` (default
       `false`) as the JVM's dual-stack knobs. `[API]` `[NUM]` `[RESEARCH]`
1.5.12 **Anycast**: the same IP announced from many locations via BGP, routed to the topologically
       nearest. The mechanism behind `8.8.8.8`, root DNS servers, and CDN edge selection.
1.5.13 BGP in the amount a backend engineer needs: it is the routing protocol between autonomous
       systems, it is trust-based, and BGP hijacks/leaks are a real outage class (name the
       Facebook 2021 BGP withdrawal). `[INCIDENT]`
1.5.14 DSCP/ToS and QoS marking — why it exists, and why it is almost always ignored across the
       public internet.

*(14 leaves)*

## §1.6 UDP, completely

1.6.1 The UDP header: **exactly 8 bytes** — source port (2), destination port (2), length (2),
      checksum (2). Nothing else. `[WIRE]` `[NUM]` `[SPEC]`
1.6.2 What UDP adds to raw IP: **ports** (demultiplexing to a process) and an optional integrity
      **checksum**. That is the entire contribution. `[PROVE]`
1.6.3 Datagram semantics: **one `send` = one `recv`**. Message boundaries are preserved. This is the
      single most important behavioural difference from TCP and it goes the *other* way from what
      people expect. `[TRAP]`
1.6.4 What UDP does *not* provide: no handshake, no ordering, no retransmission, no duplicate
      suppression, no flow control, no congestion control. Each absence is a job you inherit.
      `[TABLE]`
1.6.5 The maximum UDP payload: 65,507 bytes theoretical (65,535 − 8 UDP − 20 IP), but anything over
      the path MTU fragments; the practical safe size is **~1400 bytes**, and **508 bytes** is the
      universally safe figure. `[CALC]` `[NUM]`
1.6.6 UDP "connection refused": `connect()` on a UDP socket does not send anything; a subsequent
      send to a closed port yields an `ICMP port unreachable`, surfaced on the *next* operation.
      Why UDP error reporting is asynchronous and confusing. `[TRAP]`
1.6.7 Where UDP is genuinely correct in backend work: **statsd/DogStatsD metrics** (losing 1 in
      10,000 counters is acceptable; blocking a request thread is not), DNS, NTP, syslog, gossip
      protocols (SWIM, Serf), QUIC, real-time media, and multicast service discovery.
1.6.8 **Trap:** "UDP is faster than TCP." It avoids handshake RTT and HOL blocking, but with no
      congestion control naive UDP either floods a lossy link or under-utilises it, and goodput can
      be far worse than TCP's. QUIC is fast because it re-implemented reliability *per stream*, not
      because it is UDP. `[TRAP]`
1.6.9 `DatagramSocket`, `DatagramPacket`, `DatagramChannel` in Java, and the buffer-reuse hazard
      (`DatagramPacket.setLength` must be reset before each receive). `[API]` `[TRAP]`
1.6.10 UDP receive-buffer overflow: `net.core.rmem_max`, `SO_RCVBUF`, and reading the drop counter
       from `netstat -su` / `ss -u -m`. A silent metric loss is almost always this. `[SYSCTL]`
       `[DIAG]`
1.6.11 UDP checksum: optional in IPv4 (0 = not computed), **mandatory in IPv6**. `[SPEC]`
1.6.12 Broadcast vs multicast vs unicast, and why multicast does not work across most cloud VPCs.
       `[X-REF 18]`

*(12 leaves)*

## §1.7 TCP: the model and the header

1.7.1 TCP's contract in one sentence: a **reliable, in-order, flow-controlled, congestion-controlled,
      full-duplex byte stream between two ports**. Every word is a mechanism. `[PROVE]`
1.7.2 The TCP header field by field with widths: source port (16), destination port (16), sequence
      number (32), acknowledgment number (32), data offset (4), reserved (4), control bits (8),
      window (16), checksum (16), urgent pointer (16), options (0–40 bytes). `[WIRE]` `[NUM]`
      `[SPEC]`
1.7.3 The eight control bits in RFC 9293 order: **CWR, ECE, URG, ACK, PSH, RST, SYN, FIN**, and what
      each actually causes. `[NUM]` `[SPEC]` `[RESEARCH]`
1.7.4 **Sequence numbers count bytes, not packets.** SYN and FIN each consume one sequence number.
      This is why the handshake ACK is `ISN+1`. `[PROVE]`
1.7.5 **ISN selection** (RFC 9293 §3.4.1): clock-driven with a pseudorandom function over the
      4-tuple and a secret, specifically to prevent off-path sequence-number guessing. `[SPEC]`
      `[RESEARCH]`
1.7.6 Cumulative acknowledgment semantics: `ACK = next expected byte`. Why a cumulative ACK cannot
      express "I got 1–100 and 200–300" without SACK. `[PROVE]`
1.7.7 The **PSH** flag: a hint to deliver buffered data to the application now. It is not a
      message boundary and cannot be used for framing. `[TRAP]`
1.7.8 The **URG** flag and urgent pointer: effectively deprecated (RFC 6093), inconsistently
      implemented, and a source of middlebox bugs. Know it exists; never use it.
1.7.9 The TCP checksum and the pseudo-header (source IP, dest IP, protocol, TCP length) — why the
      transport checksum covers IP fields, and why that breaks under NAT unless the NAT recomputes
      it. `[PROVE]`
1.7.10 **The byte-stream consequence: TCP has no message boundaries.** `write(100)` then
       `write(100)` may be read as one 200-byte read, or 37 then 163. Every protocol over TCP must
       define framing. `[TRAP]` `[PROVE]`
1.7.11 The three framing strategies and who uses each: **length prefix** (gRPC's 5-byte prefix,
       most binary protocols, Kafka), **delimiter** (`\r\n\r\n` for HTTP headers, `\n` for Redis
       RESP lines), **close-of-connection** (HTTP/1.0, and HTTP/1.1 responses with no
       `Content-Length` and no chunking). `[TABLE]`
1.7.12 Why "it worked on localhost" hides framing bugs: on loopback with small writes, one write
       usually equals one read; across a WAN under load, it never does. `[TRAP]` `[INCIDENT]`
1.7.13 Full duplex: the two directions are independent streams with independent sequence spaces,
       independent windows and independent closes. This is why close is four packets. `[PROVE]`

*(13 leaves)*

## §1.8 The TCP state machine

1.8.1 The eleven states by name (RFC 9293 §3.3.2): **CLOSED, LISTEN, SYN-SENT, SYN-RECEIVED,
      ESTABLISHED, FIN-WAIT-1, FIN-WAIT-2, CLOSE-WAIT, CLOSING, LAST-ACK, TIME-WAIT**. `[SPEC]`
      `[NUM]` `[RESEARCH]`
1.8.2 The full state-transition diagram traced as a table: state → event → action → next state.
      `[TABLE]` `[FLOW]`
1.8.3 **The three-way handshake** step by step: SYN (ISN_c) → SYN-ACK (ISN_s, ack=ISN_c+1) → ACK
      (ack=ISN_s+1). Client `SYN_SENT` → `ESTABLISHED`; server `LISTEN` → `SYN_RCVD` →
      `ESTABLISHED`. `[FLOW]` `[WIRE]` `[SPEC]`
1.8.4 **Why three and not two**: two packets cannot establish agreed initial sequence numbers in
      both directions and cannot reject a delayed duplicate SYN from a previous incarnation.
      `[PROVE]`
1.8.5 **Cost:** one full RTT before the first application byte. At 80 ms RTT that is 80 ms of pure
      setup, and it is the entire reason connection pooling and keep-alive exist. `[CALC]`
1.8.6 What data can ride on the handshake: nothing, unless **TCP Fast Open** (RFC 7413) is in use
      (§1.10.7). `[SPEC]`
1.8.7 **Simultaneous open** (RFC 9293 §3.5): both sides send SYN; both go `SYN_SENT` →
      `SYN_RECEIVED` → `ESTABLISHED`. Rare, but it is why `SYN_RECEIVED` is reachable from
      `SYN_SENT`. `[SPEC]` `[RESEARCH]`
1.8.8 **The four-way close**: FIN → ACK → FIN → ACK, because each direction closes independently.
      The **active closer** (first FIN) traverses `FIN_WAIT_1` → `FIN_WAIT_2` → `TIME_WAIT`; the
      passive closer traverses `CLOSE_WAIT` → `LAST_ACK` → `CLOSED`. `[FLOW]` `[WIRE]`
1.8.9 **Simultaneous close** and the `CLOSING` state — the only path into `CLOSING`. `[SPEC]`
1.8.10 **Half-close** (RFC 9293 §3.6.1): `shutdown(fd, SHUT_WR)` sends FIN while still reading.
       `Socket.shutdownOutput()` in Java. Used by protocols that signal "request complete" by
       closing the write side. `[API]` `[SPEC]`
1.8.11 **RST**: what generates one — connecting to a port with no listener, writing to a socket the
       peer has already closed and forgotten, `SO_LINGER` with timeout 0, an application calling
       `close()` with unread data in the receive buffer, a firewall injecting one. `[TABLE]`
       `[PROVE]`
1.8.12 **Trap:** `connection refused` (an RST came back — the host is reachable and nothing is
       listening; wrong port or process down) is a *different* failure from `connection timed out`
       (no response at all — dropped by firewall/security group, wrong IP, or a full accept queue).
       Conflating them sends every investigation down the wrong path. `[TRAP]` `[DIAG]`
1.8.13 What each state means when you see it in `ss -tan`, as an operational table: many
       `SYN_RECV` = SYN flood or slow accept; many `CLOSE_WAIT` = your application leaks sockets;
       many `TIME_WAIT` = churn on the active closer; `FIN_WAIT_2` piling up = peer never sent its
       FIN. `[TABLE]` `[DIAG]`
1.8.14 `TCP_USER_TIMEOUT` and `tcp_retries2` as the bound on how long a connection survives an
       unresponsive peer with unacknowledged data — the default is roughly **15 minutes**, which is
       far longer than any application timeout you would choose. `[SYSCTL]` `[NUM]` `[RESEARCH]`

*(14 leaves)*

## §1.9 Reliability: acknowledgment, retransmission, and loss detection

1.9.1 The retransmission timer (**RTO**) and RFC 6298: `SRTT` and `RTTVAR` exponentially weighted,
      `RTO = SRTT + max(G, 4*RTTVAR)`, with a **minimum of 1 second** in the RFC (Linux uses 200 ms
      via `TCP_RTO_MIN`) and a maximum of at least 60 s. `[NUM]` `[SPEC]` `[CALC]`
1.9.2 **Exponential backoff** of the RTO on repeated loss, and why a single lost packet in a
      short-lived connection can cost hundreds of milliseconds. `[CALC]`
1.9.3 **Karn's algorithm**: do not sample RTT from a retransmitted segment (you cannot tell which
      copy was acknowledged). `[PROVE]`
1.9.4 **Fast retransmit**: three duplicate ACKs trigger retransmission without waiting for the RTO.
      Why three (tolerating reordering of up to two segments). `[NUM]` `[PROVE]`
1.9.5 **Fast recovery** (RFC 5681): after fast retransmit, halve `cwnd` and inflate rather than
      returning to slow start.
1.9.6 **SACK** (RFC 2018) and D-SACK (RFC 2883): selective acknowledgment lets the receiver report
      non-contiguous received ranges, so the sender retransmits only the holes. Enabled by default
      on Linux (`net.ipv4.tcp_sack`). `[SYSCTL]`
1.9.7 **RACK-TLP** (RFC 8985): time-based loss detection replacing the dup-ACK heuristic, plus the
      Tail Loss Probe for the last packet of a burst (the case dup-ACKs cannot detect). Linux
      default since 4.18. `[SPEC]` `[RESEARCH]`
1.9.8 **The tail-loss problem stated:** the last segment of a response has no following segments to
      generate dup-ACKs, so its loss is detected only by RTO. This is why a 1% loss rate can add
      hundreds of milliseconds to p99 on small responses. `[PROVE]` `[CALC]`
1.9.9 **Spurious retransmission** and F-RTO / Eifel: distinguishing "lost" from "delayed", and why
      an over-aggressive RTO makes congestion worse.
1.9.10 **ECN** (RFC 3168): the ECT/CE bits in the IP header and the ECE/CWR bits in TCP let routers
       signal congestion by marking instead of dropping. `net.ipv4.tcp_ecn` (default 2 = accept but
       do not initiate on Linux). L4S/ECN++ as the modern direction. `[SYSCTL]` `[NUM]`
1.9.11 Reading retransmission counters: `netstat -s | grep -i retrans`, `nstat`,
       `ss -tin` (`retrans:`, `rto:`, `rtt:`, `cwnd:`, `bytes_retrans`). `[DIAG]`
1.9.12 **Trap:** "the network is dropping packets" is rarely a cable; it is usually a full queue —
       at a switch, at a NIC ring buffer, at a receive socket buffer, or at a conntrack table.
       Locate the queue before blaming the medium. `[TRAP]`

*(12 leaves)*

## §1.10 TCP options and the negotiations that happen in the SYN

1.10.1 The option format: kind (1 byte), length (1 byte), value; the 40-byte option-space budget and
       why it is contended. `[WIRE]` `[NUM]`
1.10.2 **MSS (kind 2)**: advertised in the SYN by each side; the effective MSS is the minimum of the
       two, further reduced by PMTU. `[SPEC]`
1.10.3 **Window Scale (kind 3, RFC 7323)**: a shift count 0–14 applied to the 16-bit window,
       allowing windows up to **1 GB**. **Negotiated only in the SYN** — if either SYN lacks it,
       scaling is off for the connection's whole life. `[NUM]` `[PROVE]`
1.10.4 **Trap:** a middlebox that strips the window-scale option from the SYN silently caps your
       throughput at 64 KB per RTT forever. Symptom: throughput plateaus at a suspiciously round
       number and does not improve with more bandwidth. `[TRAP]` `[CALC]`
1.10.5 **SACK-permitted (kind 4)** and **SACK blocks (kind 5)**.
1.10.6 **Timestamps (kind 8, RFC 7323)**: two 32-bit values (TSval, TSecr) enabling accurate RTT
       measurement and **PAWS** (Protection Against Wrapped Sequence numbers) — required on
       high-bandwidth paths where the 32-bit sequence space wraps in under 2×MSL. Cost: 12 bytes per
       segment. `[NUM]` `[SPEC]`
1.10.7 **TCP Fast Open (kind 34, RFC 7413)**: a server-issued cookie lets a client send data in the
       SYN, saving one RTT on reconnect. `net.ipv4.tcp_fastopen` bitmask (default `0x1` = client
       enabled). Rarely deployable because middleboxes drop unknown options. `[SYSCTL]` `[NUM]`
       `[RESEARCH]`
1.10.8 **Multipath TCP (RFC 8684)** in one paragraph: multiple subflows under one connection; used
       by Apple Siri and some mobile carriers; not something you configure in a Spring service.
1.10.9 How to see negotiated options: `tcpdump -v` on the SYN, and `ss -tin` for the resulting
       `wscale:` and `sack` flags. `[DIAG]`

*(9 leaves)*

## §1.11 Flow control: the receive window

1.11.1 The mechanism: the receiver advertises `rwnd` = free space in its receive buffer; the sender
       may have at most `rwnd` unacknowledged bytes in flight. Flow control protects the
       **receiver**, not the network. `[PROVE]`
1.11.2 The receive buffer as a real allocation: `net.ipv4.tcp_rmem` `[min, default, max]` and
       `net.core.rmem_max`; Linux **autotunes** the receive window between min and max based on
       measured BDP (`net.ipv4.tcp_moderate_rcvbuf`, default 1). `[SYSCTL]` `[NUM]` `[RESEARCH]`
1.11.3 The send buffer: `net.ipv4.tcp_wmem`, `net.core.wmem_max`, and what "the write returned" means
       — the bytes are in the kernel send buffer, **not delivered**. `[TRAP]` `[PROVE]`
1.11.4 `SO_RCVBUF` / `SO_SNDBUF`: the kernel **doubles** the value you set to account for
       bookkeeping overhead, and setting them explicitly **disables autotuning**. `[SYSCTL]`
       `[TRAP]` `[RESEARCH]`
1.11.5 **Zero-window** and the **window probe** (persist timer): when the receiver advertises 0, the
       sender periodically probes so a lost window update cannot deadlock the connection. `[PROVE]`
1.11.6 **Zero-window as an application diagnosis**: a `ZeroWindow` in a packet capture means the
       *application* is not calling `read()` fast enough — a slow consumer, a blocked thread, a GC
       pause. It is an application problem reported by the transport. `[DIAG]` `[INCIDENT]`
1.11.7 **Silly window syndrome** and the two halves of the fix: the receiver's (do not advertise
       tiny windows) and the sender's (Nagle). `[SPEC]`
1.11.8 Flow control is per-connection; there is no cross-connection fairness in TCP. That is the
       congestion controller's job. `[PROVE]`
1.11.9 `net.ipv4.tcp_notsent_lowat`: bound the unsent bytes the kernel will accept, so an
       application using `select`/`epoll` on writability gets accurate backpressure instead of
       filling a huge send buffer. The knob that makes bufferbloat visible to userspace. `[SYSCTL]`
       `[RESEARCH]`

*(9 leaves)*

## §1.12 Congestion control

1.12.1 The distinction that must be stated first: **flow control protects the receiver; congestion
       control protects the network.** The sender's effective window is
       `min(rwnd, cwnd)`. `[PROVE]`
1.12.2 The origin: the **1986 congestion collapse** of the NSFNET, throughput dropping from 32 kbps
       to 40 bps, and Van Jacobson's response. Congestion control is not an optimisation; it is what
       keeps the internet functioning. `[PROVE]`
1.12.3 **Slow start**: `cwnd` starts at the **initial window** (Linux: 10 MSS, RFC 6928) and doubles
       every RTT until `ssthresh` or loss. "Slow" describes the starting point, not the growth rate
       — it is exponential. `[NUM]` `[TRAP]`
1.12.4 The slow-start arithmetic that matters for HTTP: with IW=10 and MSS=1460, the first RTT
       carries ~14.6 KB, the second ~29 KB, the third ~58 KB. A 100 KB response needs **4 RTTs**
       even on an idle gigabit link. This is why a cold connection is slow. `[CALC]` `[PROVE]`
1.12.5 **Congestion avoidance**: additive increase (roughly +1 MSS per RTT) once past `ssthresh`.
1.12.6 **AIMD** (additive increase, multiplicative decrease) and why multiplicative decrease is
       required for stability and fairness. `[PROVE]`
1.12.7 **Reno / NewReno** (RFC 5681, RFC 6582) as the reference algorithm, and its failure on
       high-BDP paths — recovering to a 10 MB window by +1 MSS per RTT takes hours. `[CALC]`
1.12.8 **CUBIC (RFC 9438)**, the Linux default since 2.6.19: `W_cubic(t) = C·(t − K)³ + W_max` with
       **C = 0.4** and **beta_cubic = 0.7**; concave growth approaching `W_max`, convex probing
       beyond it; the **Reno-friendly region** (take `max(W_cubic, W_est)`), and **fast
       convergence** (reduce `W_max` further when the new peak is below the old one, so new flows
       can grab bandwidth). `[NUM]` `[SPEC]` `[SOURCE]` `[RESEARCH]`
1.12.9 Why CUBIC's growth is **RTT-independent** (a function of elapsed time, not of ACK arrivals)
       and why that matters for fairness between a nearby and a distant flow. `[PROVE]`
1.12.10 **BBR** (v1 2016, v2/v3 in progress): a model-based controller estimating bottleneck
        bandwidth and minimum RTT and pacing to `BtlBw × RTprop`, rather than treating loss as the
        congestion signal. Startup / drain / probe-BW / probe-RTT phases. Why it wins on lossy paths
        and why v1 was criticised for unfairness to CUBIC. Still an IETF draft, not an RFC.
        `[RESEARCH]` `[VERSION-TRAP]`
1.12.11 The loss-based vs delay-based vs model-based taxonomy: Reno/CUBIC (loss), Vegas (delay),
        BBR (model), DCTCP (ECN, datacentre). `[TABLE]`
1.12.12 **Bufferbloat**: oversized router buffers defeat loss-based congestion signalling, producing
        seconds of queueing delay. The fixes: AQM (`fq_codel`, `CAKE`), pacing, BBR, and
        `tcp_notsent_lowat`. `[PROVE]`
1.12.13 **`tcp_slow_start_after_idle`** (default **1**, RFC 2861): after an idle period longer than
        one RTO, the kernel resets `cwnd` to the initial window. This is why the *first* request on
        a pooled-but-idle keep-alive connection is slow, and why high-throughput servers set it to
        0. `[SYSCTL]` `[NUM]` `[TRAP]` `[INCIDENT]`
1.12.14 Selecting an algorithm: `net.ipv4.tcp_congestion_control`,
        `net.ipv4.tcp_available_congestion_control`, and per-socket `TCP_CONGESTION`. `[SYSCTL]`
        `[API]`
1.12.15 **Trap:** tuning congestion control before checking whether you are actually loss-limited.
        Read `ss -tin` for `retrans` and `cwnd` first; most "slow network" problems are a full
        thread pool, a cold cache or an N+1, not the congestion controller. `[TRAP]`

*(15 leaves)*

## §1.13 Nagle, delayed ACK, and the 40 ms mystery

1.13.1 **Nagle's algorithm** (RFC 9293 §3.7.4): do not send a new small segment while an
       unacknowledged small segment is outstanding — coalesce instead. Purpose: stop a telnet
       session from putting one byte in a 41-byte packet. `[SPEC]` `[PROVE]`
1.13.2 **Delayed ACK** (RFC 1122): the receiver waits up to **500 ms** (Linux: up to **40 ms**,
       `TCP_DELACK_MAX`) hoping to piggyback the ACK on outgoing data or coalesce two ACKs. `[NUM]`
1.13.3 **The interaction** — the classic 40 ms stall. The sender has a small unacked write and holds
       the next write (Nagle); the receiver holds the ACK (delayed ACK). Nothing moves until the
       delayed-ACK timer fires. Symptom: request latency quantised at ~40 ms multiples, only for
       small write-write-read patterns. `[PROVE]` `[INCIDENT]` `[CALC]`
1.13.4 The fix hierarchy: **write the whole message in one `write()`** (the real fix — gather your
       buffer before writing), then `TCP_NODELAY` (disable Nagle), then `TCP_QUICKACK` (a one-shot
       on the receiver, and it does **not** stay set).  `[SYSCTL]` `[TRAP]`
1.13.5 `TCP_NODELAY` in Java: `Socket.setTcpNoDelay(true)`, `StandardSocketOptions.TCP_NODELAY`,
       and the fact that **Netty enables it by default** while a raw `java.net.Socket` does not.
       `[API]` `[TRAP]`
1.13.6 `TCP_CORK` (Linux): the inverse of `TCP_NODELAY` — accumulate deliberately, with a **200 ms**
       ceiling. Used by nginx (`tcp_nopush`) to send headers and file body in full frames.
       `[SYSCTL]` `[NUM]`
1.13.7 **Trap:** "always set `TCP_NODELAY`" as a cargo-cult. It is right for request/response RPC;
       it is wrong for a stream where you would rather coalesce. The real defect is usually many
       small writes, not Nagle. `[TRAP]`

*(7 leaves)*

## §1.14 The sockets API and the connection lifecycle in syscalls

1.14.1 The server sequence: `socket()` → `setsockopt(SO_REUSEADDR)` → `bind()` → `listen(backlog)` →
       `accept()` → `read()`/`write()` → `close()`. `[FLOW]`
1.14.2 The client sequence: `socket()` → (optional `bind()`) → `connect()` → `write()`/`read()` →
       `close()`. `[FLOW]`
1.14.3 **`listen(backlog)` creates two queues**, not one: the **SYN queue** (half-open, `SYN_RECV`,
       sized by `net.ipv4.tcp_max_syn_backlog`) and the **accept queue** (fully established, waiting
       for `accept()`, sized by `min(backlog, net.core.somaxconn)`). `[PROVE]` `[SYSCTL]`
1.14.4 `net.core.somaxconn` — **default changed from 128 to 4096 in Linux 5.4**. Java's
       `ServerSocket` backlog default is **50**, and Tomcat's `acceptCount` default is **100**.
       `[NUM]` `[VERSION-TRAP]` `[RESEARCH]` `[API]`
1.14.5 What happens when the accept queue overflows: by default the SYN-ACK is dropped (client
       retries and eventually times out); with `net.ipv4.tcp_abort_on_overflow=1` an RST is sent
       instead (fail fast, but breaks bursty clients). `[SYSCTL]` `[TRAP]`
1.14.6 **The diagnosis:** on a *listening* socket in `ss -lnt`, `Recv-Q` is the current accept-queue
       depth and `Send-Q` is its configured maximum; `nstat -az TcpExtListenOverflows
       TcpExtListenDrops` counts the failures. `[DIAG]` `[TRAP]`
1.14.7 **The incident shape:** the application is slow to `accept()` (thread pool exhausted, stop-
       the-world GC, blocked on a downstream), the accept queue fills, clients see *connection
       timeouts*, and server CPU looks idle. Server-side health checks pass because they were
       already connected. `[INCIDENT]` `[X-REF 06]`
1.14.8 **SYN flood** and **SYN cookies**: `net.ipv4.tcp_syncookies` (default 1) encodes the
       connection state into the ISN so no SYN-queue entry is needed; the cost is losing negotiated
       options (window scale, SACK) for cookie-established connections. `[SYSCTL]` `[PROVE]`
1.14.9 `net.ipv4.tcp_syn_retries` (default **6**, ≈127 s of total connect time) and
       `tcp_synack_retries` (default **5**). This is why a `connect()` with no explicit timeout can
       hang for over two minutes. `[SYSCTL]` `[NUM]` `[CALC]` `[RESEARCH]`
1.14.10 `SO_REUSEADDR` vs `SO_REUSEPORT`: the first allows binding while old sockets sit in
        `TIME_WAIT`; the second (Linux 3.9+) allows **multiple processes to bind the same port** with
        kernel-side load balancing across them — the mechanism behind nginx's per-worker accept and
        zero-downtime restarts. `[SYSCTL]` `[PROVE]`
1.14.11 `SO_LINGER`: default off (close returns immediately, kernel drains in background);
        `linger=0` sends an **RST** and skips `TIME_WAIT` — occasionally a legitimate tool, usually a
        data-loss bug. `Socket.setSoLinger(boolean, int)`. `[API]` `[TRAP]`
1.14.12 `SO_KEEPALIVE` and its three knobs: `tcp_keepalive_time` (**7200 s** = 2 hours),
        `tcp_keepalive_intvl` (**75 s**), `tcp_keepalive_probes` (**9**) — so a dead peer is
        detected after 2 h 11 min by default. Per-socket: `TCP_KEEPIDLE`, `TCP_KEEPINTVL`,
        `TCP_KEEPCNT`; in Java, `StandardSocketOptions.SO_KEEPALIVE` plus the
        `jdk.net.ExtendedSocketOptions.TCP_KEEPIDLE/TCP_KEEPINTERVAL/TCP_KEEPCOUNT` added in JDK 11.
        `[SYSCTL]` `[NUM]` `[API]` `[RESEARCH]`
1.14.13 `TCP_USER_TIMEOUT` as the sharper tool: bound how long *unacknowledged data* may remain
        outstanding before the connection is aborted, independent of keepalive. `[SYSCTL]`
1.14.14 `SO_RCVTIMEO`/`SO_SNDTIMEO` vs Java's `Socket.setSoTimeout(int)` — the latter maps to a
        read timeout on blocking reads and throws `SocketTimeoutException` **without closing the
        socket**. `[API]` `[TRAP]`
1.14.15 `TCP_DEFER_ACCEPT`: wake the acceptor only when data arrives, not at handshake completion —
        saves a wakeup for request/response protocols.
1.14.16 `SO_INCOMING_CPU`, `SO_BUSY_POLL`, `SO_ZEROCOPY`, `SO_INCOMING_NAPI_ID` as the
        high-performance corner of the option surface. `[RESEARCH]`
1.14.17 Blocking semantics precisely: `read()` returns **0 on orderly EOF (peer sent FIN)**, `-1`
        with `errno` on error; Java's `InputStream.read()` returns **−1** at EOF and throws on
        error. A partial `write()` is normal on a non-blocking socket. `[API]` `[TRAP]`
1.14.18 `EPIPE`/`SIGPIPE` and Java's `IOException: Broken pipe` — writing to a socket the peer has
        reset. Distinguish it from `Connection reset by peer` (an RST arrived while reading).
        `[DIAG]` `[TRAP]`

*(18 leaves)*

## §1.15 Ports, the 4-tuple, and ephemeral port allocation

1.15.1 A connection is identified by the **4-tuple** (source IP, source port, destination IP,
       destination port) — plus the protocol. Not by the port alone. `[PROVE]`
1.15.2 The consequence: **one server port can hold millions of connections**, because each is
       distinguished by the client's IP:port. Scarcity lives on the *client* side. `[PROVE]`
1.15.3 The port ranges: well-known 0–1023 (binding requires `CAP_NET_BIND_SERVICE` or root),
       registered 1024–49151, dynamic/ephemeral 49152–65535 by IANA — but Linux defaults to
       `net.ipv4.ip_local_port_range = 32768 60999`, giving **28,232 ports**. `[SYSCTL]` `[NUM]`
       `[CALC]`
1.15.4 `bind()` before `connect()` (source-port pinning) and why it destroys the 4-tuple advantage.
1.15.5 `IP_BIND_ADDRESS_NO_PORT` — the kernel defers source-port selection until `connect()`, so the
       port can be chosen with knowledge of the destination, hugely increasing the usable space when
       a source address is bound. `[SYSCTL]` `[RESEARCH]`
1.15.6 `net.ipv4.ip_local_reserved_ports` for carving out ports your applications must not grab.
1.15.7 The ports a backend engineer should know cold: 22 SSH, 25/587 SMTP, 53 DNS, 80 HTTP, 443
       HTTPS/QUIC, 853 DoT, 3306 MySQL, 5432 PostgreSQL, 6379 Redis, 8080/8443 app servers, 9092
       Kafka, 9090 Prometheus, 5672 AMQP, 27017 MongoDB, 2379 etcd. `[TABLE]` `[NUM]`
1.15.8 `ss -tanp`, `lsof -i :8443`, `netstat -tulpn` — which process owns which port. `[DIAG]`
       `[X-REF 11]`

*(8 leaves)*

## §1.16 DNS: the model and the resolution chain

1.16.1 What DNS is: a **distributed, hierarchical, cached key-value store** with eventual
       consistency and no global invalidation. Every DNS problem follows from that last clause.
       `[PROVE]`
1.16.2 The namespace hierarchy: root (`.`) → TLD (`.com`) → zone (`example.com`) → labels; FQDNs and
       the trailing dot; the 253-character name limit and 63-character label limit. `[NUM]`
1.16.3 **Delegation** via NS records, and what "authoritative" means.
1.16.4 The actors: **stub resolver** (your OS/library), **recursive resolver** (ISP, 8.8.8.8,
       `169.254.169.253` in a VPC), **root servers** (13 named, anycast), **TLD servers**,
       **authoritative servers**. `[TABLE]`
1.16.5 **Iterative vs recursive** resolution: the stub asks recursively; the recursive resolver
       queries iteratively down the hierarchy. `[FLOW]`
1.16.6 The full chain for `applicationgateway.quizstakes.com`, cache by cache, in order: application
       cache → **JVM `InetAddress` cache** → OS resolver cache (`nscd`/`systemd-resolved`,
       `dscacheutil` on macOS) → `/etc/hosts` (which short-circuits everything before all of these)
       → recursive resolver cache → root → TLD → authoritative. `[FLOW]` `[TRAP]`
1.16.7 The DNS message format: header (ID, QR, Opcode, AA, TC, RD, RA, RCODE, counts), question,
       answer, authority, additional sections. `[WIRE]` `[SPEC]`
1.16.8 **RCODEs**: 0 NOERROR, 1 FORMERR, 2 SERVFAIL, 3 **NXDOMAIN**, 5 REFUSED. The difference
       between NXDOMAIN (name does not exist) and NODATA (name exists, no record of that type) —
       and why the latter is signalled as NOERROR with an empty answer. `[NUM]` `[TRAP]`
1.16.9 **TTL semantics (RFC 2181)**: the authoritative server sets it; resolvers *may* honour it;
       nothing can revoke a cached answer early. A TTL is a promise you cannot take back.
       `[PROVE]` `[TRAP]`
1.16.10 **Negative caching (RFC 2308)**: NXDOMAIN is cached for `min(SOA MINIMUM, SOA TTL)`.
        Creating a record does not make it instantly visible to a resolver that just cached the
        NXDOMAIN. `[SPEC]` `[TRAP]`
1.16.11 `/etc/resolv.conf`: `nameserver`, `search`, `options ndots:N`, `timeout`, `attempts`,
        `rotate`, `single-request-reopen`. `[DIAG]`
1.16.12 **The `ndots:5` incident** — Kubernetes injects `ndots:5`, so any name with fewer than five
        dots is first tried against every search-domain suffix. `api.stripe.com` (2 dots) triggers
        4–5 failing lookups before the correct one, and doubles again for A + AAAA. Fix: a trailing
        dot on the FQDN, or an explicit `dnsConfig` with a lower `ndots`. `[INCIDENT]` `[TRAP]`
        `[X-REF 19]` `[RESEARCH]`

*(12 leaves)*

## §1.17 DNS record types and zone operations

1.17.1 The record table with mapping and notes: **A** (name→IPv4), **AAAA** (name→IPv6), **CNAME**
       (name→name), **MX** (mail, priority-ordered), **TXT** (SPF/DKIM/DMARC, ownership proofs),
       **NS** (delegation), **SOA** (zone parameters: serial, refresh, retry, expire, minimum),
       **PTR** (reverse), **SRV** (`_service._proto.name` → priority, weight, port, target),
       **CAA** (which CAs may issue), **DS/DNSKEY/RRSIG/NSEC/NSEC3** (DNSSEC), **SVCB (64)** and
       **HTTPS (65)**. `[TABLE]` `[NUM]`
1.17.2 **CNAME restrictions**: cannot coexist with any other record at the same name, and **cannot
       exist at the zone apex** because the apex must carry SOA and NS. `[PROVE]` `[TRAP]`
1.17.3 The apex workarounds: provider **ALIAS/ANAME** pseudo-records (Route 53 "Alias" — resolved at
       query time, free of charge, health-check aware), and the standards-track answer, the
       **HTTPS RR in AliasMode (RFC 9460 §2.4.2)**. `[RESEARCH]` `[X-REF 18]`
1.17.4 **SVCB/HTTPS RR (RFC 9460)** in full: SvcPriority 0 = AliasMode, >0 = ServiceMode;
       SvcParamKeys `alpn`, `no-default-alpn`, `port`, `ipv4hint`, `ipv6hint`, `mandatory`, `ech`.
       It lets a client learn "this origin speaks h3 at these addresses" **before the first
       connection**, replacing the Alt-Svc round trip. `[SPEC]` `[RESEARCH]`
1.17.5 **CNAME chains** and their latency cost; the `CNAME` → `CNAME` → `A` chains that CDNs
       produce and the extra resolution hops they add.
1.17.6 **TTL as an operational lock-in**: lower the TTL to 60 s at least one old-TTL-period *before*
       a planned migration, cut over, then raise it. You cannot retroactively shorten a cached
       answer. `[PROVE]` `[TRAP]`
1.17.7 **Round-robin DNS is not load balancing**: no health awareness, no weighting, and clients
       frequently pin to the first answer. `[TRAP]`
1.17.8 **Why DNS is a poor failover mechanism**: detection time + TTL + client caches that ignore
       TTL + connection pools that resolved once at startup. Real failover is an LB, anycast, or
       client-side discovery; DNS handles coarse region-level routing only. `[PROVE]`
1.17.9 Routing policies as a concept (weighted, latency-based, geolocation, failover,
       multi-value) and the health-check dependency each has. `[X-REF 18]`
1.17.10 **Split-horizon DNS**: different answers for internal and external resolvers, and the class
        of bug where a service resolves a public IP from inside the VPC and traverses the NAT
        gateway to reach itself. `[INCIDENT]`
1.17.11 Zone transfers (AXFR/IXFR), the SOA serial, and why an unrestricted AXFR is an information
        leak. `[X-REF 13]`
1.17.12 DNS as a service-discovery mechanism: Kubernetes `ClusterIP` service names, headless
        services returning pod A records, and `SRV` records for port discovery. `[X-REF 19]`

*(12 leaves)*

## §1.18 DNS transport, EDNS, and encrypted DNS

1.18.1 The classic transport: **UDP port 53, 512-byte payload limit** (RFC 1035), with the **TC
       (truncated) bit** forcing a retry over **TCP port 53**. `[NUM]` `[SPEC]`
1.18.2 **EDNS(0) (RFC 6891)**: the **OPT pseudo-RR (type 41)** in the additional section carries the
       requestor's UDP payload size (recommended start **4096**, fall back to 1280–1410, then 512),
       an extended 12-bit RCODE, and the **DO bit** for DNSSEC. `[SPEC]` `[NUM]` `[RESEARCH]`
1.18.3 The fragmentation hazard of large EDNS buffers, and why 1232 has become a common
       recommendation. `[RESEARCH]`
1.18.4 **DNS over TCP (RFC 7766)** is mandatory to support, not a fallback of last resort; the
       2-byte length prefix framing.
1.18.5 **DoT (RFC 7858)**: DNS over TLS on **port 853**, a dedicated port that is easy to block or
       to permit by policy.
1.18.6 **DoH (RFC 8484)**: DNS over HTTPS on 443, media type **`application/dns-message`**, GET with
       `?dns=` base64url or POST with the wire-format body, the `/dns-query` URI template, and the
       requirement that HTTP `Cache-Control` freshness not exceed the smallest DNS TTL. `[SPEC]`
       `[RESEARCH]`
1.18.7 **DoQ (RFC 9250)** — DNS over QUIC — in one paragraph.
1.18.8 The operational consequence of DoH: enterprise DNS-based filtering and observability stop
       working, and the resolver a browser uses may not be the one you configured. `[TRAP]`
1.18.9 **DNSSEC** in the amount needed: DNSKEY/RRSIG/DS/NSEC(3), the chain of trust from the root
       KSK, that it provides **authentication and integrity but not confidentiality**, and that a
       misconfigured DS record produces SERVFAIL for everyone — a full-outage failure mode.
       `[INCIDENT]` `[X-REF 13]`
1.18.10 `dig` as the instrument: `dig +trace`, `dig +short`, `dig @8.8.8.8`, `dig +dnssec`,
        `dig -t HTTPS`, `dig +tcp`, reading the `ANSWER SECTION` TTL countdown to see caching.
        `[DIAG]`

*(10 leaves)*

## §1.19 DNS in the JVM

1.19.1 `InetAddress.getByName` / `getAllByName` / `getLocalHost` and the fact that resolution is
       **synchronous and blocking with no timeout parameter**. `[API]` `[TRAP]`
1.19.2 The JDK's positive cache: `networkaddress.cache.ttl` in `$JAVA_HOME/conf/security/
       java.security`, overridable by the system property `sun.net.inetaddr.ttl`. `-1` means cache
       forever; with no Security Manager the effective default is **30 s**. `[API]` `[NUM]`
       `[VERSION-TRAP]` `[RESEARCH]`
1.19.3 The negative cache: `networkaddress.cache.negative.ttl` / `sun.net.inetaddr.negative.ttl`,
       **default 10 s**. `[NUM]` `[RESEARCH]`
1.19.4 `networkaddress.cache.stale.ttl` — serve a stale entry while a refresh is failing. `[API]`
       `[RESEARCH]`
1.19.5 **The production incident:** an RDS endpoint fails over or an ALB scales and changes IPs.
       DNS TTL is 60 s so everything *should* recover in a minute; the JVM keeps hammering the dead
       IP for hours because it cached the resolution above the OS. Fix: set an explicit
       `-Dsun.net.inetaddr.ttl=30` (or `networkaddress.cache.ttl=30`), keep negative TTL short, and
       for long-lived pools ensure connections are recycled so re-resolution happens.
       `[INCIDENT]` `[TRAP]` `[NUM]`
1.19.6 **JDK 18+ `InetAddressResolverProvider` (JEP 418)**: the SPI that finally lets you plug in a
       non-blocking or custom resolver, replacing the old internal `sun.net.spi.nameservice` hook.
       `[API]` `[VERSION-TRAP]` `[RESEARCH]`
1.19.7 Third-party resolvers and when they earn their place: `dnsjava`, Netty's
       `DnsNameResolver`/`DnsAddressResolverGroup` (asynchronous, per-query timeout, honours TTL).
1.19.8 `Inet4Address`/`Inet6Address`, `InetSocketAddress` (resolved vs `createUnresolved`), and the
       trap that `InetSocketAddress` resolves **eagerly in its constructor** — a hostname change is
       invisible to anything holding one. `[API]` `[TRAP]`
1.19.9 Reverse lookups triggered accidentally by `InetAddress.getHostName()` and by logging
       frameworks — each one is a blocking PTR query on a request thread. `[TRAP]` `[X-REF 20]`
1.19.10 **Happy Eyeballs v2 (RFC 8305)** and the JDK: the algorithm (query A and AAAA in parallel,
        **Resolution Delay 50 ms**, **Connection Attempt Delay 250 ms** recommended with a 10 ms
        floor and 2 s ceiling, interleave address families, cancel losers). Note where the JDK and
        Netty do and do not implement it. `[NUM]` `[SPEC]` `[RESEARCH]`

*(10 leaves)*

## §1.20 URIs, URLs and the request target

1.20.1 The URI grammar (RFC 3986): `scheme://userinfo@host:port/path?query#fragment`, and which
       parts are sent to the server. **The fragment is never transmitted.** `[SPEC]` `[TRAP]`
1.20.2 Default ports by scheme and when the port appears in `Host`.
1.20.3 Percent-encoding, reserved vs unreserved characters, and the difference between encoding a
       path segment and encoding a query value (`+` means space only in
       `application/x-www-form-urlencoded`). `[TRAP]`
1.20.4 **Java's `URL.equals()` performs a DNS lookup** and blocks — one of the worst API decisions
       in the JDK. Use `URI` for comparison and as map keys. `[API]` `[TRAP]`
1.20.5 `URI` vs `URL` vs `URLEncoder` vs Spring's `UriComponentsBuilder`; the double-encoding bug
       that arises from encoding a URI that is already encoded. `[API]` `[TRAP]`
1.20.6 IDN and punycode (`xn--`), and homograph confusion as a security note. `[X-REF 13]`
1.20.7 Absolute-form vs origin-form request targets, and where `CONNECT` and `OPTIONS *` differ.
       `[SPEC]`

*(7 leaves)*

## §1.21 HTTP/1.0 and HTTP/1.1: syntax and framing

1.21.1 HTTP as a **request/response, stateless, text-based** protocol; why statelessness is what
       makes horizontal scaling possible and cookies/tokens necessary. `[X-REF 13]`
1.21.2 Message syntax (RFC 9112): request line `METHOD SP target SP HTTP/1.1 CRLF`, field lines,
       empty line, body. `[WIRE]` `[SPEC]`
1.21.3 **HTTP/1.0's fatal property**: one request per TCP connection, connection closed after the
       response — a full handshake per image. `[PROVE]`
1.21.4 **HTTP/1.1's headline change: persistent connections (keep-alive) by default**, plus the
       `Connection: close` opt-out and the legacy `Connection: keep-alive` header from the 1.0 era.
       `[HDR]`
1.21.5 **`Host` is mandatory in HTTP/1.1** — it is how one IP address serves many sites (name-based
       virtual hosting), and its absence is a `400`. `[HDR]` `[PROVE]`
1.21.6 **The two framing mechanisms**: `Content-Length` (exact octet count) and
       `Transfer-Encoding: chunked` (hex size line, CRLF, chunk, CRLF, terminated by a `0` chunk and
       optional trailers). `[WIRE]` `[SPEC]`
1.21.7 **Request smuggling** as the consequence of ambiguous framing: CL.TE, TE.CL, TE.TE when a
       front-end and back-end disagree about which header wins. One paragraph of mechanism here,
       full treatment in `13-web-security.md`. `[X-REF 13]` `[TRAP]`
1.21.8 **Pipelining**: send request 2 before response 1 arrives. Specified, implemented badly,
       effectively dead — because responses must return **in order**, so one slow response blocks
       the rest. This is **HTTP-layer head-of-line blocking**. `[PROVE]` `[TRAP]`
1.21.9 The browser workaround: **~6 parallel connections per origin**, and "domain sharding" to get
       more. Every one of these is a workaround for HOL blocking, and every one costs a handshake.
       `[NUM]`
1.21.10 The header-size cost: headers are re-sent verbatim on every request, uncompressed. Cookies
        alone are routinely kilobytes; a 2 KB header set on 100 requests is 200 KB of pure
        repetition. `[CALC]`
1.21.11 `100 Continue` and the `Expect: 100-continue` handshake — send headers, wait for permission,
        then send a large body. Where it helps and where it adds an RTT for nothing. `[HDR]`
1.21.12 `Connection`, `Keep-Alive`, `Upgrade`, `Transfer-Encoding`, `TE`, `Trailer` as **hop-by-hop**
        headers that must not be forwarded by a proxy; everything else is end-to-end. `[HDR]`
        `[SPEC]`
1.21.13 Header field syntax rules: case-insensitive names, folding is obsolete, comma-separated list
        values, the practical 8 KB per-header-line limit in nginx (`large_client_header_buffers`)
        and Tomcat (`maxHttpHeaderSize`, default 8192), and the JDK's
        `jdk.http.maxHeaderSize` default **393216**. `[NUM]` `[RESEARCH]`
1.21.14 `431 Request Header Fields Too Large` and `414 URI Too Long` as the errors this produces.

*(14 leaves)*

## §1.22 HTTP semantics: methods, status codes, and the header surface

1.22.1 The eight methods with their **safe / idempotent / cacheable** properties: GET (S,I,C),
       HEAD (S,I,C), POST (—,—,C only with explicit directives), PUT (—,I,—), DELETE (—,I,—),
       CONNECT (—,—,—), OPTIONS (S,I,—), TRACE (S,I,—). `[TABLE]` `[SPEC]`
1.22.2 What "safe" and "idempotent" mean **precisely**, and why they are the properties that decide
       whether a client may retry automatically. RFC 9110 §9.2.1–9.2.2. `[PROVE]` `[SPEC]`
1.22.3 The status-code classes and the individual codes defined by RFC 9110, enumerated: 1xx (100,
       101), 2xx (200–206), 3xx (300–308), 4xx (400–417, 421, 422, 426), 5xx (500–505); plus the
       common extensions 103 Early Hints, 425 Too Early, 428, 429, 431, 451, 511. `[TABLE]` `[NUM]`
       `[X-REF 12]`
1.22.4 The four codes an engineer must be able to disambiguate under pressure: **502** (bad gateway
       — the upstream returned garbage or refused), **503** (service unavailable — the LB has no
       healthy target, or the app is shedding), **504** (gateway timeout — the upstream did not
       answer in time), **499** (nginx-only: client closed the connection first). `[TABLE]`
       `[DIAG]` `[TRAP]`
1.22.5 The header field categories, enumerated: representation metadata (`Content-Type`,
       `Content-Encoding`, `Content-Language`, `Content-Length`, `Content-Location`,
       `Last-Modified`, `ETag`), content negotiation (`Accept`, `Accept-Encoding`,
       `Accept-Language`, `Vary`), conditional (`If-Match`, `If-None-Match`, `If-Modified-Since`,
       `If-Unmodified-Since`, `If-Range`), range (`Range`, `Accept-Ranges`, `Content-Range`),
       authentication (`WWW-Authenticate`, `Authorization`, `Proxy-Authenticate`,
       `Proxy-Authorization`, `Authentication-Info`), request context (`Expect`, `From`, `Referer`,
       `TE`, `User-Agent`), response context (`Allow`, `Location`, `Retry-After`, `Server`), and
       control/routing (`Host`, `Connection`, `Max-Forwards`, `Via`, `Date`, `Trailer`, `Upgrade`).
       `[TABLE]` `[HDR]` `[SPEC]` `[RESEARCH]`
1.22.6 Range requests and `206 Partial Content` — resumable downloads, video seeking, and the
       `Range` header's role in CDN behaviour.
1.22.7 `Retry-After` as the server's explicit backoff instruction (seconds or an HTTP-date), and why
       a client that ignores it turns a partial outage into a full one. `[HDR]` `[X-REF 12]`
1.22.8 Content negotiation mechanics: `Accept` with q-values, `Accept-Encoding` (gzip, br, zstd),
       and how `Vary` makes negotiation cacheable. `[HDR]`
1.22.9 Compression on the wire: gzip vs Brotli vs Zstandard — ratio, CPU cost, and the rule that you
       compress text and never compress already-compressed bytes. Plus the note that compression
       over TLS with attacker-influenced content is a security concern (BREACH). `[X-REF 13]`
1.22.10 `Via` and `Max-Forwards`; `Server` and information disclosure.
1.22.11 Trailers and where they are actually used (gRPC's `grpc-status` is the canonical example).
        `[SPEC]`

*(11 leaves)*

## §1.23 HTTP caching, at the protocol level

1.23.1 The two cache mechanisms: **expiration** (do not ask again until it is stale) and
       **validation** (ask, but cheaply). `[PROVE]`
1.23.2 Every `Cache-Control` **response** directive by name and section: `max-age` (§5.2.2.1),
       `s-maxage` (§5.2.2.10), `no-cache` (§5.2.2.4), `no-store` (§5.2.2.5), `private` (§5.2.2.7),
       `public` (§5.2.2.9), `must-revalidate` (§5.2.2.2), `proxy-revalidate` (§5.2.2.8),
       `no-transform` (§5.2.2.6), `must-understand` (§5.2.2.3), `immutable`, and the RFC 5861
       extensions `stale-while-revalidate` and `stale-if-error`. `[TABLE]` `[SPEC]` `[RESEARCH]`
1.23.3 Every `Cache-Control` **request** directive: `max-age`, `max-stale`, `min-fresh`, `no-cache`,
       `no-store`, `no-transform`, `only-if-cached`. `[TABLE]` `[SPEC]`
1.23.4 **`no-cache` does not mean "do not cache"** — it means "cache, but revalidate before every
       reuse". `no-store` is the directive that means do not store. This is the single most common
       HTTP caching misconception. `[TRAP]` `[PROVE]`
1.23.5 The **freshness lifetime** precedence: `s-maxage` (shared caches) → `max-age` → `Expires` −
       `Date` → heuristic. `[SPEC]`
1.23.6 The **age calculation**, worked: `apparent_age = max(0, response_time − date_value)`;
       `corrected_age_value = age_value + response_delay`;
       `corrected_initial_age = max(apparent_age, corrected_age_value)`;
       `current_age = corrected_initial_age + resident_time`;
       `response_is_fresh = freshness_lifetime > current_age`. `[CALC]` `[PROVE]` `[SPEC]`
       `[RESEARCH]`
1.23.7 **Heuristic freshness** and the ~10% of the `Last-Modified` interval convention — and why an
       unmarked response can be cached for longer than you intended. `[TRAP]`
1.23.8 **Validators**: strong `ETag` vs weak `W/"..."`, `Last-Modified` as a weak validator with
       one-second granularity, and why an `ETag` should be cheap to compute. `[SPEC]`
1.23.9 Conditional requests and `304 Not Modified`: `If-None-Match` (preferred),
       `If-Modified-Since`, and the fact that a 304 carries no body but must carry the headers that
       would update the stored response. `[FLOW]`
1.23.10 **`Vary`** as part of the cache key, and `Vary: *` meaning "never reusable". The failure
        mode: `Vary: Cookie` on a CDN drives hit rate to zero; a missing `Vary: Accept-Encoding`
        serves gzip bytes to a client that did not ask for them. `[TRAP]` `[INCIDENT]`
1.23.11 The `Age` header and what a nonzero `Age` on a response tells you about which cache answered.
        `[DIAG]`
1.23.12 Cache invalidation triggered by unsafe methods on the same URI (RFC 9111 §4.4).
1.23.13 The practical policy set: `Cache-Control: public, max-age=31536000, immutable` for
       fingerprinted static assets; `no-store` for anything with `Authorization`;
       `private, max-age=0, must-revalidate` for authenticated HTML;
       `s-maxage` + `stale-while-revalidate` for CDN-cacheable API responses. `[TABLE]`
1.23.14 Where HTTP caching interacts with application caching (Caffeine, Redis) and why they are
        different layers with different invalidation stories. `[X-REF 15]`

*(14 leaves)*

## §1.24 TLS as a transport cost and a handshake

1.24.1 The three goals in dependency order: **confidentiality**, **integrity**, **authentication** —
       and the argument that encryption without authentication is worthless because you would have a
       perfectly private conversation with the attacker. `[PROVE]` `[X-REF 13]`
1.24.2 The asymmetric/symmetric split: asymmetric operations (RSA/ECDSA/ECDHE) only during the
       handshake, because they are orders of magnitude slower; symmetric AEAD (AES-GCM,
       ChaCha20-Poly1305) for all bulk data. `[PROVE]`
1.24.3 **The TLS 1.2 handshake, message by message**: ClientHello → ServerHello, Certificate,
       ServerKeyExchange, ServerHelloDone → ClientKeyExchange, ChangeCipherSpec, Finished →
       ChangeCipherSpec, Finished. **2 RTT** before application data. `[FLOW]` `[CALC]`
1.24.4 **The TLS 1.3 handshake (RFC 8446)**: ClientHello (with `key_share` guessed) → ServerHello,
       {EncryptedExtensions, CertificateRequest?, Certificate, CertificateVerify, Finished} →
       {Finished} + application data. **1 RTT**, and everything after ServerHello is encrypted.
       `[FLOW]` `[SPEC]` `[CALC]`
1.24.5 **HelloRetryRequest**: what happens when the client guessed the wrong group — the handshake
       costs 2 RTT after all. `[SPEC]`
1.24.6 The TLS 1.3 message list to be able to name: ClientHello, ServerHello, HelloRetryRequest,
       EncryptedExtensions, CertificateRequest, Certificate, CertificateVerify, Finished,
       NewSessionTicket, KeyUpdate. `[SPEC]` `[RESEARCH]`
1.24.7 The five TLS 1.3 cipher suites: `TLS_AES_128_GCM_SHA256`, `TLS_AES_256_GCM_SHA384`,
       `TLS_CHACHA20_POLY1305_SHA256`, `TLS_AES_128_CCM_SHA256`, `TLS_AES_128_CCM_8_SHA256` — and
       that the suite no longer encodes the key exchange or authentication algorithm. `[NUM]`
       `[SPEC]` `[RESEARCH]`
1.24.8 **What TLS 1.3 removed and why it matters operationally**: renegotiation, compression, static
       RSA key transport, custom DHE groups, and the CBC/RC4 suites. Consequence: "renegotiate to
       ask for a client certificate" is impossible — TLS 1.3 uses **post-handshake
       authentication** instead. `[VERSION-TRAP]` `[RESEARCH]`
1.24.9 **Forward secrecy** from ephemeral (EC)DHE: the session secret is never derivable from the
       long-term key, so a future private-key compromise does not decrypt captured past traffic.
       `[PROVE]`
1.24.10 **Session resumption**: TLS 1.3 PSK via `NewSessionTicket`, session tickets vs the old
        session-ID cache, and why ticket keys must be rotated (a stolen ticket key breaks forward
        secrecy for tickets it covers). `[X-REF 13]`
1.24.11 **0-RTT early data**: saves a full RTT on reconnect but is **not replay-safe** — it must
        never carry a non-idempotent request. In QuizStakes terms: never a `ReserveStake`.
        `[TRAP]` `[SPEC]`
1.24.12 **SNI**: the hostname in the *plaintext* ClientHello, solving the chicken-and-egg of "which
        certificate should I send before I can read the encrypted `Host` header". Consequence: the
        hostname is visible on the wire even over HTTPS. **ECH (Encrypted Client Hello)** is the
        in-progress fix, advertised via the `ech` SvcParam in an HTTPS RR. `[PROVE]` `[RESEARCH]`
1.24.13 **ALPN (RFC 7301)**: protocol negotiation inside the handshake — `http/1.1`, `h2`, `h3`,
        `grpc-exp` — costing zero extra round trips. This is how HTTP/2 is selected. `[SPEC]`
1.24.14 **Certificate chain validation**: leaf → intermediates → a root in the trust store;
        signature chain, validity dates, hostname match against **SAN** (CN is deprecated and
        ignored by modern clients), key usage/EKU, and revocation. `[FLOW]`
1.24.15 **Java's trust store** is `$JAVA_HOME/lib/security/cacerts`; overridden by
        `-Djavax.net.ssl.trustStore` / `trustStorePassword` / `trustStoreType`. Corporate/internal
        CAs must be imported. `[API]` `[TRAP]`
1.24.16 **`PKIX path building failed: unable to find valid certification path to requested target`**
        — the single most common Java TLS error. It means *I do not trust the signer*, not "the
        certificate is broken". The three real causes: internal CA not in the trust store, a missing
        intermediate on the server, or a TLS-intercepting proxy. `[DIAG]` `[TRAP]` `[INCIDENT]`
1.24.17 **The missing-intermediate misconfiguration**: browsers paper over it via cached
        intermediates and AIA fetching, so it works in Chrome and fails in `curl` and Java. Test
        with `openssl s_client -connect host:443 -showcerts`. `[TRAP]` `[DIAG]`
1.24.18 **Revocation**: CRL (large, stale), OCSP (a live round trip to the CA, a latency and
        availability dependency), **OCSP stapling** (`status_request`, the server presents a signed
        recent response — the only deployable option), and OCSP must-staple. Note the industry move
        toward short-lived certificates instead. `[RESEARCH]`
1.24.19 **mTLS**: the client also presents a certificate; `CertificateRequest` in the handshake; the
        service-mesh identity model. One paragraph of mechanism, full treatment in 13.
        `[X-REF 13]`
1.24.20 **The TLS record layer**: max plaintext record **16,384 bytes (2^14)**, expansion by
        AEAD tag and header, and why record size affects time-to-first-byte (a 16 KB record cannot
        be decrypted until fully received — hence nginx's `ssl_buffer_size` tuning to 4 KB for
        latency). `[NUM]` `[CALC]` `[RESEARCH]`
1.24.21 The handshake's CPU cost: an ECDSA P-256 signature/verify per handshake, a few thousand
        handshakes/sec per core; and why session resumption and keep-alive are capacity decisions,
        not just latency ones. `[CALC]`
1.24.22 **Trap:** "we use HTTPS internally so we are secure." TLS protects the segment between two
        endpoints. If `ApplicationGateway` terminates TLS and speaks plaintext HTTP to
        `PaymentService`, that leg is unencrypted. Know where termination happens (§2.14) and
        whether re-encryption is on. `[TRAP]`
1.24.23 The JSSE surface: `SSLContext`, `SSLSocketFactory`, `SSLParameters` (setting ALPN,
        `setEndpointIdentificationAlgorithm("HTTPS")` — **which is off by default on raw
        `SSLSocket` and means no hostname verification**), `X509TrustManager`,
        `jdk.tls.disabledAlgorithms`, `-Djavax.net.debug=ssl,handshake`. `[API]` `[TRAP]`
        `[DIAG]`

*(23 leaves)*

## §1.25 The Java networking API surface

1.25.1 The three generations: blocking `java.net` (JDK 1.0), non-blocking `java.nio.channels`
       (JDK 1.4), asynchronous `java.nio.channels.Async*` (JDK 7) — and where each is still correct.
       `[TABLE]`
1.25.2 `Socket`, `ServerSocket`, `SocketAddress`/`InetSocketAddress`, `SocketOption`,
       `StandardSocketOptions`, and the JDK 11 `jdk.net.ExtendedSocketOptions`. `[API]`
1.25.3 `Socket.connect(SocketAddress, int timeout)` vs the **no-arg connect with no timeout** —
       and the fact that a plain `new Socket(host, port)` has **no connect timeout** and will wait
       out `tcp_syn_retries` (~127 s). `[API]` `[TRAP]` `[NUM]`
1.25.4 `setSoTimeout`, `setTcpNoDelay`, `setKeepAlive`, `setSoLinger`, `setReuseAddress`,
       `setReceiveBufferSize`/`setSendBufferSize`, `shutdownInput`/`shutdownOutput`. `[API]`
1.25.5 `SocketChannel`, `ServerSocketChannel`, `Selector`, `SelectionKey` (OP_ACCEPT, OP_CONNECT,
       OP_READ, OP_WRITE) and the `select`/`selectNow`/`wakeup` surface. `[API]`
1.25.6 `ByteBuffer`: heap vs **direct** buffers, `flip`/`clear`/`compact`, and why direct buffers
       avoid a copy for I/O but are expensive to allocate and are freed only by GC (hence
       `-XX:MaxDirectMemorySize` and `jdk.nio.maxCachedBufferSize`). `[API]` `[X-REF 06]`
1.25.7 `FileChannel.transferTo` / `transferFrom` as the zero-copy path (`sendfile`). `[API]`
1.25.8 `AsynchronousSocketChannel` and why it is largely unused in practice.
1.25.9 `java.net.http.HttpClient` (JDK 11+): `newBuilder()`, `connectTimeout`, `version`,
       `followRedirects`, `executor`, `sslContext`, `proxy`, `authenticator`, `cookieHandler`;
       `HttpRequest.timeout` as the **total** request timeout; `BodyHandlers`/`BodyPublishers`;
       `send` vs `sendAsync`. `[API]`
1.25.10 `HttpClient`'s **implicit connection pool** and its tuning properties:
        `jdk.httpclient.keepalive.timeout` (**30 s**), `jdk.httpclient.keepalive.timeout.h2`,
        `jdk.httpclient.connectionPoolSize` (**0 = unbounded**), `jdk.httpclient.maxstreams`
        (**100**), `jdk.httpclient.windowsize` (**16 MB**), `jdk.httpclient.connectionWindowSize`
        (**2^26**), `jdk.httpclient.bufsize` (**16384**), `jdk.httpclient.redirects.retrylimit`
        (**5**), `jdk.httpclient.auth.retrylimit` (**3**), `jdk.httpclient.disableRetryConnect`
        (**false**), `jdk.httpclient.enableAllMethodRetry` (**false**),
        `jdk.httpclient.allowRestrictedHeaders`, `jdk.httpclient.HttpClient.log`. `[API]` `[NUM]`
        `[RESEARCH]`
1.25.11 **`HttpClient` has no read/idle timeout, only a total request timeout** — a distinct
        behaviour from Apache HttpClient and OkHttp, and a surprise when migrating. `[TRAP]`
1.25.12 `HttpURLConnection` and `URLConnection`: `setConnectTimeout`/`setReadTimeout` both default
        to **0 = infinite**, `http.keepAlive` (**true**), `http.maxConnections` (**5**),
        `http.agent`, `http.maxRedirects` (**20**). Legacy, but still reached by libraries.
        `[API]` `[NUM]` `[TRAP]` `[RESEARCH]`
1.25.13 Proxy properties: `http.proxyHost`/`Port` (**80**), `https.proxyHost`/`Port` (**443**),
        `http.nonProxyHosts` (default `localhost|127.*|[::1]`), `socksProxyHost`/`Port` (**1080**),
        `socksProxyVersion` (**5**), `java.net.useSystemProxies` (**false**),
        `ProxySelector`. `[API]` `[NUM]` `[RESEARCH]`
1.25.14 `jdk.https.negotiate.cbt` (default `never`) and
        `jdk.http.auth.tunneling.disabledSchemes` — the properties that bite behind corporate
        proxies. `[API]` `[RESEARCH]`
1.25.15 Unix domain sockets in `SocketChannel` (JDK 16+, `StandardProtocolFamily.UNIX`) and
        `jdk.net.unixdomain.tmpdir`. `[API]` `[VERSION-TRAP]`
1.25.16 Spring's client surface: `RestClient` (Boot 3.2+, the current synchronous choice),
        `WebClient` (reactive), `RestTemplate` (maintenance mode), `@HttpExchange` interface
        clients, `ClientHttpRequestFactory` implementations (`JdkClientHttpRequestFactory`,
        `HttpComponentsClientHttpRequestFactory`, `ReactorClientHttpRequestFactory`,
        `SimpleClientHttpRequestFactory`), and `spring.http.client.*` /
        `ClientHttpRequestFactorySettings` for connect and read timeouts. `[API]` `[RESEARCH]`
        `[VERSION-TRAP]`

*(16 leaves)*

## §1.26 Proxies, gateways and the request path through them

1.26.1 **Forward proxy** (acts for the client, configured by the client, sees the destination) vs
       **reverse proxy** (acts for the server, invisible to the client). `[TABLE]` `[PROVE]`
1.26.2 The `CONNECT` method: how a forward proxy tunnels TLS — the proxy blindly relays bytes after
       `200 Connection Established`, seeing only the hostname and port. `[FLOW]` `[SPEC]`
1.26.3 TLS-intercepting (MITM) corporate proxies: they re-sign with a private CA, which is why a
       JVM on a corporate laptop needs that CA in `cacerts` (§1.24.16). `[INCIDENT]`
1.26.4 `Proxy-Authorization`, `Proxy-Authenticate`, `407 Proxy Authentication Required`.
1.26.5 The reverse-proxy job list: TLS termination, routing, buffering, compression, caching, rate
       limiting, header injection, connection multiplexing to backends, and request/response body
       limits.
1.26.6 **Buffering** and why it matters: nginx `proxy_buffering on` protects a slow-write backend
       from a slow client (Slowloris), but breaks SSE and streaming responses unless disabled
       (`X-Accel-Buffering: no`). `[TRAP]` `[INCIDENT]`
1.26.7 nginx's key timeouts, by name and default: `keepalive_timeout` **75 s**,
       `proxy_connect_timeout` **60 s**, `proxy_send_timeout` **60 s**, `proxy_read_timeout`
       **60 s**, `client_body_timeout` **60 s**, `send_timeout` **60 s**,
       `upstream keepalive` (off by default — a very common miss). `[NUM]` `[TRAP]` `[RESEARCH]`
1.26.8 Tomcat's connector surface: `maxThreads` (**200**), `acceptCount` (**100**),
       `maxConnections` (**8192** for NIO), `connectionTimeout` (**20000 ms**),
       `keepAliveTimeout` (defaults to `connectionTimeout`), `maxKeepAliveRequests` (**100**),
       `maxHttpHeaderSize` (**8192**). `[NUM]` `[API]` `[RESEARCH]`
1.26.9 **API gateway** vs reverse proxy vs service mesh sidecar — three names for "something in the
       path" with different ownership and different failure blast radius. In QuizStakes,
       `ApplicationGateway` is the token-strip boundary and therefore a *semantic* gateway, not just
       a router. `[X-REF 22]`
1.26.10 `Via`, `Forwarded`, and hop counting; how to tell from response headers how many proxies
        answered. `[DIAG]`

*(10 leaves)*

## §1.27 Sockets as file descriptors

1.27.1 Everything the kernel gives a process is an **fd**: files, pipes, sockets, epoll instances,
       eventfds, timerfds. An fd is an index into the process's file-descriptor table.
       `[X-REF 11]`
1.27.2 The limits: per-process soft/hard `ulimit -n` (**containers frequently default to 1024**),
       system-wide `fs.file-max`, and `fs.nr_open` as the ceiling on the hard limit. `[SYSCTL]`
       `[NUM]`
1.27.3 The fd budget for a JVM service: one per accepted connection + one per outbound connection +
       one per open file + JARs held open by the classloader + one per epoll instance + pipes for
       `Selector.wakeup`. `[CALC]`
1.27.4 `java.net.SocketException: Too many open files` and `java.io.IOException: Too many open
       files` — the same root cause, surfacing at different call sites. `[DIAG]`
1.27.5 Triage: `lsof -p <pid> | wc -l`, `ls /proc/<pid>/fd | wc -l`, `cat /proc/<pid>/limits`,
       `ss -s`. `[DIAG]` `[X-REF 11]`
1.27.6 Raising it properly: `LimitNOFILE` in a systemd unit, `ulimit -n` in an entrypoint, the
       container runtime's default, and Kubernetes' inheritance of the node default. `[X-REF 19]`
1.27.7 The distinction that matters: an fd **leak** (count grows monotonically and never falls —
       your code) vs fd **pressure** (count is high but stable — you need a higher limit).
       `[TRAP]`

*(7 leaves)*

## §1.28 The complete "type a URL and press enter" walkthrough

1.28.1 Stage 0 — URL parsing: scheme, host, port, path, query, fragment; the fragment stays local.
       `[FLOW]`
1.28.2 Stage 1 — DNS resolution through the full cache chain of §1.16.6, with A and AAAA in
       parallel and Happy Eyeballs deciding which to use. `[FLOW]`
1.28.3 Stage 2 — ARP/routing: is the destination on-link or via the default gateway?
1.28.4 Stage 3 — TCP connect (or QUIC handshake, or reuse of a pooled connection, in which case
       stages 3 and 4 vanish entirely — the whole point of pooling). `[FLOW]`
1.28.5 Stage 4 — TLS handshake with SNI and ALPN; protocol selected here.
1.28.6 Stage 5 — the HTTP request: request line, `Host`, `Cookie`, `Authorization`,
       `Accept-Encoding`, `User-Agent`, body. `[WIRE]`
1.28.7 Stage 6 — the path through the infrastructure: CDN edge → WAF → load balancer → the app's
       accept queue → a thread or event-loop handler → filter chain → routing → controller →
       downstream calls → serialisation. `[FLOW]`
1.28.8 Stage 7 — the response: status line, `Cache-Control`, `ETag`, `Content-Encoding`, body;
       then browser parsing, subresource discovery, and the whole pipeline again per subresource
       (with connection reuse).
1.28.9 **The cache stack to name unprompted, in order**: browser HTTP cache → browser DNS cache →
       OS DNS cache → JVM DNS cache → recursive-resolver cache → CDN edge cache → reverse-proxy
       cache → application cache (Caffeine/Redis) → database buffer pool → OS page cache → disk.
       `[FLOW]` `[TABLE]`
1.28.10 **The failure mode to name at each stage**: DNS NXDOMAIN/SERVFAIL/stale cache → SYN dropped
        (timeout) or RST (refused) → TLS handshake failure (`PKIX`, hostname mismatch, protocol
        mismatch) → 4xx/5xx → slow backend → partial render. `[TABLE]` `[DIAG]`
1.28.11 The same walkthrough for a **backend-to-backend** call, which is what you actually do all
        day: `PaymentService` → card PSP, with pool acquisition, DNS TTL, mTLS, timeouts, retries,
        and circuit breaking replacing the browser stages. `[FLOW]`

*(11 leaves)*

## §1.29 The diagnostic toolkit

1.29.1 `ss` as the primary tool: `ss -tan`, `ss -lnt` (listening + queues), `ss -tin` (per-socket
       TCP internals: `rtt`, `cwnd`, `ssthresh`, `retrans`, `wscale`, `bytes_acked`), `ss -s`
       (summary with `timewait` count), `ss -tanp` (with process), `ss -tan state time-wait`.
       `[DIAG]`
1.29.2 `netstat -s` / `nstat -az` for the kernel's counters: `ListenOverflows`, `ListenDrops`,
       `TCPSynRetrans`, `TCPTimeouts`, `TCPAbortOnMemory`, `PruneCalled`, `TCPBacklogDrop`.
       `[DIAG]`
1.29.3 `tcpdump`: filter syntax (`host`, `port`, `tcp[tcpflags] & tcp-syn != 0`), `-nn`, `-i any`,
       `-c`, `-s0`, `-w capture.pcap`, and reading a capture in Wireshark (follow TCP stream,
       expert info, `tcp.analysis.retransmission`). `[DIAG]`
1.29.4 `curl` as the protocol microscope: `-v`, `-w '%{time_namelookup} %{time_connect}
       %{time_appconnect} %{time_starttransfer} %{time_total}\n'`, `--http1.1`/`--http2`/`--http3`,
       `--resolve`, `-k`, `--trace-time`. The `-w` timing breakdown is the fastest way to attribute
       latency to a stage. `[DIAG]` `[CALC]`
1.29.5 `dig` (§1.18.10), `nslookup`'s deficiencies, and `getent hosts` to test what the *OS
       resolver* does rather than what DNS does.
1.29.6 `openssl s_client -connect host:443 -servername host -showcerts -tls1_3`,
       `openssl x509 -noout -text -in cert.pem`, `openssl verify -CAfile`. `[DIAG]`
1.29.7 `mtr` / `traceroute` / `tracepath` and how to read asymmetric routing and ICMP-rate-limited
       hops without over-interpreting a single high-latency hop. `[TRAP]`
1.29.8 `ping` and its limits (§1.5.9); `nc -vz` / `tcping` for port reachability.
1.29.9 `ip` suite: `ip addr`, `ip route get`, `ip neigh`, `ip -s link` (drops and errors at the
       NIC), `ethtool -S` (per-queue drops). `[DIAG]`
1.29.10 `conntrack -S` / `nf_conntrack_count` vs `nf_conntrack_max` — the table that silently drops
        your packets in a container host or NAT gateway. `[SYSCTL]` `[DIAG]`
1.29.11 JVM-side: `-Djavax.net.debug=ssl,handshake`, `jdk.httpclient.HttpClient.log`,
        `-Djava.net.preferIPv4Stack`, JFR socket-read/socket-write events, `jcmd Thread.print` to
        find threads blocked in `socketRead0`. `[DIAG]` `[X-REF 06]`
1.29.12 `bpftrace`/`bcc` one-liners (`tcpconnect`, `tcpretrans`, `tcplife`, `tcpaccept`) as the
        low-overhead production option. `[RESEARCH]`
1.29.13 The **triage order** for "the call is slow or failing": is it DNS, connect, TLS, or
        response? `curl -w` answers this in one command, and it should be the first thing you run.
        `[FLOW]`

*(13 leaves)*

## §1.30 Latency budgets and the QuizStakes numbers

1.30.1 A latency budget is a **contract that shrinks with depth**: the edge budget is the sum of
       every hop plus the slack. `[PROVE]`
1.30.2 The QuizStakes budgets as the working example: stake reservation **150 ms p99**, restriction
       decision **30 ms p99**, self-exclusion **500 ms hard**, everything else degrades. `[NUM]`
1.30.3 The 30 ms restriction budget decomposed: pool acquisition + TCP (0 if pooled) + TLS (0 if
       pooled) + request serialisation + one network RTT (~1 ms in-AZ, ~1–2 ms cross-AZ) + server
       processing + response — which leaves very little, and explains why the connection must
       already exist. `[CALC]` `[PROVE]`
1.30.4 Why a cross-AZ hop is not free: ~0.5–1 ms each way, plus data-transfer charges; and why
       zone-aware routing is a latency *and* cost decision. `[X-REF 18]`
1.30.5 The identity-vendor timeout problem, stated with its real numbers: p50 900 ms, **p99 38 s**.
       A 5 s timeout fails ~4% of legitimate verifications; 40 s leaves the client watching a
       spinner. There is no correct timeout — the correct answer is to change the interaction to
       asynchronous. `[NUM]` `[PROVE]` `[TRAP]`
1.30.6 The PSP capture row: **a timeout is not a failure**. A capture that timed out may have
       succeeded at the PSP. This is the single most important operational statement about network
       timeouts and it drives idempotency-key design. `[TRAP]` `[X-REF 12]`
1.30.7 Budget arithmetic for the fan-out case: `ProfileService` assembling eight owners — latency is
       the slowest leg (if parallel) or the sum (if serial), and availability is the product.
       `[CALC]`
1.30.8 How to *spend* a budget: parallelise independent calls, collapse serial hops, cache the
       stable parts, and make the slow leg optional with a fallback rather than raising the budget.
1.30.9 Measuring against a budget: p50/p90/p99/p99.9 from client-side timers (which include queueing
       and DNS) rather than server-side timers (which do not). The gap between the two *is* the
       network and the queue. `[X-REF 20]` `[PROVE]`

*(9 leaves)*

**PART 1 total: 30 sections, 349 leaves.**

---

# PART 2 — INTERMEDIATE

PART 1 said what each layer is. PART 2 answers **which one, why, and what it costs** — the cost
models, the version comparisons, the pool/timeout/retry machinery, the topology decisions, and the
failure catalogue. Every section here should end with a decision rule, not a description.

## §2.1 The master cost tables

2.1.1 **The master latency table**: every operation in this guide with its typical cost, its
      amortised cost when a connection is reused, and its worst case. Rows: DNS lookup (cached 0 /
      uncached 20–120 ms / cold recursion 200 ms+), TCP connect (1 RTT), TLS 1.2 handshake (2 RTT),
      TLS 1.3 handshake (1 RTT), TLS 1.3 resumption (0–1 RTT), QUIC first flight (1 RTT), QUIC 0-RTT
      (0 RTT), pooled HTTP request (1 RTT), same-AZ RTT (~0.5 ms), cross-AZ (~1 ms), cross-region
      (~50–150 ms), intercontinental (~150–250 ms), CDN edge hit (~10 ms), CDN miss to origin
      (edge RTT + origin RTT). `[TABLE]` `[NUM]` `[CALC]`
2.1.2 **The master protocol comparison table**: HTTP/1.0, HTTP/1.1, HTTP/2, HTTP/3 across transport,
      framing, multiplexing, header compression, HOL blocking (HTTP layer and transport layer),
      handshake RTTs, priority mechanism, server push, connection migration, and CPU cost per byte.
      `[TABLE]`
2.1.3 **The master timeout table**: every timeout in a request path, what starts and stops its
      clock, its Java default, and a sane production value. `[TABLE]`
2.1.4 **The master failure-symptom table**: symptom → the two or three layers that can produce it →
      the one command that disambiguates. (`Connection refused`, `Connection timed out`,
      `Connection reset by peer`, `Broken pipe`, `NoHttpResponseException`, `SocketTimeoutException`,
      `EADDRNOTAVAIL`, `Too many open files`, `PKIX path building failed`,
      `UnknownHostException`, `502`, `503`, `504`.) `[TABLE]` `[DIAG]`
2.1.5 **The master per-connection memory table**: thread-per-connection (~1 MB stack + kernel
      structures), event loop (~a few KB), virtual thread (hundreds of bytes to a few KB, heap
      allocated), plus kernel socket buffers (`tcp_rmem`/`tcp_wmem` defaults) which apply to all
      three. `[TABLE]` `[CALC]`
2.1.6 **The master "what is on the wire" byte table** for one QuizStakes `ReserveStake` call:
      Ethernet + IP + TCP + TLS record overhead + HTTP/2 frame + HPACK-compressed headers + JSON
      body, summed, and contrasted with the same call over gRPC/protobuf. `[CALC]` `[WIRE]`

*(6 leaves)*

## §2.2 HTTP/2, in depth

2.2.1 Why it exists: HTTP/1.1's HOL blocking, the 6-connections-per-origin workaround, uncompressed
      repeated headers, and the fact that SPDY proved the fix before the RFC existed. `[PROVE]`
2.2.2 **Binary framing**: the 9-byte frame header — length (24 bits), type (8), flags (8), reserved
      (1) + stream identifier (31). `[WIRE]` `[NUM]` `[SPEC]`
2.2.3 **The complete frame-type list with codes**: DATA 0x00, HEADERS 0x01, PRIORITY 0x02,
      RST_STREAM 0x03, SETTINGS 0x04, PUSH_PROMISE 0x05, PING 0x06, GOAWAY 0x08, WINDOW_UPDATE 0x09,
      CONTINUATION 0x0A. `[TABLE]` `[NUM]` `[SPEC]` `[RESEARCH]`
2.2.4 **The connection preface**: the 24 octets `PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n` followed by a
      SETTINGS frame — chosen deliberately so an HTTP/1.1 server cannot misinterpret it. `[WIRE]`
      `[PROVE]` `[RESEARCH]`
2.2.5 **The complete SETTINGS parameter list with identifiers and defaults**:
      `SETTINGS_HEADER_TABLE_SIZE` 0x01 = **4096**, `SETTINGS_ENABLE_PUSH` 0x02 = **1**,
      `SETTINGS_MAX_CONCURRENT_STREAMS` 0x03 = **unlimited** (recommended ≥100),
      `SETTINGS_INITIAL_WINDOW_SIZE` 0x04 = **65,535**, `SETTINGS_MAX_FRAME_SIZE` 0x05 = **16,384**
      (range 16,384–16,777,215), `SETTINGS_MAX_HEADER_LIST_SIZE` 0x06 = **unlimited**. `[TABLE]`
      `[NUM]` `[SPEC]` `[RESEARCH]`
2.2.6 **Streams**: client-initiated streams are odd-numbered, server-initiated even; stream 0 is the
      connection control stream. Stream IDs are monotonically increasing and **exhaustible** at
      2^31−1, which is why long-lived HTTP/2 connections eventually need GOAWAY and a new
      connection. `[NUM]` `[PROVE]`
2.2.7 **The seven stream states**: idle, reserved (local), reserved (remote), open, half-closed
      (local), half-closed (remote), closed — and the transitions driven by HEADERS, END_STREAM,
      RST_STREAM and PUSH_PROMISE. `[TABLE]` `[SPEC]` `[RESEARCH]`
2.2.8 **Multiplexing**: many concurrent request/response exchanges interleaved on one TCP
      connection, responses in any order. This eliminates **HTTP-layer** HOL blocking. `[PROVE]`
2.2.9 **Flow control** in HTTP/2: per-stream *and* per-connection windows, default **65,535 bytes**,
      maximum 2^31−1, applying to **DATA frames only**, adjusted by WINDOW_UPDATE. A receiver that
      never sends WINDOW_UPDATE stalls the stream — a real bug class in hand-written clients.
      `[NUM]` `[TRAP]`
2.2.10 The window-size arithmetic: the default 65,535-byte connection window means a single-stream
       download stalls after 64 KB per RTT unless the window is raised — which is exactly why the
       JDK sets `jdk.httpclient.windowsize` to **16 MB** and `connectionWindowSize` to **2^26**.
       `[CALC]` `[NUM]` `[RESEARCH]`
2.2.11 **HPACK (RFC 7541)**: a 61-entry static table, a dynamic table with a size bound negotiated by
       `SETTINGS_HEADER_TABLE_SIZE`, Huffman coding, and the four representation forms (indexed,
       literal with incremental indexing, literal without indexing, literal never-indexed). Effect:
       repeated headers collapse to one or two bytes. `[NUM]` `[SPEC]`
2.2.12 **HPACK's `never-indexed` form** exists for security (CRIME/BREACH-style attacks on
       compressed secrets) — a protocol-level acknowledgement that compression plus secrets is
       dangerous. `[X-REF 13]`
2.2.13 **HPACK is stateful across the connection**, which means an HTTP/2 proxy must maintain
       compression contexts per connection and cannot naively forward frames.
2.2.14 **Priority: the RFC 9113 deprecation.** The PRIORITY frame, dependency tree, weights and
       exclusive flag from RFC 7540 are deprecated. The replacement is **RFC 9218 Extensible
       Priorities**: the `Priority` header field (and PRIORITY_UPDATE frame) carrying `u=` (urgency
       0–7, default 3) and `i` (incremental). `[VERSION-TRAP]` `[SPEC]` `[RESEARCH]`
2.2.15 **Server push is dead**: RFC 9113 says servers MUST NOT set `SETTINGS_ENABLE_PUSH` to 1;
       Chrome removed support. The replacement is **`103 Early Hints` (RFC 8297)** with
       `Link: </app.css>; rel=preload`. `[VERSION-TRAP]` `[RESEARCH]`
2.2.16 **The error-code list**: NO_ERROR 0x0, PROTOCOL_ERROR 0x1, INTERNAL_ERROR 0x2,
       FLOW_CONTROL_ERROR 0x3, SETTINGS_TIMEOUT 0x4, STREAM_CLOSED 0x5, FRAME_SIZE_ERROR 0x6,
       REFUSED_STREAM 0x7, CANCEL 0x8, COMPRESSION_ERROR 0x9, CONNECT_ERROR 0xa,
       ENHANCE_YOUR_CALM 0xb, INADEQUATE_SECURITY 0xc, HTTP_1_1_REQUIRED 0xd. `[TABLE]` `[NUM]`
2.2.17 **GOAWAY** and graceful shutdown: the last-stream-ID semantics, the two-GOAWAY pattern
       (2^31−1 first, then the real ID after a delay) that lets in-flight requests finish. This is
       how a zero-downtime deploy of an HTTP/2 service actually works. `[FLOW]`
2.2.18 **Pseudo-headers**: `:method`, `:scheme`, `:authority`, `:path` for requests and `:status`
       for responses; they must precede regular fields, and `:authority` replaces `Host`. Field
       names **must be lowercase**. `[WIRE]` `[SPEC]`
2.2.19 What HTTP/2 removes: chunked transfer encoding (framing is now the transport's job), the
       `Connection` header and all hop-by-hop headers, and `Upgrade`. `[SPEC]`
2.2.20 **h2 vs h2c**: HTTP/2 over TLS negotiated by ALPN vs cleartext HTTP/2. Browsers implement
       only h2; h2c is used internally (gRPC in a mesh) and via prior knowledge, not via the
       deprecated `Upgrade: h2c` dance. `[TRAP]`
2.2.21 **The remaining problem: TCP-level head-of-line blocking.** All streams share one TCP
       connection and TCP delivers bytes in order, so one lost packet stalls *every* multiplexed
       stream until it is retransmitted. On a lossy mobile link HTTP/2 can be measurably worse than
       HTTP/1.1's six connections. `[PROVE]` `[TRAP]`
2.2.22 **The backend consequence that surprises people: one HTTP/2 connection + an L4 load balancer
       = all traffic pinned to one backend.** gRPC is HTTP/2, so a REST→gRPC migration silently
       destroys load distribution. Fixes: an L7 balancer that balances per *request*, client-side
       load balancing, or `max_connection_age` forcing periodic reconnection. `[TRAP]`
       `[INCIDENT]`
2.2.23 The HTTP/2 DoS family as an operational concern: `CONTINUATION` flood, the **Rapid Reset**
       attack (CVE-2023-44487 — open and immediately RST_STREAM, unbounded by
       MAX_CONCURRENT_STREAMS), and the mitigations (rate-limit stream creation, cap resets per
       connection). `[X-REF 13]` `[RESEARCH]`
2.2.24 When HTTP/2 is *not* the right choice: a single large download (no multiplexing benefit,
       plus per-byte CPU cost), a lossy link, or a path through middleboxes that mangle it.

*(24 leaves)*

## §2.3 HTTP/3 and QUIC, in depth

2.3.1 Why QUIC exists: TCP HOL blocking is unfixable without changing TCP, TCP is ossified by
      middleboxes so it cannot be changed, therefore build a new transport in **user space over
      UDP**. `[PROVE]`
2.3.2 The layering: QUIC (RFC 9000) is the transport; TLS 1.3 (RFC 9001) is fused into it, not
      layered on top; HTTP/3 (RFC 9114) is the application mapping. `[TABLE]`
2.3.3 **Streams as first-class transport objects**: per-stream ordering and per-stream reliability.
      Loss on stream A does not block stream B. This is the entire point. `[PROVE]`
2.3.4 **The four stream types** with their two low bits: client-initiated bidirectional 0x00,
      server-initiated bidirectional 0x01, client-initiated unidirectional 0x02, server-initiated
      unidirectional 0x03. `[NUM]` `[SPEC]` `[RESEARCH]`
2.3.5 **The QUIC frame inventory** with section numbers: PADDING, PING, ACK, RESET_STREAM,
      STOP_SENDING, CRYPTO, NEW_TOKEN, STREAM, MAX_DATA, MAX_STREAM_DATA, MAX_STREAMS,
      DATA_BLOCKED, STREAM_DATA_BLOCKED, STREAMS_BLOCKED, NEW_CONNECTION_ID, RETIRE_CONNECTION_ID,
      PATH_CHALLENGE, PATH_RESPONSE, CONNECTION_CLOSE, HANDSHAKE_DONE (RFC 9000 §19.1–19.20).
      `[TABLE]` `[SPEC]` `[RESEARCH]`
2.3.6 **Packet types**: Initial, 0-RTT, Handshake, Retry, Version Negotiation, and 1-RTT (short
      header). Long header vs short header and why the short header is minimal. `[WIRE]` `[SPEC]`
2.3.7 **Connection IDs** (RFC 9000 §5.1): the connection is identified by an opaque CID, **not the
      4-tuple**. This is what makes connection migration possible. `[PROVE]`
2.3.8 **Connection migration** (§9) and **path validation** (§8.2) via PATH_CHALLENGE /
      PATH_RESPONSE: switching Wi-Fi→cellular does not drop the connection, and the new path must
      prove reachability before it is trusted (anti-amplification). `[FLOW]` `[SPEC]`
2.3.9 **Transport parameters** negotiated in the handshake: `initial_max_data`,
      `initial_max_stream_data_bidi_local/_remote/_uni`, `initial_max_streams_bidi/_uni`,
      `max_idle_timeout`, `max_udp_payload_size`, `ack_delay_exponent`, `max_ack_delay`,
      `active_connection_id_limit`, `disable_active_migration`, `preferred_address`,
      `stateless_reset_token`. `[TABLE]` `[SPEC]` `[RESEARCH]`
2.3.10 **Flow control** at two levels (connection via MAX_DATA, stream via MAX_STREAM_DATA) plus a
       **stream-count** limit via MAX_STREAMS — three limits, not two. `[SPEC]`
2.3.11 **The 3× amplification limit**: before address validation a server may send at most three
       times the bytes it received, which is why Initial packets are padded to 1200 bytes. `[NUM]`
       `[PROVE]` `[RESEARCH]`
2.3.12 **Retry packets and address-validation tokens**; `NEW_TOKEN` for future connections.
2.3.13 **Stateless reset** (§10.3): how an endpoint that lost its state tells the peer to give up
       without holding any.
2.3.14 **Handshake cost**: 1 RTT for a first connection (TLS 1.3 and transport setup are the *same*
       flight), **0 RTT** on resumption — with the same replay caveat as TLS 0-RTT. `[CALC]`
2.3.15 **HTTP/3 frames** with codes: DATA 0x00, HEADERS 0x01, CANCEL_PUSH 0x03, SETTINGS 0x04,
       PUSH_PROMISE 0x05, GOAWAY 0x06, MAX_PUSH_ID 0x07. Note the codes deliberately differ in
       meaning from HTTP/2's. `[TABLE]` `[NUM]` `[SPEC]` `[RESEARCH]`
2.3.16 **HTTP/3 unidirectional stream types**: control 0x00, push 0x01, QPACK encoder 0x02, QPACK
       decoder 0x03, plus the reserved grease pattern `0x1f*N + 0x21`. `[NUM]` `[SPEC]`
2.3.17 **HTTP/3 SETTINGS**: `SETTINGS_MAX_FIELD_SECTION_SIZE` 0x06, plus QPACK's
       `SETTINGS_QPACK_MAX_TABLE_CAPACITY` and `SETTINGS_QPACK_BLOCKED_STREAMS`; the HTTP/2
       settings that are **forbidden** in HTTP/3 (ENABLE_PUSH, INITIAL_WINDOW_SIZE, MAX_FRAME_SIZE,
       MAX_HEADER_LIST_SIZE). `[SPEC]` `[RESEARCH]`
2.3.18 **The H3_* error codes** (H3_NO_ERROR 0x00 through H3_ID_ERROR 0x0f, plus
       H3_VERSION_FALLBACK 0x110). `[TABLE]` `[NUM]` `[RESEARCH]`
2.3.19 **QPACK (RFC 9204)**: HPACK cannot work over QUIC because streams arrive out of order, so
       QPACK splits table updates onto dedicated encoder/decoder streams, tracks a **Required
       Insert Count**, and allows a bounded number of **blocked streams** — trading compression
       ratio against HOL blocking. `[PROVE]` `[SPEC]` `[RESEARCH]`
2.3.20 **What HTTP/3 forbids**: `Transfer-Encoding`, the `Connection` header, `Upgrade`, and
       uppercase field names. `[SPEC]`
2.3.21 **Extended CONNECT (RFC 9220/8441)** and how WebSockets run over HTTP/3; **CONNECT-UDP
       (RFC 9298)** and MASQUE as the tunnelling story. `[RESEARCH]`
2.3.22 **Discovery**: `Alt-Svc: h3=":443"` (requires one prior connection) vs the **HTTPS RR with
       `alpn="h3"`** (zero prior connections). `[RESEARCH]`
2.3.23 **The costs of QUIC**: significantly higher CPU per byte (user-space crypto and per-packet
       processing, no mature offload), UDP throttled or blocked on some networks, harder to inspect
       and debug (encrypted headers), and immature server-side tooling. Measured CPU gaps of 2–3×
       versus kernel TCP were the norm before GSO/GRO for UDP landed. `[TRAP]` `[RESEARCH]`
2.3.24 **Where QUIC is on AWS**: CloudFront supports HTTP/3; **ALB does not**. So "we'll just turn
       on HTTP/3" is not a checkbox for an ALB-fronted service. `[VERSION-TRAP]` `[RESEARCH]`
       `[X-REF 18]`
2.3.25 **Java's HTTP/3 story**: the JDK `HttpClient` supports HTTP/1.1 and HTTP/2 only in 21; HTTP/3
       requires a third-party stack (Netty incubator codec-http3, Jetty, `kwik`, or an
       out-of-process proxy). State this rather than implying `HttpClient.Version.HTTP_3` exists.
       `[TRAP]` `[VERSION-TRAP]` `[RESEARCH]`
2.3.26 The decision rule: HTTP/3 pays for itself on **lossy, high-latency, mobile, client-facing**
       paths; inside a datacentre on a 0.05% loss network, HTTP/2 over TCP is usually cheaper.

*(26 leaves)*

## §2.4 Protocol selection and negotiation in practice

2.4.1 The negotiation ladder: DNS HTTPS RR → ALPN in the TLS handshake → `Alt-Svc` for a future
      upgrade → prior knowledge (h2c) → `Upgrade` (dead). `[FLOW]` `[TABLE]`
2.4.2 `HttpClient.Version.HTTP_2` semantics in the JDK: it is a *preference*, negotiated by ALPN,
      falling back to 1.1 — and `HttpResponse.version()` tells you what actually happened. `[API]`
      `[TRAP]`
2.4.3 Protocol choice by workload: browser-facing (h2/h3), service-to-service RPC (h2/gRPC),
      long-poll or SSE (h1.1 or h2), bulk transfer (h1.1 is fine), internal admin (whatever).
      `[TABLE]`
2.4.4 The connection-count consequence: with h1.1 you need a pool of N connections per host; with h2
      you need one (plus a policy for when to open a second). Pool sizing changes meaning entirely
      between the two. `[PROVE]`

*(4 leaves)*

## §2.5 Connection pooling

2.5.1 What a pool actually saves, quantified: DNS + TCP + TLS = up to 3 RTTs, plus the slow-start
      warm-up of the congestion window, plus the TLS CPU. At 80 ms RTT that is 240 ms per request
      avoided. `[CALC]` `[PROVE]`
2.5.2 The pool's state per entry: the socket, its last-used timestamp, its protocol, its
      health/validity flag, and (for h2) its active stream count.
2.5.3 Pool sizing: **max total**, **max per route/host**, and why the per-route limit is the one
      that actually bites. Apache HttpClient 5 defaults to `maxTotal=25`, `maxPerRoute=5` — far too
      low for a service, and a very common production bottleneck. `[NUM]` `[TRAP]` `[RESEARCH]`
2.5.4 Sizing arithmetic via **Little's Law**: `concurrency = throughput × latency`. For the
      QuizStakes restriction call at 1,200/sec and 10 ms average, you need ~12 concurrent
      connections; at the 30 ms budget, ~36. Size the pool from the arithmetic, not from a guess.
      `[CALC]` `[PROVE]`
2.5.5 **Pool acquisition timeout** as a first-class timeout (§2.7) and the queue in front of the
      pool that has no bound unless you give it one. `[TRAP]`
2.5.6 Validation strategies: validate-on-borrow (costly, safest), time-based staleness check
      (`validateAfterInactivity`, Apache default **2 s** in 5.x), or nothing plus a retry on a
      "stale connection" exception. `[NUM]` `[TABLE]` `[RESEARCH]`
2.5.7 **Eviction**: idle eviction (must be shorter than every downstream idle timeout, §2.6),
      **max lifetime** (forces re-resolution of DNS and rebalancing across backends — the fix for
      §1.19.5 and §2.2.22), and expired-connection cleanup threads.
2.5.8 **Trap:** creating a new `RestTemplate` / `WebClient` / `OkHttpClient` / `HttpClient` per
      request. Each carries its own pool, so you get zero reuse, unbounded socket creation, and
      eventually ephemeral-port exhaustion (§2.10). These objects are designed to be singletons.
      `[TRAP]` `[INCIDENT]`
2.5.9 **Trap:** not closing the response body. Apache HttpClient and OkHttp only return the
      connection to the pool when the entity is fully consumed or closed; a leaked body leaks a
      connection until eviction. Symptom: pool exhaustion under load with idle sockets in
      `ESTABLISHED`. `[TRAP]` `[DIAG]`
2.5.10 HTTP/2's effect on pooling: one connection multiplexes up to `SETTINGS_MAX_CONCURRENT_STREAMS`
       requests, so the pool becomes a *stream* pool. The relevant limit is now streams, not
       sockets, and the JDK caps client-side concurrency by `jdk.httpclient.maxstreams` (**100**).
       `[NUM]` `[RESEARCH]`
2.5.11 The pool as a **bulkhead**: a bounded pool is an implicit concurrency limit on a downstream,
       and removing the bound (as unbounded virtual threads can) removes accidental backpressure.
       `[X-REF 14]` `[PROVE]`
2.5.12 Pool metrics worth emitting: available, leased, pending, max, acquisition-wait p99, and
       connection age distribution. Without `pending`, pool exhaustion looks like downstream
       slowness. `[X-REF 20]` `[TRAP]`
2.5.13 Comparison of the four common Java clients' pool models: JDK `HttpClient` (implicit,
       property-tuned), Apache HttpClient 5 (`PoolingHttpClientConnectionManager`, explicit),
       OkHttp (`ConnectionPool(maxIdleConnections=5, keepAliveDuration=5min)`), Reactor Netty
       (`ConnectionProvider`, `maxConnections` default = `max(availableProcessors, 8) * 2`).
       `[TABLE]` `[NUM]` `[RESEARCH]`
2.5.14 JDBC pool parallels — HikariCP's `maximumPoolSize`, `connectionTimeout` (**30 s**),
       `maxLifetime` (**30 min**), `keepaliveTime` — and why the DB pool acquisition timeout must be
       shorter than the HTTP read timeout upstream of it. `[X-REF 09]` `[NUM]`

*(14 leaves)*

## §2.6 Keep-alive, idle timeouts, and the mismatch incident

2.6.1 Keep-alive is an *agreement* to leave a TCP connection open between requests, and **every hop
      has its own opinion about how long that is allowed**. `[PROVE]`
2.6.2 **The idle-timeout ladder**, with real defaults: client pool idle timeout (JDK
      `jdk.httpclient.keepalive.timeout` **30 s**; OkHttp **5 min**), server keep-alive (nginx
      `keepalive_timeout` **75 s**; Tomcat `keepAliveTimeout` = `connectionTimeout` **20 s**),
      load-balancer idle timeout (**AWS ALB 60 s**), ALB **client keep-alive 65 s**, NAT/firewall
      conntrack idle (often **350 s**, sometimes far less; `nf_conntrack_tcp_timeout_established`
      default **432000 s** on Linux but overridden aggressively by appliances). `[TABLE]` `[NUM]`
      `[RESEARCH]`
2.6.3 **The mismatch failure, mechanism first.** The client pool holds a connection idle for 90 s;
      the ALB closes idle connections at 60 s. At t=70 s the client picks a connection it believes
      is alive and writes onto a socket the LB has already FIN'd or RST'd. `[FLOW]` `[INCIDENT]`
2.6.4 **The signature of this incident**: sporadic, low-single-digit-percentage
      `Connection reset by peer` / `NoHttpResponseException` / `java.io.IOException: Broken pipe`,
      **correlated with low traffic** (idle connections only accumulate when you are not busy),
      unreproducible in a load test, and made to vanish by a retry — which is why it goes
      unfixed for months. `[DIAG]` `[TRAP]`
2.6.5 **The rule**: the client's idle timeout must be **strictly shorter** than every downstream
      idle timeout. Against a 60 s ALB, set the client to ~30 s. Against ALB specifically, also note
      the 65 s client-keep-alive value. `[NUM]` `[PROVE]`
2.6.6 **The worse variant**: a stateful firewall that *silently drops* the flow instead of sending
      RST. Your write succeeds into a black hole and every affected request waits out the full read
      timeout. `[INCIDENT]`
2.6.7 **The defence for the silent-drop case**: TCP keep-alive probes, set per-socket to 30–60 s
      (the kernel default of **7200 s** is useless for this), or an application-level heartbeat
      (HTTP/2 PING, gRPC keepalive, WebSocket ping). `[SYSCTL]` `[NUM]`
2.6.8 **gRPC keepalive parameters** as the concrete example: `keepalive_time_ms`,
      `keepalive_timeout_ms`, `keepalive_permit_without_calls`, and the server-side
      `GRPC_ARG_HTTP2_MIN_RECV_PING_INTERVAL_WITHOUT_DATA` — plus the `ENHANCE_YOUR_CALM` GOAWAY a
      server sends when a client pings too aggressively. `[NUM]` `[TRAP]` `[RESEARCH]`
2.6.9 `max_connection_age` / `max_connection_age_grace` on the server side: force clients to
      reconnect periodically so new backends receive traffic and DNS is re-resolved. The
      counterpart of §2.2.22. `[PROVE]`
2.6.10 Retry-on-idle-connection-failure as a legitimate, narrow use of retry: an idempotent request
       that failed *before any byte was written* is safe to replay on a fresh connection, and this
       is exactly what `jdk.httpclient.disableRetryConnect=false` and Apache's
       `DefaultHttpRequestRetryStrategy` do. `[PROVE]` `[TRAP]`

*(10 leaves)*

## §2.7 The timeout taxonomy

2.7.1 **The six timeouts of an HTTP call**, each with what starts and stops its clock: pool
      acquisition, DNS resolution, TCP connect, TLS handshake, socket read (inactivity), and total
      request duration. Being able to enumerate these separates people who have run services from
      people who have read about them. `[TABLE]` `[PROVE]`
2.7.2 **The read timeout is an inactivity timeout, not a duration timeout.** A server dribbling one
      byte per second keeps a 10 s read timeout alive forever. Only a *total* timeout bounds
      latency. `[PROVE]` `[TRAP]`
2.7.3 **DNS resolution has no timeout in the JDK's blocking path** — `InetAddress.getByName` will
      wait out `resolv.conf`'s `timeout`×`attempts`×nameservers. `[TRAP]` `[NUM]`
2.7.4 **Java's defaults are infinite**: `Socket` with no `soTimeout`, `HttpURLConnection` with
      `connectTimeout=0` and `readTimeout=0`, `RestTemplate` with `SimpleClientHttpRequestFactory`
      and no settings, and JDBC drivers with no `socketTimeout`. `[NUM]` `[TRAP]`
2.7.5 **The cascading-failure story, with arithmetic.** A hung downstream + infinite read timeout +
      a 200-thread Tomcat pool = full unavailability after 200 requests accumulate. At the
      QuizStakes card-deposit rate of 40/sec, that is **five seconds**. Your process is healthy the
      entire time. `[CALC]` `[INCIDENT]` `[PROVE]`
2.7.6 Setting them in Java 21, at every layer: `HttpClient.newBuilder().connectTimeout(...)` +
      `HttpRequest.newBuilder().timeout(...)`; Apache HttpClient 5's
      `ConnectionConfig.setConnectTimeout`/`setSocketTimeout` +
      `RequestConfig.setConnectionRequestTimeout`/`setResponseTimeout`; OkHttp's
      `connectTimeout`/`readTimeout`/`writeTimeout`/`callTimeout`; Spring's
      `ClientHttpRequestFactorySettings` and `spring.http.client.connect-timeout` /
      `read-timeout`. `[API]` `[BUILD]`
2.7.7 **Timeout budgets shrink with depth.** If the edge allows 3 s, a service two hops in cannot
      have a 5 s timeout — it will still be working on a request nobody is waiting for. `[PROVE]`
2.7.8 **A timeout longer than the caller's timeout is dead code that burns resources.** State this
      as a rule and derive it. `[PROVE]`
2.7.9 **Deadline propagation** as the correct general mechanism: pass the remaining budget
      downstream (gRPC's `grpc-timeout` header, a `X-Request-Deadline` convention, `Context` with a
      deadline) so every hop knows when to give up. `[X-REF 12]` `[X-REF 20]`
2.7.10 Choosing a value: set it from the callee's **measured p99.9 plus headroom**, not from a round
       number. Then note the QuizStakes counterexample where p99 is 38 s and no value is
       defensible. `[NUM]` `[PROVE]`
2.7.11 **Trap:** setting a read timeout but not a **pool acquisition timeout**. When the pool is
       exhausted, threads queue at the pool unbounded, and your carefully configured 2 s read
       timeout never even starts counting. `[TRAP]`
2.7.12 **Trap:** assuming a timeout cancels the work. A client-side timeout abandons the *response*;
       the server keeps processing, keeps holding the DB row lock, and may still commit. This is why
       the PSP capture row says "timeout ≠ failure". `[TRAP]` `[PROVE]`
2.7.13 Server-side request timeouts as the other half: Tomcat's `connectionTimeout`, nginx's
       `proxy_read_timeout`, ALB's idle timeout, and an application-level
       `@Transactional(timeout=...)`. Without one, a hung request holds a thread indefinitely
       regardless of what the client does. `[X-REF 09]`
2.7.14 Load-balancer 504 vs application timeout: which one fires first determines whether you get a
       structured error payload or an LB-generated HTML page. Order them deliberately. `[TRAP]`

*(14 leaves)*

## §2.8 Retries, backoff, and hedging

2.8.1 What a retry is *for*: a **transient** failure. Retrying a deterministic failure (400, 404,
      validation) is pure load amplification. `[PROVE]`
2.8.2 **Retry only idempotent operations** — or non-idempotent operations protected by an
      idempotency key. GET/HEAD/PUT/DELETE/OPTIONS are idempotent by RFC 9110; POST is not.
      `[X-REF 12]` `[SPEC]`
2.8.3 The retryable-condition table: connect failure (safe — no bytes sent), connection reset before
      response (safe if idempotent), read timeout (**unsafe** — the request may have been
      processed), 429/503 with `Retry-After` (safe, and obey the header), 500 (usually unsafe),
      502/504 (ambiguous). `[TABLE]` `[PROVE]`
2.8.4 **Exponential backoff**: `delay = base × 2^attempt`, capped. Why fixed-interval retry
      synchronises clients into a thundering herd. `[PROVE]` `[CALC]`
2.8.5 **Jitter**, and why it is not optional: full jitter (`random(0, backoff)`), equal jitter,
      decorrelated jitter (`min(cap, random(base, prev*3))`). Without jitter, every client retries
      at the same instant and re-creates the outage. `[PROVE]` `[NUM]`
2.8.6 **Retry amplification arithmetic**: 3 attempts at each of 3 layers = **27×** load at the
      bottom. Retry at exactly **one** layer — usually the one closest to the failure that knows
      the semantics. `[CALC]` `[PROVE]` `[TRAP]`
2.8.7 **Retry budgets** (a token bucket over the retry rate, e.g. "retries may not exceed 10% of
      requests") as the mechanism that makes retries safe under a broad outage. This is what
      Envoy/gRPC call a retry budget and it is strictly better than a max-attempts count.
      `[PROVE]` `[RESEARCH]`
2.8.8 **Retry storms** as a failure mode: a slow dependency causes timeouts, timeouts cause retries,
      retries increase load, load increases slowness. The positive feedback loop is the outage.
      `[INCIDENT]`
2.8.9 **Hedged requests** (send a second request at p95 if the first has not answered, take the
      first response, cancel the other): they cut tail latency at a bounded cost in extra load, and
      require idempotency. Note the "tail at scale" framing. `[PROVE]`
2.8.10 Where retries belong architecturally: at the client library with a budget, *not* in
       application code sprinkled per call site; and never at more than one layer. Spring Retry,
       Resilience4j `Retry`, `RetryTemplate`, and the JDK client's built-in connect retry.
       `[API]`
2.8.11 **Trap:** enabling `jdk.httpclient.enableAllMethodRetry=true` (retrying POST) without an
       idempotency key. You are choosing duplicate charges over an error message. `[TRAP]`
       `[RESEARCH]`
2.8.12 Retry interaction with timeouts: the total request timeout must cover *all* attempts, or your
       "3 retries with 2 s timeout" is actually a 6 s worst case that nobody budgeted for.
       `[CALC]` `[TRAP]`

*(12 leaves)*

## §2.9 Circuit breakers, bulkheads, and load shedding

2.9.1 The circuit breaker's purpose: stop sending traffic to a dependency that is failing, so you
      fail fast, free your threads, and let the dependency recover. `[PROVE]`
2.9.2 The three states and their transitions: **CLOSED** (pass through, count failures), **OPEN**
      (fail immediately for `waitDurationInOpenState`), **HALF_OPEN** (allow N probe calls; on
      success close, on failure re-open). `[FLOW]`
2.9.3 Resilience4j's configuration surface by name: `failureRateThreshold` (default **50%**),
      `slowCallRateThreshold`, `slowCallDurationThreshold`, `slidingWindowType`
      (COUNT_BASED/TIME_BASED), `slidingWindowSize`, `minimumNumberOfCalls` (default **100**),
      `waitDurationInOpenState` (**60 s**), `permittedNumberOfCallsInHalfOpenState` (**10**),
      `automaticTransitionFromOpenToHalfOpenEnabled`. `[API]` `[NUM]` `[RESEARCH]`
2.9.4 **`minimumNumberOfCalls` is the knob people forget**: with the default 100, a low-traffic
      endpoint never trips the breaker at all. `[TRAP]`
2.9.5 **Bulkheads**: a bounded concurrency limit per dependency, so one slow dependency cannot
      consume every thread. Resilience4j `Bulkhead` (semaphore) and `ThreadPoolBulkhead`. A bounded
      connection pool is already a bulkhead. `[PROVE]`
2.9.6 **Load shedding**: reject early (429/503 with `Retry-After`) when the queue exceeds what you
      can serve within the deadline — because a request you will answer after the caller has given
      up is pure waste. `[PROVE]` `[X-REF 22]`
2.9.7 Adaptive concurrency limits (Netflix `concurrency-limits`, Vegas/gradient algorithms) as the
      alternative to a static bulkhead.
2.9.8 **Fallbacks** and their honest cost: a fallback that returns stale data is a *product*
      decision. In QuizStakes, `ClientRestrictions` has **no valid fallback** — you cannot let a
      self-excluded client stake because the restriction service is slow. State this as the example
      of when fail-open is unacceptable. `[TRAP]` `[PROVE]`
2.9.9 The interaction chain: timeout → retry (budgeted, jittered) → circuit breaker → bulkhead →
      fallback → shed. Ordering matters, and Resilience4j's decorator order documents it. `[FLOW]`
2.9.10 What a breaker cannot fix: a dependency that is *correct but slow forever*, and a dependency
       you cannot function without. `[PROVE]`

*(10 leaves)*

## §2.10 TIME_WAIT and ephemeral port exhaustion

2.10.1 **The mechanism**: the active closer (the side that sent the first FIN) holds the socket in
       `TIME_WAIT` for **2×MSL**. RFC 9293 §3.4.2 sets MSL = 2 minutes, so the spec value is 4
       minutes; **Linux uses a fixed 60 s** compiled in as `TCP_TIMEWAIT_LEN`. `[NUM]` `[SPEC]`
       `[RESEARCH]`
2.10.2 **The two reasons it exists**: (a) absorb delayed duplicate segments so they cannot be
       mistaken for data on a new incarnation of the same 4-tuple; (b) guarantee the final ACK can
       be retransmitted if the peer re-sends its FIN. `[PROVE]`
2.10.3 **Trap:** `net.ipv4.tcp_fin_timeout` does **not** control `TIME_WAIT`. It bounds
       `FIN_WAIT_2`. `TCP_TIMEWAIT_LEN` is compile-time and not tunable via sysctl. Almost every
       blog post gets this wrong. `[TRAP]` `[SYSCTL]` `[RESEARCH]`
2.10.4 **Why it bites the client, not the server**: each outbound connection consumes a local
       ephemeral port from `ip_local_port_range` (default 32768–60999, **28,232 ports**), and the
       4-tuple means the limit is per destination IP:port pair. `[CALC]`
2.10.5 **The arithmetic**: 28,232 ports ÷ 60 s of `TIME_WAIT` ≈ **470 new connections per second
       sustained** to a single destination before exhaustion. A service making one fresh connection
       per request to one downstream hits this at ~470 rps. QuizStakes stake reservations run at
       **1,200/sec** — comfortably past it. `[CALC]` `[PROVE]` `[NUM]`
2.10.6 **The symptom**: `connect()` fails with `EADDRNOTAVAIL` — in Java,
       `java.net.BindException: Cannot assign requested address` — intermittently, under load, on
       the *client*, while the server looks perfectly healthy. `[DIAG]` `[TRAP]`
2.10.7 **Diagnose**: `ss -s` (summary with the timewait count), `ss -tan state time-wait | wc -l`,
       `cat /proc/sys/net/ipv4/ip_local_port_range`, `nstat -az TcpExtTW*`. `[DIAG]`
2.10.8 **The fixes in order of correctness**: (1) **connection pooling / keep-alive** — the real
       fix, because reused connections create almost no `TIME_WAIT`; (2) make the **server** the
       active closer where possible, so `TIME_WAIT` accumulates on the side with one port and
       millions of distinguishing 4-tuples; (3) `net.ipv4.tcp_tw_reuse=1`, which lets the kernel
       reuse a `TIME_WAIT` socket for a new *outbound* connection when TCP timestamps prove safety;
       (4) widen `ip_local_port_range` for ~2× headroom (a band-aid); (5) add destination
       addresses/ports, which multiplies the 4-tuple space. `[TABLE]` `[SYSCTL]` `[PROVE]`
2.10.9 **Never `tcp_tw_recycle`.** It broke catastrophically behind NAT (many clients share a source
       IP with unrelated timestamp clocks, so the kernel drops their SYNs) and was **removed in
       Linux 4.12**. Recommending it dates the recommender. `[TRAP]` `[VERSION-TRAP]`
2.10.10 `SO_REUSEADDR` on the *client* and `IP_BIND_ADDRESS_NO_PORT` as the finer-grained tools.
2.10.11 **`TIME_WAIT` on the server side is normal and mostly harmless** — it consumes a small
        kernel structure, and `net.ipv4.tcp_max_tw_buckets` bounds the total (exceeding it logs
        "TCP: time wait bucket table overflow"). `[SYSCTL]` `[NUM]`
2.10.12 The same arithmetic in a cloud NAT: an **AWS NAT Gateway supports ~55,000 simultaneous
        connections per unique destination**, shared across every instance behind it — so the port
        exhaustion becomes a *fleet-wide* limit and surfaces as
        `ErrorPortAllocation` on the NAT Gateway metric. `[NUM]` `[X-REF 18]` `[INCIDENT]`

*(12 leaves)*

## §2.11 CLOSE_WAIT and socket leaks

2.11.1 **The mechanism**: `CLOSE_WAIT` means the peer sent FIN and **your application has not called
       `close()`**. The kernel is waiting for your process. `[PROVE]`
2.11.2 **It does not time out.** Unlike `TIME_WAIT`, there is no kernel timer that clears it. A
       rising `CLOSE_WAIT` count is monotonic until the process dies. `[PROVE]` `[TRAP]`
2.11.3 **The rule to memorise**: rising `CLOSE_WAIT` = your bug (an fd leak). Rising `TIME_WAIT` =
       normal churn, possibly too much of it. Conflating the two is the most common TCP-state
       mistake in interviews. `[TRAP]`
2.11.4 The Java causes: not closing an `InputStream`/`HttpResponse` body, not using
       try-with-resources, an exception path that skips `close()`, a pooled client whose entity is
       never consumed (§2.5.9), and a custom NIO loop that removes a key without closing the
       channel. `[TABLE]`
2.11.5 Diagnose: `ss -tan state close-wait`, `lsof -p <pid> | grep CLOSE_WAIT`, then a heap dump or
       `jcmd` to find who holds the socket. `[DIAG]` `[X-REF 06]`
2.11.6 `FIN_WAIT_2` accumulation as the mirror image: **you** closed, the peer never did. Bounded by
       `net.ipv4.tcp_fin_timeout` (**60 s**) for orphaned sockets. `[SYSCTL]` `[NUM]`
2.11.7 The correct Java idiom: try-with-resources on `Socket`, on `HttpResponse.body()` streams, on
       `Response` in OkHttp, and `EntityUtils.consume` in Apache. `[BUILD]` `[API]`

*(7 leaves)*

## §2.12 Load balancing: L4 vs L7

2.12.1 **The comparison table**: what each sees (L4: IP + port + protocol; L7: method, path,
       headers, cookies, body), the decision unit (**connection** vs **request**), routing
       capability, TLS handling, per-request overhead, health-check depth, retry capability, and the
       AWS product (**NLB** vs **ALB**). `[TABLE]`
2.12.2 **The consequence that matters**: an L4 balancer pins a *connection* to a backend. With
       keep-alive or HTTP/2 multiplexing, one long-lived connection carries thousands of requests,
       so the L4 balancer effectively load-balances **once**. `[PROVE]`
2.12.3 The visible symptom: you add a pod and it receives no traffic; existing pods stay hot. Fixes:
       L7 balancing, client-side load balancing, or `max_connection_age`. `[INCIDENT]`
2.12.4 **DSR (direct server return)** and the flow-hashing model of an L4 balancer; why NLB
       preserves the client IP (and therefore does not need `X-Forwarded-For`) while ALB does not.
       `[X-REF 18]`
2.12.5 **Balancing algorithms** and when each wins: round robin (uniform request cost),
       weighted round robin (heterogeneous instance sizes), **least connections** / least
       outstanding requests (variable request cost — ALB's default is round robin, with LOR
       available), **consistent hashing** / IP hash (cache or session affinity), **power of two
       choices** (near-optimal with O(1) state — the algorithm to name if you want to sound like you
       have read the literature), and **EWMA/least-latency**. `[TABLE]` `[PROVE]`
2.12.6 **Power of two choices, proved**: sampling two backends and picking the less loaded reduces
       maximum load from O(log n / log log n) to O(log log n). State the result and the intuition.
       `[PROVE]` `[RESEARCH]`
2.12.7 **Consistent hashing** in one paragraph plus virtual nodes, and why it is the right structure
       for cache affinity but the wrong one for stateless services. `[X-REF 22]` `[X-REF 15]`
2.12.8 **Health checks**: shallow (`/healthz` returns 200 if the process is up) vs deep (checks DB,
       cache, downstreams). Deep checks on a **liveness** probe cause correlated mass restarts when
       a shared dependency wobbles; deep checks on a **readiness** probe can remove every instance
       at once. `[TRAP]` `[X-REF 19]` `[X-REF 20]`
2.12.9 ALB health-check defaults: interval **30 s**, timeout **5 s**, healthy threshold **5**,
       unhealthy threshold **2** — so detection takes up to 60 s at defaults. `[NUM]` `[CALC]`
       `[RESEARCH]`
2.12.10 **Connection draining / deregistration delay** (ALB default **300 s**) and how a graceful
        shutdown must sequence: fail readiness → wait for the LB to notice → stop accepting → drain
        in-flight → close. Getting the order wrong produces 502s on every deploy. `[FLOW]`
        `[NUM]` `[INCIDENT]`
2.12.11 **Slow start** (ALB target-group setting, disabled by default) as the fix for a JIT-cold JVM
        being hit at full rate immediately after joining. `[X-REF 06]`
2.12.12 **Outlier detection / passive health checking** (Envoy) as the complement to active health
        checks.
2.12.13 **Global load balancing**: anycast, GeoDNS, and latency-based routing; and the fact that
        DNS-level global balancing has all the caching problems of §1.17.8. `[X-REF 18]`
2.12.14 **Client-side load balancing** (gRPC's `round_robin`/`pick_first`, Spring Cloud LoadBalancer,
        Ribbon's legacy): the client resolves all backends and chooses per request. It fixes
        §2.12.2 and removes a hop, at the cost of putting discovery and health logic in every
        client. `[TABLE]`
2.12.15 **Service mesh sidecars** as the way to get L7 balancing without library changes; the extra
        hop's latency cost (~0.5–1 ms per direction) as the price. `[X-REF 19]`

*(15 leaves)*

## §2.13 TLS termination topologies and identity through the path

2.13.1 **The three arrangements**: terminate at the LB with plaintext behind (simplest, cheapest,
       central cert management, requires a trusted segment); **terminate and re-encrypt** (LB sees
       the request for L7 routing/WAF and re-encrypts to the backend — compliance-friendly);
       **passthrough** (LB is L4 only, backend holds the cert — required for end-to-end mTLS, but
       you lose all L7 capability). `[TABLE]` `[PROVE]`
2.13.2 What each arrangement costs and forbids: passthrough forbids path routing, header injection,
       WAF, HTTP health checks and per-request balancing. State the trade explicitly. `[TABLE]`
2.13.3 **`X-Forwarded-For`**: the client IP list, appended by each proxy. Reading the *rightmost
       untrusted* entry, not the leftmost, is the correct algorithm — the leftmost is
       client-controlled and spoofable. `[HDR]` `[TRAP]` `[X-REF 13]`
2.13.4 `X-Forwarded-Proto`, `X-Forwarded-Host`, `X-Forwarded-Port`, `X-Real-IP` and the
       standardised **`Forwarded` (RFC 7239)** with `for=`, `by=`, `host=`, `proto=` parameters,
       obfuscated node identifiers (`for=_hidden`), and quoted IPv6 forms. `[HDR]` `[SPEC]`
       `[RESEARCH]`
2.13.5 **The Spring failure**: without `server.forward-headers-strategy=framework|native`, the app
       sees the LB's IP as the client, believes the scheme is `http`, and generates `http://`
       redirect URLs from an HTTPS site — producing a redirect loop or a mixed-content error.
       `[API]` `[INCIDENT]` `[TRAP]`
2.13.6 **The security requirement**: these headers are trivially spoofable, so a server must only
       trust them from known proxies (`ForwardedHeaderFilter` + a trusted-proxy list, nginx's
       `set_real_ip_from`, Tomcat's `RemoteIpValve` with `internalProxies`). `[X-REF 13]`
       `[TRAP]`
2.13.7 **The PROXY protocol** as the L4 answer: a preamble before the first application byte
       carrying the original 4-tuple. **v1** is ASCII, e.g.
       `PROXY TCP4 192.168.0.1 192.168.0.11 56324 443\r\n`, max 107 bytes; **v2** is binary with the
       12-byte signature `\x0D\x0A\x0D\x0A\x00\x0D\x0A\x51\x55\x49\x54\x0A` plus TLVs (ALPN, SNI,
       client cert info, unique ID). `[WIRE]` `[SPEC]` `[RESEARCH]`
2.13.8 **The PROXY-protocol security rule**: a receiver must accept it **only from trusted senders**,
       otherwise any client can forge its own source IP. Enabling it on a publicly reachable
       listener is a vulnerability. `[TRAP]` `[X-REF 13]`
2.13.9 Enabling it in practice: NLB target-group attribute `proxy_protocol_v2.enabled`, nginx
       `proxy_protocol` on `listen`, Tomcat's `AprEndpoint`/`Nio2` with
       `RemoteIpFilter`, HAProxy `send-proxy`. `[API]`
2.13.10 **mTLS through the path**: where the client certificate is verified, and how the identity is
        forwarded to the app (`X-SSL-Client-Subject`, Envoy's `x-forwarded-client-cert`) once the
        proxy terminated the TLS the certificate belonged to. `[X-REF 13]`
2.13.11 Certificate management as an operational concern: ACME/Let's Encrypt automation, cert
        expiry as a recurring outage cause, and monitoring `notAfter` as a first-class alert.
        `[INCIDENT]` `[X-REF 20]`

*(11 leaves)*

## §2.14 Service discovery

2.14.1 The problem: in an autoscaled environment, the set of backend addresses changes continuously,
       so a static config or a long-TTL DNS record is wrong by construction. `[PROVE]`
2.14.2 The four mechanisms: **DNS-based** (including Kubernetes `ClusterIP` and headless services),
       **registry-based** (Consul, Eureka, etcd, ZooKeeper), **platform-based** (Kubernetes
       Endpoints/EndpointSlice, ECS service discovery), and **mesh-based** (xDS from a control
       plane). `[TABLE]`
2.14.3 Client-side vs server-side discovery, and how it interacts with §2.12.14.
2.14.4 The **staleness window** in each: DNS TTL + client cache, registry heartbeat interval +
       eviction threshold, EndpointSlice propagation + kube-proxy sync. Every one is a period during
       which you will send traffic to a dead instance. `[CALC]` `[PROVE]`
2.14.5 Why a dead-instance window makes retries mandatory rather than optional. `[PROVE]`
2.14.6 Kubernetes `Service` resolution mechanics in one paragraph: ClusterIP → iptables/IPVS rules
       programmed by kube-proxy → a random backend pod; headless services returning pod A records
       for client-side balancing. `[X-REF 19]`

*(6 leaves)*

## §2.15 NAT, in the amount a backend engineer needs

2.15.1 The mechanism: rewrite source IP (and usually source port) on egress, keep a translation
       table keyed by the 5-tuple so replies can be reversed. **NAT is stateful by definition.**
       `[PROVE]`
2.15.2 SNAT / DNAT / PAT (NAPT / "IP masquerading") and which one each cloud/container feature is.
2.15.3 Consequence 1 — **many hosts share one public IP**: the server sees one IP for thousands of
       clients, so IP-based rate limiting punishes whole offices and IP allow-listing is coarse.
       `[X-REF 13]`
2.15.4 Consequence 2 — **per-flow state with an idle timeout**. Idle connections are silently
       reaped, which is the root cause of §2.6.6. `[PROVE]`
2.15.5 Consequence 3 — **inbound connections to a NATed host are impossible without port
       forwarding**, which is why webhooks need a public endpoint and local development needs a
       tunnel.
2.15.6 Consequence 4 — the conntrack table is finite. `nf_conntrack_max`,
       `nf_conntrack_buckets`, and the kernel log line `nf_conntrack: table full, dropping packet`.
       On a busy container host this is a real and confusing outage. `[SYSCTL]` `[INCIDENT]`
       `[DIAG]`
2.15.7 **AWS NAT Gateway** specifics: charged per hour **and per GB processed**, ~**55,000
       simultaneous connections per unique destination**, and the `ErrorPortAllocation` /
       `PacketsDropCount` metrics. Heavy S3 traffic through a NAT Gateway is both a cost bug and a
       scaling bug — use a **VPC Gateway Endpoint**. `[NUM]` `[X-REF 18]`
2.15.8 NAT vs a proxy vs a gateway: three different things people call "the egress path".
2.15.9 Hairpin NAT / NAT loopback and the split-horizon incident of §1.17.10.
2.15.10 Carrier-grade NAT (`100.64.0.0/10`) and what it means for client-IP-based logic.

*(10 leaves)*

## §2.16 CDN mental model

2.16.1 What a CDN is: a globally distributed **reverse-proxy cache** between users and origin.
2.16.2 **The mechanism**: DNS (anycast or geo) resolves the hostname to a nearby edge PoP → the edge
       checks its cache → **hit** serves in ~10 ms with zero origin traffic → **miss** fetches from
       origin, often via a warm optimised backbone connection with **tiered caching** so many edges
       collapse into one origin fetch, and stores per `Cache-Control`. `[FLOW]` `[NUM]`
2.16.3 The five things you actually buy: latency (physics — a 150 ms intercontinental RTT is not
       optimisable any other way), origin offload, **TLS termination near the user** (the handshake
       RTTs shrink because the RTT itself shrinks), DDoS absorption, and compression/optimisation at
       the edge. `[PROVE]`
2.16.4 **The cache key** = host + path + whatever you tell it to vary on (query parameters, selected
       headers, cookies, device class). **Getting the cache key wrong is the main CDN bug**: vary
       on `Cookie` and hit rate goes to zero; ignore a meaningful query parameter and users receive
       each other's content. `[TRAP]` `[INCIDENT]`
2.16.5 The **cached-authenticated-response** catastrophe: a `Set-Cookie` or a personalised body
       cached under a shared key. Mitigation: `Cache-Control: private, no-store` on anything
       carrying `Authorization`, and an explicit allow-list of cacheable paths. `[TRAP]`
       `[X-REF 13]`
2.16.6 **Invalidation**: purge by path (slow, rate-limited, eventually consistent across PoPs),
       purge by surrogate key/tag, and **versioned URLs** (`app.a1b2c3.js` with a one-year
       `immutable` TTL). Versioned URLs are strictly better — change the key rather than purge it.
       `[PROVE]`
2.16.7 `Surrogate-Control` and `Surrogate-Key` as the CDN-only directives that let you set edge
       behaviour without affecting browsers.
2.16.8 **`stale-while-revalidate` and `stale-if-error`** as the two directives that convert an
       origin outage into a slightly-stale page instead of a 502. `[SPEC]` `[NUM]`
2.16.9 **Cache stampede at the edge**: on expiry, N edges fetch simultaneously. Mitigations: request
       coalescing/collapsing at the edge, tiered caching, and jittered TTLs. `[X-REF 15]`
2.16.10 Dynamic content still benefits: TLS terminates at the edge, and the edge-to-origin leg
        reuses a warm, tuned connection with a large congestion window.
2.16.11 Edge compute (Lambda@Edge, CloudFront Functions, Workers) in one paragraph and what belongs
        there (routing, header rewriting, A/B assignment, auth checks) vs what does not.
2.16.12 Origin shield, and the arithmetic of how much origin load a shield actually removes.
        `[CALC]`
2.16.13 The metrics that matter: cache hit ratio (by path pattern, not globally), origin request
        rate, edge p50/p99, and error rate by PoP. `[X-REF 20]`

*(13 leaves)*

## §2.17 Real-time delivery

2.17.1 **The comparison table**: short polling, long polling, SSE, WebSocket, webhooks, and
       (briefly) WebTransport — across direction, transport, infrastructure requirement, per-client
       cost, proxy friendliness, reconnection story, and typical use. `[TABLE]`
2.17.2 **Short polling**: simplest, updates lag by the interval, and the load is `clients /
       interval` regardless of whether anything changed. At 2.4M QuizStakes clients polling every
       10 s that is 240,000 rps of mostly-empty responses. `[CALC]` `[PROVE]`
2.17.3 **Long polling**: the server holds the request open until data or timeout. Near-real-time
       with zero new infrastructure, but ties up a connection (and, on a thread-per-request server,
       a thread) per client — which is exactly what virtual threads or async servlets fix.
       `[X-REF 04]`
2.17.4 **SSE**: `Content-Type: text/event-stream`, one long-lived HTTP response, server→client only.
       The wire format: `event:`, `data:` (repeatable, joined with `\n`), `id:`, `retry:` (ms), and
       `:` comment lines used as keep-alive. Dispatch on a blank line. `[WIRE]` `[SPEC]`
2.17.5 SSE's built-in resilience: automatic reconnection with the `retry` interval, and the
       **`Last-Event-ID`** request header on reconnect so the server can replay missed events. This
       is a real feature WebSocket does not have. `[PROVE]`
2.17.6 `EventSource` readyState values (CONNECTING 0, OPEN 1, CLOSED 2), `withCredentials`, UTF-8
       only, BOM stripping, and CRLF/LF/CR line endings all accepted. `[NUM]` `[SPEC]`
2.17.7 **SSE's operational hazards**: proxy buffering (nginx `proxy_buffering off` /
       `X-Accel-Buffering: no`), the browser's 6-connections-per-origin limit over HTTP/1.1 (fixed
       by HTTP/2), compression breaking streaming, and LB idle timeouts killing an idle stream
       (hence periodic comment heartbeats). `[TRAP]` `[INCIDENT]`
2.17.8 SSE in Spring: `SseEmitter`, `ResponseBodyEmitter`, `Flux<ServerSentEvent<T>>`, and the
       `MvcAsync` timeout (`spring.mvc.async.request-timeout`). `[API]`
2.17.9 **WebSocket's opening handshake**: `GET` with `Connection: Upgrade`, `Upgrade: websocket`,
       `Sec-WebSocket-Key` (a base64 16-byte nonce), `Sec-WebSocket-Version: 13`, optional
       `Sec-WebSocket-Protocol` and `Sec-WebSocket-Extensions`; the server replies **`101 Switching
       Protocols`** with `Sec-WebSocket-Accept` = base64(SHA-1(key + `258EAFA5-E914-47DA-95CA-
       C5AB0DC85B11`)). It starts as HTTP precisely so it traverses port 443 and existing proxies.
       `[WIRE]` `[NUM]` `[SPEC]` `[PROVE]`
2.17.10 **The frame format**: FIN, RSV1–3, 4-bit opcode, MASK, and payload length in 7 / 7+16 / 7+64
        bits. Opcodes: 0x0 continuation, 0x1 text, 0x2 binary, 0x8 close, 0x9 ping, 0xA pong.
        `[WIRE]` `[NUM]` `[SPEC]`
2.17.11 **Client-to-server frames must be masked** with a 4-byte key XORed over the payload;
        server-to-client must not be. The reason is cache-poisoning of intermediaries by a malicious
        script crafting bytes that look like an HTTP request. `[PROVE]` `[SPEC]`
2.17.12 **Control frames**: max **125-byte** payload, never fragmented, may be interleaved between
        fragments of a message. `[NUM]`
2.17.13 **Close codes**: 1000 normal, 1001 going away, 1002 protocol error, 1003 unsupported data,
        1006 abnormal (never sent on the wire — synthesised locally), 1007 invalid payload, 1008
        policy violation, 1009 too big, 1010 mandatory extension, 1011 internal error, 1015 TLS
        failure. `[TABLE]` `[NUM]`
2.17.14 `permessage-deflate` (RFC 7692) and its memory cost per connection
        (`server_max_window_bits`, `client_no_context_takeover`). `[RESEARCH]`
2.17.15 **WebSocket over HTTP/2 (RFC 8441)** via extended CONNECT and `SETTINGS_ENABLE_CONNECT_
        PROTOCOL`, and over HTTP/3 via RFC 9220. `[RESEARCH]`
2.17.16 **Operational cost of WebSockets, the part people underestimate**: connections are
        **stateful**, so any instance can be the one holding a given user's socket. You need sticky
        routing or a **pub/sub backplane** (Redis, Kafka) so a message produced on instance A
        reaches the socket on instance B. `[PROVE]` `[X-REF 14]`
2.17.17 **Deploys drop every connection at once**, so clients must reconnect with **backoff and
        jitter** or your rolling restart becomes a self-inflicted thundering herd. `[TRAP]`
        `[INCIDENT]`
2.17.18 LB idle timeouts kill idle sockets (§2.6), so you need application-level heartbeat pings
        even though TCP has its own.
2.17.19 Spring's WebSocket surface: `WebSocketHandler`, `@EnableWebSocket`, STOMP over WebSocket
        with `@MessageMapping` and a simple/relay broker, and `WebSocketSession` concurrency (a
        session is **not** thread-safe for concurrent sends). `[API]` `[TRAP]`
2.17.20 **Capacity arithmetic** for WebSockets: fds, kernel socket buffers (`tcp_rmem` default is
        the floor per connection), application buffers, and heap per session. 100k connections at
        even 20 KB of kernel+heap each is 2 GB before you store anything. `[CALC]`
2.17.21 **Webhooks** from the receiving side: must be **idempotent** (senders retry; duplicates are
        guaranteed), must **verify the signature** (HMAC over the **raw body**, verified *before*
        parsing, with a timestamp to prevent replay), must **respond fast** (ack in under a second
        and process asynchronously via a queue), and must tolerate out-of-order delivery.
        `[X-REF 13]` `[X-REF 14]`
2.17.22 Webhooks from the sending side: retry schedule, dead-lettering, a replay endpoint, signature
        key rotation, and static egress IPs for the receiver's allow-list.
2.17.23 **The default choice**: if it is server→client only, use **SSE** — it is dramatically simpler
        to operate. Reach for WebSocket only when you genuinely need bidirectional or
        high-frequency client→server traffic. `[PROVE]`
2.17.24 WebTransport in one paragraph as the QUIC-native successor (datagrams + streams, no framing
        of your own), and its current maturity. `[RESEARCH]`

*(24 leaves)*

## §2.18 gRPC on the wire

2.18.1 gRPC is **HTTP/2 plus a framing convention plus protobuf**, not a new transport. Everything
       in §2.2 applies to it. `[PROVE]`
2.18.2 The request headers: `:method POST`, `:path /quizstakes.FundsLedger/ReserveStake`,
       `content-type: application/grpc+proto`, `te: trailers`, `grpc-timeout: 150m`,
       `grpc-encoding`. `[WIRE]` `[HDR]` `[RESEARCH]`
2.18.3 **The message framing**: 1 byte compressed flag + 4 bytes big-endian length + the message
       bytes, inside HTTP/2 DATA frames. Compression context is **not** maintained across message
       boundaries. `[WIRE]` `[NUM]` `[RESEARCH]`
2.18.4 **The response always has `:status 200`**; the real outcome is in **trailers**:
       `grpc-status` (0 = OK), `grpc-message` (percent-encoded UTF-8), `grpc-status-details-bin`.
       This is why gRPC needs `te: trailers` and why proxies that drop trailers break it. `[TRAP]`
       `[PROVE]` `[RESEARCH]`
2.18.5 The 17 gRPC status codes mapped to their HTTP equivalents: OK 0, CANCELLED 1, UNKNOWN 2,
       INVALID_ARGUMENT 3, DEADLINE_EXCEEDED 4, NOT_FOUND 5, ALREADY_EXISTS 6, PERMISSION_DENIED 7,
       RESOURCE_EXHAUSTED 8, FAILED_PRECONDITION 9, ABORTED 10, OUT_OF_RANGE 11, UNIMPLEMENTED 12,
       INTERNAL 13, UNAVAILABLE 14, DATA_LOSS 15, UNAUTHENTICATED 16. `[TABLE]` `[NUM]`
       `[X-REF 12]`
2.18.6 The four call types and their stream shapes: unary, server streaming, client streaming,
       bidirectional streaming. `[TABLE]`
2.18.7 **Deadlines, not timeouts**: `grpc-timeout` propagates the remaining budget down the call
       tree, and a deadline is absolute rather than per-hop. This is the correct model and the
       reason to mention it in §2.7.9. `[PROVE]`
2.18.8 gRPC keepalive and the `ENHANCE_YOUR_CALM` GOAWAY (§2.6.8).
2.18.9 **Load balancing gRPC** — the concrete instance of §2.2.22 — via an L7 proxy (Envoy, ALB with
       gRPC target group), client-side `round_robin` with a resolver, or a lookaside balancer.
       `[TRAP]`
2.18.10 gRPC-Web and why it exists (browsers cannot control HTTP/2 frames or read trailers), plus
        the proxy translation it requires.
2.18.11 Payload-size comparison against JSON over HTTP/1.1 for one QuizStakes `ReserveStake` call,
        with the byte arithmetic. `[CALC]`
2.18.12 When *not* to use gRPC: browser clients, public APIs, human-debuggable interfaces, and
        anything where the tooling gap costs more than the bytes saved. `[X-REF 12]`

*(12 leaves)*

## §2.19 Bytes on the wire: serialisation and payload cost

2.19.1 Why payload size is a latency issue, not just a bandwidth one: it interacts with slow start
       (§1.12.4) and with the MSS (§1.4.4). A response that fits in the initial window arrives in
       one RTT; one that does not takes two. `[PROVE]` `[CALC]`
2.19.2 The formats and their trade: JSON (human, verbose, ubiquitous), protobuf (compact, schema,
       fast), Avro (schema registry, good for Kafka), MessagePack, CBOR, and plain text.
       `[TABLE]` `[X-REF 14]`
2.19.3 Compression on the wire: gzip (universal), Brotli (better ratio, slower to compress, best for
       static), zstd (best speed/ratio balance) — with the rule that you compress above ~1 KB and
       never compress already-compressed content. `[NUM]`
2.19.4 The interaction with HTTP/2 header compression: with HPACK, a 2 KB header set costs tens of
       bytes on subsequent requests, which changes the calculus about "chatty" APIs. `[CALC]`
2.19.5 Pagination and response-size limits as network design, not just API design. `[X-REF 12]`
2.19.6 Streaming a large response (chunked, SSE, gRPC server streaming) instead of buffering it, and
       the memory argument for doing so. `[X-REF 06]`

*(6 leaves)*

## §2.20 Concurrency models for network servers — the choice

2.20.1 **Thread-per-connection**: each connection owns a platform thread blocked in `read()`. Cost:
       ~1 MB of stack (JVM default `-Xss`), kernel task structures, and context switches at ~1–5 µs
       each with cache pollution. At 10,000 connections that is ~10 GB of stack and a thrashing
       scheduler — while most connections sit idle. **This is C10K.** `[CALC]` `[PROVE]`
       `[X-REF 11]`
2.20.2 **Thread-per-request with a bounded pool** (the servlet model): decouples threads from
       connections, but a request that blocks still holds its thread — so the pool size *is* your
       concurrency limit, and a slow downstream converts it into an outage (§2.7.5). `[PROVE]`
2.20.3 **`select`/`poll`**: one thread asks "which of these fds are ready?" but passes the whole set
       each call and the kernel scans all of it — **O(n) per call** — and `select` is capped at
       `FD_SETSIZE` (**1024**). At 10k fds you rescan 10k entries thousands of times a second.
       `[PROVE]` `[NUM]`
2.20.4 **`epoll` / `kqueue` / IOCP**: a persistent kernel-side interest set registered once, a
       callback that moves ready fds onto a ready list, and `epoll_wait` returning **only the ready
       fds** — **O(number of ready events)**. 10,000 idle connections become "wake up, handle the
       12 with data, sleep." `[PROVE]`
2.20.5 **The event-loop model** (Netty, nginx, Node, Vert.x, Undertow): a small pool of event-loop
       threads (typically 2× cores), each owning a selector and thousands of channels. Memory drops
       to a few KB per connection. `[NUM]`
2.20.6 **The absolute rule: never block the event loop.** A single blocking call stalls every
       connection that loop owns. Hence the reactive/callback/`CompletableFuture` style and the
       discipline of offloading blocking work to a separate executor. `[TRAP]` `[PROVE]`
2.20.7 **The cost of the event-loop model** is the programming model: stack traces are meaningless,
       `ThreadLocal` (and therefore MDC-based correlation IDs) breaks, debuggers lose causality, and
       backpressure must be expressed explicitly. `[X-REF 20]` `[X-REF 05]`
2.20.8 **Virtual threads (JDK 21, Project Loom)**: the JVM schedules virtual threads onto a small
       pool of carrier platform threads. On a blocking operation the runtime has instrumented —
       socket I/O, `Thread.sleep`, most `java.util.concurrent` locks — it **unmounts** the virtual
       thread, stores its continuation on the heap, and runs something else. Under the hood the JVM
       is doing exactly the epoll multiplexing of §2.20.4. `[PROVE]` `[X-REF 04]`
2.20.9 What that buys: straightforward blocking code with **real stack traces** and **working
       `ThreadLocal`/`ScopedValue`**, at event-loop-class scalability, with heap-allocated stacks
       that grow on demand (hundreds of bytes to a few KB) — so a million virtual threads is
       realistic. `[CALC]`
2.20.10 **What it does not fix — pinning.** On JDK 21, a virtual thread blocking inside a
        `synchronized` block or a native/JNI frame cannot unmount and holds its carrier hostage;
        `-Djdk.tracePinnedThreads=full` diagnoses it and `ReentrantLock` avoids it. **JEP 491
        (JDK 24) removed the `synchronized` case entirely and removed the
        `jdk.tracePinnedThreads` property**; the remaining cases are native frames and class
        initialisation, observable via the `jdk.VirtualThreadPinned` JFR event. `[VERSION-TRAP]`
        `[TRAP]` `[RESEARCH]`
2.20.11 **What it does not fix — CPU-bound work.** Loom addresses I/O concurrency, not parallelism.
        Ten thousand virtual threads doing arithmetic are still bounded by your cores. `[PROVE]`
2.20.12 **What it does not fix — downstream capacity.** Unbounded virtual threads mean unbounded
        concurrent DB and HTTP calls; the bottleneck simply moves to the connection pool. "No thread
        limit" **removes an accidental backpressure mechanism**, so you must add explicit limits —
        semaphores, `StructuredTaskScope`, bulkheads, bounded pools. `[TRAP]` `[X-REF 14]`
2.20.13 The `ThreadLocal` caveat with virtual threads: per-thread caches sized for 200 platform
        threads become per-thread caches sized for a million virtual threads. `[TRAP]`
2.20.14 **The positioning statement**: for new Java services, virtual threads make the blocking style
        the sensible default and reduce the reason to reach for Netty/WebFlux to cases needing
        genuine streaming semantics, per-connection efficiency at extreme scale, or an existing
        reactive ecosystem. `[PROVE]`
2.20.15 The comparison table: thread-per-connection, thread-per-request pool, event loop, virtual
        threads — across memory per connection, max practical connections, debuggability,
        backpressure story, and library ecosystem. `[TABLE]`

*(15 leaves)*

## §2.21 The failure catalogue

2.21.1 `java.net.ConnectException: Connection refused` — RST returned; nothing listening. `[DIAG]`
2.21.2 `java.net.SocketTimeoutException: connect timed out` — no SYN-ACK; dropped by a firewall,
       wrong IP, or a full accept queue. `[DIAG]`
2.21.3 `java.net.SocketTimeoutException: Read timed out` — connection established, response too
       slow or the peer went silent. `[DIAG]`
2.21.4 `java.net.SocketException: Connection reset` / `Connection reset by peer` — an RST arrived;
       peer crashed, LB idle timeout, or the peer aborted deliberately. `[DIAG]`
2.21.5 `java.io.IOException: Broken pipe` — you wrote to a connection the peer had already reset;
       classically, the client gave up first. `[DIAG]`
2.21.6 `org.apache.hc.core5.http.NoHttpResponseException` / `The target server failed to respond` —
       the canonical stale-pooled-connection signature (§2.6.4). `[DIAG]`
2.21.7 `java.net.BindException: Cannot assign requested address` — ephemeral port exhaustion
       (§2.10.6). `[DIAG]`
2.21.8 `java.net.BindException: Address already in use` — a different bug: something else holds the
       listening port, or you did not set `SO_REUSEADDR` after a restart. `[DIAG]` `[TRAP]`
2.21.9 `java.net.SocketException: Too many open files` — fd limit (§1.27). `[DIAG]`
2.21.10 `java.net.UnknownHostException` — DNS NXDOMAIN, SERVFAIL, resolver unreachable, or a typo;
        note the JVM negative cache means the failure persists for 10 s after it is fixed.
        `[DIAG]`
2.21.11 `javax.net.ssl.SSLHandshakeException: PKIX path building failed` (§1.24.16),
        `... No subject alternative names matching IP address found` (hostname verification),
        `... Received fatal alert: handshake_failure` (no common cipher/protocol),
        `... Received fatal alert: certificate_unknown`, `... unrecognized_name` (SNI). `[DIAG]`
        `[TABLE]`
2.21.12 `java.net.http.HttpTimeoutException` vs `HttpConnectTimeoutException` in the JDK client.
        `[API]`
2.21.13 `io.netty.channel.StacklessClosedChannelException` and why Netty's exceptions are often
        stackless (performance) — and how to turn stack traces back on for debugging. `[TRAP]`
2.21.14 The 502/503/504 triage table: which component generated it, what to look at first, and how
        to tell an LB-generated error page from an application-generated one. `[TABLE]` `[DIAG]`
2.21.15 The "works in curl, fails in Java" checklist: trust store, SNI, ALPN, HTTP version, proxy
        properties, IPv6 preference, and `Host` header handling. `[TABLE]` `[TRAP]`
2.21.16 The "works locally, fails in the cluster" checklist: DNS `ndots`, security groups/network
        policy, MTU inside the overlay, conntrack limits, egress NAT, and the sidecar's startup
        race. `[TABLE]` `[X-REF 19]`
2.21.17 The intermittent-failure triage procedure: correlate with traffic level (low traffic ⇒ idle
        timeouts; high traffic ⇒ pools/queues/ports), with deploys, with a specific AZ, and with a
        specific instance. `[FLOW]`

*(17 leaves)*

## §2.22 Version history and the stale-answer sweep

2.22.1 The protocol timeline: HTTP/0.9 (1991), HTTP/1.0 (1996, RFC 1945), HTTP/1.1 (1997/1999,
       RFC 2068/2616), SPDY (2009), HTTP/2 (2015, RFC 7540), TLS 1.3 (2018, RFC 8446), QUIC + HTTP/3
       (2021, RFC 9000/9114), the RFC 911x refresh (2022), CUBIC standardised (2023, RFC 9438),
       Extensible Priorities (2022, RFC 9218). `[TABLE]`
2.22.2 The Java timeline for networking: NIO (1.4), NIO.2 async channels (7), `HttpClient` incubator
       (9) and final (11), TLS 1.3 support (11), `InetAddressResolverProvider` (18), Unix domain
       sockets in channels (16), virtual threads preview (19) and final (**21**),
       `synchronized` pinning removed (**24**), Security Manager disallowed (**24**).
       `[TABLE]` `[VERSION-TRAP]` `[RESEARCH]`
2.22.3 The Linux timeline: `epoll` (2.5.44), CUBIC default (2.6.19), `SO_REUSEPORT` (3.9), TFO
       (3.6/3.7), BBR (4.9), `tcp_tw_recycle` **removed** (4.12), RACK-TLP default (4.18),
       `somaxconn` default 4096 (5.4), io_uring (5.1+), kTLS (4.13+). `[TABLE]` `[RESEARCH]`
2.22.4 The seventeen stale answers from the header, restated as a quiz: for each, what the
       out-of-date claim is and what is true in the baseline. `[TABLE]` `[VERSION-TRAP]`

*(4 leaves)*

**PART 2 total: 22 sections, 294 leaves.**

---

# PART 3 — UNDER THE HOOD

PART 2 answered "which one and why". PART 3 answers "what does the machine actually do, in which
function, to which byte". Every leaf here names a real kernel structure, a real JDK class, a real
constant with its value, or a real algorithm with its published name. Nothing in this part may be
written from recall: `[SOURCE]` leaves quote RFC text, Linux kernel documentation
(`Documentation/networking/ip-sysctl.rst`, `net/ipv4/*`), JDK source
(`java.base/sun/nio/ch/**`, `java.net.http/jdk/internal/net/http/**`) or Netty source, and every
number is stated against **Linux 6.x / JDK 21 / the RFCs listed in the header**.

The reader's target after PART 3 is not trivia. It is the ability to answer "why did this happen"
for the five QuizStakes incidents that recur in this domain: `PaymentService` intermittently
resetting against the PSP at low traffic, `ClientRestrictions` breaching its 30 ms budget only
during deploys, `FundsLedger` clients hitting `Cannot assign requested address` at settlement
bursts, `ApplicationGateway` returning 504 while every backend reports healthy, and a request whose
latency is quantised at 40 ms.

## §3.1 How to observe the stack, from the NIC to the JVM

3.1.1 The layered instrument map: `ethtool -S` (NIC counters) → `ip -s link` (driver) →
      `nstat`/`netstat -s` (protocol) → `ss -tin` (per-socket) → `tcpdump` (bytes) →
      `bpftrace` (kernel functions) → JFR/`jcmd` (JVM). Each answers a question the layer above
      cannot. `[TABLE]` `[FLOW]`
3.1.2 `Documentation/networking/ip-sysctl.rst` in the kernel tree as the authoritative source for
      every sysctl default — **this is how you verify a constant instead of trusting a blog**.
      `[SOURCE]` `[PROVE]`
3.1.3 `/proc/net/tcp`, `/proc/net/tcp6`, `/proc/net/sockstat`, `/proc/net/netstat`,
      `/proc/net/snmp` — the raw files behind `ss` and `netstat`, and how to read the state column
      (hex TCP state values). `[DIAG]` `[SOURCE]`
3.1.4 `struct tcp_info` (from `TCP_INFO`) field by field: `tcpi_state`, `tcpi_rto`, `tcpi_ato`,
      `tcpi_snd_mss`, `tcpi_rtt`, `tcpi_rttvar`, `tcpi_snd_cwnd`, `tcpi_snd_ssthresh`,
      `tcpi_total_retrans`, `tcpi_bytes_acked`, `tcpi_delivery_rate`, `tcpi_notsent_bytes`. This is
      exactly what `ss -tin` prints. `[SOURCE]` `[DIAG]`
3.1.5 `bpftrace`/BCC tools by name and what each answers: `tcpconnect`, `tcpaccept`, `tcpretrans`,
      `tcplife`, `tcpdrop`, `tcpsynbl`, `sockstat`, `solisten`. `[DIAG]` `[RESEARCH]`
3.1.6 `perf trace`/`strace -e trace=network -T` for syscall-level timing on one process, and why
      `strace` is too heavy for production but perfect for a staging repro. `[X-REF 11]`
3.1.7 Wireshark analysis features that matter: `tcp.analysis.retransmission`,
      `tcp.analysis.zero_window`, `tcp.analysis.duplicate_ack`, follow-TCP-stream, the IO graph, and
      TLS decryption with `SSLKEYLOGFILE`. `[DIAG]`
3.1.8 **The discipline for this whole part**: a claim about internals is either quoted from source,
      shown with one of these tools, or labelled a guess. In an interview, "I would check
      `ss -tin` for `retrans` and `cwnd`" beats a confidently wrong constant. `[PROVE]`

*(8 leaves)*

## §3.2 The kernel receive path, packet by packet

3.2.1 The full path in order: wire → NIC → DMA into an **RX ring buffer** → hardware interrupt →
      **NAPI** polling in softirq context (`NET_RX_SOFTIRQ`) → `sk_buff` allocation → GRO coalescing
      → protocol handlers (`ip_rcv` → `tcp_v4_rcv`) → socket lookup by 4-tuple → receive queue →
      wake the waiting process → `recvmsg` copies to userspace. `[FLOW]` `[SOURCE]`
3.2.2 **`sk_buff`** as the universal packet structure: `head`/`data`/`tail`/`end` pointers, headroom
      and tailroom, the `skb_shared_info` fragment array, and why cloning is cheap but copying is
      not. `[SOURCE]`
3.2.3 **NAPI**: why the kernel switches from interrupt-per-packet to polling under load, the
      `netdev_budget` (default **300**) and `netdev_budget_usecs` (**2000**) limits, and
      `softnet_stat`'s `time_squeeze` counter as the sign you are exceeding them. `[SYSCTL]`
      `[NUM]` `[DIAG]` `[RESEARCH]`
3.2.4 **The three places a packet is dropped before your code sees it**: the NIC ring buffer
      (`ethtool -S | grep -i drop`, fixed by `ethtool -G rx`), the per-CPU backlog
      (`net.core.netdev_max_backlog`, default **1000**), and the socket receive buffer
      (`tcp_rmem`/`rmem_max`, counted in `netstat -s` as "packets pruned"/"collapsed").
      `[TABLE]` `[SYSCTL]` `[DIAG]`
3.2.5 **RSS / RPS / RFS / XPS**: hardware receive-side scaling across NIC queues, software receive
      packet steering, receive flow steering to the CPU running the consuming application, and
      transmit packet steering. Why flow-to-CPU locality matters for cache hit rate. `[PROVE]`
      `[RESEARCH]`
3.2.6 **Interrupt coalescing** (`ethtool -c`, `rx-usecs`, `rx-frames`): the latency/throughput knob
      that trades microseconds of delay for fewer interrupts. `[NUM]`
3.2.7 **GRO / LRO on receive and TSO / GSO on transmit**: coalescing many MSS-sized segments into
      one large `sk_buff` so the protocol stack runs once per 64 KB instead of once per 1460 bytes.
      This is why `tcpdump` shows impossible 30,000-byte "packets" — you are seeing post-GRO
      aggregates, not wire frames. `[PROVE]` `[TRAP]` `[DIAG]`
3.2.8 Checksum offload (`ethtool -k`) and why `tcpdump` reports "bad checksum" on outgoing packets
      that are perfectly fine. `[TRAP]` `[DIAG]`
3.2.9 The socket lookup: the established hash table and the listening hash table, and how
      `SO_REUSEPORT` groups are selected by a hash of the 4-tuple. `[SOURCE]`
3.2.10 **Socket memory accounting**: `sk_rmem_alloc`/`sk_wmem_alloc`, `net.ipv4.tcp_mem`
       `[low, pressure, high]` in pages, and what "TCP: out of memory -- consider tuning tcp_mem"
       actually means. `[SYSCTL]` `[DIAG]`
3.2.11 `net.core.rmem_max`/`wmem_max` as the ceiling on what `SO_RCVBUF`/`SO_SNDBUF` may request,
       and why setting them explicitly disables autotuning (§1.11.4). `[SYSCTL]`
3.2.12 The transmit path in brief: `sendmsg` → copy into the send buffer → segmentation → `tcp_write_
       xmit` under `cwnd`/`rwnd` → qdisc (`fq`, `fq_codel`, `pfifo_fast`) → driver TX ring → wire.
       `[FLOW]` `[SOURCE]`
3.2.13 **Pacing and `fq`**: why modern TCP paces packets rather than bursting them, and how BBR
       depends on it. `[RESEARCH]`
3.2.14 `tc qdisc` and AQM: `fq_codel` as the default on many distributions, and what CoDel's target
       and interval parameters do to bufferbloat. `[NUM]` `[RESEARCH]`

*(14 leaves)*

## §3.3 The accept path in detail

3.3.1 The two queues in kernel terms: `request_sock_queue` (the SYN queue, holding `request_sock`
      entries) and `icsk_accept_queue` (the accept queue, holding fully established `sock`
      structures). `[SOURCE]`
3.3.2 `listen(fd, backlog)`: `sk_max_ack_backlog = min(backlog, net.core.somaxconn)`; the SYN queue
      is sized from `tcp_max_syn_backlog` and the accept-queue length. `[SOURCE]` `[NUM]`
3.3.3 What happens on SYN when the SYN queue is full: drop (and rely on the client's SYN retry), or
      generate a **SYN cookie** if `tcp_syncookies` allows. `[FLOW]`
3.3.4 What happens on the final ACK when the **accept queue** is full: the ACK is dropped and the
      connection stays in the SYN queue to be retried, unless `tcp_abort_on_overflow=1` sends an
      RST. Counter: `TcpExtListenOverflows`. `[FLOW]` `[SYSCTL]` `[DIAG]`
3.3.5 **SYN cookie construction**: the ISN encodes a timestamp, the MSS index and a keyed hash of
      the 4-tuple, so no state is stored. The cost: window scale, SACK and timestamps are lost
      unless the timestamp option carries them. `[PROVE]` `[TRAP]`
3.3.6 The **thundering herd** on `accept()` with multiple threads/processes on one listening socket,
      and the three answers: the kernel's exclusive wakeup, `EPOLLEXCLUSIVE`, and `SO_REUSEPORT`
      with per-worker sockets. `[PROVE]`
3.3.7 `SO_REUSEPORT`'s load-distribution flaw: the hash is fixed at connection time, so removing a
      worker rehashes existing flows onto the wrong socket unless `SO_REUSEPORT` BPF steering is
      used. `[TRAP]` `[RESEARCH]`
3.3.8 How the JVM reaches this: `ServerSocket(int port, int backlog)`,
      `ServerSocketChannel.bind(SocketAddress, int backlog)`, Tomcat's `acceptCount`, Netty's
      `ChannelOption.SO_BACKLOG`, and the **default of 50** in `ServerSocket` when you omit it.
      `[API]` `[NUM]` `[TRAP]`
3.3.9 **The GC-pause interaction, proved**: a 500 ms stop-the-world pause at 1,200 rps queues 600
      connections; with an accept queue of 100 (Tomcat's default `acceptCount`), 500 clients see a
      connect failure from a process that was never unhealthy. `[CALC]` `[INCIDENT]`
      `[X-REF 06]`
3.3.10 The deploy-time variant: during a rolling restart, a starting JVM's accept queue fills before
       the JIT has warmed up, which is the mechanism behind ALB **slow start** existing at all.
       `[INCIDENT]`

*(10 leaves)*

## §3.4 Congestion control internals

3.4.1 The kernel's pluggable congestion-control interface `struct tcp_congestion_ops`: `ssthresh`,
      `cong_avoid`, `set_state`, `cwnd_event`, `pkts_acked`, `undo_cwnd`. This is how CUBIC, BBR and
      DCTCP coexist. `[SOURCE]`
3.4.2 CUBIC's state in the kernel (`struct bictcp`): `cnt`, `last_max_cwnd`, `bic_origin_point`,
      `bic_K`, `epoch_start`, `ack_cnt`, `tcp_cwnd`, `delay_min`. `[SOURCE]` `[RESEARCH]`
3.4.3 **Deriving K**: at a loss event `W_max = cwnd`, `cwnd ← beta_cubic × W_max` (×0.7), and
      `K = cbrt(W_max × (1 − beta_cubic) / C)`. Work the arithmetic for a concrete `W_max`.
      `[CALC]` `[PROVE]` `[SPEC]`
3.4.4 **The Reno-friendly region computation**: `W_est` grows as Reno would; CUBIC uses
      `max(W_cubic(t), W_est)` so it never underperforms Reno on short/low-BDP paths. `[PROVE]`
      `[SPEC]`
3.4.5 **Fast convergence**: when a new loss event finds `cwnd < W_max_last`, set
      `W_max ← cwnd × (1 + beta_cubic)/2` so an incumbent flow yields to a newcomer. `[PROVE]`
      `[SPEC]` `[RESEARCH]`
3.4.6 **HyStart / HyStart++**: exiting slow start on a delay signal instead of overshooting into
      loss; `net.ipv4.tcp_cubic hystart` module parameters. `[RESEARCH]`
3.4.7 **BBR's model**: maintain `BtlBw` (max delivery rate over a window) and `RTprop` (min RTT over
      a window), set pacing rate to `pacing_gain × BtlBw` and cwnd to `cwnd_gain × BDP`. The four
      states — Startup, Drain, ProbeBW (the gain cycle `[1.25, 0.75, 1, 1, 1, 1, 1, 1]`), ProbeRTT
      (drop cwnd to 4 packets for 200 ms every 10 s). `[NUM]` `[PROVE]` `[RESEARCH]`
3.4.8 Why BBR needs pacing and therefore `fq`, and what BBRv2/v3 changed (ECN response, loss
      response, fairness with CUBIC). `[RESEARCH]` `[VERSION-TRAP]`
3.4.9 **DCTCP** for datacentre networks: ECN-marking proportional response, and why it needs switch
      support and therefore is not an internet algorithm.
3.4.10 The `delivery_rate` estimator (RFC-adjacent, Cheng/Cardwell) and how `ss -tin`'s
       `delivery_rate` is computed. `[RESEARCH]`
3.4.11 Observing the controller: `ss -tin` fields `cwnd`, `ssthresh`, `bytes_sent`, `bytes_retrans`,
       `delivery_rate`, `busy`, `rwnd_limited`, `sndbuf_limited` — and the diagnostic value of
       knowing whether you are cwnd-limited, rwnd-limited or app-limited. `[DIAG]` `[PROVE]`

*(11 leaves)*

## §3.5 Loss recovery internals

3.5.1 The SACK **scoreboard**: how the sender tracks which byte ranges are SACKed, and the
      `tcp_sacktag_write_queue` walk. `[SOURCE]`
3.5.2 The four Linux TCP congestion states: `TCP_CA_Open`, `TCP_CA_Disorder`, `TCP_CA_CWR`,
      `TCP_CA_Recovery`, `TCP_CA_Loss`. `[SOURCE]` `[NUM]`
3.5.3 **RACK** (Recent ACKnowledgement, RFC 8985): a segment is deemed lost if a segment sent later
      has been acknowledged and `now > sent_time + RTT + reorder_window`. Time-based, not
      count-based. `[SPEC]` `[PROVE]`
3.5.4 **TLP** (Tail Loss Probe): before the RTO fires, retransmit the last segment (or send a new
      one) after `PTO = 2 × SRTT` (with a minimum), so tail loss is recovered by fast retransmit
      rather than by RTO. `[NUM]` `[SPEC]` `[PROVE]`
3.5.5 The reordering window and `net.ipv4.tcp_reordering` / adaptive reordering detection via
      DSACK. `[SYSCTL]`
3.5.6 **F-RTO** (`net.ipv4.tcp_frto`) for detecting spurious RTOs and undoing the cwnd reduction.
      `[SYSCTL]`
3.5.7 `tcp_retries1` (**3**, when to start probing the route) and `tcp_retries2` (**15**, when to
      abort) — and the derivation that 15 retries with exponential backoff is roughly **924 s
      (~15 min)**. This is why `TCP_USER_TIMEOUT` exists. `[SYSCTL]` `[NUM]` `[CALC]`
      `[RESEARCH]`
3.5.8 **QUIC's loss detection constants** for contrast (RFC 9002): `kPacketThreshold = 3`,
      `kTimeThreshold = 9/8`, `kGranularity = 1 ms`, `kInitialRtt = 333 ms`,
      `kPersistentCongestionThreshold = 3`, `kInitialWindow = min(10 × max_datagram_size,
      max(14720, 2 × max_datagram_size))`, `kMinimumWindow = 2 × max_datagram_size`,
      `kLossReductionFactor = 0.5`. `[NUM]` `[SPEC]` `[RESEARCH]`
3.5.9 **Why QUIC's loss detection is cleaner than TCP's**: monotonically increasing packet numbers
      remove retransmission ambiguity (so Karn's algorithm is unnecessary), separate packet-number
      spaces per encryption level prevent spurious cross-level retransmission, and receivers may not
      renege on ACKs. `[PROVE]` `[SPEC]` `[RESEARCH]`
3.5.10 QUIC's **PTO** = `smoothed_rtt + max(4 × rttvar, kGranularity) + max_ack_delay`, with
       exponential backoff, replacing both RTO and TLP. `[CALC]` `[SPEC]`

*(10 leaves)*

## §3.6 epoll internals

3.6.1 The three syscalls: `epoll_create1(flags)` returns an fd for a kernel-side interest set;
      `epoll_ctl(epfd, EPOLL_CTL_ADD|MOD|DEL, fd, &event)` mutates it; `epoll_wait(epfd, events,
      maxevents, timeout)` collects ready events. `[SOURCE]` `[API]`
3.6.2 The kernel data structures: an **`eventpoll`** with a red-black tree of registered
      `epitem`s (keyed by fd) and a **ready list** (a doubly-linked list), plus a wait queue for
      blocked callers. `[SOURCE]` `[PROVE]`
3.6.3 **The callback mechanism**: registration installs `ep_poll_callback` on the file's wait
      queue, so when data arrives the driver's wakeup moves the `epitem` onto the ready list. No
      scanning happens at all. `[PROVE]` `[SOURCE]`
3.6.4 **The complexity argument, proved**: `epoll_ctl` is O(log n) on the RB-tree; `epoll_wait` is
      O(number of ready events); `select`/`poll` are O(n) per call because the fd set is re-passed
      and re-scanned every time. State the asymptotics *and* the constant-factor reason (no
      user↔kernel copy of the whole set). `[PROVE]`
3.6.5 **Level-triggered vs edge-triggered** (`EPOLLET`): LT reports readiness as long as data
      remains; ET reports only the transition, so you **must** drain until `EAGAIN` or you will hang
      forever. Netty and nginx use ET; the JDK `Selector` presents LT semantics. `[TRAP]`
      `[PROVE]`
3.6.6 `EPOLLONESHOT` and `EPOLLEXCLUSIVE`, and which thundering-herd problem each solves.
3.6.7 The event flags: `EPOLLIN`, `EPOLLOUT`, `EPOLLERR`, `EPOLLHUP`, `EPOLLRDHUP` (peer closed the
      write half — the flag that lets you detect a half-close without a read). `[NUM]`
3.6.8 **The `EPOLLOUT` discipline**: register for writability only when a write returned short,
      then deregister — otherwise you spin at 100% CPU on a permanently writable socket. A classic
      hand-rolled-event-loop bug. `[TRAP]`
3.6.9 `kqueue` (BSD/macOS) as the equivalent with `kevent` filters, and IOCP (Windows) as a
      **completion**-based rather than readiness-based model — and why that distinction matters for
      the abstraction a portable library must build. `[TABLE]` `[PROVE]`
3.6.10 **The historical `epoll` bugs worth knowing**: the epoll+fork/dup semantics (registration
       follows the open file description, not the fd), and the spurious-wakeup requirement that all
       readiness APIs impose. `[TRAP]`

*(10 leaves)*

## §3.7 io_uring, zero-copy, and kTLS

3.7.1 **io_uring's model**: two shared ring buffers (submission queue and completion queue) mapped
      between userspace and kernel, so batches of operations are submitted and reaped with **zero or
      one syscall**. Completion-based, not readiness-based. `[PROVE]` `[RESEARCH]`
3.7.2 The core calls: `io_uring_setup`, `io_uring_enter`, `io_uring_register`; SQPOLL mode for
      syscall-free submission; fixed buffers and registered files. `[RESEARCH]`
3.7.3 Where io_uring beats epoll for networking (fewer syscalls, batched accept/recv/send, multishot
      accept/recv) and where it does not yet (portability, security-policy restrictions, maturity of
      Java bindings — Netty's `io_uring` transport is still incubating). `[TABLE]`
      `[VERSION-TRAP]` `[RESEARCH]`
3.7.4 **`sendfile`**: copies file→socket entirely in kernel space, avoiding two copies and a
      userspace round trip. `FileChannel.transferTo` maps to it. The constraint: you cannot
      transform the bytes, so it is useless for a dynamically generated or encrypted-in-userspace
      response. `[API]` `[PROVE]`
3.7.5 `splice`, `vmsplice` and pipe-based zero-copy for the proxy case.
3.7.6 `MSG_ZEROCOPY` / `SO_ZEROCOPY` for large sends, and the completion-notification protocol on
      the error queue that makes it correct.
3.7.7 **kTLS**: TLS record encryption performed in the kernel (`setsockopt(SOL_TLS, TLS_TX/TLS_RX)`
      after the handshake completes in userspace), which restores `sendfile` for HTTPS and enables
      NIC crypto offload. Supported by nginx and OpenSSL 3.x; not exposed by the JDK. `[PROVE]`
      `[RESEARCH]`
3.7.8 The copy accounting for one HTTPS response, with and without kTLS/sendfile: how many times the
      bytes cross the user/kernel boundary. `[CALC]` `[PROVE]`
3.7.9 `mmap` + write vs `read` + `write` vs `sendfile` vs io_uring — the four ways to move a file to
      a socket, ranked by copies and syscalls. `[TABLE]` `[CALC]`
3.7.10 Why the JVM cannot use most of this directly, and what Netty's native transports
       (`epoll`, `kqueue`, `io_uring`) do to get closer. `[API]`

*(10 leaves)*

## §3.8 TLS internals

3.8.1 **The record layer**: `ContentType` (handshake 22, application_data 23, alert 21,
      change_cipher_spec 20), legacy version, length, and the AEAD-protected payload. Max plaintext
      **2^14 = 16,384 bytes**; in TLS 1.3 the real content type is hidden inside the encrypted
      payload with padding. `[WIRE]` `[NUM]` `[SPEC]`
3.8.2 **The TLS 1.3 key schedule**, stage by stage: `Early Secret = HKDF-Extract(0, PSK)` →
      `Handshake Secret = HKDF-Extract(Derive-Secret(Early, "derived", ""), ECDHE)` →
      `Master Secret = HKDF-Extract(Derive-Secret(Handshake, "derived", ""), 0)`, with
      `client_handshake_traffic_secret`, `server_handshake_traffic_secret`,
      `client_application_traffic_secret_0`, `server_application_traffic_secret_0`,
      `exporter_master_secret`, `resumption_master_secret` derived by `HKDF-Expand-Label`.
      `[SOURCE]` `[SPEC]` `[PROVE]` `[RESEARCH]`
3.8.3 `HKDF-Expand-Label` and `Derive-Secret` definitions, and the role of the transcript hash in
      binding every derived key to the exact handshake messages seen — which is what makes
      downgrade attacks detectable. `[PROVE]` `[SPEC]`
3.8.4 **`Finished`** as a MAC over the transcript: why it authenticates the whole handshake
      retroactively. `[PROVE]`
3.8.5 **AEAD nonce construction**: a 64-bit sequence number XORed into the per-direction IV, never
      transmitted, and the catastrophic consequence of nonce reuse with GCM. `[PROVE]`
3.8.6 **`KeyUpdate`** and the record-count limits that force rekeying.
3.8.7 The TLS 1.3 **downgrade sentinel** in the last 8 bytes of `ServerHello.random`
      (`DOWNGRD\x01`/`\x00`) — how a 1.3-capable server signals to a 1.3-capable client that a
      downgrade was forced. `[NUM]` `[SPEC]` `[PROVE]` `[RESEARCH]`
3.8.8 **0-RTT anti-replay mechanisms** (RFC 8446 §8): single-use tickets, ClientHello recording, and
      freshness checks — and why none of them is sufficient across a distributed fleet, which is the
      real reason 0-RTT is restricted to idempotent requests. `[PROVE]` `[SPEC]`
3.8.9 **Session tickets**: `NewSessionTicket` contents, ticket lifetime, `ticket_age_add` and the
      obfuscated ticket age used for anti-replay windows; ticket-key rotation across a fleet and
      why a shared ticket key is a forward-secrecy weakening. `[X-REF 13]`
3.8.10 **Certificate compression (RFC 8879)** and why it matters for handshake size on a lossy link.
       `[RESEARCH]`
3.8.11 **PKIX path building (RFC 5280)** as a *search*, not a walk: multiple possible issuers, cross-
       signed roots, name constraints, path-length constraints, key usage and EKU checks, and
       expiration of an intermediate. This is why the Java error says "path **building** failed".
       `[PROVE]` `[SOURCE]`
3.8.12 The cross-signing incident class: the Let's Encrypt **DST Root CA X3 expiry (Sept 2021)**,
       where clients with old trust stores failed while browsers succeeded, is the canonical
       real-world path-building failure. `[INCIDENT]` `[RESEARCH]`
3.8.13 **Certificate Transparency (RFC 6962/9162)**: SCTs delivered in the certificate, in a TLS
       extension, or in OCSP; log structure as a Merkle tree; and Chrome's enforcement.
       `[X-REF 13]`
3.8.14 **JSSE internals**: `SSLEngine` as the codec-only state machine underneath both `SSLSocket`
       and every NIO client, its `wrap`/`unwrap` contract and `HandshakeStatus`
       (`NEED_WRAP`, `NEED_UNWRAP`, `NEED_TASK`, `NOT_HANDSHAKING`, `FINISHED`), and why
       `NEED_TASK` exists (offload expensive crypto off the I/O thread). `[API]` `[SOURCE]`
3.8.15 `SunJSSE` vs the **Conscrypt/BoringSSL** and **netty-tcnative/OpenSSL** providers, and the
       measured handshake-throughput gap that motivates them. `[RESEARCH]`
3.8.16 `jdk.tls.disabledAlgorithms`, `jdk.tls.legacyAlgorithms`, `jdk.certpath.disabledAlgorithms`
       in `java.security` — the properties that silently make a handshake fail after a JDK upgrade.
       `[API]` `[TRAP]` `[INCIDENT]`
3.8.17 Reading `-Djavax.net.debug=ssl,handshake,session` output line by line: ClientHello extension
       list, the negotiated suite, the certificate chain presented, and the exact alert. `[DIAG]`
       `[SOURCE]`
3.8.18 TLS session caching on the server: `SSLSessionContext`, `javax.net.ssl.sessionCacheSize`, and
       why a fleet without a shared cache or shared ticket key gets a full handshake on every LB
       re-route. `[CALC]` `[API]`

*(18 leaves)*

## §3.9 HPACK and QPACK internals

3.9.1 **HPACK's static table**: 61 entries, entry 1 = `:authority`, 2 = `:method GET`, 8 =
      `:status 200`, and so on — a header present in the static table costs **one byte**. `[NUM]`
      `[SPEC]`
3.9.2 **The dynamic table** as a FIFO with an eviction policy bounded by
      `SETTINGS_HEADER_TABLE_SIZE` (default 4096); the entry-size formula **name length + value
      length + 32 bytes** of overhead. `[NUM]` `[SPEC]` `[CALC]`
3.9.3 **Integer encoding with an N-bit prefix** and the continuation-octet scheme; **string
      encoding** with an optional Huffman flag and the static Huffman code. `[WIRE]` `[SPEC]`
3.9.4 The four header representations and when an encoder picks each; the **never-indexed** literal
      for secrets. `[TABLE]` `[SPEC]`
3.9.5 **Why HPACK cannot work over QUIC**: it requires strictly ordered delivery of table mutations,
      which QUIC streams do not provide across streams. `[PROVE]`
3.9.6 **QPACK's solution**: dedicated unidirectional encoder (0x02) and decoder (0x03) streams for
      table mutations, a **Required Insert Count** per field section, and a **Base** for relative
      indexing. `[SPEC]` `[PROVE]` `[RESEARCH]`
3.9.7 **Blocked streams**: a request that references a not-yet-received dynamic entry blocks;
      `SETTINGS_QPACK_BLOCKED_STREAMS` bounds how many. The encoder chooses the compression /
      HOL-blocking trade-off explicitly. `[PROVE]` `[NUM]`
3.9.8 The compression-ratio arithmetic for a QuizStakes request set (JWT `authorization` header,
      `traceparent`, `content-type`, `user-agent`) across 100 requests, HPACK vs uncompressed.
      `[CALC]`
3.9.9 The DoS surface: an attacker-controlled header that poisons the dynamic table, and the
      `CONTINUATION` flood. `[X-REF 13]`

*(9 leaves)*

## §3.10 QUIC internals

3.10.1 The **invariants (RFC 8999)**: the only fields future versions must keep — long/short header
       bit, version field, connection ID lengths. Everything else is encrypted, which is the
       deliberate **anti-ossification** design. `[PROVE]` `[SPEC]`
3.10.2 **Header protection**: even the packet number is encrypted with a separate header-protection
       key derived from the traffic secret, so middleboxes cannot parse or track it. `[PROVE]`
       `[SPEC]`
3.10.3 **Packet-number spaces**: Initial, Handshake, Application — each with its own number space
       and its own ACK state. `[SPEC]`
3.10.4 **Coalesced packets**: multiple QUIC packets of different encryption levels in one UDP
       datagram, which is how the handshake fits in a single flight. `[WIRE]`
3.10.5 The `STREAM` frame's fields (stream ID, offset, length, FIN bit) and how a byte stream is
       reassembled per stream. `[WIRE]`
3.10.6 **Variable-length integer encoding** (2-bit prefix selecting 1/2/4/8 bytes, max 2^62−1) used
       for every field in QUIC. `[WIRE]` `[NUM]` `[SPEC]`
3.10.7 **Flow control accounting**: connection-level `MAX_DATA` counts the sum of final offsets
       across all streams, so a peer that opens many streams cannot bypass the connection limit.
       `[PROVE]` `[SPEC]`
3.10.8 The **anti-deadlock rule**: a blocked sender is not required to send `DATA_BLOCKED`, so a
       receiver must not wait for one before extending credit. A real interop bug class.
       `[SPEC]` `[TRAP]` `[RESEARCH]`
3.10.9 **Connection-ID rotation** for privacy: `NEW_CONNECTION_ID`/`RETIRE_CONNECTION_ID`, the
       `active_connection_id_limit`, and why a load balancer must be able to route by CID
       (server-chosen CIDs encoding a routing key — the QUIC-LB design). `[PROVE]` `[RESEARCH]`
3.10.10 **Stateless reset tokens** and how they let a restarted server terminate connections it no
        longer knows about, without holding state. `[SPEC]`
3.10.11 **The UDP performance problem**: per-datagram syscall cost. The fixes — `sendmmsg`/`recvmmsg`,
        UDP GSO/GRO (`UDP_SEGMENT`), and `SO_REUSEPORT` sharding — and why QUIC's CPU cost fell
        substantially once these landed. `[PROVE]` `[RESEARCH]`
3.10.12 **`qlog`/`qvis`** as the QUIC equivalent of a packet capture, since `tcpdump` cannot read
        encrypted QUIC headers. `[DIAG]` `[RESEARCH]`
3.10.13 QUIC datagrams (RFC 9221) for unreliable payloads inside a reliable connection, and what
        WebTransport builds on them. `[RESEARCH]`

*(13 leaves)*

## §3.11 JDK networking internals

3.11.1 The class chain for a blocking socket in JDK 21: `Socket` → `SocketImpl` →
      **`NioSocketImpl`** (which replaced the old `PlainSocketImpl` in JDK 13, JEP 353) → `Net` →
      native. The reimplementation exists specifically so sockets could later be made
      virtual-thread-friendly. `[SOURCE]` `[API]` `[VERSION-TRAP]` `[RESEARCH]`
3.11.2 **JEP 353 (Reimplement the Legacy Socket API)** and **JEP 373 (DatagramSocket API)** as the
      prerequisite work for Loom. `[RESEARCH]`
3.11.3 `sun.nio.ch.Net`, `sun.nio.ch.IOUtil`, `sun.nio.ch.NativeThread` — where the JDK actually
      issues `read`/`write`/`connect`. `[SOURCE]`
3.11.4 **`Selector` implementations by platform**: `EPollSelectorImpl` (Linux),
      `KQueueSelectorImpl` (macOS/BSD), `WEPollSelectorImpl` (Windows, JDK 13+). `[SOURCE]`
      `[API]`
3.11.5 The `Selector` mechanics: `selectedKeys` must be **removed by the iterator** or the key is
      reported again forever — the single most common hand-rolled-NIO bug. `[TRAP]` `[API]`
3.11.6 **The epoll spin bug** (JDK-6670302): a `Selector` waking with zero ready keys in a tight
      loop, burning a core. Netty's famous workaround is to count consecutive empty selects
      (`SELECTOR_AUTO_REBUILD_THRESHOLD`, default **512**) and rebuild the selector. `[INCIDENT]`
      `[NUM]` `[SOURCE]` `[RESEARCH]`
3.11.7 **The JDK 21 `Poller`** (`sun.nio.ch.Poller`, `PollerProvider`): the per-JVM I/O poller that
      parks virtual threads on socket readiness. Its modes — one poller per JVM vs per carrier —
      are controlled by `jdk.pollerMode`, and `Poller.pollerCount` scales with cores. This is the
      concrete answer to "how do virtual threads do non-blocking I/O without you writing
      non-blocking code". `[SOURCE]` `[API]` `[RESEARCH]`
3.11.8 The unmount path for a socket read on a virtual thread, traced: `SocketInputStream.read` →
      `NioSocketImpl.tryRead` returns `IOStatus.UNAVAILABLE` → `Poller.poll(fd, event)` →
      `VirtualThread.park` → continuation copied to the heap → carrier freed → readiness event →
      `unpark` → remount → retry the read. `[FLOW]` `[PROVE]` `[SOURCE]`
3.11.9 **Continuation representation**: the stack chunk on the heap, `StackChunk` objects, and why
      stack depth affects mount/unmount cost. `[X-REF 06]` `[X-REF 04]`
3.11.10 **Pinning implementation**: on JDK 21 a `synchronized` monitor is owned by the *carrier*, so
        unmounting would break monitor ownership — hence the pin. JEP 491 (JDK 24) makes the monitor
        owned by the virtual thread. `[PROVE]` `[VERSION-TRAP]` `[RESEARCH]`
3.11.11 `java.net.http.HttpClient` architecture: `HttpClientImpl` with a single `SelectorManager`
        thread, `Http1Exchange`/`Http2Connection`, `ConnectionPool` keyed by
        (origin, proxy, protocol), `Http2ClientImpl`, `WindowController`, and the `Flow.Publisher`/
        `Flow.Subscriber` body pipeline. `[SOURCE]` `[API]` `[RESEARCH]`
3.11.12 Why the JDK client's single selector thread matters: all I/O demultiplexing for the client
        runs on it, and a blocking `BodyHandler` can stall every in-flight request on that client.
        `[TRAP]`
3.11.13 `jdk.internal.net.http.common.Utils` and the `jdk.httpclient.*` property read points — how to
        confirm a property is actually honoured rather than assumed. `[SOURCE]`
3.11.14 `InetAddress`'s cache implementation (`InetAddress$NameServiceAddresses`, the
        `CachedLocalHost` entry) and where the TTL is applied. `[SOURCE]`
3.11.15 JFR events for networking: `jdk.SocketRead`, `jdk.SocketWrite` (with the
        `threshold`/`bytesRead` fields), `jdk.TLSHandshake`, `jdk.X509Validation`,
        `jdk.VirtualThreadPinned`, `jdk.VirtualThreadSubmitFailed`. `[DIAG]` `[API]`
        `[RESEARCH]`

*(15 leaves)*

## §3.12 Netty internals

3.12.1 The object model: `EventLoopGroup` → `EventLoop` (one thread + one `Selector`) → `Channel` →
       `ChannelPipeline` → `ChannelHandlerContext` → `ChannelHandler`. `[SOURCE]` `[API]`
3.12.2 **The single-threaded-per-channel guarantee**: all handlers for a channel run on that
       channel's event loop, so handler state needs no synchronisation — the design's central
       simplification. `[PROVE]`
3.12.3 The boss/worker split (`bossGroup` accepting, `workerGroup` handling) and why the default
       worker count is `2 × availableProcessors` (`io.netty.eventLoopThreads`). `[NUM]`
3.12.4 `ByteBuf` vs `ByteBuffer`: separate reader and writer indices, reference counting, pooled vs
       unpooled, heap vs direct, and composite buffers for zero-copy concatenation. `[API]`
       `[PROVE]`
3.12.5 **`ByteBuf` reference counting and the leak detector**: `ReferenceCountUtil.release`, the
       four `io.netty.leakDetection.level` settings (DISABLED, SIMPLE, ADVANCED, PARANOID), and why
       a leak shows up as native-memory growth rather than a heap OOM. `[TRAP]` `[X-REF 06]`
3.12.6 **`PooledByteBufAllocator`**: arenas, chunks (default 16 MB), pages (8 KB), subpages, and
       thread-local caches — a jemalloc-style allocator inside the JVM, and the source of
       `io.netty.maxDirectMemory` accounting. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.12.7 The codec framework: `ByteToMessageDecoder` and its cumulator, `MessageToByteEncoder`,
       `LengthFieldBasedFrameDecoder` (the concrete answer to §1.7.11), `DelimiterBasedFrameDecoder`,
       `LineBasedFrameDecoder`. `[API]`
3.12.8 **Backpressure in Netty**: `Channel.isWritable()`, the write buffer high/low watermarks
       (defaults **64 KB / 32 KB**), and `channelWritabilityChanged` — the mechanism you must use or
       a fast producer OOMs the server. `[NUM]` `[TRAP]` `[PROVE]`
3.12.9 `ChannelFuture`, `ChannelPromise`, and why every Netty operation is asynchronous including
       `close()`.
3.12.10 Native transports: `EpollEventLoopGroup`, `KQueueEventLoopGroup`, `IOUringEventLoopGroup`,
        and the extra options they expose (`EpollChannelOption.TCP_FASTOPEN`, `SO_REUSEPORT`,
        `TCP_QUICKACK`). `[API]`
3.12.11 `netty-tcnative` / OpenSSL `SslContext` vs JDK `SSLEngine`, and the handshake-throughput
        difference. `[RESEARCH]`
3.12.12 `FastThreadLocal` and `Recycler` as the allocation-avoidance machinery, and why they matter
        at millions of messages per second.
3.12.13 What sits on Netty in a typical Java stack: Reactor Netty (Spring WebFlux's default server
        and `WebClient`), gRPC-java, Cassandra/Elasticsearch drivers, Redis clients (Lettuce),
        Vert.x. Understanding Netty is understanding half the ecosystem's I/O. `[TABLE]`
3.12.14 **Blocking on the event loop** in a Reactor Netty application: `BlockHound` as the detector,
        `publishOn(Schedulers.boundedElastic())` as the offload, and the symptom (throughput
        collapses to the number of event-loop threads). `[TRAP]` `[INCIDENT]`

*(14 leaves)*

## §3.13 Servlet-container and Spring internals on the wire

3.13.1 Tomcat's NIO connector architecture: `Acceptor` thread → `Poller` (a `Selector`) →
       `SocketProcessor` on the executor → `Http11Processor` → the servlet. Where each configured
       limit applies. `[SOURCE]` `[FLOW]`
3.13.2 `maxConnections` (**8192** for NIO) vs `maxThreads` (**200**) vs `acceptCount` (**100**) —
       three different queues, and the arithmetic of what happens at each boundary. `[NUM]`
       `[CALC]` `[TRAP]`
3.13.3 Tomcat's `keepAliveTimeout` and `maxKeepAliveRequests` (**100**): the connection is closed
       after 100 requests by default, which quietly gives an L4 balancer a rebalancing opportunity.
       `[NUM]`
3.13.4 The async servlet path (`AsyncContext`, `startAsync`, `spring.mvc.async.request-timeout`) and
       how it decouples the request from the thread — the pre-Loom answer to long polling and SSE.
       `[API]`
3.13.5 **Virtual threads in Boot 3.2+**: `spring.threads.virtual.enabled=true` swaps the Tomcat
       executor for `VirtualThreadPerTaskExecutor`, so `maxThreads` stops being the concurrency
       limit — and you must add explicit limits elsewhere (§2.20.12). `[API]` `[VERSION-TRAP]`
       `[TRAP]` `[RESEARCH]`
3.13.6 Undertow and Jetty contrasts in one paragraph each (XNIO worker model; Jetty 12's
       `EE10`/core split and its virtual-thread support).
3.13.7 Reactor Netty's `HttpClient` internals as used by `WebClient`: `ConnectionProvider`
       (`maxConnections` default `max(availableProcessors, 8) * 2`, `pendingAcquireMaxCount`,
       `pendingAcquireTimeout` **45 s**, `maxIdleTime`, `maxLifeTime`, `evictInBackground`).
       `[NUM]` `[API]` `[RESEARCH]`
3.13.8 `ClientHttpRequestFactory` implementations and exactly which timeouts each supports — the
       table that explains why "I set the timeout and it did nothing". `[TABLE]` `[API]`
3.13.9 `ForwardedHeaderFilter` / `RemoteIpValve` implementation: which headers are consumed, the
       `internalProxies` regex default, and what `server.forward-headers-strategy=native` delegates
       to the container. `[SOURCE]` `[API]`
3.13.10 Graceful shutdown implementation: `server.shutdown=graceful`,
        `spring.lifecycle.timeout-per-shutdown-phase` (**30 s**), and the required sequencing with
        the LB's deregistration delay (§2.12.10). `[NUM]` `[API]` `[FLOW]`

*(10 leaves)*

## §3.14 Container and cluster networking internals

3.14.1 Network namespaces, **veth pairs**, and the Linux bridge: what `docker0` actually is and what
       happens to a packet leaving a container. `[FLOW]` `[X-REF 19]`
3.14.2 The four Docker network drivers (`bridge`, `host`, `none`, `overlay`) and the port-publishing
       DNAT rule that `-p 8080:8080` installs. `[X-REF 19]`
3.14.3 **conntrack** as the state table behind both NAT and stateful filtering; `nf_conntrack_max`
       sizing on a container host, and the DNAT race condition (a known Kubernetes packet-loss bug
       with `--random-fully` as the mitigation). `[INCIDENT]` `[RESEARCH]`
3.14.4 Kubernetes' networking model requirements: every pod gets a routable IP, pods communicate
       without NAT, and nodes can reach all pods. Why that constraint drives every CNI design.
       `[PROVE]` `[X-REF 19]`
3.14.5 **kube-proxy** modes: `iptables` (a linear chain of DNAT rules, O(n) rule evaluation),
       `ipvs` (hash-based, scales to thousands of services), and `nftables`/eBPF replacements
       (Cilium). What each programs and what each costs at 5,000 services. `[TABLE]` `[CALC]`
3.14.6 **ClusterIP is a virtual IP with no listener** — it exists only as a DNAT rule, which is why
       you cannot ping it and why `tcpdump` on the node shows the pod IP, not the service IP.
       `[TRAP]` `[PROVE]`
3.14.7 CoreDNS in the cluster: the `Corefile`, the `kubernetes` plugin, the cache plugin's default
       TTL (**30 s**), and `NodeLocal DNSCache` as the fix for DNS latency and conntrack pressure.
       `[NUM]` `[RESEARCH]`
3.14.8 The `ndots:5` mechanism restated at implementation level (§1.16.12), with the exact query
       sequence a pod issues for `psp.vendor.com`. `[FLOW]` `[CALC]`
3.14.9 **MTU inside an overlay**: VXLAN's 50-byte overhead means a 1500-byte pod MTU on a 1500-byte
       node MTU silently fragments or blackholes. Symptom: small requests work, large ones hang —
       the §1.4.10 incident, inside a cluster. `[INCIDENT]` `[CALC]`
3.14.10 **Service mesh data path**: an `iptables`/eBPF redirect into an Envoy sidecar, the extra two
        hops per request, mTLS termination in the sidecar, and the startup race where the app makes
        a call before the sidecar is ready (`holdApplicationUntilProxyStarts`). `[INCIDENT]`
        `[X-REF 19]`
3.14.11 eBPF-based networking (Cilium) as the model that removes iptables and can bypass the host
        stack for pod-to-pod traffic; XDP for line-rate filtering. `[RESEARCH]`
3.14.12 Where the cloud's own SDN sits underneath all of this: ENIs, security groups as stateful
        distributed firewalls, and the per-instance packet-per-second and flow limits that produce
        `bw_in_allowance_exceeded` / `conntrack_allowance_exceeded` in ENA metrics. `[NUM]`
        `[X-REF 18]` `[RESEARCH]`

*(12 leaves)*

## §3.15 Five incidents, traced end to end

3.15.1 **Incident A — the low-traffic reset.** `PaymentService` sees 0.4% `NoHttpResponseException`
       against the PSP, only outside peak hours. Trace: pooled connection idle 70 s → ALB idle
       timeout 60 s → FIN unobserved by the pool → write onto a closed socket. Fix: client idle
       25 s, plus retry-on-idle-failure for idempotent calls. `[INCIDENT]` `[FLOW]`
3.15.2 **Incident B — the 30 ms budget breached only during deploys.** `ClientRestrictions` p99 goes
       to 900 ms for 40 s after each rollout. Trace: new pods join, clients open new connections,
       every one pays DNS + TCP + TLS + slow start, and `tcp_slow_start_after_idle` resets the
       window on the survivors. Fix: pre-warm, connection `maxLifetime` staggering, slow start on
       the target group. `[INCIDENT]` `[FLOW]` `[CALC]`
3.15.3 **Incident C — `Cannot assign requested address` at settlement bursts.** A client library
       constructed per call created a new pool per request; at 3,400/sec the ephemeral range was
       consumed in under 10 s. Trace via §2.10.5's arithmetic. Fix: singleton client, then
       `tcp_tw_reuse`. `[INCIDENT]` `[CALC]`
3.15.4 **Incident D — 504 at the gateway with every backend healthy.** Trace: `ApplicationGateway`
       read timeout 3 s; the backend's own downstream timeout was 5 s; the backend was still working
       on requests nobody was waiting for, consuming its thread pool, so *new* requests queued.
       The budget inversion of §2.7.7 is the root cause. `[INCIDENT]` `[PROVE]`
3.15.5 **Incident E — latency quantised at 40 ms.** Trace: a client writing headers and body in two
       `write()` calls, Nagle on the sender, delayed ACK on the receiver (§1.13.3). Fix: single
       gathered write. `[INCIDENT]` `[DIAG]`
3.15.6 The common structure of all five: **a timer on one side and a different timer on the other,
       or a resource whose limit nobody computed.** State it as the generalisation. `[PROVE]`

*(6 leaves)*

**PART 3 total: 15 sections, 170 leaves.**

---

# PART 4 — BUILD IT

Every item here is a complete, compiling **Java 21** artifact (or a complete runnable config/shell
session where that is the artifact), followed by a **Diff vs the real one** table. The point is not
to ship these; it is that having written one, you can never again be vague about the mechanism.
All examples use the QuizStakes domain.

## §4.1 A length-prefixed framing codec over raw TCP `[BUILD]`

4.1.1 A `FrameCodec` writing `[4-byte big-endian length][payload]` and a reader that loops until the
      full frame is present — the concrete refutation of "one read = one message" (§1.7.10).
4.1.2 The reader must handle: partial length prefix, partial payload, multiple frames in one read,
      a frame spanning many reads, EOF mid-frame, and a **maximum frame size** guard (an
      unbounded length prefix is a memory-exhaustion vulnerability).
4.1.3 A blocking `ReserveStakeServer` and client exchanging framed JSON, plus a deliberate test that
      splits a frame across two `write()` calls with a sleep between them to prove the point.
4.1.4 A delimiter-based variant (`\r\n`) and the buffer-scan state machine it requires.
4.1.5 **Diff vs the real one** (Netty `LengthFieldBasedFrameDecoder`): configurable
      `lengthFieldOffset`/`lengthFieldLength`/`lengthAdjustment`/`initialBytesToStrip`, cumulative
      buffer with `ByteBuf` slices instead of copies, `TooLongFrameException` with fail-fast
      discard mode, reference counting, and zero-copy composite buffers. `[TABLE]`

*(5 leaves)*

## §4.2 Three HTTP/1.1 servers: blocking, NIO-selector, virtual-thread `[BUILD]`

4.2.1 Version 1 — thread-per-connection with `ServerSocket` + a platform-thread executor: parse the
      request line and headers, dispatch, write a response with `Content-Length`, honour
      `Connection: keep-alive`.
4.2.2 Version 2 — a single-threaded `Selector` event loop: `ServerSocketChannel` in non-blocking
      mode, `OP_ACCEPT`/`OP_READ`/`OP_WRITE`, per-connection state objects attached to the
      `SelectionKey`, correct **iterator removal** of `selectedKeys` (§3.11.5), and the
      register-for-`OP_WRITE`-only-when-needed discipline (§3.6.8).
4.2.3 Version 3 — the identical blocking code of version 1 running on
      `Executors.newVirtualThreadPerTaskExecutor()`, demonstrating that the source is unchanged and
      the scalability is not.
4.2.4 A measurement harness: 10,000 concurrent idle connections against each, reporting RSS, thread
      count and accept latency, so the memory arithmetic of §2.1.5 is observed, not asserted.
      `[CALC]`
4.2.5 A `synchronized`-block pinning demonstration on JDK 21 with `-Djdk.tracePinnedThreads=full`,
      and the note that this specific demo no longer pins on JDK 24. `[VERSION-TRAP]`
4.2.6 **Diff vs the real one** (Tomcat / Netty): HTTP parsing hardened against smuggling and header
      injection, chunked encoding, `Expect: 100-continue`, pipelining, keep-alive accounting,
      `maxHttpHeaderSize` enforcement, backpressure via watermarks, TLS via `SSLEngine`, HTTP/2
      upgrade, and graceful shutdown. `[TABLE]`

*(6 leaves)*

## §4.3 A connection pool `[BUILD]`

4.3.1 A generic `ConnectionPool<T>` with max-total and max-per-route limits, a bounded acquisition
      queue with a **timeout**, idle eviction, max lifetime, and validate-on-borrow.
4.3.2 The state machine per entry (idle → leased → returned → evicted) and the invariant tests that
      prove no connection is leased twice and none is leaked on an exception path.
4.3.3 Metrics: available / leased / pending / acquisition-wait histogram (§2.5.12).
4.3.4 A test that reproduces **pool exhaustion** and shows the difference between "downstream is
      slow" and "we are queued at the pool" in the metrics.
4.3.5 A test that reproduces the **stale-connection** failure of §2.6.3 with a server that closes
      idle sockets after 1 s.
4.3.6 **Diff vs the real one** (Apache HttpClient 5 `PoolingHttpClientConnectionManager`, HikariCP):
      per-route routing including proxy and TLS context, `validateAfterInactivity`, connection
      keep-alive strategy from the `Keep-Alive` response header, lock-free concurrent bag (Hikari),
      housekeeping thread, JMX exposure, and leak detection. `[TABLE]`

*(6 leaves)*

## §4.4 A retry executor with backoff, jitter and a budget `[BUILD]`

4.4.1 A `RetryPolicy` record (max attempts, base delay, max delay, multiplier, jitter strategy,
      retryable-exception predicate, retryable-status predicate) and an executor that applies it.
4.4.2 The three jitter strategies implemented and compared by simulation: none, full jitter,
      decorrelated jitter — with a histogram of retry arrival times proving the herd. `[CALC]`
4.4.3 A **retry budget** as a token bucket over the last N seconds, rejecting retries above a 10%
      ratio, with a test showing it caps amplification during a total outage. `[PROVE]`
4.4.4 `Retry-After` honouring (both delta-seconds and HTTP-date forms).
4.4.5 Integration with a total deadline so retries cannot exceed the caller's budget (§2.8.12).
4.4.6 **Diff vs the real one** (Resilience4j `Retry`, Spring Retry, gRPC retry policy): event
      publishing, metrics, async support, integration with the circuit breaker's state, per-method
      configuration, and `hedging` as a separate policy. `[TABLE]`

*(6 leaves)*

## §4.5 A circuit breaker `[BUILD]`

4.5.1 A three-state breaker with a **time-based sliding window** of buckets, a failure-rate
      threshold, a slow-call-rate threshold, a minimum-calls guard, and half-open probe limiting.
4.5.2 The concurrency design: why the window must be updated without a global lock, and how
      `LongAdder`-style striping or a ring of atomic buckets achieves it. `[X-REF 05]`
4.5.3 A test that trips the breaker at the QuizStakes PSP failure signature and verifies the
      half-open probe behaviour.
4.5.4 A demonstration of the `minimumNumberOfCalls` trap (§2.9.4) on a low-traffic endpoint.
4.5.5 **Diff vs the real one** (Resilience4j `CircuitBreaker`): count-based and time-based windows,
      `recordExceptions`/`ignoreExceptions`, `FORCED_OPEN`/`DISABLED` states, event stream, metrics,
      and the `Decorators` composition order. `[TABLE]`

*(5 leaves)*

## §4.6 A DNS resolver over UDP, with EDNS(0) `[BUILD]`

4.6.1 Encode a DNS query message by hand (header flags, QNAME label encoding, QTYPE, QCLASS), send
      it over `DatagramChannel`, and decode the answer including **name compression pointers**
      (the 0xC0 prefix).
4.6.2 Add an OPT pseudo-RR advertising a 1232-byte payload size, and handle the **TC bit** by
      retrying over TCP with the 2-byte length prefix.
4.6.3 Honour the TTL in a small local cache, and cache NXDOMAIN using the SOA MINIMUM (§1.16.10).
4.6.4 Query an HTTPS RR (type 65) and parse the `alpn` SvcParam — proving §1.17.4 rather than
      quoting it.
4.6.5 A timeout and retry policy matching `resolv.conf` semantics.
4.6.6 **Diff vs the real one** (`dnsjava`, Netty `DnsNameResolver`, glibc): EDNS option handling,
      DNSSEC validation, DoT/DoH transports, `/etc/hosts` and NSS integration, search-domain
      expansion, Happy Eyeballs integration, and connection reuse for TCP. `[TABLE]`

*(6 leaves)*

## §4.7 A WebSocket server: handshake and framing `[BUILD]`

4.7.1 Implement the opening handshake: validate `Upgrade`/`Connection`/`Sec-WebSocket-Version: 13`,
      compute `Sec-WebSocket-Accept` = base64(SHA-1(key + the RFC 6455 GUID)), and return `101`.
4.7.2 Implement frame parsing for all three payload-length encodings and all six opcodes, including
      **unmasking** client frames and rejecting unmasked ones.
4.7.3 Implement fragmentation reassembly and control-frame interleaving, enforcing the 125-byte
      control-frame limit.
4.7.4 Implement ping/pong heartbeats and the closing handshake with a proper close code.
4.7.5 A broadcast test proving the §2.17.16 problem: two server instances, a client on each, and a
      message that does not cross — then the same test with a Redis pub/sub backplane.
      `[X-REF 15]`
4.7.6 **Diff vs the real one** (Netty `WebSocketServerProtocolHandler`, Tomcat's JSR-356): UTF-8
      validation on text frames, `permessage-deflate`, subprotocol negotiation, max-frame and
      max-message limits, backpressure, origin checking, and per-session concurrency guarantees.
      `[TABLE]`

*(6 leaves)*

## §4.8 An SSE endpoint and a resilient client `[BUILD]`

4.8.1 A Spring `SseEmitter` (and a `Flux<ServerSentEvent<Stake>>` variant) publishing QuizStakes
      settlement events with `id:`, `event:`, `data:` and periodic `:heartbeat` comments.
4.8.2 A hand-written client over `HttpClient` with `BodyHandlers.ofLines()` that parses the stream
      per the WHATWG rules, tracks the last event ID, and reconnects with `Last-Event-ID` and
      jittered backoff.
4.8.3 A demonstration of proxy buffering breaking the stream, and the `X-Accel-Buffering: no` /
      `proxy_buffering off` fix. `[INCIDENT]`
4.8.4 **Diff vs the real one** (browser `EventSource`, Spring's `WebFlux` SSE): automatic
      reconnection with the server-supplied `retry`, `withCredentials`, BOM handling, the
      readyState machine, and CORS integration. `[TABLE]`

*(4 leaves)*

## §4.9 An HTTP/2 frame parser and a minimal client handshake `[BUILD]`

4.9.1 Emit the 24-byte connection preface plus a SETTINGS frame over a TLS connection negotiated
      with ALPN `h2` (`SSLParameters.setApplicationProtocols`).
4.9.2 Parse the 9-byte frame header and dispatch on type; implement SETTINGS/SETTINGS-ACK, PING/
      PING-ACK, WINDOW_UPDATE accounting, and GOAWAY handling.
4.9.3 Implement HPACK **decoding** for the static table and indexed representations (enough to read
      a `:status 200`), and explain why full HPACK requires the dynamic table and Huffman decoding.
4.9.4 Demonstrate multiplexing by issuing three concurrent requests on one connection and logging
      the interleaved frame order. `[WIRE]`
4.9.5 **Diff vs the real one** (JDK `Http2Connection`, Netty's HTTP/2 codec): full HPACK with
      Huffman, flow-control windows on both levels, stream-state validation, CONTINUATION handling,
      priority/Extensible Priorities, error handling per RFC 9113 §5.4, and the Rapid-Reset
      mitigation. `[TABLE]`

*(5 leaves)*

## §4.10 Diagnostic harnesses `[BUILD]`

4.10.1 A `curl`-equivalent timing tool in Java measuring DNS, connect, TLS, first byte and total,
       so §1.29.4's breakdown is reproducible from inside the JVM. `[CALC]`
4.10.2 A port-exhaustion reproducer: open and close N connections per second without pooling, and
       watch `TIME_WAIT` climb until `BindException`. `[INCIDENT]`
4.10.3 A stale-connection reproducer: a server that closes idle connections after 1 s against a
       client pool with a 5 s idle timeout, producing the §2.6.4 signature on demand.
4.10.4 An accept-queue reproducer: a server that sleeps instead of accepting, with `ss -lnt` output
       showing `Recv-Q` climbing to `Send-Q` and `nstat` showing `ListenOverflows`. `[DIAG]`
4.10.5 A Nagle/delayed-ACK reproducer producing the 40 ms quantisation, and the one-line fix.
       `[INCIDENT]`
4.10.6 A TLS chain inspector using `X509TrustManager` + `SSLSession.getPeerCertificates()` that
       prints the presented chain, the trust anchors, and exactly which link is missing —
       a `PKIX path building failed` explainer. `[DIAG]`
4.10.7 A `tcpdump` + Wireshark walkthrough of one complete `ReserveStake` call over TLS 1.3,
       annotated packet by packet, with `SSLKEYLOGFILE` decryption enabled. `[WIRE]` `[DIAG]`

*(7 leaves)*

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The question bank

5.1.1 **The opener**: "What happens when you type a URL and press enter?" — the full §1.28 pipeline,
      with the cache stack and a failure mode named at each stage. Answer it as a pipeline, not a
      list. `[FLOW]`
5.1.2 "TCP vs UDP" — and the follow-ups that separate levels: what does TCP actually guarantee, why
      is UDP not simply faster, what does QUIC change, and when would *you* pick UDP.
5.1.3 "Walk me through the three-way handshake" → "why three?" → "what is in the SYN besides the
      sequence number?" → "what happens if the accept queue is full?"
5.1.4 "Why does a TCP connection close in four packets?" → "who ends up in `TIME_WAIT`?" → "why
      does `TIME_WAIT` exist?" → "how would you fix ephemeral port exhaustion?"
5.1.5 "You see thousands of `CLOSE_WAIT` sockets. What is wrong?" (Answer: your application is not
      calling `close()`. It is an fd leak, not a network problem.)
5.1.6 "Your service intermittently gets `Connection reset by peer`, about 0.3% of calls, mostly at
      night. Diagnose it." (The §2.6.3 idle-timeout mismatch.)
5.1.7 "Explain HTTP/2 multiplexing" → "does it eliminate head-of-line blocking?" (No — HTTP-layer
      yes, TCP-layer no) → "what does HTTP/3 do about it?" → "what does HTTP/3 cost?"
5.1.8 "You migrated REST to gRPC behind an NLB and one pod is now taking all the traffic. Why?"
      (§2.2.22.)
5.1.9 "How many timeouts are in an HTTP call?" (Six. §2.7.1.) → "which one do people forget?"
      (Pool acquisition.) → "what are Java's defaults?" (Infinite.)
5.1.10 "Your downstream hangs. Walk me through what happens to your service over the next 60
       seconds." (§2.7.5, with the arithmetic.)
5.1.11 "How would you set a timeout for a dependency whose p50 is 900 ms and p99 is 38 s?"
       (The QuizStakes identity-vendor question — the correct answer is to change the interaction.)
5.1.12 "Design a retry policy." → backoff, jitter, budget, idempotency, one layer only, circuit
       breaker, and the 27× amplification arithmetic.
5.1.13 "Explain TLS." → three goals, asymmetric bootstraps symmetric, ECDHE and forward secrecy,
       chain validation, SNI, ALPN, 1 RTT vs 2 RTT, and 0-RTT's replay hazard.
5.1.14 "What does `PKIX path building failed` mean and how do you fix it?"
5.1.15 "Your service resolves a database endpoint once and never notices a failover. Why?"
       (JVM DNS cache. §1.19.5.)
5.1.16 "Why can't you put a CNAME at the apex?" → "what do you do instead?" (ALIAS, or the HTTPS RR
       in AliasMode.)
5.1.17 "L4 vs L7 load balancing — what actually differs?" (Connection vs request. Then all the
       consequences.)
5.1.18 "Where does TLS terminate in your architecture, and what is unencrypted?"
5.1.19 "Explain C10K." → thread-per-connection cost → `select`/`poll` O(n) → epoll's persistent
       interest set and ready list → event loops → virtual threads → what Loom does *not* fix.
5.1.20 "Level-triggered vs edge-triggered epoll — what breaks if you get it wrong?"
5.1.21 "SSE or WebSocket?" → the decision rule, then the operational cost of WebSocket state.
5.1.22 "Design the delivery mechanism for live QuizStakes settlement notifications to 2.4M clients."
       (A full design question using §2.17 and §2.16.)
5.1.23 "How does a CDN decide whether to serve from cache?" (Cache key, freshness, validation, Vary.)
5.1.24 "What is bandwidth-delay product and why do you care?" (§1.3.4–1.3.5.)
5.1.25 "Why is the first request on a new connection slow even on a fast link?" (Slow start
       arithmetic, §1.12.4, plus handshakes.)
5.1.26 "Requests to a service work for small responses and hang for large ones. Diagnose."
       (PMTUD black hole, §1.4.10.)
5.1.27 "Your latency is quantised at 40 ms. Why?" (Nagle + delayed ACK.)
5.1.28 "How do you find out whether a slow call is DNS, connect, TLS or the server?"
       (`curl -w`, then the JFR/metric equivalent.)
5.1.29 "What is a 502 vs a 503 vs a 504, mechanically?"
5.1.30 "You have a 30 ms budget for a cross-service call. Is that achievable, and what must be
       true?" (The §1.30.3 decomposition.)
5.1.31 **Staff-level framing questions**: how do you set timeouts across a whole organisation
       (deadline propagation), how do you prevent retry storms at company scale (budgets and load
       shedding), and how do you migrate a fleet from HTTP/1.1 to HTTP/2 without losing load
       distribution.
5.1.32 The five whiteboard diagrams you should be able to draw from memory: the TCP state machine,
       the handshake + close with sequence numbers, the OSI/TCP-IP stack with encapsulation, the
       DNS resolution chain with caches, and the request path from browser to database with every
       intermediary.

*(32 leaves)*

## §5.2 One-line assertions to be able to state cold

5.2.1 Every checklist line from the current `src/topics/10-networking.md` — all 46 — restated and
      preserved verbatim as the floor of this section. `[TABLE]`
5.2.2 The new assertions this syllabus adds, grouped by part: the constants (MSS 536/1220, MSL 2
      min, Linux `TIME_WAIT` 60 s, `somaxconn` 4096, keepalive 7200/75/9, ephemeral 32768–60999,
      HTTP/2 window 65,535 and frame 16,384, HPACK table 4096, TLS record 16,384, CUBIC C=0.4
      β=0.7, QUIC kPacketThreshold 3 / kInitialRtt 333 ms, ALB 60/65/300 s, JDK keepalive 30 s,
      Happy Eyeballs 50/250 ms), the mechanisms, and the traps. `[TABLE]` `[NUM]`
5.2.3 The ten sentences that most reliably signal depth in an interview, and the ten that most
      reliably signal its absence. `[TABLE]`

*(3 leaves)*

## §5.3 Retention drills

5.3.1 **Constant recall drill**: 40 flashcard pairs (name → value) covering every `[NUM]` leaf.
5.3.2 **Symptom → layer drill**: 25 error strings, name the layer and the first command.
5.3.3 **Arithmetic drill**: BDP for three link/RTT pairs, port-exhaustion rate for two port ranges,
      slow-start RTTs for four response sizes, fan-out availability for three dependency counts,
      pool size by Little's Law for three workloads. `[CALC]`
5.3.4 **Trace drill**: from memory, write the packet sequence for a complete HTTPS request over a
      cold TLS 1.3 connection, then the same over a pooled HTTP/2 connection.
5.3.5 **Version drill**: for each of the seventeen deltas, state the stale claim and the true one.
5.3.6 **Design drill**: given the QuizStakes latency budgets, allocate a timeout and retry policy
      for every dependency in Appendix A's table, and justify each. `[TABLE]`
5.3.7 The spaced-repetition schedule: constants daily for a week, mechanisms weekly, the full
      question bank once before the interview.

*(7 leaves)*

---

## Diagram manifest

Diagrams the write pass must produce as standalone SVGs (never inline `<svg>`, never ASCII art),
embedded at the point of explanation. Numbered `D-NN-slug.svg`, topic-scoped.

| ID | Diagram | Anchored at |
|---|---|---|
| D-01 | The layered stack with encapsulation, byte offsets marked for a 1500-byte frame | §1.2.3 |
| D-02 | The TCP header, bit by bit, all 8 control flags labelled | §1.7.2 |
| D-03 | The full TCP state machine, all 11 states with transition labels | §1.8.1 |
| D-04 | Three-way handshake and four-way close on one timeline with sequence numbers | §1.8.3, §1.8.8 |
| D-05 | SYN queue vs accept queue, with the overflow paths and their counters | §1.14.3, §3.3.1 |
| D-06 | `cwnd` over time: slow start, congestion avoidance, fast recovery, and CUBIC's cubic curve | §1.12.3, §1.12.8 |
| D-07 | Nagle + delayed ACK deadlock as a two-party timeline showing the 40 ms gap | §1.13.3 |
| D-08 | The DNS resolution chain with every cache layer and its TTL | §1.16.6 |
| D-09 | TLS 1.2 (2 RTT) vs TLS 1.3 (1 RTT) vs TLS 1.3 resumption (0 RTT) side by side | §1.24.3–§1.24.4 |
| D-10 | The TLS 1.3 key schedule as a derivation tree | §3.8.2 |
| D-11 | Certificate chain and path building, with the missing-intermediate failure marked | §1.24.14, §3.8.11 |
| D-12 | HTTP/1.1 HOL blocking vs HTTP/2 multiplexing vs HTTP/3 per-stream delivery, one lost packet in each | §2.2.21, §2.3.3 |
| D-13 | The HTTP/2 frame header (9 bytes) and a multiplexed frame sequence on one connection | §2.2.2 |
| D-14 | HPACK static + dynamic table with one request's encoding shown byte by byte | §3.9.1 |
| D-15 | QUIC packet structure: long header, short header, coalesced datagram | §3.10.4 |
| D-16 | QUIC connection migration with CID rotation and path validation | §2.3.8 |
| D-17 | The six timeouts of an HTTP call on one timeline | §2.7.1 |
| D-18 | The idle-timeout ladder: client pool, server, ALB, NAT — with the mismatch window shaded | §2.6.2 |
| D-19 | `TIME_WAIT` accumulation and the ephemeral-port arithmetic as a capacity graph | §2.10.5 |
| D-20 | L4 connection pinning vs L7 per-request balancing, with a new backend added | §2.12.2 |
| D-21 | The three TLS termination topologies with the unencrypted segment highlighted | §2.13.1 |
| D-22 | CDN request flow: edge hit, edge miss, tiered cache, origin shield | §2.16.2 |
| D-23 | SSE vs WebSocket vs long polling as three connection-lifetime timelines | §2.17.1 |
| D-24 | The kernel receive path from NIC ring to socket buffer, with every drop point marked | §3.2.1, §3.2.4 |
| D-25 | epoll internals: RB-tree, ready list, callback registration | §3.6.2 |
| D-26 | Virtual thread unmount/remount on a socket read, through `Poller` | §3.11.8 |
| D-27 | Netty pipeline and event-loop ownership of channels | §3.12.1 |
| D-28 | Tomcat's three queues (accept, connection, thread) with the numeric limits | §3.13.2 |
| D-29 | A packet's path from pod to pod through veth, bridge, conntrack and kube-proxy | §3.14.1, §3.14.5 |
| D-30 | The full QuizStakes `ReserveStake` request path with every hop's latency budget annotated | §1.30.3 |

## Overall leaf totals

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — BASICS | §1.1–§1.30 (30) | 349 |
| PART 2 — INTERMEDIATE | §2.1–§2.22 (22) | 294 |
| PART 3 — UNDER THE HOOD | §3.1–§3.15 (15) | 170 |
| PART 4 — BUILD IT | §4.1–§4.10 (10) | 56 |
| PART 5 — INTERVIEW AND RETENTION | §5.1–§5.3 (3) | 42 |
| **Total** | **80 sections** | **911 leaves** |

Tag census for the write pass's planning: **73 leaves carry `[RESEARCH]`** and must be re-verified
against the cited source before a constant is committed to the page; **17 `[VERSION-TRAP]`** leaves
correspond to the deltas listed in the header; `[BUILD]` covers §4.1–§4.10 (56 leaves including 10
diff tables); `[SOURCE]` appears throughout PART 3 and in §1.4.5, §1.7.3, §1.7.5, §1.8.1;
`[INCIDENT]` appears 30 times and each must be written as symptom → diagnosis → root cause → fix.

## Sources consulted

Primary sources first. Every URL below was fetched during this pass unless explicitly marked
otherwise. **The WebSearch budget for this session was exhausted before the research phase began**,
so discovery was performed by fetching known-canonical primary sources directly (IETF RFCs, Linux
man pages, Oracle JDK documentation, AWS documentation, OpenJDK JEPs, the gRPC and WHATWG specs)
rather than through search. That is a real limitation and it is recorded here honestly: no
interview-question aggregators, no expert blog posts and no course syllabi were consulted, so the
"curriculum", "interview surface" and "adversarial" research angles were covered from the existing
guide, the sibling syllabi and the primary specs alone. The write pass should re-run those three
angles if search budget is available.

**IETF RFCs (primary — fetched)**

- <https://www.rfc-editor.org/rfc/rfc9293.html> — TCP. Source of §1.7, §1.8, §1.9, §1.13.1: the
  eleven state names (§3.3.2), **MSL = 2 minutes** (§3.4.2), **default MSS 536 IPv4 / 1220 IPv6**
  (§3.7.1), the eight control bits in CWR/ECE/URG/ACK/PSH/RST/SYN/FIN order (§3.1), ISN generation
  as clock-driven with a pseudorandom function (§3.4.1), simultaneous open (§3.5, Figure 7), RST
  generation rules (§3.5.2–3.5.3), half-close (§3.6.1), TIME-WAIT = 2×MSL (§3.6.1), Nagle (§3.7.4),
  PMTUD/PLPMTUD (§3.7.2), keep-alive (§3.8.4), PAWS (§3.4.3), and the mandatory option set (§3.2).
  Confirms RFC 9293 obsoletes RFC 793. `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc9000.html> — QUIC transport. Source of §2.3 and §3.10: the four
  stream types with their 2-bit codes (§2.1 Table 1), the complete frame inventory PADDING through
  HANDSHAKE_DONE (§19.1–19.20), packet types (§17.2–17.3), connection IDs (§5.1), migration (§9),
  path validation (§8.2), version negotiation (§6), stateless reset (§10.3), the transport-parameter
  names (§18.2), the error-code list (§20), the **3× amplification limit**, and the anti-deadlock
  rule (§4.2). `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc9002.html> — QUIC loss detection and congestion control. Source
  of §3.5.8–§3.5.10: `kPacketThreshold = 3`, `kTimeThreshold = 9/8`, `kGranularity = 1 ms`,
  `kInitialRtt = 333 ms`, `kPersistentCongestionThreshold = 3`, `kInitialWindow` (10× max datagram,
  bounded by max(14,720, 2×)), `kMinimumWindow = 2×`, `kLossReductionFactor = 0.5`, the PTO formula,
  and the five differences from TCP loss detection. `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc9113.html> — HTTP/2. Source of §2.2: the ten frame types with
  hex codes, all six SETTINGS parameters with identifiers **and defaults (4096 / 1 / unlimited /
  65,535 / 16,384 / unlimited)**, the exact 24-octet connection preface, the seven stream states,
  the flow-control default and 2^31−1 maximum, and — critically — the statement that RFC 9113
  **deprecates the RFC 7540 priority scheme** and that servers MUST NOT set `SETTINGS_ENABLE_PUSH`
  to 1. `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc9114.html> — HTTP/3. Source of §2.3.15–§2.3.21: frame types
  with codes, the four unidirectional stream types plus the grease pattern,
  `SETTINGS_MAX_FIELD_SECTION_SIZE` and the forbidden HTTP/2 settings, the full H3_* error list,
  request-to-stream mapping (§6.1) including the "SHOULD permit ≥100 concurrent request streams"
  guidance, GOAWAY semantics (§5.2), the prohibitions on `Transfer-Encoding`/`Connection`/`Upgrade`/
  uppercase field names, extended CONNECT (§4.4), and a QPACK summary. `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc9110.html> — HTTP semantics. Source of §1.22: the eight methods
  with safe/idempotent/cacheable properties (§9.3), the complete status-code list by class, the
  eight header-field categories with their members, and §2.4's guidance on automatic retry of
  idempotent requests after a connection failure.
- <https://www.rfc-editor.org/rfc/rfc9111.html> — HTTP caching. Source of §1.23: every response
  directive with its section number (`max-age` 5.2.2.1 … `s-maxage` 5.2.2.10, including
  `must-understand` 5.2.2.3), every request directive (5.2.1.1–5.2.1.7), the freshness-lifetime
  precedence (§4.2.1), the **exact age formulas** (§4.2.3), the ~10% heuristic (§4.2.2), validator
  strength, `Vary` including `Vary: *` (§4.1), the `Age` field (§5.1), and invalidation (§4.4).
  `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc8446.html> — TLS 1.3. Source of §1.24 and §3.8: the handshake
  message list in order, the key-schedule secret names and `HKDF-Expand-Label`, the **five
  mandatory cipher suites**, the required and important extensions, 0-RTT's lack of forward secrecy
  (§2.3) and the anti-replay mechanisms (§8), `NewSessionTicket`-based resumption replacing RFC 5077,
  and the removal list (renegotiation, compression, static RSA/DH, custom DHE groups,
  ChangeCipherSpec except in compatibility mode). `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc6455.html> — WebSocket. Source of §2.17.9–§2.17.13 and §4.7:
  the handshake header set, the **GUID `258EAFA5-E914-47DA-95CA-C5AB0DC85B11`** (§1.3), the frame
  bit layout (§5.2), the full opcode table, the three payload-length encodings, the masking rule
  (§5.3) and its cache-poisoning rationale (§10.3), the close codes 1000–1015 (§7.4.1), the
  **125-byte** control-frame limit (§5.5), ping/pong (§5.5.2–5.5.3), and fragmentation rules (§5.4).
  `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc8305.html> — Happy Eyeballs v2. Source of §1.19.10: the
  algorithm steps (§2), **Resolution Delay 50 ms** (§3), **Connection Attempt Delay 250 ms
  recommended, 10 ms absolute minimum, 100 ms recommended floor, 2 s ceiling** (§5), and address
  interleaving with the First Address Family Count (§4). `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc9438.html> — CUBIC. Source of §1.12.8 and §3.4.3–§3.4.5:
  `W_cubic(t) = C(t−K)³ + W_max` (§4.2), **C = 0.4** (§5.1), **β_cubic = 0.7** (§4.6), the
  Reno-friendly region taking `max(W_cubic, W_est)` (§4.3), fast convergence (§4.7), and the
  statement that CUBIC is the default in Linux, Windows and Apple stacks (§1). `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc9460.html> — SVCB and HTTPS RRs. Source of §1.17.3–§1.17.4 and
  §2.3.22: **SVCB = type 64, HTTPS = type 65** (§14.1–14.2), AliasMode (SvcPriority 0, §2.4.2) vs
  ServiceMode (§2.4.3), the SvcParamKeys `alpn`/`no-default-alpn` (§7.1), `port` (§7.2),
  `ipv4hint`/`ipv6hint` (§7.3), `mandatory` (§7.4, §8) and `ech` (§14.3.2), the apex solution (§9.1),
  and direct HTTP/3 endpoint discovery without Alt-Svc (§1.1). `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc6891.html> — EDNS(0). Source of §1.18.2–§1.18.3: the **OPT
  pseudo-RR type 41**, its once-per-message additional-section placement and the MUST-NOT-cache
  rule, the requestor's UDP payload size in the CLASS field with the **4096 → 1280–1410 → 512**
  fallback ladder and the 512 floor, the TTL field carrying the extended 12-bit RCODE and the DO
  flag, and the fragmentation/TC-bit/TCP-retry consequences. `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc8484.html> — DNS over HTTPS. Source of §1.18.6:
  **`application/dns-message`**, GET with base64url `?dns=`, POST with the wire-format body, the
  `{?dns}` URI template, the rule that HTTP freshness must not exceed the smallest DNS TTL (and the
  SOA MINIMUM for negative answers), the DNS-ID-0 recommendation, the comparison to DoT on port 853,
  and the enterprise-visibility consequence. `[RESEARCH]`
- <https://www.rfc-editor.org/rfc/rfc7239.html> — the `Forwarded` header. Source of §2.13.4: the
  `for`/`by`/`host`/`proto` parameters, IP/`unknown`/obfuscated node identifiers, the
  `X-Forwarded-For: 192.0.2.43, 2001:db8:cafe::17` → `Forwarded: for=192.0.2.43,
  for="[2001:db8:cafe::17]"` conversion example, and the explicit statement that the field "cannot
  be relied upon to be correct" plus the trusted-proxy whitelisting requirement. `[RESEARCH]`

**Linux (primary — fetched)**

- <https://man7.org/linux/man-pages/man7/tcp.7.html> — Source of every sysctl and socket-option
  default in §1.10–§1.14 and §3.2–§3.5: `tcp_fin_timeout` **60 s**, `tcp_keepalive_time` **7200 s**,
  `tcp_keepalive_probes` **9**, `tcp_keepalive_intvl` **75 s**, `tcp_max_syn_backlog` **256 (1024
  with adequate memory)**, `tcp_syncookies` **1**, `tcp_synack_retries` **5**, `tcp_syn_retries`
  **6**, `tcp_tw_reuse` disabled by default, `tcp_rmem`/`tcp_wmem` vectors, `tcp_fastopen` **0x1**,
  `tcp_slow_start_after_idle` enabled, `tcp_abort_on_overflow` disabled; and the socket options
  `TCP_NODELAY`, `TCP_CORK` (with its **200 ms ceiling**), `TCP_QUICKACK`, `TCP_DEFER_ACCEPT`,
  `TCP_USER_TIMEOUT`, `TCP_INFO`, `TCP_MAXSEG`, `TCP_FASTOPEN`, `TCP_KEEPIDLE`/`KEEPCNT`/`KEEPINTVL`.
  **Note:** the page does not state `TCP_TIMEWAIT_LEN`, `somaxconn`'s 5.4 default change, or
  `tcp_retries2`'s value — the write pass must confirm those against
  `Documentation/networking/ip-sysctl.rst` and `include/net/tcp.h` before printing them.
  `[RESEARCH]`
- <https://man7.org/linux/man-pages/man7/socket.7.html> — Source of §1.14.10–§1.14.16 and §3.2.11:
  `SO_REUSEADDR`, `SO_REUSEPORT` (Linux 3.9+, must precede `bind`), `SO_RCVBUF`/`SO_SNDBUF` and the
  **kernel doubling** behaviour with defaults from `/proc/sys/net/core/{r,w}mem_default`,
  `SO_RCVTIMEO`/`SO_SNDTIMEO` returning `EAGAIN`, `SO_KEEPALIVE`, `SO_LINGER`, `SO_ERROR`,
  `SO_INCOMING_CPU` (3.19), `SO_BUSY_POLL` (3.11). The page does **not** document `SO_ZEROCOPY` or a
  `somaxconn` default — both must be verified elsewhere. `[RESEARCH]`

**JDK (primary — fetched)**

- <https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/net/doc-files/net-properties.html>
  — Source of §1.5.11, §1.19.2–§1.19.4 and §1.25.12–§1.25.14: `java.net.preferIPv4Stack` **false**,
  `java.net.preferIPv6Addresses` **false**, `http.proxyPort` **80**, `https.proxyPort` **443**,
  `http.nonProxyHosts` default `localhost|127.*|[::1]`, `socksProxyPort` **1080**,
  `socksProxyVersion` **5**, `java.net.useSystemProxies` **false**, `http.keepAlive` **true**,
  `http.maxConnections` **5**, `http.maxRedirects` **20**, `jdk.http.maxHeaderSize` **393216**,
  `jdk.https.negotiate.cbt` **never**, **`networkaddress.cache.negative.ttl` default 10**, and the
  existence of `networkaddress.cache.stale.ttl`. It states `networkaddress.cache.ttl`'s default as
  `-1` **with a security manager** and implementation-specific otherwise — so the "30 s" figure in
  §1.19.2 must be re-verified against `java.security` in a JDK 21 build before it is printed.
  `[RESEARCH]`
- <https://docs.oracle.com/en/java/javase/21/docs/api/java.net.http/module-summary.html> — Source of
  §1.25.10 and §2.5.10: `jdk.httpclient.keepalive.timeout` **30**, `keepalive.timeout.h2`,
  `connectionPoolSize` **0 (unbounded)**, `connectionWindowSize` **2^26**, `windowsize` **16777216
  (16 MB)**, `maxstreams` **100**, `bufsize` **16384**, `redirects.retrylimit` **5**,
  `auth.retrylimit` **3**, `disableRetryConnect` **false**, `enableAllMethodRetry` **false**,
  `websocket.writeBufferSize` **16384**, `allowRestrictedHeaders` (connection, content-length,
  expect, host, upgrade restricted by default), `receiveBufferSize`/`sendBufferSize` = OS default,
  and `jdk.httpclient.HttpClient.log` values. `[RESEARCH]`
- <https://openjdk.org/jeps/491> — "Synchronize Virtual Threads without Pinning". Source of
  §2.20.10 and §3.11.10: **targets Java 24**, removes pinning for `synchronized`
  methods/statements and monitor acquisition, leaves pinning for class loading, class initializers
  and waiting on another thread's class initialization (all native-frame cases), retains the
  `jdk.VirtualThreadPinned` JFR event with narrowed scope, and **removes the
  `jdk.tracePinnedThreads` system property entirely**. `[RESEARCH]`

**Other primary sources (fetched)**

- <https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-HTTP2.md> — Source of §2.18: `:method POST`,
  `:path /{Service-Name}/{method-name}`, `content-type: application/grpc[+proto|+json]`,
  `te: trailers`, `grpc-timeout` with H/M/S/m/u/n units, `grpc-encoding`, the **1-byte compressed
  flag + 4-byte big-endian length** message framing with the "compression contexts are NOT
  maintained over message boundaries" rule, the always-200 `:status` with `grpc-status`/
  `grpc-message`/`grpc-status-details-bin` in trailers, and PING-based keepalive with call
  cancellation on deadline. `[RESEARCH]`
- <https://html.spec.whatwg.org/multipage/server-sent-events.html> — Source of §2.17.4–§2.17.6: the
  `event`/`data`/`id`/`retry` fields and their buffer semantics, `:` comment lines, blank line as
  the dispatch trigger, UTF-8-only with BOM stripping, CRLF/LF/CR line endings, `Last-Event-ID` on
  reconnect, the readyState constants CONNECTING 0 / OPEN 1 / CLOSED 2, and `withCredentials`.
  `[RESEARCH]`
- <https://www.haproxy.org/download/2.8/doc/proxy-protocol.txt> — Source of §2.13.7–§2.13.8: the v1
  ASCII format with its `PROXY TCP4 192.168.0.1 192.168.0.11 56324 443\r\n` shape and **107-character
  maximum**, the v2 **12-byte signature `\x0D\x0A\x0D\x0A\x00\x0D\x0A\x51\x55\x49\x54\x0A`**, the
  TLV extension set (ALPN, certificate details, checksums, unique ID, namespace), and the MUST-level
  requirement that receivers accept the header only from explicitly trusted proxies. `[RESEARCH]`
- <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancer-components.html>
  — Source of §2.6.2, §2.12.9–§2.12.11: ALB **idle timeout default 60 s (range 1–4000)**, **HTTP
  client keep-alive 65 s**, **deregistration delay 300 s (range 1–3600)**, health-check defaults
  (interval **30 s**, timeout **5 s**, healthy threshold **5**, unhealthy threshold **2**), protocol
  support for HTTP/1.1, HTTP/2 and gRPC but **not HTTP/3** (CloudFront only), slow start disabled by
  default, and automatic `X-Forwarded-For` injection. The **NAT Gateway 55,000-connections-per-
  destination** figure in §2.10.12 and §2.15.7 comes from the existing guide and was **not**
  re-verified in this pass — the write pass must confirm it against the VPC NAT Gateway
  documentation. `[RESEARCH]`

**Sources deliberately not consulted, and the gap that leaves**

The WebSearch budget was exhausted, so the following angles were not run and the leaves that would
have come from them may be missing: published course syllabi and book tables of contents
(curriculum angle), interview-question aggregators (interview-surface angle), postmortem write-ups
(failure-mode angle beyond what the primary specs and the existing guide supply), and
"what people get wrong" articles (adversarial angle). Several version-dependent numbers used above
therefore rest on the existing guide or on recall and are explicitly flagged for re-verification:
Linux `TCP_TIMEWAIT_LEN = 60 s`, `net.core.somaxconn` **4096** since 5.4, `tcp_retries2 = 15`,
`ip_local_port_range` **32768–60999**, nginx and Tomcat connector defaults, Apache HttpClient 5 and
Reactor Netty pool defaults, Resilience4j defaults, the JDK's effective 30 s positive DNS TTL, and
the AWS NAT Gateway connection limit. **No URL above is invented, and no constant flagged here may
be written without confirmation.**

## Gaps vs the current guide

`src/topics/10-networking.md` is **627 lines** across 15 numbered sections plus a 46-item atomic
concept checklist. It is a strong breadth-first guide for its size: the TIME_WAIT section, the
timeout taxonomy, the keep-alive mismatch section and the C10K/Loom section are all correct,
mechanism-aware, and genuinely better than most material at this level. **Every `**Trap:**` and
every one of the 46 checklist lines must survive into the bible** — none is superseded. What it is
not is a complete networking document: it has no link layer, no IP layer, no congestion control, no
flow control, no HTTP semantics or caching, no kernel internals, no build-it section, and no
version discipline.

| Syllabus area | Present in `src/topics/10-networking.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why networking is a backend discipline; the eight fallacies | one-line scope preamble | ✅ the fallacies, the four paid-for questions | ✅ |
| §1.2 layering and encapsulation; ossification | — | ✅ entire section | |
| §1.3 physics: RTT floors, BDP, tail latency, fan-out availability | §2 mentions "100 ms RTT" in passing | ✅ BDP, the latency table, the fan-out arithmetic, goodput | ✅ severely |
| §1.4 MTU/MSS/PMTUD, fragmentation, the black-hole incident | — | ✅ entire section — one of the highest-value gaps in the file | |
| §1.5 IP addressing, CIDR, TTL, ICMP, IPv6, anycast, BGP | §13 mentions anycast for CDN | ✅ almost everything | ✅ |
| §1.6 UDP completely | §1 (the 4-field summary and the use-case list) | ✅ the 8-byte header detail, datagram-boundary semantics, safe payload size, ICMP port-unreachable, receive-buffer drops | ✅ the "UDP is faster" trap is excellent and must be preserved verbatim |
| §1.7 TCP header, sequence semantics, framing | §1 (byte-stream and framing, well done) | ✅ the header fields, the eight flags, ISN generation, PSH/URG, the pseudo-header | ✅ framing is correct and must be preserved verbatim and extended with the three strategies |
| §1.8 the 11-state machine, RST generation, half-close | §2 (handshake, 4-way close, refused vs timeout) | ✅ the state machine, simultaneous open/close, half-close, RST causes, `tcp_retries2` | ✅ the refused-vs-timeout trap is excellent and must be preserved verbatim |
| §1.9 RTO, Karn, fast retransmit, SACK, RACK-TLP, ECN | §1 mentions "RTO or dup ACKs" in one clause | ✅ every mechanism and every constant | ✅ severely |
| §1.10 TCP options: MSS, window scale, SACK, timestamps, TFO | — | ✅ entire section | |
| §1.11 flow control, zero-window, buffer autotuning | §1 mentions the receive window in one clause | ✅ everything else | ✅ severely |
| §1.12 congestion control: slow start, CUBIC, BBR, bufferbloat, `tcp_slow_start_after_idle` | §1 mentions cwnd in one clause; §6 mentions "congestion window stays warm" | ✅ the whole subject including the slow-start arithmetic that explains §6's own claim | ✅ severely |
| §1.13 Nagle + delayed ACK, the 40 ms stall, `TCP_NODELAY` | — | ✅ entire section | |
| §1.14 the sockets API, backlog/accept queue, every socket option | §2 (SYN backlog vs accept queue, `ss -lnt`, `netstat -s`) | ✅ the syscall sequence, `somaxconn`, syncookies, `SO_REUSEPORT`, `SO_LINGER`, keepalive knobs, `TCP_USER_TIMEOUT` | ✅ the accept-queue incident is correct and must be preserved verbatim and quantified |
| §1.15 ports and the 4-tuple | §10 (the 4-tuple point, made well) | ✅ the port ranges, `IP_BIND_ADDRESS_NO_PORT`, the well-known port table | ✅ |
| §1.16–§1.18 DNS model, records, transport, EDNS, DoH/DoT, DNSSEC | §3.2 (the cache chain) and §5 (records, TTL, failover gotchas) — both good | ✅ the message format, RCODEs, NXDOMAIN vs NODATA, negative-caching arithmetic, `resolv.conf`/`ndots`, EDNS(0), DoT/DoH/DoQ, DNSSEC, SVCB/HTTPS RRs | ✅ the CNAME-apex and TTL-migration points are correct and must be preserved verbatim |
| §1.19 DNS in the JVM | §3.2 item 3 + the JVM DNS trap (excellent) | ✅ `networkaddress.cache.stale.ttl`, JEP 418, `InetSocketAddress` eager resolution, Happy Eyeballs | ✅ the JVM-DNS incident is the guide's best trap and must be preserved verbatim |
| §1.20 URIs and the request target | §3.1 (one line on URL parsing) | ✅ percent-encoding, `URL.equals` DNS blocking, IDN, request-target forms | ✅ |
| §1.21 HTTP/1.x syntax, framing, chunked, smuggling, pipelining | §6 (keep-alive, pipelining, HOL, sharding, header repetition) | ✅ message syntax, `Content-Length` vs chunked, smuggling, `100-continue`, hop-by-hop headers, header-size limits | ✅ the pipelining/HOL explanation is correct and must be preserved verbatim |
| §1.22 HTTP semantics: methods, status codes, headers | §3.5 (a header list) | ✅ the entire semantics surface — methods with safe/idempotent/cacheable, the status-code inventory, the header categories, 502/503/504 disambiguation | ✅ severely |
| §1.23 HTTP caching at the protocol level | §3.7 and §13 mention `Cache-Control`/`ETag` | ✅ every directive, the age formulas, heuristic freshness, validators, `Vary`, the `no-cache` trap | ✅ severely — this is a major hole |
| §1.24 TLS as cost and handshake | §4 (goals, asymmetric/symmetric, forward secrecy, chain, cacerts, PKIX, intermediates, SNI, RTTs, 0-RTT, mTLS) — the guide's strongest section | ✅ the message lists, cipher suites, what 1.3 removed, HelloRetryRequest, ALPN, revocation/OCSP stapling, the record layer, JSSE surface | ✅ every trap here is correct and must be preserved verbatim |
| §1.25 the Java networking API surface | §7 shows one `HttpClient` snippet | ✅ the whole surface: `Socket`/NIO/`HttpClient` properties, `HttpURLConnection` defaults, proxy properties, Spring's `RestClient` | ✅ severely |
| §1.26 proxies, `CONNECT`, nginx/Tomcat defaults | §11 (LB-focused only) | ✅ forward vs reverse, `CONNECT` tunnelling, buffering, every nginx and Tomcat timeout default | ✅ |
| §1.27 sockets as fds | §10 (limits, the fd budget, `Too many open files`) | ✅ `fs.nr_open`, systemd `LimitNOFILE`, leak vs pressure | ✅ mostly complete; preserve verbatim |
| §1.28 the URL walkthrough | §3 (all seven stages plus the cache stack) — very good | ✅ ARP/routing stage, the per-stage failure table, the backend-to-backend variant | ✅ the cache stack is excellent and must be preserved verbatim |
| §1.29 the diagnostic toolkit | scattered (`ss`, `netstat -s`, `openssl s_client`) | ✅ `curl -w`, `tcpdump`/Wireshark, `nstat`, `ip`, `conntrack`, JFR, bpftrace, and the triage order | ✅ severely |
| §1.30 latency budgets and the QuizStakes numbers | — | ✅ entire section; the guide uses no scenario numbers at all | |
| §2.1 the master cost/failure/memory tables | — | ✅ entire section; the guide has no master table | |
| §2.2 HTTP/2 in depth | §6 (multiplexing, HPACK, push, TCP HOL, the L4/gRPC consequence) | ✅ frames, SETTINGS defaults, preface, stream states, flow control, Extensible Priorities, error codes, GOAWAY, Rapid Reset | ✅ the TCP-HOL and L4-pinning points are excellent and must be preserved verbatim |
| §2.3 HTTP/3 and QUIC in depth | §6 (UDP, per-stream reliability, 0/1 RTT, migration, CPU cost) | ✅ frames, streams, transport parameters, amplification limit, QPACK, the H3 error codes, discovery, AWS support, Java support | ✅ the migration and CPU points are correct and must be preserved verbatim |
| §2.4 protocol negotiation | — | ✅ entire section | |
| §2.5 connection pooling | §8 fix 1 and §7's rules mention pooling | ✅ the whole section: sizing by Little's Law, validation, eviction, per-client comparison, the body-not-closed leak, pool metrics | ✅ the "new client per request is a bug" point is correct and must be preserved verbatim |
| §2.6 keep-alive and the idle-timeout ladder | §9 (the ladder, the mismatch incident, the silent-drop variant, the keepalive fix) — excellent | ✅ the ALB 65 s client keep-alive, gRPC keepalive parameters, `max_connection_age`, retry-on-idle-failure | ✅ preserve the whole section verbatim |
| §2.7 the timeout taxonomy | §7 (four timeouts + total, the inactivity point, Java's infinite defaults, the cascade, the budget rules, the pool-acquisition trap) — excellent | ✅ DNS having no timeout, deadline propagation, the timeout-≠-cancellation point, server-side timeouts, LB-vs-app ordering | ✅ preserve verbatim; add the arithmetic |
| §2.8 retries, backoff, jitter, hedging | §7 (the 27× amplification rule, one clause) | ✅ the retryable-condition table, jitter strategies, retry budgets, hedging, where retries belong | ✅ the 27× point is correct and must be preserved verbatim |
| §2.9 circuit breakers, bulkheads, load shedding | §7 mentions "behind a circuit breaker" once | ✅ entire section | ✅ severely |
| §2.10 TIME_WAIT and port exhaustion | §8 (mechanism, both reasons, the arithmetic, the symptom, the five fixes, `tcp_tw_recycle`, the CLOSE_WAIT trap) — the guide's second-strongest section | ✅ the RFC MSL value vs Linux's 60 s, `tcp_max_tw_buckets`, `IP_BIND_ADDRESS_NO_PORT`, the NAT-Gateway variant | ✅ preserve the entire section verbatim |
| §2.11 CLOSE_WAIT and socket leaks | §8's closing trap | ✅ the Java causes, `FIN_WAIT_2`, the diagnosis path, the try-with-resources idiom | ✅ |
| §2.12 L4 vs L7, algorithms, health checks, draining | §11 (the comparison table, the pinning consequence, termination, health checks, four algorithms, `X-Forwarded-For`) — very good | ✅ DSR, power-of-two-choices proof, ALB health-check defaults, deregistration sequencing, slow start, outlier detection, client-side LB, mesh | ✅ preserve the table and the `X-Forwarded-For` point verbatim |
| §2.13 TLS termination and identity through the path | §11 (the three arrangements, `X-Forwarded-For`/`-Proto`) | ✅ RFC 7239 `Forwarded`, the rightmost-untrusted rule, the PROXY protocol v1/v2 with its bytes, mTLS identity forwarding, cert-expiry monitoring | ✅ the Spring `forward-headers-strategy` point is correct and must be preserved verbatim |
| §2.14 service discovery | — | ✅ entire section | |
| §2.15 NAT | §12 (the mechanism, four consequences, the NAT Gateway note) | ✅ SNAT/DNAT/PAT, conntrack limits, hairpin, CGNAT | ✅ preserve verbatim |
| §2.16 CDN | §13 (mechanism, benefits, cache key, invalidation, dynamic content) — good | ✅ the authenticated-response catastrophe, surrogate keys, `stale-while-revalidate`, edge stampede, origin shield, edge compute, metrics | ✅ the cache-key and versioned-URL points are correct and must be preserved verbatim |
| §2.17 real-time delivery | §14 (the table, the WebSocket handshake, operational costs, webhook design, the SSE default) — very good | ✅ the SSE wire format and `Last-Event-ID`, the frame format and opcodes, masking and why, close codes, `permessage-deflate`, RFC 8441, capacity arithmetic, Spring's surface | ✅ preserve the whole section verbatim |
| §2.18 gRPC on the wire | §6 mentions "gRPC is HTTP/2" | ✅ entire section | ✅ severely |
| §2.19 serialisation and payload cost | — | ✅ entire section | |
| §2.20 concurrency models | §15 (C10K, select/poll O(n), epoll, event loops, virtual threads, pinning, Loom's three limits) — the guide's third-strongest section | ✅ the thread-per-request model, LT vs ET, the comparison table, the `ThreadLocal`-at-scale caveat, and the **JDK 24 pinning change** | ✅ preserve verbatim; the JDK 21 pinning statement needs the JEP 491 update |
| §2.21 the failure catalogue | scattered across §2, §8, §9 | ✅ a single indexed catalogue of every exception string with its layer and first command | ✅ |
| §2.22 version history and the stale-answer sweep | — | ✅ entire section; the guide has no version discipline and states no target versions | |
| §3.1–§3.15 (all of PART 3) | §15 describes epoll's three mechanisms correctly at a conceptual level | ✅ **everything else**: the kernel receive path, sk_buff, NAPI, GRO/TSO, the accept path in kernel terms, congestion-control internals, RACK/TLP, epoll's RB-tree and callback, io_uring, zero-copy and kTLS, the TLS key schedule, PKIX path building, HPACK/QPACK internals, QUIC internals, `NioSocketImpl`/`Poller`/`HttpClient` internals, Netty internals, Tomcat/Reactor internals, container networking, and the five traced incidents | ✅ §15's epoll description is correct and must be preserved verbatim as the entry point to §3.6 |
| §4.1–§4.10 (all of PART 4) | — | ✅ entire part; the guide contains one 10-line `HttpClient` snippet and nothing else executable | |
| §5.1–§5.3 (all of PART 5) | the 46-item atomic concept checklist | ✅ the question bank, the retention drills, the arithmetic drills | ✅ the checklist is good and must be preserved in full inside §5.2.1 |

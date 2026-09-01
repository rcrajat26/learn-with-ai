# Ad-hoc Paper 2 — Linux, Containers & Operations

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `ad-hoc-paper-2-key.md`. Suggested time: 85 min.
20 questions, 1 mark each.

**Why this paper exists:** topics 11 (OS/Linux), 19 (Docker/Kubernetes) and 20
(observability/operations) have been sampled by four questions in nine papers
between them, none scoring above 0.5. This is the widest unmeasured territory
on the board. Difficulty sits at the easy→medium boundary: commands and
mechanisms, not tuning.

Where a question asks for **commands**, write the actual command line you would
type, not a description of it.

## Section 1 — Processes, threads and signals

**Q1.** Process vs thread on Linux: what does each own, what do they share, and
what is the single system call that creates both? Then: if one thread
segfaults, what happens to the other threads in that process?

**Q2.** `kill <pid>` does nothing; the process stays. Give three distinct
reasons this can happen, and say for each whether `kill -9` would help. Then:
before you `kill -9` a hung JVM, what is the one thing you should do first, and
what does it cost you if you skip it?

**Q3.** A JVM process shows `VSZ` of 12 GB and `RSS` of 1.4 GB on a box with
4 GB of RAM. Explain why this is not necessarily a problem, and say which of
the two numbers you should be alerting on.

## Section 2 — Diagnosing a sick box

**Q4.** You SSH into a production box that "feels slow." Give the **first four
commands** you run, in order, and state what decision each one's output lets
you make. (This is a sequence question — an unordered list of tools scores half.)

**Q5.** `top` shows CPU at 4% idle 2%, and `wa` at 89%. What is the bottleneck,
which command do you run next, and which column of its output is the latency
you actually feel?

**Q6.** The app logs "Too many open files." (a) What resource is exhausted, and
name three things that consume it besides files. (b) Give the command that
shows the limit **actually applying to the running process** (not the shell's).
(c) How do you tell a too-low limit apart from a leak?

**Q7.** `df -h` says the disk is 60% full, but writes are failing with "No space
left on device." What is the most likely cause, and which command confirms it?
Separately: `df` and `du` disagree by 40 GB — what does that mean and how do you
find the culprit?

**Q8.** You have a 2 GB rotating JSON log. Write the command lines for:
(a) following the live log across a rotation; (b) the 20 most frequent values
of the `path` field; (c) every line for correlation id `abc-123` with 3 lines of
surrounding context, including in already-rotated `.gz` files.

## Section 3 — Docker

**Q9.** Review this Dockerfile and list every defect you can find, with the fix
for each:
```dockerfile
FROM openjdk:latest
WORKDIR /app
COPY . .
RUN ./mvnw package
ENV DB_PASSWORD=hunter2
CMD ./app.sh
```

**Q10.** Layer caching: what creates a layer, and why does copying your source
before installing dependencies make every build slow? Give the reordering that
fixes it for a Maven project. Then: a colleague adds `RUN rm /app/secrets.txt`
in a later layer — is the secret gone from the image?

**Q11.** Every deploy, your service takes exactly 30 seconds to die and
in-flight requests are dropped. The Dockerfile ends with `CMD ./start.sh`.
Explain the mechanism precisely — what is PID 1, what happens to SIGTERM — and
give the fix.

**Q12.** Containers vs VMs: what isolates a container, what does it share with
the host, and what is the security consequence of that sharing? Then: name the
main reason teams actually adopt containers (it is not efficiency).

## Section 4 — Kubernetes

**Q13.** Liveness, readiness and startup probes: what does the platform DO when
each one fails? Then the trap: a team wires a database check into the
**liveness** probe. Describe exactly what happens during a 5-minute database
outage, and why it makes the outage worse.

**Q14.** Requests vs limits. (a) What does each one actually control?
(b) What happens when a pod exceeds its CPU limit, and what happens when it
exceeds its memory limit — and why is the difference important? (c) Why is CPU
throttling invisible on a CPU-utilisation dashboard, and what metric exposes it?

**Q15.** A pod is in `CrashLoopBackOff`. Give the exact command sequence you
would run to diagnose it, including how you read the logs of the container that
**already died**. Then name four distinct causes that produce this state.

**Q16.** Rolling updates drop requests even with `maxUnavailable: 0` and a
correct readiness probe. Explain the race that causes it, and give the fix.
Then list the full shutdown chain from the platform's decision to terminate
through to process exit.

## Section 5 — Observability

**Q17.** Logs, metrics and traces: define each in one line, state the question
each is best at answering, and describe the workflow that uses all three during
an incident. Then: why do you put a user id in a log but never in a metric label?

**Q18.** Your dashboard shows average latency of 120 ms and users are
complaining. (a) Why is the average useless here and what should you be showing?
(b) You have p99 latency per instance and want p99 for the service — why can't
you average them, and what do you do instead? (c) What does a widening gap
between p50 and p99 usually indicate?

**Q19.** Correlation IDs. (a) Where is one generated and where is it stored so
every log line picks it up automatically? (b) Name the cleanup discipline it
requires in a thread pool and what goes wrong without it. (c) Name the boundary
it silently fails to cross and what you need to add there.

**Q20.** Alerting. (a) State the rule about what you alert on, with an example
of the wrong kind. (b) Every alert should be classified into one of three
buckets — name them and the test for the most urgent one. (c) What is an
error budget, what decision does it drive, and why is 100% availability the
wrong target?
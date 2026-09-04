# Syllabus — 23 Terraform & Infrastructure as Code

**Target versions: Terraform CLI 1.16.1 (released 2 Sep 2026) and OpenTofu 1.12.6 (released
19 Aug 2026), checked 2026-09-03.** Every block name, meta-argument, constant, default, flag,
command and file name below is stated against this pair unless a leaf says otherwise. Because
most corporate estates pin something older, every leaf that depends on a version boundary names
the release that introduced the behaviour, and every widely-repeated-but-now-stale claim carries
`[VERSION-TRAP]`.

| Layer | Release this file targets | Previous generation, also covered |
|---|---|---|
| Terraform CLI | **1.16.1** (2 Sep 2026). 1.16.0 (26 Aug 2026) added `import` blocks **inside modules**, `lifecycle { destroy = false }`, `terraform_data`'s `store` block, `action_trigger` `on_failure` = `halt`/`taint`/`continue`, `before_destroy`/`after_destroy` action events, Mermaid output for `terraform graph`, `console -scope`, JSON output for `state show` and `workspace list`, and provider "planned private data" persisted across plan and apply | **1.5.x** (last MPL-2.0 release), **1.9/1.10/1.11** (the lines most CI images still pin), **1.12** (14 May 2025) |
| Terraform pre-release | **1.17.0-alpha20260827** — deferred actions (`-allow-deferral`), batch-mode default changes | — |
| OpenTofu | **1.12.6** (19 Aug 2026): dynamic `prevent_destroy`, `destroy = false`, `-json-into=FILENAME`, concurrent provider installation, `zh:` **and** `h1:` checksums written at `init` | **1.6** (Jan 2024, the fork), **1.7** (state encryption), **1.8** (early eval, `.tofu` files), **1.9** (provider `for_each`, `-exclude`), **1.10** (OCI registries, native S3 locking), **1.11** (ephemeral values) |
| OpenTofu pre-release | **1.13.0-beta1** (27 Aug 2026): experimental **Symbol Libraries**, experimental `-lint`, `convert` function, Windows ARM64, Unicode 17, **WinRM provisioner removed**, 32-bit support ending after 1.13 | — |
| Licence | Terraform: **BUSL-1.1** since Aug 2023; licensor is now **International Business Machines Corporation** (IBM closed the $6.4B HashiCorp acquisition **27 Feb 2025**). OpenTofu: **MPL-2.0**, Linux Foundation, CNCF sandbox since Apr 2025 with a licence exception | Terraform ≤ **1.5.5** was MPL-2.0 |
| Provider plugin protocol | **tfplugin6** (`tfplugin6.proto`, Terraform CLI ≥ 1.0) — nested attributes via `SchemaAttribute.NestedType` | **tfplugin5** (`tfplugin5.proto`, CLI ≥ 0.12) — still what most SDKv2 providers speak |
| Provider SDK | **terraform-plugin-framework** (current; `terraform-plugin-mux` for incremental migration) | **terraform-plugin-sdk v2** — maintained for Terraform 1.x, **feature development stopped** |
| Plan/state JSON | `format_version` **"1.0"** (since 1.1.0); plan adds `applyable`, `complete`, `errored` | — |
| State file | JSON, `version` **4** `[RESEARCH]` | v3 and earlier, upgraded in place by newer CLIs |
| Managed platform | **HCP Terraform** (RUM-priced) and **Terraform Enterprise** (self-hosted, adds audit logging + SAML SSO) | Terraform Cloud (the old name) |
| Stacks | **GA** at HashiConf 2025 for RUM-based HCP plans: `*.tfcomponent.hcl` + `*.tfdeploy.hcl`, deployment groups, auto-approve checks, deferred changes. **HCP-only** | the beta, which used `tfstack.hcl` |
| Beta / new surfaces | **Terraform Actions** (public beta), **Terraform Search** (public beta, AWS + Azure), list resources + `terraform query` (`*.tfquery.hcl`, 1.14), **Terraform Policy** — native HCL policy framework (beta), HYOK (GA), Terraform MCP Server | Sentinel and OPA policy sets |
| CDKTF | **DEPRECATED — unsupported and unmaintained since 10 Dec 2025** | CDKTF 0.20.x for TypeScript/Python/Java/C#/Go |
| Java runtime for all code | **Java 21 LTS**, Spring Boot 3.x | — |

**The twenty-two deltas that most often produce a stale answer in a 2026 IaC interview**, each
marked `[VERSION-TRAP]` at its leaf:

1. **Terraform is not open source.** It moved from MPL-2.0 to **BUSL-1.1** in **August 2023**;
   **1.5.5 was the last MPL release**. The licence text now names **IBM** as licensor. Saying
   "Terraform is open source" is factually wrong and, in a regulated shop, a procurement
   problem. `[RESEARCH]`
2. **OpenTofu is not "a fork that will die".** It is a Linux Foundation project, in the CNCF
   sandbox since **April 2025** with a special exception to keep MPL-2.0, on **1.12.6**, and it
   has shipped features Terraform does not have. `[RESEARCH]`
3. **The fork has actually diverged.** OpenTofu-only: **state and plan encryption**, **provider
   `for_each`**, **early variable evaluation** in backends/module sources, `.tofu` file
   extensions, `-exclude`, `-target-file`/`-exclude-file`, OCI registries for providers *and*
   modules, `-json-into`. Terraform-only: **Stacks**, **Actions**, **list resources / `terraform
   query`**, `terraform test` in its current shape, HCP integration. "They are the same tool with
   a different name" is a 2024 answer. `[RESEARCH]`
4. **You do not need DynamoDB to lock S3 state.** `use_lockfile = true` (beta 1.10, **GA 1.11**)
   writes a `.tflock` object beside the state and uses S3 conditional writes. **All
   `dynamodb_*` arguments are deprecated** and will be removed. Naming a DynamoDB table as *the*
   locking mechanism dates the candidate by two years. `[RESEARCH]`
5. **Secrets no longer have to land in state.** **Ephemeral values and `ephemeral` resources**
   (1.10) plus **write-only arguments** (`*_wo`, 1.11) let a password reach a provider without
   being written to state or plan. "Everything Terraform touches ends up in state, full stop" is
   now only true for non-write-only attributes. `[RESEARCH]`
6. **State can be encrypted client-side — in OpenTofu.** The `encryption` block with `key_provider`
   (`pbkdf2`, `aws_kms`, `gcp_kms`, `azure_vault`, `openbao`, `external`) and `method "aes_gcm"`.
   Terraform's answer is server-side encryption of the *backend* plus HCP's HYOK. `[RESEARCH]`
7. **Refactoring no longer needs `terraform state mv`.** `moved` blocks (1.1) and `removed`
   blocks (1.7) are declarative, reviewable, and run inside the plan. `import` blocks (1.5) plus
   `plan -generate-config-out` replace `terraform import`. 1.16 allows `import` blocks **inside
   modules**. "Run `terraform import` for each resource" is a pre-1.5 answer. `[RESEARCH]`
8. **`terraform destroy` is not how you stop managing a resource.** `removed { from = …
   lifecycle { destroy = false } }` — and, since 1.16/OpenTofu 1.12, `lifecycle { destroy =
   false }` on the resource itself — drop it from state without touching the infrastructure.
   `[RESEARCH]`
9. **Terraform has a native test framework.** `terraform test` (**1.6**), provider mocking
   (**1.7**), `-junit-xml` GA (**1.11**), parallel `run` blocks, `state_key`. "Testing Terraform
   means Terratest in Go" is a 2022 answer. `[RESEARCH]`
10. **Providers can define functions.** `provider::<local-name>::<function>()` since **1.8**.
    The built-in function set is no longer the whole function surface. `[RESEARCH]`
11. **Module `source` and `version` can be dynamic — in 1.15+.** `variables and locals in module
    source and version attributes`. The flat "module sources must be literal" rule is now
    version-dependent (and OpenTofu got there first, via early evaluation in 1.8). `[RESEARCH]`
12. **Variables and outputs can be deprecated.** `deprecated = "…"` on `variable` and `output`
    blocks (Terraform **1.15**; OpenTofu 1.10, experimental). `[RESEARCH]`
13. **`lifecycle` is much bigger than three arguments.** `create_before_destroy`,
    `prevent_destroy`, `ignore_changes`, `replace_triggered_by` (1.2), `precondition`,
    `postcondition` (1.2), **`destroy`** (1.16), **`action_trigger`** (1.14/1.16). `[RESEARCH]`
14. **`count`/`for_each` unknown at plan time no longer always aborts.** Stacks' **deferred
    changes** produce a partial plan; core has `-allow-deferral` in alpha. `[RESEARCH]`
15. **CDKTF is dead.** Unsupported and unmaintained since **10 Dec 2025**. Recommending it as
    "Terraform for people who prefer Java" now recommends an abandoned tool. `[RESEARCH]`
16. **Stacks are not "workspaces done properly", and they are HCP-only.** `component` blocks in
    `*.tfcomponent.hcl` (renamed from `tfstack.hcl` at GA), `deployment` blocks in
    `*.tfdeploy.hcl`, **max 500 deployments and 100 components per Stack**. `[RESEARCH]`
17. **Policy is no longer only Sentinel or OPA.** HCP Terraform now also has **Terraform
    Policy**, a native HCL policy framework (beta), and ships **350+ pre-written Sentinel
    policies** for NIST SP 800-53 Rev 5 on AWS. `[RESEARCH]`
18. **`terraform validate` now validates `backend` blocks** (1.15) — type existence, required
    attributes, backend-specific validation. The old "validate never looks at the backend" claim
    is stale. `[RESEARCH]`
19. **There is a query/discovery surface now.** **List resources** in `*.tfquery.hcl` and the
    `terraform query` command (**1.14**), plus **Terraform Search** in HCP (beta), can enumerate
    existing infrastructure and generate import configuration. `[RESEARCH]`
20. **Providers can do non-CRUD work declaratively.** **Action** blocks (1.14, public beta) —
    e.g. `aws_lambda_invoke`, `aws_cloudfront_create_invalidation` — triggered by
    `lifecycle { action_trigger { … } }` or `-invoke`. This is the sanctioned replacement for
    `local-exec` glue. `[RESEARCH]`
21. **`null_resource` is legacy.** `terraform_data` (1.4) is the built-in replacement, needs no
    provider, and gained a `store` block in 1.16 for ephemeral/sensitive values. `[RESEARCH]`
22. **`prevent_destroy` can be dynamic — in OpenTofu 1.12** (it may reference variables). In
    Terraform it must still be a literal. `[RESEARCH]`

**Scope boundary against the sibling guides.** This file owns **Terraform as a runtime and as a
language**: what HCL evaluates to, how the graph is built and walked, what the provider protocol
carries, what state actually contains byte for byte, and every way the tool corrupts, deadlocks,
surprises or lies. Owned elsewhere:

- EC2/S3/RDS/DynamoDB/IAM/VPC primitives, IAM policy evaluation, KMS, cost modelling and the AWS
  service surface live in `18-cloud-aws.md`. This guide owns the AWS provider only as *the thing
  the graph calls*, and the S3/DynamoDB backend only as a **state store with a locking
  primitive**. `[X-REF 18]`
- Images, layers, Kubernetes objects, Helm, probes, HPA and CrashLoopBackOff live in
  `19-docker-kubernetes.md`. This guide owns the `kubernetes`/`helm` providers only as a source
  of unknown-value and eventual-consistency problems, and the "Terraform vs Kubernetes
  controllers" reconciliation argument. `[X-REF 19]`
- The object model, branching, rebase, hooks and reviewable commits live in `17-git-craft.md`.
  This guide owns the PR-driven plan/apply gate, what belongs in `.gitignore`, and why the lock
  file is committed. `[X-REF 17]`
- Test pyramid theory, JUnit 5 mechanics, Mockito, Testcontainers and flakiness live in
  `16-testing.md`. This guide owns `terraform test`, provider mocking, and what an
  infrastructure test can and cannot prove. `[X-REF 16]`
- Secrets *storage* design, OAuth/OIDC flows, TLS configuration and the OWASP list live in
  `13-web-security.md`. This guide owns secrets **in the IaC pipeline**: state as a secret store,
  ephemeral values, OIDC federation for CI, and the plan-output leak. `[X-REF 13]`
- Metrics, logs, traces, SLIs and postmortem practice live in `20-observability-operations.md`.
  This guide owns drift detection as a signal, `TF_LOG`, OpenTelemetry tracing of a run, and what
  a run's telemetry should emit. `[X-REF 20]`
- Locking, isolation, MVCC and deadlock theory live in `09-sql-databases.md`. This guide owns
  state locking as a *distributed mutual-exclusion* problem and the fencing argument.
  `[X-REF 09]`
- Graph algorithms — topological sort, cycle detection, DFS — live in `01-dsa-fundamentals.md`.
  This guide owns Terraform's specific graph, its node types and its walk. `[X-REF 01]`
- Idempotency, retries, timeouts and eventual consistency as distributed-systems concepts live in
  `22-system-design.md` and `10-networking.md`. This guide owns their Terraform-shaped versions:
  create-then-timeout, `-refresh=false`, provider retry/backoff. `[X-REF 22]` `[X-REF 10]`
- JVM memory, GC and heap dumps live in `06-jvm-internals.md`; Terraform is a Go binary and has
  none of that, which is itself worth one sentence. `[X-REF 06]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the
mechanism in **one paragraph** before pointing away — it never sends the reader off empty-handed.

**Every example, resource name, module name, workspace, account and incident in the bible comes
from the QuizStakes domain in `src/scenario/scenario.md`.** Module names are
`modules/service-runtime`, `modules/ledger-database`, `modules/document-bucket`,
`modules/payment-run-scheduler`, `modules/restrictions-cache`. Environments are `dev`,
`staging`, `prod`; accounts are `quizstakes-dev`, `quizstakes-staging`, `quizstakes-prod`,
`quizstakes-shared` (registry + state), `quizstakes-audit`. Services are the real ones:
`ApplicationGateway`, `RouterInt`, `JwtService`, `ClientRestrictions`, `AccountOpening`,
`AccountActivation`, `AccountMaintenance`, `DocumentVerification`, `ScreeningService`,
`BankDeposits`, `BankWithdrawal`, `FundsLedger`, `BonusService`, `CardPayments`,
`PaymentService`, `InternalPlatforms`, `BalanceView`, `ProfileService`, `PendingActions`,
`ApplicationHistory`, `NotificationService`, `AssessmentService`, `PersonalDetails`,
`ClientAgreements`, `DocumentRequirements`. Status codes are the real ones (`AO-100`, `AO-400`,
`AA-610`, `AA-700`, `AA-801`, `DEP-301`, `DEP-400`). **The current guide uses `aws_instance.api`,
`aws_security_group.api`, `aws_subnet.tier`, `var.subnets`, `myapp`, `networking` and
`payments`; every one of those must be re-domained by the write pass.**

**Domain facts the bible's examples must be consistent with** (scenario Appendix A and B): 2.4M
registered clients; 380k monthly active; **14k concurrent sessions, 55k peak**; 12k
registrations/day; 7.2k applications reaching `AO-400`/day; 95k card deposits/day at **40/sec**;
**2.8M stake reservations/day at 1,200/sec**; 2.8M settlements/day with **3,400/sec** bursts;
19.8M ledger entries/day at **230 writes/sec sustained, 13,600/sec peak**, ~180 bytes/row,
~1.3 TB/year, 7.2B rows/year, **90-day hot window, 7-year retention**; 24k document uploads/day
at **2–6 MB each = 68 GB/day**; 7k bank withdrawals/day across **4 `PaymentRun` windows/day**;
a **30 ms** restriction-decision budget, an 80 ms balance read, a **150 ms** stake reservation, a
**4 s** card deposit, a **90 s** async document verification and a **hard 500 ms**
self-exclusion budget. Deployment shapes are Appendix B.1 verbatim: `ApplicationGateway` 2 GB
heap 12→40 instances; `ClientRestrictions` 4 GB × 8; `DocumentVerification` 8 GB × 6;
`FundsLedger` 12 GB × 3, **deliberately not function-based**; `BankDeposits` 6 GB × 2 idle 23
hours; `BankWithdrawal` 6 GB × 2 with a **scheduled run job and a single leader — it must not run
twice**; `PaymentService` 4 GB × 8; `InternalPlatforms` 4 GB × 3 session-affine.

**The Appendix B.4 rules constrain every configuration in this guide** and the bible must say so
at the point of decision: workload identity with short-lived credentials and mTLS (so **CI
authenticates by OIDC role assumption, never a long-lived access key**); secrets in a managed
store, **never in config or environment** (so `terraform.tfvars` never holds a password and
`TF_VAR_db_password` is an anti-pattern); configuration **versioned and promoted through
environments, never edited in place** (so a `prod` apply replays an artifact that already
applied in `staging`); scheduled work behind a central scheduler plus leader election, never
per-instance cron; rolling deployment with **drain-before-terminate on the payment run**; and
object lifecycle policies plus partition detach-and-archive on the ledger. Appendix B.5's
`PaymentRun` invariant — **`signedOffBy` ≠ `authorisedBy`** — is the model for the
"plan is reviewed by a human who did not write it" gate.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument or the arithmetic through; do not state the result and move on |
| `[SOURCE]` | quote real documentation, changelog, `.proto`, or actual Go/HCL source (short excerpt) and explain every line |
| `[BUILD]` | ship a complete, runnable artifact — compiling Java 21, complete HCL, complete Go provider, complete Rego, complete pipeline YAML |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in the baseline and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default, threshold or byte arithmetic explicitly |
| `[CFG]` | give the exact argument / block / environment-variable name and its default |
| `[HCL]` | must show real HCL, not a description of it |
| `[CLI]` | show the exact command with its flags and read the output |
| `[FLOW]` | must be rendered as an ordered step-by-step trace, not prose |
| `[DIAG]` | must show real output — an error message, a plan diff, a state excerpt, a `TF_LOG` line — and read it line by line |
| `[TABLE]` | must be rendered as a table |
| `[TOFU]` | Terraform/OpenTofu behaviour differs; state both |
| `[SURGERY]` | a state-mutating recovery procedure; must include the backup step and the "when is this safe" test |
| `[COST]` | must show money or time arithmetic against QuizStakes volumes |
| `[INCIDENT]` | must describe a concrete, plausible failure with its symptom and its blast radius |

---

# PART 1 — BASICS

## §1.1 Why any of this exists at all

1.1.1 The origin problem: infrastructure was created by **humans clicking consoles and running
      one-off scripts**, so the only record of what existed was the thing itself. Nobody could
      answer "what is in staging?" without looking. `[TRAP]`
1.1.2 The four consequences, each named: **snowflake servers** (no two alike), **no review**
      (a change is a click, not a diff), **no reproducibility** (a region cannot be rebuilt),
      and **no audit** (who opened port 22, and when?). `[TABLE]`
1.1.3 Why QuizStakes specifically cannot live with that: a regulator asks *"show me that
      `CardPayments` was the only service able to reach the PSP on 14 March"*. That is a
      question about a **historical configuration**, and only a versioned artifact answers it.
      `[X-REF 13]`
1.1.4 **Infrastructure as code** as the answer: the desired state is a file, the file is in Git,
      and a tool makes reality match the file.
1.1.5 The **five properties** IaC buys: reproducibility, reviewability, auditability,
      **drift detectability**, and disaster recovery as a re-apply rather than a rebuild.
      `[TABLE]`
1.1.6 **Declarative vs imperative** as the central distinction. A script says *"create a
      bucket"*; a configuration says *"a bucket exists with these properties"*. Running the
      script twice creates two buckets; applying the configuration twice is a no-op. `[PROVE]`
1.1.7 **Idempotence** is therefore a property of the *tool*, not of your discipline — and it is
      exactly what a shell script cannot give you without hand-written existence checks.
      `[X-REF 22]`
1.1.8 **Convergence** vs **congruence**: converging on desired state (Terraform, Puppet) versus
      guaranteeing nothing else exists (immutable images, `terraform destroy`+re-apply).
      Terraform converges *the resources it knows about* and is blind to the rest. `[TRAP]`
1.1.9 **Mutable vs immutable infrastructure**, and why Terraform sits at the boundary: it can do
      either, and *the provider decides* which one a given attribute change gets.
1.1.10 The **configuration-management** distinction: Ansible/Chef/Puppet configure the inside of
      a machine; Terraform provisions the machine and the world around it. Where they overlap
      (`remote-exec`, the Ansible provider, Terraform Actions with Ansible playbooks) and why
      that overlap is where projects go wrong. `[TABLE]`
1.1.11 The **provisioning-vs-orchestration** distinction against Kubernetes: a Kubernetes
      controller reconciles **continuously**; Terraform reconciles **when you run it**. That one
      sentence explains most of Terraform's failure modes. `[X-REF 19]` `[PROVE]`
1.1.12 The honest costs of IaC, enumerated: a new language, a new failure mode (state), slower
      change (plan → review → apply), a tool that lags provider APIs by weeks, and an enormous
      blast radius concentrated in one `apply`. `[TABLE]` `[TRAP]`
1.1.13 When **not** to use Terraform: a one-off experiment, a resource whose API has no provider,
      an object with a lifecycle faster than a plan/apply cycle (individual Kubernetes pods,
      per-request objects), and anything an application creates at runtime. `[TRAP]`
1.1.14 The framing that lands in an interview: **"Terraform is a graph engine with a diff engine
      bolted to a plugin protocol, and a JSON file remembering what it did."** Everything else in
      this guide is detail on those four nouns. `[PROVE]`

## §1.2 The tool landscape, the licence, and the fork

1.2.1 **Terraform's history in one line each**: 2014 first release; **0.12** (2019) brought HCL2
      and first-class expressions; **0.13** provider source addresses; **0.14** the lock file and
      concise diffs; **0.15**/**1.0** the compatibility promise; then the 1.x line.
1.2.2 The **1.x compatibility promise**: configuration written for 1.0 keeps working; state is
      forward-migrated and **never backward-compatible**. `[NUM]` `[TRAP]`
1.2.3 **August 2023: the licence change.** MPL-2.0 → **BUSL-1.1**. `[VERSION-TRAP]` `[RESEARCH]`
1.2.4 What BUSL-1.1 actually restricts: you may not offer a **competitive** hosted service; it is
      **not OSI-approved**; there is a four-year conversion to MPL for each release. What it does
      *not* restrict: internal use, including commercial internal use. `[TRAP]` `[RESEARCH]`
1.2.5 **1.5.5 is the last MPL-2.0 Terraform release**, and it is the commit OpenTofu forked from.
      `[NUM]` `[RESEARCH]`
1.2.6 **IBM acquired HashiCorp for $6.4B, closing 27 Feb 2025.** The licence did not change; the
      **licensor named in the files is now International Business Machines Corporation**.
      `[NUM]` `[RESEARCH]`
1.2.7 **OpenTofu**: forked within ~30 days of the licence change, donated to the **Linux
      Foundation**, in the **CNCF sandbox since April 2025** with an explicit exception to keep
      MPL-2.0 rather than move to Apache-2.0. `[RESEARCH]`
1.2.8 The **drop-in-ness** claim, stated precisely: OpenTofu reads `.tf` files, `.tfvars`,
      `.tfstate` and `.terraform.lock.hcl`; the binary is `tofu`; `TF_*` environment variables
      are honoured alongside `TOFU_*`. Migration is usually a binary swap. `[CFG]` `[TOFU]`
1.2.9 Where it is **not** a drop-in: the registry hostname (`registry.opentofu.org` vs
      `registry.terraform.io`), the HCP integration (`cloud` block), Stacks, Actions, list
      resources, and any state that has been written by a newer Terraform than the OpenTofu you
      are moving to. `[TABLE]` `[TRAP]` `[TOFU]`
1.2.10 **The divergence table** — the leaf that makes this section worth reading. OpenTofu-only:
      state/plan **encryption**, **provider `for_each`**, **early variable evaluation**, `.tofu`
      extensions, `-exclude`, `-target-file`/`-exclude-file`, OCI registries for providers and
      modules, `-json-into`, global provider-cache lock, `TF_STATE_PERSIST_INTERVAL`, dynamic
      `prevent_destroy`, experimental **Symbol Libraries** and `-lint`. Terraform-only:
      **Stacks**, **Actions**, **list resources / `terraform query`**, `import` blocks in
      modules, `terraform_data { store }`, dynamic module `source`/`version`, HCP/TFE
      integration, `cloud` block, HYOK. `[TABLE]` `[VERSION-TRAP]` `[RESEARCH]`
1.2.11 The **decision procedure** for a real team: licence exposure (are you a vendor?),
      feature dependence (do you need Stacks?), platform (are you already on HCP?), and support
      posture (who do you page?). State the recommendation, not a survey. `[TABLE]`
1.2.12 **The rest of the field, bounded in one paragraph each**: CloudFormation (AWS-only,
      no plan-as-artifact in the same sense, stack drift detection, nested stacks),
      **AWS CDK** (imperative → CloudFormation), **Pulumi** (real languages, its own state
      service), **Crossplane** (Kubernetes controllers reconciling cloud resources
      continuously), **Ansible** (imperative, agentless, config management), **Terragrunt** (a
      wrapper for DRY backends and dependency ordering), **Terramate**/**Atmos** (generators and
      orchestration), **Spacelift**/**env0**/**Scalr** (managed run platforms). `[TABLE]`
1.2.13 The one honest reason Terraform won: **the provider ecosystem**. The language is
      unremarkable; ~4,000+ providers is the moat. `[PROVE]`
1.2.14 **`terraform` the binary**: a single static Go binary, no runtime, no JVM, no daemon. What
      that buys (trivial CI installation, `tfenv`/`tofuenv` version switching) and what it costs
      (no JVM-style introspection; debugging is `TF_LOG`, not a heap dump). `[X-REF 06]`
1.2.15 **Version management**: `required_version` in the `terraform` block, `tfenv`/`tofuenv`,
      `.terraform-version`, and why the CI image pin and `required_version` must agree.
      `[CFG]` `[TRAP]`

## §1.3 The CLI surface, complete

1.3.1 The **command inventory** as one table, each with its one-line job: `init`, `validate`,
      `fmt`, `plan`, `apply`, `destroy`, `show`, `output`, `refresh`, `import`, `taint`,
      `untaint`, `graph`, `console`, `state`, `workspace`, `providers`, `get`, `login`,
      `logout`, `version`, `force-unlock`, `test`, `metadata`, `query`, `stacks`. `[TABLE]`
1.3.2 The **deprecated-but-still-present** commands and their replacements: `terraform taint` →
      `apply -replace=`, `terraform refresh` → `apply -refresh-only`, `terraform import` →
      `import` blocks. `[TABLE]` `[VERSION-TRAP]`
1.3.3 **`terraform init`**, step by step: read the configuration, initialise the **backend**
      (and offer state migration), install **modules** into `.terraform/modules`, install
      **providers** into `.terraform/providers`, write/verify `.terraform.lock.hcl`, write
      `.terraform/terraform.tfstate` (the *backend* record, not your state). `[FLOW]`
1.3.4 `init` flags that matter: `-backend=false`, `-backend-config=`, `-reconfigure`,
      `-migrate-state`, `-upgrade`, `-get=false`, `-lockfile=readonly`, `-input=false`,
      `-plugin-dir=`. `[CFG]` `[CLI]`
1.3.5 **`-reconfigure` vs `-migrate-state`** — the distinction that loses state. `-reconfigure`
      *discards* the backend record and starts fresh; `-migrate-state` *copies* the existing
      state to the new backend. Choosing the first when you meant the second silently orphans
      everything. `[TRAP]` `[SURGERY]`
1.3.6 **`terraform validate`**: syntax, internal consistency, type checking, and (since **1.15**)
      **backend block validation**. What it cannot see: anything requiring provider API calls or
      remote state. `[VERSION-TRAP]` `[RESEARCH]`
1.3.7 **`terraform fmt`**: canonical formatting only — two-space indent, aligned `=` in
      consecutive single-line arguments, arguments before blocks. `-check` and `-recursive` for
      CI. It is not a linter. `[CFG]` `[TRAP]`
1.3.8 **`terraform plan`** flags: `-out=`, `-refresh=false`, `-refresh-only`, `-destroy`,
      `-target=`, `-replace=`, `-var`, `-var-file`, `-parallelism=`, `-lock=`,
      `-lock-timeout=`, `-input=false`, `-json`, `-detailed-exitcode`,
      `-generate-config-out=`, `-compact-warnings`. `[TABLE]` `[CFG]`
1.3.9 **`-detailed-exitcode`** and its three values: **0** = no changes, **1** = error,
      **2** = changes present. This is the flag every CI pipeline needs and almost none use.
      `[NUM]` `[CLI]` `[TRAP]`
1.3.10 **`terraform apply`** flags: a saved plan file as the positional argument,
      `-auto-approve`, `-replace=`, `-target=`, `-refresh=false`, `-parallelism=`, `-json`.
      `[CFG]`
1.3.11 **`terraform destroy`** as `apply -destroy`, and `-target` on destroy as the single most
      dangerous flag combination in the tool. `[TRAP]`
1.3.12 **`terraform show`**: human output, `-json` for a plan file or for state, and its role as
      the input to every policy tool. `[CLI]`
1.3.13 **`terraform output`**: `-json`, `-raw`, naming a single output, and the fact that
      `sensitive` outputs require `-raw`/`-json` to extract. `[CFG]` `[TRAP]`
1.3.14 **`terraform graph`**: `-type=plan|apply|plan-destroy`, DOT output, and (since **1.16**)
      **Mermaid** output. Why the raw graph is unreadable above ~50 nodes and what to do instead.
      `[CLI]` `[RESEARCH]`
1.3.15 **`terraform console`**: expression evaluation against real state, `-plan` to evaluate
      against a plan, and (since **1.16**) **`-scope`** to evaluate inside a module.
      `[CLI]` `[RESEARCH]`
1.3.16 **`terraform state`** subcommands, complete: `list`, `show`, `mv`, `rm`, `pull`, `push`,
      `replace-provider`, `identities`. Each with its blast radius. `[TABLE]` `[SURGERY]`
1.3.17 **`terraform providers`** subcommands: bare (the dependency tree), `lock`, `mirror`,
      `schema -json`. `[CLI]`
1.3.18 **`terraform force-unlock <LOCK_ID>`**: requires the exact lock ID as a nonce, and the
      documentation's own warning — *"If you unlock the state when someone else is holding the
      lock it could cause multiple writers."* `[SOURCE]` `[SURGERY]` `[TRAP]`
1.3.19 **`terraform login` / `logout`**: the credentials file at
      `~/.terraform.d/credentials.tfrc.json`, `TF_TOKEN_<hostname>` environment variables, and
      credentials helpers. `[CFG]`
1.3.20 **`terraform test`** (1.6+), **`terraform query`** (1.14+), **`terraform stacks`**
      (1.13+), **`terraform metadata functions -json`**. `[RESEARCH]`
1.3.21 The **environment-variable surface**, complete: `TF_LOG`, `TF_LOG_PATH`,
      `TF_LOG_CORE`, `TF_LOG_PROVIDER`, `TF_VAR_<name>`, `TF_CLI_ARGS`,
      `TF_CLI_ARGS_<command>`, `TF_DATA_DIR`, `TF_WORKSPACE`, `TF_IN_AUTOMATION`,
      `TF_INPUT`, `TF_PLUGIN_CACHE_DIR`, `TF_REGISTRY_DISCOVERY_RETRY`,
      `TF_TOKEN_<host>`, `TF_STATE_PERSIST_INTERVAL` (OpenTofu). `[TABLE]` `[CFG]` `[TOFU]`
1.3.22 **`TF_IN_AUTOMATION`** specifically: suppresses the "next step" hints, and is the marker
      CI should always set. `[CFG]`
1.3.23 The **CLI configuration file** (`~/.terraformrc` / `%APPDATA%\terraform.rc`):
      `plugin_cache_dir`, `disable_checkpoint`, `provider_installation` with
      `filesystem_mirror`, `network_mirror`, `dev_overrides`, `direct`, `include`/`exclude`.
      `[CFG]` `[HCL]`
1.3.24 **`dev_overrides`** as the provider-development workflow, and why it makes `init` refuse
      to write the lock file. `[TRAP]`
1.3.25 **Exit codes** across commands, and the automation contract they form. `[TABLE]` `[NUM]`

## §1.4 HCL2 — the syntax layer

1.4.1 **HCL is not YAML and not a DSL over JSON.** It is a two-layer language: a *syntax* layer
      (native HCL or JSON) over a *structural* layer (bodies, blocks, attributes) and an
      *expression* layer (HIL, now first-class). `[PROVE]`
1.4.2 The three primitives: **attribute** (`name = expression`), **block**
      (`type "label" "label" { body }`), and **comment** (`#`, `//`, `/* */`). Everything in a
      `.tf` file is one of the three. `[HCL]`
1.4.3 **Block labels are positional and typed by the block kind**: `resource` takes two
      (type, name), `variable` one, `terraform` none, `locals` none.
1.4.4 The **top-level block inventory**, complete: `terraform`, `provider`, `resource`,
      `data`, `variable`, `output`, `locals`, `module`, `moved`, `removed`, `import`,
      `check`, `ephemeral`, and — in test/query/stack files — `run`, `mock_provider`,
      `override_resource`, `override_module`, `override_data`, `list`, `action`,
      `component`, `deployment`, `identity_token`, `store`. `[TABLE]`
1.4.5 The **`terraform` block** and its arguments: `required_version`, `required_providers`,
      `backend`, `cloud`, `experiments`, `provider_meta`, and (OpenTofu) `encryption`.
      `[CFG]` `[TOFU]`
1.4.6 **`required_providers`** entry shape: `source` (`registry.terraform.io/hashicorp/aws` in
      full) and `version`. The local name is the map key, and it is what `provider` blocks and
      resource type prefixes bind to. `[HCL]` `[TRAP]`
1.4.7 **Version constraint syntax**, exhaustively: `=`, `!=`, `>`, `>=`, `<`, `<=`, `~>`, and
      comma-separated conjunction. `~> 5.0` means `>= 5.0, < 6.0`; `~> 5.1.2` means
      `>= 5.1.2, < 5.2.0`. The difference is the single most common version-pinning bug.
      `[NUM]` `[PROVE]` `[TRAP]`
1.4.8 **File loading rules**: every `*.tf` and `*.tf.json` in the directory, in no guaranteed
      order, merged into one namespace; **subdirectories are not loaded**. `[TRAP]`
1.4.9 **Override files**: `override.tf` and `*_override.tf` merge over the base definitions, and
      why they exist (generated configuration) and why you should not use them. `[TRAP]`
1.4.10 **OpenTofu's `.tofu` family**: `.tofu`, `.tofu.json`, `_override.tofu`, `.tofutest.hcl`,
      `.tofutest.json` — and the point, which is a module that ships different bodies to the two
      tools. When a `.tofu` file exists, the matching `.tf` is ignored. `[TOFU]` `[RESEARCH]`
1.4.11 **JSON syntax equivalence** (`.tf.json`): the exact mapping of blocks to nested objects,
      `${…}` for expressions, and why generators emit it. `[HCL]`
1.4.12 **Heredocs**: `<<EOT` and the indented `<<-EOT`, and why they are the wrong tool for
      anything with structure (use `jsonencode`/`yamlencode`). `[TRAP]`
1.4.13 **String templates**: `${…}` interpolation, `%{ if }`/`%{ for }` directives, `~` for
      whitespace stripping. `[HCL]`
1.4.14 **Quoted vs unquoted**: why `type = string` is bare, `version = "~> 5.0"` is quoted, and
      why `"${var.x}"` alone is a lint failure (`terraform fmt` will not fix it; TFLint will
      flag it). `[TRAP]`
1.4.15 **Identifier rules and reserved names**: `count`, `for_each`, `depends_on`, `provider`,
      `lifecycle`, `source`, `version`, `providers` may not be used as variable or output
      names in some positions. `[TRAP]`
1.4.16 **Comments and `#` as the canonical form** per the style guide.
1.4.17 The **style guide** as an explicit checklist: file names (`backend.tf`, `main.tf`,
      `outputs.tf`, `providers.tf`, `terraform.tf`, `variables.tf`, `locals.tf`,
      `override.tf`), alphabetical ordering of variables and outputs, argument ordering inside a
      resource (`count`/`for_each` first, then arguments, then blocks, then `lifecycle`, then
      `depends_on`), resource names as **descriptive nouns without the type in them**
      (`aws_db_instance.funds_ledger`, never `aws_db_instance.funds_ledger_db_instance`).
      `[TABLE]` `[SOURCE]` `[RESEARCH]`
1.4.18 The **`.gitignore` contract**: never commit `terraform.tfstate`, `terraform.tfstate.*`,
      `.terraform/`, `.terraform.tfstate.lock.info`, saved plan files, or secret-bearing
      `*.tfvars`; **always** commit `.terraform.lock.hcl`. `[TABLE]` `[SOURCE]` `[TRAP]`
      `[X-REF 17]`

## §1.5 The type system

1.5.1 Why there is a type system at all: HCL2 (0.12) replaced string-interpolation-everything
      with **cty**, a real value/type system, and that is why `for_each` over a map and
      `jsonencode` of an object work at all. `[VERSION-TRAP]`
1.5.2 The three **primitive types**: `string`, `number` (arbitrary precision decimal, **not**
      float64), `bool`. `[NUM]` `[TRAP]`
1.5.3 The three **collection types**: `list(T)`, `set(T)`, `map(T)` — homogeneous element type.
1.5.4 The three **structural types**: `object({ … })`, `tuple([ … ])`, and the `any`
      placeholder.
1.5.5 **`null`** as a value of every type, and its distinct meaning: *"argument not set, use the
      provider default"* — which is not the same as `""` or `0`. `[TRAP]`
1.5.6 **Unknown** as a fourth state alongside null and a value, visible in the plan as
      `(known after apply)`. It is a type-system feature, not a UI artifact. `[PROVE]`
1.5.7 **Type conversion rules**: automatic conversions HCL will perform (`"5"` → `5`, `true` →
      `"true"`, list → set, tuple → list, object → map when homogeneous), and the ones it will
      not. `[TABLE]`
1.5.8 **Set vs list semantics**, and why this matters more than anything else in the type
      system: sets are **unordered and deduplicated**, so `toset()` on a list with duplicates
      silently loses elements, and a set's iteration order in `for_each` keys is the *value
      itself*. `[PROVE]` `[TRAP]`
1.5.9 **Type constraints on variables**, including nested: `list(object({ name = string, cidr =
      string }))`. `[HCL]`
1.5.10 **`optional()`** in object type constraints, with and without a default:
      `optional(string)`, `optional(number, 30)`. The defaults are applied *after* conversion.
      `[HCL]` `[NUM]`
1.5.11 **`any`** and why it is contagious: one `any` in a nested constraint disables checking
      for that subtree and defers every error to apply time. `[TRAP]`
1.5.12 **Output type constraints** — `output` blocks gained explicit `type` in **1.15**.
      `[VERSION-TRAP]` `[RESEARCH]`
1.5.13 **Type-conversion functions**: `tostring`, `tonumber`, `tobool`, `tolist`, `toset`,
      `tomap`, plus `can()`, `try()` and `convert()` (Terraform 1.15 / OpenTofu 1.13).
      `[TABLE]` `[RESEARCH]`
1.5.14 **Sensitivity as a type-system property**: `sensitive(x)` and `nonsensitive(x)`, and the
      fact that sensitivity *propagates through expressions* — a `local` derived from a
      sensitive variable is itself sensitive. `[PROVE]` `[TRAP]`
1.5.15 **Ephemerality as a second such property** (1.10+): ephemeral values propagate the same
      way, and any expression touching one becomes ephemeral, which is why they cannot reach
      `output` or state. `[PROVE]` `[RESEARCH]`
1.5.16 The **marks** mechanism underneath both — cty value marks — named here and explained in
      §3.12. `[X-REF §3.12]`

## §1.6 Expressions

1.6.1 **Operators**, complete with precedence: `!`, `-` (unary), `*`, `/`, `%`, `+`, `-`, `>`,
      `>=`, `<`, `<=`, `==`, `!=`, `&&`, `||`, and the conditional `? :`. `[TABLE]` `[NUM]`
1.6.2 **Equality is deep and typed**: `[1,2] == [1,2]` is true; `1 == "1"` is true by conversion;
      `{a=1} == {a=1}` is true. `[PROVE]`
1.6.3 **The conditional expression** and its trap: **both branches must be the same type**, and
      **both branches are evaluated for type purposes**, so a conditional cannot be used to guard
      an invalid index. `[TRAP]` `[PROVE]`
1.6.4 **`for` expressions** in all four shapes: list output `[for … in … : …]`, object output
      `{for … in … : k => v}`, with `if` filtering, and with two iterator variables over a map
      (`for k, v in …`). `[HCL]`
1.6.5 **`for` over a map produces pairs; over a list produces index/value**; the `...` grouping
      modifier for `{for … : k => v...}` producing lists as values. `[HCL]` `[TRAP]`
1.6.6 **Splat expressions**: `aws_instance.gateway[*].id`, the legacy attribute-only splat
      `.*.`, and the fact that a splat over a non-list wraps it. `[TRAP]`
1.6.7 **Index and attribute access**: `list[0]`, `map["key"]`, `obj.attr`, and the
      `try(map["k"], default)` idiom for absent keys. `[HCL]`
1.6.8 **`can()` and `try()`**: what they catch (evaluation errors) and what they do not
      (unknown values, provider errors). `[TRAP]`
1.6.9 **Dynamic blocks**: `dynamic "ingress" { for_each = … content { … } }`, the `ingress.key`
      / `ingress.value` iterator, the `iterator` argument to rename it, and nesting them.
      `[HCL]`
1.6.10 **When `dynamic` is wrong**: for two or three static blocks it makes the configuration
      unreadable for no gain, and it defeats `terraform fmt`-level review. The style guide's own
      position. `[TRAP]`
1.6.11 **References**, exhaustively: `var.x`, `local.x`, `resource_type.name.attr`,
      `data.type.name.attr`, `module.name.output`, `each.key`/`each.value`, `count.index`,
      `self.attr` (provisioners and `connection` only), `path.module`, `path.root`, `path.cwd`,
      `terraform.workspace`, `terraform.applying` (1.10+), and `ephemeral.type.name.attr`.
      `[TABLE]` `[CFG]`
1.6.12 **`terraform.applying`** — true during apply, false during plan — and its one legitimate
      use: fetching a secret only when it will actually be used. `[RESEARCH]`
1.6.13 **`path.module` vs `path.root` vs `path.cwd`**, and the bug each mix-up causes when a
      module reads a file. `[TRAP]`
1.6.14 **Resource addresses** as a formal grammar: `module.a[0].aws_instance.b["key"]`, used
      identically by `-target`, `state mv`, `moved`, `import`, `removed`, and the JSON plan.
      Learn it once. `[PROVE]` `[TABLE]`
1.6.15 **Operator/function evaluation is eager, and there is no short-circuit guarantee** you
      can rely on for validity. `[TRAP]`

## §1.7 Functions

1.7.1 There are **no user-defined functions in HCL** — the deliberate design choice, its
      rationale, and the three escapes: `locals`, modules, and **provider-defined functions**.
      `[TRAP]`
1.7.2 **Numeric**: `abs`, `ceil`, `floor`, `log`, `max`, `min`, `parseint`, `pow`, `signum`.
      `[TABLE]`
1.7.3 **String**: `chomp`, `endswith`, `format`, `formatlist`, `indent`, `join`, `lower`,
      `regex`, `regexall`, `replace`, `split`, `startswith`, `strcontains`, `strrev`, `substr`,
      `title`, `trim`, `trimprefix`, `trimsuffix`, `trimspace`, `upper`. `[TABLE]`
1.7.4 **`format` and `formatlist`** verb reference (`%s`, `%d`, `%q`, `%v`, `%%`, index
      modifiers) — the thing everyone re-derives from examples. `[TABLE]`
1.7.5 **Collection**: `alltrue`, `anytrue`, `chunklist`, `coalesce`, `coalescelist`, `compact`,
      `concat`, `contains`, `distinct`, `element`, `flatten`, `index`, `keys`, `length`,
      `lookup`, `matchkeys`, `merge`, `one`, `range`, `reverse`, `setintersection`,
      `setproduct`, `setsubtract`, `setunion`, `slice`, `sort`, `sum`, `transpose`, `values`,
      `zipmap`. `[TABLE]`
1.7.6 **`contains()` now handles `null`** (Terraform 1.16). `[RESEARCH]` `[VERSION-TRAP]`
1.7.7 **`element()` accepts negative indices in OpenTofu 1.10+**; in Terraform it wraps modulo
      length. `[TOFU]` `[RESEARCH]`
1.7.8 **`lookup` vs direct index vs `try`** — three ways to read a possibly-absent map key, with
      the failure mode of each. `[TABLE]` `[TRAP]`
1.7.9 **`flatten` + `setproduct`** as the canonical nested-`for_each` idiom, worked on
      QuizStakes' (service × environment) matrix. `[HCL]` `[PROVE]`
1.7.10 **`merge` and deep-merge's absence**: HCL has no deep merge; the recursive-`merge`
      workarounds and why they are fragile. `[TRAP]`
1.7.11 **Encoding**: `base64decode`, `base64encode`, `base64gzip`, `csvdecode`, `jsondecode`,
      `jsonencode`, `textdecodebase64`, `textencodebase64`, `urlencode`, `yamldecode`,
      `yamlencode`. `[TABLE]`
1.7.12 **`jsonencode` beats a heredoc** for IAM policies and container definitions — and
      `aws_iam_policy_document` beats both. `[TRAP]` `[X-REF 18]`
1.7.13 **Filesystem**: `abspath`, `dirname`, `pathexpand`, `basename`, `file`, `fileexists`,
      `fileset`, `filebase64`, `templatefile`. All evaluated **on the machine running
      Terraform**, at **parse/eval time**. `[TRAP]`
1.7.14 **`templatefile` vs the removed `template_file` data source** — the migration everyone
      still has pending. `[VERSION-TRAP]`
1.7.15 **Date/time**: `formatdate`, `plantimestamp`, `timeadd`, `timecmp`, `timestamp`.
      `timestamp()` changes every run and therefore **forces perpetual diffs** unless paired
      with `ignore_changes`; `plantimestamp()` is stable within a plan. `[TRAP]` `[NUM]`
1.7.16 **Hash/crypto**: `base64sha256`, `base64sha512`, `bcrypt`, `filebase64sha256`,
      `filemd5`, `filesha1`, `filesha256`, `filesha512`, `md5`, `rsadecrypt`, `sha1`,
      `sha256`, `sha512`, `uuid`, `uuidv5`. `[TABLE]`
1.7.17 **`uuid()` is the same class of bug as `timestamp()`** — non-deterministic, so it belongs
      in `random_uuid` (a resource, therefore stateful) not in an expression. `uuidv5()` is
      deterministic and is usually what you wanted. `[TRAP]` `[PROVE]`
1.7.18 **`bcrypt()` in configuration writes a hash to state and is non-deterministic** — the
      classic "why does my plan always change" answer. `[TRAP]`
1.7.19 **IP/network**: `cidrhost`, `cidrnetmask`, `cidrsubnet`, `cidrsubnets`. Worked against
      QuizStakes' three-AZ layout. `[NUM]` `[X-REF 18]`
1.7.20 **`cidrsubnets` supports IPv6 prefix extensions in OpenTofu 1.13**. `[TOFU]` `[RESEARCH]`
1.7.21 **Type conversion and validation**: `can`, `convert` (1.15+), `nonsensitive`, `sensitive`,
      `ephemeralasnull`, `tobool`, `tolist`, `tomap`, `tonumber`, `toset`, `tostring`, `try`.
      `[TABLE]`
1.7.22 **`terraform`-namespaced functions**: `decode_tfvars`, `encode_tfvars`, `encode_expr` —
      what they are for (tooling, not configuration). `[RESEARCH]`
1.7.23 **Provider-defined functions**: syntax `provider::<local-name>::<name>(…)`, requires
      **Terraform 1.8+** and a provider built on terraform-plugin-framework's `Function`
      interface (`Definition`, `Run`). Real examples worth naming. `[SOURCE]` `[RESEARCH]`
1.7.24 **`terraform metadata functions -json`** as the machine-readable inventory of every
      function the current binary has — the way to answer "does this version have `strcontains`?"
      `[CLI]`
1.7.25 **The functions that do not exist and are constantly assumed to**: no `deepmerge`, no
      user functions, no loops outside `for`/`for_each`/`dynamic`, no `if` statement, no shell
      execution in an expression, no HTTP call in an expression (that is the `http` **data
      source**). `[TABLE]` `[TRAP]`

## §1.8 Variables

1.8.1 The **`variable` block** arguments, complete: `type`, `default`, `description`,
      `sensitive`, `nullable`, `ephemeral` (1.10+), `deprecated` (1.15+), and one or more
      `validation` blocks. `[TABLE]` `[CFG]` `[RESEARCH]`
1.8.2 **Required vs optional**: a variable with no `default` is required. There is no
      `required = true`. `[TRAP]`
1.8.3 **`nullable = false`** (1.1+) and what it changes: passing `null` explicitly then falls
      back to the default rather than setting null. `[NUM]` `[TRAP]`
1.8.4 **`sensitive = true`**: redacts the value from plan/apply output and from any expression
      derived from it. It does **not** encrypt, and it does **not** keep the value out of state.
      `[TRAP]`
1.8.5 **`ephemeral = true`** (1.10+): the value may not be persisted at all, so it may only be
      used in ephemeral contexts and write-only arguments. `[RESEARCH]`
1.8.6 **`deprecated = "…"`** (1.15+): emits a warning when the variable is set. The migration
      tool for a module's own API. `[RESEARCH]` `[VERSION-TRAP]`
1.8.7 **`validation` blocks**: `condition` + `error_message`, multiple blocks per variable, and
      the fact that since 1.9 a condition **may reference other variables**. `[HCL]` `[NUM]`
1.8.8 Validation idioms worth naming: `can(regex(…))`, `contains([…], var.x)`,
      `length(var.x) > 0`, `alltrue([for … ])`, and range checks. Worked on QuizStakes'
      `heap_size_gb` (2, 4, 6, 8, 12 are the only legal values per Appendix B). `[HCL]` `[NUM]`
1.8.9 **The precedence order for variable values**, exact and complete, lowest to highest:
      environment `TF_VAR_*` → `terraform.tfvars` → `terraform.tfvars.json` →
      `*.auto.tfvars`/`*.auto.tfvars.json` **in lexical order** → `-var`/`-var-file` **in
      command-line order**. `[TABLE]` `[NUM]` `[PROVE]`
1.8.10 **`terraform.tfvars` is loaded automatically; `prod.tfvars` is not.** The
      `.auto.tfvars` suffix is the only auto-loading naming rule besides the canonical file.
      `[TRAP]`
1.8.11 **Variables are not available in every context**: not in `backend` blocks, not in
      `terraform.required_version`, and (in Terraform) not in module `source` before 1.15.
      OpenTofu's **early evaluation** (1.8) lifts the first two. `[TOFU]` `[VERSION-TRAP]`
      `[RESEARCH]`
1.8.12 **Why `backend` cannot take variables** — the chicken-and-egg: the backend must be
      initialised before the configuration is evaluated. And the workaround: partial
      configuration plus `-backend-config`. `[PROVE]` `[CFG]`
1.8.13 **`-var-file` with a non-existent file fails; a missing required variable prompts**
      unless `-input=false`, in which case it errors. The CI implication. `[CLI]` `[TRAP]`
1.8.14 **Variables in test files**: a `variables` block at file level, per-`run` overrides, and
      the requirement (1.13 upgrade note) that external variables used in test files have a
      matching `variable` block declared **in the test file**. `[RESEARCH]` `[VERSION-TRAP]`
1.8.15 **Secrets must not arrive via variables in this estate.** Appendix B.4 says secrets live
      in a managed store; the correct pattern is an `ephemeral` data source or write-only
      argument, not `TF_VAR_db_password`. `[TRAP]` `[X-REF 13]`

## §1.9 Locals

1.9.1 The **`locals` block** — plural, multiple blocks allowed, all merged; referenced as
      `local.name` (singular). The plural/singular mismatch is a real stumbling block. `[TRAP]`
1.9.2 Locals are **evaluated lazily and may reference each other**, but not cyclically.
1.9.3 What locals are for: naming a repeated expression once
      (`local.common_tags`, `local.name_prefix`), and encoding a decision table as a map so the
      configuration reads as data. `[HCL]`
1.9.4 What locals are **not** for: hiding complexity that should be a module input, or building
      a 200-line `merge`/`for` pyramid that no reviewer can evaluate. `[TRAP]`
1.9.5 Locals **cannot be overridden** from outside and do not appear in state.
1.9.6 The **`local.common_tags`** pattern worked for QuizStakes: `owner`, `environment`,
      `cost-center`, `service`, `data-classification` (PII vs not — Appendix B.2 makes this a
      real distinction). `[HCL]` `[X-REF 18]`
1.9.7 **Sensitivity and ephemerality propagate into locals** — a local built from a sensitive
      variable is sensitive, and Terraform will refuse to output it without `sensitive = true`.
      `[PROVE]`

## §1.10 Outputs

1.10.1 The **`output` block** arguments: `value`, `description`, `sensitive`, `ephemeral`
      (1.10+), `depends_on`, `precondition` (via `lifecycle`), `type` (1.15+), `deprecated`
      (1.15+). `[TABLE]` `[CFG]` `[RESEARCH]`
1.10.2 Outputs serve **three distinct audiences**, and conflating them is a design error: a
      module's return value, a root module's human/CI-readable result, and the payload other
      configurations read via `terraform_remote_state`. `[TABLE]`
1.10.3 **Root outputs are stored in state** — including sensitive ones, unredacted. This is the
      leak the current guide correctly warns about and must now be explained mechanically.
      `[TRAP]` `[PROVE]`
1.10.4 **`sensitive = true` on an output** hides it from CLI output and forces `-raw`/`-json` to
      read it. It is a display control. `[TRAP]`
1.10.5 **`ephemeral = true` on an output** (1.10+) is the real answer for a secret: it is not
      persisted, and it may only be consumed by an ephemeral context in the calling module.
      `[RESEARCH]`
1.10.6 **`output` `precondition`** as a module's postcondition on itself — assert the invariant
      before the caller sees the value. `[HCL]`
1.10.7 **`depends_on` on an output** and the one case it is needed: an output whose value is
      valid only after a resource the value does not reference has completed. `[TRAP]`
1.10.8 **Outputs are the module's public API**, so removing or renaming one is a breaking
      change, and `deprecated` (1.15+) is how you stage it. `[RESEARCH]`
1.10.9 `terraform output -json` as the CI integration point; `-raw` for a single scalar; the
      exit code when the output does not exist. `[CLI]`
1.10.10 **Outputs of a `count`/`for_each` module** are maps/lists and must be indexed —
      `module.service_runtime["FundsLedger"].task_role_arn`. `[HCL]`

## §1.11 Providers

1.11.1 **What a provider is**: a separate executable, written in Go, that Terraform Core launches
      as a subprocess and speaks gRPC to over a `go-plugin` handshake. It owns *all* knowledge of
      resource types, their schemas and their CRUD. Core knows nothing about AWS. `[PROVE]`
      `[SOURCE]`
1.11.2 The **three provider tiers** in the registry — Official (HashiCorp/IBM), Partner,
      Community — and what the badge actually guarantees. `[TABLE]`
1.11.3 **Source addresses**: `[<HOSTNAME>/]<NAMESPACE>/<TYPE>`, defaulting to
      `registry.terraform.io`; `hashicorp/aws` is `registry.terraform.io/hashicorp/aws`.
      OpenTofu defaults to `registry.opentofu.org`. `[CFG]` `[TOFU]`
1.11.4 **The local name is a per-module alias**, not the type: `required_providers { aws = {…} }`
      binds `aws_*` resource types and `provider "aws"` blocks. Renaming it is legal and
      confusing. `[TRAP]`
1.11.5 **Provider installation**: registry protocol discovery, platform-specific package
      download, checksum verification against the lock file, unpack into
      `.terraform/providers/<host>/<ns>/<type>/<version>/<os_arch>/`. `[FLOW]`
1.11.6 **`TF_PLUGIN_CACHE_DIR`** and the CLI-config `plugin_cache_dir`: one copy per version per
      machine instead of one per working directory. The disk arithmetic for a 50-module estate
      makes this mandatory in CI. `[COST]` `[NUM]` `[CFG]`
1.11.7 **OpenTofu's global provider-cache lock** (1.10) makes a shared cache safe under
      concurrent runs; Terraform's cache is documented as not concurrency-safe. `[TOFU]`
      `[RESEARCH]` `[TRAP]`
1.11.8 **Filesystem and network mirrors** (`terraform providers mirror`, `filesystem_mirror`,
      `network_mirror`) as the air-gapped/regulated-estate answer, which QuizStakes' compliance
      posture would likely require. `[CFG]` `[X-REF 13]`
1.11.9 **OCI registries as a provider and module source** — OpenTofu 1.10, with
      repository-scoped tokens improved in 1.13. `[TOFU]` `[RESEARCH]`
1.11.10 **Provider *configuration* vs provider *requirement*** — `provider "aws" { region = … }`
      versus `required_providers`. A module declares requirements; the root configures.
      `[PROVE]` `[TRAP]`
1.11.11 **Provider configuration is not versioned in state**, but the provider *version* used to
      write each resource is (`schema_version` per instance). `[X-REF §3.8]`
1.11.12 **Authentication is the provider's business, not Terraform's.** The AWS provider uses
      the same chain as the SDK (env vars → shared config → IMDS → SSO), which is why
      `AWS_PROFILE` works and why nothing in Terraform "logs you in". `[X-REF 18]` `[TRAP]`
1.11.13 **`assume_role` in the provider vs in the backend** — two independent credential
      resolutions in one run, and the failure where one works and the other does not. `[TRAP]`
1.11.14 **Provider aliases**: `alias = "eu_west_2"`, referenced as `provider = aws.eu_west_2`.
      The default (unaliased) configuration and the implied-empty-default rule when every block
      is aliased. `[HCL]` `[SOURCE]`
1.11.15 **Passing providers to modules**: the `providers = { aws = aws.eu_west_2 }` map,
      implicit inheritance of the default configuration, and `configuration_aliases` in the
      child's `required_providers` for modules that need a named alias. `[HCL]` `[SOURCE]`
1.11.16 **Provider inheritance rules, stated precisely**: a child module inherits *default*
      provider configurations implicitly, inherits nothing when `providers` is set explicitly,
      and never inherits `source`/`version` requirements. `[PROVE]` `[TRAP]`
1.11.17 **A module should not contain `provider` blocks.** The reason: a provider configuration
      inside a module cannot be removed while resources still exist, which makes the module
      undestroyable in the wrong order. HashiCorp's own guidance. `[TRAP]` `[PROVE]`
1.11.18 **Provider `for_each`** — OpenTofu 1.9's answer to "one configuration per region without
      copy-paste". Terraform has no equivalent; the workaround is a module per region or a
      Stack. `[TOFU]` `[VERSION-TRAP]` `[RESEARCH]`
1.11.19 **Multi-region in practice for QuizStakes**: `eu-west-1` primary, `eu-west-2` for the
      7-year ledger archive, plus `us-east-1` **only** for the global services that require it
      (ACM certificates for CloudFront). Three aliases, one root. `[HCL]` `[X-REF 18]`
1.11.20 **`provider_meta`** — the rarely-seen block letting a module declare metadata to its
      provider; named and bounded.
1.11.21 **Built-in providers**: `terraform.io/builtin/terraform` (the `terraform_remote_state`
      data source and `terraform_data` resource). They have no version and are never downloaded.
      `[TRAP]`
1.11.22 **Provider bugs are your bugs**: pinning, reading provider changelogs before an upgrade,
      and the fact that a provider minor release can change whether an attribute forces
      replacement. This is the current guide's best trap and it must survive. `[TRAP]`
      `[VERSION-TRAP]`

## §1.12 The dependency lock file

1.12.1 **`.terraform.lock.hcl`** — location (working directory root, beside the `.tf` files),
      purpose (reproducible provider selection), and the rule: **commit it**. `[SOURCE]`
1.12.2 It locks **providers only** — not modules, not Terraform itself. Module versions are
      pinned by `version` constraints and, for Git sources, by ref. `[TRAP]`
1.12.3 The **`provider` block** in the lock file: `version` (the exact selection),
      `constraints` (informational, recorded for diagnostics), `hashes` (a list).
      `[HCL]` `[SOURCE]`
1.12.4 **`zh:` vs `h1:`**: `zh:` is the legacy SHA-256 **of the official `.zip` package**, valid
      only for registry installs; `h1:` is the current scheme, computed **over package
      contents**, so it verifies a zip, an unpacked directory or a recompressed archive. Terraform
      opportunistically adds `h1:` as it sees new platforms. `[PROVE]` `[SOURCE]` `[RESEARCH]`
1.12.5 **The mixed-platform failure**: a lock file created on `darwin_arm64` lacks the
      `linux_amd64` hashes, so CI fails with *"provider … does not match any of the checksums"*.
      This is the single most common lock-file incident. `[TRAP]` `[DIAG]` `[INCIDENT]`
1.12.6 **The fix**: `terraform providers lock -platform=linux_amd64 -platform=darwin_arm64
      -platform=linux_arm64`, committed. `[CLI]` `[SOURCE]`
1.12.7 **OpenTofu 1.12 writes both `zh:` and `h1:` at `init`**, which removes most of the need
      for the manual command. `[TOFU]` `[RESEARCH]`
1.12.8 **`init -upgrade`** ignores the recorded selections and re-solves the constraints;
      without it, `init` honours the lock even when a newer version satisfies the constraint.
      `[SOURCE]` `[PROVE]`
1.12.9 **`-lockfile=readonly`** for CI: fail rather than silently update. `[CFG]`
1.12.10 **What a lock-file diff means in review**: a version bump is a *behavioural* change to
      every resource that provider owns, and it must be reviewed with a plan, not waved through.
      `[TRAP]` `[X-REF 17]`
1.12.11 **`terraform providers` (bare)** prints the requirement tree, including which module
      demanded which constraint — the tool for "why did it pick 5.62?". `[CLI]`
1.12.12 **Lock-file conflicts in Git** and how to resolve them (re-run `init -upgrade`, never
      hand-merge hashes). `[TRAP]` `[X-REF 17]`

## §1.13 Resources

1.13.1 The **`resource` block**: `resource "<TYPE>" "<NAME>" { … }`, where the type's prefix
      binds to a provider local name and the pair (type, name) is the address within the module.
1.13.2 **Arguments vs attributes**: arguments are what you set; attributes are what you can read;
      many are both, and some are read-only (`id`, `arn`). The schema decides. `[TABLE]`
1.13.3 **`id`** — every managed resource has one, it is a string, it is provider-defined, and it
      is what `import` matched on before **resource identity** (1.12+) existed. `[RESEARCH]`
1.13.4 **Resource identity** (1.12+): a provider-defined *set* of attributes uniquely naming the
      object — e.g. an S3 bucket is `account_id` + `bucket` + `region`. `import` blocks accept
      `identity` as an alternative to `id`, and `terraform state identities` inspects them.
      `[RESEARCH]` `[VERSION-TRAP]`
1.13.5 **The four resource actions in a plan**: create, update in place, destroy, and
      **replace** (destroy-then-create or create-then-destroy). Plus **read** for data sources
      and **no-op**. The symbols: `+`, `~`, `-`, `-/+`, `+/-`, `<=`. `[TABLE]` `[NUM]`
1.13.6 **Why replacement happens**: the provider schema marks an attribute as forcing
      replacement (`ForceNew: true` in SDKv2, `RequiresReplace` plan modifier in the framework).
      Core does not decide; the provider does, in `PlanResourceChange`. `[PROVE]` `[SOURCE]`
1.13.7 **The `# forces replacement` annotation** in plan output, and that reading it is the
      entire skill of reviewing a plan. `[DIAG]`
1.13.8 **Tainting** — the old `terraform taint` marking an instance for replacement in state —
      superseded by `apply -replace=ADDRESS`, which does it **in the plan** so it is reviewable.
      `[VERSION-TRAP]`
1.13.9 **`tainted` still appears in state** when a create-time provisioner fails, and what to do
      about it. `[DIAG]` `[SURGERY]`
1.13.10 **Partial apply and the create-then-fail case**: the resource exists remotely, Terraform
      recorded it (or did not), and the next plan's behaviour in each case. `[FLOW]` `[TRAP]`
1.13.11 **`terraform_data`** (1.4+): a built-in resource with `input`, `output`, `triggers_replace`
      and (1.16) a `store` block for ephemeral/sensitive values. The replacement for
      `null_resource`, requiring no provider. `[RESEARCH]` `[VERSION-TRAP]`
1.13.12 **`null_resource`** and `random_*`, `time_*`, `tls_*`, `local_file`, `external`,
      `http` — the "utility providers" whose resources exist to hold state rather than to own
      infrastructure, and the trap that `local_file` writes secrets to disk. `[TABLE]` `[TRAP]`
1.13.13 **Resource behaviour is not uniform across providers**: some APIs are eventually
      consistent, some return before the object is usable, some silently normalise your input.
      Each produces a distinct symptom (§3.15). `[X-REF 22]`
1.13.14 **`ephemeral` blocks** as the third block kind alongside `resource` and `data`: opened,
      optionally renewed, closed within one operation; never in state. `[RESEARCH]`
1.13.15 **`list` blocks** in `*.tfquery.hcl` (1.14) — a fourth kind, for querying rather than
      managing. `[RESEARCH]`
1.13.16 **`action` blocks** (1.14) — a fifth kind, for imperative provider operations invoked
      from `lifecycle.action_trigger` or `-invoke`. `[RESEARCH]`

## §1.14 Data sources

1.14.1 The **`data` block** and what it is: a **read** performed by the provider, whose result is
      available to expressions. Address `data.<TYPE>.<NAME>`.
1.14.2 **When data sources are read**: during **plan** if their arguments are known, and deferred
      to **apply** if any argument is unknown — which is why an unknown-dependent data source
      turns everything downstream unknown. `[PROVE]` `[TRAP]`
1.14.3 **Data sources are in state** (as `mode: "data"` instances) but are re-read every plan;
      they are a cache with a one-run lifetime. `[X-REF §3.8]`
1.14.4 **`depends_on` on a data source** and the one case it is needed: the data source reads
      something a resource creates but does not reference.
1.14.5 **The `data` + `count`/`for_each` combination**, and the cost: 200 data-source reads is
      200 API calls on every plan. `[COST]` `[NUM]`
1.14.6 **`terraform_remote_state`** — the built-in data source that reads another configuration's
      state. Arguments: `backend`, `config`, `workspace`, `defaults`. `[HCL]`
1.14.7 **Why `terraform_remote_state` is a coupling you should minimise**: it needs read access to
      the *whole* other state (including its secrets), it breaks if the other configuration
      renames an output, and it creates an implicit deploy ordering with no enforcement.
      `[TRAP]` `[PROVE]` `[X-REF 13]`
1.14.8 **The alternatives, ranked**: a provider data source that queries the real API
      (`aws_vpc` by tag), **SSM Parameter Store / a published contract**, explicit input
      variables, or a Stack. State the recommendation. `[TABLE]`
1.14.9 **Scoped data sources inside `check` blocks** — a data source that exists only for
      assertion and does not become a dependency. `[RESEARCH]`
1.14.10 **`external` data source** as the escape hatch (a program returning JSON on stdout) and
      why it makes the plan non-reproducible. `[TRAP]`
1.14.11 **`http` data source** for a health probe at plan time, its timeout behaviour, and the
      fact that it turns a plan into a network-dependent operation. `[TRAP]` `[X-REF 10]`
1.14.12 **The self-reference trap**: a data source reading a resource *the same configuration
      manages* — it will read the pre-apply value at plan time, and the result is a diff that
      never converges. Use the resource attribute directly. `[TRAP]` `[INCIDENT]`

## §1.15 Meta-arguments

1.15.1 The **five meta-arguments** available on `resource`: `count`, `for_each`, `depends_on`,
      `provider`, `lifecycle`; on `module`: the same five minus `lifecycle` (plus `source`,
      `version`, `providers`); on `data`: `count`, `for_each`, `depends_on`, `provider`, and
      `lifecycle` limited to `precondition`/`postcondition`. `[TABLE]`
1.15.2 **`count`**: an integer; instances addressed `[0]`, `[1]`, …; `count.index` available in
      the body; `count = 0` creates nothing. `[HCL]`
1.15.3 **`count` as a conditional**: `count = var.enable_bonus_service ? 1 : 0` and the
      resulting `[0]` indexing everywhere downstream. The idiom, and why `one()` cleans it up.
      `[HCL]` `[TRAP]`
1.15.4 **`for_each`**: a **map** or a **set of strings**; instances addressed `["key"]`;
      `each.key` and `each.value` in the body. `[HCL]`
1.15.5 **`for_each` over a list is an error** — you must `toset()` it, and doing so makes the
      *value* the key, which is why the elements must be stable strings. `[TRAP]` `[PROVE]`
1.15.6 **The index-instability catastrophe**, worked properly: with `count`, removing the middle
      element of a list re-indexes every later element, and Terraform plans a destroy+create for
      each — because state binds objects to `[n]`, not to identity. Shown as a before/after
      state address table for QuizStakes' service list. `[PROVE]` `[TABLE]` `[TRAP]` `[INCIDENT]`
1.15.7 **Why `for_each` fixes it**: the key is part of the address, so adding or removing a
      service touches only that service. `[PROVE]`
1.15.8 **The rule**: `count` for a genuine on/off or for N identical unnamed things;
      `for_each` for anything with identity. `[TRAP]`
1.15.9 **`for_each` keys must be known at plan time.** A key derived from a resource attribute
      that does not yet exist produces *"The 'for_each' value depends on resource attributes
      that cannot be determined until apply"* — and the fixes: derive keys from configuration,
      use `-target` as a one-off staging step, or split the apply. `[DIAG]` `[TRAP]`
      `[INCIDENT]`
1.15.10 **`for_each` on a `module`** (0.13+) and the same rules.
1.15.11 **Changing `count` to `for_each`** on an existing resource: every instance would be
      destroyed and recreated unless you write `moved` blocks. The exact `moved` block set for
      the QuizStakes service list. `[HCL]` `[SURGERY]`
1.15.12 **`depends_on`**: a list of *addresses* (not strings, not attributes), creating an
      explicit edge. Only for dependencies not visible in an expression. `[HCL]`
1.15.13 **`depends_on` on a module** applies to every resource inside it, which is a heavier
      hammer than people expect and can serialise a whole subgraph. `[PROVE]` `[TRAP]`
1.15.14 **Why over-using `depends_on` is costly**: it removes parallelism, hides the real
      relationship, and survives long after the reason is forgotten. The current guide's
      "maintainability debt" point, with the parallelism arithmetic added. `[PROVE]` `[COST]`
1.15.15 **`provider`** meta-argument: selecting a non-default configuration by
      `provider = aws.eu_west_2`.
1.15.16 **`lifecycle`** — the full inventory, each as its own leaf below.
1.15.17 **`create_before_destroy = true`**: reverses the replace order. What it fixes (downtime,
      and "name already exists" on replacement) and what it breaks (unique-name constraints,
      capacity limits, and the fact that it **propagates to dependencies**). `[PROVE]` `[TRAP]`
1.15.18 **`prevent_destroy = true`**: makes any plan that would destroy the object an **error**,
      not a warning. Its blind spot: it does not stop `terraform destroy` of the whole
      configuration from *failing*, it just makes it fail — and it does not survive the resource
      block being deleted from the configuration. `[TRAP]` `[PROVE]`
1.15.19 **`prevent_destroy` must be a literal in Terraform; OpenTofu 1.12 allows references.**
      `[TOFU]` `[RESEARCH]` `[VERSION-TRAP]`
1.15.20 **`ignore_changes`**: a list of attribute paths, or `all`. Semantics: ignore *drift* in
      those attributes on **update**; they are still used on **create**. `[SOURCE]` `[PROVE]`
1.15.21 **`ignore_changes` is a declaration of shared ownership**, and every use should name the
      other owner in a comment — an autoscaler owning `desired_count`, a deploy pipeline owning
      the container image tag, an operator owning `ClientRestrictions`' policy document.
      `[TRAP]`
1.15.22 **`ignore_changes = all`** and why it is almost always wrong: it silently accepts every
      future drift, including a deletion of your security-group rules. `[TRAP]`
1.15.23 **`replace_triggered_by`** (1.2+): a list of references — a resource, an instance, or an
      *attribute* — whose change forces replacement of this resource. The canonical use: force a
      task-definition redeploy when a config hash changes. `[HCL]` `[RESEARCH]`
1.15.24 **`precondition`** and **`postcondition`** (1.2+): `condition` + `error_message` inside
      `lifecycle`. Preconditions run before the resource is planned; postconditions after it is
      created/read. Both are **errors**, unlike `check`. `[HCL]` `[SOURCE]`
1.15.25 **Where each validation mechanism belongs** — the table that settles the confusion:
      `variable.validation` (input contract), `precondition` (assumption about the world),
      `postcondition` (guarantee about what I made), `check` (continuous non-blocking
      assertion), `terraform test` (behaviour of the module), policy-as-code (organisational
      rule). `[TABLE]` `[PROVE]`
1.15.26 **`destroy = false`** (Terraform 1.16, OpenTofu 1.12): remove from state without
      destroying the remote object. The declarative `state rm`. `[RESEARCH]` `[VERSION-TRAP]`
1.15.27 **`action_trigger`** (1.14/1.16): `events` from `before_create`, `after_create`,
      `before_update`, `after_update`, `before_destroy`, `after_destroy`; `actions` list;
      optional `condition`; `on_failure` = `halt` | `taint` | `continue`. `[HCL]` `[RESEARCH]`
1.15.28 **`lifecycle` cannot use variables** (except OpenTofu's dynamic `prevent_destroy`) —
      the block is evaluated too early. `[TRAP]` `[TOFU]`

## §1.16 Modules

1.16.1 **A module is a directory of `.tf` files.** The root module is the directory you run in.
      There is no other definition. `[PROVE]`
1.16.2 The **`module` block**: `source` (required), `version` (registry sources only), inputs as
      arbitrary arguments, plus `count`, `for_each`, `depends_on`, `providers`.
      `[TABLE]` `[CFG]`
1.16.3 **Module addressing**: `module.<NAME>.<OUTPUT>` from outside;
      `module.<NAME>[<KEY>].<OUTPUT>` when iterated; and resources inside are addressed
      `module.<NAME>.<TYPE>.<NAME>` in state and `-target`.
1.16.4 **A module is a namespace, not an isolation boundary.** It shares the provider, the
      state file and the graph with its caller. Nothing about a module is sandboxed. `[TRAP]`
      `[PROVE]`
1.16.5 **Module source types**, complete: local path (`./modules/x`), Terraform Registry
      (`namespace/name/provider`), a private registry host, GitHub/Bitbucket shorthand, generic
      **Git** (`git::https://…?ref=v1.4.0`, `//subdir`), **Mercurial**, **HTTP archive**, **S3**
      (`s3::https://…`), **GCS**, and (OpenTofu 1.10) **OCI**. `[TABLE]` `[CFG]` `[TOFU]`
1.16.6 **`ref=` is the only version pin for a Git source** — and `ref=main` is not a pin. Use a
      tag, or a commit SHA for a regulated estate. `[TRAP]` `[X-REF 17]`
1.16.7 **The `//subdir` double-slash syntax** for a module inside a monorepo, and how often it
      is mistyped. `[TRAP]`
1.16.8 **Dynamic `source`/`version`** — Terraform 1.15 allows variables and locals in both;
      OpenTofu allows it via early evaluation since 1.8. Before that they had to be literal.
      `[VERSION-TRAP]` `[TOFU]` `[RESEARCH]`
1.16.9 **`terraform init` fetches modules to `.terraform/modules`** and records them in
      `modules.json`; `terraform get -update` refreshes them. `[CFG]`
1.16.10 **The standard module structure**: `main.tf`, `variables.tf`, `outputs.tf`, `README.md`,
      `LICENSE`, `examples/`, `modules/` for nested submodules, `tests/`. Registry publishing
      requires the repository name `terraform-<PROVIDER>-<NAME>` and semver tags. `[TABLE]`
      `[SOURCE]`
1.16.11 **`terraform-docs`** as the generator for the input/output table, and keeping it in CI so
      the README cannot drift. `[CLI]`
1.16.12 **Registry publishing mechanics**: tags as versions, the module protocol, the
      private-registry equivalent in HCP/TFE.
1.16.13 **When to make a module at all** — the honest bar: the same three-or-more-resource shape
      appears in two places *and* the shape is stable. A module wrapping one resource with
      pass-through variables is negative value. `[TRAP]` `[PROVE]`
1.16.14 **The QuizStakes module set** as the worked example: `modules/service-runtime` (task
      definition + service + target group + autoscaling + log group + IAM roles),
      `modules/ledger-database` (instance, parameter group, subnet group, secret rotation),
      `modules/document-bucket` (bucket, encryption, lifecycle at 90 days, Object Lock on the
      bank-file prefix), `modules/payment-run-scheduler` (schedule + leader lock table),
      `modules/restrictions-cache`. `[HCL]` `[X-REF 18]`
1.16.15 **Module composition patterns**: flat root calling many leaf modules (recommended),
      wrapper/"facade" modules, and the **deep nesting anti-pattern** — three levels of
      pass-through variables where nobody can find where a value came from. `[TABLE]` `[TRAP]`
1.16.16 **Inflexible-module anti-pattern**: a module that takes 60 variables to be reusable is a
      configuration file with extra steps. The alternative — accept an object, or fork.
      `[TRAP]`
1.16.17 **Module versioning discipline**: semver, what constitutes a breaking change for a
      module (removing an input, changing a default, renaming a resource **address**), and why an
      address change is breaking even when the infrastructure is identical. `[PROVE]` `[TRAP]`
1.16.18 **`moved` blocks are a module's migration tool** — shipping them inside the module lets a
      consumer upgrade without a state operation. This is the single most under-used feature in
      module design. `[HCL]` `[RESEARCH]`
1.16.19 **Nested-module state addresses** get long fast
      (`module.money["prod"].module.service_runtime.aws_ecs_service.this`) and every `-target`,
      `moved` and `import` must spell them exactly. `[TRAP]`
1.16.20 **Module inputs cannot be secret-safe by convention alone** — `sensitive = true` on the
      variable, and `ephemeral` where the value must not persist. `[X-REF 13]`
1.16.21 **`for_each` over a module** to instantiate one runtime per QuizStakes service, keyed by
      service name, with per-service heap and instance counts from Appendix B.1 as the map
      value. `[HCL]` `[NUM]`
1.16.22 **Public-registry modules**: the argument for (`terraform-aws-modules/vpc` encodes years
      of edge cases) and against (an unreviewed transitive dependency with cloud credentials).
      The middle path: vendor it, review it, pin it. `[TRAP]` `[X-REF 13]`

## §1.17 State — the model

1.17.1 **What state is, precisely**: a mapping from *configuration addresses* to *remote object
      identities*, plus a cached copy of each object's attributes, plus metadata. The
      documentation's own words: *"to store bindings between objects in a remote system and
      resource instances declared in your configuration."* `[SOURCE]` `[PROVE]`
1.17.2 **Why the binding cannot be inferred**: two `aws_instance` resources with identical
      arguments are indistinguishable remotely, so nothing but a record can say which is
      `aws_instance.gateway[0]`. `[PROVE]` `[TRAP]`
1.17.3 **Why state is not a cache** — the current guide's central claim, now proved: a cache can
      be rebuilt from the authority, but here *state is the only place the binding exists*.
      Losing it does not slow Terraform down; it makes Terraform wrong. `[PROVE]` `[TRAP]`
1.17.4 The **four things state holds**: the binding, the attribute snapshot (for diffing),
      the **dependency graph edges as recorded at last apply** (needed to destroy correctly when
      the configuration is gone), and metadata (`serial`, `lineage`, `terraform_version`,
      `schema_version`, `private`). `[TABLE]` `[PROVE]`
1.17.5 **The dependency-edges point is the one people miss**: this is why Terraform can destroy a
      resource in the right order after you delete its configuration. `[PROVE]`
1.17.6 **`lineage`** — a UUID identifying the *state's* identity, used to detect that you have
      pointed a configuration at a different state's history. `[NUM]`
1.17.7 **`serial`** — a monotonically increasing write counter, and the basis of the
      "state was modified by someone else" detection. `[NUM]` `[PROVE]`
1.17.8 **`terraform_version`** in state — and the **hard rule** it enforces: a state written by
      1.16 cannot be read by 1.11. State is forward-migrated only. This is why the CI pin and
      the developer's binary must agree. `[TRAP]` `[NUM]`
1.17.9 **State is not encrypted by Terraform** (OpenTofu excepted) and contains every attribute
      the provider returned, including secrets: RDS passwords, generated keys, `tls_private_key`
      material. The current guide's trap, expanded with a real list. `[TRAP]` `[X-REF 13]`
1.17.10 **`terraform state list` / `show` / `pull`** as the read-only inspection path, and
      `show -json` as the machine-readable one. `[CLI]`
1.17.11 **Never hand-edit the state file** — the documentation's own instruction — and the three
      reasons: `serial`, format changes, and the fact that the CLI operations are the stable
      interface. `[SOURCE]` `[TRAP]`
1.17.12 **State per configuration, not per project**: how many state files an estate should have
      and the criteria (blast radius, apply duration, ownership, change frequency). `[PROVE]`
1.17.13 **Blast radius as the primary state-splitting criterion**, worked for QuizStakes: the
      `FundsLedger` database and the `ApplicationGateway` service should not share a state file,
      because a bad apply on a stateless tier must not be able to plan a destroy on the ledger.
      `[PROVE]` `[TABLE]`
1.17.14 **Apply duration as the secondary criterion**: a 40-minute plan is a 40-minute lock, and
      a 40-minute lock means the team stops using Terraform. `[COST]` `[NUM]`

## §1.18 Backends

1.18.1 **What a backend is**: the plugin that stores state and (usually) provides locking. It
      does *not* run Terraform — except for `remote`/`cloud`, which do. `[TRAP]`
1.18.2 The **`backend` block** inside `terraform`, exactly one, and the fact that it takes no
      variables, functions or expressions. `[TRAP]` `[PROVE]`
1.18.3 **Partial configuration**: omit arguments from the block and supply them by
      `-backend-config=key=value`, `-backend-config=file.hcl`, or environment variables. The
      only sanctioned way to parameterise a backend per environment. `[CFG]` `[HCL]`
1.18.4 The **backend inventory**, with locking support and a one-line note each: `local`,
      `s3`, `azurerm`, `gcs`, `oss`, `cos`, `http`, `consul`, `kubernetes`, `pg`, `oci`
      (1.12+), `remote`, plus the `cloud` block. `[TABLE]` `[NUM]`
1.18.5 The **removed** backends — `etcd`, `etcdv3`, `artifactory`, `manta`, `swift`, `atlas` —
      and what to do if you find one in an old repository. `[VERSION-TRAP]`
1.18.6 **`local` backend**: `terraform.tfstate` plus `terraform.tfstate.backup`, workspace states
      under `terraform.tfstate.d/<name>/`, and file-based locking that is useless across
      machines. `[CFG]`
1.18.7 **`s3` backend** arguments, complete: required `bucket`, `key`, `region`; `use_lockfile`
      (default **false**); deprecated `dynamodb_table`/`dynamodb_endpoint`; `encrypt`,
      `kms_key_id`, `sse_customer_key`; `workspace_key_prefix` (default **`env:`**); `acl`;
      `max_retries` (default **5**); `assume_role` block (`role_arn`, `session_name`,
      `duration`, `external_id`); `assume_role_with_web_identity`
      (`role_arn` + `web_identity_token`/`web_identity_token_file`);
      `skip_credentials_validation`; `profile`; `access_key`/`secret_key`/`token`.
      `[TABLE]` `[CFG]` `[SOURCE]` `[NUM]`
1.18.8 **`use_lockfile = true`** — the mechanism: a `<key>.tflock` object written with an S3
      conditional write (`If-None-Match`), which is atomic, so the winner holds the lock.
      Beta in 1.10, **GA in 1.11**. `[PROVE]` `[RESEARCH]` `[X-REF 18]`
1.18.9 **The DynamoDB mechanism it replaces**: a conditional `PutItem` on `LockID`, one item per
      state path, and the table's `LockID` hash key. Still works, now deprecated. `[TABLE]`
      `[VERSION-TRAP]`
1.18.10 **The S3 bucket's own required configuration** for a state bucket: **versioning on**
      (your only undo), Block Public Access, SSE-KMS, a bucket policy denying non-TLS, and
      restricted IAM. Named here as a checklist. `[TABLE]` `[X-REF 18]`
1.18.11 **Versioning as the recovery mechanism**: the exact procedure to roll state back to a
      prior object version, and the reason it is a `[SURGERY]` item, not a routine one.
      `[SURGERY]` `[CLI]`
1.18.12 **`azurerm`** backend: blob container, blob lease as the lock, and the 1.11+
      authentication arguments (`use_cli`, `use_aks_workload_identity`, `client_id_file_path`,
      `client_certificate`, `client_secret_file_path`). `[CFG]` `[RESEARCH]`
1.18.13 **`gcs`** backend and its object-generation-based locking; **`pg`** backend and advisory
      locks; **`kubernetes`** backend storing state in a Secret (and the 1 MiB Secret limit
      that makes it unsuitable for a real estate). `[NUM]` `[TRAP]` `[X-REF 19]`
1.18.14 **`http`** backend: `address`, `lock_address`, `unlock_address`, `lock_method`,
      `unlock_method`, and why it is the one to implement when your platform team wants control.
      `[CFG]`
1.18.15 **`remote` backend vs the `cloud` block** — both talk to HCP/TFE; `cloud` is the current
      form and supports `organization`, `workspaces { name | tags | project }`. `[CFG]`
      `[VERSION-TRAP]`
1.18.16 **Backend migration**: change the block, run `init -migrate-state`, confirm the copy,
      **verify with `state list`**, then remove the old store. The full procedure with the
      verification step nobody does. `[FLOW]` `[SURGERY]`
1.18.17 **`.terraform/terraform.tfstate`** is the *backend record*, not your state — the file
      that makes `init` remember where state lives, and why deleting `.terraform/` is safe but
      re-`init` is then mandatory. `[TRAP]`
1.18.18 **State locking as documented**: *"State locking happens automatically on all operations
      that could write state. You do not see any message that it happens."* And `-lock=false`
      exists but the documentation advises against it. `[SOURCE]`
1.18.19 **`-lock-timeout=10m`** and why every CI pipeline should set it: without it, a concurrent
      run fails instantly instead of queueing. `[CFG]` `[NUM]`
1.18.20 **`.terraform.tfstate.lock.info`** for the local backend, and the DynamoDB item /
      `.tflock` object for S3 — what a stuck lock physically looks like in each. `[DIAG]`

## §1.19 The workflow, end to end

1.19.1 **The canonical loop**: write → `init` → `validate` → `fmt` → `plan` → review →
      `apply`. Each step's failure mode. `[FLOW]`
1.19.2 **`plan` in six steps**: load and evaluate configuration; read state; **refresh** each
      managed resource via `ReadResource`; build the graph; ask each provider to
      `PlanResourceChange`; emit the diff (and optionally serialise it to a plan file). This
      expands the current guide's five-step list with the provider RPCs named. `[FLOW]`
      `[PROVE]`
1.19.3 **`apply` in five steps**: acquire the lock; walk the graph in dependency order with
      `-parallelism` concurrency; call `ApplyResourceChange` per node; **write state after each
      resource completes**, not at the end; release the lock. `[FLOW]` `[PROVE]`
1.19.4 **The incremental-state-write point matters**: it is why a crashed apply leaves a
      *partially updated but consistent* state rather than nothing. `[PROVE]` `[TRAP]`
1.19.5 **`apply` without a plan file re-plans**, and the current guide is right that this is
      dangerous. The mechanism: the configuration, the state and the world may all have changed
      since you looked. `[TRAP]`
1.19.6 **`apply` with a saved plan file** does **not** re-plan, refuses if state has moved on
      (`serial` mismatch / stale plan), and is the only form a pipeline should use. `[PROVE]`
1.19.7 **The plan file is a binary artifact containing secrets in cleartext** and must be treated
      as one: encrypted at rest, short-lived, never a build artifact in a public log.
      `[TRAP]` `[X-REF 13]`
1.19.8 **Refresh in three modes**: default (refresh then diff), `-refresh=false` (trust state),
      and `-refresh-only` (update state to match reality, propose no changes). `[TABLE]`
1.19.9 **`-refresh=false` as a real production tool**: on a 400-resource state the refresh is the
      slow part, and skipping it converts a 4-minute plan into a 20-second one — at the cost of
      being blind to drift. `[COST]` `[NUM]` `[TRAP]`
1.19.10 **`-target=ADDRESS`**: the documented emergency tool, the fact that it takes dependencies
      with it, and that it makes the resulting state *knowingly* inconsistent with the
      configuration. Terraform prints a warning saying exactly that. `[SOURCE]` `[TRAP]`
1.19.11 **`-replace=ADDRESS`** as the reviewable replacement for `taint`. `[CLI]`
1.19.12 **`-exclude` / `-target-file` / `-exclude-file`** — OpenTofu 1.9/1.10 only, and the
      "apply everything except" case they answer. `[TOFU]` `[RESEARCH]`
1.19.13 **`-parallelism=10`** as the default node concurrency, when to lower it (provider rate
      limits, a small API quota) and when raising it does nothing (a serialised dependency
      chain). `[NUM]` `[PROVE]`
1.19.14 **`terraform apply -json`** and the machine-readable UI protocol as the basis of every CI
      integration that renders a plan into a PR comment. `[CLI]`
1.19.15 **`TF_LOG=TRACE|DEBUG|INFO|WARN|ERROR`**, `TF_LOG_CORE` / `TF_LOG_PROVIDER` for
      independent levels, and `TF_LOG_PATH`. Reading a provider's HTTP request/response pairs in
      `TRACE` is the debugging technique of last resort. `[CLI]` `[DIAG]`
1.19.16 **The guarantees Terraform gives**: determinism *given the same configuration, state and
      world*; ordering per the dependency graph; and that a saved plan applies exactly what it
      showed **or fails**. `[TABLE]` `[PROVE]`
1.19.17 **The guarantees it does not give**: no atomicity across resources (there is no
      rollback), no continuous reconciliation, no protection against a second actor, no
      guarantee that a plan will still be applicable in five minutes, and no promise that
      `destroy` succeeds. `[TABLE]` `[TRAP]` `[PROVE]`
1.19.18 **The "no rollback" consequence** stated plainly: a failed apply leaves you halfway, and
      the recovery is *forward* — fix the configuration and apply again. This is the single most
      important operational fact in the tool. `[PROVE]` `[TRAP]`

## §1.20 The registry and the ecosystem

1.20.1 The **public registry**: providers, modules, policies; the discovery protocol
      (`/.well-known/terraform.json`); versioned documentation. `[CFG]`
1.20.2 **`registry.terraform.io` vs `registry.opentofu.org`** — two registries, mostly the same
      providers, different mirrors of the same upstream repositories. `[TOFU]`
1.20.3 **Private registries** in HCP/TFE, and the alternative (a Git monorepo of modules plus
      tags), with the trade-off stated. `[TABLE]`
1.20.4 **Reading provider documentation properly**: the version selector, the "Attribute
      Reference" vs "Argument Reference" split, and the `Import` section — the three places the
      answer to a real question actually lives. `[TRAP]`
1.20.5 **`terraform providers schema -json`** as the authoritative, machine-readable answer to
      "does this attribute force replacement?" — the tool that ends the argument. `[CLI]`
      `[PROVE]`
1.20.6 **The tool ecosystem, named and bounded**: `tflint` (linting, provider-aware rules),
      `tfsec`/`trivy config` (security), `checkov` (policy + security), `terrascan`,
      `terraform-docs`, `infracost` (cost), `tfenv`/`tofuenv` (version switching),
      `terragrunt` (DRY wrapper), `atmos`/`terramate` (generation), `driftctl` (drift),
      `terratest` (Go tests), `pre-commit-terraform` (hooks), `terraform-compliance`,
      `conftest` (OPA), `sentinel`. Each with its one job. `[TABLE]`
1.20.7 **`tfsec` is now folded into Trivy** — recommending `tfsec` as a live project is a stale
      answer. `[VERSION-TRAP]` `[RESEARCH]`
1.20.8 **The Terraform MCP Server** — the AI-assistance surface, now authenticating against HCP
      Terraform / TFE. Named, bounded, and cross-referenced. `[RESEARCH]` `[X-REF 21]`

---

# PART 2 — INTERMEDIATE

## §2.1 The four worlds, and the cost of each operation

2.1.1 **The four worlds** that every Terraform question is really about: the **configuration**
      (what you wrote), the **state** (what Terraform believes), the **reality** (what the API
      says), and the **plan** (the proposed delta). Every failure mode in this guide is a
      disagreement between two of them. `[PROVE]` `[TABLE]`
2.1.2 The six pairwise disagreements, each with its name and its symptom:
      config↔state = *a normal change*; state↔reality = **drift**; config↔reality with empty
      state = *an import candidate*; state↔reality where state has an object reality does not =
      *a deleted-outside-Terraform resource* (plan shows create); reality has an object nobody
      records = *shadow infrastructure*; plan↔reality at apply time = **a stale plan**.
      `[TABLE]` `[PROVE]`
2.1.3 **The master cost table** for the whole topic: for every command, the API calls it makes,
      whether it takes the lock, whether it writes state, whether it needs credentials, and its
      wall-clock cost on a 400-resource state. `[TABLE]` `[NUM]` `[COST]`
2.1.4 `init` cost model: N provider downloads (~50–600 MB for the AWS provider family), M module
      fetches, zero provider API calls, no lock. Cached: seconds. Cold in CI: minutes.
      `[NUM]` `[COST]`
2.1.5 `validate` cost model: zero API calls, zero lock, zero credentials (since 1.15 it also
      validates the backend block *shape*, still without contacting it). Therefore it belongs in
      every pre-commit hook. `[NUM]` `[RESEARCH]`
2.1.6 `plan` cost model: **one `ReadResource` per resource instance in state** plus one read per
      data source, plus the lock (read lock), plus `PlanResourceChange` per changed resource.
      This is why plan time is **linear in state size**, not in diff size. `[PROVE]` `[NUM]`
2.1.7 `plan -refresh=false` cost model: zero `ReadResource` calls. The 400-resource arithmetic:
      at ~40 ms per describe call with parallelism 10, refresh is ~1.6 s of wall clock per 400
      resources in the ideal case and 2–5 minutes in the real one (rate limits, paginated list
      calls, providers that refresh in serial). `[PROVE]` `[NUM]` `[COST]`
2.1.8 `apply` cost model: the write lock for its entire duration, one `ApplyResourceChange` per
      changed instance, and **one state write per completed resource**. A 40-minute apply is a
      40-minute exclusive lock. `[NUM]` `[COST]`
2.1.9 `destroy` cost model, and the asymmetry: destroy is often *slower* than create (dependency
      chains serialise; deletion protection and drain timers dominate). `[NUM]`
2.1.10 **Where the time actually goes** in a slow plan, in order of likelihood: refresh API
      calls, a provider that does not parallelise, `for_each` over a large data-source result,
      `terraform_remote_state` on a huge state, and module fetches over Git. The diagnostic
      order. `[TABLE]` `[DIAG]`
2.1.11 **The lock is a queue with no queue discipline**: N pipelines waiting on one lock are
      served in arrival-of-retry order, not FIFO. The consequence for a busy repository.
      `[PROVE]` `[TRAP]`

## §2.2 `count` vs `for_each`, decided

2.2.1 The decision table: identity, add/remove behaviour, addressing, conditional use, nested
      iteration, and what each does when the collection is reordered. `[TABLE]`
2.2.2 **The reordering proof**, worked on QuizStakes' service list: with `count` over
      `["FundsLedger","BonusService","PaymentService"]`, inserting `BankWithdrawal` at index 1
      re-binds `[1]`, `[2]` and `[3]`, so the plan destroys and recreates `BonusService` and
      `PaymentService` and creates a fourth — three replacements for one addition. With
      `for_each` keyed by service name it is one create. `[PROVE]` `[TABLE]` `[TRAP]`
2.2.3 **Why state cannot save you here**: the address *is* `[1]`. Terraform has no notion that
      `[1]` "used to mean BonusService". `[PROVE]`
2.2.4 **The `for_each` key rules**: keys must be strings, known at plan time, and stable across
      runs. Anything derived from a timestamp, a random value, or an unapplied attribute breaks
      one of the three. `[TRAP]`
2.2.5 **Keys leak into the address, so keys leak into review**: `aws_ecs_service.svc["FundsLedger"]`
      is a readable plan; `aws_ecs_service.svc["a3f9c2"]` is not. Choose keys for humans.
      `[TRAP]`
2.2.6 **Nested iteration** with `setproduct` + `flatten` and a composite key
      (`"${service}/${environment}"`), worked for the 25-service × 3-environment matrix, with the
      arithmetic: 75 module instances, and what that does to plan time. `[HCL]` `[NUM]` `[COST]`
2.2.7 **`for_each` over a map of objects** as the preferred module input shape, because the value
      carries the per-instance configuration (heap size, instance count) rather than requiring a
      parallel lookup. `[HCL]`
2.2.8 **The `one()` idiom** for a `count = 0 or 1` resource, replacing
      `length(x) > 0 ? x[0].id : null`. `[HCL]`
2.2.9 **`count`'s legitimate remaining uses**: a feature flag, and N genuinely interchangeable
      objects (three NAT gateways, one per AZ, where the index *is* the identity). `[TABLE]`
2.2.10 **Migrating `count` → `for_each` safely**: the complete `moved` block set, the dry-run
      (`plan` must show zero changes), and the failure if a key is mistyped. `[HCL]` `[SURGERY]`
2.2.11 **`for_each` with `toset()` over a list containing duplicates silently drops them** —
      three services named the same in a list become one instance and no error. `[TRAP]`
      `[PROVE]`

## §2.3 Iteration, dynamic blocks and configuration shape

2.3.1 **`dynamic` blocks** in depth: what they generate, the `.key`/`.value` iterator, the
      `iterator` rename, `labels` for labelled nested blocks, and nesting.
2.3.2 **When `dynamic` is required**: a provider schema with a repeatable nested block whose
      count is data-driven (security-group rules, container port mappings,
      `lifecycle_rule` on the document bucket). `[HCL]`
2.3.3 **When `dynamic` is a mistake**: fewer than ~4 static blocks, or when the provider offers a
      first-class list attribute instead of a block. `[TRAP]`
2.3.4 **Blocks vs attributes in provider schemas** — protocol 6's `NestedType` lets a provider
      expose what used to be a block as a *list-of-object attribute*, which you can then set with
      a normal `for` expression and no `dynamic` at all. The AWS provider's newer resources do
      this. `[PROVE]` `[RESEARCH]` `[VERSION-TRAP]`
2.3.5 **Configuration-as-data**: pushing the variation into a `locals` map or a YAML file read
      with `yamldecode(file(...))`, so the HCL is a template and the data is reviewable
      separately. `[HCL]`
2.3.6 **The limit of configuration-as-data**: once the YAML has conditionals in it you have
      built a worse language inside a better one. State the boundary. `[TRAP]`
2.3.7 **Generated Terraform** (Terramate, Atmos, cdktf's JSON output) — when generation is
      justified and the reviewability cost it imposes. `[TABLE]`
2.3.8 **Why you cannot `for_each` a `provider` block in Terraform** (you can in OpenTofu 1.9),
      and the three workarounds: a module per provider configuration, a Stack with one deployment
      per region, or code generation. `[TOFU]` `[RESEARCH]` `[TRAP]`
2.3.9 **You cannot iterate a `backend`, a `terraform` block, or `required_providers`.** The
      consequence for multi-environment layout, resolved in §2.7. `[TRAP]`

## §2.4 Module design at scale

2.4.1 The **three module archetypes**, named: **resource module** (one logical thing done well —
      `modules/document-bucket`), **service/composition module** (a whole deployable —
      `modules/service-runtime`), **environment root** (not reusable, wires composition modules
      together). `[TABLE]` `[PROVE]`
2.4.2 **The interface-design rule**: a module's inputs should describe *intent*, not pass through
      provider arguments. `heap_size_gb = 12` and `partition_affine = true` beat forty
      pass-through variables. `[TRAP]`
2.4.3 **Input-shape choice**: many scalars vs one `object({...})` with `optional()` defaults, and
      the versioning consequence of each (adding an optional object field is not breaking;
      adding a required scalar is). `[PROVE]` `[TABLE]`
2.4.4 **Defaults are API**: changing a default changes every consumer's next plan. Treat it as a
      minor-with-a-plan or a major. `[TRAP]`
2.4.5 **Outputs are API too**, and passing a whole resource object out
      (`output "bucket" { value = aws_s3_bucket.this }`) couples consumers to the provider
      schema. `[TRAP]`
2.4.6 **What a module must never contain**: a `provider` block, a `backend` block, a hard-coded
      account or region, a `terraform.tfvars`, or a secret. Each with the failure it causes.
      `[TABLE]` `[TRAP]`
2.4.7 **Composition over nesting**: two levels of module depth is a working limit; three means
      nobody can trace a value. The arithmetic of pass-through variables:
      a leaf needing 6 inputs through 3 levels is 18 variable declarations. `[PROVE]` `[COST]`
2.4.8 **Dependency direction**: modules take data in and give data out; a module should never
      read the caller's state via `terraform_remote_state`. `[TRAP]`
2.4.9 **Versioning a module estate**: semver, a changelog per module, `moved` blocks shipped
      with breaking address changes, and a deprecation window using `deprecated` on variables
      (1.15+). `[RESEARCH]`
2.4.10 **The monorepo-of-modules vs repo-per-module** decision: atomic cross-module changes and
      one CI pipeline versus independent versioning and per-module access control. Recommend
      monorepo with tag prefixes (`service-runtime/v1.4.0`) for a team of QuizStakes' size.
      `[TABLE]` `[X-REF 17]`
2.4.11 **Testing a module** is `terraform test` plus an `examples/` directory that CI actually
      plans. `[X-REF §2.16]`
2.4.12 **Module registry documentation contract**: `terraform-docs` output committed, an
      `examples/` per supported shape, and an explicit "supported provider versions" statement.
2.4.13 **The QuizStakes `service-runtime` module interface**, written out: inputs
      (`service_name`, `image`, `heap_size_gb`, `min_instances`, `max_instances`,
      `session_affine`, `egress_allowlist`, `latency_budget_ms`), outputs (`task_role_arn`,
      `target_group_arn`, `log_group_name`, `service_arn`), and the invariants it enforces via
      `precondition` (e.g. `FundsLedger` may not be given `min_instances = 0`; only
      `CardPayments` may declare PSP egress). `[HCL]` `[NUM]` `[PROVE]`

## §2.5 Multi-environment layout

2.5.1 The **four layout patterns**, with a table of trade-offs: (a) directory per environment
      with duplicated roots, (b) one root + `-var-file` per environment, (c) CLI workspaces,
      (d) Terragrunt/Stacks-style generated roots. `[TABLE]` `[PROVE]`
2.5.2 **Pattern (a) — directory per environment** — is the boring, correct default: `envs/dev`,
      `envs/staging`, `envs/prod`, each with its own `backend.tf` and its own
      `terraform.tfvars`, all calling the same versioned modules. Duplication is ~30 lines per
      environment and buys per-environment state, credentials and blast radius. `[HCL]` `[PROVE]`
2.5.3 **Pattern (b) — one root, many var files** — and its fatal flaw: the backend cannot take a
      variable, so the state key must come from `-backend-config`, which is easy to get wrong
      and catastrophic when you do (a `prod` apply against `dev` state). `[TRAP]` `[INCIDENT]`
2.5.4 **Pattern (c) — workspaces** — and HashiCorp's own guidance against it for environments
      (§2.9). `[SOURCE]`
2.5.5 **The promotion model** Appendix B.4 demands: configuration is versioned and **promoted**,
      never edited in place. Mechanically: the same module version and the same variable values
      progress dev → staging → prod, and the only diff between environments is a values file.
      `[PROVE]` `[TRAP]`
2.5.6 **Where environments must legitimately differ**, enumerated for QuizStakes: instance
      counts (`ApplicationGateway` 12→40 in prod, 2 in dev), retention (7 years in prod, 7 days
      in dev), deletion protection, real PSP vs sandbox, and whether PII exists at all.
      `[TABLE]` `[NUM]`
2.5.7 **Prod-only settings are a drift source**: if `prevent_destroy` and deletion protection
      only exist in prod, prod is the only place the configuration is untested. Resolve by making
      the flags variables with prod-safe defaults. `[TRAP]` `[PROVE]`
2.5.8 **Layering within an environment** — the state-splitting layout: `00-bootstrap` (state
      bucket, OIDC roles), `10-network`, `20-data` (the ledger and PII instances),
      `30-platform` (clusters, registries), `40-services` (the 25 service runtimes),
      `50-observability`. Dependencies flow one way and are read via data sources or published
      parameters, never backwards. `[TABLE]` `[PROVE]`
2.5.9 **The bootstrap chicken-and-egg**: the state bucket cannot be in the state it holds — the
      three answers (local state committed once, a separate bootstrap state, or click it once
      and import) and which to choose. `[PROVE]` `[TRAP]`
2.5.10 **Naming and tagging as a layout concern**: `local.name_prefix =
      "quizstakes-${var.environment}"`, and `default_tags` on the AWS provider so every resource
      is tagged without repetition — plus the trap that `default_tags` conflicts with resource-level
      `tags` in older provider versions. `[TRAP]` `[X-REF 18]`

## §2.6 Multi-account and multi-region

2.6.1 **Why multi-account**: IAM blast radius, quota isolation, and billing separation. The
      QuizStakes account map: `quizstakes-dev`, `quizstakes-staging`, `quizstakes-prod`,
      `quizstakes-shared` (state, registry, CI), `quizstakes-audit` (log archive, write-only).
      `[TABLE]` `[X-REF 18]`
2.6.2 **How Terraform crosses an account boundary**: one provider configuration per account,
      each with `assume_role`, from a single CI identity. The trust-policy requirement on both
      sides. `[HCL]` `[X-REF 18]`
2.6.3 **The cross-account state-access question**: the state lives in `quizstakes-shared`, so the
      backend's credentials and the provider's credentials are *different roles*, resolved
      independently. This is the failure where `plan` cannot read state but the provider works,
      or vice versa. `[TRAP]` `[DIAG]`
2.6.4 **Multi-region within one configuration**: aliases, and the rule that a resource's region
      is a property of its *provider configuration*, not an argument — which is why you cannot
      `for_each` a region in Terraform. `[PROVE]` `[TRAP]`
2.6.5 **`us-east-1`-only resources** (ACM for CloudFront, some global services) forcing a second
      alias into every otherwise-single-region configuration. `[X-REF 18]`
2.6.6 **Region as a deployment dimension instead**: one root per region, or a Stack with one
      deployment per region — the shape that scales past two regions. `[PROVE]`
2.6.7 **QuizStakes' actual regional shape**: `eu-west-1` primary; `eu-west-2` for the 7-year
      ledger archive and DR; `us-east-1` only for global-service prerequisites. Data-residency
      constraints make this a compliance requirement, not a preference. `[X-REF 13]`
2.6.8 **Provider-level `default_tags`, `allowed_account_ids` and `forbidden_account_ids`** as
      the guardrail against applying to the wrong account — the cheapest control in this guide.
      `[CFG]` `[TRAP]`
2.6.9 **The wrong-account incident**: a developer with `AWS_PROFILE=prod` runs an apply intended
      for dev; `allowed_account_ids` turns a catastrophe into an error message. `[INCIDENT]`
      `[PROVE]`

## §2.7 Remote state and cross-configuration data flow

2.7.1 **Four mechanisms** for one configuration to consume another's facts, ranked:
      `terraform_remote_state`, a **provider data source** querying the live API, a **published
      contract** (SSM Parameter Store / a registry of outputs), and explicit variables.
      `[TABLE]` `[PROVE]`
2.7.2 **`terraform_remote_state` mechanics**: it reads and parses the *entire* remote state
      object, so it requires read access to every secret in it. This is the security argument
      against it, stated as a fact rather than a preference. `[PROVE]` `[TRAP]` `[X-REF 13]`
2.7.3 **`outputs` is the only accessible surface** of a remote state through the data source —
      but the *file* it read contains everything. Least privilege therefore cannot be expressed.
      `[PROVE]`
2.7.4 **The coupling it creates**: renaming an output in `10-network` breaks `40-services`' plan
      with no compile-time signal, and the failure appears in a different repository.
      `[TRAP]`
2.7.5 **`defaults` argument** as the shim for a not-yet-existing output. `[CFG]`
2.7.6 **The data-source alternative**, worked: `data "aws_vpc" "main" { tags = { Name =
      "quizstakes-prod" } }` couples to a *tag contract* instead of a state file, and the tag
      contract can be enforced by policy. `[HCL]` `[PROVE]`
2.7.7 **The published-contract alternative**: `10-network` writes
      `/quizstakes/prod/network/private_subnet_ids` to Parameter Store; consumers read it. This
      is versionable, auditable and least-privilege-able. Recommend it. `[HCL]` `[X-REF 18]`
2.7.8 **The ordering problem no mechanism solves**: nothing prevents `40-services` from applying
      before `10-network`. Ordering is a pipeline concern (or a Stack). `[PROVE]` `[TRAP]`
2.7.9 **Stacks as the first-party answer** to cross-configuration dependencies, with
      **deferred changes** handling the unknown-value case that breaks the data-source approach.
      `[X-REF §2.23]` `[RESEARCH]`

## §2.8 Workspaces

2.8.1 **CLI workspaces defined**: *"separate instances of state data inside the same Terraform
      working directory"*, sharing the plugin and module cache. `[SOURCE]`
2.8.2 The **`default` workspace** always exists and cannot be deleted; `terraform workspace
      list|new|select|delete|show`; `TF_WORKSPACE` for automation. `[CLI]` `[CFG]`
2.8.3 **`terraform.workspace`** as the expression-level hook, and the pattern of a
      `local.settings = { dev = {...}, prod = {...} }[terraform.workspace]` map. `[HCL]`
2.8.4 **Where workspace state physically goes**: `terraform.tfstate.d/<name>/terraform.tfstate`
      locally; `<workspace_key_prefix>/<name>/<key>` in S3 with `workspace_key_prefix`
      defaulting to **`env:`**. `[NUM]` `[SOURCE]`
2.8.5 **What workspaces genuinely are for**, per HashiCorp: *"a parallel, distinct copy of a set
      of infrastructure to test a set of changes"* — a feature-branch environment. `[SOURCE]`
2.8.6 **Why they are wrong for dev/staging/prod**: one backend, one credential set, one set of
      access controls, and one configuration — so a prod apply is one `workspace select` away
      from being a dev apply, and you cannot give different teams different access.
      HashiCorp says so explicitly. `[SOURCE]` `[TRAP]` `[PROVE]`
2.8.7 **The second reason**: a single configuration must then contain every environment's
      conditionals, which is exactly the complexity directory-per-environment avoids. `[PROVE]`
2.8.8 **HCP Terraform workspaces are a different thing entirely** — they are independent working
      directories with their own variables, credentials and run history. Sharing the noun is a
      genuine source of interview confusion. `[TRAP]` `[SOURCE]`
2.8.9 **The `default` workspace's asymmetric state path** in S3 (no `env:` prefix) — the reason a
      migration from `default` to a named workspace loses track of state. `[TRAP]` `[SURGERY]`

## §2.9 Refactoring: `moved`, `removed`, `import`, and state surgery

2.9.1 **The problem class**: renaming a resource, moving it into a module, splitting a state,
      changing `count` to `for_each`, adopting existing infrastructure, and letting go of
      infrastructure. All are *address* operations, not infrastructure operations. `[PROVE]`
2.9.2 **`moved` blocks** (1.1+): `from`/`to` required strings. Plan-time semantics per the
      documentation: find the object at `from`, **rename it in state**, then plan the resource at
      its new address — *"Terraform does not destroy the resource during the Terraform run."*
      `[SOURCE]` `[FLOW]`
2.9.3 **Why `moved` beats `terraform state mv`**: it is in the repository, it is reviewed, it
      runs inside the plan (so the plan proves it is a no-op), and it works for every consumer of
      a module. `[PROVE]`
2.9.4 **What `moved` can move**: resource → resource, resource → module resource, whole modules,
      index changes (`[0]` → `["FundsLedger"]`), and module instances. `[TABLE]` `[HCL]`
2.9.5 **What `moved` cannot do**: change the resource *type* (Terraform), cross state files, or
      move something that is not in state. **OpenTofu 1.10 added cross-type moves.** `[TOFU]`
      `[TRAP]` `[RESEARCH]`
2.9.6 **`moved` blocks are permanent-ish**: they must remain until every consumer has applied,
      and removing one early strands anyone who has not. The retention policy question.
      `[TRAP]`
2.9.7 **`removed` blocks** (1.7+): `from` plus a `lifecycle { destroy = false }` body — drop the
      resource from state without destroying it. This is the declarative `state rm`.
      `[HCL]` `[RESEARCH]`
2.9.8 **`removed` with `destroy = true`** — the "yes, actually delete it, and I have deleted the
      configuration" case, which is otherwise impossible to express once the `resource` block is
      gone. `[PROVE]`
2.9.9 **The 1.16 alternative**: `lifecycle { destroy = false }` on the resource itself, for the
      "stop owning this but keep the block" case. `[RESEARCH]` `[VERSION-TRAP]`
2.9.10 **`import` blocks** (1.5+): `to` (the target address), `id` **or** `identity` (1.12+),
      and `for_each` (1.13+ / with count-and-for_each fixes in 1.16.1). `[HCL]` `[RESEARCH]`
2.9.11 **`terraform plan -generate-config-out=generated.tf`** — Terraform writes candidate
      `resource` blocks for every `import` block whose address has no configuration. The 1.14
      `GenerateResourceConfiguration` RPC lets providers emit *more precise* values.
      `[CLI]` `[RESEARCH]`
2.9.12 **Reading generated configuration critically**: it includes every attribute including
      read-only ones and provider defaults, so it must be pruned; it does not include
      `lifecycle`, `moved` or comments; and it will happily encode a value you did not intend to
      own. `[TRAP]` `[DIAG]`
2.9.13 **The import loop**, as a procedure: write the `import` block → `plan -generate-config-out`
      → prune → `plan` until **zero changes** → `apply` → delete the `import` block. The
      zero-changes gate is the whole point. `[FLOW]` `[PROVE]`
2.9.14 **Import at scale**: `for_each` over a map of IDs, `terraform query` / list resources
      (1.14) or Terraform Search (HCP beta) to discover them, and the honest statement that
      importing 400 hand-made resources is a multi-week project. `[COST]` `[RESEARCH]`
2.9.15 **`terraform import` (the command)** as legacy: it mutates state directly with no plan and
      no review, and it cannot generate configuration. `[VERSION-TRAP]`
2.9.16 **What import does not do**: it does not import into a module you have not written, it
      does not import dependencies, and it does not import *relationships* — the imported
      security group will not know which instances use it. `[TRAP]`
2.9.17 **`terraform state mv`** — the imperative form, its exact syntax including cross-state
      `-state-out`, and why it is now `[SURGERY]`-only. `[SURGERY]` `[CLI]`
2.9.18 **`terraform state rm`** and the orphan it deliberately creates. `[SURGERY]`
2.9.19 **`terraform state push`/`pull`** and the `serial`/`lineage` checks that make a naive push
      fail — plus `-force` and why using it is the last thing you will do before an incident
      review. `[SURGERY]` `[TRAP]`
2.9.20 **`terraform state replace-provider`** for a provider source change
      (`hashicorp/aws` → a fork, or `registry.terraform.io` → `registry.opentofu.org`).
      `[CLI]` `[TOFU]`
2.9.21 **Splitting one state into two** — the complete runbook: back up both states, `state mv
      -state-out`, verify with `state list` on both, `plan` both to zero changes, then
      re-point the pipelines. `[SURGERY]` `[FLOW]`
2.9.22 **The universal surgery preamble**: `terraform state pull > backup.tfstate`, confirm the
      backend has versioning, announce the lock, and know the rollback. Every `[SURGERY]` leaf in
      this file inherits it. `[SURGERY]` `[PROVE]`
2.9.23 **When surgery is the wrong answer**: if the fix is expressible as `moved`/`removed`/
      `import`, use those — they are reviewable and idempotent. `[TRAP]`

## §2.10 Drift

2.10.1 **Drift defined precisely**: a disagreement between **state** and **reality** for a
      resource Terraform manages. Not to be confused with **shadow infrastructure** (reality has
      objects nothing manages) or with **configuration drift between environments**. `[PROVE]`
      `[TABLE]`
2.10.2 **How Terraform detects it**: `ReadResource` during refresh overwrites the state snapshot
      with reality, and the diff against configuration then shows the repair. Drift detection is
      a **side effect of refresh**, not a feature. `[PROVE]`
2.10.3 **Drift is read-only** until you apply — the current guide's correct claim, with the
      mechanism now stated. `[PROVE]`
2.10.4 **`plan -refresh-only`** as the drift report, and `apply -refresh-only` as *accept
      reality into state* — which is a genuinely different operation from repairing it.
      `[TABLE]` `[PROVE]` `[TRAP]`
2.10.5 **The four drift responses**, and how to choose: repair (apply), accept
      (`apply -refresh-only`), disown (`ignore_changes`), or prevent (IAM). `[TABLE]` `[PROVE]`
2.10.6 **The causes of drift**, enumerated: console changes, another IaC tool, an autoscaler, a
      deployment pipeline updating an image tag, cloud-provider-side defaults and normalisation,
      resource deletion outside Terraform, and provider upgrades changing how an attribute is
      read. `[TABLE]`
2.10.7 **Provider-side normalisation as false drift**: an IAM policy JSON reordered by AWS, a
      tag AWS adds itself, a `Z`-suffixed timestamp. The symptom is a diff that reappears after
      every apply. The fixes: `jsonencode` canonical form,
      `aws_iam_policy_document`, `ignore_changes`, or a provider bug report. `[TRAP]` `[DIAG]`
2.10.8 **The perpetual-diff catalogue**: `timestamp()`/`uuid()` in configuration, `bcrypt()`,
      a `for_each` over a data source that changes, a `null` vs `""` mismatch, a
      computed-then-set attribute, and a provider that returns a different case than you wrote.
      `[TABLE]` `[TRAP]` `[DIAG]`
2.10.9 **`ignore_changes` as ownership transfer**, restated as policy: every entry names another
      owner, in a comment, with a ticket. Otherwise it is a silenced alarm. `[TRAP]`
2.10.10 **The `ClientRestrictions` drift case** from the domain: an operator applies a
      restriction through `InternalPlatforms`, not Terraform. If Terraform owned the policy
      document it would revert a regulatory control on the next apply. Therefore Terraform must
      **not** own that field — `ignore_changes`, or better, the field is not in Terraform at all.
      `[INCIDENT]` `[PROVE]` `[X-REF 13]`
2.10.11 **Continuous drift detection**: a scheduled `plan -detailed-exitcode` per state, exit
      code 2 as the alert, and the cost arithmetic (25 states × 4 runs/day × 3 minutes = 5 hours
      of runner time daily). `[COST]` `[NUM]` `[X-REF 20]`
2.10.12 **`check` blocks vs drift detection**: `check` asserts a *property* continuously and
      warns; drift detection compares *state* and proposes changes. Different jobs. `[TABLE]`
2.10.13 **HCP Terraform's drift detection and continuous validation** as the managed version.
      `[RESEARCH]`
2.10.14 **Preventing drift with IAM**, which is the only real fix: deny console mutations on
      Terraform-managed resource types outside a break-glass role, and audit the exceptions.
      `[X-REF 18]` `[X-REF 13]` `[PROVE]`
2.10.15 **The honest limit**: Terraform cannot detect drift in a resource it does not manage, in
      an attribute the provider does not read back, or in anything between two runs.
      `[PROVE]` `[TRAP]`

## §2.11 Secrets

2.11.1 **The three places a secret leaks** in a Terraform workflow: **state**, the **plan file**,
      and the **run log**. Each needs a separate control. `[TABLE]` `[PROVE]`
2.11.2 **State**: every attribute the provider returns is written, unencrypted by Terraform, for
      every managed resource. `aws_db_instance.password`, `tls_private_key.private_key_pem`,
      `random_password.result`, a Kubernetes `Secret`'s data — all in cleartext. `[TRAP]`
      `[X-REF 13]`
2.11.3 **The plan file** contains the planned values, including secrets, and is a build artifact
      by default. `[TRAP]`
2.11.4 **The run log**: `sensitive` redacts, but a value embedded in a non-sensitive string
      (a connection URL built with `format`) escapes redaction unless sensitivity propagated.
      `[PROVE]` `[TRAP]`
2.11.5 **`sensitive = true` does exactly three things**: redacts CLI output, propagates the mark
      through expressions, and forces `sensitive = true` on any output derived from it. It does
      **not** encrypt state, and the current guide's trap must survive verbatim-plus-mechanism.
      `[PROVE]` `[TRAP]`
2.11.6 **`nonsensitive()`** as the deliberate override, and the review rule: every use is a
      security decision. `[TRAP]`
2.11.7 **Ephemeral values** (1.10+): `variable { ephemeral = true }`, `ephemeral` resources,
      `output { ephemeral = true }`, `local`s that inherit ephemerality. Guarantee: *not
      persisted to state or plan*. `[SOURCE]` `[RESEARCH]`
2.11.8 **Where ephemeral values may be used**: write-only arguments, other ephemeral blocks,
      provider configuration, provisioner/connection blocks, and ephemeral outputs. Where they
      may not: any persisted attribute, any non-ephemeral output, `count`/`for_each`.
      `[TABLE]` `[RESEARCH]`
2.11.9 **The ephemeral resource lifecycle**: **Open → (Renew)* → Close**, within one operation,
      re-opened separately for plan and for apply — which is why *"write-only argument
      configuration values are not expected to be consistent between plan and apply"*.
      `[SOURCE]` `[FLOW]` `[PROVE]` `[RESEARCH]`
2.11.10 **Write-only arguments** (1.11+): provider-declared, conventionally `*_wo` (e.g.
      `password_wo` with a paired `password_wo_version`); *"prior state, planned state, and
      final state values for write-only arguments should always be null"*; not supported on set
      attributes/blocks. `[SOURCE]` `[NUM]` `[RESEARCH]`
2.11.11 **The `*_wo_version` idiom**: because the value is never in state, Terraform cannot see
      it change — so a companion version integer is what actually triggers the update. This is
      the mechanism people miss. `[PROVE]` `[TRAP]` `[RESEARCH]`
2.11.12 **What still lands in state after all of that**: attributes the provider returns
      *computed* (a generated endpoint, a certificate), so ephemeral values shrink the exposure
      rather than eliminating it. `[PROVE]` `[TRAP]`
2.11.13 **OpenTofu state encryption**: the `encryption` block; key providers `pbkdf2`
      (**minimum 16-character passphrase, 600,000 iterations by default**, SHA-256/512),
      `aws_kms`, `gcp_kms`, `azure_vault` (1.11), `openbao`, `external` (experimental);
      `method "aes_gcm"` (**16/24/32-byte keys**) and `method "unencrypted"`; `state {}` and
      `plan {}` targets; `fallback` for rollover; `encrypted_metadata_alias` for renaming.
      `[TABLE]` `[NUM]` `[SOURCE]` `[TOFU]` `[RESEARCH]`
2.11.14 **The migration and rollback procedures** for state encryption, and the documentation's
      own warning that encrypted state is unrecoverable without the key — so the DR exercise is
      mandatory, not advisable. `[SURGERY]` `[SOURCE]` `[RESEARCH]`
2.11.15 **What encryption does not protect against**: data loss, replay of an old state, or
      anyone who can run the binary. Stated as the documentation states it. `[SOURCE]` `[TRAP]`
2.11.16 **Terraform's equivalents**: backend-side encryption (SSE-KMS), and **HCP HYOK** (GA
      2025) for HCP-held artifacts. `[RESEARCH]`
2.11.17 **The correct secret patterns**, ranked for QuizStakes: (1) the resource generates the
      secret and nothing reads it (`manage_master_user_password` — AWS holds it, Terraform never
      sees it); (2) an ephemeral data source + write-only argument; (3) a secret created out of
      band and referenced by ARN only; (4) `random_password` + Secrets Manager, accepting the
      state exposure. Never: a secret in `.tfvars`, a secret in `TF_VAR_*` in CI, or a secret in
      a `local`. `[TABLE]` `[PROVE]` `[X-REF 13]` `[X-REF 18]`
2.11.18 **Appendix B.4 compliance check**: "vendor credentials in a managed secret store,
      rotated, never in config or environment" means options (1) and (3) are the only compliant
      ones for the PSP credentials that `CardPayments` uses. `[PROVE]`
2.11.19 **Rotation and Terraform**: a rotated secret is drift Terraform must not repair, so the
      version/ARN is what Terraform owns and the value is not. `[PROVE]` `[TRAP]`
2.11.20 **CI credentials**: **OIDC federation** (GitHub Actions / GitLab → an assumable role
      with a `sub` condition), no long-lived keys, per-environment roles, and a plan role that is
      **read-only**. Appendix B.4's "workload identity, short-lived credentials". `[HCL]`
      `[X-REF 13]`
2.11.21 **The read-only-plan-role trick and its limit**: refresh needs `Describe*`, so a plan
      role can be read-only — but `plan` on a data source that calls `sts:GetCallerIdentity` or
      a provider that validates on configure still needs those. Enumerate what a plan role
      actually needs. `[PROVE]` `[X-REF 18]`

## §2.12 Validation, checks and assertions

2.12.1 **The six-layer validation stack** as one table: `terraform fmt` → `terraform validate` →
      `variable validation` → `precondition`/`postcondition` → `check` → policy-as-code →
      `terraform test`. Each with what it can see and when it runs. `[TABLE]` `[PROVE]`
2.12.2 **`variable validation`**: evaluated before anything else, may reference other variables
      (1.9+), and is the module's input contract. `[NUM]`
2.12.3 **`precondition`**: an assumption about the world, evaluated before the resource is
      planned; failure is an **error** that stops the plan. `[SOURCE]`
2.12.4 **`postcondition`**: a guarantee about what was created, evaluated after create/read;
      failure is an **error** *after* the resource exists — so it does not prevent the resource,
      it fails the run. This asymmetry is the trap. `[PROVE]` `[TRAP]`
2.12.5 **`check` blocks** (1.5+): top-level, containing `assert` blocks and optional **scoped
      data sources**; run *last*, after plan or apply; failure is a **warning**, not an error, so
      the operation continues. `[SOURCE]` `[PROVE]`
2.12.6 **Why `check` is warning-only by design**: it is for continuous validation of properties
      you do not control, so blocking on it would make an unrelated outage block every apply.
      `[PROVE]`
2.12.7 **The scoped-data-source property**: a data source inside a `check` does not become a
      dependency of anything, so it cannot make your graph unknown. `[PROVE]` `[RESEARCH]`
2.12.8 **The QuizStakes check set**: assert the `ClientRestrictions` health endpoint returns 200,
      assert the document bucket has Object Lock on the bank-file prefix, assert the
      `BankWithdrawal` schedule exists exactly once, assert the ledger instance is in the
      partition-affine subnet group. `[HCL]` `[X-REF 20]`
2.12.9 **Where each QuizStakes invariant belongs** — the worked mapping: "`FundsLedger` must not
      be function-based" is a **policy** rule; "only `CardPayments` egresses to the PSP" is a
      **policy** rule *and* a `precondition` in the module; "heap must be one of the Appendix B
      values" is a **variable validation**; "the payment-run schedule must be singular" is a
      **check**; "the module produces a task role" is a **postcondition**. `[TABLE]` `[PROVE]`
2.12.10 **`error_message` quality**: it is the entire UX of a module. Name the variable, the
      offending value and the legal set. `[TRAP]`
2.12.11 **What none of these layers can do**: prove the infrastructure works. Only a test that
      exercises the thing does that, and Terraform's own test framework mostly cannot either
      (§2.16). `[PROVE]` `[TRAP]`

## §2.13 Testing

2.13.1 **The infrastructure test pyramid**, honestly shaped: `fmt`/`validate` (free), lint
      (free), policy (free), **plan-only unit tests with mocked providers** (cheap),
      **apply-based integration tests in a sandbox** (slow, expensive, flaky), and
      **post-deploy smoke tests** (the only thing that proves it works). `[TABLE]` `[PROVE]`
      `[X-REF 16]`
2.13.2 **`terraform test`** (**1.6+**): `*.tftest.hcl` / `*.tftest.json`, discovered in the
      configuration directory and in `tests/`. `[SOURCE]` `[RESEARCH]`
2.13.3 **The `run` block**: `command = plan | apply` (**default `apply`**), `variables`,
      `module`, `providers`, `assert`, `expect_failures`, `state_key`, `parallel`,
      and `plan_options { mode = normal|refresh-only, refresh, replace, target }`.
      `[TABLE]` `[SOURCE]` `[RESEARCH]`
2.13.4 **`assert`** blocks reference outputs, resource attributes, data sources and variables —
      including **previous `run` blocks' outputs** via `run.<name>.<output>`. `[HCL]`
2.13.5 **Variable precedence inside tests**, exact: `run`-block variables → file-level
      `variables` → command line → var files → environment. `[TABLE]` `[NUM]` `[RESEARCH]`
2.13.6 **The `module` block in a `run`**: takes only `source` and `version`, and exists for
      **setup** modules (create prerequisites) and **loading** modules (read back and assert).
      Each alternate module gets its own state file unless `state_key` is shared. `[PROVE]`
      `[RESEARCH]`
2.13.7 **Cleanup semantics**: Terraform destroys in **reverse `run` order**, which is why an S3
      object created in run 3 is removed before the bucket from run 1. And the 1.14+ experimental
      `terraform test cleanup` command with a manifest, plus `skip_cleanup` and `backend` blocks
      in tests for persistent test infrastructure. `[PROVE]` `[RESEARCH]`
2.13.8 **When cleanup fails you have leaked real infrastructure**, and the test suite must be
      treated as a cost centre with an owner. `[COST]` `[TRAP]`
2.13.9 **Provider mocking** (**1.7+**): `mock_provider` with `mock_resource`, `mock_data`,
      `override_during`, and `*.tfmock.hcl` files referenced by `source`. Generated values for
      everything the schema declares computed. `[HCL]` `[RESEARCH]`
2.13.10 **`override_resource`, `override_module`, `override_data`** — pinning specific values
      instead of mocking a whole provider. `[HCL]` `[RESEARCH]`
2.13.11 **What a mocked plan-only test actually proves**: that the module's *logic* (counts,
      names, conditionals, validation) is right. It proves nothing about the cloud. Say so
      plainly. `[PROVE]` `[TRAP]`
2.13.12 **`expect_failures`** for negative tests, and the documented recommendation to pair it
      with `command = plan` because custom conditions on computed attributes only evaluate after
      creation. `[SOURCE]` `[TRAP]` `[RESEARCH]`
2.13.13 **Parallelism**: `test { parallel = true }` globally or per-`run`; runs parallelise only
      when they do not reference each other and do not share a `state_key`; a single
      `parallel = false` is a synchronisation barrier. `[PROVE]` `[RESEARCH]`
2.13.14 **`-junit-xml`** — **GA in 1.11** — for CI reporting; `-verbose` shows expected
      diagnostics (1.14). `[CLI]` `[RESEARCH]`
2.13.15 **`-filter`**, `TF_TEST_*`, and running tests against a real backend vs in-memory state.
      `[CFG]`
2.13.16 **Terratest** (Go): what it does that `terraform test` cannot — arbitrary assertions
      (SSH in, curl the ALB, query the database), retries, and stage-based test structure. Its
      cost: Go, and a real apply. `[TABLE]` `[X-REF 16]`
2.13.17 **The honest recommendation**: `terraform test` with mocks for module logic, one
      apply-based test per module in a sandbox account on a schedule (not per PR), Terratest only
      where you need to assert against a live system, and smoke tests owned by the service team.
      `[PROVE]` `[TABLE]`
2.13.18 **`terraform-compliance`** and **`conftest`** as plan-assertion tools that sit between
      testing and policy. `[TABLE]`
2.13.19 **Testing a module's `moved` blocks**: apply the old version, upgrade, plan, assert zero
      changes. The test almost nobody writes, and the one that would prevent most module-upgrade
      incidents. `[PROVE]` `[TRAP]`
2.13.20 **Flakiness sources specific to infrastructure tests**: eventual consistency, quota
      exhaustion, name collisions across parallel runs, leaked resources from a previous failure,
      and provider rate limits. Each with its mitigation (`random_pet` suffixes, per-run
      prefixes, retries, a nightly reaper). `[TABLE]` `[X-REF 16]`

## §2.14 Policy as code

2.14.1 **Why policy is a separate layer** from validation: it is *organisational* rather than
      *module* correctness, it is enforced centrally, and the module author must not be able to
      turn it off. `[PROVE]`
2.14.2 **The universal mechanism**: `terraform show -json <planfile>` produces the plan JSON, and
      every policy tool is a predicate over `resource_changes`. Learn the JSON once and every
      tool is interchangeable. `[PROVE]` `[SOURCE]`
2.14.3 **Sentinel**: HashiCorp's language, HCP/TFE-only, with the `tfplan/v2`, `tfconfig/v2`,
      `tfstate/v2` and `tfrun` imports, `main` rule, `mocks` for testing, and the
      `sentinel test` harness. `[TABLE]` `[RESEARCH]`
2.14.4 **Enforcement levels**: `advisory` (log), `soft-mandatory` (overridable by an authorised
      user), `hard-mandatory` (blocks the run). Mapping QuizStakes' rules onto the three.
      `[TABLE]` `[NUM]` `[RESEARCH]`
2.14.5 **HCP's 350+ pre-written Sentinel policies** for NIST SP 800-53 Rev 5 on AWS — the
      "do not write your own encryption-at-rest policy" argument. `[RESEARCH]`
2.14.6 **OPA / Rego**: `opa exec --decision terraform/analysis/authz --bundle policy/
      tfplan.json`, rules over `input.resource_changes[_].change.actions`, and the published
      **blast-radius scoring** example. `[SOURCE]` `[CLI]` `[RESEARCH]`
2.14.7 **`conftest test --policy policy/ tfplan.json`** as the CI-friendly OPA wrapper, with
      `deny`/`warn`/`violation` rule naming conventions. `[CLI]`
2.14.8 **Terraform Policy** — the native HCL policy framework in HCP Terraform, **in beta**, and
      the fact that a policy set may contain only one framework's policies. `[RESEARCH]`
      `[VERSION-TRAP]`
2.14.9 **What plan-JSON policy cannot see** (the documented limits): computed attributes,
      the contents of dynamic blocks, and unevaluated function results — so "deny any bucket
      without encryption" can be defeated by a value that is unknown at plan time. `[SOURCE]`
      `[PROVE]` `[TRAP]`
2.14.10 **The mitigation**: pair plan-time policy with **config-time** policy (`tfconfig`,
      checkov, tflint) and **runtime** policy (AWS Config, SCPs). Defence in depth, because each
      layer has a different blind spot. `[TABLE]` `[PROVE]` `[X-REF 18]`
2.14.11 **The QuizStakes policy set**, written as rules: no unencrypted storage; no `0.0.0.0/0`
      ingress except on the `ApplicationGateway` load balancer; no PSP egress from any service
      but `CardPayments`; every resource carries `owner`, `environment`, `cost-center`,
      `data-classification`; no deletion of any `aws_db_instance` outside a break-glass run;
      `prevent_destroy` present on the ledger and the document bucket; 7-year retention on the
      bank-file prefix; and a **blast-radius cap** — a plan destroying more than 5 resources
      requires a second approver, mirroring `PaymentRun`'s `signedOffBy` ≠ `authorisedBy`.
      `[TABLE]` `[HCL]` `[PROVE]`
2.14.12 **Policy on the *plan*, not on the apply** — and the corollary that the applied plan must
      be the *same artifact* the policy approved. `[PROVE]` `[TRAP]`
2.14.13 **Cost policy** as a first-class case: fail the run if the monthly delta exceeds a
      threshold (§2.17). `[COST]`

## §2.15 Security of the IaC pipeline

2.15.1 **The threat model**, enumerated: the state store (credentials for the whole estate),
      the CI identity (admin in every account), the module supply chain (arbitrary code with
      those credentials), the provider supply chain (a signed binary you execute), the plan
      artifact, and the reviewer (who is the only control on intent). `[TABLE]` `[PROVE]`
      `[X-REF 13]`
2.15.2 **A Terraform apply is remote code execution with cloud-admin credentials.** That single
      sentence sets the review bar for a module dependency bump. `[PROVE]` `[TRAP]`
2.15.3 **Module supply chain controls**: pin to a tag or SHA, vendor third-party modules into
      `quizstakes-shared`, review the diff on upgrade, and never allow `ref=main`.
      `[TABLE]` `[X-REF 17]`
2.15.4 **Provider supply chain controls**: the lock file's hashes, GPG-signed registry releases,
      a **private mirror** so `init` never reaches the internet, and `-plugin-dir` in an
      air-gapped build. `[PROVE]`
2.15.5 **`provisioner "local-exec"` is an arbitrary-command primitive** in a file anyone can PR.
      A policy rule should ban it outright. `[TRAP]`
2.15.6 **State store hardening checklist**: versioning, SSE-KMS with a CMK, Block Public Access,
      TLS-only bucket policy, access logging to `quizstakes-audit`, separate buckets per
      environment, and IAM that lets the plan role read but only the apply role write.
      `[TABLE]` `[X-REF 18]`
2.15.7 **Least privilege for the apply role**, and the honest limit: an apply role that can
      create IAM roles can escalate to anything. The mitigations — permissions boundaries, SCPs,
      and a separate bootstrap role for IAM changes. `[PROVE]` `[X-REF 18]`
2.15.8 **Static analysis tools compared**: `tflint` (correctness + provider-aware rules,
      deep AWS rule set), `checkov` (1,000+ policies, multi-framework, SARIF output),
      `trivy config` (**absorbed tfsec**), `terrascan`, `kics`. What each catches that the
      others do not, and the recommendation to run two, not five. `[TABLE]` `[RESEARCH]`
2.15.9 **`tfsec` is deprecated in favour of Trivy** — stale-answer flag. `[VERSION-TRAP]`
      `[RESEARCH]`
2.15.10 **Scanning the plan vs scanning the code**: code scanning catches what you wrote, plan
      scanning catches what it resolves to (including module defaults). Run both. `[PROVE]`
2.15.11 **Secret scanning** in the repository (`gitleaks`, `trufflehog`) as the control against
      the `.tfvars` mistake, plus a `pre-commit` hook. `[X-REF 17]`
2.15.12 **The plan-output leak in a PR comment**: a plan rendered into a public pull request
      publishes every non-sensitive value, including IP ranges, ARNs, account IDs and sometimes
      secrets. The control: private repositories, redaction, or a link to the run rather than the
      diff. `[TRAP]` `[INCIDENT]` `[X-REF 13]`
2.15.13 **Audit**: CloudTrail on the state bucket, run logs retained, and the `PaymentRun`-style
      two-actor rule for production applies. `[X-REF 18]`

## §2.16 CI/CD patterns

2.16.1 **The canonical pipeline**, as a sequence with the exact commands and gates: `fmt -check`
      → `init -backend=false` + `validate` → lint + security scan → `init` → `plan -out=tfplan`
      → `show -json tfplan` → policy → **publish the plan for review** → manual approval →
      `apply tfplan`. `[FLOW]` `[CLI]` `[PROVE]`
2.16.2 **The plan artifact is the contract**: `apply` must consume the *saved* plan, never
      re-plan. Otherwise the thing reviewed and the thing applied are different. `[PROVE]`
      `[TRAP]`
2.16.3 **Why the plan file must be stored securely** and expire: it contains secrets. Encrypt it,
      scope it to the run, delete it after. `[TRAP]`
2.16.4 **Plan staleness**: between plan and apply the world moves. The controls — a short
      approval TTL, `serial` checking (Terraform refuses a stale plan), and a re-plan-and-compare
      step for long approvals. `[PROVE]`
2.16.5 **`-detailed-exitcode`** driving the pipeline: 0 = skip apply, 2 = require approval,
      1 = fail. `[NUM]` `[CLI]`
2.16.6 **Concurrency control** at the pipeline level, not just the lock: one in-flight run per
      state (GitHub Actions `concurrency` group, GitLab `resource_group`), because two queued
      applies with stale plans is exactly the current guide's concurrent-apply failure.
      `[PROVE]` `[TRAP]`
2.16.7 **The concurrent-apply failure, fully worked**: job A plans at T0, job B plans at T1, A
      applies at T2, B applies at T3 with A's changes invisible to it. B's plan is *stale*, and
      Terraform's `serial` check will reject a saved plan — but a `-auto-approve` re-plan will
      cheerfully apply the wrong thing. The fixes, in order: saved plans, pipeline concurrency
      groups, `-lock-timeout`. `[FLOW]` `[PROVE]` `[TRAP]` `[INCIDENT]`
2.16.8 **PR-driven workflow**: plan on PR with a read-only role, comment the summary, apply on
      merge to `main` with the write role. Environment protection rules as the approval gate.
      `[X-REF 17]`
2.16.9 **OIDC authentication** for both roles, with `sub` claim conditions restricting to the
      repository, the branch and the environment. Appendix B.4's short-lived credentials.
      `[HCL]` `[X-REF 13]`
2.16.10 **Caching in CI**: `TF_PLUGIN_CACHE_DIR` restored between runs, and the arithmetic — the
      AWS provider is ~600 MB unpacked, and 25 states × 20 runs/day of cold downloads is
      bandwidth and minutes you are paying for. `[COST]` `[NUM]`
2.16.11 **Matrix pipelines over many states** and the ordering problem: layers must apply in
      order, and CI is where that order is enforced. `[PROVE]`
2.16.12 **`terraform init -upgrade` in CI is an anti-pattern** — it silently changes provider
      versions on an unrelated PR. Use `-lockfile=readonly`. `[TRAP]`
2.16.13 **Drift pipeline** (scheduled `plan -detailed-exitcode`) and **destroy pipeline** (for
      ephemeral environments, with a hard allowlist of states it may target). `[COST]`
2.16.14 **Ephemeral/preview environments**: a workspace or a state per PR, a TTL reaper, and the
      cost cap. This is workspaces' one good use. `[COST]`
2.16.15 **HCP Terraform / TFE as the alternative to building this**: VCS-driven runs, remote
      execution, run tasks, policy sets, cost estimation, and a real audit trail. The trade-off:
      RUM-based pricing against the engineering cost of the pipeline above. `[TABLE]` `[COST]`
2.16.16 **Rollback strategy**: there is none. Recovery is *forward* — revert the commit and
      apply. And for a destroyed stateful resource, the recovery is a restore, not a Terraform
      operation. `[PROVE]` `[TRAP]`
2.16.17 **The break-glass path**: a documented, audited, time-boxed procedure for a local apply
      with elevated credentials when the pipeline is down — because pretending it will never
      happen is how it happens unaudited. `[PROVE]`

## §2.17 Cost

2.17.1 **Terraform's own cost** is nearly zero (a binary, some API calls); the cost is what it
      provisions and what the pipeline burns. Separate the two. `[COST]`
2.17.2 **Infracost**: `infracost breakdown --path .` and `infracost diff --path .` against a plan
      JSON, the price-API model, `infracost.yml`, usage-based estimates
      (`infracost-usage.yml`), and the CI comment. `[CLI]` `[COST]`
2.17.3 **What Infracost cannot price**: data transfer, request-count-driven services, anything
      usage-based without a usage file — which for QuizStakes means the document-upload egress
      and the ledger's IOPS are exactly the numbers it will miss. `[TRAP]` `[PROVE]`
2.17.4 **A cost gate as policy**: fail if the monthly delta exceeds a threshold, or require a
      second approver. `[COST]`
2.17.5 **Tagging for cost allocation** enforced by policy — `cost-center`, `service`,
      `environment` — with `default_tags` doing the work. `[X-REF 18]`
2.17.6 **The pipeline's own bill**, computed: 25 states × (3-minute plan + 90-second init) × 20
      PR runs/day + 4 scheduled drift runs/day. State the runner-minute total and the honest
      conclusion that plan caching and `-refresh=false` on non-drift runs are worth real money.
      `[COST]` `[NUM]` `[PROVE]`
2.17.7 **The cost of *not* having IaC**: a manual `prod` rebuild after a regional failure, priced
      in hours of downtime against QuizStakes' 2.8M stake reservations/day. `[COST]` `[PROVE]`

## §2.18 Performance at scale

2.18.1 **The scaling variable is the number of resources in one state**, not the number of lines
      of HCL. `[PROVE]`
2.18.2 **The symptom ladder**: 100 resources = fine; 500 = a slow plan; 2,000 = a 10-minute plan
      and a contended lock; 5,000+ = a state file large enough that *transferring and parsing it*
      is measurable. `[NUM]` `[TABLE]`
2.18.3 **Where the time goes, measured**: refresh API calls (dominant), state
      serialisation/upload, graph construction, and expression evaluation over large
      collections. `[TABLE]` `[DIAG]`
2.18.4 **The five levers**, in order of effect: **split the state**, `-refresh=false` for
      non-drift runs, `-parallelism` tuning, fewer/cheaper data sources, and reducing
      `terraform_remote_state` fan-in. `[TABLE]` `[PROVE]`
2.18.5 **Splitting state is the only lever with unbounded headroom** — the others are constant
      factors. `[PROVE]`
2.18.6 **`-parallelism` tuning is bidirectional**: raise it when the provider is the bottleneck
      and the API is not rate-limited; lower it when you are being throttled (the AWS provider
      backs off, but a throttled plan is a slow plan). `[NUM]` `[PROVE]`
2.18.7 **Provider rate limits and retry behaviour** as a real cost: `max_retries`, the
      provider's backoff, and the symptom (`RequestLimitExceeded` mid-apply, a half-applied
      change). `[DIAG]` `[X-REF 18]`
2.18.8 **Large `for_each` collections**: 500 instances means 500 graph nodes, 500 refresh calls
      and a 500-entry plan nobody reads. The alternative is a coarser resource or a different
      tool. `[PROVE]` `[TRAP]`
2.18.9 **Module fetch cost**: Git-sourced modules are cloned per `init`; `TF_PLUGIN_CACHE_DIR`
      does not help modules. Shallow clones and a module mirror do. `[COST]`
2.18.10 **State file size arithmetic**: ~2–10 KB per resource instance of JSON, so 2,000
      resources is roughly 4–20 MB, downloaded and uploaded on every operation.
      `[NUM]` `[PROVE]` `[COST]`
2.18.11 **`TF_STATE_PERSIST_INTERVAL`** (OpenTofu) as the knob controlling how often state is
      written during a long apply, and the trade-off between write cost and crash exposure.
      `[TOFU]` `[NUM]` `[RESEARCH]`
2.18.12 **OpenTofu's compact JSON state encoding** (1.8) and the transfer saving. `[TOFU]`
      `[RESEARCH]`
2.18.13 **OpenTelemetry tracing of a run** (OpenTofu 1.10, experimental; improved 1.13) as the
      way to answer "which resource is slow" instead of guessing. `[TOFU]` `[RESEARCH]`
      `[X-REF 20]`
2.18.14 **The lock as a throughput ceiling**: one apply at a time per state, so a team's change
      throughput is bounded by `applies/day = 24h / mean apply duration`. Compute it for a
      6-minute apply and 25 states. `[PROVE]` `[NUM]` `[COST]`

## §2.19 Provisioners and the escape hatches

2.19.1 **The documentation's own position**: provisioners are a **last resort** — *"we strongly
      recommend using purpose-built solutions to perform post-apply operations."* `[SOURCE]`
2.19.2 **Why they break the model**: Terraform cannot plan them (they have no diff), cannot
      re-run them idempotently, and cannot detect that they failed halfway. `[PROVE]`
2.19.3 **`file`**, **`local-exec`**, **`remote-exec`** — the three built-ins, with arguments
      (`command`, `interpreter`, `working_dir`, `environment`, `inline`, `script`, `scripts`,
      `source`, `content`, `destination`). `[TABLE]` `[CFG]`
2.19.4 **`connection` blocks**: `type = ssh | winrm`, `host`, `user`, `private_key`, `password`,
      `port`, `timeout`, `agent`, plus `bastion_host`, `bastion_user`, `bastion_private_key`,
      `bastion_host_key` (correctly applied since **1.16**), and proxy settings.
      `[TABLE]` `[CFG]` `[RESEARCH]`
2.19.5 **WinRM is removed in OpenTofu 1.13**; OpenSSH for Windows is the migration.
      `[TOFU]` `[VERSION-TRAP]` `[RESEARCH]`
2.19.6 **`self`** is the only way to reference the parent resource inside a provisioner or its
      connection, because a name reference would be a self-dependency. `[SOURCE]` `[TRAP]`
2.19.7 **Create-time failure taints the resource**, so the next apply replaces it — which for a
      database is a data-loss event. `[TRAP]` `[PROVE]`
2.19.8 **`on_failure = continue | fail`** (default `fail`). `[CFG]`
2.19.9 **`when = destroy`** and its fundamental flaw: the provisioner must still be *in the
      configuration* when the destroy happens, so you cannot delete the resource block and the
      cleanup in the same commit. `[SOURCE]` `[TRAP]` `[PROVE]`
2.19.10 **The alternatives, ranked**: cloud-init/user data, a purpose-built provider resource,
      a baked image (Packer), a Kubernetes Job, and — new — **Terraform Actions** as the
      sanctioned declarative way to trigger imperative work. `[TABLE]` `[RESEARCH]`
2.19.11 **`terraform_data` + `triggers_replace`** as the "run this local-exec only when X
      changes" idiom, replacing `null_resource` + `triggers`. `[HCL]` `[RESEARCH]`
2.19.12 **A policy rule banning provisioners** in the QuizStakes estate, with the two documented
      exceptions and their approval path. `[PROVE]`

## §2.20 Terraform Actions, list resources and the new surfaces

2.20.1 **`action` blocks** (1.14, public beta): provider-defined imperative operations —
      `aws_lambda_invoke`, `aws_cloudfront_create_invalidation`, an Ansible playbook run —
      declared in configuration and invoked from `lifecycle.action_trigger` or
      `terraform apply -invoke=<address>`. `[HCL]` `[RESEARCH]`
2.20.2 **Why this exists**: it moves Day-2 imperative work from `local-exec` (unplanned,
      unreviewed, credentialed by whatever the runner has) into the graph, with the provider's
      authentication and the plan's review. `[PROVE]`
2.20.3 **`on_failure = halt | taint | continue`** (1.16) as the error contract, and what `taint`
      means for the triggering resource. `[NUM]` `[RESEARCH]`
2.20.4 **The QuizStakes use case**: invalidate the CloudFront cache after the
      `ClientAgreements` document version changes; invoke the `BankDeposits` reconciliation
      lambda after its schedule changes. Both are currently `local-exec` in most estates.
      `[HCL]`
2.20.5 **List resources** (1.14): `list` blocks in `*.tfquery.hcl`, executed by
      **`terraform query`**, which enumerates and filters existing infrastructure and can
      **generate import configuration** for the results. `[HCL]` `[CLI]` `[RESEARCH]`
2.20.6 **`terraform validate -query`** for offline validation of query files. `[CLI]`
      `[RESEARCH]`
2.20.7 **Terraform Search** (HCP, public beta) as the hosted bulk-discovery equivalent for AWS
      and Azure. `[RESEARCH]`
2.20.8 **Why this matters for QuizStakes specifically**: adopting a hand-built prod estate is
      the single biggest IaC project any team does, and 1.14 turned it from a script-writing
      exercise into a supported workflow. `[PROVE]` `[COST]`

## §2.21 HCP Terraform and Terraform Enterprise

2.21.1 **What they are**: two distributions of the same application — HCP Terraform (SaaS) and
      Terraform Enterprise (self-hosted, adding **audit logging and SAML SSO**). `[SOURCE]`
2.21.2 **The `cloud` block** vs the `remote` backend, `organization`, and
      `workspaces { name | tags | project }`. `[HCL]` `[CFG]`
2.21.3 **The remote-execution model**: the run happens on HCP's workers, so the plan artifact,
      the state and the credentials all live there — which is the value and the concern.
      `[PROVE]`
2.21.4 **Agents** for a private network: an outbound-only worker inside the VPC, so HCP never
      needs inbound access to QuizStakes' network. `[X-REF 18]`
2.21.5 **Workspace concepts**: variables and variable sets, sensitive variables, the VCS
      connection, `terraform` vs `env` variables, working directory, auto-apply, execution mode
      (remote/local/agent), and run triggers between workspaces. `[TABLE]`
2.21.6 **Run pipeline stages**: pre-plan → plan → **post-plan (run tasks, policy checks,
      cost estimation)** → pre-apply → apply → post-apply. The policy gate's exact position.
      `[FLOW]` `[RESEARCH]`
2.21.7 **Run tasks** as the third-party integration point (the **Cloudability governance run
      task** for cost, security scanners, CMDB checks). `[RESEARCH]`
2.21.8 **Private module registry**, **no-code modules** (self-service provisioning from a module
      with no HCL written), and **projects** for grouping. `[RESEARCH]`
2.21.9 **Drift detection and continuous validation** as managed features, including `check`
      block results surfaced over time. `[RESEARCH]`
2.21.10 **Ephemeral workspaces** with a TTL — the managed answer to preview environments.
      `[RESEARCH]`
2.21.11 **HYOK (Hold Your Own Key)**, GA 2025: customer-controlled keys for HCP-held sensitive
      artifacts (state, plans, variables). This is the control that makes HCP viable for a
      regulated estate. `[RESEARCH]` `[X-REF 13]`
2.21.12 **RUM-based pricing** (resources under management) and the arithmetic for a 2,000-resource
      QuizStakes estate — compared against the runner-minute cost of the self-built pipeline in
      §2.16. `[COST]` `[NUM]`
2.21.13 **The API and `tfe` provider**: managing HCP Terraform itself as code, and the
      chicken-and-egg it creates. `[TRAP]`
2.21.14 **Sentinel, OPA and Terraform Policy** availability by tier, and the fact that Sentinel
      is *only* available here. `[RESEARCH]`
2.21.15 **The honest positioning**: HCP buys the pipeline, the audit trail, the policy engine and
      the state service. It does not buy correctness, and it introduces a third party into the
      credential path. `[PROVE]`

## §2.22 Stacks

2.22.1 **The problem Stacks solve**: many interdependent configurations, each with its own state,
      manually ordered — and the same shape repeated per environment/region/account with
      copy-pasted roots. `[PROVE]` `[SOURCE]`
2.22.2 **Components**: `component` blocks in `*.tfcomponent.hcl`, each referencing a **module**
      with `source`, `inputs` and `providers`. Components share a lifecycle. `[HCL]` `[SOURCE]`
2.22.3 **Deployments**: `deployment` blocks in `*.tfdeploy.hcl`, each an instantiation of the
      whole component set with its own inputs and **its own isolated state**. `[HCL]` `[SOURCE]`
2.22.4 **`identity_token` and `store` blocks** in the deployment file for credentials, so a Stack
      can assume a different role per deployment. `[RESEARCH]`
2.22.5 **Deployment groups** and **auto-approve checks** — e.g. auto-approve any plan containing
      no deletions. This is policy expressed as orchestration. `[SOURCE]` `[RESEARCH]`
2.22.6 **Deferred changes**: when a component's inputs are unknown, HCP produces a **partial
      plan** and schedules a follow-up plan rather than failing. The canonical case is a
      Kubernetes cluster and the workloads on it in one Stack. `[SOURCE]` `[PROVE]` `[RESEARCH]`
2.22.7 **Why deferred changes matter conceptually**: they are the first crack in the
      "everything must be known at plan time" rule that shapes all of §1.15. `[PROVE]`
2.22.8 **Core's experimental `-allow-deferral`** (1.14 alpha, 1.17 alpha) as the non-HCP
      equivalent, and its status. `[RESEARCH]`
2.22.9 **The limits**: **HCP-only**, **max 500 deployments per Stack**, **max 100 components**,
      one deployment per group currently. `[NUM]` `[SOURCE]` `[RESEARCH]`
2.22.10 **`terraform stacks` CLI** (1.13+) and the GA backward-compatibility promise on the APIs.
      `[RESEARCH]`
2.22.11 **Stacks vs modules vs workspaces vs Terragrunt** — the four-way table that settles where
      each belongs. `[TABLE]` `[PROVE]`
2.22.12 **Migrating to Stacks**: the beta→GA rename from `tfstack.hcl` to `tfcomponent.hcl`, and
      the honest recommendation for a team of QuizStakes' size (Stacks earn their keep at the
      point where you have >6 layered states × 3 environments). `[PROVE]` `[VERSION-TRAP]`
      `[RESEARCH]`
2.22.13 **The QuizStakes Stack sketch**: components `network`, `data`, `platform`,
      `money-services`, `onboarding-services`, `read-models`, `observability`; deployments
      `dev`, `staging`, `prod-eu-west-1`, `prod-eu-west-2`. `[HCL]`

## §2.23 CDKTF and the language-based alternatives

2.23.1 **CDKTF is deprecated** — unsupported and unmaintained **since 10 December 2025**. Any
      recommendation of it is now a recommendation of an abandoned tool. `[VERSION-TRAP]`
      `[RESEARCH]`
2.23.2 **What it was**: TypeScript/Python/**Java**/C#/Go generating Terraform **JSON**
      configuration, then executing normal Terraform. It sat *above* Terraform, not beside it.
      `[SOURCE]`
2.23.3 **Why a Java engineer cared**: constructs, real types, IDE completion, unit tests in
      JUnit. And why it failed anyway: the generated configuration was unreviewable, the state
      addresses were synthesised, provider bindings had to be code-generated, and the abstraction
      leaked at every plan. `[PROVE]` `[TRAP]` `[X-REF 16]`
2.23.4 **What to do if you find CDKTF in a repository**: `cdktf synth` produces
      `cdk.tf.json`, which *is* valid Terraform configuration — so the migration path is to
      commit the synthesised JSON, then progressively rewrite it as HCL. `[SURGERY]` `[PROVE]`
2.23.5 **Pulumi** as the surviving language-based option, and the trade-off (real languages and a
      good state service versus a smaller ecosystem and its own hosted dependency). `[TABLE]`
2.23.6 **The general lesson**: for infrastructure, **reviewability beats expressiveness**, which
      is why the deliberately weak language won. State it as the argument, not as taste.
      `[PROVE]`

## §2.24 Choosing, and not choosing, Terraform

2.24.1 **The decision table** against CloudFormation, CDK, Pulumi, Crossplane, Ansible, and
      "clicking it": multi-cloud, state ownership, drift model, review model, ecosystem, and
      operational burden. `[TABLE]`
2.24.2 **Where Terraform is the wrong tool**: per-request or per-user objects, anything with a
      lifecycle shorter than a plan cycle, in-cluster Kubernetes objects that a controller should
      reconcile, and application-level configuration. `[TABLE]` `[TRAP]`
2.24.3 **The Kubernetes-provider question**, answered: use Terraform for the cluster and its
      cloud dependencies, and a GitOps controller for the workloads inside it — because
      Terraform's plan-time unknowns and one-shot reconciliation are exactly wrong for
      Kubernetes objects. `[PROVE]` `[X-REF 19]`
2.24.4 **The "Terraform all the way down" failure**: a single state containing the network, the
      cluster and 300 Kubernetes manifests, where a plan takes 14 minutes and an unknown value in
      one manifest blocks the whole apply. `[INCIDENT]` `[PROVE]`
2.24.5 **The two-tool boundary rule**: whatever provisions a thing must be the only thing that
      mutates it. Every drift incident in §2.10 is a violation of it. `[PROVE]`

---

# PART 3 — UNDER THE HOOD

## §3.1 The pipeline, end to end

3.1.1 The **eleven stages of a run**, named in order, each expanded below: CLI argument parsing →
      backend initialisation → configuration loading → module tree assembly → provider
      installation/launch → state read + lock → **graph construction** → **graph walk with
      evaluation** → provider RPCs (`ReadResource`, `PlanResourceChange`) → diff rendering /
      plan serialisation → (on apply) `ApplyResourceChange` + incremental state writes → lock
      release. `[FLOW]` `[PROVE]`
3.1.2 **Terraform Core is a Go program with four internal packages worth naming**: `configs`
      (HCL → configuration), `terraform` (graph + evaluation), `plans` (the change set),
      `states` (the state model), plus `providers` (the plugin client). Knowing the boundaries
      explains every error message prefix. `[SOURCE]`
3.1.3 **Where the boundary between Core and provider actually falls**: Core owns the graph,
      evaluation, unknowns, sensitivity, state and the diff *presentation*; the provider owns
      schemas, the *decision* about replacement, all API calls, and every default value.
      `[TABLE]` `[PROVE]`
3.1.4 **The consequence of that boundary**: "Terraform decided to replace my instance" is always
      wrong — the provider decided, in `PlanResourceChange`, and the provider's changelog is where
      the answer is. `[TRAP]` `[PROVE]`

## §3.2 HCL parsing and the value system

3.2.1 **Two-phase parsing**: the HCL library parses to a syntax tree with **no knowledge of
      Terraform's schema**, then Terraform's `configs` package decodes blocks against expected
      schemas. This is why a misspelled block name gives a Terraform-level error while a missing
      brace gives an HCL-level one. `[PROVE]` `[DIAG]`
3.2.2 **`hcl.Body`, `hcl.Attribute`, `hcl.Expression`** and partial decoding — the mechanism
      behind `override.tf` merging and behind "unsupported argument" diagnostics carrying a
      line/column. `[SOURCE]`
3.2.3 **Diagnostics** as a first-class type: severity, summary, detail, subject range. Why
      Terraform can report *many* configuration errors at once but stops at the first provider
      error. `[PROVE]`
3.2.4 **`cty`** — the value/type system underneath everything: primitive, list, set, map, object,
      tuple, plus **unknown**, **null** and **marks**. Every HCL expression evaluates to a
      `cty.Value`. `[SOURCE]` `[PROVE]`
3.2.5 **Why `number` is arbitrary precision**: `cty.Number` wraps `big.Float`, which is why
      Terraform round-trips a 20-digit integer that JSON/float64 would corrupt — and why a
      provider with an `int64` field can still reject it. `[NUM]` `[PROVE]`
3.2.6 **Marks** are the mechanism for both `sensitive` and `ephemeral`: a mark travels with the
      value through every function and operator, which is why sensitivity propagates and cannot
      be laundered except by `nonsensitive()`. `[PROVE]` `[SOURCE]`
3.2.7 **Unknown values in `cty`**: `cty.UnknownVal(type)` — a value whose *type* is known and
      whose content is not. Operations on unknowns produce unknowns; comparisons produce unknown
      booleans, which is why a conditional on an unapplied attribute cannot be resolved at plan
      time. `[PROVE]` `[TRAP]`
3.2.8 **Refinements** — the newer mechanism that lets Terraform know things *about* an unknown
      (not null, string prefix, collection length lower bound), which is how modern versions
      resolve some previously-blocking `for_each` and conditional cases. `[RESEARCH]`
3.2.9 **The evaluation context** (`EvalContext`): the scope of `var.*`, `local.*`, `each.*`,
      `count.index`, `self`, `path.*`, `terraform.*`, and how module boundaries create nested
      scopes. `[PROVE]`
3.2.10 **Why there is no `import` of one `.tf` file into another**: there is no file scope — the
      directory *is* the scope, and all files are merged before evaluation. `[PROVE]` `[TRAP]`

## §3.3 The graph

3.3.1 **What the graph is**: a **DAG** whose vertices are graph nodes (not only resources) and
      whose edges are dependencies. It is built fresh on every run, from configuration **and**
      state. `[PROVE]`
3.3.2 **The node types**, per the internals documentation: **resource nodes** (one per instance,
      including one per `count` index), **provider configuration nodes**, and **resource
      meta-nodes** (a convenience grouping for `count`, containing no actions of their own).
      Plus, in practice: variable, local, output, module expansion, data, and destroy nodes.
      `[TABLE]` `[SOURCE]`
3.3.3 **The nine construction steps** the documentation enumerates: resource nodes from
      configuration → provisioner mapping → explicit `depends_on` edges → **orphaned resources**
      from state → provider configuration nodes → interpolation-derived edges → … → **cycle
      check** and **single root node**. `[FLOW]` `[SOURCE]`
3.3.4 **Graph transformers** as the architecture: the graph is built by a *pipeline of
      transformers*, each adding or rewriting nodes (`ConfigTransformer`, `StateTransformer`,
      `AttachSchemaTransformer`, `ProviderTransformer`, `DestroyEdgeTransformer`,
      `TransitiveReductionTransformer`, `RootTransformer`). Naming them explains the internal
      error messages. `[TABLE]` `[SOURCE]` `[RESEARCH]`
3.3.5 **Orphans come from state, not configuration** — this is the mechanism by which deleting a
      `resource` block produces a destroy plan, and why it needs state's recorded dependency
      edges to order that destroy. `[PROVE]`
3.3.6 **Destroy edges are reversed**: if A depends on B, then destroy(B) depends on destroy(A).
      The transformer that does this, and the proof that it is the only correct ordering.
      `[PROVE]` `[TABLE]`
3.3.7 **Replacement as two nodes**: a destroy node and a create node, ordered
      destroy→create normally and **create→destroy** under `create_before_destroy`. `[PROVE]`
3.3.8 **`create_before_destroy` propagates upward**: if A must be created before its
      replacement's destroy, and B depends on A, B is forced into create-before-destroy too. This
      is why one `lifecycle` flag can restructure a subgraph — and why it sometimes fails with
      *"…must also have create_before_destroy"*. `[PROVE]` `[DIAG]` `[TRAP]`
3.3.9 **Transitive reduction**: redundant edges are removed so the graph is minimal, which is why
      `terraform graph` output does not show every reference you wrote. `[PROVE]`
3.3.10 **The walk**: depth-first, *"a node is walked as soon as all of its dependencies are
      walked"*, with **up to 10 nodes concurrently** by default (`-parallelism`). `[SOURCE]`
      `[NUM]` `[PROVE]`
3.3.11 **The critical path determines apply duration**, not the resource count — so parallelism
      cannot help a chain of five sequential dependencies. Worked for a
      VPC → subnet → security group → database → service chain. `[PROVE]` `[NUM]`
3.3.12 **Cycle detection and reading a cycle error**: the message lists the nodes in the cycle;
      the fix is almost always a `depends_on` you added or two resources referencing each other's
      attributes (a security-group pair is the classic). The correct fix for that case —
      separate `aws_security_group_rule` / `vpc_security_group_ingress_rule` resources.
      `[DIAG]` `[TRAP]` `[PROVE]`
3.3.13 **Module expansion** as a graph operation: a `for_each` module becomes N subgraphs, and
      `depends_on` on the module attaches to all of them. `[PROVE]`
3.3.14 **`terraform graph -type=plan|apply|plan-destroy`** and (1.16) **Mermaid** output; how to
      make a 500-node graph legible (filter by module, render only the critical path).
      `[CLI]` `[RESEARCH]`
3.3.15 **The graph and `-target`**: targeting prunes the graph to the target and its
      *dependencies* — not its dependents — which is exactly why the resulting state can be
      inconsistent. `[PROVE]` `[TRAP]`
3.3.16 **Provider nodes and initialisation order**: a provider configuration that depends on a
      resource attribute (a common anti-pattern) makes the provider itself a graph dependency,
      and Terraform will refuse or defer. `[TRAP]` `[PROVE]`

## §3.4 Evaluation, unknowns and the two-phase model

3.4.1 **Plan and apply are the same walk, twice**, with different node implementations —
      which is why an error that appears only at apply is almost always an unknown that became
      known and violated an assumption. `[PROVE]`
3.4.2 **The unknown-propagation rule**: any expression containing an unknown is unknown; any
      resource argument that is unknown is planned as `(known after apply)`. `[PROVE]`
3.4.3 **Why `count`/`for_each` cannot be unknown**: the number of graph *nodes* would be unknown,
      and the graph must be built before evaluation completes. This is the deepest structural
      constraint in Terraform and it explains a whole class of errors. `[PROVE]` `[TRAP]`
3.4.4 **The full error text and its remedies**: *"The 'for_each' value depends on resource
      attributes that cannot be determined until apply, so Terraform cannot predict how many
      instances will be created."* Remedies: derive keys from configuration; two-phase apply with
      `-target`; split into two configurations; or (HCP) Stacks' deferred changes. `[DIAG]`
      `[TABLE]` `[RESEARCH]`
3.4.5 **Deferred actions** as the structural answer: produce a *partial* plan, apply it, then
      re-plan with the previously-unknown values known. Alpha in core (`-allow-deferral`), GA in
      Stacks. `[PROVE]` `[RESEARCH]`
3.4.6 **Data sources and the plan/apply split**: a data source with known arguments is read at
      plan; with unknown arguments it is deferred to apply and its result is unknown throughout
      the plan. `[PROVE]`
3.4.7 **Provider configuration with unknown values** is an error, because the provider must be
      configured before any of its resources can be planned. `[PROVE]` `[TRAP]`
3.4.8 **`terraform.applying`** and how it is implemented — a context value differing between the
      two walks. `[RESEARCH]`
3.4.9 **Plan-time vs apply-time consistency checks**: Core verifies that the applied value
      **conforms to the planned value** and raises *"Provider produced inconsistent result after
      apply"* when it does not. That error is a provider bug, always. `[DIAG]` `[TRAP]` `[PROVE]`
3.4.10 **The consistency rules Core enforces on providers**, stated as invariants: a planned
      known value must be returned unchanged; a planned unknown may become anything of the right
      type; a planned null must stay null. Violating any of the three produces a specific
      diagnostic. `[TABLE]` `[PROVE]` `[RESEARCH]`

## §3.5 The resource instance change lifecycle

3.5.1 **The RPC sequence for one managed resource, per run**, in order:
      `GetProviderSchema` → `ValidateProviderConfig` → `ConfigureProvider` →
      `ValidateResourceConfig` → `UpgradeResourceState` → `ReadResource` →
      `PlanResourceChange` → (apply) `ApplyResourceChange`. `[FLOW]` `[SOURCE]` `[PROVE]`
3.5.2 **`GetProviderSchema`** — the whole schema for every resource, data source, function and
      the provider itself, transferred at startup. Why the AWS provider's schema is tens of
      megabytes and why that shows up as `init`/plan startup latency. `[NUM]` `[COST]`
3.5.3 **`ValidateResourceConfig`** — provider-side validation before planning; the reason some
      errors appear during `validate` and some only during `plan`. `[PROVE]`
3.5.4 **`UpgradeResourceState`** — the mechanism that makes state forward-compatible: the
      provider migrates a stored instance from its recorded `schema_version` to the current one.
      This is why a provider upgrade can rewrite state without any infrastructure change.
      `[PROVE]` `[NUM]` `[TRAP]`
3.5.5 **`ReadResource`** — refresh for one instance. Returns the current object, or **null** to
      mean "it is gone", which Core turns into a create in the plan. `[PROVE]`
3.5.6 **`PlanResourceChange`** — the provider receives prior state, configuration and a proposed
      new state, and returns the **planned new state**, `RequiresReplace` paths, and private
      data. **This is where replacement is decided.** `[PROVE]` `[SOURCE]`
3.5.7 **`ApplyResourceChange`** — performs the API calls and returns the final state and private
      data. Errors here may be partial: the object may exist even when the RPC failed. `[PROVE]`
      `[TRAP]`
3.5.8 **Private data** (`private` in state): opaque provider-owned bytes per instance, used for
      things like SDKv2 timeouts and internal flags. **1.16 persists provider "planned private
      data" across plan and apply** — a real behavioural change. `[RESEARCH]`
      `[VERSION-TRAP]`
3.5.9 **`ImportResourceState`** and, from 1.14, **`GenerateResourceConfiguration`** — how import
      and `-generate-config-out` are actually implemented. `[RESEARCH]`
3.5.10 **`ReadDataSource`**, `ValidateDataResourceConfig`; **`OpenEphemeralResource`**,
      `RenewEphemeralResource`, `CloseEphemeralResource`; **`CallFunction`**/`GetFunctions`;
      **`ListResource`** (1.14); `MoveResourceState` (cross-type moves); `GetResourceIdentitySchemas`.
      `[TABLE]` `[RESEARCH]`
3.5.11 **`Stop`** — the RPC Core calls on SIGINT so providers can cancel in-flight work, and why
      hitting Ctrl-C twice is how state gets left inconsistent. `[TRAP]` `[PROVE]`
3.5.12 **The create-then-crash case, traced**: `ApplyResourceChange` creates the object, the
      network call returns after Core died. State has no record; reality has the object. Next
      plan proposes a create, which fails on a name conflict. The recovery is `import`.
      `[FLOW]` `[INCIDENT]` `[SURGERY]`
3.5.13 **The timeout case**: SDKv2's per-resource `timeouts` block, what the provider does when
      it fires (usually returns an error while the cloud continues), and why a timed-out RDS
      creation is the worst version of §3.5.12. `[CFG]` `[TRAP]` `[X-REF 18]`

## §3.6 The plugin protocol

3.6.1 **The transport**: `hashicorp/go-plugin` launches the provider binary as a subprocess and
      negotiates a handshake over stdout, then all traffic is **gRPC over a local socket**.
      `[PROVE]` `[SOURCE]`
3.6.2 **Handshake details** worth knowing: the magic cookie environment variable, the protocol
      version, the network address and the TLS certificate printed on the provider's stdout —
      which is why a provider that prints to stdout breaks the handshake. `[TRAP]` `[DIAG]`
3.6.3 **`tfplugin5.proto` and `tfplugin6.proto`** live in `docs/plugin-protocol/` in the
      Terraform repository and are the canonical definition. `[SOURCE]`
3.6.4 **Protocol 5 requires CLI ≥ 0.12; protocol 6 requires CLI ≥ 1.0.** A provider may serve
      both via muxing. `[NUM]` `[SOURCE]`
3.6.5 **What protocol 6 added**: **nested attributes** — `SchemaAttribute` with a `NestedType`
      field — allowing argument syntax instead of block syntax and **per-nested-attribute
      sensitivity** instead of marking a whole read-only attribute. `[SOURCE]` `[PROVE]`
      `[RESEARCH]`
3.6.6 **Why that matters to a configuration author**: it is the reason two AWS resources of
      similar age take different syntax for what looks like the same thing. `[TRAP]`
3.6.7 **Schema shape**: `Block` with `attributes` and `block_types`; per-attribute `Required`,
      `Optional`, `Computed`, `Sensitive`, `WriteOnly`, `Deprecated`; `NestingMode` =
      `SINGLE`/`LIST`/`SET`/`MAP`/`GROUP`; `MinItems`/`MaxItems`. `[TABLE]` `[SOURCE]`
3.6.8 **`Optional + Computed`** — the shape behind most surprising diffs: if you omit the
      argument the provider supplies a value and Terraform keeps it; if you later set it,
      you take ownership; if you then remove it, **Terraform does not revert it**. `[PROVE]`
      `[TRAP]`
3.6.9 **`msgpack` encoding of dynamic values** on the wire, and why the protocol can carry
      unknowns and nulls faithfully where JSON could not. `[PROVE]`
3.6.10 **`terraform providers schema -json`** as the human-accessible projection of all of this,
      and how to read `"required_with"`, `"computed"` and replacement information from it.
      `[CLI]` `[DIAG]`
3.6.11 **Provider process lifecycle**: one process per provider *configuration*, started at plan,
      reused for the walk, killed at the end; `TF_LOG_PROVIDER` for its logs; and what an
      orphaned provider process means. `[PROVE]` `[DIAG]`

## §3.7 Provider development: framework vs SDKv2

3.7.1 **The two SDKs**: `terraform-plugin-sdk` v2 (legacy; *"maintained for Terraform 1.x"* with
      **feature development stopped**) and `terraform-plugin-framework` (current, recommended).
      `[SOURCE]` `[RESEARCH]`
3.7.2 **SDKv2's model**: declarative `*schema.Resource` structs with `Create`/`Read`/`Update`/
      `Delete` functions, `*schema.ResourceData` accessors, `d.Get()` returning **zero values**
      for null and unknown — *"making them indistinguishable"*. `[SOURCE]` `[PROVE]`
3.7.3 **The zero-value problem, made concrete**: SDKv2 cannot distinguish `count = 0` from
      "unset", or `""` from null, which is the root cause of a large family of "Terraform ignores
      my explicit false" bugs. `[PROVE]` `[TRAP]`
3.7.4 **The framework's model**: Go interfaces (`resource.Resource` with `Metadata`, `Schema`,
      `Create`, `Read`, `Update`, `Delete`, optionally `ImportState`, `ModifyPlan`,
      `ConfigValidators`, `UpgradeState`), request/response structs per operation, and typed
      values that expose **null and unknown distinctly** (`types.String`, `basetypes`).
      `[SOURCE]` `[TABLE]`
3.7.5 **Plan modifiers** as the framework's replacement for `ForceNew`:
      `stringplanmodifier.RequiresReplace()`, `UseStateForUnknown()`,
      `RequiresReplaceIfConfigured()`, and custom modifiers. `[SOURCE]` `[PROVE]`
3.7.6 **`UseStateForUnknown()`** is the fix for the most common provider bug — an attribute that
      shows `(known after apply)` on every plan because the provider does not tell Core it will
      not change. `[PROVE]` `[TRAP]`
3.7.7 **`SDKv2` `ForceNew: true`** vs the framework's `RequiresReplace` — the same effect, two
      mechanisms, and the exact place a version bump changes replacement behaviour.
      `[TABLE]` `[PROVE]`
3.7.8 **`terraform-plugin-mux`** for incremental migration: *"migrate individual resources or
      data sources to the framework one at a time"*, serving both SDKs from one binary.
      `[SOURCE]` `[RESEARCH]`
3.7.9 **`terraform-plugin-go`** as the raw protocol layer, for the rare provider that implements
      the protocol directly. `[RESEARCH]`
3.7.10 **`terraform-plugin-testing`** and acceptance tests: `TF_ACC=1`, `resource.Test`,
      `TestStep` with `Config`/`Check`/`ImportState`, `PlanOnly` steps asserting an empty plan,
      and `ExpectNonEmptyPlan`. The `PlanOnly` step is the provider-side equivalent of §2.13.19.
      `[CFG]` `[X-REF 16]`
3.7.11 **Write-only argument implementation** on both SDKs, and the framework's rule that the
      provider is the **terminal point** for an ephemeral value: use it or ignore it, never store
      it. `[SOURCE]` `[RESEARCH]`
3.7.12 **Provider-defined functions** in the framework: the `function.Function` interface with
      `Definition` (parameters, return type, variadic support) and `Run`; requires **protocol
      support and Terraform 1.8+**; callable as `provider::<local>::<name>()`. `[SOURCE]`
      `[RESEARCH]`
3.7.13 **Ephemeral resources** in the framework: `ephemeral.EphemeralResource` with `Open`,
      optional `Renew` and `Close`, plus `RenewAt` and private data. `[RESEARCH]`
3.7.14 **Actions and list resources** as new provider-side surfaces (1.14) — named, with their
      protocol additions. `[RESEARCH]`
3.7.15 **Why a Java engineer should still read provider source**: the answer to "why does this
      force replacement", "why is this always unknown" and "why is my explicit `false` ignored"
      is 20 lines of Go in a public repository, and reading it is faster than guessing.
      `[PROVE]`
3.7.16 **`GetProviderSchema` cost and provider size** as a design consequence: the AWS provider
      is one binary with ~1,400 resources, so every run pays for the whole schema. The
      (rejected) alternatives and why the monolith won. `[NUM]` `[COST]`

## §3.8 The state file, decoded

3.8.1 **Top-level keys of a `version = 4` state file**: `version`, `terraform_version`,
      `serial`, `lineage`, `outputs`, `resources`, `check_results`. `[TABLE]` `[SOURCE]`
      `[RESEARCH]`
3.8.2 **`resources[]`** entry shape: `module` (absent for root), `mode` (`managed` | `data`),
      `type`, `name`, `provider` (a fully-qualified provider *configuration* address), and
      `instances[]`. `[TABLE]` `[RESEARCH]`
3.8.3 **`instances[]`** entry shape: `index_key` (int for `count`, string for `for_each`),
      `schema_version`, `attributes` (the whole object as JSON), `sensitive_attributes` (paths),
      `private` (base64 provider data), `dependencies` (addresses),
      `create_before_destroy`, and `status` (`tainted`). `[TABLE]` `[RESEARCH]`
3.8.4 **`outputs`** entry shape: `value`, `type`, `sensitive`. Note that the *value* is stored in
      full even when sensitive. `[PROVE]` `[TRAP]`
3.8.5 **`check_results`** — the recorded outcome of `check` blocks and conditions, which is how
      HCP surfaces continuous validation history. `[RESEARCH]`
3.8.6 **`dependencies` is the recorded graph**, and the leaf that makes §1.17.5 concrete: this
      array is why a destroy after configuration deletion is correctly ordered. `[PROVE]`
3.8.7 **`serial` semantics**: incremented on every write; a push with a lower or equal serial is
      rejected; this is optimistic concurrency control on the state object. `[PROVE]` `[NUM]`
3.8.8 **`lineage` semantics**: a UUID generated when state is created; a mismatch means you have
      pointed at an unrelated state's history, and Terraform refuses. `[PROVE]`
3.8.9 **`schema_version` per instance** drives `UpgradeResourceState`; a state written by
      provider 4.x is upgraded in place by 5.x, and the upgrade is **not reversible**.
      `[PROVE]` `[TRAP]`
3.8.10 **`sensitive_attributes`** as a list of attribute *paths*, which is how sensitivity
      survives a round trip through state. `[PROVE]`
3.8.11 **A real state excerpt, read line by line**, for `aws_db_instance.funds_ledger` — every
      key explained, including where the password would be if the configuration had not used
      `manage_master_user_password`. `[SOURCE]` `[DIAG]` `[PROVE]`
3.8.12 **What is *not* in state**: your configuration (only the resolved attribute snapshot), the
      plan, the provider binaries, any history (the backend's versioning is the history), and
      module source code. `[TABLE]` `[TRAP]`
3.8.13 **State size arithmetic** for QuizStakes: 25 service runtimes × ~12 resources each × ~3 KB
      = ~900 KB for the services layer; the ledger layer's parameter groups push its instances to
      ~8 KB each. Uploaded and downloaded per operation. `[NUM]` `[COST]` `[PROVE]`
3.8.14 **Why `terraform state pull | jq` is the right first debugging step** for any
      "why does it think that" question, and the four `jq` queries worth memorising.
      `[CLI]` `[DIAG]`
3.8.15 **The pseudo-resources in state**: `data` instances, `terraform_data`, `random_*`,
      `null_resource` — objects whose only existence *is* the state entry. Deleting state
      destroys them in the only sense they exist. `[PROVE]`
3.8.16 **State format stability**: the CLI is the stable interface, the JSON is not; the
      documentation says *"direct parsing requires ongoing maintenance"*. Therefore tooling
      should read `terraform show -json`, not the file. `[SOURCE]` `[TRAP]`

## §3.9 Locking, internals per backend

3.9.1 **State locking as distributed mutual exclusion**, framed properly: you need an atomic
      compare-and-set on a shared object plus a way to break a lock held by a dead holder. Every
      backend's implementation is one of those two primitives. `[PROVE]` `[X-REF 09]`
3.9.2 **S3 + `use_lockfile`**: `PutObject` with `If-None-Match: *` on `<key>.tflock` — an atomic
      create-if-absent, so exactly one writer wins. Release is a delete. `[PROVE]` `[RESEARCH]`
      `[X-REF 18]`
3.9.3 **S3 + DynamoDB (legacy)**: conditional `PutItem` on `LockID = "<bucket>/<key>"` with
      `attribute_not_exists`. Deprecated. `[PROVE]` `[VERSION-TRAP]`
3.9.4 **The lock payload** (`LockInfo`): `ID`, `Operation`, `Info`, `Who` (user@host), `Version`,
      `Created`, `Path`. This is what the "Lock Info" block in the error message prints, and
      `Who` is how you find the human holding it. `[TABLE]` `[DIAG]`
3.9.5 **Neither mechanism has a TTL by default.** The current guide's claim that "DynamoDB lock
      entries have a TTL (default 0 = no expiry)" must be corrected: Terraform writes **no
      expiry** and relies on the client releasing it; a crashed client leaves the lock forever
      until `force-unlock`. `[TRAP]` `[PROVE]` `[VERSION-TRAP]`
3.9.6 **`force-unlock` requires the exact lock ID** as a nonce, precisely to make "unlock
      whatever is stuck" impossible to script accidentally. `[SOURCE]` `[PROVE]`
3.9.7 **When `force-unlock` is safe**, as a test: the holder's process is provably gone (the CI
      job is finished/cancelled, the `Who` host is unreachable), and no state write is in flight.
      Otherwise you are creating two writers. `[SURGERY]` `[PROVE]`
3.9.8 **What two writers actually do**: both read serial N, both write serial N+1, and the second
      write overwrites the first — so a resource created by the first apply is **absent from
      state while existing in reality**. That is the corruption, precisely. `[PROVE]` `[INCIDENT]`
      `[TRAP]`
3.9.9 **Why S3 versioning is the recovery** and object-level rollback the procedure. `[SURGERY]`
3.9.10 **The absence of fencing tokens**: Terraform's lock is advisory-with-cooperation, not
      fenced — a lock holder that resumes after a `force-unlock` is not blocked from writing.
      Compare with the fencing-token design in `22-system-design.md`. `[PROVE]` `[X-REF 22]`
      `[X-REF 09]`
3.9.11 **`azurerm`** blob leases (a real lease with a duration and renewal), **`gcs`** object
      generation preconditions, **`pg`** advisory locks, **`consul`** sessions, **`http`**
      backend's `lock_address`/`unlock_address` — one line each on which primitive they use.
      `[TABLE]`
3.9.12 **The lease-vs-lock distinction** and why Azure's design is arguably better: a lease
      expires, so a dead holder self-heals; an S3 object does not. The trade-off is that a live
      holder can lose its lease mid-apply. `[PROVE]` `[TABLE]`
3.9.13 **HCP Terraform's run queue** as the alternative model: the platform serialises runs per
      workspace, so the lock is a queue with discipline rather than a race with retries.
      `[PROVE]`

## §3.10 The plan file and the JSON formats

3.10.1 **The saved plan file** is a **binary archive**, opaque and version-specific: it contains
      the planned changes, the prior state, the configuration snapshot and the variable values —
      which is why it is self-contained and why it contains secrets. `[PROVE]` `[TRAP]`
3.10.2 **`terraform show -json <planfile>`** as the stable projection, with
      `format_version = "1.0"` since 1.1.0. `[SOURCE]` `[NUM]`
3.10.3 **Plan JSON top-level keys**: `format_version`, `terraform_version`, `prior_state`,
      `configuration`, `planned_values`, `proposed_unknown`, `resource_changes`,
      `output_changes`, `checks`, `applyable`, `complete`, `errored`. `[TABLE]` `[SOURCE]`
3.10.4 **`applyable` / `complete` / `errored`** as the automation contract: `complete = false`
      means the plan is partial (deferred actions), which a pipeline must handle rather than
      treat as success. `[PROVE]` `[RESEARCH]`
3.10.5 **`resource_changes[]`** entry: `address`, `module_address`, `mode`, `type`, `name`,
      `index`, `provider_name`, `action_reason`, and `change`. `[TABLE]`
3.10.6 **The `actions` array**, complete: `["no-op"]`, `["create"]`, `["read"]`, `["update"]`,
      `["delete"]`, `["delete","create"]` (destroy-then-create) and `["create","delete"]`
      (create-then-destroy). **The order encodes `create_before_destroy`** — that is the whole
      difference. `[TABLE]` `[SOURCE]` `[PROVE]`
3.10.7 **`before` / `after` / `after_unknown` / `before_sensitive` / `after_sensitive` /
      `replace_paths`** — each explained, with `after_unknown` being how `(known after apply)`
      is represented and `replace_paths` being how `# forces replacement` is derived.
      `[TABLE]` `[SOURCE]` `[PROVE]`
3.10.8 **`action_reason`** values (`replace_because_tainted`, `replace_because_cannot_update`,
      `replace_by_request`, `delete_because_no_resource_config`,
      `delete_because_no_module`, …) — the machine-readable "why", and the field every policy
      should key on rather than guessing from `actions`. `[TABLE]` `[RESEARCH]`
3.10.9 **State JSON** (`terraform show -json` with no plan): `format_version`,
      `terraform_version`, `values` (a values representation). Simpler than the plan by design.
      `[SOURCE]`
3.10.10 **The `configuration` section** as the basis of `tfconfig`-style policy — it exposes
      *expressions*, including references, which lets a policy assert "this argument must be a
      reference to a KMS key resource, not a literal". `[PROVE]`
3.10.11 **The machine-readable UI (`-json` on plan/apply)**: a newline-delimited event stream with
      `@level`, `@message`, `@module`, `type` (`planned_change`, `apply_start`,
      `apply_complete`, `diagnostic`, `change_summary`), and how PR-comment tooling consumes it.
      `[TABLE]` `[CLI]`
3.10.12 **Reading a plan diff like a professional**: the symbol legend, `# forces replacement`,
      `(known after apply)`, `(sensitive value)`, the `~` vs `-/+` distinction, the change
      summary line, and the `Objects have changed outside of Terraform` block. Every one of these
      is a decision point in review. `[DIAG]` `[TABLE]` `[PROVE]`

## §3.11 Refresh internals

3.11.1 **Refresh is per-instance `ReadResource`**, run as part of the plan walk, not as a
      separate phase — which is why refresh respects `-parallelism` and provider rate limits.
      `[PROVE]`
3.11.2 **The refreshed values do not go to disk during `plan`** (they go into the in-memory prior
      state and the plan file); `apply -refresh-only` is what persists them. `[PROVE]` `[TRAP]`
3.11.3 **A `null` return from `ReadResource`** means the object is gone; Core removes the instance
      from prior state and plans a create. This is how "someone deleted it in the console" is
      handled. `[PROVE]`
3.11.4 **The `Objects have changed outside of Terraform` report** is generated by diffing prior
      state against refreshed state — the drift report, printed even when it causes no change.
      `[DIAG]` `[PROVE]`
3.11.5 **What refresh cannot see**: attributes the provider does not read back (write-only,
      some secrets), objects not in state, and anything the API does not expose. `[PROVE]`
3.11.6 **`-refresh=false` and the risk it takes**: the plan is computed against a possibly-stale
      snapshot, so an apply can fail on a precondition the world no longer satisfies — or worse,
      succeed and overwrite a change someone else made deliberately. `[PROVE]` `[TRAP]`
3.11.7 **Legacy `terraform refresh`** wrote state directly with no plan; `apply -refresh-only`
      shows you the changes first. The migration and why it matters. `[VERSION-TRAP]`
3.11.8 **Refresh and `ignore_changes`** interact in a way people get wrong: refresh **always**
      records reality in state; `ignore_changes` only suppresses the resulting *diff*. The state
      therefore holds the drifted value. `[PROVE]` `[TRAP]`

## §3.12 Sensitivity, ephemerality and the mark machinery

3.12.1 **Marks**, mechanically: a `cty.Value` may carry a set of marks; `sensitive` and
      `ephemeral` are two of them; operators and functions **union** the marks of their inputs
      into their output. `[PROVE]` `[SOURCE]`
3.12.2 **The consequence**: `"postgres://${var.user}:${var.password}@${local.host}"` is sensitive
      in its entirety, so the whole URL is redacted — which is correct but often surprising.
      `[PROVE]` `[TRAP]`
3.12.3 **Redaction happens at rendering time**, not storage time. The value in state and in the
      plan file is plaintext; only the display is redacted. This is the precise mechanical
      statement of the current guide's trap. `[PROVE]` `[TRAP]`
3.12.4 **`sensitive_attributes` in state** carries the marks forward across runs.
3.12.5 **Provider-declared sensitivity**: `Sensitive: true` in the schema marks an attribute
      automatically (a generated password), and protocol 6 allows this per nested attribute.
      `[PROVE]` `[RESEARCH]`
3.12.6 **Ephemeral marks are enforced, not cosmetic**: Core *errors* if an ephemeral value reaches
      a persisted location. That enforcement is the whole feature. `[PROVE]` `[RESEARCH]`
3.12.7 **`ephemeralasnull()`** as the escape: convert an ephemeral value to null so an expression
      can be evaluated in a persisted context. `[CFG]` `[RESEARCH]`
3.12.8 **Where sensitivity leaks anyway**, enumerated: a provisioner's command line, a
      `local_file` written to disk, a `terraform output -json` in a CI log, a plan artifact
      published to a build store, and an error message from a provider that echoes the input.
      `[TABLE]` `[TRAP]` `[X-REF 13]`

## §3.13 Version history — what changed and when

3.13.1 **The table**, one row per release from 0.12 to 1.16 plus OpenTofu 1.6–1.13, with the
      feature and the reason it existed. This is the section every `[VERSION-TRAP]` in the file
      points back to. `[TABLE]` `[RESEARCH]`
3.13.2 **0.12** — HCL2, first-class expressions, `for`, `dynamic`, real types. The largest
      breaking change in the tool's history. `[NUM]`
3.13.3 **0.13** — provider source addresses and third-party provider installation;
      **`count`/`for_each` on modules**.
3.13.4 **0.14** — the **dependency lock file**, concise diffs, `sensitive` variables.
3.13.5 **0.15 / 1.0** — the compatibility promise, and the end of the state-format churn era.
3.13.6 **1.1** — **`moved` blocks**.
3.13.7 **1.2** — **`precondition`/`postcondition`**, `replace_triggered_by`.
3.13.8 **1.3** — `moved` for module refactoring at scale, better `for_each` diffs.
3.13.9 **1.4** — **`terraform_data`**.
3.13.10 **1.5** — **`import` blocks**, **`check` blocks**, `-generate-config-out`.
      **1.5.5 is the last MPL-2.0 release.** `[NUM]`
3.13.11 **1.6** — **`terraform test`**; OpenTofu 1.6 forks.
3.13.12 **1.7** — **`removed` blocks**, provider mocking in tests.
3.13.13 **1.8** — **provider-defined functions**, provider-defined refactoring support.
3.13.14 **1.9** — cross-variable `validation` references, `templatestring`.
3.13.15 **1.10** — **ephemeral values and `ephemeral` resources**, S3 native locking (beta),
      `terraform.applying`.
3.13.16 **1.11** (27 Feb 2025) — **write-only arguments**, **S3 native locking GA
      (`use_lockfile`)** with DynamoDB arguments deprecated, `-junit-xml` GA, new Azure backend
      authentication arguments. `[NUM]` `[RESEARCH]`
3.13.17 **1.12** (14 May 2025) — **OCI object storage backend**, **`import` by `identity`**,
      Linux kernel ≥ 3.2 requirement. `[NUM]` `[RESEARCH]`
3.13.18 **1.13** — **`terraform stacks` CLI**; test files must declare `variable` blocks for
      external variables. `[RESEARCH]`
3.13.19 **1.14** — **list resources (`*.tfquery.hcl`) and `terraform query`**, **Action blocks**,
      `GenerateResourceConfiguration` RPC, deferred actions behind `-allow-deferral` (alpha),
      `terraform test cleanup` (experimental), **macOS Monterey minimum** (Go 1.25), container
      parallelism now derived from CPU bandwidth limits. `[NUM]` `[RESEARCH]` `[X-REF 19]`
3.13.20 **1.15** — **Windows ARM64 builds**, **`deprecated` on variables and outputs**,
      **dynamic module `source`/`version`**, **output type constraints**, `convert()`,
      **backend validation in `validate`**, S3 backend `aws login` support, and the
      `AWS_USE_FIPS_ENDPOINT`/`AWS_USE_DUALSTACK_ENDPOINT` strict-boolean change. `[NUM]`
      `[RESEARCH]`
3.13.21 **1.16** (26 Aug 2026) — **`import` blocks in modules**, **`lifecycle { destroy = false }`**,
      **`terraform_data { store }`**, `action_trigger` `on_failure` = `halt`/`taint`/`continue`,
      `before_destroy`/`after_destroy` events, **Mermaid `terraform graph`**, `console -scope`,
      JSON output for `state show`/`workspace list`, nested blocks as computed provider values,
      **provider planned private data persisted across plan and apply**, Linux s390x builds,
      `contains()` null support, `bastion_host_key` now correctly applied. `[NUM]` `[RESEARCH]`
3.13.22 **1.16.1** (2 Sep 2026) — CLI no longer hangs after a run-task failure with pending policy
      evaluations; `import` blocks with `count`/`for_each` fixed; sensitive import identity fixed;
      dynamic module source fixes. `[NUM]` `[RESEARCH]`
3.13.23 **1.17.0-alpha** — deferred actions, batch-mode default changes, removal of several
      table/field override options. Status: **alpha, do not quote as current**. `[RESEARCH]`
3.13.24 **OpenTofu 1.6** (Jan 2024) — the fork, at parity with Terraform 1.5.x.
3.13.25 **OpenTofu 1.7** — **state and plan encryption**, `removed` blocks, provider-defined
      functions. `[RESEARCH]`
3.13.26 **OpenTofu 1.8** — **early variable/locals evaluation** for backends, module sources and
      encryption; provider mocking; `override_resource`/`override_data`/`override_module`;
      **`.tofu` file extensions**; compact state encoding; `TF_STATE_PERSIST_INTERVAL`;
      `use_legacy_workflow` removed from the S3 backend. `[RESEARCH]`
3.13.27 **OpenTofu 1.9** — **provider `for_each`**, **`-exclude`**, `encrypted_metadata_alias`,
      multi-line `tofu console`, `-show-sensitive`, large-graph performance work. `[RESEARCH]`
3.13.28 **OpenTofu 1.10** — **OCI registries for providers *and* modules**, native S3 locking,
      **experimental OpenTelemetry tracing**, `-target-file`/`-exclude-file`, **global provider
      cache lock**, experimental variable/output deprecation, **cross-type `moved`**, external
      key providers, negative `element()` indices, `decode_tfvars`/`encode_tfvars`/`encode_expr`,
      `-concise`. `[RESEARCH]`
3.13.29 **OpenTofu 1.11** — **ephemeral values and resources**, `azure_vault` key provider,
      `azurerm` backend `use_cli`/`use_aks_workload_identity`. `[RESEARCH]`
3.13.30 **OpenTofu 1.12** — dynamic `prevent_destroy`, `zh:`+`h1:` checksums at `init`,
      `-json-into=FILENAME`, **`destroy = false`**, concurrent provider installation; WinRM
      deprecated; 32-bit deprecation warnings planned. `[RESEARCH]`
3.13.31 **OpenTofu 1.13.0-beta1** — experimental **Symbol Libraries** (reusable functions and
      types — the first real answer to "no user-defined functions"), experimental `-lint`,
      `convert()`, Windows ARM64, Unicode 17, encryption providers gaining additional
      authenticated data, `cidrsubnets` IPv6 prefix extension, repository-scoped OCI tokens,
      **WinRM removed**, 32-bit support ending. `[RESEARCH]`
3.13.32 **The two "what version am I on" tells** in an interview: whether the candidate reaches
      for DynamoDB locking, and whether they know secrets can stay out of state. `[PROVE]`

## §3.14 The failure catalogue

3.14.1 A **consolidated 30-row table**: symptom → cause → where to look → fix, covering every
      failure named anywhere in this file. The single most re-read artifact in the bible.
      `[TABLE]` `[DIAG]`
3.14.2 **State lost or deleted** — symptom: plan proposes creating everything. Cause: state
      deleted, backend re-`init`-ed with `-reconfigure`, or wrong `key`. Fix: restore from the
      backend's versioning; never apply. `[INCIDENT]` `[SURGERY]`
3.14.3 **Wrong state applied to the wrong environment** — symptom: prod plan proposes destroying
      prod. Cause: `-backend-config` key mistake or workspace mis-selection. Fix:
      `allowed_account_ids`, per-environment credentials, directory-per-environment.
      `[INCIDENT]` `[PROVE]`
3.14.4 **Stuck lock** — symptom: `Error acquiring the state lock`. Read `LockInfo`, verify the
      holder is dead, `force-unlock` with the exact ID. `[DIAG]` `[SURGERY]`
3.14.5 **Two writers / lost update** — the §3.9.8 corruption, with recovery via versioning plus
      `import` of the orphaned objects. `[INCIDENT]` `[SURGERY]`
3.14.6 **Stale plan applied** — symptom: apply fails with a conflict, or succeeds and undoes
      someone's change. Fix: saved plans, pipeline concurrency groups. `[INCIDENT]`
3.14.7 **Resource exists but not in state** (create-then-crash, or a partially failed apply) —
      symptom: `AlreadyExists`/`EntityAlreadyExists` on create. Fix: `import`. `[DIAG]`
      `[SURGERY]`
3.14.8 **Resource in state but not in reality** — symptom: plan proposes create after a console
      deletion, or `state rm` was used. Normal path: apply. `[DIAG]`
3.14.9 **`for_each` unknown at plan time** — §3.4.4. `[DIAG]`
3.14.10 **Cycle** — §3.3.12. `[DIAG]`
3.14.11 **`create_before_destroy` propagation error** — §3.3.8. `[DIAG]`
3.14.12 **Provider produced inconsistent result after apply** — a provider bug; workarounds are
      pinning and `ignore_changes`; the real fix is an upstream issue. `[DIAG]` `[TRAP]`
3.14.13 **Provider version bump changed replacement behaviour** — the current guide's best trap.
      Detection: read the provider changelog, and diff `providers schema -json` between versions.
      `[PROVE]` `[VERSION-TRAP]`
3.14.14 **Lock-file checksum mismatch in CI** — §1.12.5. `[DIAG]`
3.14.15 **`Error: Invalid provider configuration` / credentials not found** — the provider chain,
      not Terraform; the debugging order (`sts get-caller-identity`, `AWS_PROFILE`,
      `assume_role`, the backend's separate credentials). `[DIAG]` `[X-REF 18]`
3.14.16 **Perpetual diff** — §2.10.8. `[DIAG]`
3.14.17 **`Objects have changed outside of Terraform`** followed by an unexpected revert — the
      `ignore_changes` decision point. `[DIAG]`
3.14.18 **Timeout during create on a stateful resource** — §3.5.13, with the RDS case worked and
      the recovery (wait, refresh, import, or delete-and-retry) chosen by evidence. `[INCIDENT]`
      `[SURGERY]`
3.14.19 **Rate limiting mid-apply** — symptom: `RequestLimitExceeded`, a half-applied plan. Fix:
      lower `-parallelism`, raise `max_retries`, split the state. `[DIAG]` `[X-REF 18]`
3.14.20 **`destroy` fails** — deletion protection, `prevent_destroy`, a non-empty bucket, an ENI
      still attached, a dependency outside Terraform. The generic remedy order. `[TABLE]`
      `[DIAG]`
3.14.21 **`-target` left the state inconsistent** — symptom: the next full plan proposes
      surprising changes. Fix: run a full plan/apply and read it carefully. `[TRAP]`
3.14.22 **A module upgrade destroyed everything** — cause: the module renamed resource addresses
      without `moved` blocks. Fix: pin, read the changelog, and demand `moved` blocks in module
      review. `[INCIDENT]` `[PROVE]`
3.14.23 **Secret in a public plan comment** — §2.15.12. `[INCIDENT]`
3.14.24 **State grew until plans timed out** — §2.18. `[INCIDENT]`
3.14.25 **The `FundsLedger` near-miss**, as the domain-specific worst case: a `for_each` key
      change on the ledger's parameter group cascades to a `replace_triggered_by` on the
      instance; the plan says `-/+`; `prevent_destroy` turns it into an error instead of 1.3 TB
      of lost ledger. The controls that caught it, in order: `prevent_destroy`, the
      blast-radius policy, and the second reviewer. `[INCIDENT]` `[PROVE]`

## §3.15 The proofs and the arithmetic

3.15.1 **`count` re-indexing** costs N−k replacements for a removal at index k. Proved in
      §2.2.2; restated here as the general form. `[PROVE]`
3.15.2 **Plan time is O(resources in state)**, not O(diff), because refresh touches every
      instance. Therefore splitting state is the only asymptotic fix. `[PROVE]`
3.15.3 **Apply duration is bounded below by the critical path**, so parallelism buys nothing on a
      chain. Worked with the 5-node QuizStakes network chain. `[PROVE]` `[NUM]`
3.15.4 **The lock throughput ceiling**: `max applies/day = 86400 / mean_apply_seconds`, computed
      for a 6-minute apply (240/day) and then divided by the number of teams contending.
      `[PROVE]` `[NUM]`
3.15.5 **State-transfer cost**: bytes per resource × resources × operations per day, computed for
      QuizStakes' 2,000-resource estate and 500 daily operations. `[PROVE]` `[COST]`
3.15.6 **Why `~>` on a provider is a range, not a pin**, and the probability arithmetic of an
      unreviewed provider minor bump across 25 states over a quarter. `[PROVE]` `[NUM]`
3.15.7 **Why the lock is necessary but insufficient**: mutual exclusion prevents concurrent
      *writes* but not stale *plans*. The two-phase argument. `[PROVE]`
3.15.8 **Why there is no rollback**, derived: an apply is a sequence of non-transactional remote
      operations with no compensating actions defined, so the only recovery is forward.
      Compare with the saga/compensation argument in the domain (`DEP-301 → DEP-400`).
      `[PROVE]` `[X-REF 22]`
3.15.9 **Why state cannot be reconstructed from reality** in general: the mapping is
      many-to-many without identity, and provider `import` support is partial. Where it *can*
      (resources with natural unique names) and where it cannot (auto-named, index-addressed).
      `[PROVE]`
3.15.10 **Why `for_each` keys must be plan-time-known**, derived from graph construction order.
      `[PROVE]`
3.15.11 **Why a provider, not Core, decides replacement** — derived from the fact that Core has
      no API knowledge. `[PROVE]`
3.15.12 **The blast-radius arithmetic** for state splitting: with one state, a worst-case bad
      apply can touch all 2,000 resources; with the six-layer split, the worst case is bounded by
      the largest layer. Compute both. `[PROVE]` `[NUM]`
3.15.13 **Drift-detection cost vs value**: the runner-minute cost from §2.17.6 against the
      expected cost of an undetected security-group change on the money path. `[COST]` `[PROVE]`
3.15.14 **The `-refresh=false` risk calculation**: probability of drift per day × cost of
      applying against a stale snapshot, versus the minutes saved per plan. State when it is
      rational. `[PROVE]` `[COST]`

---

# PART 4 — BUILD IT

Every item here ships a **complete, runnable artifact** — compiling Java 21, complete HCL,
complete Go for the provider items, complete Rego, complete pipeline YAML — and is followed by a
**Diff vs the real one** table covering what the production implementation does that this does
not, why it bothers, and what breaks first at scale. Terraform itself is Go, so the two
provider-side items are Go by necessity; everything a Java engineer would realistically own
(plan analysis, state analysis, policy, the CI harness) is Java 21.

4.1 **`TerraformGraph`** — a Java 21 implementation of Terraform's graph: build vertices from a
    resource set, add explicit and reference-derived edges, **detect cycles** with the exact
    error text shape Terraform uses, perform **transitive reduction**, produce the
    **destroy-order reversal**, and walk it with a bounded executor at
    `parallelism = 10` recording the critical path. Then run QuizStakes' network→ledger→service
    chain through it and print the schedule. `[BUILD]` `[PROVE]` `[X-REF 01]`
4.1.1 Diff vs Terraform's `internal/dag` and its transformer pipeline: meta-nodes for `count`,
    provider nodes, module expansion, orphan nodes sourced from state,
    `create_before_destroy` propagation, `-target` pruning, and the fact that Terraform's walk
    is per-node-type polymorphic rather than uniform. `[TABLE]`

4.2 **`PlanDiffEngine`** — a Java 21 diff engine over a minimal schema model
    (`record AttributeSchema(String name, boolean required, boolean optional, boolean computed,
    boolean sensitive, boolean forcesReplacement)`): given prior state, configuration and a
    schema, produce a change with the correct `actions` array, `after_unknown`,
    `before_sensitive`/`after_sensitive` and `replace_paths`. Reproduce the
    `Optional+Computed` behaviour from §3.6.8 exactly. `[BUILD]` `[PROVE]`
4.2.1 Diff vs the real split between Core and provider: who computes `ProposedNewState`, what
    `PlanResourceChange` may change, the consistency rules Core enforces afterwards, plan
    modifiers, `UseStateForUnknown`, and cty unknown *refinements*. `[TABLE]`

4.3 **`StateFileDecoder`** — a Java 21 reader for a `version = 4` state file using
    `java.util.jdk.internal`-free plain Jackson: records for `TerraformState`,
    `StateResource`, `StateInstance`; validation of `version`, `serial` and `lineage`; a
    `findByAddress(String)` that parses the full address grammar
    (`module.money["prod"].module.service_runtime.aws_ecs_service.this["FundsLedger"]`); and a
    **secret scanner** that reports every attribute path whose name matches a credential pattern
    or which appears in `sensitive_attributes`. Run it against the QuizStakes ledger state and
    print the report. `[BUILD]` `[DIAG]` `[X-REF 13]`
4.3.1 Diff vs `terraform show -json` and the `states` package: schema-version upgrades,
    provider-address normalisation, the documented instability of the on-disk format, and why
    real tooling must read the CLI's JSON rather than the file. `[TABLE]`

4.4 **`PlanJsonAnalyser`** — a Java 21 tool that reads `terraform show -json tfplan` and
    enforces the QuizStakes policy set from §2.14.11 without OPA: parse `resource_changes`,
    classify each by `actions` and `action_reason`, compute a **blast-radius score** (weighted:
    stateful delete = 100, delete = 20, replace = 10, update = 1, create = 1), fail the build
    above a threshold, and emit a Markdown summary suitable for a PR comment. Includes the
    `applyable`/`complete`/`errored` handling. `[BUILD]` `[PROVE]` `[COST]`
4.4.1 Diff vs Sentinel and OPA: the `tfplan/v2`/`tfconfig/v2`/`tfstate/v2` import surface,
    enforcement levels, policy testing with mocks, rule composition, and the fact that neither
    can see values that are unknown at plan time. `[TABLE]`

4.5 **`quizstakes-service-runtime`** — a complete, valid Terraform module: `versions.tf`,
    `variables.tf` (with `validation` on `heap_size_gb` against the Appendix B.1 set, and
    `optional()` object inputs), `main.tf` (task definition, service, target group, log group,
    two IAM roles, autoscaling), `outputs.tf` (typed, with a `precondition`), a `lifecycle`
    block per resource justified in a comment, `moved` blocks for the last address change, and a
    `README.md` generated by `terraform-docs`. Instantiated with `for_each` over the 25 services.
    `[BUILD]` `[HCL]` `[NUM]`
4.5.1 Diff vs `terraform-aws-modules/ecs`: IPv6, capacity providers, Service Connect, blue/green
    deployment controllers, EFS volumes, the deployment circuit breaker, the sheer number of
    optional inputs, and the maintenance cost that buys. `[TABLE]` `[X-REF 18]`

4.6 **`service-runtime.tftest.hcl`** — the complete test suite for 4.5: a `mock_provider "aws"`
    with `*.tfmock.hcl` data, plan-only `run` blocks asserting the name prefix, the tag set, the
    autoscaling bounds per service, and that `FundsLedger` cannot be given `min_instances = 0`;
    `expect_failures` for each `validation`; one `apply`-mode run against a sandbox behind a
    variable; a **`moved`-block regression run** proving a zero-change plan after upgrade; and
    `-junit-xml` wiring. `[BUILD]` `[X-REF 16]`
4.6.1 Diff vs Terratest: real assertions against the running service, retries with backoff,
    `terraform.Options`, stage-based tests, and the cost/latency comparison per test run.
    `[TABLE]` `[COST]`

4.7 **`quizstakes-policy/`** — a complete Rego policy bundle plus `conftest` invocation
    implementing the §2.14.11 rule set: `deny` rules for unencrypted storage, `0.0.0.0/0`
    ingress outside the gateway, PSP egress from any service but `CardPayments`, missing
    mandatory tags, and any `aws_db_instance` delete; a `warn` rule for cost; unit tests for
    every rule with fixture plan JSON. `[BUILD]` `[SOURCE]`
4.7.1 Diff vs the same rules in Sentinel and in Checkov: language, testability, where each runs
    in the pipeline, what each can see, and why you would deliberately implement one rule in two
    of them. `[TABLE]`

4.8 **`minimal-provider`** — a complete Go provider on **terraform-plugin-framework** exposing
    one resource (`quizstakes_restriction`, with `client_id`, `type`, `source`, `reason`,
    `expires_at`, and a **composite identity** of `type` + `source` per scenario §9.3), one data
    source, one **provider-defined function**
    (`provider::quizstakes::status_phase("AA-610") → 6`), one **ephemeral resource** returning a
    short-lived vendor token, and one **write-only argument**. Includes `Schema`, CRUD,
    `ImportState`, a `RequiresReplace` plan modifier on `type`, `UseStateForUnknown` on the
    computed id, an `UpgradeState` implementation, `main.go` with `providerserver.Serve`, and
    acceptance tests with a `PlanOnly` step. Plus the `dev_overrides` block to run it locally.
    `[BUILD]` `[SOURCE]` `[PROVE]`
4.8.1 Diff vs the AWS provider: 1,400 resources, code generation from the AWS API model,
    SDKv2/framework muxing, retry and rate-limit handling, per-resource `timeouts`, sweepers in
    acceptance tests, `default_tags` plumbing, and the schema-size cost from §3.7.16. `[TABLE]`

4.9 **`StateLockSimulator`** — a Java 21 harness that reproduces the §3.9.8 lost-update
    corruption: an in-memory `ConditionalObjectStore` with compare-and-set semantics standing in
    for S3's `If-None-Match`, two `Runner` threads performing read-state → plan → write-state,
    a mode switch for *locking off*, *locking on*, and *locking on with a `force-unlock` race*,
    and assertions showing exactly which resource is lost in each mode. Then the same harness
    with a **lease** (Azure-style) and with a **fencing token**, proving what each adds.
    `[BUILD]` `[PROVE]` `[X-REF 09]` `[X-REF 22]`
4.9.1 Diff vs the real S3/DynamoDB/blob-lease implementations: `LockInfo` contents, retry and
    `-lock-timeout` behaviour, the absence of TTLs, `force-unlock`'s nonce requirement, and
    HCP's run queue as an alternative model. `[TABLE]`

4.10 **`DriftDetector`** — a Java 21 scheduled component that runs
    `terraform plan -detailed-exitcode -refresh-only -json` per state via `ProcessBuilder`,
    parses the ndjson event stream, extracts the drifted resources and attributes, emits
    Micrometer counters (`terraform.drift.resources`, tagged by state and resource type), and
    raises one alert per *new* drift rather than one per run. Includes the exit-code contract
    and a timeout. `[BUILD]` `[CLI]` `[X-REF 20]`
4.10.1 Diff vs HCP Terraform's drift detection and `driftctl`: continuous scheduling, shadow-
    infrastructure discovery (which Terraform cannot do at all), historical trends, and
    per-workspace notification routing. `[TABLE]`

4.11 **`quizstakes-bootstrap`** — the complete zero-to-one HCL: the state bucket with versioning,
    SSE-KMS, Block Public Access and a TLS-only policy; the GitHub OIDC provider; a read-only
    `terraform-plan` role and a write `terraform-apply` role with `sub` conditions per
    environment; and the documented three-step procedure for the chicken-and-egg (local state →
    apply → migrate state into the bucket it just created → verify). `[BUILD]` `[HCL]`
    `[SURGERY]` `[X-REF 18]`
4.11.1 Diff vs Control Tower / Landing Zone Accelerator and vs HCP-hosted state: what the managed
    versions add (SCPs, account vending, audit aggregation) and what you keep owning. `[TABLE]`

4.12 **`.github/workflows/terraform.yml`** — the complete pipeline implementing §2.16: matrix
    over the six layers, `fmt -check`, `init -backend=false` + `validate`, tflint + trivy,
    OIDC assume-role, `init -lockfile=readonly`, `plan -out` with `-detailed-exitcode`, plan
    JSON → `PlanJsonAnalyser` (4.4) → PR comment, artifact encryption, a `concurrency` group per
    state, environment protection for the apply, and `apply tfplan` consuming the saved artifact.
    `[BUILD]` `[CFG]` `[X-REF 17]`
4.12.1 Diff vs HCP Terraform's run pipeline: run tasks, policy sets, cost estimation, the queue,
    the audit trail, agents for private networking, and the RUM cost comparison from §2.21.12.
    `[TABLE]` `[COST]`

4.13 **`import-campaign`** — the complete artifact set for adopting a hand-built environment:
    a `*.tfquery.hcl` `list` block plus the `terraform query` invocation to enumerate candidates,
    a `for_each` `import` block driven by a map produced from that output, the
    `plan -generate-config-out` step, a Java 21 `GeneratedConfigPruner` that strips read-only
    attributes and provider defaults from the generated HCL, and the **zero-changes gate** as a
    CI check. `[BUILD]` `[CLI]` `[RESEARCH]`
4.13.1 Diff vs Terraform Search (HCP beta) and vs `terraformer`: discovery breadth, config
    generation quality, provider coverage, and the honest statement of what still needs a human.
    `[TABLE]`

4.14 **`state-surgery-runbook.md`** — the complete, executable runbook for the six operations
    that appear in incidents: restore state from a bucket version; split one state into two;
    move a resource into a module; adopt an orphan by `import`; disown a resource with `removed`;
    and recover from a lost-update corruption. Each with the backup step, the "is this safe"
    test, the verification (`plan` must be empty), and the rollback. `[BUILD]` `[SURGERY]`
    `[FLOW]`
4.14.1 Diff vs the imperative equivalents (`state mv`, `state rm`, `state push -force`): why the
    declarative blocks are preferred, and the two cases where only the imperative command works.
    `[TABLE]`

4.15 **`EphemeralSecretPath`** — the complete HCL proving §2.11.17: an `ephemeral "aws_secretsmanager_secret_version"`
    read of the PSP credential, passed to a write-only argument, with the paired `*_wo_version`
    trigger; plus a Java 21 `StateSecretAudit` test that applies the configuration in a sandbox,
    pulls the state, and **asserts that the secret string appears nowhere in it** — the test that
    turns a claim into a guarantee. `[BUILD]` `[PROVE]` `[X-REF 13]`
4.15.1 Diff vs `random_password` + Secrets Manager and vs `manage_master_user_password`: what
    lands in state in each case, what rotation does, and which of the three satisfies Appendix
    B.4. `[TABLE]`

4.16 **`InfracostGate`** — a Java 21 wrapper that runs `infracost diff --format json` against the
    plan, extracts the monthly delta, applies the QuizStakes thresholds (auto-approve under
    $200/month, second approver above, fail above $2,000), and comments the breakdown. Includes
    an `infracost-usage.yml` for the document-upload egress and ledger IOPS that Infracost cannot
    infer. `[BUILD]` `[COST]` `[NUM]`
4.16.1 Diff vs the Cloudability run task in HCP and vs AWS Cost Explorer forecasting: pre- vs
    post-facto, resource-level vs account-level, and what none of them price. `[TABLE]`

# PART 5 — INTERVIEW & RETENTION

## §5.1 The questions, with the answer shape

5.1.1 *"What is Terraform state and why can't you just query the cloud?"* — the binding argument
      (§1.17.2), the dependency-edge argument, and the one-sentence close. `[PROVE]`
5.1.2 *"Walk me through what `terraform plan` does."* — the six steps with the RPCs named
      (§1.19.2). The tell: candidates who say "it compares config to cloud" have skipped state.
5.1.3 *"What happens if the state file is deleted?"* — restore from versioning; never apply;
      and the enumeration of what a blind re-apply does (destroy running infrastructure, fail on
      taken names, orphan resources). Carries the current guide's list forward. `[PROVE]`
5.1.4 *"How does Terraform decide to replace instead of update?"* — the provider decides, in
      `PlanResourceChange`, via `ForceNew`/`RequiresReplace`, and a provider bump can change it.
      `[PROVE]`
5.1.5 *"`count` or `for_each`?"* — the reordering proof, worked out loud. This is the question
      most likely to be asked and most likely to be answered shallowly. `[PROVE]`
5.1.6 *"How do you keep secrets out of state?"* — ephemeral values, write-only arguments,
      provider-managed passwords, and the honest residual. Naming only `sensitive = true` fails
      this question. `[PROVE]`
5.1.7 *"How do you stop two people applying at once?"* — locking, and then the harder half:
      locking does not stop stale plans, so you need saved plans plus pipeline concurrency.
      `[PROVE]`
5.1.8 *"A resource exists in AWS but not in state. What do you do?"* — `import` block,
      `-generate-config-out`, prune, plan to zero, apply, delete the block.
5.1.9 *"You need to rename a resource. How?"* — `moved` block, not `state mv`, and why.
5.1.10 *"How do you stop managing something without deleting it?"* — `removed` block with
      `destroy = false`, or `lifecycle { destroy = false }` in 1.16+.
5.1.11 *"How do you structure Terraform for dev/staging/prod?"* — directory per environment,
      layered states, versioned modules, promotion; and the explicit rejection of workspaces
      with HashiCorp's own reasoning.
5.1.12 *"What is drift and what do you do about it?"* — the four responses table, and the IAM
      answer as the only real fix.
5.1.13 *"When would you use `ignore_changes`?"* — ownership transfer, named other owner, never
      `all`.
5.1.14 *"What's in the plan file, and can I commit it?"* — binary, self-contained, contains
      secrets, short-lived, encrypted. No.
5.1.15 *"How do you test Terraform?"* — the pyramid, `terraform test` with mocks for logic,
      apply-based tests on a schedule, policy as the cheap layer, and what none of it proves.
5.1.16 *"Terraform or OpenTofu?"* — the licence facts, the divergence table, and a decision
      procedure rather than an opinion.
5.1.17 *"Why is my plan slow?"* — refresh is O(state); split the state; `-refresh=false`;
      parallelism; data-source count.
5.1.18 *"What does `-target` do and when is it acceptable?"* — prunes to the target and its
      dependencies, leaves state knowingly inconsistent, emergency use only.
5.1.19 *"Why does my plan always show a change?"* — the perpetual-diff catalogue, diagnosed in
      order.
5.1.20 *"How do modules pass providers?"* — implicit inheritance, the `providers` map,
      `configuration_aliases`, and why a module must not contain a `provider` block.
5.1.21 *"What is the dependency lock file for, and do you commit it?"* — yes; `h1:` vs `zh:`; the
      multi-platform failure.
5.1.22 *"How does Terraform talk to providers?"* — go-plugin, gRPC, protocol 5/6, the RPC list.
5.1.23 *"Explain unknown values."* — `(known after apply)`, propagation, and why `for_each`
      cannot be unknown.
5.1.24 *"How would you adopt 400 hand-built resources?"* — the import campaign, with an honest
      timeline.
5.1.25 *"Design the IaC setup for this estate."* — the [STAFF]-shaped answer: account topology,
      state layering by blast radius, module estate, pipeline with OIDC and policy gates, secret
      strategy, drift detection, and the two-actor rule on production applies. Judged on
      *ordering* and *what you refuse to do*. `[PROVE]`
5.1.26 *"What would you do differently at 10× the resource count?"* — Stacks or a state-per-
      service split, generated roots, a provider mirror, and a platform team owning the modules.
5.1.27 *"What does Terraform not guarantee?"* — no atomicity, no rollback, no continuous
      reconciliation, no protection from a second actor. The answer that separates senior from
      mid.
5.1.28 *"How do you review a plan?"* — the symbol legend, `# forces replacement`, the change
      summary, the drift block, and the blast-radius question.
5.1.29 *"When would you not use Terraform?"* — §2.24.2.
5.1.30 *"What is a provider, in one sentence, and who wrote the AWS one?"* — the tell for whether
      someone has ever read provider source.

## §5.2 The consolidated trap list

5.2.1 Every `**Trap:**` in the bible, collected as a numbered list of *wrong belief → symptom →
      fix*, ~70 entries. The pre-interview read. `[TABLE]`
5.2.2 The ten that appear most often, called out: `sensitive` ≠ encrypted; state is not a cache;
      `count` re-indexes; `for_each` keys must be known; `-target` leaves state inconsistent;
      `ignore_changes` still records drift in state; the provider decides replacement; the lock
      does not prevent stale plans; the plan file holds secrets; and workspaces are not
      environments. `[TABLE]`
5.2.3 The five **stale answers** that date a candidate: DynamoDB for locking, `terraform import`
      the command, `terraform taint`, "everything ends up in state", and "Terraform is open
      source". `[VERSION-TRAP]`
5.2.4 The three claims in the **current guide** that the write pass must correct: the DynamoDB
      TTL claim (§3.9.5), the implication that `terraform destroy` is the way to stop managing a
      resource (§2.9.7 is), and the five-step plan description that omits the provider RPCs
      (§1.19.2). `[PROVE]`

## §5.3 The cheat sheets

5.3.1 **The constants sheet**: `-parallelism` default **10**; `max_retries` default **5** on the
      S3 backend; `workspace_key_prefix` default **`env:`**; `use_lockfile` default **false**;
      PBKDF2 **600,000** iterations and a **16-character** minimum passphrase; AES-GCM keys of
      **16/24/32** bytes; plan JSON `format_version` **"1.0"**; state `version` **4**; protocol
      **5** (CLI ≥ 0.12) and **6** (CLI ≥ 1.0); `-detailed-exitcode` **0/1/2**; Stacks limits
      **500 deployments / 100 components**. `[TABLE]` `[NUM]`
5.3.2 **The version sheet**: feature → minimum version, for every feature named in the file.
      `[TABLE]`
5.3.3 **The address-grammar sheet**: every form of resource address, with an example of each in
      `-target`, `moved`, `import`, `removed` and state. `[TABLE]`
5.3.4 **The plan-symbol sheet**: `+`, `~`, `-`, `-/+`, `+/-`, `<=`, `#forces replacement`,
      `(known after apply)`, `(sensitive value)`. `[TABLE]`
5.3.5 **The decision sheet**: `count` vs `for_each`; workspace vs directory vs Stack;
      `terraform_remote_state` vs data source vs parameter store; `precondition` vs `check` vs
      policy vs test; ephemeral vs `sensitive` vs provider-managed secret; Terraform vs OpenTofu.
      `[TABLE]`
5.3.6 **The command sheet**: the 15 invocations worth having in muscle memory, including the
      three `[SURGERY]` ones and their backup step. `[TABLE]` `[CLI]`
5.3.7 **The debugging tree**: symptom → first command → second command → likely cause, for the
      ten most common failures. `[TABLE]` `[DIAG]`
5.3.8 **The QuizStakes reference layout**: the account map, the six state layers, the module
      estate, and the pipeline gates, on one page. `[TABLE]`

## §5.4 The verbal answers

5.4.1 **State in one sentence.** *"State is the binding between the addresses in my configuration
      and the real objects in the cloud, plus a snapshot for diffing and the dependency edges
      needed to destroy things correctly — which is why it is the authority, not a cache."*
5.4.2 **Plan in one sentence.** *"It loads configuration, reads state, refreshes every managed
      instance through the provider, builds a dependency graph, asks each provider what it would
      do, and prints the delta."*
5.4.3 **Replacement in one sentence.** *"The provider's schema marks the attribute as
      replacement-forcing, so the provider — not Terraform — decides, which is why a provider
      upgrade can turn an in-place update into downtime."*
5.4.4 **`for_each` in one sentence.** *"`count` binds objects to positions and `for_each` binds
      them to keys, so reordering a list re-binds every later object and plans a replacement."*
5.4.5 **Secrets in one sentence.** *"`sensitive` only redacts output; keeping a secret out of
      state needs an ephemeral value into a write-only argument, or a provider that manages the
      secret so Terraform never sees it."*
5.4.6 **Locking in one sentence.** *"The lock gives mutual exclusion on the state write; it does
      nothing about a plan that went stale while it waited, which is why the pipeline must apply
      a saved plan and serialise runs itself."*
5.4.7 **The tool in one sentence.** *"A graph engine, a diff engine, a plugin protocol and a JSON
      file that remembers what it did."*

## §5.5 Retention

5.5.1 The **spaced-repetition set**: the 45 facts most likely to be asked and most likely to be
      forgotten, phrased as questions. `[TABLE]`
5.5.2 The **self-quiz procedure**: read only the atomic concept checklist; if you cannot state the
      mechanism in one sentence, return to that section.
5.5.3 The **hands-on exercises** that make each part stick: delete a state file in a sandbox and
      recover it from a bucket version; force a lock and read the `LockInfo`; corrupt a state
      deliberately with two concurrent `-lock=false` applies and find the lost resource;
      re-index a `count` list and read the plan; convert it to `for_each` with `moved` blocks and
      prove a zero-change plan; import a hand-made bucket; write a provider with one resource and
      watch `TF_LOG=TRACE` carry the gRPC calls; put a password through a write-only argument and
      grep the state for it; and run the same configuration under `tofu`. `[TABLE]`
5.5.4 The **checklist before an interview**: which CLI version, which provider version, whether
      the estate is Terraform or OpenTofu, and which of the twenty-two version deltas you can
      state correctly. `[TABLE]`

---

## Sources consulted

| Source | URL | What it contributed |
|---|---|---|
| Terraform release index (September 2026) | https://releases.sh/hashicorp/terraform | The baseline: **1.16.1 on 2 Sep 2026**, 1.16.0 on 26 Aug 2026, and the 1.17.0-alpha20260827 pre-release with deferred actions — the fact that established the target version for the whole file |
| Terraform CHANGELOG, v1.16 branch | https://raw.githubusercontent.com/hashicorp/terraform/v1.16/CHANGELOG.md | Every 1.16.0 feature in §3.13.21: `import` blocks in modules, `lifecycle { destroy = false }`, `terraform_data`'s `store` block, `action_trigger` `on_failure` = halt/taint/continue, `before_destroy`/`after_destroy` events, Mermaid `terraform graph`, `console -scope`, JSON output for `state show`/`workspace list`, nested blocks as computed provider values, provider planned private data persisted across plan and apply, Linux s390x, `contains()` null support, `bastion_host_key`; plus the 1.16.1 bug-fix list |
| Terraform CHANGELOG, v1.15 branch | https://raw.githubusercontent.com/hashicorp/terraform/v1.15/CHANGELOG.md | Windows ARM64 builds, **`deprecated` on `variable` and `output`**, S3 backend `aws login`, **backend-block validation in `validate`**, `convert()`, **dynamic module `source`/`version`**, **output type constraints**, and the strict-boolean change to `AWS_USE_FIPS_ENDPOINT`/`AWS_USE_DUALSTACK_ENDPOINT` |
| Terraform CHANGELOG, v1.14 branch | https://raw.githubusercontent.com/hashicorp/terraform/v1.14/CHANGELOG.md | **List resources in `*.tfquery.hcl`** and the **`terraform query`** command, the **Actions block** with `aws_lambda_invoke`/`aws_cloudfront_create_invalidation` examples and the `-invoke` flag, the **`GenerateResourceConfiguration` RPC**, deferred actions behind `-allow-deferral`, experimental `terraform test cleanup` with `skip_cleanup` and test `backend` blocks, the macOS Monterey/Go 1.25 requirement, and container-CPU-derived parallelism |
| Terraform CHANGELOG, v1.13 branch | https://raw.githubusercontent.com/hashicorp/terraform/v1.13/CHANGELOG.md | The **`terraform stacks` CLI command**, and the upgrade note that test files should declare `variable` blocks for external variables |
| Terraform CHANGELOG, v1.12 branch | https://raw.githubusercontent.com/hashicorp/terraform/v1.12/CHANGELOG.md | **1.12.0 dated 14 May 2025**, the **OCI object storage backend**, **`import` by `identity`** (mutually exclusive with `id`), and the Linux kernel ≥ 3.2 requirement |
| Terraform CHANGELOG, v1.11 branch | https://raw.githubusercontent.com/hashicorp/terraform/v1.11/CHANGELOG.md | **1.11.0 dated 27 Feb 2025**: write-only attributes, `-junit-xml` GA, **S3 native state locking GA via `use_lockfile`** with the DynamoDB arguments deprecated, and the new `azurerm` authentication properties (`use_cli`, `use_aks_workload_identity`, `client_id_file_path`, `client_certificate`, `client_secret_file_path`) |
| Terraform: ephemeral values in resources | https://developer.hashicorp.com/terraform/language/manage-sensitive-data/ephemeral | The `ephemeral` block syntax, the Open/Renew/Close lifecycle, where ephemeral values may and may not be used, and the `*_wo` write-only argument pairing |
| Terraform plugin framework: write-only arguments | https://developer.hashicorp.com/terraform/plugin/framework/resources/write-only-arguments | **Write-only arguments require v1.11+**; prior/planned/final state values *"should always be null"*; not supported on set attributes, set nested attributes or set nested blocks; values *"are not expected to be consistent between plan and apply"*; the provider as the terminal point for an ephemeral value |
| HashiCorp blog — Terraform 1.11 ephemeral values in managed resources | https://www.hashicorp.com/en/blog/terraform-1-11-ephemeral-values-managed-resources-write-only-arguments | The 1.10 → 1.11 progression from ephemeral resources to write-only arguments, and the `*_wo_version` trigger pattern |
| Terraform `lifecycle` meta-argument reference | https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle | The complete inventory: `action_trigger` with its six lifecycle events and `on_failure`, `create_before_destroy`, `prevent_destroy`, `ignore_changes`, `replace_triggered_by`, `precondition`, `postcondition`, and **`destroy = false`** for removal from state without destruction |
| Terraform `moved` block reference | https://developer.hashicorp.com/terraform/language/moved | The `from`/`to` arguments as required strings, and the exact plan-time sequence — find the object, rename it in state, plan at the new address — with the assurance *"Terraform does not destroy the resource during the Terraform run"* |
| Terraform import overview | https://developer.hashicorp.com/terraform/language/import | ID vs **identity** as the two ways a resource is uniquely named (S3 uses `account_id` + `bucket` + `region`), `plan -generate-config-out`, and the requirement that a destination `resource` block match the `import` block's address. Also confirmed **v1.16.x as the current documented version** |
| Terraform state overview | https://developer.hashicorp.com/terraform/language/state | The canonical definition — *"store bindings between objects in a remote system and resource instances declared in your configuration"* — plus the JSON format's documented instability, the instruction never to edit state directly, and the CLI as the stable interface |
| Terraform state locking | https://developer.hashicorp.com/terraform/language/state/locking | *"State locking happens automatically on all operations that could write state. You do not see any message that it happens."*, `-lock=false` and the advice against it, and `force-unlock`'s lock-ID nonce with the multiple-writers warning |
| Terraform S3 backend reference | https://developer.hashicorp.com/terraform/language/backend/s3 | The full argument list: required `bucket`/`key`/`region`, `use_lockfile` **default false**, `dynamodb_table` deprecated with *"will be removed in a future minor version"*, `workspace_key_prefix` **default `env:`**, `encrypt`/`kms_key_id`/`sse_customer_key`, `max_retries` **default 5**, `assume_role` and `assume_role_with_web_identity` sub-arguments, `acl`, `skip_credentials_validation` |
| Terraform CLI workspaces | https://developer.hashicorp.com/terraform/cli/workspaces | The definition, the `default` workspace, `terraform.tfstate.d` for local state, workspace-name appending for remote backends, the feature-branch use case, and HashiCorp's explicit guidance **against** workspaces for system decomposition and access isolation |
| Terraform dependency lock file | https://developer.hashicorp.com/terraform/language/files/dependency-lock | Location, the `version`/`constraints`/`hashes` structure, the **`zh:` (zip hash, registry-only) vs `h1:` (content hash, installation-method-agnostic)** distinction, opportunistic `h1:` addition, `terraform providers lock -platform=`, and `init -upgrade` semantics |
| Terraform `check` block reference | https://developer.hashicorp.com/terraform/language/checks | `check` runs *"as the last step of plan or apply"*, after preconditions and postconditions; `assert` with `condition` + `error_message`; scoped data sources; **failures are warnings and the operation continues**; requires **v1.5.0+** |
| Terraform tests | https://developer.hashicorp.com/terraform/language/tests | `*.tftest.hcl`/`*.tftest.json`; the `test`, `run`, `variables` and `provider` blocks; `command = apply` as the **default**; `plan_options` (`mode`, `refresh`, `replace`, `target`); `assert`, `expect_failures`, `state_key`, `parallel`; the `module` block accepting only `source`/`version`; the variable precedence order; **cleanup in reverse `run` order**; parallelism rules and the `parallel = false` barrier; framework available in **v1.6.0+** with **mocking from v1.7.0** |
| Terraform functions index | https://developer.hashicorp.com/terraform/language/functions | The ten function categories and their members, and the **`provider::<local-name>::function_name()`** call syntax for provider-defined functions |
| Terraform plugin framework: functions | https://developer.hashicorp.com/terraform/plugin/framework/functions | Provider-defined functions require **Terraform 1.8+**, the `Definition`/`Run` implementation shape, and the fact that functions can be added to an existing provider |
| Terraform plugin framework benefits | https://developer.hashicorp.com/terraform/plugin/framework-benefits | The framework-vs-SDKv2 comparison: SDKv2 *"maintained for Terraform 1.x"* with feature development stopped, `d.Get()` returning zero values so null and unknown are *"indistinguishable"*, the framework's typed request/response model, and **`terraform-plugin-mux`** for per-resource incremental migration |
| Terraform plugin protocol | https://developer.hashicorp.com/terraform/plugin/terraform-plugin-protocol | **Protocol 6 requires CLI 1.0+, protocol 5 requires CLI 0.12+**; protocol 6 added **nested attributes** via `SchemaAttribute.NestedType` and per-nested-attribute sensitivity; the canonical `tfplugin5.proto`/`tfplugin6.proto` in `docs/plugin-protocol/` |
| How Terraform works with plugins | https://developer.hashicorp.com/terraform/plugin/how-terraform-works | *"Terraform Plugins are written in Go and are executable binaries invoked by Terraform Core over RPC"*, and the `init`-time discovery/download/lock sequence |
| Terraform graph internals | https://developer.hashicorp.com/terraform/internals/graph | The three node types (resource, provider configuration, resource meta-node), the **nine construction steps** ending in cycle validation and a single root, *"Graph walking is done in parallel: a node is walked as soon as all of its dependencies are walked"*, and **`-parallelism` defaulting to 10 concurrent nodes** |
| Terraform JSON output format | https://developer.hashicorp.com/terraform/internals/json-format | `format_version` **"1.0"** since 1.1.0; the plan keys `prior_state`, `configuration`, `planned_values`, `proposed_unknown`, `resource_changes`, `output_changes`, `checks`, `applyable`, `complete`, `errored`; the complete `actions` array set including `["delete","create"]` vs `["create","delete"]`; and `before`/`after`/`after_unknown`/`before_sensitive`/`after_sensitive`/`replace_paths` |
| Terraform provisioners syntax | https://developer.hashicorp.com/terraform/language/resources/provisioners/syntax | *"we strongly recommend using purpose-built solutions to perform post-apply operations"*; the `file`/`local-exec`/`remote-exec` set; create-time failure marking the resource **tainted**; `when = destroy` requiring the provisioner to still be in the configuration; `on_failure = continue`; the `connection` block with SSH/WinRM and bastion support; `self`; and `terraform_data` as the alternative |
| Terraform provider configuration | https://developer.hashicorp.com/terraform/language/providers/configuration | `alias`, the default (unaliased) configuration and the implied empty default, the `provider` meta-argument, the `providers` map for child modules, **`configuration_aliases`** in `required_providers`, and the rule that child modules inherit default configurations but never `source`/`version` requirements |
| Terraform style guide | https://developer.hashicorp.com/terraform/language/style | The canonical file names (`backend.tf`, `main.tf`, `outputs.tf`, `providers.tf`, `terraform.tf`, `variables.tf`, `locals.tf`, `override.tf`), two-space indent and `=` alignment, resource naming as descriptive nouns without the type, the argument-ordering rule ending with `lifecycle` then `depends_on`, `./modules/<name>` for local modules, the `terraform-<PROVIDER>-<NAME>` registry naming, and the **`.gitignore` never/always lists including "always commit `.terraform.lock.hcl`"** |
| Terraform Stacks overview | https://developer.hashicorp.com/terraform/language/stacks | `component` blocks in **`tfcomponent.hcl`** referencing modules with `inputs`, `deployment` blocks in **`tfdeploy.hcl`**, per-deployment isolated state, deployment groups with auto-approve conditions, **HCP-only execution**, and the limits: **500 deployments, 100 components, one deployment per group** |
| HashiCorp blog — Terraform Stacks, explained | https://www.hashicorp.com/en/blog/terraform-stacks-explained | The problem statement (manual dependency management across isolated states, duplicated roots per environment/region/account), the component/deployment split, auto-approve checks such as "no deletions", and **deferred changes** producing a partial plan for the Kubernetes cluster-plus-workload case |
| HashiCorp blog — HashiConf 2025 Terraform and Packer features | https://www.hashicorp.com/en/blog/scale-infrastructure-with-new-terraform-and-packer-features-at-hashiconf-2025 | **Stacks GA** with a unified CLI and deployment groups, **Terraform Search public beta** for bulk discovery and import from AWS and Azure, **Terraform Actions public beta** including Ansible playbook triggering, **HYOK GA**, the Cloudability governance run task, the **350+ pre-written Sentinel policies for NIST SP 800-53 Rev 5 on AWS**, and the authenticated Terraform MCP Server |
| HCP Terraform policy enforcement | https://developer.hashicorp.com/terraform/cloud-docs/policy-enforcement | The three frameworks — **Terraform Policy (beta, native HCL)**, Sentinel, and OPA/Rego — the rule that a policy set contains only one framework's policies, policy checks against the plan during a run, and project/workspace-scoped application |
| Terraform Enterprise overview | https://developer.hashicorp.com/terraform/enterprise | *"a self-hosted instance of HCP Terraform with features like audit logging and SAML single sign-on"* and the statement that HCP Terraform and TFE are **different distributions of the same application** |
| CDK for Terraform overview | https://developer.hashicorp.com/terraform/cdktf | **CDKTF is deprecated — "HashiCorp no longer supports or maintains" it as of 10 December 2025**; the five supported languages (TypeScript, Python, Java, C#, Go); and the fact that it generates Terraform JSON configuration rather than replacing Terraform |
| Open Policy Agent — Terraform integration | https://www.openpolicyagent.org/docs/terraform | The `terraform plan --out tfplan.binary` → `terraform show -json` → `opa exec --decision terraform/analysis/authz --bundle policy/ tfplan.json` workflow, policies over `resource_changes[_].change.actions`, the published **blast-radius scoring** example, and the documented blind spots: computed attributes, dynamic block contents and unevaluated function results |
| OpenTofu releases | https://github.com/opentofu/opentofu/releases | **1.12.6 (19 Aug 2026) as the latest stable**, 1.11.14 as the final 1.11 patch, and **1.13.0-beta1 (27 Aug 2026)** with Symbol Libraries, experimental `-lint`, `convert()`, Windows ARM64, Unicode 17, encryption providers gaining additional authenticated data, IPv6 `cidrsubnets`, repository-scoped OCI tokens, **WinRM removed** and 32-bit support ending |
| OpenTofu "what's new" (current) | https://opentofu.org/docs/intro/whats-new/ | OpenTofu 1.12: **dynamic `prevent_destroy`**, `zh:`+`h1:` checksums written at `init`, `-json-into=FILENAME`, **`destroy = false`**, concurrent provider installation, WinRM deprecation and the 32-bit phase-out |
| OpenTofu 1.11 "what's new" | https://opentofu.org/docs/v1.11/intro/whats-new/ | Ephemeral values and resources *"that exist only in memory during a single OpenTofu phase"*, the **`azure_vault` key provider**, and the `azurerm` backend's `use_cli` (default true) and `use_aks_workload_identity` (default false) |
| OpenTofu 1.10 "what's new" | https://opentofu.org/docs/v1.10/intro/whats-new/ | **OCI registries for providers and modules**, **native S3 state locking via conditional writes**, experimental **OpenTelemetry tracing**, `-target-file`/`-exclude-file`, the **global provider cache lock**, experimental variable/output deprecation, enhanced `moved`/`removed` including **cross-type moves**, external key providers, negative `element()` indices, `decode_tfvars`/`encode_tfvars`/`encode_expr`, and `-concise` |
| OpenTofu 1.9 "what's new" | https://opentofu.org/docs/v1.9/intro/whats-new/ | **Provider iteration with `for_each`**, the **`-exclude` flag**, `encrypted_metadata_alias`, multi-line `tofu console`, `-show-sensitive`, and large-graph performance work |
| OpenTofu 1.8 "what's new" | https://opentofu.org/docs/v1.8/intro/whats-new/ | **Early variable/locals evaluation for backends, module sources and encryption configuration**; provider mocking in `tofu test`; `override_resource`/`override_data`/`override_module`; the **`.tofu`/`.tofu.json`/`.tofutest.hcl` extension family**; `use_legacy_workflow` removal from the S3 backend; compact JSON state encoding and **`TF_STATE_PERSIST_INTERVAL`** |
| OpenTofu state and plan encryption | https://opentofu.org/docs/language/state/encryption/ | The `encryption` block's key-provider + method + target structure; **PBKDF2 with a 16-character minimum passphrase and 600,000 default iterations**, SHA-256/512; `aws_kms`, `gcp_kms`, `azure_vault` (RSA-OAEP-256 / AES-GCM), `openbao` (16/32/64-byte keys) and experimental `external` providers; **AES-GCM requiring 16/24/32-byte keys** with key-saturation caveats; the `unencrypted` method; `fallback` for rollover and rollback; `encrypted_metadata_alias` instead of renaming; and the warnings that encryption does not protect against data loss or replay and that lost keys mean unrecoverable state |
| OpenTofu / IBM-HashiCorp licensing analysis (2026) | https://scalr.com/learning-center/update-regarding-licensing-changes-to-terraform and https://scalr.com/learning-center/what-is-opentofu | The **August 2023 MPL-2.0 → BUSL-1.1 change**, BUSL being non-OSI-approved and restricting competitive hosted use, the **IBM acquisition of HashiCorp for $6.4B closing 27 Feb 2025** with IBM now named as licensor, OpenTofu's fork within 30 days, its move to the **Linux Foundation** and **CNCF sandbox entry in April 2025 with an MPL-2.0 exception**, and adoption figures — all to be re-verified against the licence files and a first-party CNCF/Linux Foundation announcement before the write pass states them |
| Terraform interview-question and best-practice surveys | https://spacelift.io/blog/terraform-best-practices and https://spacelift.io/blog/terraform-test | Used purely as **completeness probes** against the leaf list: shared-backend locking, versioned modules, secret references not values, tagging strategy, `fmt`/`validate` automation, policy as code, loops and conditionals, dynamic blocks, lifecycle controls, variable validation, workspaces for lightweight separation, the tflint/tfenv/Checkov/Terratest tool set, per-environment configurations with independent state, community-module reuse, and infrastructure import — every one of which mapped to an existing leaf, with the tooling names feeding §1.20.6 |
| S3-native locking migration write-ups (2026) | https://developer.hashicorp.com/terraform/language/backend/s3 (primary) plus community migration guides | Confirmation of the migration shape — `use_lockfile = true` plus removal of `dynamodb_table`, with both configurable simultaneously during migration, and the `.tflock` object written beside the state — to be re-verified against the backend reference before the write pass states the object name |

**Searches that returned nothing usable.** No first-party page states the on-disk state
**format version** in current documentation — HashiCorp deliberately documents the format as
unstable and directs tooling to `terraform show -json` — so `version = 4` in §3.8.1 carries
`[RESEARCH]` and the write pass must confirm it by decoding a state file produced by 1.16.1
rather than citing a document. No canonical university syllabus or published curriculum for
"infrastructure as code" was located; the curriculum angle was covered instead by the
HashiCorp style guide, the module-structure documentation, and the best-practice surveys above.
No first-party page enumerates the internal graph **transformers** by name (§3.3.4); those are
sourced from the Terraform repository's `internal/terraform` package and must be verified
against the v1.16 source tree before the write pass names them. The web-search budget for the
session was exhausted after the first tranche of queries, so the version-history rows for
Terraform 1.6–1.10 (§3.13.11–§3.13.15) rest on recall plus the surrounding changelogs rather
than on a fetched changelog for each branch; the write pass must fetch
`https://raw.githubusercontent.com/hashicorp/terraform/v1.N/CHANGELOG.md` for N = 6, 7, 8, 9, 10
and correct any row that does not match. No published, named postmortem of a Terraform
state-corruption incident with a citable timeline was located, so every `[INCIDENT]` leaf is
framed as a reconstructed mechanism against the QuizStakes estate rather than attributed to a
real organisation.

---

## Gaps vs the current guide

`src/topics/23-terraform.md` is **171 lines across 5 sections plus a 10-item atomic concept
checklist** — the shortest guide in the set. **Every concept in it survives as a leaf.** The
table below is the work order.

| Syllabus area | Present in `src/topics/23-terraform.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why IaC exists | absent | **the entire origin section** — snowflakes, no review/reproducibility/audit, declarative vs imperative, idempotence, convergence vs congruence, config management vs provisioning, the Kubernetes reconciliation contrast, the honest costs, when not to use it | — |
| §1.2 licence and the fork | absent | **the entire subject** — BUSL-1.1, 1.5.5 as the last MPL release, the IBM acquisition, OpenTofu's governance, the drop-in claim and its limits, the full divergence table, the tool landscape (CloudFormation/CDK/Pulumi/Crossplane/Ansible/Terragrunt/Spacelift) | — |
| §1.3 the CLI surface | `init`, `plan`, `apply`, `force-unlock` named in prose | the command inventory; the deprecated commands; every flag table; `-detailed-exitcode`; `-reconfigure` vs `-migrate-state`; `show -json`; `console`; `graph`; `state` subcommands; `providers` subcommands; `test`/`query`/`stacks`; the whole `TF_*` environment surface; the CLI config file and `dev_overrides`; exit codes | `init` gets two sentences and is described only as "downloads plugins and initialises the backend" |
| §1.4 HCL2 syntax | absent (HCL appears only in two code fragments) | **the entire syntax layer** — the two-layer model, block inventory, the `terraform` block, version-constraint grammar including `~>` precisely, file-loading rules, override files, `.tofu` extensions, JSON syntax, heredocs, string templates, identifier rules, the style guide, the `.gitignore` contract | — |
| §1.5 the type system | absent | **the entire subject** — primitives, collections, structural types, `null`, **unknown as a third state**, conversion rules, set-vs-list semantics, `optional()`, `any`'s contagion, output type constraints, sensitivity and ephemerality as type properties, cty marks | — |
| §1.6 expressions | `for_each` shown once in a fragment | operators and precedence; the conditional's same-type/both-evaluated rule; all four `for` shapes; splats; index/attribute access; `can`/`try`; **dynamic blocks**; the complete reference inventory; `terraform.applying`; `path.*` distinctions; **the resource-address grammar** | — |
| §1.7 functions | absent | **the entire subject** — all ten categories by name, the `format` verbs, `flatten`+`setproduct`, the absence of deep merge, `templatefile`, the `timestamp()`/`uuid()`/`bcrypt()` perpetual-diff family, CIDR functions, **provider-defined functions**, `terraform metadata functions`, and the list of functions that do not exist | — |
| §1.8 variables | `var` described in one sentence in § 3 | the full block argument set; required-vs-optional; `nullable`; `ephemeral`; `deprecated`; `validation` blocks and idioms; **the complete precedence order**; the `.auto.tfvars` rule; the contexts variables cannot reach; why `backend` cannot take variables; test-file variables | "`var` is an input parameter" |
| §1.9 locals | one sentence in § 3 | the plural/singular mismatch; lazy evaluation; what locals are and are not for; the `common_tags` pattern; sensitivity propagation | "`local` is a computed intermediate value" |
| §1.10 outputs | `sensitive = true` mentioned twice | the full argument set; **the three audiences**; root outputs stored in state; `ephemeral` outputs; output `precondition`; `depends_on`; outputs as module API and `deprecated`; `-json`/`-raw`; indexing iterated module outputs | sensitivity covered correctly but only as a display caveat |
| §1.11 providers | § 4 — the definition, `required_providers`, `~> 5.0`, the lock-file trap | the plugin-subprocess mechanism; registry tiers; source-address grammar; installation flow; `TF_PLUGIN_CACHE_DIR`; mirrors and air-gapped installs; OCI sources; requirement-vs-configuration; authentication being the provider's job; **aliases**; **passing providers to modules**; `configuration_aliases`; inheritance rules; why a module must not contain a `provider` block; provider `for_each`; built-in providers | provider versioning is named but the mechanism and the alias/module plumbing are absent |
| §1.12 the lock file | § 4 — one trap about committing it | the file's structure; **`h1:` vs `zh:`**; the multi-platform CI failure and `providers lock -platform`; `-upgrade`; `-lockfile=readonly`; reviewing a lock diff; `terraform providers` as the requirement tree | the trap is right but has no mechanism behind it |
| §1.13 resources | `aws_instance`/`aws_security_group` used as examples | arguments vs attributes; `id`; **resource identity**; the six plan actions and their symbols; **why replacement happens (`ForceNew`/`RequiresReplace`)**; tainting and `-replace`; partial-apply cases; `terraform_data`; the utility providers; `ephemeral`/`list`/`action` blocks | replace-vs-update is explained well in § 2 but attributes the decision to "provider schema" without naming the mechanism |
| §1.14 data sources | `terraform_remote_state` named in § 4 | **the entire subject** — when data sources are read, plan-vs-apply deferral, their state entries, cost at scale, `terraform_remote_state`'s arguments and its security coupling, the ranked alternatives, scoped data sources, `external`, `http`, and the self-reference trap | one sentence: "lets you reference state from another Terraform project" |
| §1.15 meta-arguments | § 2 — `depends_on`; § 3 — `for_each` and the index trap; § 5 — `ignore_changes` | the per-block availability table; `count` fully; `count` as a conditional; the `toset()` rule; **the re-indexing proof**; plan-time key requirement and its error text; `count`→`for_each` migration; `depends_on` on modules and its parallelism cost; **`create_before_destroy`**; **`prevent_destroy`**; `replace_triggered_by`; `precondition`/`postcondition`; **`destroy = false`**; **`action_trigger`**; the "lifecycle cannot use variables" rule | the `for_each` index trap is the guide's best paragraph and must be kept and expanded; `ignore_changes` appears only as a drift workaround |
| §1.16 modules | § 3 — folder definition, invocation, scope, `module.` prefix | the `module` block's full argument set; **all module source types**; `ref=` pinning and `//subdir`; dynamic `source`/`version`; `.terraform/modules`; the standard structure and registry naming; `terraform-docs`; **when to make a module at all**; composition vs nesting with the pass-through arithmetic; the inflexible-module anti-pattern; module versioning and breaking changes; **`moved` blocks as a module's migration tool**; nested addresses; `for_each` over modules; public-registry risk | "a module is a scope boundary" is stated but modules-as-API, versioning and composition are absent |
| §1.17 state model | § 1 — strong: the file, refresh, drift, why-not-a-cache, locking, the secrets trap | the formal binding definition; **the dependency-edges-in-state point**; `lineage`; `serial`; `terraform_version` forward-only migration; inspection commands; the never-hand-edit rule; **how many states an estate should have**; blast radius and apply duration as splitting criteria | the "not a cache" argument is asserted with consequences but not derived; state contents are described as "all attributes" without the structure |
| §1.18 backends | § 4 — local vs remote in two sentences; DynamoDB locking in § 1 | the backend inventory with locking support; the removed backends; **partial configuration and `-backend-config`**; the complete S3 argument set with defaults; **`use_lockfile` and the conditional-write mechanism**; the state-bucket hardening checklist; versioning as recovery; `azurerm`/`gcs`/`pg`/`kubernetes`/`http` specifics; `remote` vs `cloud`; **backend migration procedure**; `.terraform/terraform.tfstate` as the backend record; `-lock-timeout` | "Local backend uses `.tfstate` on disk" and one DynamoDB sentence |
| §1.19 the workflow | § 2 — the five-step plan description, apply, and the plan-file warning | the six-step plan **with the provider RPCs named**; the five-step apply with **incremental state writes**; saved-plan semantics and staleness rejection; the plan file as a secret; the three refresh modes; `-refresh=false` economics; `-target` and its documented warning; `-replace`; `-exclude`; **`-parallelism` = 10**; `-json`; `TF_LOG`; **the guarantees and non-guarantees table**; **"there is no rollback"** | the plan steps are correct but omit the RPCs, the lock semantics and the state-write cadence |
| §1.20 registry and ecosystem | absent | **the entire subject** — the registries, private registries, reading provider docs, `providers schema -json`, and the 16-tool ecosystem table including the tfsec→Trivy change | — |
| §2.1 the four worlds and cost | absent | **the entire subject** — the four-worlds frame, the six pairwise disagreements, and the master per-command cost table | — |
| §2.2 `count` vs `for_each` decided | § 3 — the trap, correctly | the decision table; the worked re-indexing proof; the key rules; keys-for-humans; nested iteration arithmetic; `one()`; `count`'s remaining uses; the migration procedure; the silent `toset()` deduplication | the trap names the symptom but not the mechanism or the migration |
| §2.3 iteration and shape | absent | **the entire subject** — `dynamic` in depth, blocks vs nested attributes under protocol 6, configuration-as-data and its limit, generated Terraform, and why provider iteration is impossible in Terraform | — |
| §2.4 module design at scale | absent | **the entire subject** — the three archetypes, interface design, input shape and versioning consequences, defaults-as-API, what a module must never contain, composition depth arithmetic, monorepo vs repo-per-module, and the worked QuizStakes module interface | — |
| §2.5–2.6 environment, account and region layout | absent | **the entire subject** — the four layout patterns, promotion, where environments legitimately differ, prod-only-setting drift, the six-layer split, the bootstrap chicken-and-egg, the account map, cross-account credential resolution, multi-region aliases, and `allowed_account_ids` as a guardrail | — |
| §2.7 remote state and data flow | § 4 — one sentence | the four ranked mechanisms; why `terraform_remote_state` requires read access to every secret; the rename coupling; `defaults`; the data-source and parameter-store alternatives; the unsolved ordering problem | — |
| §2.8 workspaces | absent | **the entire subject** — the definition, state paths, `workspace_key_prefix = env:`, the feature-branch use case, **HashiCorp's explicit guidance against workspaces for environments**, the HCP-workspace name collision, and the `default`-workspace path asymmetry | — |
| §2.9 refactoring and surgery | § 5 — `removed` blocks named in one clause | **`moved` blocks** in full; what they can and cannot move; retention policy; `removed` with and without `destroy`; `lifecycle { destroy = false }`; **`import` blocks**, `identity`, `for_each`, `-generate-config-out` and the pruning discipline; the zero-changes gate; import at scale; the legacy `terraform import`; `state mv`/`rm`/`push`/`pull`/`replace-provider`; the state-splitting runbook; **the universal surgery preamble** | `removed` blocks get half a sentence with no syntax |
| §2.10 drift | § 1 and § 5 — the definition, examples, read-only nature, and the `ignore_changes` workaround | the precise definition against shadow infrastructure; drift as a **side effect of refresh**; `-refresh-only` as report vs acceptance; **the four drift responses**; the cause taxonomy; provider normalisation as false drift; **the perpetual-diff catalogue**; `ignore_changes` as ownership transfer; the `ClientRestrictions` case; continuous detection and its cost; `check` vs drift; IAM as the only real fix; the honest limits | drift is defined and exemplified but the response taxonomy and the perpetual-diff family are absent |
| §2.11 secrets | § 1 and § 5 — the state-secrets trap and the `sensitive` clarification, both correct | the three leak sites; what `sensitive` does mechanically; `nonsensitive()`; **ephemeral values and their lifecycle**; **write-only arguments and `*_wo_version`**; what still lands in state; **OpenTofu state encryption in full**; migration and rollback; HYOK; **the four ranked secret patterns**; the Appendix B.4 compliance check; rotation; **OIDC CI credentials and the read-only plan role** | the trap is right; there is no mechanism, no ephemeral/write-only coverage and no encryption story |
| §2.12 validation and checks | absent | **the entire subject** — the six-layer stack, `variable validation`, `precondition`/`postcondition` and their asymmetry, **`check` blocks and their warning-only design**, scoped data sources, the QuizStakes check set, the invariant-to-layer mapping, and `error_message` quality | — |
| §2.13 testing | absent | **the entire subject** — the pyramid, **`terraform test` in full** (`run`, `plan_options`, `assert`, `expect_failures`, `state_key`, `parallel`, cleanup order, `-junit-xml`), provider mocking and overrides, what a mocked test proves, Terratest, the recommendation, the `moved`-block regression test, and infrastructure-specific flakiness | — |
| §2.14 policy as code | absent | **the entire subject** — plan JSON as the universal mechanism, Sentinel and its imports, enforcement levels, the 350+ pre-written policies, OPA/Rego and `conftest`, Terraform Policy (beta), **what plan-time policy cannot see**, defence in depth, and the QuizStakes policy set with the blast-radius cap | — |
| §2.15 pipeline security | § 1 — state encryption at rest advised | the threat model; **"an apply is RCE with cloud-admin credentials"**; module and provider supply chain; banning provisioners; the state-bucket hardening checklist; least privilege for the apply role and its IAM-escalation limit; the tflint/checkov/Trivy comparison and the **tfsec deprecation**; code vs plan scanning; secret scanning; **the plan-output-in-a-PR leak**; audit | one sentence of advice |
| §2.16 CI/CD | § 5 — "always plan + apply in one CI job", correctly | **the canonical pipeline with commands and gates**; the plan artifact as contract; artifact security and expiry; staleness handling; `-detailed-exitcode` driving the pipeline; **pipeline concurrency groups**; the fully worked concurrent-apply trace; PR-driven workflow; OIDC; plugin caching arithmetic; matrix ordering; why `init -upgrade` in CI is an anti-pattern; drift and destroy pipelines; ephemeral environments; HCP as the alternative; **"recovery is forward, there is no rollback"**; the break-glass path | the advice is right but stated as a rule with no mechanism and no pipeline |
| §2.17 cost | absent | **the entire subject** — Infracost and its blind spots, cost as a policy gate, tagging for allocation, **the pipeline's own bill**, and the cost of not having IaC | — |
| §2.18 performance at scale | absent | **the entire subject** — resources-per-state as the scaling variable, the symptom ladder, where time goes, the five levers, why splitting state is the only asymptotic fix, parallelism tuning in both directions, rate limits, large `for_each`, module fetch cost, **state size arithmetic**, `TF_STATE_PERSIST_INTERVAL`, OTel tracing, and **the lock as a throughput ceiling** | — |
| §2.19 provisioners | absent | **the entire subject** — the documented last-resort position, why they break the model, all three provisioners and their arguments, `connection` blocks, the WinRM removal, `self`, create-time failure tainting, `when = destroy`'s flaw, the ranked alternatives, `terraform_data` + `triggers_replace`, and a policy banning them | — |
| §2.20 Actions, list resources, Search | absent | **the entire subject** — `action` blocks, `on_failure`, list resources and `terraform query`, `validate -query`, Terraform Search, and why this matters for adopting a hand-built estate | — |
| §2.21 HCP Terraform / TFE | Terraform Cloud named twice as a backend option | **the entire subject** — the two distributions, the `cloud` block, remote execution, agents, workspace concepts, **the run pipeline stages and where policy sits**, run tasks, private registry and no-code modules, drift detection, ephemeral workspaces, **HYOK**, RUM pricing arithmetic, the `tfe` provider, and the honest positioning | named, never explained |
| §2.22 Stacks | absent | **the entire subject** — components and deployments, the file names and the beta→GA rename, deployment groups and auto-approve checks, **deferred changes**, `-allow-deferral`, the hard limits, the four-way comparison against modules/workspaces/Terragrunt, and the QuizStakes Stack sketch | — |
| §2.23 CDKTF and alternatives | absent | **the entire subject** — **the 10 Dec 2025 deprecation**, what CDKTF was, why a Java engineer cared and why it failed, the migration path via synthesised JSON, Pulumi, and the reviewability-beats-expressiveness argument | — |
| §2.24 choosing Terraform | absent | **the entire subject** — the decision table, where Terraform is the wrong tool, the Kubernetes-provider boundary, the "Terraform all the way down" failure, and the two-tool boundary rule | — |
| §3.1–3.2 pipeline and value system | absent | **the entire subject** — the eleven run stages, the Core/provider boundary and its consequence, two-phase HCL parsing, diagnostics, **cty**, arbitrary-precision numbers, **marks**, **unknowns and refinements**, the evaluation context, and why there is no file scope | — |
| §3.3 the graph | § 2 — "constructs a dependency graph" and "topological order" | **the node types**; the nine construction steps; **the transformer pipeline**; orphans from state; **destroy-edge reversal**; replacement as two nodes; **`create_before_destroy` propagation**; transitive reduction; the parallel walk and **`-parallelism` = 10**; **the critical-path argument**; cycle diagnosis; module expansion; `terraform graph`; how `-target` prunes; provider-node ordering | one clause per concept, with no node types and no parallelism |
| §3.4 unknowns and the two-phase model | absent | **the entire subject** — plan and apply as the same walk, unknown propagation, **why `count`/`for_each` cannot be unknown**, the exact error and its four remedies, deferred actions, data-source deferral, unknown provider configuration, `terraform.applying`, and **the plan/apply consistency rules** | — |
| §3.5 the change lifecycle | absent | **the entire subject** — the full RPC sequence, `GetProviderSchema` cost, `UpgradeResourceState`, `ReadResource` returning null, **`PlanResourceChange` as where replacement is decided**, `ApplyResourceChange`'s partial-failure semantics, private data and the 1.16 change, `ImportResourceState`, `GenerateResourceConfiguration`, the ephemeral and function RPCs, `Stop`, and the create-then-crash and timeout traces | — |
| §3.6 the plugin protocol | absent | **the entire subject** — go-plugin and gRPC, the handshake, the `.proto` files, protocol 5 vs 6 and their CLI requirements, **nested attributes**, the schema shape, **`Optional + Computed`**, msgpack, `providers schema -json`, and provider process lifecycle | — |
| §3.7 provider development | absent | **the entire subject** — SDKv2 vs the framework, the zero-value problem, the framework's interfaces, **plan modifiers and `UseStateForUnknown`**, `ForceNew` vs `RequiresReplace`, muxing, `terraform-plugin-go`, acceptance testing with `PlanOnly`, write-only implementation, provider-defined functions, ephemeral resources, actions and list resources, and why reading provider source is faster than guessing | — |
| §3.8 the state file decoded | § 1 — "a JSON blob" | **every top-level key**; the `resources`/`instances` structure; `outputs` storing sensitive values in full; `check_results`; **`dependencies` as the recorded graph**; `serial` and `lineage` semantics; `schema_version` and irreversible upgrades; `sensitive_attributes`; **a real excerpt read line by line**; what is not in state; state-size arithmetic; the `jq` debugging queries; pseudo-resources; and the format-stability warning | "a JSON blob that captures the last known configuration and attributes" |
| §3.9 locking internals | § 1 — DynamoDB locking, the TTL claim, and the unlock ceremony | locking as distributed mutual exclusion; **the S3 conditional-write mechanism**; the DynamoDB conditional `PutItem`; **the `LockInfo` payload**; the **correction that there is no TTL by default**; `force-unlock`'s nonce; **the "is it safe" test**; **the exact lost-update corruption**; versioning as recovery; **the absence of fencing tokens**; the per-backend primitive table; lease vs lock; HCP's run queue | the unlock ceremony is named; the TTL claim is **wrong and must be corrected**; the corruption mechanism is asserted, not derived |
| §3.10 plan file and JSON formats | § 2 — "writes the diff to a binary plan file" | the plan file's contents; `format_version`; **every plan-JSON key**; `applyable`/`complete`/`errored`; `resource_changes` structure; **the `actions` array and how order encodes `create_before_destroy`**; `after_unknown`/`replace_paths`/sensitivity; **`action_reason`**; state JSON; the `configuration` section as policy input; the ndjson UI protocol; **how to read a plan diff properly** | one clause |
| §3.11 refresh internals | § 1 — refresh defined correctly | per-instance `ReadResource`; refresh not persisting during plan; null meaning deletion; the "changed outside of Terraform" report; what refresh cannot see; `-refresh=false`'s risk; the legacy `terraform refresh`; **the `ignore_changes`-still-records-drift interaction** | refresh is defined in two sentences with no mechanism |
| §3.12 sensitivity machinery | § 5 — the sensitive-output clarification | **marks**; propagation through interpolation; **redaction at render time, not storage time**; `sensitive_attributes`; provider-declared sensitivity; ephemeral enforcement; `ephemeralasnull()`; **the leak inventory** | the clarification is correct but has no mechanism |
| §3.13 version history | § 5 — "Terraform 1.7+" for `removed` blocks | **the entire subject** — 0.12 through 1.16.1 and OpenTofu 1.6 through 1.13, feature by feature. This is where every `[VERSION-TRAP]` lives | one parenthetical |
| §3.14 failure catalogue | § 5 — four failure modes: manual-change drift, concurrent applies, sensitive-output leaks, resource orphaning | **the 30-row table**; state loss; wrong-environment applies; stuck locks; the lost-update corruption; create-then-crash; `for_each` unknown; cycles; `create_before_destroy` propagation errors; inconsistent-result-after-apply; provider-bump replacement changes; lock-file checksum mismatch; credential failures; perpetual diffs; timeouts on stateful resources; rate limiting; failing destroys; `-target` aftermath; module-upgrade destruction; plan leaks; state growth; **and the `FundsLedger` near-miss** | the four present are good and must survive verbatim-plus-mechanism; the concurrent-apply entry needs the full trace and the corruption entry needs its derivation |
| §3.15 proofs | absent | **the entire subject** — the re-indexing cost, plan time as O(state), the critical-path bound, the lock throughput ceiling, state-transfer cost, the `~>` probability argument, why the lock is insufficient, **why there is no rollback**, why state cannot be reconstructed, why `for_each` keys must be known, why the provider decides replacement, the blast-radius arithmetic, and the drift-detection and `-refresh=false` cost calculations | § 1 asserts consequences without deriving any of them |
| §4 build it | two HCL fragments (a `for_each` subnet and a `required_providers` block) | **all sixteen artifacts and their Diff tables** — the graph engine, the diff engine, the state decoder, the plan analyser, the module, its test suite, the Rego bundle, **the minimal provider**, the lock simulator, the drift detector, the bootstrap, the pipeline, the import campaign, the surgery runbook, the ephemeral-secret proof, and the Infracost gate | — |
| §5 interview and retention | the 10-item atomic concept checklist | the 30 questions with answer shapes; the ~70-entry trap list; **the five stale answers**; the five cheat sheets; the debugging tree; the verbal one-liners; and the retention plan with the nine hands-on exercises | the checklist is correct as far as it goes and must be carried forward **expanded, never trimmed** — all ten items map to leaves and none may be dropped |

**Corrections the write pass must make to existing text** (not additions — the current file is
wrong, imprecise or stale here):

1. **§ 1's DynamoDB TTL claim is wrong.** *"DynamoDB lock entries have a TTL (default 0 = no
   expiry)"* conflates DynamoDB's TTL feature with Terraform's behaviour. Terraform writes the
   lock item with **no expiry attribute at all** and relies on the client to delete it; a crashed
   client leaves the lock held indefinitely. The corrected statement, plus the fact that
   **`use_lockfile` on S3 is now the recommended mechanism and every `dynamodb_*` argument is
   deprecated**, belongs in §1.18.8–§1.18.9 and §3.9.5. `[VERSION-TRAP]`
2. **§ 5's orphaning advice is backwards.** *"always run `terraform destroy` on resources you no
   longer manage via Terraform"* destroys the infrastructure, which is the opposite of what "no
   longer manage" means. The correct mechanism is a **`removed` block with
   `lifecycle { destroy = false }`** (1.7+), or `lifecycle { destroy = false }` on the resource
   (1.16+). The `removed` block is mentioned in the same paragraph but as an afterthought.
3. **§ 2's plan description omits the provider.** The five steps are right but attribute the
   refresh and the diff to Terraform; both are provider RPCs (`ReadResource`,
   `PlanResourceChange`), and the replacement decision in particular is the provider's. Without
   that, § 2's own correct trap about provider upgrades changing `ForceNew` has no mechanism
   behind it.
4. **§ 2's `terraform init` description is incomplete.** It omits module installation, the lock
   file, and the `.terraform/terraform.tfstate` backend record — and the claim that
   *"running `init` twice is idempotent"* is only true absent a backend change, where
   `-reconfigure` and `-migrate-state` produce materially different outcomes.
5. **§ 3's `for_each` trap uses list indices as the example** (*"if you change a `for_each` key
   from `[0]` to `[1]`"*), which conflates `count` addressing with `for_each` addressing. The
   mechanism must be restated as §2.2.2 does: `count` binds to positions, `for_each` binds to
   keys, and the bug is `count`-over-a-list (or `for_each` over a `toset()` of a list whose
   values change).
6. **§ 4's `terraform_remote_state` sentence understates the coupling.** It reads as a neutral
   feature; the write pass must state that it grants read access to the entire remote state,
   including its secrets, and rank the alternatives.
7. **§ 1's "Refresh does not modify resources"** is correct but must be paired with the fact that
   refresh **does** modify state (during `apply -refresh-only`) and does not persist during
   `plan` — the distinction the current text elides.
8. **Every example must be re-domained.** `aws_instance.api`, `aws_security_group.api`,
   `aws_subnet.tier`, `var.subnets`, `myapp`, the "networking state exported for a compute team"
   and the generic `payments` pipeline must become QuizStakes services, modules and status codes
   per the domain block at the top of this file.

---

## Leaf counts

Counted from the numbered leaf lines in this file.

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — BASICS | 20 (§1.1–§1.20) | 332 |
| PART 2 — INTERMEDIATE | 24 (§2.1–§2.24) | 294 |
| PART 3 — UNDER THE HOOD | 15 (§3.1–§3.15) | 208 |
| PART 4 — BUILD IT | 16 artifacts + 16 Diff tables | 32 |
| PART 5 — INTERVIEW & RETENTION | 5 (§5.1–§5.5) | 53 |
| **Total** | **80** | **919** |

**Tag counts** (occurrences of each tag across the file, including the legend row and the gap
table): `[RESEARCH]` **188** — every leaf that exists because of, or was corrected by, the
research phase, and which the write pass must re-verify against its cited source.
`[VERSION-TRAP]` **44**, of which 22 are the numbered deltas in the header.
`[TOFU]` **29** — leaves where Terraform and OpenTofu differ and both must be stated.
`[PROVE]` **295**, `[TRAP]` **222**, `[SOURCE]` **89**, `[BUILD]` **18**, `[SURGERY]` **31**,
`[INCIDENT]` **24**, `[COST]` **41**, `[X-REF nn]` **101**.

**Target version restated for the write pass: Terraform CLI 1.16.1 and OpenTofu 1.12.6, as of
2026-09-03.** Any constant, default, block name or flag the write pass cannot confirm against a
current primary source must not be written.


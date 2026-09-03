# 23 — Terraform & Infrastructure as Code

Scope: what a backend engineer must know about Terraform as a runtime — the state model, the execution
model, how drift detection works, why `terraform apply` requires explicit review, and why Terraform is
not a templating tool. Depth target: understanding why a seemingly small change requires a resource
replacement, why state corruption is catastrophic, and how to reason about concurrent applies.

---

## 1. State: the central authority, and why it is not just a cache

**State file** — a JSON blob (usually `.tfstate` on disk or in S3/Terraform Cloud) that captures the
**last known configuration and attributes of every resource Terraform has ever created**. It is the
single source of truth for what resources exist; the Terraform configuration file is a *recipe* for
what should exist, not a record of what does.

**Refresh** — Terraform queries the live infrastructure (e.g., `aws ec2-describe-instances`) and
updates the state with current attribute values (e.g., if an EBS volume grew, the state volume size
updates). Refresh does not modify resources; it synchronises state with reality.

**Drift** — when reality diverges from state. Examples: you manually stopped an EC2 instance via the
AWS console, changed an IAM policy in the console, or a Lambda's environment variables got overwritten
by a deployment pipeline. Drift is **read-only**: Terraform *detects* it (state-vs-reality mismatch)
but does not automatically fix it. `terraform plan` will show you the changes needed to repair drift.

**Why state is not a cache.** A cache can be evicted and rebuilt. State cannot. If the state file is
deleted or corrupted, Terraform loses the link between resource names in your configuration (e.g.,
`aws_instance.api`) and the actual AWS resource IDs. Re-running `terraform apply` without state will
attempt to re-create every resource, which means:
- Destroying the running instance and its data.
- Attempting to re-reserve S3 bucket names or IPs that are already taken (fails).
- A partially failed apply leaves you with orphaned resources not tracked by Terraform.

**State locking** — when using a remote backend (S3 with DynamoDB, Terraform Cloud, Consul), a lock
entry prevents concurrent applies. One apply acquires the lock, runs, and releases it. A concurrent
apply blocks until the lock is free. DynamoDB lock entries have a TTL (default 0 = no expiry) and can
leave you locked indefinitely if an apply crashes. Understand the unlock mechanism (typically `terraform
force-unlock <lock-id>`) and when it is safe (only if the holder truly died; forcing during an active
apply corrupts state).

**Trap:** the state file contains **all attributes**, including secrets (database passwords, API keys).
It is not encrypted by default when stored locally. Use `sensitive = true` on outputs to hide them from
console logs, and store the state file in S3 with encryption at rest, versioning, and restricted IAM
access.

---

## 2. Execution model: plan, graph, apply

**terraform init** — downloads provider plugins (e.g., the AWS provider binary) and initialises the
backend. Running `init` twice is idempotent; it checks if the backend is already initialised.

**terraform plan** — (1) loads the configuration (`.tf` files); (2) reads the current state; (3) queries
the provider to refresh attributes; (4) constructs a **dependency graph** (if you reference
`aws_instance.api.id` in `aws_security_group.api`, the SG depends on the instance); (5) computes the
diff (what resource actions are needed — create, update, replace, destroy) in **topological order**
(destroy orphans first, then update in dependency order); (6) writes the diff to a binary plan file (or
displays it in the CLI).

**terraform apply** — takes the plan file (or re-plans if none provided, which is dangerous: configuration
may change between plan and apply, a source of race conditions in CI/CD). Reads the plan, asks "do you
want to proceed?" (unless `-auto-approve` is set), then executes each action serially in dependency order.
Terraform acquires the lock, applies changes, and releases the lock.

**Replace vs. update.** An *update* modifies the resource in place (e.g., changing a tag). A *replace*
destroys and re-creates (e.g., changing an EC2 instance's AMI, which the provider cannot modify live).
Terraform decides based on provider schema: each resource attribute is marked `ForceNew: true` (forces
replace on change) or not. **Trap:** a provider version upgrade can change these flags, so a field you
thought was updatable becomes a replace — leading to surprise downtime in production.

**Depends-on and implicit dependencies.** If your config references `aws_instance.api.id` in
`aws_security_group.api`, Terraform infers the SG depends on the instance. Explicit `depends_on = [...]`
forces an ordering that is not discoverable from references (e.g., "deploy this Lambda after this IAM
role, even though the Lambda's code does not reference it"). Use sparingly; explicit dependencies are
maintainability debt.

---

## 3. Modules: reuse, and the scope of `for_each`

**Module** — a folder containing `.tf` files that define a set of resources. You invoke a module with
`module "name" { source = "path"; var1 = value1 }`. The module receives input variables, outputs
selected attributes, and is a **scope boundary**: resources inside the module use paths like
`aws_instance.api` internally, but are referred to globally as `module.name.aws_instance.api` (the
`module.` prefix).

**for_each and for loops.** A resource or module can be instantiated multiple times:
```hcl
resource "aws_subnet" "tier" {
  for_each = var.subnets  # e.g., { "public" = {...}, "private" = {...} }
  cidr_block = each.value.cidr
}
```
Each iteration is keyed and addressable: `aws_subnet.tier["public"].id`. **Trap:** if you change a `for_each`
key from `[0]` to `[1]` (reordering a list), Terraform interprets it as "destroy resource at index 0, create
new resource at index 1" — a replace of all resources downstream. Use map keys (strings) instead, which are
stable under reordering.

**Locals and vars.** `var` is an input parameter; `local` is a computed intermediate value (like a local
variable in a function). Locals are not exposed outside the module. Use them to avoid repetition (`local.common_tags`).

---

## 4. Providers, versions, and required

**Provider** — a plugin that translates Terraform resource types into API calls (e.g., the AWS provider
interprets `aws_instance` into `ec2:RunInstances`). Providers are versioned independently of Terraform.

**required_providers** block pins versions:
```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # means >= 5.0, < 6.0
    }
  }
}
```
This goes into `.terraform.lock.hcl` after `terraform init`. **Trap:** forgetting to commit the lock file
means teammates may get different provider versions, leading to mysterious plan/apply divergence.

**Backend** — how Terraform persists state. Local backend (the default) uses `.tfstate` on disk.
`terraform_remote_state` data source lets you reference state from another Terraform project (e.g.,
networking state exported for a compute team to consume). Each state is separate; there is no global
registry.

---

## 5. Common failure modes

**State drift with manual changes.** A team member changes an IAM policy in the console. The next
`terraform plan` sees the divergence and shows a revert. Running `apply` overwrites the manual change
with whatever is in the config. Prevent this: lock down console/API access via IAM policy, or use
`lifecycle { ignore_changes = [policy_document] }` to declare Terraform does not own this field.

**Concurrent applies.** Two CI jobs both run `terraform apply` on the same state. The first acquires the
lock, applies, and releases. The second waits for the lock, then applies. **Problem:** the second apply's
plan is stale — it was computed before the first apply, so it may re-create resources the first apply
already made, or destroy things it should not. Prevent this: use DynamoDB locking and always plan +
apply in one CI job without human gap; never re-plan after a time delay.

**Sensitive output leaks.** Marking an output `sensitive = true` hides it from `terraform output` console
display, but the value is still stored in state (unencrypted, by default). It does not encrypt the value,
only redacts the console output. Always encrypt state at rest.

**Resource orphaning.** If you delete a resource from the config without running `terraform destroy`
first, the resource lingers in reality. The state still references it. Next apply, Terraform tries to
destroy it. If that fails, you have orphaned infrastructure. Practice: always run `terraform destroy` on
resources you no longer manage via Terraform, or use `removed` blocks (Terraform 1.7+) to gracefully
unmanage resources.

---

## Atomic concept checklist

- [ ] I understand state is the authority, not a cache, and that deleting it means Terraform will attempt
  re-creates on next apply.
- [ ] I know the difference between update and replace, and that provider versions can change which is
  which, causing surprise downtime.
- [ ] I know that `depends_on` is for ordering, not for indicating ownership, and should be explicit only
  when implicit references exist.
- [ ] I understand `for_each` keys should be stable maps, not reordered lists, to avoid unwanted destroys.
- [ ] I know that `sensitive = true` on outputs does not encrypt state, only hides console display.
- [ ] I know DynamoDB locking can deadlock and understand the unlock ceremony.
- [ ] I understand drift detection (plan shows mismatches) and that fixing drift requires `terraform apply`.
- [ ] I know concurrent applies are unsafe and require backend locking + single-job discipline.
- [ ] I understand that state encryption at rest is separate from sensitive output redaction.
- [ ] I know the difference between local and remote backends, and that `terraform_remote_state` reads
  another project's state.

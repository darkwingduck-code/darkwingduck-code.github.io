---
title: "Safe Terraform IaC Design: Boundaries for Modules, Environments, State, and Secrets"
date: 2026-07-21 09:30:00 +0900
categories: [Platform Engineering, Infrastructure]
tags: [terraform, infrastructure-as-code, state-management, security, devops]
description: Understand Terraform as a declarative change system and design module contracts, environment isolation, remote state, secret management, and plan/apply verification procedures.
lang: en
translation_key: terraform-iac-safe-foundations
hidden: true
---

{% include language-switcher.html %}

## The problem: Turning infrastructure into code does not automatically make it safe

Terraform turns manual clicks into reproducible code, but at the same time, it concentrates infrastructure change permissions and actual resource state into a single workflow. If you begin without structure, one small root module ends up shouldering every environment, permission, secret, and provider configuration.

Common failures include the following.

- Development and production share the same state and credentials.
- A module exposes so many choices that it effectively becomes another platform.
- Local state is lost, or multiple runners modify it at the same time.
- `sensitive = true` is mistaken for encryption, leaving secrets in state.
- Code, providers, or state change between the reviewed plan and the actual apply.
- `-target` and manual console changes become standard operating practice.

The goal of IaC is not to increase the number of files. It is to **turn change intent, actual state, permission boundaries, and verification results into a single auditable flow**.

## Mental model: Reconciling configuration, state, providers, and real infrastructure

A Terraform run has four elements.

- **configuration**: HCL that expresses the desired state
- **state**: Mapping information between Terraform addresses and actual remote object IDs and attributes
- **provider**: A plugin that reads and changes APIs
- **real infrastructure**: Actual resources in the cloud, SaaS systems, and on-premises environments

`terraform plan` is not a simple file diff. It creates an execution plan by comparing configuration, previous state, and the actual state read by providers. `apply` calls APIs according to the dependency graph and records successful results in state.

State is therefore not a cache. It is critical operational data containing items such as:

- Actual resource identifiers
- Dependencies and attribute snapshots
- Outputs and some provider return values
- Inputs and computed results that may be secret

Losing state does not make the actual infrastructure disappear, but Terraform loses its ownership mapping. Conversely, someone with only the state file can still learn sensitive information and the infrastructure's structure.

### Declarative does not mean “unordered”

A resource reference creates a dependency edge. Terraform parallelizes operations where possible while respecting graph order. Adding many meaningless `depends_on` declarations creates hidden coupling and slower plans. Express data flow through references, and use `depends_on` only when an API imposes an implicit constraint.

### A module is a policy contract more than a code-reuse mechanism

A good module narrows the choices the organization permits.

- input: What callers are allowed to decide
- local: Names, tags, and policies standardized by the module
- resource: Implementation details
- output: Stable contracts on which other components may depend

A “thin wrapper” that exposes every provider argument unchanged as a variable offers little abstraction value. At the other extreme, if one module owns the network, database, application, and monitoring, its change blast radius becomes large.

## Practical pattern: Small roots, stable modules, and independent state per environment

### A recommended starting structure

```text
infrastructure/
├── modules/
│   └── service/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── versions.tf
└── live/
    ├── development/
    │   ├── backend.hcl
    │   ├── main.tf
    │   └── terraform.tfvars.example
    └── production/
        ├── backend.hcl
        ├── main.tf
        └── terraform.tfvars.example
```

Duplicating an environment directory is not the only correct answer. Separate repositories, an orchestration layer, or per-account pipelines are also possible. The important invariants are:

- Each environment has an independent state key and apply permissions.
- Production uses a separate account or project and an independent approval boundary.
- The shared module's version or commit is pinned explicitly.
- Environment differences are explicit inputs, not a forest of conditionals.

Terraform workspaces are a convenience for operating multiple states from the same configuration, but they do not automatically provide strong security isolation or substantially different environment structures. If you need credential and account boundaries, separate the execution identities as well as the directories and state.

### Give modules narrow, verifiable contracts

An example `variables.tf`:

```hcl
variable "name" {
  description = "서비스를 식별하는 짧은 이름"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "name은 소문자로 시작하고 소문자, 숫자, 하이픈만 사용해야 합니다."
  }
}

variable "environment" {
  description = "배포 환경"
  type        = string

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "허용된 environment 값을 사용해야 합니다."
  }
}

variable "labels" {
  description = "추가 공통 label"
  type        = map(string)
  default     = {}
}
```

Keep standardized values inside the module in `main.tf`.

```hcl
locals {
  required_labels = {
    managed-by  = "terraform"
    environment = var.environment
    service     = var.name
  }

  labels = merge(var.labels, local.required_labels)
}

# provider에 독립적인 예시를 위해 실제 resource는 생략했다.
# 각 resource는 local.labels를 사용해 소유권과 환경을 표시한다.
```

Because later maps in `merge` override earlier ones, placing required labels last prevents callers from changing them. This is a small example of how a module encapsulates policy.

Expose only the minimum required contract through outputs.

```hcl
output "service_id" {
  description = "다른 module이 참조할 안정된 서비스 ID"
  value       = <RESOURCE_ADDRESS>.id
}
```

Outputting the entire resource object couples callers to implementation details. Return only what consumers actually need, such as an ID, endpoint, or role identifier.

### Manage version constraints and the provider lock together

```hcl
terraform {
  required_version = ">= 1.8, < 2.0"

  required_providers {
    <PROVIDER_NAME> = {
      source  = "<PROVIDER_NAMESPACE>/<PROVIDER_NAME>"
      version = "~> <REVIEWED_MAJOR.MINOR>"
    }
  }
}
```

Replace the placeholders in this example with the actual provider. Set version constraints in the root module and commit the `.terraform.lock.hcl` produced by `terraform init`. A module should declare the minimum provider version it needs, while the root is generally responsible for final selection and locking.

The lock file pins the provider binary selection and checksums. If execution spans multiple operating systems or architectures, deliberately manage the platform checksums required by CI and development environments.

### Separate backend and state access from code access

Do not write secrets directly in the backend block.

```hcl
terraform {
  backend "<REMOTE_BACKEND_TYPE>" {}
}
```

You can supply non-sensitive per-environment settings through a separate file.

```hcl
# live/production/backend.hcl
bucket         = "<REMOTE_STATE_BUCKET>"
key            = "<SERVICE>/production/terraform.tfstate"
region         = "<REGION>"
encrypt        = true
use_lockfile   = true
```

These arguments vary by backend type and Terraform version, so check the official documentation and the actual backend's capabilities. The core requirements are:

- Encryption in transit and at rest
- Locking that prevents concurrent applies
- Versioning and a recovery policy
- A least-privilege identity
- Separate keys and access policies for each environment
- Audit logs and alerts for anomalous access

Run initialization explicitly from the environment directory.

```bash
terraform init -backend-config=backend.hcl
terraform providers
```

Do not put backend credentials in files; issue short-lived credentials through CI OIDC or a standard credential chain. Writing an access key in `backend.hcl` can leave it behind through several paths, including `.terraform` metadata and shell history.

### Bind plan and apply into one reviewable change

The basic verification flow is:

```bash
terraform fmt -check -recursive
terraform init -input=false -backend=false
terraform validate
```

Run a plan that uses actual remote state and provider APIs from an approved identity and environment.

```bash
terraform init -input=false -backend-config=backend.hcl
terraform plan -input=false -out=tfplan
terraform show -no-color tfplan
```

A saved plan file is binary and may contain sensitive values. Do not preserve it indefinitely as a public CI artifact; apply encryption, access control, and short retention. Apply only a plan produced from the same commit, lock file, and state lineage.

```bash
terraform apply -input=false tfplan
```

If a person approves a textual plan and the pipeline automatically applies a new plan from another commit, that approval loses its meaning. The pipeline must bind the source SHA to the plan artifact digest.

### Pass secret references rather than secret values

The following declaration hides the value in the UI and some output, but it does not encrypt state.

```hcl
variable "bootstrap_secret" {
  type        = string
  sensitive   = true
  description = "초기 구성에만 필요한 비밀값"
}
```

If a provider API accepts the value as a resource attribute, that value may be stored in state. A possible design is:

1. Create the secret in a secret manager under a separate lifecycle.
2. Terraform connects only the secret ID or path and read permissions.
3. The workload reads the value from the secret manager using its runtime identity.
4. Do not pass the plaintext secret into plans, outputs, or logs.

If Terraform must also create the secret, acknowledge that state has become a secret store and operate state access, encryption, and rotation to that standard. Removing the marker with `nonsensitive()` is not a security solution.

### Drift detection does not end with a nightly plan

Detect drift from console changes and external automation with regular read-only plans. When you find drift, explicitly choose one of three responses.

- The real change was wrong: Restore the originally declared state with Terraform.
- The real change was legitimate: Reflect it in configuration and apply it through the normal PR process.
- Ownership was wrong: Review `import`, `moved`, and state operations to correct the responsibility boundary.

When changing a resource address, use a `moved` block so Terraform does not mistake the change for deletion and recreation.

```hcl
moved {
  from = <OLD_RESOURCE_ADDRESS>
  to   = <NEW_RESOURCE_ADDRESS>
}
```

Imports and state commands change Terraform's understanding of ownership even when they do not change the real resource. Check state versioning before the operation; afterward, always verify that the plan is empty as expected or contains only the intended diff.

## Verification checklist

Module review:

- [ ] The module has one cohesive lifecycle and owner.
- [ ] Input types, descriptions, validation, and defaults are clear.
- [ ] Callers cannot bypass required security and ownership labels.
- [ ] Outputs form a stable minimum contract rather than exposing the entire implementation.
- [ ] Provider and Terraform version ranges are specified.
- [ ] Upgrades and address changes have `moved` blocks and migration documentation.

Environment and state review:

- [ ] Development, staging, and production state and execution identities are separated.
- [ ] The remote backend provides encryption, locking, versioning, and auditing.
- [ ] Access to state and plan artifacts is narrower than permission to read the code.
- [ ] `.terraform/`, `*.tfstate*`, real `*.tfvars`, and plan files are not committed.
- [ ] `.terraform.lock.hcl` is committed after review.
- [ ] Production applies run only in a protected environment and an approved pipeline.

Change review:

- [ ] `fmt`, `validate`, linting, and policy checks pass.
- [ ] The plan's add, change, destroy, and replace actions have been read resource by resource.
- [ ] Forced replacements, data loss, and potential network disruption have been checked.
- [ ] The reviewed plan and the binary plan to apply came from the same source and state.
- [ ] There is a way to verify critical functionality and observability metrics after application.
- [ ] For changes that cannot be rolled back, the roll-forward procedure and backup restoration have been tested.

## Failure cases and limitations

### One enormous state

References are convenient, but even a small change requires refreshing the entire graph and broad permissions. Group resources into the same state when they change together, share an owner, and should have the same blast radius. Conversely, splitting state too finely increases the burden of cross-state outputs, ordering, and orchestration.

### Absorbing every environment difference into conditionals

Putting all environments into one root with `count`, `for_each`, and ternary expressions makes plans hard to read. Put shared policies in modules and environment-specific composition in thin roots.

### Using `-target` as an everyday deployment tool

`-target` is a limited tool for recovery and special situations. Applying only part of the graph can lose consistency between the full configuration and actual state. Always run a full plan after using it.

### Treating `prevent_destroy` as a backup

A lifecycle guard prevents some mistakes, but a privileged user can remove it, and it cannot prevent deletion outside the provider. Data resources need separate backups, recovery drills, retention, and deletion protection.

### Treating a successful apply as a healthy service

The fact that an API created a resource is not the same as the application being healthy. After deployment, check DNS, permissions, connectivity, health, and SLO metrics. IaC does not replace operational verification or incident response.

### Managing everything with Terraform

Terraform excels at declarative resources with long lifecycles. Forcing high-frequency application deployments, imperative data migrations, and one-off bootstrapping into it can destabilize state and the graph. Choose tools that fit each change's lifecycle and rollback characteristics.

Safe Terraform comes from boundary design, not clever HCL. Treat modules as policy boundaries, state as a security asset, plans as change contracts, and pipeline identities as execution authority.

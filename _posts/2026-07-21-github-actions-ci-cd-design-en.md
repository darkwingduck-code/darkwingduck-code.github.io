---
title: "Designing GitHub Actions CI/CD: Start with Trust Boundaries, Not Fast Automation"
date: 2026-07-21 09:20:00 +0900
categories: [Platform Engineering, CI-CD]
tags: [github-actions, ci-cd, supply-chain, automation, security]
description: Learn to design GitHub Actions workflows, jobs, and runner trust boundaries securely with permissions, secrets, environments, matrices, caches, and concurrency.
lang: en
translation_key: github-actions-ci-cd-design
hidden: true
---

{% include language-switcher.html %}

## The Problem: A Passing Workflow Is Not the Same as a Trustworthy Pipeline

CI/CD reduces repetitive work, but a poor design connects the repository's most powerful privileges to external input. A workflow checks out source code, downloads dependencies, runs tests, and sometimes changes the production environment. In other words, a small YAML file serves simultaneously as a build system, credential broker, and deployment control plane.

If you stop at “the tests run automatically,” the following problems remain.

- Every job shares a default token with write access.
- Untrusted code from a fork PR can access secrets.
- An older deployment from the same branch overwrites the latest deployment.
- Caches and artifacts move into execution stages without provenance checks.
- Only one of many matrix combinations performs meaningful validation.
- Build and deployment are coupled, preventing promotion of the same artifact.

The goal of a good pipeline is not simply a green check. It is **a reproducible result for the same input, least privilege, consistent promotion of a validated artifact, and clear stopping points on failure**.

## Mental Model: A Workflow Is a DAG That Transmits Privileges and Data

Distinguish the principal units of GitHub Actions.

- **event**: External input that starts a run, such as `pull_request`, `push`, or `workflow_dispatch`
- **workflow**: A file that defines events and the job graph
- **job**: A collection of steps that run on one runner. Filesystems are not shared between jobs by default.
- **step**: One action or shell command
- **runner**: Ephemeral or self-hosted compute that executes code
- **artifact**: An output explicitly transferred and retained between jobs and workflows
- **cache**: An optimization that quickly restores reproducible dependencies
- **environment**: A control boundary that groups a deployment target, approvals, protection rules, and environment secrets

Ask four questions at every boundary.

1. Who controls the input?
2. What code is executed?
3. Which tokens and secrets are exposed?
4. How are the provenance and integrity of outputs verified?

### Separate CI from CD

CI validates a commit's quality and creates an immutable artifact. CD promotes an already validated artifact to a specific environment. If every environment rebuilds it, the “binary that was tested” may differ from the “binary deployed to production.”

```text
commit -> test -> build -> scan -> signed artifact
                                      |
                                      +-> staging deploy
                                      +-> production approval -> production deploy
```

A deployment identifier should be an immutable value such as a commit SHA, image digest, or artifact digest, rather than a branch name.

## Practical Pattern: Validate PRs with Low Privilege and Deploy Across a Separate Boundary

### A Least-Privilege CI Workflow

The following example is a basic skeleton for a Python project. Adapt it to the repository's lock file and test commands.

{% raw %}
```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

# workflow 전체의 기본값은 읽기 전용이다.
permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: python-${{ matrix.python }} / ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ["3.11", "3.12"]

    steps:
      - name: Check out source
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
          cache-dependency-path: requirements.lock

      - name: Install locked dependencies
        run: python -m pip install --require-hashes -r requirements.lock

      - name: Static checks
        run: python -m ruff check .

      - name: Unit tests
        run: python -m pytest -q --maxfail=1
```
{% endraw %}

For readability, the example uses the major tags of official actions. In a high-assurance repository, pin an action to a reviewed **full commit SHA** and update it using a dependency update tool. Review a third-party action's source, maintainer, release provenance, and requested permissions rather than its marketplace rating.

A matrix is not better simply because it is larger. Include only the dimensions that the support contract must actually guarantee.

- Library: the minimum and latest supported runtime combinations
- Application: the primary environment matching production, plus environments with high compatibility risk
- GPU or large integration: separate smoke tests on every PR from scheduled full tests

`fail-fast: false` preserves compatibility information from the remaining combinations when one fails. Conversely, expensive jobs should generally follow fast lint and unit jobs and be blocked with `needs`.

### Distinguish a Cache from an Artifact

| Item | Cache | Artifact |
|---|---|---|
| Purpose | Speed up reproducible inputs | Transfer and retain build outputs and reports |
| On a miss | The run should still succeed correctly, though more slowly | A required downstream stage should fail |
| Key | OS, runtime, lock-file hash, and so on | Commit SHA, build ID, digest, and so on |
| Trust | Assume possible contamination and validate | Manage provenance and digest together |

Validate dependencies restored from a cache against the lock file and package hashes. Do not put arbitrary executable scripts or long-lived credentials in a cache. Review event and scope settings so that a cache writable from a PR does not flow into a privileged job on a protected branch.

Promote an artifact built once across environments. Limit its retention period to the business need, and verify its digest before deployment. Test reports and coverage are observability data; they do not replace the deployment binary.

### Deployment Jobs Use Environments and Short-Lived Credentials

Run a production deployment in a separate workflow triggered from a protected branch or tag, or in a strictly isolated job, rather than in the PR workflow. The following skeleton demonstrates the structure. Replace `<...>` values and action SHAs with settings for the relevant cloud and repository.

{% raw %}
```yaml
name: deploy

on:
  workflow_dispatch:
    inputs:
      artifact_digest:
        description: "검증된 artifact digest"
        required: true
        type: string

permissions:
  contents: read
  id-token: write

concurrency:
  group: production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    environment: production

    steps:
      - uses: actions/checkout@<REVIEWED_FULL_COMMIT_SHA>
        with:
          persist-credentials: false

      - name: Exchange OIDC token for short-lived cloud credentials
        uses: <CLOUD_PROVIDER_LOGIN_ACTION>@<REVIEWED_FULL_COMMIT_SHA>
        with:
          role: <DEPLOYMENT_ROLE_IDENTIFIER>

      - name: Verify and deploy the immutable artifact
        env:
          ARTIFACT_DIGEST: ${{ inputs.artifact_digest }}
        run: ./scripts/deploy.sh --digest "$ARTIFACT_DIGEST"
```
{% endraw %}

The essential points are as follows.

- Grant `id-token: write` only to the job that needs the OIDC exchange.
- Restrict the cloud trust policy by repository, branch or tag, and environment claims.
- Issue short-lived credentials instead of storing long-lived access keys as repository secrets.
- Configure approvers, allowed branches or tags, and environment-specific secrets on the `production` environment.
- Set production deployment to `cancel-in-progress: false`, and make the deployment tool itself safe under duplicate execution.

Using OIDC is not automatically secure. If the cloud-side trust conditions are too broad, a workflow on any branch may obtain the production role.

### Manage Secret Exposure Paths, Not Just Secret “Values”

Storing a secret in the GitHub UI is not the end of the task.

- A shell argument may appear in a process listing or debug log.
- Transforming or encoding a secret may prevent masking from recognizing it.
- Error objects, test fixtures, or artifacts may duplicate the value.
- The disk or processes of a self-hosted runner may leave traces for the next job.

Pass it only as an environment variable to the step that needs it, and never print the complete value.

{% raw %}
```yaml
- name: Call protected service
  env:
    SERVICE_TOKEN: ${{ secrets.SERVICE_TOKEN }}
  run: python scripts/publish.py
```
{% endraw %}

The default is not to provide protected secrets to fork PRs. In particular, `pull_request_target` can receive privileges in the base-branch context, so it must not be combined with a pattern that checks out and executes untrusted PR code. Separate metadata processing, such as labels and comments, from code execution into different workflows.

### Separate Expression Injection from Shell Quoting

Direct interpolation of user input such as a PR title into a `run` block can turn it into shell code. Pass the value through the environment and quote it in the shell.

Risky form:

{% raw %}
```yaml
- run: echo "${{ github.event.pull_request.title }}"
```
{% endraw %}

Safer form:

{% raw %}
```yaml
- name: Print PR title as data
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  shell: bash
  run: printf '%s\n' "$PR_TITLE"
```
{% endraw %}

When possible, avoid even printing user input, and use format validation and an allowlist.

### Concurrency Policies Differ Between CI and CD

In PR CI, a previous run loses value when a new commit arrives, so cancellation is efficient.

{% raw %}
```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
{% endraw %}

During deployment, abruptly canceling an in-progress change may leave the environment in an intermediate state. Serialize deployments to the same environment, and use queueing by default rather than cancellation. The application's deployment tool should support idempotency, timeouts, and either rollback or roll-forward.

## Validation Checklist

Check the following items in a PR that changes a workflow:

- [ ] The trigger responds only to required events and branches.
- [ ] Top-level `permissions` are read-only, with write access only on jobs that require it.
- [ ] Fork PRs and untrusted code cannot access secrets or deployment credentials.
- [ ] A policy pins actions from trustworthy sources to reviewed SHAs.
- [ ] Dependencies are verified with a lock file and hashes.
- [ ] The build succeeds correctly even on a cache miss.
- [ ] The artifact is linked to a commit or digest and is not rebuilt in each environment.
- [ ] Environment approvals and the cloud trust policy limit branch and tag scope.
- [ ] CI cancels stale runs, while CD serializes changes to the same environment.
- [ ] Every job has a reasonable `timeout-minutes` value.
- [ ] Failure logs and artifacts contain no secrets or personal information.
- [ ] Required-check names in branch protection remain valid after the workflow change.

Combine workflow schema linting, dependency review, secret scanning, and action-policy checks for static validation. Passing lint is not proof of a safe permission design, so also review the threat model for each event.

## Failure Cases and Limitations

### Solving Problems with `permissions: write-all`

Permission errors disappear, but the blast radius grows. Identify the required API operation and add only the specific scope at the job level.

### Assuming a Tag Fully Pins the Supply Chain

A major or version tag can move. A full commit SHA is a stronger fixed point, but the source and release process of that commit still require review. Pinning must be accompanied by update automation and vulnerability response.

### Using a Cache as a Trusted Build Output

A cache is an optimization, and deleting it must not affect correctness. Transfer deployment targets as explicit artifacts with provenance.

### Treating a Self-Hosted Runner Only as a Cost-Saving Measure

A self-hosted runner may have a larger attack surface, including network access, persistent disks, and cloud metadata. Do not execute public or fork PRs on a persistent runner; operate ephemeral isolation, image resets, egress restrictions, and patching.

### Running Every Test on Every PR

When validation becomes slow, developers work around it or create large batches. Layer the test portfolio into fast required gates, change-path-based integration, scheduled full regression, and post-deployment validation. Design path filters conservatively so that they do not omit real dependencies.

GitHub Actions is not a YAML syntax problem; it is a trust-boundary design problem. Separating events, code, credentials, artifacts, and environments reveals risky automation much earlier.

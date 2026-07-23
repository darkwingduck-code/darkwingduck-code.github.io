---
title: "Reproducible and Secure Docker Images: From Build Context to Non-Root Execution"
date: 2026-07-21 09:40:00 +0900
categories: [Platform Engineering, Containers]
tags: [docker, containers, reproducibility, supply-chain, security]
description: Design multi-stage builds, dependency pinning, health checks, non-root execution, and image verification around Docker layers and build contexts.
lang: en
translation_key: docker-reproducible-secure-images
hidden: true
---

{% include language-switcher.html %}

## The Problem: You Can Move “It Works on My Machine” into an Image

Containers package an execution environment, but they do not automatically guarantee reproducibility or security. If you retain a `latest` base image, unlocked dependencies, an oversized build context, the root user, or secrets copied into the image, you package environmental differences and attack surface along with the application.

Two images can differ even when built from the same Dockerfile.

- At build time, the base tag pointed to a different digest.
- The package index selected a new dependency.
- A local temporary file entered the build context.
- A different native wheel was downloaded for a different CPU architecture.
- Build metadata and timestamps differed.

Therefore, distinguish the goals.

1. **Functional reproducibility**: the same source and lock produce the same behavior.
2. **Dependency reproducibility**: the same base and package artifacts are selected.
3. **Bit-for-bit reproducibility**: even the generated image digest is identical.

A typical service should achieve the first two goals before extending to deterministic builds and provenance when supply-chain requirements are stricter.

## Mental Model: An Image Is Immutable Layers; a Container Is Runtime State

The core components of a Docker build are as follows.

- **Build context**: the set of files sent to the builder
- **Dockerfile instruction**: a step that creates a layer and image metadata
- **Image**: an immutable set of content-addressed layers and configuration
- **Container**: a running instance that combines an image with a writable layer, process, namespaces, and resource limits
- **Registry**: storage that retains and distributes image manifests and blobs

Each Dockerfile step creates a cache key from the previous state, the instruction, and the files it uses. If frequently changing source code is copied before dependencies are installed, even a small code change invalidates the dependency layer.

Tags and digests also differ.

```text
registry.example.invalid/service:1.4    # 이동 가능한 이름
registry.example.invalid/service@sha256:<DIGEST>  # 불변 content 주소
```

A useful combination is for humans to find releases by version tag while deployment systems use verified digests.

### Container isolation is one layer of the security boundary

Containers generally do not have a separate kernel like a VM. Use rootless runtimes, seccomp/AppArmor/SELinux, capability removal, read-only filesystems, network policies, and host patching together. Setting `USER` to non-root in the image is an important default, but it is not a complete sandbox.

## Practical Pattern: Small Context, Locked Inputs, Multiple Stages, and Minimum Runtime Privilege

### Restrict the build context first

Example `.dockerignore`:

```dockerignore
.git
.github
.env
.env.*
!.env.example
.venv
__pycache__/
*.pyc
*.log
.pytest_cache/
.mypy_cache/
tests/
docs/
dist/
build/
```

`.dockerignore` is not merely a tool for reducing image size. It reduces what is sent to the builder and prevents secrets and unnecessary files from being included by `COPY . .`. If a project actually needs tests or documentation at runtime, do not exclude them indiscriminately; design contexts for each build purpose.

Even if `.env` is excluded, its contents can be exposed if it has already been committed to Git or passed as a build argument. Secret scanning and credential rotation are separately required.

### A multi-stage Dockerfile for a Python service

The following example is a service skeleton that uses hash-locked binary wheels without requiring a compiler.

```dockerfile
# syntax=docker/dockerfile:1.7

# 로컬에서는 tag로 실행할 수 있지만, CI에서는 검토한 digest로 덮어쓴다.
ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS dependencies

WORKDIR /build
COPY requirements.lock ./requirements.lock

RUN python -m pip download \
      --require-hashes \
      --only-binary=:all: \
      --destination /wheelhouse \
      --requirement requirements.lock

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /nonexistent app

WORKDIR /app

COPY --from=dependencies /wheelhouse /wheelhouse
COPY requirements.lock ./requirements.lock
RUN python -m pip install \
      --no-index \
      --find-links=/wheelhouse \
      --require-hashes \
      --requirement requirements.lock \
    && rm -rf /wheelhouse requirements.lock

COPY --chown=10001:10001 app/ ./app/

USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]

CMD ["python", "-m", "app"]
```

This pattern is intended to do the following.

- Copy the dependency lock before the source to stabilize the cache boundary.
- Reject package artifacts absent from the lock with `--require-hashes`.
- Separate the build-time download stage from the runtime.
- Reduce differences in runtime user resolution with numeric UIDs and GIDs.
- Use exec-form `CMD` rather than shell form to simplify signal delivery.
- Have the health check verify an HTTP response rather than merely the existence of the service process.

In CI, pin the base by digest.

```bash
docker build \
  --pull \
  --build-arg 'PYTHON_IMAGE=python:3.12-slim@sha256:<REVIEWED_BASE_IMAGE_DIGEST>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

Replace `<...>` placeholders with values that have actually been reviewed. Digest pinning does not prevent updates; it makes changes visible in pull requests. When a base-image vulnerability fix is released, review an automated digest-update pull request and rebuild.

If native extensions must be compiled from source, install the compiler and headers in a builder stage and copy only the resulting wheels into the runtime. The compiler toolchain and OS package versions are also inputs, so include them within the scope of locking and provenance.

### A lock file represents exact artifacts, not ranges

A file containing only ranges like the following can select different results over time.

```text
framework>=1.0
client-library
```

A production lock pins versions and hashes through transitive dependencies, and an automated update tool creates a new lock that is then tested. Manually editing only part of the dependency tree can produce an inconsistent resolution.

The same principle applies to OS packages. Running `apt-get upgrade` on every build may be current, but it is not a reproducible input. Choose a policy that fits the system's requirements.

- Include the OS package set in a trusted base-image digest and update the base frequently.
- Use a package snapshot repository and exact versions.
- Use the organization's hardened base-image pipeline.

Vulnerability response is not a choice between “always latest” and “pinned forever.” It is a **process of periodically updating and validating pinned inputs**.

### Do not leave build secrets in layers and history

Avoid this form:

```dockerfile
ARG PACKAGE_TOKEN
ENV PACKAGE_TOKEN=${PACKAGE_TOKEN}
RUN python -m pip install --index-url "https://${PACKAGE_TOKEN}@<PRIVATE_INDEX>/simple" <PACKAGE>
```

Build arguments and environments can be exposed in image history, metadata, logs, and cache paths. Use a BuildKit secret mount and do not print the value within the instruction.

```dockerfile
RUN --mount=type=secret,id=package_token \
    PACKAGE_TOKEN="$(cat /run/secrets/package_token)" \
    python scripts/fetch_private_dependency.py
```

```bash
docker build \
  --secret id=package_token,src='<LOCAL_SECRET_FILE>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

The example script must also avoid leaving the token in URLs, exceptions, or debug logs. When possible, use a short-lived credential issued by the build service rather than a long-lived token.

### Run with a read-only filesystem and minimal capabilities

Add runtime policy to the image's non-root default.

```bash
docker run --rm \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL \
  --security-opt no-new-privileges=true \
  --memory 512m \
  --cpus 1.0 \
  --publish 127.0.0.1:8080:8080 \
  'service:<SOURCE_REVISION>'
```

If the service must write files, do not open the entire root filesystem. Explicitly mount only required locations such as `/tmp`, uploads, and caches. `--privileged`, host socket mounts, and host networking substantially weaken the isolation model and should not be used as convenience options.

Do not bake credentials into an image or ordinary environment file. Use the deployment platform's secret store and workload identity, and deliver secrets only to the process that needs them through memory or a restricted mount.

### Distinguish liveness from readiness in health checks

A Dockerfile `HEALTHCHECK` represents only one state. An orchestrator generally separates the following.

- **Startup**: Has initialization completed?
- **Liveness**: Is the process stuck badly enough that it must be restarted?
- **Readiness**: Can it accept new traffic now?

Strongly coupling readiness to every external dependency can remove every replica from traffic during a transient downstream failure and amplify a cascading outage. The endpoint should reflect the ability to handle real traffic, but an external failure that cannot be fixed by restarting should not become a liveness failure.

### Preserve evidence after building an image

The verification pipeline's output includes not only the image, but also the following.

- Source revision and build invocation
- Base-image and final-image digests
- SBOM
- Vulnerability-scan results and exception expiration dates
- Test results
- Build provenance and signatures or attestations

At deployment time, do not resolve the tag again; use the approved digest. Align registry-retention policy so that blobs referenced by the digest are not deleted before the deployment period ends.

## Verification Checklist

Before the build:

- [ ] `.dockerignore` excludes Git data, secrets, local caches, and unnecessary artifacts.
- [ ] Base images and language dependencies are locked to reviewed versions or digests and hashes.
- [ ] Lock updates undergo automated testing and vulnerability review.
- [ ] Build secrets are absent from `ARG`, `ENV`, URLs, and logs.
- [ ] Dependency manifests are copied before source code to establish the cache boundary.

Image review:

- [ ] The runtime image contains no compiler, package-manager cache, or test credentials.
- [ ] `USER` is non-root and uses fixed UID and GID values.
- [ ] The entry point can receive signals and shut down gracefully.
- [ ] The health check is fast, has a timeout, and causes no side effects.
- [ ] Layer contents, the SBOM, and vulnerabilities—not only image size—have been inspected.
- [ ] Multi-architecture images have been tested on each actual target architecture.

Runtime review:

- [ ] Deployment uses an immutable digest.
- [ ] The root filesystem is read-only and writable mounts are minimized.
- [ ] Capability removal, no-new-privileges, and a seccomp layer are applied.
- [ ] CPU, memory, and PID limits and a graceful-shutdown period are defined.
- [ ] Secrets are delivered from a runtime identity or secret store.
- [ ] The meanings of readiness, liveness, and startup probes are distinct.

## Failure Cases and Limitations

### Choosing Alpine based only on image size

Smaller size does not always mean lower risk or faster operations. Compare libc differences, lack of native wheels, DNS and time-zone behavior, and debugging difficulty. Choose the smallest base whose operational compatibility has been validated.

### Assuming a multi-stage build is automatically safe

Copying an entire filesystem into the final stage with something like `COPY --from=builder / /` brings build secrets and the toolchain back in. Copy only the required artifact paths.

### Performing authentication, writes, or heavy queries in a health check

Probes run frequently. A slow or state-changing probe becomes a source of failure itself. Check only essential readiness within a limited time.

### Treating scanner results as absolute judgments

Scanners depend on package inventories and advisory quality. Both false positives and undiscovered vulnerabilities are possible. Review reachable code, exploitability, and compensating controls, while assigning each exception an owner and expiration date.

### Trying to achieve all reproducibility through containers alone

External database schemas, feature flags, secret versions, hardware drivers, kernels, and network dependencies remain outside the image. Track deployment manifests, migrations, IaC, configuration versions, and data contracts as well.

A good Dockerfile is not merely a short file. It is a build contract that explains which inputs produced what, what is unnecessary at runtime, and under which privileges the result executes.

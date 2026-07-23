---
title: "Linux Diagnostics Fundamentals: Reading Processes, Files, Signals, and systemd as Evidence"
date: 2026-07-21 12:06:00 +0900
categories: [Linux, Operations]
tags: [linux, diagnostics, processes, signals, systemd]
description: A practical workflow for narrowing down Linux incidents using evidence from processes, descriptors, filesystems, signals, resources, and the systemd journal instead of starting with a restart.
lang: en
translation_key: linux-diagnostics-processes-files-signals-systemd
hidden: true
---
{% include language-switcher.html %}

## The problem: restarting erases the symptoms but does not explain the cause

When a Linux service is slow or unresponsive, restarting it immediately may restore it temporarily.

However, evidence from memory, descriptors, sockets, child processes, filesystems, and dependencies may disappear with it.

The following misconceptions delay diagnosis.

- Low CPU means the process is healthy.
- Low free memory must mean a memory shortage.
- If a file exists, it must be readable.
- `kill` means forced termination.
- If the service status is active, user-facing functionality must also be healthy.
- The last line of the log must be the cause.
- Running as root is an acceptable way to bypass permission problems.

Operational diagnosis should follow `observation -> hypothesis -> minimal check -> safe mitigation -> verification`.

## Mental model: a process is a bundle of kernel resources

A process is not merely an executable file.

It has the following.

- PID and parent PID
- User and group identity
- Virtual memory map
- Open file descriptor table
- Current working directory
- Environment
- Signal disposition
- Namespace and cgroup membership
- Threads and scheduling state

Replacing an executable file does not automatically change the memory mapping of a process that is already running.

A deleted file can continue occupying disk blocks while a descriptor to it remains open.

### `/proc` is a window into the running kernel

`/proc/<pid>/status` shows a status and memory overview.

`/proc/<pid>/fd` shows open descriptors.

`/proc/<pid>/maps` shows memory mappings.

`/proc/<pid>/limits` shows resource limits.

Permission and namespace boundaries apply even to reads.

### File descriptors do not point only to files

Regular files, directories, sockets, pipes, devices, and event objects can all be descriptors.

A descriptor leak may appear not only as a failure to open files, but also as a failure to establish new connections.

Check both per-process and system-wide limits.

### A signal is an asynchronous notification

`SIGTERM` is a catchable signal requesting graceful termination.

`SIGKILL` cannot be handled or ignored by a process.

Historically, `SIGHUP` means terminal disconnection, and some daemons use it to mean reload, but you must verify the application's contract.

Successful signal delivery and successful application cleanup are different things.

## Workflow: an order for narrowing down incidents

### Step 1. Pin down the user-visible symptom

- When did it begin?
- Does it affect every request or only a specific endpoint?
- Is it a timeout or an immediate error?
- Is it one host or the entire fleet?
- Were there recent deployment, configuration, certificate, or dependency changes?

Capture a UTC timestamp and correlation ID.

### Step 2. Check the service manager state

```bash
systemctl status example.service --no-pager
systemctl show example.service -p ActiveState -p SubState -p Result -p MainPID
journalctl -u example.service --since "-30 min" --no-pager
```

`active (running)` means little more than that the main process is alive.

It does not guarantee that business requests succeed.

Also inspect the unit's `ExecStart`, `User`, `WorkingDirectory`, `EnvironmentFile`, and restart policy.

### Step 3. Inspect the process tree and state

```bash
ps -eo pid,ppid,user,stat,etimes,%cpu,%mem,cmd --forest
```

The principal clues in `STAT` are as follows.

- `R`: running or runnable
- `S`: interruptible sleep
- `D`: uninterruptible sleep, usually waiting for I/O
- `T`: stopped or traced
- `Z`: zombie

A zombie is a child that has already exited but whose parent has not collected its exit status.

A zombie itself uses almost no memory, but a sustained increase is a sign of a parent bug.

### Step 4. Separate CPU from scheduler behavior

Load average is not the same as CPU utilization.

It may include runnable tasks and some uninterruptible tasks.

```bash
uptime
vmstat 1
pidstat -p <PID> 1
```

Examine user CPU, system CPU, I/O wait, and context switches together.

In a container, a cgroup quota may cause throttling.

Even if the host has CPU capacity remaining, the workload may still be constrained.

### Step 5. View memory by component

Linux uses spare memory as page cache.

Also look at the `available` estimate from `free`.

```bash
free -h
cat /proc/<PID>/status
cat /proc/<PID>/smaps_rollup
```

Distinguish RSS, virtual size, anonymous memory, file-backed mappings, and shared memory.

Check the kernel journal and cgroup events for evidence of an OOM kill.

```bash
journalctl -k --since "-1 hour" --no-pager
```

### Step 6. Check descriptors and sockets

```bash
ls -l /proc/<PID>/fd
cat /proc/<PID>/limits
ss -lntp
ss -antp
```

Compare the descriptor count trend with its limit.

See whether connection states are concentrated in `SYN-SENT`, `CLOSE-WAIT`, or `TIME-WAIT`.

Accumulating `CLOSE-WAIT` connections can indicate that the application is not closing sockets after the peer disconnects.

### Step 7. Separate filesystem capacity from inode capacity

```bash
df -h
df -i
findmnt
```

Inodes can be exhausted even when byte capacity remains.

An open, deleted file is absent from directory listings but still consumes space.

```bash
lsof +L1
```

Also check mount options, read-only remounts, and network filesystem latency.

### Step 8. Inspect permissions along the entire path

File mode alone is insufficient.

Traverse permission is required on every parent directory.

```bash
namei -l /path/to/resource
id example-user
getfacl /path/to/resource
```

If SELinux or AppArmor is in use, also check for MAC policy denials.

Running as root can obscure the cause and break permission boundaries.

### Step 9. Observe I/O and syscalls within a minimal scope

```bash
iostat -xz 1
strace -f -p <PID> -tt -T
```

`strace` can add overhead and expose sensitive data.

Use it briefly, filter to only the required syscalls, and follow operational policy.

Apply the same safety principles to `perf` and eBPF tools.

### Step 10. Shut down safely

First stop the service through the service manager.

```bash
systemctl stop example.service
```

If necessary, send SIGTERM and observe the state during the grace period.

SIGKILL is the last resort.

Before forced termination, capture the evidence you need, such as stacks, logs, descriptors, and core dump policy.

## How to read a systemd unit

### Dependency and ordering are different

`After=` defines start ordering, but does not automatically add a dependency requirement.

`Requires=` and `Wants=` express dependency relationships.

The network being `online` does not mean an application dependency is actually ready.

### Restart policy can conceal failures

`Restart=on-failure` helps recover from transient crashes.

However, a rapid crash loop can put pressure on dependencies.

Check the start rate limit and backoff.

Alert on repeated restart counts and the most recent exit reason.

### The execution environment differs from an interactive shell

PATH, working directory, environment, umask, and limits may differ.

Do not assume that a shell profile is loaded automatically.

Specify required paths in the unit file.

Do not expose secrets in the unit source or command line.

## Practical example: the service is active, but the API times out

1. Use a synthetic request to pin down the endpoint and timestamp.
2. Inspect MainPID and restart history with `systemctl show`.
3. Search the journal for timeouts and dependency errors at the same time.
4. Inspect outbound connection states with `ss`.
5. Compare the `/proc/<pid>/fd` count with its limit.
6. Inspect per-thread CPU and blocked states.
7. Send a bounded diagnostic request to the downstream endpoint.
8. Test the hypothesis that the thread pool or connection pool is exhausted.
9. Decide whether to restart after draining traffic.
10. After recovery, check the user SLI and resource metrics.

If you restarted, do not record it as resolving the root cause.

Record `symptoms mitigated by restart; cause unconfirmed` separately.

## Verification checklist

### Evidence preservation

- [ ] Recorded the symptom timestamp and scope of impact.
- [ ] Checked recent changes and the artifact version.
- [ ] Collected the journal and process state before restarting.
- [ ] Checked core dump and sensitive-information policies.
- [ ] Ensured command output did not include secrets.

### Processes and resources

- [ ] Checked the process tree and owner.
- [ ] Distinguished CPU, load, and I/O wait.
- [ ] Checked both host and cgroup limits.
- [ ] Checked memory composition and OOM events.
- [ ] Checked descriptors and socket states.
- [ ] Checked both disk bytes and inodes.

### Service operations

- [ ] The unit's execution user and environment are explicit.
- [ ] Tested graceful shutdown with SIGTERM.
- [ ] Restart storms are limited.
- [ ] Readiness is distinguished from process survival.
- [ ] Checked journal retention and time synchronization.
- [ ] Verified user-facing functionality after recovery.

## Common failures and limitations

### Starting with `kill -9`

This bypasses both cleanup and diagnostic hooks.

You must also consider the possibility of shared-state corruption.

### Looking only at host metrics

Containers and systemd services can exhaust resources within cgroup limits.

### Assuming that no log means no event occurred

Logs can be lost because of a crash before buffer flush, sampling, rate limits, or full storage.

Cross-check metrics, kernel events, and traces.

### Trying to remove a process in `D` state immediately with a signal

Signal handling may be delayed until the uninterruptible kernel wait is released.

Investigate the underlying I/O and device state.

### Running unbounded tracing in production

The diagnostic tool itself can create latency and disk problems.

Define the scope, duration, filters, and rollback before use.

## Official references

- [Linux man-pages Project](https://www.kernel.org/doc/man-pages/)
- [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html)
- [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)
- [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
- [The Linux Kernel cgroup v2 Documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)

## Conclusion

Linux diagnosis is not about memorizing commands; it is about reading the evidence exposed by the kernel at the correct boundaries.

Test hypotheses by connecting processes, descriptors, memory, filesystems, signals, cgroups, and the service manager.

Even when a restart is necessary, preserve evidence first and verify recovery through user-facing functionality to reduce repeat incidents.

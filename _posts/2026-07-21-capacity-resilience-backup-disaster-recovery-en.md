---
title: "Capacity, Resilience, and Disaster Recovery: From Load Tests to Backup Restores"
date: 2026-07-21 12:09:00 +0900
categories: [Reliability, Operations]
tags: [capacity-planning, resilience, backup, disaster-recovery, load-testing]
description: A unified verification framework connecting capacity planning, overload protection, resilience testing, backup restoration, RTO/RPO, and disaster recovery.
lang: en
translation_key: capacity-resilience-backup-disaster-recovery
mermaid: true
math: true
hidden: true
---
{% include language-switcher.html %}

## The problem: a successful backup and recoverability are different claims

Measuring performance only while a service is healthy tells you nothing about its behavior during a failure.

A green backup job status tells you nothing about whether the backup can actually be restored.

The following risks are often hidden.

- Average load is low, but a short burst overwhelms the queue.
- The latency SLO is violated before autoscaling begins.
- Retries create more load than the original traffic.
- After failover, the remaining zones lack sufficient capacity.
- A backup exists, but its encryption key and IAM configuration cannot be recovered.
- The database was restored, but the application schema does not match.
- The DR runbook exists only in one person's memory.

Resilience is not the number of replicas. It is evidence that functionality and data were recovered within the permitted time after a failure.

## Mental model: normal load, overload, failure, and disaster form a continuum

```mermaid
flowchart LR
    N[Normal] --> P[Peak]
    P --> O[Overload]
    O --> F[Component Failure]
    F --> D[Site or Region Disaster]
    D --> R[Recovery]
    R --> N
```

### Capacity is not a single number for a single resource

End-to-end throughput is limited by the first constraint to saturate.

- CPU
- Memory
- Connection pool
- Thread or worker
- Network bandwidth
- Storage IOPS and throughput
- Queue partition
- Database lock
- External API quota

### Use Little's Law to build queue intuition

In a steady state, the relationship between the average number of concurrent jobs $L$, arrival rate $\lambda$, and average time in the system $W$ is as follows.

$$
L = \lambda W
$$

If the arrival rate remains above the processing rate, the backlog continues to grow.

Even with autoscaling, you must calculate how much accumulates during the scale-out delay.

### Distinguish RTO from RPO

- **RTO**: the maximum time allowed to restore the service after a failure
- **RPO**: the acceptable point-in-time range of data loss during recovery

They may differ by dataset and functionality.

Requiring RPO 0 and immediate RTO for every system causes cost and complexity to surge.

## Workflow: establish a capacity baseline

### Step 1. Record the workload model

- Proportion of each request type
- Payload size distribution
- Read/write ratio
- Cache hit ratio
- User think time
- Overlap between batch and interactive traffic
- External dependency latency
- Growth and seasonality

A test that repeats one average user does not reproduce real-world skew.

### Step 2. Select representative SLIs

- Throughput
- Latency percentiles
- Error rate
- Queue age
- Saturation
- Number of successful business transactions
- Data correctness

Average latency hides tail problems, so inspect percentiles.

To avoid coordinated omission, also verify that the load generator does not stop producing new requests because of slow responses.

### Step 3. Separate baseline and limit tests

A baseline test examines stability at the normal target load.

A stress test identifies the knee point and failure modes.

A spike test examines sudden bursts.

A soak test examines leaks and cumulative problems.

A breakpoint test finds limits in a safely isolated environment.

### Step 4. Verify the autoscaling loop

Add together metrics collection delay, the evaluation window, provisioning time, and warm-up time.

Check that the scale-out trigger is not too late relative to the user SLO.

Review connection draining and cache loss during scale-in.

Align the maximum instance count with downstream capacity.

### Step 5. Add admission control

Explicitly rejecting requests a system cannot handle may support recovery better than placing them in an unbounded queue.

Use per-tenant quotas, concurrency limits, bounded queues, deadlines, and priorities.

Preserve critical traffic.

Give retries a separate budget.

## Workflow: design resilience and DR

### Step 6. Inventory failure modes

- Process crash
- Node loss
- Zone loss
- Dependency timeout
- DNS or identity failure
- Data corruption
- Accidental deletion
- Credential compromise
- Loss of a region or site
- Operator error

Assign owners for detection, containment, recovery, and verification for each mode.

### Step 7. Verify the independence of redundancy

Multiple replicas may share the same zone, account, credentials, deployment, or configuration.

Mark common causes on the architecture map.

Regularly verify that real traffic can be sent to the failover target.

An idle standby is prone to patch and configuration drift.

### Step 8. Choose backup types and retention

- Full, incremental, and differential
- Snapshot and logical dump
- Transaction log or point-in-time recovery
- Application-consistent backup
- Immutable or write-protected copy
- Cross-account or off-site copy

The 3-2-1 rule is a useful starting point, but adapt it to the threat model and regulatory requirements.

The backup itself must be isolated from ransomware and credential compromise.

### Step 9. Preserve recovery dependencies together

Data alone cannot restore an application.

- IaC and images
- Schema migrations
- Configuration
- Encryption keys and certificates
- IAM bootstrap
- DNS and domain control
- Observability
- Runbooks and contacts
- License or external integration information

Design a recoverable management system without placing secret bytes directly in documents.

### Step 10. Test restoration in an isolated environment

1. Select a specific recovery point.
2. Create infrastructure in a clean account or namespace.
3. Bootstrap keys and permissions.
4. Restore the backup.
5. Align schema and application versions.
6. Verify integrity and business invariants.
7. Perform a synthetic transaction.
8. Record the actual RTO and RPO.
9. Safely clean up the temporary environment and sensitive copies.

### Step 11. Distinguish failover from failback

Failback to the original site after successful failover has its own risks.

Decide how to merge writes generated on both sides.

Fencing and authority transfer are needed to prevent split-brain.

DNS TTL, client caches, and connection reuse may keep traffic switching from completing immediately.

### Step 12. Set recovery priorities by service tier

Do not try to restore every function at once.

- Identity and control plane
- Core read path
- Core write path
- Asynchronous processing
- Reporting and batch
- Noncritical functions

Set the order based on the dependency graph and business impact.

## Practical example: testing the loss of one zone

### Hypothesis

Even if one zone disappears, the core API SLO remains within a bounded level of degradation.

### Preconditions

- Check reservations and quotas in the remaining zones
- Verify database failover behavior
- Check PDB and placement
- Define the abort threshold for customer impact
- Assign rollback and observers

### Execution

1. Record the baseline with canary traffic.
2. Inject the selected failure into a small scope.
3. Observe request routing and replica relocation.
4. Observe retries and queue age.
5. Observe database connection reestablishment.
6. Compare the SLO with the abort threshold.
7. Restore the healthy state.
8. Check data invariants and backlog drain.

### Results

Record actual detection time, failover time, peak error, recovery time, and manual actions instead of a simple pass/fail.

## Practical example: point-in-time restore

Choose a hypothetical time for an erroneous deletion.

Restore the database to a recovery point just before the incident.

Restore to a new instance rather than overwriting the original.

Compare the deleted data with valid writes that occurred afterward.

Create a correction plan that reapplies only the necessary records.

Have the business owner approve whether all data may be rolled back to a single point in time.

After recovery, rebuild the search index, cache, and derived tables.

## Verification checklist

### Capacity

- [ ] The workload mix and peak reflect real traffic.
- [ ] Percentile latency and saturation are examined together.
- [ ] Retry traffic is included in the load model.
- [ ] Autoscaling delay and warm-up were measured.
- [ ] Admission control operates before downstream limits are reached.
- [ ] Remaining capacity after zone loss was verified.

### Backup

- [ ] RPO and retention are defined for each dataset.
- [ ] Backup copies are isolated from production credentials.
- [ ] Encryption-key recovery was tested.
- [ ] Alerts exist for backup failures and age.
- [ ] Both deletion and corruption scenarios were tested.
- [ ] Business invariants of restored results are verified.

### DR

- [ ] RTO and recovery order are defined for each tier.
- [ ] DNS, identity, and observability are included in the plan.
- [ ] Another operator can execute the runbook.
- [ ] Failover authority and fencing are explicit.
- [ ] Failback and data reconciliation were tested.
- [ ] Actual exercise time is recorded and compared with the target.

## Common failures and limitations

### Turning a load test into a competition for the highest production number

The goal is not to boast about a number, but to find the knee point and a safe operating range.

### Believing autoscaling replaces capacity planning

Quotas, provisioning delay, stateful bottlenecks, and downstream limits remain.

### Treating replication as backup

Deletion and corruption can also be replicated rapidly.

An independent recovery point is necessary.

### Recording a successful snapshot restore as service recovery

Application connectivity, schema, keys, and business transaction verification are missing.

### Writing DR documentation without exercising it

Dependencies, permissions, contacts, and commands change over time.

Regular rehearsals keep the document valid.

## Official references

- [AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- [Google SRE Book: Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [NIST SP 800-34 Rev. 1 Contingency Planning Guide](https://csrc.nist.gov/pubs/sp/800/34/r1/final)
- [PostgreSQL Backup and Restore](https://www.postgresql.org/docs/current/backup.html)

## Conclusion

Capacity and disaster recovery are not separate documents, but different scales of the same reliability question.

Measure limits under normal load, constrain overload, inject failures, and actually restore backups.

Recoverability is demonstrated not by an architecture diagram, but by repeatable restores and records verifying user-facing functionality.

---
title: "Contract-First API Design: Errors, Versions, Idempotency, and Asynchronous Jobs"
date: 2026-07-21 10:30:00 +0900
categories: [Software Engineering, API Design]
tags: [api, openapi, idempotency, schema, pagination, versioning]
description: Treat an API as a long-lived, evolving contract rather than a collection of functions, and design its requests, responses, errors, retries, and versions accordingly.
lang: en
translation_key: api-contract-idempotency
hidden: true
---

{% include language-switcher.html %}

API quality should be judged not by the number of endpoints, but by **whether callers can predict success, failure, and retries**. Server implementations change, but contracts persist across multiple clients and automation systems.

## A Contract Is Broader Than a Successful Response

At minimum, the contract for one operation includes the following.

- Method and path
- Authentication and authorization requirements
- Path, query, header, and body schemas
- Units, time zones, ranges, and nullable rules
- Success status codes and response schemas
- Error codes and retryability
- Idempotency and concurrency rules
- Rate limits and pagination
- Timeouts or asynchronous-processing methods

A machine-readable specification such as OpenAPI is not merely a file for generating documentation. It is the reference point connecting schema validation, client generation, contract tests, and breaking-change checks.

## Distinguish Resources from Jobs

Noun-based resources represent state, while HTTP methods express intent.

```text
GET    /v1/jobs/{job_id}
POST   /v1/jobs
PATCH  /v1/jobs/{job_id}
DELETE /v1/jobs/{job_id}
```

Do not keep a synchronous HTTP connection open until a job that takes minutes has finished.

1. `POST /v1/jobs` validates the input and registers a job.
2. The server returns `202 Accepted`, a `job_id`, and a status URL.
3. The client polls the status or receives a webhook or event.
4. States are made explicit, for example `queued → running → succeeded | failed | cancelled`.

State transitions should be unidirectional and distinguish the reason for failure from whether the job can be retried.

## Validate Input Strictly at the Boundary

```yaml
components:
  schemas:
    CreateJobRequest:
      type: object
      additionalProperties: false
      required: [source_uri, mode]
      properties:
        source_uri:
          type: string
          format: uri
        mode:
          type: string
          enum: [quick, full]
```

The policy, not the YAML syntax, is what matters.

- Decide whether to reject or ignore unknown fields.
- Distinguish omission from an explicit `null`.
- Reflect numeric units and permitted ranges in names, descriptions, and validation.
- Exchange time in a standard format that includes an offset, and define the internal reference.
- When adding an enum value, consider how older clients will respond.

## Errors Also Have a Stable Schema

Returning only a human-readable sentence forces the client to parse text.

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "The request failed validation.",
    "details": [
      {"field": "mode", "reason": "unsupported_value"}
    ],
    "request_id": "req-example",
    "retryable": false
  }
}
```

- `code` is a stable identifier for machine branching.
- `message` is read by users or operators.
- `details` structures field-level problems.
- `request_id` connects support cases with traces.
- Do not return internal stack traces, SQL, paths, or secrets externally.

## POST Retries Need an Idempotency Key

If the connection breaks after a client sends a request but before it receives the response, the client cannot know whether the job was created. Unconditionally sending the POST again can create a duplicate.

```text
Idempotency-Key: client-generated-unique-key
```

The basic server flow is as follows.

1. Look up an existing record by the combination of authenticated principal and key.
2. On the first request, store the result together with a normalized hash of the request body.
3. For the same key and same body, return the stored result.
4. For the same key and a different body, reject the request as a conflict.
5. Document the retention period and concurrent-request handling rules.

Using only an application-level “check first” without a database unique constraint creates a race condition.

## Concurrent Modifications Need Conditional Requests

If two users read and modify the same resource, the later write can overwrite the earlier change. Optimistic concurrency using a version number or `ETag` is a common solution.

```text
GET /v1/items/42
ETag: "version-7"

PATCH /v1/items/42
If-Match: "version-7"
```

If the version has changed, the server reports a conflict so the client can reread the latest state.

## Pagination Must Tolerate Data Changes

Do not return a large list all at once. Offset pagination is simple, but insertions or deletions near the front can cause duplicates or omissions. For large, frequently changing lists, cursor pagination based on a stable sort key is more suitable.

```json
{
  "items": [],
  "next_cursor": "opaque-cursor",
  "has_more": false
}
```

Treat the cursor as opaque, and include the sort order, maximum page size, and rules for combining filters and cursors in the contract.

## Versioning Is a Change Policy, Not a Last Resort

Classify changes into three types.

- Compatible: adding an optional field or new endpoint
- Conditionally compatible: adding an enum value or loosening a restriction
- Incompatible: removing a field or changing its type or meaning

Move incompatible changes to an explicit new version or parallel operation. Manage deprecation notices, observation periods, client usage, and retirement schedules together. Adding a version number to the URL does not complete change management.

## Contract Tests and Deployment Gates

- Validate the specification.
- Test that server responses conform to the specification.
- Verify that representative clients can be generated and compiled from the new specification.
- Check for breaking changes relative to the previous version.
- Test missing authentication, insufficient authorization, rate limits, and validation errors.
- Test concurrent requests with the same idempotency key.
- Smoke-test critical endpoints after deployment.

## Verification Checklist

- [ ] Error schemas as well as request and response schemas are specified.
- [ ] Policies for units, time zones, nullable values, and enum extension are clear.
- [ ] A duplicate-prevention strategy exists for side-effecting POST requests.
- [ ] Long-running work is separated into a status resource.
- [ ] Lost updates from concurrent modifications are prevented.
- [ ] Pagination ordering is deterministic and cursors are opaque.
- [ ] CI includes incompatible-change detection.
- [ ] Stack traces and internal implementation details are not exposed in external errors.

## Common Failures

- Returning every result as `200 OK` with free-form JSON
- Failing to distinguish retryable errors from permanent errors
- Creating jobs after a client timeout without preventing duplicates
- Using different units or time zones for the same field across endpoints
- Removing a response field and “only updating the documentation”
- Omitting data when it changes during offset pagination

A good API hides implementation details while **specifying enough behavior for callers to fail and retry safely**.

## References

- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)

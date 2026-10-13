---
category: upstream_rate_limit
title: Upstream API rate limiting
---
# Upstream API rate limiting

## Symptoms
HTTP 429 Too Many Requests, "quota exceeded", retry-after headers from an external or shared API. Often starts after a batch job, a re-run or a retry storm.

## Likely causes
Request volume above the agreed quota; retries without backoff; a batch job sharing the same quota as live traffic.

## Checks
Correlate 429s with batch jobs or traffic changes. Check the quota and current usage with the provider. Review retry and backoff settings.

## Mitigation (human decision)
Pause or throttle the batch; honour retry-after with backoff; separate batch and live quotas.

---
category: dependency_timeout
title: Slow downstream dependency
---
# Slow downstream dependency

## Symptoms
"timed out after ...ms" when calling a specific downstream; circuit breaker OPEN; the downstream's own latency well above normal. The caller's errors follow the downstream's latency.

## Likely causes
The dependency is degraded (resource saturation, its own dependency, a bad deploy); timeouts or retries in the caller amplify load.

## Checks
Compare the downstream's latency to its baseline. Check its saturation and recent changes. Confirm caller timeout and retry settings are not causing a retry storm.

## Mitigation (human decision)
Engage the dependency's owners; shed or degrade gracefully (fallback, cached result); keep the breaker open rather than retrying harder.

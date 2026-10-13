---
category: credential_rotation
title: Credential rotation mismatch
---
# Credential rotation mismatch

## Symptoms
"password authentication failed", "invalid credentials", 401/403 from a dependency right after a secret was rotated. Connections that were open keep working until they are recycled, then fail.

## Likely causes
The consumer caches the old secret and was not restarted or reloaded; the rotation updated one store but not the one the app reads.

## Checks
Line up the rotation event with the first auth failure. Confirm which secret version the app has mounted. Check whether the app supports hot reload of credentials.

## Mitigation (human decision)
Restart or reload the consumer so it picks up the new secret, or temporarily restore the previous version with security's agreement.

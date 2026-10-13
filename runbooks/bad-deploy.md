---
category: bad_deploy
title: Regression after a deployment
---
# Regression after a deployment

## Symptoms
Errors (unhandled exceptions, 500s) begin within minutes of a rollout completing, often tagged with the new version or revision. The previous revision had a low baseline error rate.

## Likely causes
A code change, removed default, schema mismatch or configuration change shipped in the new version.

## Checks
Line up the error start time with the rollout timeline. Confirm errors carry the new version. Diff the release for the failing code path. Check whether only some replicas or regions run the new version.

## Mitigation (human decision)
Roll back to the previous revision or pause the rollout; then fix forward with a test covering the failing case.

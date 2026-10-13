---
category: oom_kill
title: OOMKilled containers and memory leaks
---
# OOMKilled containers and memory leaks

## Symptoms
Kubelet reports a container exited with OOMKilled (exit code 137); pods in CrashLoopBackOff; memory or heap usage climbing steadily toward the container limit before each restart.

## Likely causes
A memory leak such as an unbounded cache; a limit set below real working-set needs; a traffic pattern that loads much more data per request.

## Checks
Graph container working-set memory against the limit across restarts. Look for growing object counts (cache entries, queues). Take a heap profile on a non-production replica.

## Mitigation (human decision)
Bound the cache or fix the leak; temporarily raise the limit only with capacity headroom; roll back if a recent change introduced the growth.

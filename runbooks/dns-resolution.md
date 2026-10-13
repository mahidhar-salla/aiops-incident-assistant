---
category: dns_failure
title: DNS resolution failures
---
# DNS resolution failures

## Symptoms
"lookup <host> ... i/o timeout", "no such host", SERVFAIL, or coredns logs reporting "no healthy upstreams". Several unrelated services fail at once when calling hosts by name.

## Likely causes
Cluster DNS cannot reach its upstream resolver; coredns pods overloaded or crashlooping; a bad change to DNS zones or forwarding config; network policy blocking UDP/TCP 53.

## Checks
Check coredns pod health and logs. Resolve the failing name from a debug pod. Test the upstream resolver directly. Review recent DNS or network policy changes.

## Mitigation (human decision)
Restore upstream reachability or fail over to a secondary resolver; scale coredns if overloaded; revert a bad config change.

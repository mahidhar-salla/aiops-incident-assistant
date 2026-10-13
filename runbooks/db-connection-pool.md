---
category: db_pool_exhaustion
title: Database connection pool exhaustion
---
# Database connection pool exhaustion

## Symptoms
Application logs show "Connection is not available, request timed out", "connection pool exhausted" or pool stats with active equal to the maximum and idle=0 with many waiting threads. Latency rises first, then 5xx errors as requests time out waiting for a connection. Callers see 503s or timeouts.

## Likely causes
Slow queries or long transactions holding connections; a traffic spike beyond pool size; connection leaks where code paths never return connections; pool max set far below what the database allows.

## Checks
Compare pool active/idle/waiting over time. Look for slow queries and long-running transactions on the database. Check whether a recent deploy changed query patterns or transaction scope. Confirm the database itself has spare max_connections.

## Mitigation (human decision)
Scale out the service only if the database has headroom. Kill runaway queries with DBA agreement. Roll back a deploy that introduced leaks. Do not raise pool size blindly; it can overload the database.

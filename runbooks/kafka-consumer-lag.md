---
category: kafka_consumer_lag
title: Kafka consumer lag
---
# Kafka consumer lag

## Symptoms
Consumer group lag growing on a topic; "poll timeout has expired", "max.poll.interval.ms" exceeded; repeated group rebalancing; downstream processing (for example notifications) delayed.

## Likely causes
Per-batch processing too slow for max.poll.interval.ms, causing members to leave and rebalance; too few consumers or partitions; a slow downstream call inside the consumer loop.

## Checks
Plot lag per partition and the rebalance rate. Compare batch processing time to max.poll.interval.ms. Look for slow calls inside the processing loop.

## Mitigation (human decision)
Reduce max.poll.records or speed up processing; scale consumers up to the partition count; fix the slow dependency.

---
category: disk_full
title: Disk or volume full
---
# Disk or volume full

## Symptoms
"no space left on device", "Errno 28", filesystem avail=0B or 100% used. Writes and jobs fail while reads may still work.

## Likely causes
Temp or log files not rotated or cleaned up; unexpected data growth; a volume sized too small.

## Checks
Find the largest directories on the volume. Check log rotation and temp-file cleanup jobs. Review the filesystem usage trend to see if this was gradual or sudden.

## Mitigation (human decision)
Free space by removing files that are confirmed safe to delete; expand the volume; fix the cleanup job so it does not recur.

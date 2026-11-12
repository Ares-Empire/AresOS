The incomplete-scan closure finding is fixed. Closure now requires matching FETCH UID, body literal and hash evidence, even when `SCAN_RESULT.accepted` falsely claims success.

No new problems found in the scoped changes.

Validation: 34 unit tests and eight in-memory scan probes passed. No files edited or containers run.

SAFE
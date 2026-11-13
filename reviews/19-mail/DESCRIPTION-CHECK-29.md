# Description check after round 29 of brief 19 (Mail)

Reviewer: Codex `gpt-6-luna`, high, read-only, fresh context, 2026-11-09. Reviewed `4fc165eb..d3babf1f` (the duplicate-warning description fix only). Run by the lead; saved by the lead.

Reviewed `4fc165eb..d3babf1f`. In `control/`, only the two Mail tool descriptions in `definitions.py` and their generated copy in `mail-tools.json` changed. `python3 control/generate.py --check` passed: “Generated artifacts match definitions.”

The wording matches the implementation: matching Sent-copy references are fingerprinted; unchanged evidence reuses the occurrence, while changed evidence creates a new one. Acknowledgement applies to that notice occurrence. “Acknowledging” refers to the warning, not approving or sending mail. The descriptions retain the relevant limits: status never resubmits, and repair never invokes SMTP.

SAFE
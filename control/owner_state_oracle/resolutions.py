"""The only ways a committed claim may discharge an owner obligation.

The caller supplies independently computed proofs, never the claimed row flag.
Missing kinds and missing proofs fail closed. Keep FORMAT.md's table in sync.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Resolution:
    proofs: tuple
    ends: tuple


RESOLUTIONS = {
    'acknowledgement': Resolution(('scripted_identity', 'commit_order'), ('occurrence', 'operation_notice', 'intent')),
    'submission': Resolution(('scripted_approval', 'commit_order'), ('cancel_hold',)),
    'completion': Resolution(('scripted_approval', 'required_effects', 'commit_order'), ('work', 'operation', 'cancel_hold', 'settle_hold')),
    'failure': Resolution(('fault_or_negative_reply', 'commit_order'), ('work', 'operation', 'cancel_hold', 'settle_hold')),
    'uncertainty': Resolution(('attempt_or_fault', 'commit_order'), ('cancel_hold',)),
    'clean_check': Resolution(('clean_server_result', 'commit_order'), ('check', 'unchecked')),
    'check_result': Resolution(('server_result', 'commit_order'), ('check', 'unchecked')),
    'cancellation': Resolution(('scripted_identity', 'reserved', 'commit_order'), ('work', 'cancel_hold')),
    'expiry': Resolution(('scripted_clock', 'reserved', 'commit_order'), ('work', 'cancel_hold')),
    'settlement': Resolution(('scripted_identity', 'read_only_evidence', 'commit_order'), ('work', 'operation', 'settle_hold')),
    'restore': Resolution(('scripted_confirmation', 'rollback_interval', 'commit_order'), ('cancel_hold',)),
    'restore_invalidation': Resolution(('scripted_confirmation', 'prior_reserved', 'no_effect', 'commit_order'), ('work', 'cancel_hold')),
    'archive': Resolution(('scripted_archive', 'no_obligation', 'qualified_manifest', 'commit_order'), ()),
    'onboarding_completion': Resolution(('scripted_account', 'delivered_probe', 'commit_order'), ('account',)),
    'intent_completion': Resolution(('scripted_action', 'required_effects', 'commit_order'), ('intent',)),
    'export_publication': Resolution(('scripted_export', 'publication_or_fault', 'commit_order'), ('export', 'export_hold')),
}


def permitted(kind, proofs):
    return kind in RESOLUTIONS and all(proofs.get(name) is True for name in RESOLUTIONS[kind].proofs)

import tempfile
import unittest
from pathlib import Path
from review_queue import build_review_queue, stable_review_id
from review_decisions import apply_decisions, record_decision


class LegacyReviewDecisionTests(unittest.TestCase):
    def test_exact_legacy_evidence_survives_id_upgrade(self):
        ref = '1_0_1_2_3_4_5_6_7_8'
        sha = 'a' * 64
        match = {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': ref, 'candidate_sha256': sha,
                 'candidate_source': 'C:/work/logo.png'}
        item = build_review_queue({}, {}, [], [match])['items'][0]
        legacy = dict(item, review_id=stable_review_id('REGISTRY_MATCH', ref, sha))
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / 'decisions.json'
            record_decision(ledger, legacy, 'APPROVED_FOR_REVIEW', 'Reviewed', True)
            upgraded = apply_decisions({'items': [item]}, ledger)['items'][0]
            self.assertEqual(upgraded['decision'], 'APPROVED_FOR_REVIEW')

    def test_changed_reason_cannot_reuse_legacy_approval(self):
        ref = '1_0_1_2_3_4_5_6_7_8'
        sha = 'b' * 64
        match = {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': ref, 'candidate_sha256': sha,
                 'candidate_source': 'C:/work/logo.png'}
        item = build_review_queue({}, {}, [], [match])['items'][0]
        legacy = dict(item, review_id=stable_review_id('REGISTRY_MATCH', ref, sha))
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / 'decisions.json'
            record_decision(ledger, legacy, 'APPROVED_FOR_REVIEW', 'Reviewed', True)
            changed = dict(item, reasons=['IDENTITY_REQUIRES_VERIFICATION'])
            self.assertEqual(apply_decisions({'items': [changed]}, ledger)['items'][0]['decision'], 'PENDING')


if __name__ == '__main__':
    unittest.main()

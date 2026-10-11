import tempfile
import unittest
import hashlib
import json
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

    def test_existing_11_app_ledger_is_read_only_fallback_and_canonical_wins(self):
        match = {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': '1_0_1_2_3_4_5_6_7_8', 'candidate_sha256': 'c' * 64,
                 'candidate_source': 'fixture/logo.png'}
        item = build_review_queue({}, {}, [], [match])['items'][0]
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            legacy = root / '11-APP' / '.factory-data' / 'review-decisions.json'
            canonical = root / '05-QA' / 'review-decisions.json'
            record_decision(legacy, item, 'DEFERRED', 'legacy', True)
            legacy_sha = hashlib.sha256(legacy.read_bytes()).hexdigest()
            resumed = apply_decisions({'items': [item]}, canonical, legacy)['items'][0]
            self.assertEqual(resumed['decision'], 'DEFERRED')
            record_decision(canonical, item, 'REJECTED', 'new explicit choice', True)
            resumed = apply_decisions({'items': [item]}, canonical, legacy)['items'][0]
            self.assertEqual(resumed['decision'], 'REJECTED')
            self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(), legacy_sha)
            self.assertEqual(json.loads(legacy.read_text())['decisions'][item['review_id']]['decision'], 'DEFERRED')


if __name__ == '__main__':
    unittest.main()

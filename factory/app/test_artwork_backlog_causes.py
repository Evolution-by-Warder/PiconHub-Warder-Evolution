import unittest
from qa_backlog_diagnostics import explain_review_backlog


class ArtworkBacklogCausesTests(unittest.TestCase):
    def test_separates_single_and_multi_artwork_without_approving(self):
        items = [
            {'review_id':'WR-SINGLE','workstream':'ARTWORK_REVIEW','category':'REGISTRY_MATCH',
             'decision':'PENDING','candidate_identity':'ref1','sha256':'a'*64,
             'source_origin':'openatv8','reasons':['EXISTING_SERVICE_DIFFERENT_ART']},
            {'review_id':'WR-MULTI','workstream':'ARTWORK_REVIEW','category':'REGISTRY_MATCH',
             'decision':'PENDING','candidate_identity':'ref2','sha256':None,
             'distinct_sha256':2,'source_origins':['openatv8','vhannibal'],
             'source_evidence':[{'sha256':'b'*64},{'sha256':'c'*64}],
             'reasons':['EXISTING_SERVICE_DIFFERENT_ART']},
            {'review_id':'WR-APPROVED','workstream':'ARTWORK_REVIEW','category':'REGISTRY_MATCH',
             'decision':'APPROVED_FOR_REVIEW','candidate_identity':'ref3','sha256':'d'*64},
        ]
        result = explain_review_backlog({'items':items})
        causes=result['artwork_review_subcauses']
        self.assertEqual(causes['SINGLE_CANDIDATE_ARTWORK_DIFFERS_FROM_MASTER'],1)
        self.assertEqual(causes['MULTIPLE_CANDIDATE_ARTWORKS_SAME_REFERENCE'],1)
        self.assertEqual(result['artwork_review_by_source']['vhannibal']['MULTIPLE_CANDIDATE_ARTWORKS_SAME_REFERENCE'],1)
        self.assertEqual(result['pending_review_tasks'],2)
        self.assertEqual(items[0]['decision'],'PENDING')

if __name__ == '__main__':
    unittest.main()

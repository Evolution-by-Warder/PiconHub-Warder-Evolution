import unittest
from review_queue import build_review_queue, _proven_openatv_style_only, _proven_openatv_style_only


class CrossFeedReviewGroupingTests(unittest.TestCase):
    def test_verified_style_only_suppression_retains_all_evidence(self):
        dark='f044684c32c051eb692305411225715b0c362f0bcae05c70eb3d155c1932022e'
        light='162117cf31343e0a153b4fd5297c6545b13a85833f1481d5d9e02fbcad9435de'
        styles={dark:('srp','dark'),light:('srp','light')}
        collision={'candidate_service_ref':'1_0_1_2_3_4_5_6_7_8','variants':[
            {'sha256':'a'*64,'sources':[rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\{dark}\\picon\\a.png']},
            {'sha256':'b'*64,'sources':[rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\{light}\\picon\\a.png']},
        ]}
        self.assertTrue(_proven_openatv_style_only(collision,styles))
        queue=build_review_queue({}, {}, [collision], package_styles=styles)
        self.assertEqual(queue['count'],0)
        self.assertEqual(queue['consolidation']['openatv_style_only_identity_tasks_avoided'],1)
        evidence=queue['suppressed_identity_reviews'][0]
        self.assertEqual(evidence['identity_approval'],'NONE')
        self.assertEqual(len(evidence['variants']),2)
        self.assertEqual(sum(len(v['sources']) for v in evidence['verified_provenance']),2)

    def test_different_openatv_formats_are_not_suppressed(self):
        dark='f044684c32c051eb692305411225715b0c362f0bcae05c70eb3d155c1932022e'
        light='162117cf31343e0a153b4fd5297c6545b13a85833f1481d5d9e02fbcad9435de'
        styles={dark:('srp','dark'),light:('utf8snp','light')}
        collision={'candidate_service_ref':'1_0_1_2_3_4_5_6_7_8','variants':[
            {'sha256':'a'*64,'sources':[rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\{dark}\\picon\\a.png']},
            {'sha256':'b'*64,'sources':[rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\{light}\\picon\\a.png']},
        ]}
        queue=build_review_queue({}, {}, [collision], package_styles=styles)
        self.assertEqual(queue['count'],1)
        self.assertEqual(queue['items'][0]['decision'],'PENDING')
        self.assertEqual(queue['consolidation']['openatv_style_only_identity_tasks_avoided'],0)

    def test_unknown_provenance_keeps_collision_pending(self):
        known='f044684c32c051eb692305411225715b0c362f0bcae05c70eb3d155c1932022e'
        styles={known:('srp','dark')}
        collision={'candidate_service_ref':'1_0_1_2_3_4_5_6_7_8','variants':[
            {'sha256':'a'*64,'sources':[rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\{known}\\picon\\a.png']},
            {'sha256':'b'*64,'sources':[r'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\'+'e'*64+r'\\picon\\b.png']},
        ]}
        queue=build_review_queue({}, {}, [collision], package_styles=styles)
        self.assertEqual(queue['count'],1)
        self.assertEqual(queue['items'][0]['decision'],'PENDING')
        self.assertEqual(queue['consolidation']['openatv_style_only_identity_tasks_avoided'],0)

    def test_windows_source_provenance_is_case_insensitive(self):
        rows = [
            {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
             'service_reference': 'service-a', 'candidate_sha256': 'a' * 64,
             'candidate_source': r'D:\\SOURCE-INGEST\\ORIGINALS\\OpenATV8\\a.png'},
            {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
             'service_reference': 'service-a', 'candidate_sha256': 'b' * 64,
             'candidate_source': r'D:\\source-ingest\\originals\\OPENATV8\\b.png'},
        ]
        result = build_review_queue({}, {}, [], rows)
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['items'][0]['source_origins'], ['openatv8'])
        self.assertEqual(result['items'][0]['source_origin'], 'openatv8')


    def test_same_service_and_reason_across_feeds_is_one_review(self):
        rows = [
            {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
             'service_reference': '1_0_1_2_3_4_5_6_7_8',
             'candidate_sha256': 'a'*64,
             'candidate_source': r'C:\\source-ingest\\originals\\openatv8\\a.png'},
            {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
             'service_reference': '1_0_1_2_3_4_5_6_7_8',
             'candidate_sha256': 'b'*64,
             'candidate_source': r'C:\\source-ingest\\originals\\vhannibal\\b.png'},
        ]
        result = build_review_queue({}, {}, [], rows)
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['consolidation']['registry_sha_reviews_before_grouping'], 2)
        self.assertEqual(result['consolidation']['registry_review_tasks_after_grouping'], 1)
        self.assertEqual(result['consolidation']['review_tasks_avoided'], 1)
        item = result['items'][0]
        self.assertEqual(item['distinct_sha256'], 2)
        self.assertEqual(item['source_observations'], 2)
        self.assertEqual(len(item['source_evidence']), 2)
        self.assertEqual(item['decision'], 'PENDING')

    def test_pixel_identical_sha_variants_keep_pending_review_and_audit(self):
        rows = [{'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': 'service-a', 'candidate_sha256': sha * 64,
                 'candidate_source': sha + '.png'} for sha in ('a', 'b', 'c')]
        pixels = {'a' * 64: 'pixel-x', 'b' * 64: 'pixel-x', 'c' * 64: 'pixel-y'}
        result = build_review_queue({}, {}, [], rows, pixel_digests=pixels)
        self.assertEqual(result['count'], 1)
        item = result['items'][0]
        self.assertEqual(item['decision'], 'PENDING')
        self.assertEqual(item['distinct_sha256'], 3)
        self.assertEqual(item['distinct_pixel_artworks'], 2)
        self.assertEqual(item['pixel_grouping'], 'VERIFIED_RGBA_GROUPS')
        self.assertEqual(item['review_priority'], 'P2_COMPARE_DISTINCT_PIXEL_ARTWORKS')
        self.assertNotIn('pixel_equivalence', item)
        self.assertEqual(len(item['pixel_artwork_groups']), 2)
        self.assertEqual(len(item['artwork_review_units']), 2)
        self.assertEqual(sum(len(u['duplicate_sha256']) for u in item['artwork_review_units']), 1)
        self.assertEqual(result['consolidation']['pixel_duplicate_sha_observations'], 1)
        self.assertEqual(result['consolidation']['pixel_distinct_artworks_avoided'], 1)

    def test_full_pixel_equivalence_prioritizes_master_comparison_not_approval(self):
        rows = [{'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': 'service-a', 'candidate_sha256': sha * 64,
                 'candidate_source': sha + '.png'} for sha in ('a', 'b')]
        result = build_review_queue({}, {}, [], rows, pixel_digests={'a' * 64: 'same', 'b' * 64: 'same'})
        item = result['items'][0]
        self.assertEqual(item['review_priority'], 'P1_VERIFY_SINGLE_PIXEL_ARTWORK_AGAINST_MASTER')
        self.assertEqual(item['decision'], 'PENDING')
        self.assertEqual(len(item['artwork_review_units']), 1)
        self.assertEqual(len(item['artwork_review_units'][0]['duplicate_sha256']), 1)
        self.assertEqual(result['count'], 1)

    def test_single_verified_artwork_has_one_review_unit(self):
        rows = [{'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': 'service-single', 'candidate_sha256': 'a' * 64,
                 'candidate_source': 'a.png'}]
        result = build_review_queue({}, {}, [], rows, pixel_digests={'a' * 64: 'pixel-a'})
        item = result['items'][0]
        self.assertEqual(item['distinct_pixel_artworks'], 1)
        self.assertEqual(item['artwork_review_units'][0]['representative_sha256'], 'a' * 64)
        self.assertEqual(item['review_priority'], 'P1_VERIFY_SINGLE_PIXEL_ARTWORK_AGAINST_MASTER')
        self.assertEqual(item['decision'], 'PENDING')

    def test_grouped_missing_pixel_evidence_keeps_every_sha_inspectable(self):
        rows = [{'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': 'service-a', 'candidate_sha256': sha * 64,
                 'candidate_source': sha + '.png'} for sha in ('a', 'b', 'c')]
        queue = build_review_queue({}, {}, [], rows, pixel_digests={'a' * 64: 'verified-a'})
        self.assertEqual(queue['count'], 1)
        item = queue['items'][0]
        self.assertEqual(item['decision'], 'PENDING')
        self.assertEqual(item['review_priority'], 'P3_COMPLETE_PIXEL_EVIDENCE')
        self.assertEqual({unit['representative_sha256'] for unit in item['artwork_review_units']},
                         {sha * 64 for sha in ('a', 'b', 'c')})
        self.assertTrue(all(unit['pixel_verification'] == 'UNVERIFIED'
                            for unit in item['artwork_review_units']))
        self.assertTrue(all(not unit['duplicate_sha256']
                            for unit in item['artwork_review_units']))
        self.assertNotIn('pixel_equivalence', item)

    def test_missing_pixel_proof_never_claims_pixel_equivalence(self):
        rows = [{'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': 'service-a', 'candidate_sha256': sha * 64,
                 'candidate_source': sha + '.png'} for sha in ('a', 'b')]
        result = build_review_queue({}, {}, [], rows, pixel_digests={'a' * 64: 'pixel-x'})
        self.assertNotIn('pixel_equivalence', result['items'][0])
        self.assertEqual(result['items'][0]['review_priority'], 'P3_COMPLETE_PIXEL_EVIDENCE')
        self.assertNotIn('pixel_artwork_groups', result['items'][0])
        self.assertEqual(result['consolidation']['pixel_distinct_artworks_avoided'], 0)

    def test_different_references_remain_separate(self):
        rows = [
            {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
             'service_reference': ref, 'candidate_sha256': sha*64,
             'candidate_source': r'C:\\source-ingest\\originals\\openatv8\\a.png'}
            for ref, sha in [('1_0_1_2_3_4_5_6_7_8', 'a'), ('1_0_1_9_3_4_5_6_7_8', 'b')]
        ]
        result = build_review_queue({}, {}, [], rows)
        self.assertEqual(result['count'], 2)


if __name__ == '__main__':
    unittest.main()

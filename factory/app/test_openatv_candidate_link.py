import unittest
from openatv_candidate_link import attach_name_candidates, _station_key
from openatv_station_groups import group_openatv_stations
from openatv_triage import build_openatv_triage


class OpenAtvNameCandidateTests(unittest.TestCase):
    def test_name_typography_aliases(self):
        self.assertEqual(_station_key('NOVA Sports 2.png'), _station_key('nova-sports_2.PNG'))
        self.assertNotEqual(_station_key('NOVA Sports 2.png'), _station_key('NOVA Sports 3.png'))
        self.assertNotEqual(_station_key('NOVA Sports HD.png'), _station_key('NOVA Sports.png'))

    def test_service_reference_not_treated_as_name(self):
        self.assertIsNone(_station_key('1_0_1_13C99_1BBC_13E_820000_0_0_0.png'))

    def test_unique_exact_artwork_evidence_links_alias(self):
        a={'candidate_source':r'C:\\SOURCE-INGEST\\OPENATV8\\NOVA Sports 2.png','classification':'UNMAPPED',
           'artwork_evidence':{'status':'EXACT_ARTWORK_SINGLE_MASTER_REF','possible_master_service_references':['1:0:1:2']}}
        b={'candidate_source':r'C:\\SOURCE-INGEST\\OPENATV8\\nova-sports_2.png','classification':'UNMAPPED'}
        counts=attach_name_candidates([a,b])
        self.assertEqual(counts['candidate_linked_files'],2)
        self.assertEqual(b['candidate_service_reference'],'1:0:1:2')
        self.assertFalse(b['name_group_candidate']['identity_verified'])

    def test_triage_groups_aliases_as_one_station(self):
        rows = [
            {'candidate_source':r'C:\\SOURCE-INGEST\\OPENATV8\\NOVA Sports 2.png',
             'candidate_sha256':'a'*64, 'classification':'UNMAPPED'},
            {'candidate_source':r'C:\\SOURCE-INGEST\\OPENATV8\\nova-sports_2.png',
             'candidate_sha256':'a'*64, 'classification':'UNMAPPED'},
            {'candidate_source':r'C:\\SOURCE-INGEST\\OPENATV8\\NOVA Sports 3.png',
             'candidate_sha256':'b'*64, 'classification':'UNMAPPED'}]
        triage = build_openatv_triage(rows)
        self.assertEqual(triage['summary']['station_names'], 2)
        self.assertEqual(triage['summary']['repeated_source_files'], 1)
        groups = group_openatv_stations(rows)
        self.assertEqual(groups['station_names'], 2)

    def test_unverified_existing_candidate_cannot_seed_another_alias(self):
        rows=[
            {'candidate_source':r'C:\\SOURCE-INGEST\\OPENATV8\\NOVA Sports 2.png',
             'classification':'EVIDENCE_LINKED','candidate_service_reference':'1:0:1:2'},
            {'candidate_source':r'C:\\SOURCE-INGEST\\OPENATV8\\nova-sports_2.png',
             'classification':'UNMAPPED'}]
        counts=attach_name_candidates(rows)
        self.assertEqual(counts['candidate_linked_files'],0)
        self.assertEqual(rows[1]['classification'],'UNMAPPED')

    def test_conflict_never_promotes(self):
        rows=[]
        for ref in ('1:0:1:2','1:0:1:3'):
            rows.append({'candidate_source':r'C:\\SOURCE-INGEST\\OPENATV8\\same-name.png','classification':'UNMAPPED',
                         'artwork_evidence':{'status':'EXACT_ARTWORK_SINGLE_MASTER_REF','possible_master_service_references':[ref]}})
        counts=attach_name_candidates(rows)
        self.assertEqual(counts['conflicting_names'],1)
        self.assertTrue(all(row['classification']=='UNMAPPED' for row in rows))


if __name__=='__main__':
    unittest.main()

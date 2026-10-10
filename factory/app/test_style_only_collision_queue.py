import unittest
from review_queue import build_review_queue

DARK='bf8cb399d92f16682bb81639588894dbaed8f7bda7af3ecbc80cbc9a3b15e0ad'
LIGHT='c3b149471e6b16edc5068481e8df14c8ef71bb0e1dcdf04cdd865c5143178e5a'
REF='1_0_1_2_3_4_5_6_7_8'

def source(package, origin='openatv8'):
    return f'/factory/source-ingest/originals/{origin}/{package}/{REF}.png'

def collision(variants):
    return [{'candidate_service_ref':REF,'variants':[
        {'sha256':sha,'sources':paths} for sha,paths in variants]}]

class StyleOnlyCollisionTests(unittest.TestCase):
    def queue(self, variants):
        return build_review_queue({}, {}, collision(variants))

    def test_known_dark_light_style_is_audit_only(self):
        queue=self.queue([('a'*64,[source(DARK)]),('b'*64,[source(LIGHT)])])
        self.assertEqual(queue['count'],0)
        self.assertEqual(queue['consolidation']['openatv_style_only_identity_tasks_avoided'],1)

    def test_same_style_multiple_sha_stays_manual(self):
        queue=self.queue([('a'*64,[source(DARK)]),('b'*64,[source(DARK)])])
        self.assertEqual(queue['workstream_counts']['IDENTITY_VERIFICATION'],1)

    def test_unknown_package_stays_manual(self):
        queue=self.queue([('a'*64,[source(DARK)]),('b'*64,[source('unknown')])])
        self.assertEqual(queue['count'],1)

    def test_other_feed_stays_manual(self):
        queue=self.queue([('a'*64,[source(DARK)]),('b'*64,[source(LIGHT,'vhannibal')])])
        self.assertEqual(queue['count'],1)

    def test_cross_feed_same_sha_stays_manual(self):
        queue=self.queue([('a'*64,[source(DARK),source(DARK,'vhannibal')]),('b'*64,[source(LIGHT)])])
        self.assertEqual(queue['count'],1)

if __name__=='__main__':
    unittest.main()

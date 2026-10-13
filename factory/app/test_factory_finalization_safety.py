"""Regression: local NEW candidate output is never an implicit approval."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from factory_finalization import finalize_new_candidates, STYLES
from unittest.mock import patch
import factory_finalization


class FinalizationSafetyTests(unittest.TestCase):
    def test_idempotent_and_never_overwrites_existing_variant(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            work, final = base / "work", base / "final"
            sha = hashlib.sha256(b"immutable original").hexdigest()
            ref = "_".join(["1"] * 10)
            srcdir = work / sha[:2] / sha
            srcdir.mkdir(parents=True)
            for style in STYLES:
                Image.new("RGBA", (220, 132), (12, 30, 48, 255)).save(srcdir / (style + ".png"))
            matches = [{"service_reference": ref, "candidate_sha256": sha, "classification": "NEW"}]
            first = finalize_new_candidates(matches, {}, work, final, verified_shas={sha})
            self.assertEqual(first["copied"], 3)
            self.assertEqual(first["conflicts"], 0)
            second = finalize_new_candidates(matches, {}, work, final, verified_shas={sha})
            self.assertEqual(second["copied"], 0)
            self.assertEqual(second["already_present"], 1)
            protected = final / "NEW-CANDIDATES" / "black" / (ref + ".png")
            protected.write_bytes(b"protected local file")
            third = finalize_new_candidates(matches, {}, work, final, verified_shas={sha})
            self.assertEqual(third["copied"], 0)
            self.assertEqual(third["conflicts"], 1)
            self.assertEqual(third["existing_target_conflicts"], 1)
            self.assertEqual(third["existing_target_conflicts"], 1)
            self.assertEqual(protected.read_bytes(), b"protected local file")

    def test_repeated_source_triplets_reuse_sha256_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            work,final=base/'work',base/'final'
            sha=hashlib.sha256(b'one immutable source').hexdigest()
            srcdir=work/sha[:2]/sha
            srcdir.mkdir(parents=True)
            for style in STYLES:
                Image.new('RGBA',(220,132),(12,30,48,255)).save(srcdir/(style+'.png'))
            refs=['_'.join(['1']*9+['2']), '_'.join(['1']*9+['3'])]
            matches=[{'service_reference':ref,'candidate_sha256':sha,'classification':'NEW'} for ref in refs]
            with patch('factory_finalization._digest',wraps=factory_finalization._digest) as digest:
                result=finalize_new_candidates(matches,{},work,final,verified_shas={sha})
            self.assertEqual(result['copied'],6)
            self.assertEqual(result['source_digest_cache_misses'],3)
            self.assertEqual(result['source_digest_cache_hits'],3)
            self.assertEqual(result['candidates_ready_to_copy'],2)
            self.assertEqual(digest.call_count,3)

    def test_missing_qa_is_not_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            sha = hashlib.sha256(b"unverified").hexdigest()
            ref = "_".join(["A"] * 10)
            result = finalize_new_candidates(
                [{"service_reference": ref, "candidate_sha256": sha, "classification": "NEW"}],
                {}, Path(temp) / "work", Path(temp) / "final", verified_shas=set())
            self.assertEqual(result["qa_blocked"], 1)
            self.assertEqual(result["copied"], 0)
            self.assertFalse((Path(temp) / "final").exists())

    def test_qa_signature_avoids_repeat_decode_but_copy_hashes_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); work=base/'work'; final=base/'final'
            sha=hashlib.sha256(b'original identity evidence').hexdigest()
            ref='_'.join(['4']*10)
            srcdir=work/sha[:2]/sha; srcdir.mkdir(parents=True)
            signatures={}
            for style in STYLES:
                source=srcdir/(style+'.png')
                Image.new('RGBA',(220,132),(22,35,49,255)).save(source)
                stat=source.stat()
                signatures[style]={'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                                   'stat':[stat.st_dev,stat.st_ino,stat.st_size,
                                           stat.st_mtime_ns,stat.st_ctime_ns]}
            matches=[{'service_reference':ref,'candidate_sha256':sha,'classification':'NEW'}]
            class NoDecode:
                @staticmethod
                def open(*args,**kwargs):
                    raise AssertionError('trusted QA evidence should avoid re-decoding')
            result=finalize_new_candidates(matches,{},work,final,verified_shas={sha},
                                           verified_signatures={sha:signatures},
                                           image_class=NoDecode)
            self.assertEqual(result['copied'],3)
            for style in STYLES:
                target=final/'NEW-CANDIDATES'/style/(ref+'.png')
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                                 signatures[style]['sha256'])

    def test_changed_source_invalidates_qa_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); work=base/'work'; final=base/'final'
            sha=hashlib.sha256(b'identity').hexdigest(); ref='_'.join(['5']*10)
            srcdir=work/sha[:2]/sha; srcdir.mkdir(parents=True)
            signatures={}
            for style in STYLES:
                source=srcdir/(style+'.png')
                Image.new('RGBA',(220,132),(31,40,50,255)).save(source)
                stat=source.stat()
                signatures[style]={'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                                   'stat':[stat.st_dev,stat.st_ino,stat.st_size,
                                           stat.st_mtime_ns,stat.st_ctime_ns]}
            (srcdir/'white.png').write_bytes(b'changed after QA')
            result=finalize_new_candidates(
                [{'service_reference':ref,'candidate_sha256':sha,'classification':'NEW'}],
                {},work,final,verified_shas={sha},verified_signatures={sha:signatures})
            self.assertEqual(result['copied'],0)
            self.assertEqual(result['invalid'],1)
            self.assertFalse(final.exists())

    def test_interrupted_triplet_copy_rolls_back_visible_variants(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); work=base/'work'; final=base/'final'
            sha=hashlib.sha256(b'identity').hexdigest(); ref='_'.join(['6']*10)
            srcdir=work/sha[:2]/sha; srcdir.mkdir(parents=True)
            for style in STYLES:
                Image.new('RGBA',(220,132),(61,70,80,255)).save(srcdir/(style+'.png'))
            real_copy=factory_finalization._copy_verified_exclusive
            calls={'count':0}
            def fail_second(source,target,expected):
                calls['count']+=1
                if calls['count']==2:
                    raise OSError('simulated interrupted copy')
                return real_copy(source,target,expected)
            with patch('factory_finalization._copy_verified_exclusive',side_effect=fail_second):
                result=finalize_new_candidates(
                    [{'service_reference':ref,'candidate_sha256':sha,'classification':'NEW'}],
                    {},work,final,verified_shas={sha})
            self.assertEqual(result['copy_failures'],1)
            self.assertEqual(list(final.rglob('*.png')),[])


if __name__ == "__main__":
    unittest.main()

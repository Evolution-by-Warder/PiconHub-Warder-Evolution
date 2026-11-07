"""Local admission/template regressions using the actual immutable singleton6 fixture."""
import copy
import gzip
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
import prepare43 as prep

HERE=Path(__file__).resolve().parent
FIXTURE=Path(os.environ.get('WARDER_PREP43_SELECTION_FIXTURE','continuation/country-singletons/ci-reproduce/github-results/selection.json.gz'))
class Preparation43(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=json.loads(gzip.decompress(FIXTURE.read_bytes()))['entries']
        cls.workflow=(HERE/'workflow43-reviewed.yml').read_text()
    def check_rows(self,rows,count):
        with tempfile.TemporaryDirectory()as d:
            f=Path(d)/'selection.json';f.write_text(json.dumps(dict(entries=rows)))
            return prep.validate_source(f,count)
    def test_actual_existing_pinned_six_fixture_validates(self):
        self.assertEqual(len(self.check_rows(self.rows,6)),6)
    def test_source_count_mismatch_fails(self):
        with self.assertRaises(ValueError):self.check_rows(self.rows,113)
    def test_unpinned_source_fails(self):
        rows=copy.deepcopy(self.rows);rows[0]['source_commit']=None
        with self.assertRaises(ValueError):self.check_rows(rows,6)
    def test_parent_asset_root_required(self):
        for root in ('.','../escape','/absolute','pending/source','picons/radio-world/staging/x/verified-assets'):
            rows=copy.deepcopy(self.rows);rows[0]['asset_root']=root
            with self.subTest(root=root),self.assertRaises(ValueError):self.check_rows(rows,6)
    def test_wrong_variant_cannot_hide_behind_count_nine(self):
        rows=copy.deepcopy(self.rows);rows[0]['variants']['400x241/black']=rows[0]['variants'].pop('400x240/black')
        with self.assertRaises(ValueError):self.check_rows(rows,6)
    def test_boolean_is_not_valid_byte_count(self):
        rows=copy.deepcopy(self.rows);rows[0]['variants']['220x132/white'][1]=True
        with self.assertRaises(ValueError):self.check_rows(rows,6)
    def test_duplicate_ref_fails(self):
        with self.assertRaises(ValueError):self.check_rows([self.rows[0],self.rows[0]],2)
    def test_absent_producer_count_pair_writes_nothing(self):
        with tempfile.TemporaryDirectory()as d:
            stage=Path(d)/'stage'
            with self.assertRaises(ValueError):prep.main(['--source',str(FIXTURE)+':missing-ledger','--expected-source-count','113','--expected-source-count','25','--stage',str(stage)])
            self.assertFalse(stage.exists())
    def test_existing_sources_cannot_be_misreported_as_predicted_113(self):
        with tempfile.TemporaryDirectory()as d:
            stage=Path(d)/'stage'
            with self.assertRaises(ValueError):prep.main(['--source',str(FIXTURE)+':missing-ledger','--expected-source-count','113','--expected-total','113','--stage',str(stage)])
            self.assertFalse(stage.exists())
    def test_workflow_all_four_gates_have_complete_history(self):
        expected={'picons/radio-world/staging/'+name for name in prep.HISTORY}|{'$stage/visual-ledger.json.gz'}
        calls=[]
        for line in self.workflow.splitlines():
            if 'python3 picons/radio-world/tools/visual_gate.py 'in line or 'python3 picons/radio-world/tools/audit_png_admission.py 'in line:
                tokens=shlex.split(line);ledgers=[tokens[i+1]for i,t in enumerate(tokens)if t=='--ledger'];self.assertEqual(len(ledgers),7);self.assertEqual(set(ledgers),expected);calls.append(line)
        self.assertEqual(len(calls),4)
        self.assertEqual(self.workflow.count('actual=sys.argv[1:]; assert len(actual)==7'),4)
    def test_every_workflow_shell_block_parses(self):
        import yaml
        data=yaml.safe_load(self.workflow);runs=[s['run']for s in data['jobs']['build']['steps']if'run'in s]
        for code in runs:
            result=subprocess.run(['bash','-n'],input=code,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
    def test_workflow_never_targets_production_ref(self):
        self.assertIn('work/radio-world-batch43-reviewed-history-20261107',self.workflow)
        self.assertNotIn('refs/heads/main',self.workflow)
        self.assertIn('b7384bfdb55621beaf183ca6d40e9dedacaecdb9',self.workflow)
        self.assertIn('--countries all-available',self.workflow)
        self.assertIn('audit_production_preservation.py',self.workflow)

if __name__=='__main__':unittest.main()

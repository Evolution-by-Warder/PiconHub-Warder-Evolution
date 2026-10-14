import json
import tempfile
import unittest
from pathlib import Path



import source_cycle as cycle

class SourceCycleTests(unittest.TestCase):
    def make_legacy(self):
        items = ([{"workstream": "IDENTITY_VERIFICATION"}] * 4054 +
                 [{"workstream": "ARTWORK_REVIEW"}] * 5877 +
                 [{"workstream": "TECHNICAL_QA"}])
        return {"schema": 1, "count": 9932, "workstream_counts": dict(cycle.LEGACY_QUEUE_COUNTS), "items": items}

    def test_only_exact_legacy_queue_is_removed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); exceptions = root / "05-QA" / "EXCEPTIONS"; reports = root / "08-REPORTS"; state = root / "00-STATE"
            exceptions.mkdir(parents=True); reports.mkdir(parents=True)
            old = exceptions / "review-queue-20261014.json"; old.write_text(json.dumps(self.make_legacy()), encoding="utf-8")
            new = exceptions / "review-queue-new.json"; new.write_text(json.dumps({"schema": 1, "count": 1, "items": [{"review_id": "new"}]}), encoding="utf-8")
            report = reports / "review-evidence-old.json"; report.write_text("preserve", encoding="utf-8")
            first = cycle.migrate_legacy_review_queue(exceptions, reports, state)
            second = cycle.migrate_legacy_review_queue(exceptions, reports, state)
            self.assertEqual(first["status"], "COMPLETED"); self.assertEqual(first["deleted"], 1)
            self.assertEqual(second["deleted"], 1)
            self.assertFalse(old.exists()); self.assertTrue(new.exists()); self.assertTrue(report.exists())

    def test_changed_target_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); exceptions = root / "exceptions"; reports = root / "reports"; state = root / "state"
            exceptions.mkdir(); reports.mkdir()
            old = exceptions / "review-queue-old.json"; old.write_text(json.dumps(self.make_legacy()), encoding="utf-8")
            marker = state / "migrations" / "cancel-legacy-review-queue-9932-v1.json"
            marker.parent.mkdir(parents=True)
            marker.write_text(json.dumps({"schema": 1, "migration": "cancel-legacy-review-queue-9932-v1", "status": "PLANNED", "deleted": 0, "conflicts": [], "targets": [{"root_id": "exceptions", "filename": old.name, "sha256": "0" * 64}]}), encoding="utf-8")
            result = cycle.migrate_legacy_review_queue(exceptions, reports, state)
            self.assertEqual(result["status"], "BLOCKED"); self.assertTrue(old.exists())

    def test_source_order_waits_for_openatv(self):
        ledger = {"schema": 1, "source_order": list(cycle.SOURCE_ORDER), "sources": {
            "openatv8": {"status": "AWAITING_APPROVAL"}, "vhannibal": {"status": "NOT_CHECKED"},
            "chocholousek": {"status": "NOT_CHECKED"}}}
        self.assertEqual(cycle.active_source(ledger), "openatv8")
        ledger["sources"]["openatv8"]["status"] = "COMPLETED"
        self.assertEqual(cycle.active_source(ledger), "vhannibal")
        self.assertEqual(cycle.validate_source_ledger(ledger), [])

    def test_artwork_hash_never_merges_different_references(self):
        master = {"ref-a": [{"sha256": "same"}], "ref-b": [{"sha256": "master"}]}
        self.assertEqual(cycle.classify_master_reference("ref-a", "same", master), "EXACT_MATCH")
        self.assertEqual(cycle.classify_master_reference("ref-b", "same", master), "EXISTING_REFERENCE_DIFFERENT_ARTWORK")
        self.assertEqual(cycle.classify_master_reference("ref-c", "same", master), "NEW_IDENTITY_CANDIDATE")
        self.assertEqual(cycle.classify_master_reference(None, "same", master), "AMBIGUOUS_OR_CONFLICT")

    def test_verified_local_openatv_package_requires_marker_and_hash_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "openatv8" / "schema-3"; package = root / ("a" * 64); package.mkdir(parents=True)
            (package / ".warder-import-schema").write_text("3", encoding="ascii")
            (package / "picon").mkdir(); (package / "picon" / "a.png").write_bytes(b"x")
            invalid = root / "latest"; invalid.mkdir(); (invalid / ".warder-import-schema").write_text("3", encoding="ascii")
            self.assertEqual(cycle.find_verified_openatv_packages(Path(tmp)), [{"package_id": "a" * 64, "png_count": 1}])


    def test_manifest_is_source_relative_and_contains_only_metadata(self):
        import gzip
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); package='a'*64
            source=root/'openatv8'/'schema-3'/package/'picon'/'1_0_1_0001_0002_0003_0004_0005_0000_0000.png'
            source.parent.mkdir(parents=True);source.write_bytes(b'PNG bytes must not enter manifest')
            blobs,summary=cycle.build_openatv_manifest([{'source':str(source),'sha256':'b'*64}], [root/'openatv8'],root/'out')
            payload=gzip.decompress(next(iter(blobs.values())))
            row=json.loads(payload.decode().splitlines()[0])
            self.assertEqual(row['path'],f'schema-3/{package}/picon/{source.name}')
            self.assertEqual(row['sha256'],'b'*64)
            self.assertNotIn(b'PNG bytes must not enter manifest',payload)
            self.assertTrue(summary['metadata_only']);self.assertFalse(summary['contains_png_bytes'])

    def test_source_writer_rejects_png_and_refuses_changed_head(self):
        with self.assertRaisesRegex(ValueError,'PATH_OR_CONTENT_REJECTED'):
            cycle.commit_source_checkpoint('token','a'*40,{
                'factory/registry/source-processing-ledger.json':b'{}',
                'factory/registry/source-manifests/openatv8/a.png':b'png'})
        class Response:
            def __init__(self,payload):self.payload=payload
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self):return json.dumps(self.payload).encode()
        class Opener:
            def __init__(self):self.calls=[]
            def __call__(self,request,timeout=20):
                self.calls.append(request.method)
                return Response({'commit':{'sha':'b'*40}})
        ledger={'schema':1,'source_order':list(cycle.SOURCE_ORDER),'sources':{
            'openatv8':{'status':'AWAITING_APPROVAL'},'vhannibal':{'status':'NOT_CHECKED'},
            'chocholousek':{'status':'NOT_CHECKED'}}}
        opener=Opener()
        with self.assertRaisesRegex(RuntimeError,'HEAD_CHANGED'):
            cycle.commit_source_checkpoint('token','a'*40,{
                'factory/registry/source-processing-ledger.json':json.dumps(ledger).encode()},opener=opener)
        self.assertEqual(opener.calls,['GET'])

    def test_validate_source_ledger_rejects_parallel_active_sources(self):
        ledger={'schema':1,'source_order':list(cycle.SOURCE_ORDER),'sources':{
            'openatv8':{'status':'AWAITING_APPROVAL'},'vhannibal':{'status':'PROCESSING'},
            'chocholousek':{'status':'NOT_CHECKED'}}}
        self.assertIn('MULTIPLE_ACTIVE_SOURCES',cycle.validate_source_ledger(ledger))

    def test_source_writer_commits_one_atomic_development_transaction_and_reads_back(self):
        import hashlib
        ledger={'schema':1,'source_order':list(cycle.SOURCE_ORDER),'sources':{
            'openatv8':{'status':'AWAITING_APPROVAL'},'vhannibal':{'status':'NOT_CHECKED'},
            'chocholousek':{'status':'NOT_CHECKED'}}}
        content=json.dumps(ledger).encode(); blob_sha='c'*40
        class Response:
            def __init__(self,payload):self.payload=payload
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self):return json.dumps(self.payload).encode()
        class Opener:
            def __init__(self):self.calls=[];self.updated=False
            def __call__(self,request,timeout=20):
                self.calls.append((request.method,request.full_url))
                url=request.full_url;method=request.method
                if url.endswith('/branches/factory-warder-development'):
                    return Response({'commit':{'sha':('f'*40 if self.updated else 'a'*40)}})
                if url.endswith('/git/commits/'+'a'*40):return Response({'tree':{'sha':'b'*40}})
                if url.endswith('/git/blobs'):return Response({'sha':blob_sha})
                if url.endswith('/git/trees') and method=='POST':return Response({'sha':'d'*40})
                if url.endswith('/git/commits') and method=='POST':return Response({'sha':'f'*40})
                if '/git/refs/heads/' in url and method=='PATCH':self.updated=True;return Response({})
                if url.endswith('/git/commits/'+'f'*40):return Response({'tree':{'sha':'e'*40}})
                if '/git/trees/' in url:return Response({'tree':[{'path':'factory/registry/source-processing-ledger.json','sha':blob_sha}]})
                raise AssertionError((method,url))
        opener=Opener()
        result=cycle.commit_source_checkpoint('dummy-secret','a'*40,{
            'factory/registry/source-processing-ledger.json':content},opener=opener)
        self.assertEqual(result['status'],'SAVED_TO_GIT');self.assertEqual(result['commit'],'f'*40)
        self.assertEqual(result['branch'],'factory-warder-development')
        self.assertEqual(sum(1 for method,url in opener.calls if method=='PATCH'),1)
        self.assertNotIn('warder-master-production',str(opener.calls))

    def test_real_openatv_git_checkpoint_manifest_matches_reported_rows(self):
        import gzip, hashlib
        app_root=Path(__file__).resolve().parent
        repo_root=app_root.parent.parent
        ledger=json.loads((repo_root/'factory'/'registry'/'source-processing-ledger.json').read_text(encoding='utf-8'))
        self.assertEqual(cycle.validate_source_ledger(ledger),[])
        source=ledger['sources']['openatv8']
        self.assertEqual(source['status'],'AWAITING_APPROVAL')
        self.assertEqual(source['png_observations'],148466)
        total=0
        for item in source['content_manifest']:
            path=repo_root/item['path']
            raw=path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256'])
            with gzip.open(path,'rt',encoding='utf-8') as stream:
                for line in stream:
                    row=json.loads(line);total+=1
                    self.assertFalse(Path(row['path']).is_absolute())
                    self.assertNotIn('\\',row['path'])
                    self.assertEqual(len(row['byte_sha256']),64)
                    self.assertEqual(len(row['decoded_rgba_pixel_sha256']),64)
                    self.assertNotIn('png_bytes',row)
        self.assertEqual(total,148466)

if __name__ == "__main__":
    unittest.main()

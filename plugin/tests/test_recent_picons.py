import hashlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).parents[1]/"src/Plugins/Extensions/WarderPiconHub"
spec=importlib.util.spec_from_file_location("recent_test_module",ROOT/"warder_recent.py")
recent=importlib.util.module_from_spec(spec);spec.loader.exec_module(recent)


class RecentTests(unittest.TestCase):
    def fixtures(self):
        sources=json.loads((ROOT/"images/recent/sources.json").read_text())["items"]
        images=[(entry["sha"],(ROOT/"images/recent"/(entry["sha"]+".png")).read_bytes()) for entry in sources]
        commit="a"*40
        files=[{"filename":entry["source_path"],"sha":entry["sha"],"status":"added"} for entry in sources]
        urls={recent.API+"/commits?sha=main&path=picons&per_page=8":json.dumps([{"sha":commit}]).encode(),
              recent.API+"/commits/"+commit+"?per_page=100":json.dumps({"files":files}).encode()}
        urls.update({recent.RAW+commit+"/"+entry["source_path"]:data for entry,(sha,data) in zip(sources,images)})
        return urls,images,files,commit

    def test_seed_is_six_distinct_exact_source_blobs(self):
        paths=recent.bundled(ROOT)
        self.assertEqual(len(paths),6)
        metadata=json.loads((ROOT/"images/recent/sources.json").read_text())
        self.assertTrue(all("/black/" in entry["source_path"] for entry in metadata["items"]))
        self.assertEqual(len({p.stem for p in paths}),6)
        for p in paths:recent.verify_png(p.read_bytes(),p.stem)

    def test_live_discovery_cache_and_offline_reopen(self):
        urls,images,files,commit=self.fixtures();calls=[]
        def opener(url):calls.append(url);return io.BytesIO(urls[url])
        with tempfile.TemporaryDirectory() as folder:
            paths=recent.load_recent(ROOT,folder,opener,now=10000)
            self.assertEqual([p.stem for p in paths],[sha for sha,data in images])
            self.assertTrue(all(p.parent==pathlib.Path(folder) for p in paths))
            self.assertEqual(len(calls),8)
            def offline(url):raise OSError("offline")
            self.assertEqual(recent.load_recent(ROOT,folder,offline,now=10001),paths)
            self.assertEqual(recent.load_recent(ROOT,folder,offline,now=14000),paths)

    def test_offline_first_open_uses_bundled_real_additions(self):
        def offline(url):raise OSError("offline")
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(recent.load_recent(ROOT,folder,offline),recent.bundled(ROOT))

    def test_previous_transparent_cache_is_never_displayed_in_black_strip(self):
        with tempfile.TemporaryDirectory() as folder:
            (pathlib.Path(folder)/"manifest.json").write_text(json.dumps({"style":"transparent","items":[],"checked_at":10000}))
            self.assertEqual(recent.cached(pathlib.Path(folder)),([],0))
            self.assertTrue(str(recent.CACHE).endswith("/recent-black"))

    def test_modified_files_foreign_paths_and_duplicates_are_not_new_additions(self):
        urls,images,files,commit=self.fixtures()
        invalid=[dict(files[0],status="modified"),dict(files[0],filename="../../foreign.png"),
                 dict(files[0],filename=files[0]["filename"].replace("/black/","/white/"))]
        urls[recent.API+"/commits/"+commit+"?per_page=100"]=json.dumps({"files":invalid+[files[0]]+files}).encode()
        result=recent.discover(lambda url:io.BytesIO(urls[url]))
        self.assertEqual([sha for sha,data in result],[sha for sha,data in images])

    def test_corrupt_download_and_corrupt_cache_fall_back_without_installing(self):
        urls,images,files,commit=self.fixtures()
        urls[recent.RAW+commit+"/"+files[0]["filename"]]=images[0][1]+b"corrupt"
        with tempfile.TemporaryDirectory() as folder:
            paths=recent.load_recent(ROOT,folder,lambda url:io.BytesIO(urls[url]))
            self.assertEqual(paths,recent.bundled(ROOT))
            self.assertFalse((pathlib.Path(folder)/"manifest.json").exists())
            sha=images[0][0]
            (pathlib.Path(folder)/(sha+".png")).write_bytes(b"bad")
            (pathlib.Path(folder)/"manifest.json").write_text(json.dumps({"items":[sha],"checked_at":10000}))
            self.assertEqual(recent.cached(pathlib.Path(folder)),([],0))

    def test_oversized_and_invalid_images_and_metadata_are_bounded(self):
        for data in (b"bad",b"x"*(recent.MAX_PNG+1)):
            with self.assertRaises(ValueError):recent.verify_png(data,"a"*40)
        with self.assertRaises(ValueError):
            recent.read_json("unused",lambda url:io.BytesIO(b"x"*(2*1024*1024+1)))


if __name__=="__main__":unittest.main()

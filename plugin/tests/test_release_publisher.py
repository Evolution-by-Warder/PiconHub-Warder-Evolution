import base64
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

PLUGIN=pathlib.Path(__file__).parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


publisher=module("publisher_tests",PLUGIN/"tools/publish_plugin_release.py")
builder=module("publisher_test_builder",PLUGIN/"tools/build_ipk.py")
REVISION="a"*40


class FakeGitHub:
    def __init__(self,data):
        self.data=data;self.events=[];self.release=None;self.head=REVISION;self.bad_public=False
        self.feed={"schema":1,"product":"PiconHub Warder Evolution","channel":"stable","release":None}

    def request(self,method,path,payload=None,binary=None,allow_missing=False):
        self.events.append((method,path,payload))
        if method=="GET" and path.startswith("/contents/"):
            return {"content":base64.b64encode(json.dumps(self.feed).encode()).decode()}
        if method=="GET" and path.startswith("/git/refs/"):return {"object":{"sha":self.head}}
        if method=="GET" and path.startswith("/releases/tags/"):return self.release
        if method=="POST" and path=="/releases":
            self.release=dict(payload,id=1,assets=[]);return self.release
        if method=="POST" and "/assets?" in path:
            asset={"name":parse_qs(urlsplit(path).query)["name"][0],"size":len(binary),"digest":"sha256:"+hashlib.sha256(binary).hexdigest()}
            self.release["assets"].append(asset);return asset
        if method=="PATCH" and path.startswith("/releases/"):
            self.release.update(payload);return self.release
        if method=="GET" and path.startswith("/git/commits/"):return {"tree":{"sha":"b"*40}}
        if method=="POST" and path=="/git/trees":
            self.pending_feed=json.loads(payload["tree"][0]["content"]);return {"sha":"c"*40}
        if method=="POST" and path=="/git/commits":return {"sha":"d"*40}
        if method=="PATCH" and path.startswith("/git/refs/"):
            self.feed=self.pending_feed;self.head=payload["sha"];return {"object":{"sha":self.head}}
        raise AssertionError((method,path))

    def public_package(self,url,expected_bytes):
        self.events.append(("PUBLIC",url,None))
        return self.data+b"corrupt" if self.bad_public else self.data


class PublisherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory()
        cls.path,unused=builder.build(pathlib.Path(cls.folder.name),source_revision=REVISION)
        cls.version=(builder.RUNTIME/"version.txt").read_text().strip()

    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()

    def test_publication_order_integrity_and_old_dev8_compatibility(self):
        client=FakeGitHub(self.path.read_bytes())
        document=publisher.publish(self.path,self.version,REVISION,"Notes",client)
        offered=publisher.updates.parse_release(json.dumps(document),"0.1.0-dev8")
        self.assertEqual(offered.version,self.version)
        self.assertIsNone(publisher.updates.parse_release(json.dumps(document),self.version))
        self.assertTrue(client.release["prerelease"])
        self.assertEqual(client.release["make_latest"],"false")
        public_index=next(i for i,e in enumerate(client.events) if e[0]=="PUBLIC")
        feed_index=next(i for i,e in enumerate(client.events) if e[0]=="PATCH" and e[1].startswith("/git/refs/"))
        self.assertLess(public_index,feed_index)
        self.assertFalse(client.events[feed_index][2]["force"])
        self.assertEqual(client.feed,document)

    def test_damaged_public_download_never_updates_feed(self):
        client=FakeGitHub(self.path.read_bytes());client.bad_public=True
        with self.assertRaises(ValueError):publisher.publish(self.path,self.version,REVISION,"Notes",client)
        self.assertIsNone(client.feed["release"])
        self.assertFalse(any(e[0]=="PATCH" and e[1].startswith("/git/refs/") for e in client.events))

    def test_repeat_publication_verifies_existing_immutable_package(self):
        client=FakeGitHub(self.path.read_bytes())
        first=publisher.publish(self.path,self.version,REVISION,"Notes",client)
        writes=len([e for e in client.events if e[0] in ("POST","PATCH")])
        self.assertEqual(publisher.publish(self.path,self.version,REVISION,"Notes",client),first)
        self.assertEqual(len([e for e in client.events if e[0] in ("POST","PATCH")]),writes)

    def test_advanced_branch_and_version_collision_are_rejected(self):
        client=FakeGitHub(self.path.read_bytes());client.head="e"*40
        with self.assertRaises(ValueError):publisher.publish(self.path,self.version,REVISION,"Notes",client)
        self.assertIsNone(client.release)
        client=FakeGitHub(self.path.read_bytes())
        client.feed=publisher.manifest(self.path,self.version,"Notes")
        client.feed["release"]["sha256"]="0"*64
        with self.assertRaises(ValueError):publisher.publish(self.path,self.version,REVISION,"Notes",client)
        self.assertIsNone(client.release)


if __name__=="__main__":unittest.main()

import gettext
import importlib.util
import io
import json
import pathlib
import sys
import tarfile
import tempfile
import unittest

PLUGIN=pathlib.Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location("warder_package_builder",PLUGIN/"tools/build_ipk.py")
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


def ar_members(data):
    assert data[:8]==b"!<arch>\n"
    offset=8;members={}
    while offset<len(data):
        header=data[offset:offset+60];size=int(header[48:58]);name=header[:16].decode().strip().rstrip("/")
        members[name]=data[offset+60:offset+60+size];offset+=60+size+(size%2)
    return members


class PackageTests(unittest.TestCase):
    def test_build_is_repeatable_and_contains_complete_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            path,sha=builder.build(pathlib.Path(folder)/"a",source_revision="test-source")
            other,other_sha=builder.build(pathlib.Path(folder)/"b",source_revision="test-source")
            self.assertEqual(sha,other_sha);self.assertEqual(path.read_bytes(),other.read_bytes())
            members=ar_members(path.read_bytes())
            self.assertEqual(set(members),{"debian-binary","control.tar.gz","data.tar.gz"})
            self.assertEqual(members["debian-binary"],b"2.0\n")
            with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]),mode="r:gz") as control:
                text=control.extractfile("./control").read().decode()
                self.assertIn("Package: "+builder.PACKAGE,text)
                self.assertIn("Version: "+(builder.RUNTIME/"version.txt").read_text().strip(),text)
                self.assertIn("Conflicts: enigma2-plugin-extensions-chocholousek-picons",text)
                self.assertEqual(control.getmember("./postinst").mode,0o755)
                self.assertNotIn(b"reboot",control.extractfile("./postinst").read())
            with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]),mode="r:gz") as payload:
                names=payload.getnames()
                for name in ("plugin.py","warder_gui.py","warder_engine.py","warder_update.py","images/warder-background.png","images/preview-white.png","data/skin-menu.json","data/channel-manifest.json"):
                    self.assertIn("./"+builder.INSTALL_ROOT+"/"+name,names)
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                self.assertFalse(any(name.startswith("./etc/") for name in names))
                prefix="./"+builder.INSTALL_ROOT+"/"
                source=json.loads(payload.extractfile(prefix+"build.json").read())
                self.assertEqual(source["source_revision"],"test-source")
                catalog=json.loads(payload.extractfile(prefix+"data/channel-manifest.json").read())
                self.assertEqual(len(catalog["packages"]),468)
                translations=[name for name in names if name.endswith(".mo")]
                self.assertEqual(len(translations),9)
                for name in translations:gettext.GNUTranslations(io.BytesIO(payload.extractfile(name).read()))


if __name__=="__main__":unittest.main()

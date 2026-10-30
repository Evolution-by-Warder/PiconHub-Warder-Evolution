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
    def test_upgrade_manifest_keeps_the_version_read_by_the_running_old_gui(self):
        # Model opkg obsolete-file removal before unpack/postinst, where 0.1.7
        # crashed. Only paths absent from the new manifest can be removed.
        with tempfile.TemporaryDirectory() as folder:
            folder=pathlib.Path(folder)
            path,_=builder.build(folder/'package',source_revision='transition-test')
            members=ar_members(path.read_bytes())
            with tarfile.open(fileobj=io.BytesIO(members['data.tar.gz']),mode='r:gz') as payload:
                new_names={n.removeprefix('./') for n in payload.getnames()}
                legacy='usr/lib/enigma2/python/Plugins/Extensions/ChocholousekPicons/'
                old_names=[legacy+'plugin.py',legacy+'version.txt']
                for name in old_names:
                    target=folder/name;target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_text('0.1.6' if name.endswith('version.txt') else '# old')
                for name in old_names:
                    if name not in new_names:(folder/name).unlink()
                    self.assertEqual((folder/(legacy+'version.txt')).read_text(),'0.1.6')
                self.assertFalse((folder/(legacy+'plugin.py')).exists())

    def test_build_is_repeatable_and_contains_complete_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            path,sha=builder.build(pathlib.Path(folder)/"a",source_revision="test-source")
            other,other_sha=builder.build(pathlib.Path(folder)/"b",source_revision="test-source")
            self.assertEqual(sha,other_sha);self.assertEqual(path.read_bytes(),other.read_bytes())
            self.assertEqual(path.name,'enigma2-plugin-extensions-piconhub_'+(builder.RUNTIME/'version.txt').read_text().strip()+'_all.ipk')
            self.assertEqual(list(path.parent.glob('*.ipk')),[path])
            members=ar_members(path.read_bytes())
            self.assertEqual(set(members),{"debian-binary","control.tar.gz","data.tar.gz"})
            self.assertEqual(members["debian-binary"],b"2.0\n")
            with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]),mode="r:gz") as control:
                text=control.extractfile("./control").read().decode()
                self.assertIn("Package: "+builder.PACKAGE,text)
                self.assertIn("Version: "+(builder.RUNTIME/"version.txt").read_text().strip(),text)
                self.assertIn("Conflicts: enigma2-plugin-extensions-chocholousek-picons",text)
                # OpenEmbedded ships gettext.py in core, not python3-gettext.
                dependencies = next(line for line in text.splitlines() if line.startswith("Depends: ")).removeprefix("Depends: ").split(", ")
                self.assertIn("python3-core", dependencies)
                self.assertNotIn("python3-gettext", dependencies)
                self.assertEqual(control.getmember("./postinst").mode,0o755)
                self.assertEqual(control.getmember("./preinst").mode,0o755)
                self.assertIn(b"legacy-transition-needed",control.extractfile("./preinst").read())
                self.assertIn(b"WarderPiconHub/warder_migrate.py",control.extractfile("./postinst").read())
                self.assertNotIn(b"reboot",control.extractfile("./postinst").read())
            with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]),mode="r:gz") as payload:
                names=payload.getnames()
                self.assertEqual(builder.INSTALL_ROOT,"usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub")
                legacy="./usr/lib/enigma2/python/Plugins/Extensions/ChocholousekPicons/version.txt"
                self.assertEqual([n for n in names if "/Extensions/ChocholousekPicons/" in n],[legacy])
                self.assertEqual(payload.extractfile(legacy).read(),(builder.RUNTIME/"version.txt").read_bytes())
                for name in ("plugin.py","warder_gui.py","warder_engine.py","warder_update.py","warder_recent.py","warder_brand.py","warder_i18n.py","warder_migrate.py","data/translations.json","images/recent/sources.json","images/warder-emblem.png","images/selectors/sources.json","images/selectors/CANALPLUS_CZ.png","images/warder-background.png","images/preview-white.png","data/skin-menu.json","data/channel-manifest.json"):
                    self.assertIn("./"+builder.INSTALL_ROOT+"/"+name,names)
                recent=[name for name in names if "/images/recent/" in name and name.endswith(".png")]
                self.assertEqual(len(recent),6)
                self.assertEqual(len([n for n in names if "/images/selectors/" in n and n.endswith(".png")]),55)
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                self.assertFalse(any(name.startswith("./etc/") for name in names))
                prefix="./"+builder.INSTALL_ROOT+"/"
                source=json.loads(payload.extractfile(prefix+"build.json").read())
                self.assertEqual(source["source_revision"],"test-source")
                notes=json.loads(payload.extractfile(prefix+"data/release-notes.json").read())
                self.assertEqual(notes['version'],source['version'])
                self.assertEqual(set(notes['notes']),{'sk','cs','en','de','pl','hu','ru','fr','it','es'})
                self.assertTrue(all(isinstance(text,str) and text.strip() for text in notes['notes'].values()))
                catalog=json.loads(payload.extractfile(prefix+"data/channel-manifest.json").read())
                self.assertEqual(len(catalog["packages"]),469)
                translations=[name for name in names if name.endswith(".mo")]
                self.assertEqual(len(translations),9)
                for name in translations:gettext.GNUTranslations(io.BytesIO(payload.extractfile(name).read()))


if __name__=="__main__":unittest.main()

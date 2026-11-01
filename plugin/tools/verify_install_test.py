#!/usr/bin/env python3
"""Inspect the actual RC IPK, including health helper and four localized entries."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT/'src/Plugins/Extensions/WarderPiconHub/version.txt').read_text().strip()
PREFIX = 'usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/'


def main():
    package = ROOT/'build'/('enigma2-plugin-extensions-piconhub_'+VERSION+'_all.ipk')
    raw = package.read_bytes()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['ar','p',str(package),'control.tar.gz'])),mode='r:gz') as archive:
        control=archive.extractfile('./control').read().decode()
        assert 'Package: enigma2-plugin-extensions-piconhub-warder-evolution\n' in control
        assert 'Version: '+VERSION+'\n' in control
        assert b'--verify-installed-files' in archive.extractfile('./postinst').read()
        for name in ('preinst','postinst'):
            assert archive.getmember('./'+name).mode & 0o111
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['ar','p',str(package),'data.tar.gz'])),mode='r:gz') as archive:
        files={m.name.removeprefix('./'):m for m in archive if m.isfile()}
        runtime=ROOT/'src/Plugins/Extensions/WarderPiconHub'
        for p in runtime.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'):
                name=PREFIX+p.relative_to(runtime).as_posix()
                assert archive.extractfile(files[name]).read()==p.read_bytes(),name
        assert not any(n.startswith('etc/') or '__pycache__' in n for n in files)
        assert archive.extractfile(files[PREFIX+'version.txt']).read().decode().strip()==VERSION
        notes=json.loads(archive.extractfile(files[PREFIX+'data/release-notes.json']).read())
        assert notes['version']==VERSION and len(notes['entries'])==4
        assert all(len(e['notes'])==10 for e in notes['entries'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('warder_update.py','version.txt','plugin.py','__init__.py','warder_gui.py','warder_engine.py','warder_migrate.py'):
                (root/name).write_bytes(archive.extractfile(files[PREFIX+name]).read())
            spec=importlib.util.spec_from_file_location('packaged_piconhub_health',root/'warder_update.py')
            module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
            assert module.verify_payload(VERSION,root)==VERSION
    proof=json.loads((ROOT/'build/install-test-feed-isolation.json').read_text())
    assert hashlib.sha256((ROOT/'update/stable.json').read_bytes()).hexdigest()==proof['stable_feed_sha256']
    proof.update(package=package.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),payload_verified=True,receiver_test=False)
    (ROOT/'build/install-test-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof))


if __name__=='__main__':
    main()

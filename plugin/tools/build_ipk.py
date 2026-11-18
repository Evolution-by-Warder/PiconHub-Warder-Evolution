#!/usr/bin/env python3
"""Build a deterministic development IPK from the Warder/Chocholousek runtime."""
import argparse
import gzip
import hashlib
import io
import json
import pathlib
import runpy
import subprocess
import sys
import tarfile
import tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"src/Plugins/Extensions/WarderPiconHub"
PACKAGE="enigma2-plugin-extensions-piconhub-warder-evolution"
DOWNLOAD_PREFIX="enigma2-plugin-extensions-piconhub"
INSTALL_ROOT="usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub"


def archive(entries):
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode="w",format=tarfile.GNU_FORMAT) as output:
        directories=set()
        for name,data,mode in sorted(entries):
            for parent in reversed(pathlib.PurePosixPath(name).parents):
                if str(parent)=="." or str(parent) in directories:continue
                info=tarfile.TarInfo("./"+str(parent));info.type=tarfile.DIRTYPE;info.mode=0o755;info.mtime=0
                output.addfile(info);directories.add(str(parent))
            info=tarfile.TarInfo("./"+name);info.mode=mode;info.mtime=0;info.size=len(data)
            output.addfile(info,io.BytesIO(data))
    compressed=io.BytesIO()
    with gzip.GzipFile(fileobj=compressed,mode="wb",filename="",mtime=0) as stream:
        stream.write(raw.getvalue())
    return compressed.getvalue()


def ar(entries):
    output=bytearray(b"!<arch>\n")
    for name,data in entries:
        output.extend(("%-16s%-12s%-6s%-6s%-8s%-10s`\n" % (name+"/",0,0,0,"100644",len(data))).encode())
        output.extend(data)
        if len(data)%2:output.extend(b"\n")
    return bytes(output)


def revision():
    try:
        value=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
        dirty=subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).strip()
        return value+("-dirty" if dirty else "")
    except (OSError,subprocess.CalledProcessError):
        return "unversioned-development-tree"


def build(destination,source_revision=None):
    version=(RUNTIME/"version.txt").read_text().strip()
    runpy.run_path(str(RUNTIME/"warder_update.py"))["version_key"](version)
    metadata=json.loads((ROOT/"project.json").read_text())
    if version!=metadata["development_version"]:raise ValueError("Package and runtime version differ")
    selectors=json.loads((RUNTIME/"data/skin-menu.json").read_text())["selectors"]
    missing=[row["selector"] for row in selectors
             if not (RUNTIME/"images/selectors"/(row["selector"]+".png")).is_file()]
    if missing:raise ValueError("Selector icons missing: "+", ".join(missing))
    control=("Package: %s\nVersion: %s\nArchitecture: all\nSection: extra\nPriority: optional\n"
             "Maintainer: Warder Evolution\n"
             "Depends: enigma2, python3-core, python3-compression, python3-crypt, python3-datetime, python3-fcntl, python3-io, python3-json, python3-netclient, python3-threading, python3-xml\n"
             "Conflicts: enigma2-plugin-extensions-chocholousek-picons\n"
             "Replaces: enigma2-plugin-extensions-chocholousek-picons\n"
             "Homepage: https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution\n"
             "Description: Download and manage picons.\n") % (PACKAGE,version)
    # Only print lifecycle banners; preserve legacy migration and integrity checks.
    preinst='''#!/bin/sh
if [ -z "${D:-}" ]; then
    case "${1:-}" in
        install|upgrade)
            echo "******************************************************************"
            echo "                    PiconHub Warder Evolution"
            echo "******************************************************************"
            if [ "${1:-}" = upgrade ]; then
                echo "Preparing PiconHub Warder Evolution upgrade/reinstall..."
            else
                echo "Preparing PiconHub Warder Evolution installation/reinstall..."
            fi
            echo "Existing PiconHub settings, profiles and picons will be preserved."
            echo "******************************************************************"
            ;;
    esac
    old=/usr/lib/enigma2/python/Plugins/Extensions/ChocholousekPicons
    new=/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub
    if { [ -f "$old/version.txt" ] || [ -f "$old/plugin.py" ]; } && [ ! -f "$new/version.txt" ]; then
        mkdir -p /var/lib/warder-piconhub || exit 1
        touch /var/lib/warder-piconhub/legacy-transition-needed || exit 1
    fi
fi
exit 0
'''
    postinst='''#!/bin/sh
if [ -z "${D:-}" ]; then
    for log in /tmp/piconhub-picons.log /tmp/chocholousekpicons.log /tmp/chocholousekpicons-cmd.log; do
        if [ -f "$log" ] && [ ! -L "$log" ]; then rm -f "$log"; fi
    done
    python3 /usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/warder_migrate.py || exit 1
    python3 /usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/warder_update.py --verify-installed-files || exit 1
    echo "******************************************************************"
    echo "Install/upgrade/reinstall finished: PiconHub Warder Evolution"
    echo "Existing PiconHub settings, profiles and picons were preserved."
    echo "Please restart GUI to activate changes."
    echo "******************************************************************"
fi
exit 0
'''
    prerm='''#!/bin/sh
# Upgrade must not report that the plugin has been uninstalled.
[ -z "${D:-}" ] || exit 0
case "${1:-}" in
    remove|purge)
        echo "******************************************************************"
        echo "                    PiconHub Warder Evolution"
        echo "******************************************************************"
        echo "Removing PiconHub Warder Evolution plugin files..."
        echo "Existing user settings, profiles and picons will remain untouched."
        echo "******************************************************************"
        ;;
    upgrade|deconfigure)
        echo "******************************************************************"
        echo "Preparing PiconHub Warder Evolution upgrade/reinstall..."
        echo "******************************************************************"
        ;;
esac
exit 0
'''
    postrm='''#!/bin/sh
# Do not announce an uninstall during upgrade or failed upgrade.
[ -z "${D:-}" ] || exit 0
case "${1:-}" in
    remove|purge)
        echo "******************************************************************"
        echo "Removal finished: PiconHub Warder Evolution"
        echo "Saved PiconHub user settings, profiles and picons were left intact."
        echo "Please restart GUI to activate changes."
        echo "******************************************************************"
        ;;
esac
exit 0
'''
    entries=[]
    for path in sorted(RUNTIME.rglob("*")):
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts and path.suffix not in (".pyc",".pyo"):
            entries.append((INSTALL_ROOT+"/"+path.relative_to(RUNTIME).as_posix(),path.read_bytes(),0o644))
    # Keep this path in the package manifest so opkg never removes it as an
    # obsolete file while a pre-rename GUI is still reading it every second.
    entries.append(("usr/lib/enigma2/python/Plugins/Extensions/ChocholousekPicons/version.txt",
                    (version+"\n").encode(),0o644))
    notes_path=ROOT/"update/RELEASE-NOTES.i18n.json"
    notes=json.loads(notes_path.read_text(encoding="utf-8"))
    if notes.get("version")!=version:raise ValueError("Release notes and runtime version differ")
    entries.append((INSTALL_ROOT+"/data/release-notes.json",notes_path.read_bytes(),0o644))
    source={"version":version,"source_revision":source_revision or revision(),"receiver_tested":False}
    entries.append((INSTALL_ROOT+"/build.json",(json.dumps(source,indent=2)+"\n").encode(),0o644))
    with tempfile.TemporaryDirectory() as temporary:
        for po in sorted((RUNTIME/"locale").rglob("*.po")):
            mo=pathlib.Path(temporary)/"translation.mo"
            subprocess.run([sys.executable,str(ROOT/"tools/msgfmt.py"),"-o",str(mo),str(po)],check=True,capture_output=True)
            entries.append((INSTALL_ROOT+"/"+po.relative_to(RUNTIME).with_suffix(".mo").as_posix(),mo.read_bytes(),0o644))
    data=ar((("debian-binary",b"2.0\n"),("control.tar.gz",archive((("control",control.encode(),0o644),("preinst",preinst.encode(),0o755),("postinst",postinst.encode(),0o755),("prerm",prerm.encode(),0o755),("postrm",postrm.encode(),0o755)))),
             ("data.tar.gz",archive(entries))))
    destination=pathlib.Path(destination);destination.mkdir(parents=True,exist_ok=True)
    path=destination/(DOWNLOAD_PREFIX+"_"+version+"_all.ipk");path.write_bytes(data)
    checksum=hashlib.sha256(data).hexdigest()
    path.with_suffix(path.suffix+".sha256").write_text(checksum+"  "+path.name+"\n")
    # Public download name is independent of opkg's installed package identity.
    download=destination/("enigma2-plugin-extensions-piconhub_"+version+"_all.ipk")
    download.write_bytes(data)
    download.with_suffix(".ipk.sha256").write_text(checksum+"  "+download.name+"\n")
    return path,checksum


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=pathlib.Path,default=ROOT/"build")
    parser.add_argument("--revision")
    args=parser.parse_args()
    path,checksum=build(args.output,args.revision)
    print(path.with_name("enigma2-plugin-extensions-piconhub_"+(RUNTIME/"version.txt").read_text().strip()+"_all.ipk"))
    print("SHA256",checksum)

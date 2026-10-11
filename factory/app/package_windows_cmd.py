"""Build one self-extracting CMD launcher around a tested Windows executable."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import zipfile

EXE_NAME = 'WARDER-PICON-FACTORY.exe'
OFFSET_MARKER = 'set "WARDER_PAYLOAD_OFFSET=0000000000"'
PS_MARKER = '__PS_INSTALL_CODE__'

_INSTALL_SCRIPT = r'''$ErrorActionPreference='Stop'
$workspace='D:\WARDER-PICON-FACTORY'
$required=@('00-STATE','01-SOURCES','02-ORIGINALS','03-REGISTRY','04-WORK','05-QA','06-OUTPUT','07-PUBLISH-STAGING','08-REPORTS','09-LOGS','10-TOOLS','11-APP','12-ARCHIVE')
$missing=@()
if (-not (Test-Path -LiteralPath $workspace -PathType Container)) {
  Write-Host ('WARDER read-only preflight failed. No workspace files were changed. Root is unavailable: '+$workspace)
  exit 3
}
$rootItem=Get-Item -LiteralPath $workspace -Force
if (($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
  Write-Host ('WARDER read-only preflight failed. No workspace files were changed. Root is a reparse point: '+$workspace)
  exit 3
}
foreach($name in $required) {
  $path=Join-Path $workspace $name
  if (-not (Test-Path -LiteralPath $path -PathType Container)) { $missing += $name; continue }
  $item=Get-Item -LiteralPath $path -Force
  if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { $missing += ($name+' (reparse point)') }
  try {
    Get-ChildItem -LiteralPath $path -Force -Recurse -ErrorAction Stop | ForEach-Object {
      if (($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { $missing += ($name+' contains reparse point '+$_.FullName) }
    }
  } catch { $missing += ($name+' (unreadable: '+$_.Exception.GetType().Name+')') }
}
if ($missing.Count -gt 0) {
  Write-Host ('WARDER read-only preflight failed. No workspace files were changed. Missing or unsafe: '+($missing -join ', '))
  exit 3
}
$root=$env:WARDER_APP_DIR
$stage=$root+'.stage-'+[guid]::NewGuid().ToString('N')
$zip=Join-Path $env:TEMP ('warder-factory-'+[guid]::NewGuid().ToString('N')+'.zip')
$previous=$null
try {
  New-Item -ItemType Directory -Path $stage -Force | Out-Null
  $src=[IO.File]::OpenRead($env:WARDER_CMD_FILE)
  try {
    $src.Position=[long]$env:WARDER_PAYLOAD_OFFSET
    $dst=[IO.File]::Create($zip)
    try { $src.CopyTo($dst) } finally { $dst.Dispose() }
  } finally { $src.Dispose() }
  Expand-Archive -LiteralPath $zip -DestinationPath $stage -Force
  $new=Join-Path $stage 'WARDER-PICON-FACTORY.exe'
  $sha=[Security.Cryptography.SHA256]::Create()
  try { $actual=([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($new)))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
  if ($actual -ne $env:WARDER_SHA256) { throw 'Factory executable SHA-256 mismatch' }
  if (Test-Path -LiteralPath $root) {
    $previous=$root+'.previous-'+[guid]::NewGuid().ToString('N')
    Move-Item -LiteralPath $root -Destination $previous
  }
  Move-Item -LiteralPath $stage -Destination $root
} catch {
  [IO.File]::AppendAllText($env:WARDER_LOG,((Get-Date -Format o)+' '+$_.Exception.Message+[Environment]::NewLine))
  if ($previous -and (Test-Path -LiteralPath $previous) -and -not (Test-Path -LiteralPath $root)) {
    Move-Item -LiteralPath $previous -Destination $root
  }
  exit 1
} finally {
  if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
  if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
}'''


def _encoded_install_script() -> str:
    return base64.b64encode(_INSTALL_SCRIPT.encode('utf-16le')).decode('ascii')


def _launcher(version: str, digest: str, offset: int) -> bytes:
    text = r'''@echo off
setlocal EnableExtensions
set "WARDER_VERSION=__VERSION__"
set "WARDER_SHA256=__SHA256__"
set "WARDER_PAYLOAD_OFFSET=0000000000"
set "WARDER_CMD_FILE=%~f0"
set "WARDER_PICON_FACTORY_ROOT=D:\WARDER-PICON-FACTORY"
set "WARDER_APP_DIR=%WARDER_PICON_FACTORY_ROOT%\11-APP\WARDER-PICON-FACTORY"
set "WARDER_EXE=%WARDER_APP_DIR%\WARDER-PICON-FACTORY.exe"
set "WARDER_LOG_DIR=%WARDER_PICON_FACTORY_ROOT%\09-LOGS"
set "WARDER_LOG=%WARDER_LOG_DIR%\installer.log"
if not exist "%WARDER_EXE%" goto install
for /f "usebackq delims=" %%H in (`certutil -hashfile "%WARDER_EXE%" SHA256 ^| findstr /r /v "^CertUtil ^SHA256 ^$"`) do set "WARDER_CURRENT_SHA=%%H"
set "WARDER_CURRENT_SHA=%WARDER_CURRENT_SHA: =%"
if /i "%WARDER_CURRENT_SHA%"=="%WARDER_SHA256%" goto launch
:install
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand __PS_INSTALL_CODE__
if errorlevel 1 goto failed
:launch
start "" "%WARDER_EXE%"
exit /b 0
:failed
echo WARDER PICON FACTORY installer stopped. Read-only preflight must find the original D:\WARDER-PICON-FACTORY structure. No fallback root was created.
if exist "%WARDER_LOG%" echo Installer diagnostic: "%WARDER_LOG%"
pause
exit /b 1
exit /b 0
:: WARDER-PICON-FACTORY-PAYLOAD
'''
    text = (text.replace('__VERSION__', version).replace('__SHA256__', digest)
            .replace(PS_MARKER, _encoded_install_script()))
    if PS_MARKER in text:
        raise ValueError('PowerShell installation script was not embedded')
    if text.count(OFFSET_MARKER) != 1:
        raise ValueError('Launcher offset marker is missing or duplicated')
    text = text.replace(OFFSET_MARKER, f'set "WARDER_PAYLOAD_OFFSET={offset:010d}"')
    return text.replace('\n', '\r\n').encode('ascii')


def build_launcher(exe_path, output_path, version):
    exe_path, output_path = Path(exe_path), Path(output_path)
    if not exe_path.is_file() or exe_path.is_symlink():
        raise ValueError('Windows executable is missing or unsafe')
    if not isinstance(version, str) or not re.fullmatch(r'factory-v\d+\.\d+\.\d+', version):
        raise ValueError('Invalid Factory version')
    data = exe_path.read_bytes()
    if not data.startswith(b'MZ') or not data:
        raise ValueError('Input is not a Windows PE executable')
    digest = hashlib.sha256(data).hexdigest()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_zip = output_path.with_suffix('.payload.zip.tmp')
    try:
        with zipfile.ZipFile(temporary_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(EXE_NAME, data)
            archive.writestr('factory-payload.json', json.dumps(
                {'version': version, 'executable': EXE_NAME, 'sha256': digest},
                sort_keys=True) + '\n')
        with zipfile.ZipFile(temporary_zip) as archive:
            if archive.testzip() is not None:
                raise ValueError('Generated launcher payload is corrupt')
        # The fixed-width offset keeps the final prefix byte length stable.
        prefix = _launcher(version, digest, 0)
        offset = len(prefix)
        launcher = _launcher(version, digest, offset)
        if len(prefix) != len(launcher) or offset > 9_999_999_999:
            raise ValueError('Launcher payload offset is invalid')
        with output_path.open('wb') as stream:
            stream.write(launcher)
            stream.write(temporary_zip.read_bytes())
            stream.flush()
        return {'path': str(output_path), 'size': output_path.stat().st_size,
                'sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
                'executable_sha256': digest, 'payload_offset': offset}
    finally:
        temporary_zip.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    print(json.dumps(build_launcher(args.exe, args.output, args.version), indent=2))


if __name__ == '__main__':
    main()

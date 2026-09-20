#!/usr/bin/env python3
"""Inspect installer/archive contents without running privileged install scripts."""
# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DRIVER = 'Library/Printers/DellC1660wNative/'
PPD = 'Library/Printers/PPDs/Contents/Resources/Dell-C1660w-Native.ppd'
EXPECTED = {DRIVER + name for name in ['filter/rastertohbpl1', 'LICENSE', 'VERSION',
            'INSTALL-MARKER', 'README.md', 'UPSTREAM.md', 'scripts/common.sh',
            'scripts/setup.sh', 'scripts/diagnose.sh', 'scripts/uninstall.sh']} | {PPD}


def command(*args):
    return subprocess.check_output([str(a) for a in args], stderr=subprocess.STDOUT, text=True)


def check(directory):
    metadata = json.loads((directory / 'release.json').read_text())
    version = metadata['version']
    assert metadata['channel'] == 'release'
    evidence = metadata['hardware_validation']
    assert evidence['status'] == 'partial' and evidence['evidence'] == 'user_report'
    assert evidence['full_acceptance_complete'] is False
    assert metadata['architecture'] == 'arm64' and metadata['minimum_macos'] == '26.0'
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert Path(name).name == name
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, name
    listed = {line.split('  ',1)[1] for line in (directory/'SHA256SUMS').read_text().splitlines()}
    assert listed == {p.name for p in directory.iterdir()} - {'SHA256SUMS'}
    package = directory / metadata['package']
    source = directory / metadata['source_archive']
    assert hashlib.sha256(package.read_bytes()).hexdigest() == metadata['package_sha256']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == metadata['source_sha256']
    prefix = f'DellC1660wNative-{version}/'
    with tarfile.open(source) as archive:
        members = archive.getmembers()
        for member in members:
            assert member.name.startswith(prefix) and '..' not in Path(member.name).parts
            assert member.isfile() or member.isdir()
            assert member.uid == member.gid == 0 and member.uname == member.gname == ''
            assert member.mtime == 0
            rel = member.name[len(prefix):]
            assert not any(p in {'build','dist','.git','__pycache__'} for p in Path(rel).parts)
            assert Path(rel).suffix.lower() not in {'.dmg','.pkg','.p12','.p8','.pyc','.key'}
        sources = {m.name[len(prefix):]: archive.extractfile(m).read() for m in members if m.isfile()}
    for required in ['VERSION','LICENSE','Makefile','README.md','src/hbpl1.c','src/hbpl1.h',
                     'src/rastertohbpl1.c','scripts/version_header.py','scripts/install.sh',
                     'docs/UPSTREAM.md','vendor/foo2zjs/foo2hbpl1.c','tests/test_driver.py']:
        assert required in sources, required
    assert sources['VERSION'].decode().strip() == version

    with tempfile.TemporaryDirectory(prefix='pkg-inspect-') as temp:
        expanded = Path(temp) / 'expanded'
        command('pkgutil', '--expand-full', package, expanded)
        xml = ET.parse(expanded / 'Distribution').getroot()
        assert xml.find('options').get('hostArchitectures') == 'arm64'
        assert xml.find('domains').get('enable_anywhere') == 'false'
        assert xml.find('domains').get('enable_currentUserHome') == 'false'
        assert xml.find('.//os-version').get('min') == '26.0'
        payloads = list(expanded.rglob('Payload'))
        assert len(payloads) == 1 and payloads[0].is_dir()
        payload = payloads[0]
        actual = {p.relative_to(payload).as_posix() for p in payload.rglob('*') if p.is_file()}
        assert actual == EXPECTED, (actual - EXPECTED, EXPECTED - actual)
        assert not any(p.is_symlink() for p in payload.rglob('*'))
        info = ET.parse(payload.parent / 'PackageInfo').getroot()
        assert info.get('identifier') == metadata['package_identifier']
        assert info.get('version') == version and info.get('install-location') == '/'
        bom = command('lsbom', '-f', '-p', 'fmug', payload.parent/'Bom')
        for line in bom.splitlines():
            fields = line.split('\t')
            assert fields[-2:] == ['0','0'], line
            assert '/._' not in fields[0], line
            mode = int(fields[1],8)
            assert not mode & 0o022, line
        for name in ['setup','diagnose','uninstall','common']:
            file = payload / f'{DRIVER}scripts/{name}.sh'
            assert file.read_bytes() == sources[f'scripts/{name}.sh']
            assert file.stat().st_mode & 0o777 == 0o755
            command('bash','-n',file)
        for script in ['preinstall','postinstall']:
            path = payload.parent/'Scripts'/script
            assert path.read_bytes() == sources[f'packaging/scripts/{script}']
            command('bash','-n',path)
        assert (payload/PPD).read_bytes() == sources['ppd/Dell-C1660w-Native.ppd']
        assert (payload/f'{DRIVER}LICENSE').read_bytes() == sources['LICENSE']
        assert (payload/f'{DRIVER}README.md').read_bytes() == sources['packaging/INSTALLED_README.md']
        assert (payload/f'{DRIVER}VERSION').read_text().strip() == version
        binary = payload/f'{DRIVER}filter/rastertohbpl1'
        command('lipo',binary,'-verify_arch','arm64')
        command('codesign','--verify','--strict',binary)
        assert command(binary,'--version').strip() == f'rastertohbpl1 {version}'
        if metadata['distribution'] == 'unsigned':
            p = subprocess.run(['pkgutil','--check-signature',str(package)],capture_output=True,text=True)
            assert 'no signature' in p.stdout.lower() or 'unsigned' in p.stdout.lower(), p.stdout
        else:
            assert 'Developer ID Installer' in command('pkgutil','--check-signature',package)
            command('xcrun','stapler','validate',package)
    print(f'PASS: {directory.name}: contents, source pairing, versions, signatures, platform checks, root ownership, checksums')


if __name__ == '__main__':
    directories = [Path(sys.argv[1])] if len(sys.argv)>1 else sorted((ROOT/'dist').glob('*'))
    if not directories:
        raise SystemExit('No release artifacts. Run make release first.')
    for directory in directories:
        check(directory)

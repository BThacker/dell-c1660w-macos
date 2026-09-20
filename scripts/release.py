#!/usr/bin/env python3
"""Build and test a source snapshot, then package those exact sources and binaries."""
# SPDX-License-Identifier: GPL-2.0-or-later
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = 'org.dellc1660wnative.driver'
SOURCE_FILES = ['VERSION', 'LICENSE', 'README.md', 'Makefile', '.gitignore',
                'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md']
SOURCE_DIRS = ['src', 'ppd', 'scripts', 'tests', 'docs', 'packaging', 'vendor', '.github']


def run(*args, cwd=None, **kwargs):
    return subprocess.run([str(a) for a in args], cwd=cwd, check=True, **kwargs)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(destination):
    for name in SOURCE_FILES + SOURCE_DIRS:
        path = ROOT / name
        if path.is_symlink():
            raise SystemExit(f'Refusing source symlink: {name}')
        if path.is_dir():
            for child in path.rglob('*'):
                if child.is_symlink():
                    raise SystemExit(f'Refusing source symlink: {child}')
            shutil.copytree(path, destination / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        else:
            shutil.copy2(path, destination / name)
    # Fail closed if a future contributor drops credentials or vendor installers
    # inside an otherwise permitted source directory.
    for path in destination.rglob('*'):
        if path.is_file() and (path.suffix.lower() in {'.dmg', '.pkg', '.p12', '.p8', '.key'}
                               or path.name.startswith('.env')):
            raise SystemExit(f'Forbidden release input: {path.name}')


def source_archive(tree, output, name):
    # Stable archive metadata; no user names, absolute paths, or macOS xattrs.
    with output.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.PAX_FORMAT) as archive:
            for path in sorted(tree.rglob('*')):
                rel = path.relative_to(tree)
                if rel.parts[0] == 'build':
                    continue
                info = archive.gettarinfo(str(path), arcname=f'{name}/{rel.as_posix()}')
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                info.mtime = 0
                info.pax_headers = {}
                info.mode = 0o755 if path.is_dir() or os.access(path, os.X_OK) else 0o644
                if path.is_file():
                    with path.open('rb') as contents:
                        archive.addfile(info, contents)
                else:
                    archive.addfile(info)


def normalize_component(component, payload, work):
    """Strip AppleDouble from the archive, not from protected filesystem xattrs.

    Apple's tools may reattach provenance even after xattr -c. Re-archiving the
    existing CPIO keeps its root ownership and bytes, without copying metadata.
    This happens before signing the enclosing product archive.
    """
    expanded = work / 'component'
    run('pkgutil', '--expand', component, expanded)
    for filename in ['Payload', 'Scripts']:
        original = expanded / filename
        if not original.exists():
            continue
        clean = work / f'{filename}.cpio.gz'
        command = ['tar', '--format=odc', '--no-mac-metadata', '--no-xattrs',
                   '--exclude', '*/._*', '--uid', '0', '--gid', '0', '-czf', clean]
        if original.is_dir():
            run(*command, '-C', original, '.')
            shutil.rmtree(original)
        else:
            run(*command, '@' + str(original))
        shutil.move(clean, original)
    entries = subprocess.check_output(['lsbom', str(expanded/'Bom')], text=True).splitlines()
    entries = [line for line in entries if '/._' not in line.split('\t')[0]]
    listing = work / 'bom.txt'
    listing.write_text('\n'.join(entries) + '\n')
    run('mkbom', '-i', listing, expanded / 'Bom')
    info = ET.parse(expanded / 'PackageInfo')
    info.find('payload').set('numberOfFiles', str(len(entries)))
    size = sum(p.stat().st_size for p in payload.rglob('*') if p.is_file())
    info.find('payload').set('installKBytes', str((size + 1023)//1024))
    info.write(expanded / 'PackageInfo', encoding='utf-8', xml_declaration=True)
    component.unlink()
    # Scripts is already a CPIO stream; pkgutil --flatten would wrap it again.
    # Flat component packages use XAR, with these four standard members.
    run('xar', '--distribution', '--compression=none', '-cf', component,
        'Bom', 'PackageInfo', 'Payload', 'Scripts', cwd=expanded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--signed', action='store_true', help='require Developer ID signatures and notarization')
    args = parser.parse_args()
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise SystemExit('Invalid VERSION')
    identities = {key: os.environ.get(key) for key in
                  ['DEVELOPER_ID_APPLICATION', 'DEVELOPER_ID_INSTALLER', 'NOTARY_PROFILE']}
    if args.signed and not all(identities.values()):
        raise SystemExit('--signed requires DEVELOPER_ID_APPLICATION, DEVELOPER_ID_INSTALLER, and NOTARY_PROFILE')
    kind = 'notarized' if args.signed else 'unsigned'
    name = f'DellC1660wNative-{version}'
    dist = ROOT / 'dist' / f'{version}-{kind}'
    if dist.exists():
        raise SystemExit(f'{dist} already exists; move it aside before rebuilding this release.')
    (ROOT / 'build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='release-', dir=ROOT / 'build') as tmp:
        work = Path(tmp)
        source = work / name
        source.mkdir()
        snapshot(source)
        products = work / 'products'
        products.mkdir()
        archive = products / f'{name}-source.tar.gz'
        source_archive(source, archive, name)
        # This exact copied tree supplies BOTH the archive and all installed code.
        run('make', 'test', 'sanitize', cwd=source)
        payload = work / 'payload'
        run(source / 'scripts/install.sh', '--stage', payload)
        binary = payload / 'Library/Printers/DellC1660wNative/filter/rastertohbpl1'
        if args.signed:
            run('codesign', '--force', '--options', 'runtime', '--timestamp', '--sign',
                identities['DEVELOPER_ID_APPLICATION'], binary)
        run('codesign', '--verify', '--strict', binary)

        component = work / 'driver.pkg'
        run('pkgbuild', '--root', payload, '--identifier', PACKAGE_ID, '--version', version,
            '--install-location', '/', '--ownership', 'recommended',
            '--filter', r'/\._', '--filter', r'/\.DS_Store$',
            '--scripts', source / 'packaging/scripts', component)
        normalize_component(component, payload, work)
        requirements = work / 'requirements.plist'
        requirements.write_bytes(plistlib.dumps({'arch': ['arm64'], 'os': ['26.0']}))
        distribution = work / 'Distribution.xml'
        run('productbuild', '--synthesize', '--product', requirements, '--package', component, distribution)
        tree = ET.parse(distribution)
        xml = tree.getroot()
        ET.SubElement(xml, 'title').text = f'Dell C1660w Native {version}'
        ET.SubElement(xml, 'welcome', {'file': 'welcome.html', 'mime-type': 'text/html'})
        ET.SubElement(xml, 'conclusion', {'file': 'conclusion.html', 'mime-type': 'text/html'})
        ET.SubElement(xml, 'license', {'file': 'LICENSE.txt', 'mime-type': 'text/plain'})
        ET.SubElement(xml, 'domains', {'enable_anywhere': 'false', 'enable_currentUserHome': 'false',
                                      'enable_localSystem': 'true'})
        options = xml.find('options')
        if options is not None:
            options.set('customize', 'never')
        tree.write(distribution, encoding='utf-8', xml_declaration=True)
        resources = work / 'resources'
        resources.mkdir()
        shutil.copy2(source / 'LICENSE', resources / 'LICENSE.txt')
        (resources / 'welcome.html').write_text(f'''<!doctype html><html><meta charset="utf-8"><body>
<h1>Dell C1660w Native {version}</h1><p><b>Provided as is, without warranty. Use at your own risk.</b></p>
<p>To the extent permitted by applicable law. See the license for the full terms.</p>
<p>Independent GPL open-source project; not affiliated with or endorsed by Dell.</p>
<p>Requires Apple Silicon and macOS 26 or later. Color and grayscale, Letter/A4 plain paper,
direct Wi-Fi printing. No Rosetta or Ghostscript required.</p>
<p>Distribution: {kind}. Installs the filter, printer description, management commands, and license.
It does not change your default printer or create a queue. Your printer must already be on Wi-Fi.</p>
</body></html>''')
        (resources / 'conclusion.html').write_text('''<!doctype html><html><meta charset="utf-8"><body>
<h1>Connect your printer</h1><p>Open Terminal and replace PRINTER_IP below with your printer's address:</p>
<pre>sudo /Library/Printers/DellC1660wNative/scripts/setup.sh PRINTER_IP</pre>
<p>Select <b>Dell C1660w Native</b> in the print dialog.</p>
<p>After an upgrade, rerun setup to refresh the queue's printer description (defaults return to Letter/color).</p>
<p>Diagnostics:</p><pre>/Library/Printers/DellC1660wNative/scripts/diagnose.sh PRINTER_IP</pre>
<p>Uninstall:</p><pre>sudo /Library/Printers/DellC1660wNative/scripts/uninstall.sh</pre>
<p>See /Library/Printers/DellC1660wNative/README.md and the release's matching source archive.</p>
</body></html>''')
        package = products / f'{name}-arm64-{kind}.pkg'
        command = ['productbuild', '--distribution', distribution, '--package-path', work,
                   '--resources', resources]
        if args.signed:
            command += ['--sign', identities['DEVELOPER_ID_INSTALLER'], '--timestamp']
        run(*command, package)
        if args.signed:
            run('xcrun', 'notarytool', 'submit', package, '--keychain-profile', identities['NOTARY_PROFILE'], '--wait')
            run('xcrun', 'stapler', 'staple', package)
            run('xcrun', 'stapler', 'validate', package)
            run('spctl', '--assess', '--type', 'install', '--verbose=2', package)
        metadata = {'project': 'Dell C1660w Native', 'version': version,
                    'channel': 'release', 'architecture': 'arm64', 'minimum_macos': '26.0',
                    'hardware_validation': {
                        'status': 'partial',
                        'reported_on': '2026-09-20',
                        'evidence': 'user_report',
                        'model': 'Dell C1660w',
                        'result': 'One color page printed successfully over Wi-Fi from the normal macOS print dialog',
                        'full_acceptance_complete': False,
                    },
                    'warranty': 'as-is; no warranty; use at your own risk; see LICENSE',
                    'distribution': kind,
                    'package_identifier': PACKAGE_ID,
                    'source_archive': archive.name, 'source_sha256': sha256(archive),
                    'package': package.name, 'package_sha256': sha256(package),
                    'build_macos': subprocess.check_output(['sw_vers','-productVersion'],text=True).strip()}
        (products / 'release.json').write_text(json.dumps(metadata, indent=2) + '\n')
        notes = f'''# Dell C1660w Native {version}

Native Apple Silicon driver for macOS 26+, using the normal print dialog over Wi-Fi.
Color/grayscale, Letter/A4 plain paper, page selection, landscape layout, and copies.

**Basic color printing confirmed by a user report (2026-09-20):** one color page
printed successfully on a Dell C1660w over Wi-Fi from the normal macOS print dialog.
See docs/VALIDATION.md in the source archive for the scope of testing.

## Warranty

Provided as is, without warranty of any kind, to the extent permitted by applicable law. Use at your own risk. See LICENSE for the full terms.

## Installation

The installer is **{kind}**. Unsigned downloads may be blocked by Gatekeeper;
building from the matching source archive is an alternative.

Open the PKG to install. Then run:

    sudo /Library/Printers/DellC1660wNative/scripts/setup.sh PRINTER_IP

Replace PRINTER_IP with the printer's local address. For removal:

    sudo /Library/Printers/DellC1660wNative/scripts/uninstall.sh

The source archive includes the complete corresponding GPL-2.0-or-later source,
build/installation scripts, license, upstream notices, and hardware test checklist.
Keep the source archive available with this binary release. Verify downloads with
`shasum -a 256 -c SHA256SUMS` after downloading every listed artifact.

Independent community project; not affiliated with Dell. No proprietary Dell
installer, driver binaries, or artwork are included.
'''
        (products / 'RELEASE_NOTES.md').write_text(notes)
        (products / 'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in sorted(products.iterdir())))
        run('python3', source / 'tests/test_packaging.py', products)
        dist.parent.mkdir(exist_ok=True)
        shutil.move(str(products), dist)
    print(f'Release ready: {dist}')


if __name__ == '__main__':
    main()

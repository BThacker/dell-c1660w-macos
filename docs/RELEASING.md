# Releasing

## Build

```sh
make release
```

Tests a source snapshot and packages that exact code. Output in
`dist/VERSION-unsigned/`: installer, corresponding source archive, checksums,
metadata, and release notes. Existing output is preserved; move it aside to rebuild.
`make package-test` inspects packages without installing them.

Always publish the matching source archive beside the installer and preserve GPL
attribution. Dell proprietary files and signing credentials must stay excluded.
Bump `VERSION` and update CHANGELOG.md for a new version. Keep package identifier
`org.dellc1660wnative.driver` stable; the PPD has its own format revision.

The installer requires Apple Silicon/macOS 26+, writes under `/Library/Printers`,
and includes setup, diagnostics, and uninstall commands. Queue setup is separate.
Upgrades require rerunning setup to refresh the PPD, restoring Letter/color defaults.

## Sign and notarize (optional)

Default packages are unsigned; Gatekeeper may block downloads. For notarized
builds, install Developer ID Application/Installer identities in your keychain
and save credentials with `notarytool store-credentials`:

```sh
export DEVELOPER_ID_APPLICATION='Developer ID Application: YOUR NAME (TEAMID)'
export DEVELOPER_ID_INSTALLER='Developer ID Installer: YOUR NAME (TEAMID)'
export NOTARY_PROFILE='your-saved-notary-profile'
python3 scripts/release.py --signed
```

This signs, notarizes, staples, and verifies the package, then writes
`dist/VERSION-notarized/`. It never falls back to unsigned output. The signed
path still requires validation with real credentials.
[Apple's guide](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow).

## Publish

Create an empty remote repository, review the files, commit, and push `main`.
Enable private vulnerability reporting and require CI for pull requests.

Push a tag matching VERSION to create a **draft release**:

```sh
git tag v1.0.0
git push origin v1.0.0
```

Review and publish the draft manually. Keep the warranty notice and signing
status visible. If using a local notarized build, replace the entire draft artifact
set and notes together; never mix checksums or sources from different builds.

Continue recording hardware results in [VALIDATION.md](VALIDATION.md). Check
clean-machine installation, upgrades, removal, and downloaded-package behavior.

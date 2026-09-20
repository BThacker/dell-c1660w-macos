#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
source "$(dirname "$0")/common.sh"
stage=""
if [[ $# == 2 && "$1" == --stage ]]; then
    [[ "$2" == /* && "$2" != / ]] || die "Stage must be an absolute directory other than /."
    stage="${2%/}"
elif [[ $# != 0 ]]; then die "Usage: $0 [--stage /absolute/directory]";
else require_root; fi
[[ -x "$PROJECT_ROOT/build/rastertohbpl1" ]] || die "Run make first (without sudo)."
[[ "$(uname -m)" == arm64 ]] || die "This release targets Apple Silicon."
/usr/bin/lipo "$PROJECT_ROOT/build/rastertohbpl1" -verify_arch arm64
/usr/bin/codesign --verify --strict "$PROJECT_ROOT/build/rastertohbpl1"
/usr/bin/cupstestppd -W filters "$PROJECT_ROOT/ppd/Dell-C1660w-Native.ppd"
dest="$stage$DRIVER_DIR"
[[ ! -L "$dest" && ! -L "$stage$PPD_PATH" ]] || die "Refusing a symbolic-link destination."
if [[ -e "$dest" && ! -f "$dest/INSTALL-MARKER" ]]; then
    die "Existing unrecognized driver directory: $dest"
fi
/usr/bin/install -d -m 755 "$dest/filter" "$(dirname "$stage$PPD_PATH")"
/usr/bin/install -m 755 "$PROJECT_ROOT/build/rastertohbpl1" "$dest/filter/rastertohbpl1"
/usr/bin/install -m 644 "$PROJECT_ROOT/ppd/Dell-C1660w-Native.ppd" "$stage$PPD_PATH"
/usr/bin/install -m 644 "$PROJECT_ROOT/LICENSE" "$dest/LICENSE"
/usr/bin/install -m 644 "$PROJECT_ROOT/VERSION" "$dest/VERSION"
/usr/bin/install -m 644 "$PROJECT_ROOT/packaging/INSTALLED_README.md" "$dest/README.md"
/usr/bin/install -m 644 "$PROJECT_ROOT/docs/UPSTREAM.md" "$dest/UPSTREAM.md"
/usr/bin/install -d -m 755 "$dest/scripts"
for script in common setup diagnose uninstall; do
    /usr/bin/install -m 755 "$PROJECT_ROOT/scripts/$script.sh" "$dest/scripts/$script.sh"
done
printf 'DellC1660wNative %s\n' "$(cat "$PROJECT_ROOT/VERSION")" > "$dest/INSTALL-MARKER"
chmod 644 "$dest/INSTALL-MARKER"
if [[ -z "$stage" ]]; then
    chown -R root:wheel "$dest"
    chown root:wheel "$PPD_PATH"
    /usr/bin/cupstestppd "$PPD_PATH"
    echo "Installed native driver. Run scripts/setup.sh with the printer host when available."
else
    echo "Staged at $stage (system printing configuration unchanged)."
fi

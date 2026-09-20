#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
source "$(dirname "$0")/common.sh"
[[ $# == 0 ]] || die "Usage: sudo $0"
require_root
[[ ! -L "$DRIVER_DIR" && -f "$DRIVER_DIR/INSTALL-MARKER" ]] || die "No recognized installation found."
if /usr/bin/lpstat -p "$QUEUE" >/dev/null 2>&1; then
    our_queue || die "Queue name belongs to a different driver; refusing to remove it."
    /usr/sbin/lpadmin -x "$QUEUE"
fi
# Remove only our known files; preserve anything else placed in the directory.
rm -f "$DRIVER_DIR/filter/rastertohbpl1" "$DRIVER_DIR/LICENSE" "$DRIVER_DIR/INSTALL-MARKER" \
    "$DRIVER_DIR/VERSION" "$DRIVER_DIR/README.md" "$DRIVER_DIR/UPSTREAM.md"
if [[ -f "$PPD_PATH" ]] && /usr/bin/grep -Fqx '*ModelName: "Dell C1660w Native"' "$PPD_PATH"; then rm -f "$PPD_PATH"; fi
/usr/sbin/pkgutil --forget "$PACKAGE_ID" >/dev/null 2>&1 || true
for script in common setup diagnose uninstall; do rm -f "$DRIVER_DIR/scripts/$script.sh"; done
rmdir "$DRIVER_DIR/filter" "$DRIVER_DIR/scripts" "$DRIVER_DIR" 2>/dev/null || true
echo 'Removed the Dell C1660w Native installation.'

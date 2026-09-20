#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
source "$(dirname "$0")/common.sh"
[[ $# -le 1 ]] || die "Usage: $0 [PRINTER_IP_OR_HOSTNAME]"
if [[ $# == 1 ]]; then validate_host "$1"; fi
sw_vers
uname -m
if [[ -x "$DRIVER_DIR/filter/rastertohbpl1" ]]; then
    file "$DRIVER_DIR/filter/rastertohbpl1"
    "$DRIVER_DIR/filter/rastertohbpl1" --version
    /usr/bin/codesign --verify --strict "$DRIVER_DIR/filter/rastertohbpl1"
    /usr/bin/otool -L "$DRIVER_DIR/filter/rastertohbpl1"
else echo "Native driver is not installed."; fi
if [[ -f "$PPD_PATH" ]]; then /usr/bin/cupstestppd "$PPD_PATH"; fi
/usr/bin/lpstat -r || true
/usr/bin/lpstat -l -p "$QUEUE" || true
/usr/bin/lpstat -v "$QUEUE" || true
/usr/bin/lpstat -o "$QUEUE" || true
if [[ $# == 1 ]]; then
    /usr/bin/nc -z -G 3 -w 3 "$1" 9100 && echo 'Printer port is reachable.' || die 'Cannot reach printer port 9100.'
fi

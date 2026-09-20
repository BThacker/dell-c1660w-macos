#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRIVER_DIR=/Library/Printers/DellC1660wNative
PPD_PATH=/Library/Printers/PPDs/Contents/Resources/Dell-C1660w-Native.ppd
QUEUE=Dell_C1660w_Native
PACKAGE_ID=org.dellc1660wnative.driver
die() { echo "Error: $*" >&2; exit 1; }
require_root() { [[ $EUID == 0 ]] || die "Run this command with sudo."; }
validate_host() {
    [[ -n "$1" && ${#1} -le 253 && "$1" != *[!a-zA-Z0-9.-]* && "$1" != [-.]* && "$1" != *- ]] ||
        die "Supply an IPv4 address or DNS hostname, without a URL, port, or whitespace."
}
our_queue() {
    [[ -f "/etc/cups/ppd/$QUEUE.ppd" ]] &&
        /usr/bin/grep -Fqx '*ModelName: "Dell C1660w Native"' "/etc/cups/ppd/$QUEUE.ppd"
}

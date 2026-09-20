#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
source "$(dirname "$0")/common.sh"
[[ $# == 1 ]] || die "Usage: sudo $0 PRINTER_IP_OR_HOSTNAME"
validate_host "$1"
require_root
[[ -f "$DRIVER_DIR/INSTALL-MARKER" && -x "$DRIVER_DIR/filter/rastertohbpl1" && -f "$PPD_PATH" ]] || die "Install the driver first."
if /usr/bin/lpstat -p "$QUEUE" >/dev/null 2>&1 && ! our_queue; then
    die "A different printer already uses the queue name $QUEUE."
fi
/usr/sbin/lpadmin -p "$QUEUE" -D 'Dell C1660w Native' -E \
    -v "socket://$1:9100" -P "$PPD_PATH" \
    -o printer-is-shared=false -o PageSize=Letter -o ColorModel=RGB \
    -o printer-error-policy=stop-printer
echo "Queue ready: $QUEUE. Select it in the macOS print dialog."
echo "The default printer has not been changed."

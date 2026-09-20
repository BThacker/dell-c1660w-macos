#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
version = (root / 'VERSION').read_text().strip()
if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
    raise SystemExit('VERSION must contain a numeric major.minor.patch version')
(root / 'build/version.h').write_text(f'#define HBPL_VERSION "{version}"\n')

# Contributing

Fixes and Dell C1660w hardware reports are welcome.

On Apple Silicon with Apple's Command Line Tools and Python 3:

```sh
make test
make sanitize
make release
```

Keep changes focused, add relevant regression coverage, and describe how you
validated them. Follow the [hardware checklist](docs/HARDWARE_TESTS.md) when
reporting prints; include OS/driver versions, firmware, paper, and print settings.
Redact personal documents, job titles, usernames, and network addresses.

Contributions use GPL-2.0-or-later. Preserve attribution and exclude proprietary
Dell files, credentials, and private print jobs.

Maintainers: see [releasing](docs/RELEASING.md).

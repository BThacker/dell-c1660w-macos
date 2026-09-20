# Dell C1660w for macOS

Native Apple Silicon driver for the Dell C1660w. Print over Wi-Fi from the
normal macOS print dialog on macOS 26+ with color/grayscale, Letter/A4, and
600 dpi. No Rosetta, Ghostscript, or old Dell driver.

## Install

Download the arm64 `.pkg` from Releases, then run (replace `PRINTER_IP` with the
printer's Wi-Fi address):

```sh
sudo /Library/Printers/DellC1660wNative/scripts/setup.sh PRINTER_IP
```

Select **Dell C1660w Native** when printing. Rerun setup after upgrading;
defaults return to Letter/color. The installer is unsigned and Gatekeeper may
block it.

Diagnose or remove with:

```sh
/Library/Printers/DellC1660wNative/scripts/diagnose.sh PRINTER_IP
sudo /Library/Printers/DellC1660wNative/scripts/uninstall.sh
```

For a stopped job, check the connection and resume or cancel it in Print Center.

## Build from source

Requires Apple's Command Line Tools (`xcode-select --install`). Run `make`,
`sudo ./scripts/install.sh`, then `sudo ./scripts/setup.sh PRINTER_IP`. For
development use `make test`, `make sanitize`, and `make release`; see
[CONTRIBUTING.md](CONTRIBUTING.md) and [docs/RELEASING.md](docs/RELEASING.md).

## License

[GPL-2.0-or-later](LICENSE), based on Dave Coffin's HBPL1 encoder
([upstream](docs/UPSTREAM.md)). One color print was confirmed on 2026-09-20;
see [validation](docs/VALIDATION.md). USB, duplex, and specialty media are out
of scope. Not affiliated with or endorsed by Dell. Provided as is, without
warranty; use at your own risk.

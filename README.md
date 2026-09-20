# Dell C1660w for macOS

Native Apple Silicon driver for the Dell C1660w. Self-contained, so no Rosetta
(Intel translation), Ghostscript (PDF converter), or Dell software is needed.
Prints over Wi-Fi from the normal macOS print dialog on macOS 26+ with
color/grayscale, Letter/A4, and 600 dpi.

## Install

Download the arm64 `.pkg` from Releases and open it. Then run (replace
`PRINTER_IP` with the printer's Wi-Fi address):

```sh
sudo /Library/Printers/DellC1660wNative/scripts/setup.sh PRINTER_IP
```

Select **Dell C1660w Native** when printing. After an upgrade, run setup again;
this restores the Letter/color defaults.

### If macOS blocks the installer

The package is unsigned, so macOS may warn that it is from an unidentified
developer. Try to open it, then allow it under **System Settings → Privacy &
Security → Security → Open Anyway**. From Terminal you can instead clear the
download flag and open it again:

```sh
xattr -d com.apple.quarantine ~/Downloads/DellC1660wNative-*.pkg
```

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

## iOS and iPadOS

This driver covers macOS only. To print from iPhone or iPad, run the AirPrint
bridge: [dell-c1660w-airprint](https://github.com/BThacker/dell-c1660w-airprint).

## License

[GPL-2.0-or-later](LICENSE), based on Dave Coffin's HBPL1 encoder
([upstream](docs/UPSTREAM.md)). Color printing was confirmed on a real C1660w on
2026-09-20; see [validation](docs/VALIDATION.md). USB, duplex, and specialty
media are out of scope. Not affiliated with or endorsed by Dell. Provided as is,
without warranty; use at your own risk.

# Dell C1660w Native

Wi-Fi printing for Apple Silicon Macs on macOS 26+. Color/grayscale,
Letter/A4 plain paper, 600 dpi. No developer tools required.

## Setup

Connect the printer to your Wi-Fi network. Replace `PRINTER_IP` with its address:

```sh
sudo /Library/Printers/DellC1660wNative/scripts/setup.sh PRINTER_IP
```

Select **Dell C1660w Native** in the print dialog. After an upgrade, rerun setup;
this restores Letter/color defaults.

## Diagnose or uninstall

```sh
/Library/Printers/DellC1660wNative/scripts/diagnose.sh PRINTER_IP
sudo /Library/Printers/DellC1660wNative/scripts/uninstall.sh
```

For a stopped job, check the connection and resume or cancel it in Print Center.

## Reinstalling from a download

Downloads are unsigned, so macOS may warn that the package is from an
unidentified developer. Allow it under **System Settings → Privacy & Security →
Security → Open Anyway**, or clear the download flag and open it again:

```sh
xattr -d com.apple.quarantine ~/Downloads/DellC1660wNative-*.pkg
```

## License

GPL-2.0-or-later; see LICENSE and UPSTREAM.md. Matching source is supplied as
`DellC1660wNative-VERSION-source.tar.gz` alongside the installer. Distributors
must keep it available with the binary. Not affiliated with or endorsed by Dell.

Provided as is, without warranty, to the extent permitted by applicable law.
Use at your own risk. See LICENSE for full terms.

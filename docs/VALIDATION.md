# Validation

## Software — 2026-09-14

Tested on macOS 26.5.1 (25F80), Apple Silicon:

- 12 tests passed, including the complete macOS PDF-to-HBPL filter chain.
- 10 applicable sanitizer tests passed; two PDF integration tests run separately.
- PPD validation, staged installation, and native binary/signature checks passed.
- Runtime dependencies are system CUPS and libSystem only.

Coverage includes RGB/grayscale, Letter/A4, margins, blank/multiple pages,
landscape rotation, page ranges, copies/collation, malformed input, cancellation,
and output failures. A separate decoder checks generated HBPL page data.
Release builds repeat these checks and inspect package contents, ownership,
source pairing, and checksums.

## Hardware — 2026-09-20

The user reported **one successful color page on a Dell C1660w over Wi-Fi through
the normal macOS print dialog**.

Application, paper size, firmware, installed driver version, installation method,
and exact macOS version were not recorded. This confirms basic printing on that
setup; it does not establish detailed color quality or public-installer behavior.

## Additional coverage needed

Grayscale, both paper sizes, landscape, multiple pages/copies, color accuracy,
margins, cancellation, sleep/offline recovery, clean installs/upgrades/removal,
and additional applications or system versions.

See the [hardware checklist](HARDWARE_TESTS.md).

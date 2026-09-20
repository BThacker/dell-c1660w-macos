# Upstream provenance

Repository: https://github.com/mikerr/foo2zjs

Pinned revision: `5bf0142d1e3d4363684608ac42933510d3b66e27`

The unmodified source files are retained under `vendor/foo2zjs` for comparison.
They are reference material, not installed or compiled into the production
filter. The production adaptation is `src/hbpl1.c`.

| File | SHA-256 |
| --- | --- |
| `foo2hbpl1.c` | `8568b79110859fb1de0db02ec4666aa92f7ce8125967f8c20d05694f3ba33c26` |
| `hbpldecode.c` | `2c0fba0cc5c057da0b984f26f9c6fd9e17d9b037663928ec261801aa727434c6` |
| `COPYING` | `2755e341424617537485c1ff51b1cb43133ba2323c674ef87bf7192510cb2ad1` |

Dave Coffin wrote the HBPL1 encoder in March 2014 and contributed HBPL1 decoding
to `hbpldecode.c`. That file also credits Rick Richardson and Peter Korf.
Both source files specify GPL version 2 or later. The project LICENSE contains
the GPL text from upstream COPYING. The unrelated proprietary assets named in
upstream COPYING are not included in this project.

## Native port changes

- Replace the PBM/PGM/PPM/PAM command-line parser with CUPS Raster API input.
- Retain HBPL1 framing, compression, KCMY channel order, and RGB conversion.
- Iterate paper-size triplets by three, fixing the original out-of-bounds lookup.
- Limit match search to remaining pixels; allocate guard rows explicitly.
- Replace aliasing-sensitive integer loads with byte comparisons and implement
  byte-difference wrapping independently of the platform's default `char` sign.
- Replace negative left shifts and use unsigned little-endian serialization.
- Check allocation growth and writes; support interruption and sanitize job labels.
- Construct full-page canvases using the raster imageable area and Dell margins;
  keep hardware copy count at one after macOS performs copy expansion.
- Use a buffered CUPS input callback to handle cancellation and distinguish
  incomplete trailing headers from clean EOF. No private CUPS structs are used.

The independent test decoder reuses the upstream decoding algorithm, with bounded
bitstreams and dimension checks, and omits the unrelated HBPL2/JBIG code.

## Dell reference

Local image: `Printer C1760 C1660 Installer Dell A02 MAC.dmg`

The C1660w PPD identifies driver v1.4 and 600 dpi. Its Letter dimensions are
612 × 792 points; A4 is 595 × 842 points. Both use 11.62-point margins.
The original HBPL filter contains PowerPC, i386, and x86_64 executable slices,
with no arm64 slice. No Dell code, lookup tables, icons, or dialog plugins are
included in the new driver. The PPD is newly written for the supported subset.

## Interfaces

`rastertohbpl1 job-id user title copies options [raster-file]` follows the CUPS
filter calling convention. Raster comes from the named file or stdin, HBPL goes
to stdout, and CUPS diagnostics/page accounting go to stderr. Exit 0 means the
stream was encoded successfully; nonzero means failure or cancellation.

`--version` reports the local driver version. This is a developer utility;
ordinary users should print through CUPS, not invoke the filter directly.

References:

- https://www.cups.org/doc/raster-driver.html
- https://www.cups.org/doc/api-raster.html
- https://www.cups.org/doc/man-filter.html

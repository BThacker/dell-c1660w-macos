# Hardware tests

One successful color page over Wi-Fi through the normal macOS print dialog was
reported on 2026-09-20. [Recorded evidence](VALIDATION.md).

For additional tests, record OS/driver versions, printer firmware, application,
paper, settings, and physical results. Generate sample PDFs with `make test-pages`.

- Print a page from Preview and another application.
- Print `build/test-page.pdf`: check text, RGB patches, grayscale gradient,
  continuous-tone image, border, and page order. Also try a real photograph.
- Test grayscale, Letter/A4 with matching paper, and landscape using
  `build/landscape-test-page.pdf`. For command-line PDFs, use `-o fit-to-page`.
- Select pages 2–3. Print two copies with collation on (1,2,3,1,2,3) and off
  (1,1,2,2,3,3); compare physical counts.
- Cancel a job, then print another. Test sleep, offline errors, and recovery.
- Test installation, upgrade, uninstall, and reinstall; preserve other queues.

Check actual pages, not just Print Center completion. Record failures and redact
private information from shared logs or photographs.

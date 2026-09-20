/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "hbpl1.h"
#include "version.h"
#include <cups/cups.h>
#include <cups/raster.h>
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

volatile sig_atomic_t hbpl1_cancelled;
static void cancel_job(int signal_number) { (void)signal_number; hbpl1_cancelled = 1; }

static int fail(const char *message)
{
    fprintf(stderr, "ERROR: %s\n", message);
    return 1;
}

typedef struct {
    int fd, reading_pixels, compressed, error;
    size_t position, available, delivered;
    unsigned char buffer[65536], magic[4];
} Input;

/* Own the read-ahead buffer so EOF can be distinguished from a partial header.
 * While decompressing, hand CUPS one byte at a time: its private buffer must
 * not swallow the beginning of the next header. Disk reads remain buffered.
 * Uncompressed pixels and headers use bulk transfers. */
static ssize_t input_read(void *context, unsigned char *buffer, size_t length)
{
    Input *input = context;
    if (hbpl1_cancelled) return -1;
    if (input->position == input->available) {
        ssize_t n;
        do { n = read(input->fd, input->buffer, sizeof(input->buffer)); }
        while (n < 0 && errno == EINTR && !hbpl1_cancelled);
        if (n <= 0) { if (n < 0) input->error = 1; return n; }
        input->position = 0;
        input->available = (size_t)n;
    }
    if (input->reading_pixels && input->compressed && length > 1) length = 1;
    size_t n = input->available - input->position;
    if (n > length) n = length;
    memcpy(buffer, input->buffer + input->position, n);
    for (size_t i = 0; i < n && input->delivered + i < 4; ++i)
        input->magic[input->delivered+i] = buffer[i];
    input->position += n;
    input->delivered += n;
    return (ssize_t)n;
}

/* PJL strings must not introduce commands or terminate quoted values. */
static void safe_label(char out[128], const char *in)
{
    size_t i;
    for (i = 0; i < 127 && in[i]; ++i) {
        unsigned char c = (unsigned char)in[i];
        out[i] = c >= 32 && c < 127 && c != '"' && c != '\\' ? (char)c : '_';
    }
    out[i] = 0;
}

static int raster_page(cups_raster_t *raster, const cups_page_header2_t *h,
                       int *job_color)
{
    int color, channels;
    switch (h->cupsColorSpace) {
    case CUPS_CSPACE_RGB: case CUPS_CSPACE_SRGB: color = 1; channels = 3; break;
    case CUPS_CSPACE_W: case CUPS_CSPACE_SW: color = 0; channels = 1; break;
    default: return fail("Unsupported color space; select RGB or Grayscale.");
    }
    if (h->HWResolution[0] != 600 || h->HWResolution[1] != 600 ||
        h->cupsBitsPerColor != 8 || h->cupsBitsPerPixel != (unsigned)channels * 8 ||
        h->cupsColorOrder != CUPS_ORDER_CHUNKED || h->cupsNumColors != (unsigned)channels)
        return fail("Expected 600-dpi, 8-bit chunky RGB or grayscale raster.");
    if (h->Duplex || h->Tumble) return fail("Only single-sided printing is supported.");
    /* Copies must be expanded by the macOS PDF/raster pipeline. */
    if (h->NumCopies > 1) return fail("Copies were not expanded by macOS; check the installed PPD.");
    if (*job_color >= 0 && *job_color != color)
        return fail("Changing color mode within a job is unsupported.");
    *job_color = color;

    double pw = h->cupsPageSize[0] > 0 ? h->cupsPageSize[0] : h->PageSize[0];
    double ph = h->cupsPageSize[1] > 0 ? h->cupsPageSize[1] : h->PageSize[1];
    if (!isfinite(pw) || !isfinite(ph) ||
        !((fabs(pw-612) < 1 && fabs(ph-792) < 1) ||
          (fabs(pw-595) < 1 && fabs(ph-842) < 1)))
        return fail("Only portrait-fed Letter and A4 paper are supported.");
    int width = (int)lround(pw * 600 / 72), height = (int)lround(ph * 600 / 72);
    if (!h->cupsWidth || !h->cupsHeight || h->cupsWidth > (unsigned)width ||
        h->cupsHeight > (unsigned)height ||
        h->cupsBytesPerLine < h->cupsWidth * (unsigned)channels ||
        h->cupsBytesPerLine > (unsigned)(width * channels + 4096))
        return fail("Invalid raster dimensions or row length.");

    int left = 0, top = 0;
    if (h->cupsWidth != (unsigned)width || h->cupsHeight != (unsigned)height) {
        double x = h->cupsImagingBBox[0], y = ph - h->cupsImagingBBox[3];
        if (!isfinite(x) || !isfinite(y) || x < 0 || y < 0 || x > pw || y > ph)
            return fail("Invalid raster imageable area.");
        left = (int)lround(x * 600 / 72);
        top = (int)lround(y * 600 / 72);
        if (left + h->cupsWidth > (unsigned)width || top + h->cupsHeight > (unsigned)height)
            return fail("Raster imageable area extends outside paper.");
    }
    int stride = (width + 7) & ~7, depth = color ? 4 : 1;
    size_t count = (size_t)(height + 2) * (size_t)stride * (size_t)depth;
    unsigned char *image = calloc(1, count), *row = malloc(h->cupsBytesPerLine);
    if (!image || !row) { free(image); free(row); return fail("Out of memory."); }
    int result = 0;
    const int margin = (int)ceil(11.62 * 600 / 72);
    for (unsigned y = 0; y < h->cupsHeight; ++y) {
        if (hbpl1_cancelled) { result = fail("Job cancelled."); break; }
        if (cupsRasterReadPixels(raster, row, h->cupsBytesPerLine) != h->cupsBytesPerLine) {
            result = fail("Truncated raster page."); break;
        }
        int dy = top + (int)y;
        if (dy < margin || dy >= height-margin) continue;
        unsigned char *dest = image + ((size_t)(dy+1)*stride + left+1)*depth;
        for (unsigned x = 0; x < h->cupsWidth; ++x, dest += depth) {
            int dx = left + (int)x;
            if (dx < margin || dx >= width-margin) continue;
            if (!color) dest[0] = 255 - row[x];
            else {
                const unsigned char *rgb = row + x*3;
                int k = rgb[0];
                if (k < rgb[1]) k = rgb[1];
                if (k < rgb[2]) k = rgb[2];
                dest[0] = 255-k;
                for (int c = 0; c < 3; ++c)
                    dest[c+1] = k ? (unsigned char)((k-rgb[c])*255/k) : 255;
            }
        }
    }
    free(row);
    if (!result) hbpl1_encode_page(color, width, height, image);
    free(image);
    return result;
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--version")) {
        puts("rastertohbpl1 " HBPL_VERSION ""); return 0;
    }
    if (argc != 6 && argc != 7)
        return fail("CUPS filter usage: job-id user title copies options [raster-file]");
    struct sigaction action = {0};
    action.sa_handler = cancel_job;
    sigemptyset(&action.sa_mask);
    sigaction(SIGTERM, &action, NULL);
    sigaction(SIGINT, &action, NULL);
    signal(SIGPIPE, SIG_IGN);
    char user[128], title[128];
    safe_label(user, argv[2]); safe_label(title, argv[3]);
    hbpl1_begin(user, title);
    int fd = argc == 7 ? open(argv[6], O_RDONLY) : STDIN_FILENO;
    if (fd < 0) return fail("Cannot open raster input.");
    Input input = {.fd = fd};
    cups_raster_t *raster = cupsRasterOpenIO(input_read, &input, CUPS_RASTER_READ);
    if (!raster) { if (fd != STDIN_FILENO) close(fd); return fail("Invalid raster stream."); }
    input.compressed = !memcmp(input.magic, "RaS2", 4) || !memcmp(input.magic, "2SaR", 4);
    if (!input.compressed && memcmp(input.magic,"RaSt",4) && memcmp(input.magic,"tSaR",4) &&
        memcmp(input.magic,"RaS3",4) && memcmp(input.magic,"3SaR",4)) {
        cupsRasterClose(raster); if (fd != STDIN_FILENO) close(fd);
        return fail("Expected a CUPS raster stream.");
    }
    cups_page_header2_t header;
    int result = 0, color = -1, pages = 0;
    while (!hbpl1_cancelled) {
        size_t before = input.delivered;
        input.reading_pixels = 0;
        if (!cupsRasterReadHeader2(raster, &header)) {
            if (input.delivered != before || input.error)
                result = fail("Incomplete or invalid raster header.");
            break;
        }
        input.reading_pixels = 1;
        result = raster_page(raster, &header, &color);
        if (result) break;
        fprintf(stderr, "PAGE: %d 1\n", ++pages);
    }
    const char *error = cupsRasterErrorString();
    if (!result && error && *error) result = fail(error);
    if (!result && !pages) result = fail("Raster contains no pages.");
    if (hbpl1_cancelled) result = fail("Job cancelled.");
    cupsRasterClose(raster);
    if (fd != STDIN_FILENO) close(fd);
    if (!result && hbpl1_end()) result = fail("Cannot finish printer output.");
    return result;
}

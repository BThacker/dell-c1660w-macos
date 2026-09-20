/* SPDX-License-Identifier: GPL-2.0-or-later
 * Generates CUPS raster without going through the production conversion code. */
#include <cups/raster.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "rgb";
    int gray = !strcmp(mode,"gray"), a4 = !strcmp(mode,"a4");
    int cropped = !strcmp(mode,"cropped"), pages = !strcmp(mode,"multi") ? 3 : 1;
    cups_raster_t *r = cupsRasterOpen(STDOUT_FILENO, CUPS_RASTER_WRITE_COMPRESSED);
    cups_page_header2_t h = {0};
    h.HWResolution[0] = h.HWResolution[1] = 600;
    h.PageSize[0] = a4 ? 595 : 612; h.PageSize[1] = a4 ? 842 : 792;
    h.cupsPageSize[0] = h.PageSize[0]; h.cupsPageSize[1] = h.PageSize[1];
    h.cupsWidth = a4 ? 4958 : 5100; h.cupsHeight = a4 ? 7017 : 6600;
    h.cupsBitsPerColor = 8; h.cupsNumColors = gray ? 1 : 3;
    h.cupsBitsPerPixel = h.cupsNumColors * 8;
    h.cupsColorSpace = gray ? CUPS_CSPACE_W : CUPS_CSPACE_RGB;
    h.cupsColorOrder = CUPS_ORDER_CHUNKED; h.NumCopies = 1;
    if (cropped) {
        h.cupsWidth -= 194; h.cupsHeight -= 194;
        h.cupsImagingBBox[0] = h.cupsImagingBBox[1] = 11.64f;
        h.cupsImagingBBox[2] = 600.36f; h.cupsImagingBBox[3] = 780.36f;
    }
    if (!strcmp(mode,"resolution")) h.HWResolution[0] = 300;
    if (!strcmp(mode,"colorspace")) h.cupsColorSpace = CUPS_CSPACE_CMY;
    if (!strcmp(mode,"copies")) h.NumCopies = 2;
    if (!strcmp(mode,"duplex")) h.Duplex = 1;
    if (!strcmp(mode,"dimensions")) h.cupsWidth = 6000;
    if (!strcmp(mode,"paper")) h.cupsPageSize[0] = 1000000;
    h.cupsBytesPerLine = h.cupsWidth*h.cupsNumColors + (!strcmp(mode,"padding") ? 18 : 0);
    unsigned char *line = malloc(h.cupsBytesPerLine);
    if (!r || !line) return 1;
    for (int page = 0; page < pages; ++page) {
        if (!cupsRasterWriteHeader2(r, &h)) return 1;
        unsigned rows = !strcmp(mode,"truncated") ? 120 : h.cupsHeight;
        for (unsigned y = 0; y < rows; ++y) {
            memset(line,255,h.cupsBytesPerLine);
            unsigned gy = y + (cropped ? 97 : 0);
            for (unsigned x = 0; x < h.cupsWidth; ++x) {
                unsigned gx = x + (cropped ? 97 : 0);
                if (gy < 200 || gy >= 456 || gx < 200 || gx >= 456 || !strcmp(mode,"blank")) continue;
                unsigned char *p = line+x*h.cupsNumColors;
                if (gray) p[0] = (gx-200);
                else if (!strcmp(mode,"noise")) {
                    unsigned n = gx*1664525u + gy*1013904223u;
                    p[0] = n; p[1] = n>>9; p[2] = n>>19;
                } else {
                    p[0] = page == 0 ? 255 : 0;
                    p[1] = page == 1 ? 255 : 0;
                    p[2] = page == 2 ? 255 : 0;
                }
            }
            if (cupsRasterWritePixels(r,line,h.cupsBytesPerLine) != h.cupsBytesPerLine) return 1;
        }
    }
    free(line); cupsRasterClose(r);
    return 0;
}

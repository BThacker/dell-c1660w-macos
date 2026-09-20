/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef HBPL1_H
#define HBPL1_H
#include <signal.h>
extern volatile sig_atomic_t hbpl1_cancelled;
void hbpl1_begin(const char *user, const char *title);
/* Input: KCMY or K; padded to 8 pixels, one leading row and pixel,
 * and one trailing row. Dimensions have already been validated. */
void hbpl1_encode_page(int color, int width, int height, unsigned char *image);
int hbpl1_end(void);
#endif

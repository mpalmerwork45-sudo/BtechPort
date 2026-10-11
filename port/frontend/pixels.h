#ifndef BTP_PIXELS_H
#define BTP_PIXELS_H
#include "core/game.h"
enum { BTP_SCREEN_W = 320, BTP_SCREEN_H = 200 };
extern const uint32_t btp_palette[16]; /* opaque ARGB */
void btp_render(const BtpResources *resources, const BtpState *state, int debug,
                uint32_t frame[BTP_PIXELS]);
int btp_write_ppm(const char *path, const uint32_t frame[BTP_PIXELS]);
#endif

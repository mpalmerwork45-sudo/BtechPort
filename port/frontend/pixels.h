#ifndef BTP_PIXELS_H
#define BTP_PIXELS_H
#include "core/game.h"
enum { BTP_SCREEN_W = 320, BTP_SCREEN_H = 200 };
extern const uint32_t btp_palette[16]; /* opaque ARGB */
int btp_draw_sprite(const BtpGraphic *atlas, unsigned id, int x, int y,
                    unsigned hidden_rows, int clip_left, uint32_t frame[BTP_PIXELS]);
void btp_sprite_preview(const BtpResources *resources, unsigned tick, uint32_t frame[BTP_PIXELS]);
void btp_world_preview(const BtpResources *resources,const BtpState *state,uint32_t frame[BTP_PIXELS]);
void btp_render(const BtpResources *resources, const BtpState *state, int debug,
                uint32_t frame[BTP_PIXELS]);
int btp_write_ppm(const char *path, const uint32_t frame[BTP_PIXELS]);
#endif

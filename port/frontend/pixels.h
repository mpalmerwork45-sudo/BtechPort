#ifndef BTP_PIXELS_H
#define BTP_PIXELS_H
#include "core/game.h"
enum { BTP_SCREEN_W = 320, BTP_SCREEN_H = 200 };
extern const uint32_t btp_palette[16]; /* opaque ARGB */
/* Application setup precedes the original logo and never advances the game. */
void btp_startup_screen(const BtpResources *resources,unsigned selected,
    const char *error,uint32_t frame[BTP_PIXELS]);
int btp_draw_sprite(const BtpGraphic *atlas, unsigned id, int x, int y,
                    unsigned hidden_rows, int clip_left, uint32_t frame[BTP_PIXELS]);
void btp_sprite_preview(const BtpResources *resources, unsigned tick, uint32_t frame[BTP_PIXELS]);
void btp_world_preview(const BtpResources *resources,const BtpState *state,uint32_t frame[BTP_PIXELS]);
void btp_mech_screen(const BtpResources *resources,const uint8_t record[125],
    const char *pilot,const char *rider,unsigned heat,unsigned tick,uint32_t frame[BTP_PIXELS]);
/* Original salvage text stream, also compared with the executable oracle. */
size_t btp_salvage_text(const BtpResources *resources,const BtpState *state,uint8_t message[1024]);
size_t btp_battle_text(const BtpResources *resources,const BtpBattleText *report,unsigned verbosity,uint8_t message[1024]);
void btp_render(const BtpResources *resources, const BtpState *state, int debug,
                uint32_t frame[BTP_PIXELS]);
int btp_write_ppm(const char *path, const uint32_t frame[BTP_PIXELS]);
#endif

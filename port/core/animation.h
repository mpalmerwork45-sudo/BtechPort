#ifndef BTP_ANIMATION_H
#define BTP_ANIMATION_H
#include <stdint.h>
#include "core/game.h"
/* Human walking index 0..15 corresponds to original frame 16..31.
   Primary 1732/231D/276A and the eight direction programs at image 28130. */
uint8_t btp_walk_next(uint8_t frame, unsigned previous_direction, unsigned direction);
uint8_t btp_walk_first(unsigned direction);
unsigned btp_player_direction(unsigned facing);
/* Original 0000:240B / DS:04B0, ten tile IDs and three consecutive pages. */
unsigned btp_terrain_frame(unsigned tile, unsigned phase); /* 0: static tile */
int btp_cutscene_begin(BtpState *s, const BtpResources *r, unsigned kind, unsigned active);
int btp_cutscene_tick(BtpState *s, const BtpResources *r); /* 1 when complete */
int btp_cutscene_valid(const BtpState *s);
#endif

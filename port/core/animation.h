#ifndef BTP_ANIMATION_H
#define BTP_ANIMATION_H
#include <stdint.h>
/* Human walking index 0..15 corresponds to original frame 16..31.
   Primary 1732/231D/276A and the eight direction programs at image 28130. */
uint8_t btp_walk_next(uint8_t frame, unsigned previous_direction, unsigned direction);
uint8_t btp_walk_first(unsigned direction);
unsigned btp_player_direction(unsigned facing);
#endif

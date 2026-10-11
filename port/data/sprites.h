#ifndef BTP_SPRITES_H
#define BTP_SPRITES_H
#include "data/resources.h"
enum { BTP_SPRITE_COUNT = 376 };
typedef struct { unsigned x, y, width, height; } BtpSpriteRect;
/* Original MECHSHAP extraction rectangles (primary image 567B..5AA1). */
int btp_sprite_rect(unsigned id, BtpSpriteRect *rect);
#endif

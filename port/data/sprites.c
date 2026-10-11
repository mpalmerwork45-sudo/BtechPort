#include "data/sprites.h"

int btp_sprite_rect(unsigned id, BtpSpriteRect *r)
{
    if (!r || id >= BTP_SPRITE_COUNT) return 0;
    *r = (BtpSpriteRect){0,0,8,8};
    if (id < 16 || (id >= 146 && id < 162)) {
        unsigned n = id < 16 ? id : id-146;
        *r = (BtpSpriteRect){(n%12)*24,(id < 16 ? 0u : 48u)+(n/12)*24,24,24};
    } else if (id < 36) { r->x = (id-4)*8; r->y = 24; }
    else if (id < 120) { r->x = 96+(id-36)%12*8; r->y = 72+(id-36)/12*8; }
    else if (id < 124 || (id >= 162 && id < 166)) {
        unsigned n = id < 124 ? id-120 : id-162;
        static const unsigned x[] = {0,24,72,48,48,72,0,24};
        *r = (BtpSpriteRect){x[n+(id < 124 ? 0u : 4u)],96+(n/2)*24,24,24};
    } else if (id < 126) *r = (BtpSpriteRect){64+(id-124)*16,160,16,14};
    else if (id < 128) { r->x = (id-126)*8; r->y = 160; }
    else if (id < 130) *r = (BtpSpriteRect){64+(id-128)*16,144,16,16};
    else if (id < 146) { r->x = 32+(id-130)%4*8; r->y = 144+(id-130)/4*8; }
    else if (id < 186) { r->x = (id-154)*8; r->y = 32; }
    else if (id < 270) { r->x = 192+(id-186)%12*8; r->y = 72+(id-186)/12*8; }
    else if (id < 290) { r->x = (id-258)*8; r->y = 40; }
    else if (id < 374) { r->x = 96+(id-290)%12*8; r->y = 128+(id-290)/12*8; }
    else *r = (BtpSpriteRect){(id-374)*16,144,16,11};
    return 1;
}

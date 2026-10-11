#include "core/animation.h"
#include "core/game.h"

uint8_t btp_walk_first(unsigned direction)
{
    static const uint8_t first[8] = {8,4,4,4,0,12,12,12};
    return first[direction & 7u];
}
uint8_t btp_walk_next(uint8_t frame, unsigned before, unsigned direction)
{
    unsigned first = btp_walk_first(direction);
    return (uint8_t)(first + (before == direction && (frame & ~3u) == first ? (frame+1u)%4 : 0));
}
unsigned btp_player_direction(unsigned facing)
{
    return facing == BTP_UP ? 0u : facing == BTP_RIGHT ? 2u : facing == BTP_LEFT ? 6u : 4u;
}

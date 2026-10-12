#include "core/world.h"
#include "core/training.h"

unsigned btp_world_tile(const BtpResources *r,const BtpState *s,int x,int y)
{
    if (x>=BTP_CITADEL_ORIGIN && y>=BTP_CITADEL_ORIGIN &&
        x<BTP_CITADEL_ORIGIN+r->map.width && y<BTP_CITADEL_ORIGIN+r->map.height)
        return btp_mission_tile(s,&r->map,x-BTP_CITADEL_ORIGIN,y-BTP_CITADEL_ORIGIN);
    if (!r->world.loaded || x<BTP_WORLD_ORIGIN || y<BTP_WORLD_ORIGIN ||
        x>=BTP_WORLD_ORIGIN+BTP_WORLD_SIDE || y>=BTP_WORLD_ORIGIN+BTP_WORLD_SIDE) return 255;
    return r->world.tiles[(unsigned)(y-BTP_WORLD_ORIGIN)*BTP_WORLD_SIDE+(unsigned)(x-BTP_WORLD_ORIGIN)];
}

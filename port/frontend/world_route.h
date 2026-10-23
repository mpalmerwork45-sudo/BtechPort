#ifndef BTP_AUTHORED_WORLD_ROUTE_H
#define BTP_AUTHORED_WORLD_ROUTE_H
#include "core/events.h"

/* Authoring automation, not a gameplay pathfinder. Coordinates in a world
   request are half-tile movement units, like the ordinary party cursor. */
enum { BTP_ROUTE_DEFAULT=262144, BTP_ROUTE_MAX=1048576 };
typedef struct {
    const char *entrance,*map,*world;
    unsigned x,y,budget;
} BtpRouteTarget;
typedef struct {
    const char *code,*message;
    unsigned examined,inputs,world,map,x,y;
} BtpRouteReport;
int btp_authored_walk(BtpState *s,const BtpResources *r,const BtpRouteTarget *target,
                     void (*input)(BtpState *,const BtpResources *,BtpAction),BtpRouteReport *report);
int btp_authored_formation(const BtpState *s,const BtpResources *r);
#endif

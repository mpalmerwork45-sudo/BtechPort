#ifndef BTP_WORLD_H
#define BTP_WORLD_H
#include "core/game.h"
/* Original generated sectors with the authentic local MAP1 overlay.
   Current early-campaign barriers still prevent outer travel. */
unsigned btp_world_tile(const BtpResources *resources,const BtpState *state,int x,int y);
int btp_world_location(const BtpResources *resources,const BtpState *state,int x,int y);
int btp_world_populated(const BtpResources *resources,const BtpState *state);
void btp_world_move(BtpState *state,const BtpResources *resources,BtpAction action);
void btp_world_step(BtpState *state,const BtpResources *resources,BtpAction action);
void btp_world_clock(BtpState *state,const BtpResources *resources);
void btp_world_actions(BtpState *state,const BtpResources *resources,BtpAction action);
#endif

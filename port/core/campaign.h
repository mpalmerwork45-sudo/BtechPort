#ifndef BTP_CAMPAIGN_H
#define BTP_CAMPAIGN_H
#include "core/game.h"
void btp_campaign_rex(BtpState *state,const BtpResources *resources);
int btp_campaign_random(BtpState *state,const BtpResources *resources);
unsigned btp_campaign_candidates(BtpState *state,const BtpResources *resources,BtpCombatUnit units[12],uint8_t ids[12],int *x,int *y);
void btp_campaign_result(BtpState *state,const BtpResources *resources);
#endif

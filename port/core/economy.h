#ifndef BTP_ECONOMY_H
#define BTP_ECONOMY_H
#include "core/game.h"
int btp_economy_below_cap(const BtpState *state);
void btp_economy_wrap(BtpState *state);
void btp_economy_market(BtpState *state);
void btp_economy_market_resources(BtpState *state,const BtpResources *resources);
void btp_economy_wrap_resources(BtpState *state,const BtpResources *resources);
#endif

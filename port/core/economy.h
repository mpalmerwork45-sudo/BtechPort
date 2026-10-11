#ifndef BTP_ECONOMY_H
#define BTP_ECONOMY_H
#include "core/game.h"
int btp_economy_below_cap(const BtpState *state);
void btp_economy_wrap(BtpState *state);
#endif

#ifndef BTP_SPY_H
#define BTP_SPY_H
#include "core/game.h"
int btp_spy_unit(const BtpState *state,unsigned unit);
unsigned btp_spy_outcome(const BtpState *state);
void btp_spy_resolve(BtpState *state);
int btp_spy_begin(BtpState *state);
void btp_spy_combat_finish(BtpState *state);
#endif

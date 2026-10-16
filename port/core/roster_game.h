#ifndef BTP_ROSTER_GAME_H
#define BTP_ROSTER_GAME_H
#include "core/game.h"
enum { BTP_BROKER_BOUGHT=1,BTP_BROKER_NO_FUNDS,BTP_BROKER_FULL,BTP_BROKER_UNAVAILABLE };
int btp_broker_available(const BtpState *state,const BtpResources *resources);
unsigned btp_broker_buy(BtpState *state,const BtpResources *resources,unsigned definition);
const uint8_t *btp_roster_enemy(BtpState *state,const BtpResources *resources);
int btp_roster_state_valid(const BtpState *state,const BtpResources *resources);
#endif

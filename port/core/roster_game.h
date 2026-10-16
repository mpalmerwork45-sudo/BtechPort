#ifndef BTP_ROSTER_GAME_H
#define BTP_ROSTER_GAME_H
#include "core/game.h"
enum { BTP_BROKER_BOUGHT=1,BTP_BROKER_NO_FUNDS,BTP_BROKER_FULL,BTP_BROKER_UNAVAILABLE,
    BTP_BROKER_SOLD,BTP_BROKER_CREDIT_LIMIT };
enum { BTP_BROKER_BUILDING=26,BTP_BROKER_ENTRY=12,BTP_BROKER_X=54,BTP_BROKER_Y=50 };
int btp_broker_door(const BtpState *state,const BtpResources *resources,int x,int y);
void btp_broker_open(BtpState *state);
int btp_broker_page(unsigned page);
unsigned btp_broker_owned(const BtpState *state,unsigned bay);
unsigned btp_broker_count(const BtpState *state);
unsigned btp_broker_slot(const BtpState *state,unsigned ordinal);
uint32_t btp_broker_offer(const BtpState *state,const BtpResources *resources,unsigned bay);
unsigned btp_broker_sell(BtpState *state,const BtpResources *resources,unsigned bay);
int btp_broker_available(const BtpState *state,const BtpResources *resources);
unsigned btp_broker_buy(BtpState *state,const BtpResources *resources,unsigned definition);
const uint8_t *btp_roster_enemy(BtpState *state,const BtpResources *resources);
int btp_roster_state_valid(const BtpState *state,const BtpResources *resources);
#endif

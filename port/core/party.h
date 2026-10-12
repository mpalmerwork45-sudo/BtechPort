#ifndef BTP_PARTY_H
#define BTP_PARTY_H
#include "core/game.h"
enum { BTP_PARTY_BYTES=1024 };
void btp_party_init(BtpState *state);
void btp_party_sync(BtpState *state);
unsigned btp_party_count(const BtpPartyState *party);
uint8_t *btp_party_mech(BtpState *state,unsigned slot);
const char *btp_party_name(const BtpPartyState *party,unsigned slot);
int btp_party_recruit(BtpState *state,unsigned skill);
void btp_party_follow(BtpState *state,uint16_t old_x,uint16_t old_y);
void btp_party_encode(const BtpPartyState *party,uint8_t bytes[BTP_PARTY_BYTES]);
int btp_party_decode(const uint8_t bytes[BTP_PARTY_BYTES],BtpPartyState *party);
#endif

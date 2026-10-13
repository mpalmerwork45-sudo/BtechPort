#ifndef BTP_PARTY_H
#define BTP_PARTY_H
#include "core/game.h"
enum { BTP_PARTY_BYTES=1024 };
void btp_party_init(BtpState *state);
void btp_party_sync(BtpState *state);
void btp_party_allocate(BtpState *state,unsigned member,unsigned mech,unsigned seat);
void btp_party_transfer(BtpState *state,unsigned giver,unsigned recipient,unsigned item);
unsigned btp_party_heal(BtpState *state,const BtpResources *resources,unsigned hospital_skill);
void btp_heal_character(uint8_t person[17],unsigned program,uint8_t rng[3]);
unsigned btp_party_field_salvage(BtpState *state,const uint8_t wrecks[4][125],const uint8_t marked[4]);
unsigned btp_party_count(const BtpPartyState *party);
unsigned btp_party_slot(const BtpPartyState *party,unsigned ordinal);
unsigned btp_party_ordinal(const BtpPartyState *party,unsigned slot);
uint8_t *btp_party_mech(BtpState *state,unsigned slot);
const char *btp_party_name(const BtpPartyState *party,unsigned slot);
const char *btp_character_name(unsigned id);
/* Return the recruited slot plus one, or zero when the party is full.
   Original name IDs wrap and may duplicate; callers must retain the slot. */
int btp_party_recruit(BtpState *state,unsigned skill);
int btp_party_walkable(const BtpState *state,const BtpResources *resources,int x,int y,int mech);
void btp_party_follow(BtpState *state,const BtpResources *resources,uint16_t old_x,uint16_t old_y);
void btp_party_encode(const BtpPartyState *party,uint8_t bytes[BTP_PARTY_BYTES]);
int btp_party_decode(const uint8_t bytes[BTP_PARTY_BYTES],BtpPartyState *party);
#endif

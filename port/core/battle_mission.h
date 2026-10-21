#ifndef BTP_BATTLE_MISSION_H
#define BTP_BATTLE_MISSION_H
#include "core/events.h"
/* 5600..6111 is reserved in the original 6144-byte combat encoding. Only
   state version 51 uses it; the ordinary combat codec still sees zeros. */
enum { BTP_BATTLE_MISSION_OFFSET=4096+5600, BTP_BATTLE_MISSION_BYTES=512 };
int btp_battle_mission_begin(BtpState *s,const BtpResources *r,unsigned battle);
void btp_battle_signal(BtpState *s,const BtpAdventure *a,unsigned when,unsigned group);
void btp_battle_observe(BtpState *s,const BtpAdventure *a);
unsigned btp_battle_hook(BtpState *s,const BtpAdventure *a);
int btp_battle_reinforce(BtpState *s,const BtpResources *r,unsigned group,unsigned radius);
unsigned btp_battle_group_value(const BtpState *s,const BtpAdventure *a,unsigned group,unsigned kind);
unsigned btp_battle_side(const BtpState *s,const BtpAdventure *a,unsigned index);
int btp_battle_hostile(const BtpState *s,unsigned actor,unsigned target);
unsigned btp_battle_hostiles(const BtpState *s);
int btp_battle_actor_plan(BtpState *s,const BtpResources *r,const BtpMap *map,unsigned index);
int btp_battle_mission_valid(const BtpState *s,const BtpAdventure *a);
void btp_battle_mission_encode(const BtpState *s,uint8_t b[BTP_BATTLE_MISSION_BYTES]);
int btp_battle_mission_decode(BtpState *s,const uint8_t b[BTP_BATTLE_MISSION_BYTES]);
#endif

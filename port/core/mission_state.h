#ifndef BTP_MISSION_STATE_H
#define BTP_MISSION_STATE_H
#include "core/events.h"
enum { BTP_MISSION_BYTES=192 };
/* v52 uses a separately versioned authored block in the reserved v18+
   payload area. Released v25..v51 saves keep all 1536 bytes there zero. */
enum { BTP_CAPACITY_OFFSET=512, BTP_CAPACITY_BYTES=1024 };
unsigned btp_objective_state(const BtpState *s,const BtpAdventure *a,unsigned index);
const char *btp_objective_name(unsigned state);
int btp_mission_region(const BtpState *s,const BtpAdventure *a,unsigned index);
int btp_mission_check(const BtpState *s,const BtpAdventure *a,const BtpEventNode *e);
int btp_mission_variable(BtpState *s,const BtpAdventure *a,const BtpEventNode *e);
int btp_mission_objective(BtpState *s,const BtpAdventure *a,const BtpEventNode *e);
void btp_mission_initialize(BtpState *s,const BtpAdventure *a);
/* Reconcile exploration crossings, then take one deterministic continuation.
   Returns BTP_EVENT_NODES if no trigger is pending. */
unsigned btp_mission_trigger(BtpState *s,const BtpAdventure *a);
void btp_mission_preview(BtpState *s,const BtpAdventure *a);
int btp_mission_valid(const BtpState *s,const BtpAdventure *a);
void btp_mission_encode(const BtpState *s,uint8_t b[BTP_MISSION_BYTES]);
int btp_mission_decode(BtpState *s,const uint8_t b[BTP_MISSION_BYTES]);
void btp_capacity_encode(const BtpState *s,uint8_t b[BTP_CAPACITY_BYTES]);
int btp_capacity_decode(BtpState *s,const uint8_t b[BTP_CAPACITY_BYTES]);
#endif

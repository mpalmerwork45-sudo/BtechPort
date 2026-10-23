#ifndef BTP_YARD_H
#define BTP_YARD_H
#include "core/game.h"
enum { BTP_YARD_WALK, BTP_YARD_CLIMB, BTP_YARD_SWITCH, BTP_YARD_FAIL,
    BTP_YARD_FOUND, BTP_YARD_BOOT, BTP_YARD_LOAN, BTP_YARD_OWN, BTP_YARD_FIGHT };
int btp_yard_native(BtpState *state,const BtpResources *resources);
void btp_yard_input(BtpState *state,const BtpResources *resources,BtpAction action);
void btp_yard_result(BtpState *state,const BtpResources *resources);
int btp_yard_valid(const BtpState *state);
int btp_yard_valid_resources(const BtpState *state,const BtpResources *resources);
unsigned btp_yard_tile(const BtpState *state,unsigned tile,int x,int y);
void btp_yard_alarm(BtpState *state,const BtpResources *resources,unsigned target);
void btp_yard_begin_guards(BtpState *state,const BtpResources *resources);
void btp_yard_begin_arena(BtpState *state,const BtpResources *resources);
void btp_yard_finish_prison(BtpState *state,const BtpResources *resources,int success);
#endif

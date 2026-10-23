#ifndef BTP_SCHOOL_H
#define BTP_SCHOOL_H
#include "core/game.h"
enum { BTP_SCHOOL_STR_INTRO=43, BTP_SCHOOL_STR_MASTERED=44,
    BTP_SCHOOL_STR_NO_FUNDS=45, BTP_SCHOOL_STR_RANK=46,
    BTP_SCHOOL_STR_SUBJECT=51, BTP_SCHOOL_STR_COME_BACK=54 };
unsigned btp_school_price(unsigned rank);
void btp_school_native(BtpState *state, const BtpResources *resources);
int btp_school_valid(const BtpState *state);
int btp_school_valid_bld(const BtpState *state,const BtpBld *script);
int btp_school_text(const BtpState *state, const BtpResources *resources,
    uint8_t *out, size_t capacity, size_t *length);
#endif

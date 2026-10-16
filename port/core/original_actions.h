#ifndef BTP_ORIGINAL_ACTIONS_H
#define BTP_ORIGINAL_ACTIONS_H
#include "core/game.h"

/* Original F5 operands, not a new script ABI. Building and story context
   remain part of dispatch; the same number alone is not a general command. */
enum {
    BTP_NATIVE_MISSION=1, BTP_NATIVE_RESULT_NAME=2, BTP_NATIVE_TRAINING_RETURN=3,
    BTP_NATIVE_CLASS_PRICES=4, BTP_NATIVE_CLASS_TAKE=5,
    BTP_NATIVE_ACCOUNTS=6, BTP_NATIVE_BUY_SHARES=7, BTP_NATIVE_SELL_SHARES=8,
    BTP_NATIVE_TALK=12, BTP_NATIVE_SERVICE_SELECT=13, BTP_NATIVE_PARTY_COUNT=14,
    BTP_NATIVE_REPAIR=18, BTP_NATIVE_REFIT=19, BTP_NATIVE_TECH_PAYMENT=20,
    BTP_NATIVE_REX=30, BTP_NATIVE_CADET_RETURN=43, BTP_NATIVE_AMMO=44,
    BTP_NATIVE_PHOENIX=45
};
void btp_original_checkpoint(BtpState *state);
void btp_original_native_input(BtpState *state, const BtpResources *resources, BtpAction action);
void btp_original_services(BtpState *state, const BtpResources *resources);
#endif

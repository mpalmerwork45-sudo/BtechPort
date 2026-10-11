#ifndef BTP_BANK_H
#define BTP_BANK_H
#include "core/game.h"
/* Native strings appended to the audited EXE cache; no asset text in source. */
enum { BTP_BANK_STR_NONE = 17, BTP_BANK_STR_NO_STOCK, BTP_BANK_STR_SELL_MENU,
    BTP_BANK_STR_SELL_AMOUNT, BTP_BANK_STR_STOCK_ACCOUNT, BTP_BANK_STR_SELL_CLAMP,
    BTP_BANK_STR_SOLD, BTP_BANK_STR_OF, BTP_BANK_STR_SELL_BALANCE, BTP_BANK_STR_SELL_PERIOD,
    BTP_BANK_STR_SELL_ZERO, BTP_BANK_STR_NOT_OWNED, BTP_BANK_STR_NO_CASH,
    BTP_BANK_STR_BUY_MENU, BTP_BANK_STR_BUY_AMOUNT, BTP_BANK_STR_CASH_ACCOUNT,
    BTP_BANK_STR_BUY_CLAMP, BTP_BANK_STR_BOUGHT, BTP_BANK_STR_IN,
    BTP_BANK_STR_BUY_BALANCE, BTP_BANK_STR_BUY_PERIOD, BTP_BANK_STR_BUY_ZERO,
    BTP_BANK_STR_NOTHING, BTP_BANK_STR_COMPANY };
void btp_bank_native(BtpState *state, const BtpResources *resources);
void btp_bank_input(BtpState *state, const BtpResources *resources, BtpAction action);
int btp_bank_valid(const BtpState *state);
int btp_bank_text(const BtpState *state, const BtpResources *resources,
    uint8_t *output, size_t capacity, size_t *length);
#endif

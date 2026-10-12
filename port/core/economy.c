#include "core/economy.h"
#include "core/npc.h"

int btp_economy_below_cap(const BtpState *s)
{
    uint32_t assets = s->credits;
    for (unsigned i = 0; i < 3; ++i) assets += s->investments[i];
    /* Image 2FE..341 adds with 32-bit carry, then compares the high WORD
       signed and the low WORD unsigned. The bounded cadet cap is 50. */
    return (assets & UINT32_C(0x80000000)) != 0 || assets < s->allowance_cap;
}
void btp_economy_market(BtpState *s)
{
    /* Original 381..447 mutates D374[3] in place. Tables 2A2/2A8 and
       unsigned math helpers establish masks, rates, truncation and wrap. */
    static const uint8_t masks[3] = {255,7,1}, rates[3] = {96,90,48};
    for (unsigned i = 0; i < 3; ++i) {
        int growth = (btp_rng_next(s->npc.rng) & masks[i]) != 0;
        uint32_t product = s->investments[i] * (growth ? 100u : rates[i]);
        s->investments[i] = product / (growth ? rates[i] : 110u);
        if (growth && i == 2 && s->investments[i] > 18000) s->investments[i] >>= 2;
    }
}
void btp_economy_wrap(BtpState *s)
{
    if (!btp_economy_below_cap(s)) return;
    s->credits+=15;btp_economy_market(s);
}

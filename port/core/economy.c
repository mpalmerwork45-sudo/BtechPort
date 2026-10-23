#include "core/economy.h"
#include "core/npc.h"
#include "data/chi_services.h"

int btp_economy_below_cap(const BtpState *s)
{
    uint32_t assets = s->credits;
    for (unsigned i = 0; i < 3; ++i) assets += s->investments[i];
    /* Image 2FE..341 adds with 32-bit carry, then compares the high WORD
       signed and the low WORD unsigned. The bounded cadet cap is 50. */
    return (assets & UINT32_C(0x80000000)) != 0 || assets < s->allowance_cap;
}
void btp_economy_market_resources(BtpState *s,const BtpResources *r)
{
    /* Original 381..447 mutates D374[3] in place. Tables 2A2/2A8 and
       unsigned math helpers establish masks, rates, truncation and wrap. */
    for (unsigned i = 0; i < 3; ++i) {
        unsigned rate=btp_chi_service(r,BTP_SVC_MARKET_RATE_0+2u*i);
        int growth = (btp_rng_next(s->npc.rng) & btp_chi_service(r,BTP_SVC_MARKET_MASK_0+2u*i)) != 0;
        uint32_t product = s->investments[i] * (growth ? 100u : rate);
        s->investments[i] = product / (growth ? rate : btp_chi_service(r,BTP_SVC_MARKET_LOSS_DIVISOR));
        if (growth && i == 2 && s->investments[i] > btp_chi_service(r,BTP_SVC_MARKET_SPLIT_THRESHOLD)) s->investments[i] >>= btp_chi_service(r,BTP_SVC_MARKET_SPLIT_SHIFT);
    }
}
void btp_economy_market(BtpState *s) { btp_economy_market_resources(s,NULL); }
void btp_economy_wrap_resources(BtpState *s,const BtpResources *r)
{
    if (!btp_economy_below_cap(s)) return;
    s->credits+=btp_chi_service(r,BTP_SVC_CADET_ALLOWANCE);btp_economy_market_resources(s,r);
}
void btp_economy_wrap(BtpState *s) { btp_economy_wrap_resources(s,NULL); }

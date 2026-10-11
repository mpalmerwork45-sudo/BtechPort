#include "core/shop.h"
#include "core/economy.h"

static void unsupported(BtpState *s)
{
    s->script.status = BTP_SCRIPT_ERROR; s->script.error = BTP_SCRIPT_NATIVE_CONTEXT;
    s->script.fault_pc = s->script.pc >= 2 ? (uint16_t)(s->script.pc-2) : 0;
}
void btp_shop_native(BtpState *s, const BtpResources *r)
{
    const BtpBld *b = btp_building_bld(r,s->entry_slot);
    if (!b || s->recruitment || s->story_flags[4] || (s->entry_slot != 3 && s->entry_slot != 4)) {
        unsupported(s); return;
    }
    switch (s->script.native_action) {
    case 10:
        if (s->script.has_cash || !s->script.text_count) { unsupported(s); return; }
        s->script.has_cash = 1; s->script.cash_after = s->script.text_count;
        s->script.cash_value = s->credits;
        break;
    case 9: case 11: {
        /* Audited unsigned price tables at DS:4F26 / 4F44; equipment
           assignments at 0FDC:13DE / 15E6. One active party member. */
        static const uint32_t armor_prices[6] = {0,50,150,200,10000,1000};
        static const uint32_t weapon_prices[11] = {2,10,100,10,20,35,40,80,250,1500,1500};
        static const uint8_t protection[6] = {0,25,40,30,50,50};
        int armor = s->script.native_action == 9;
        unsigned choice = armor ? s->script.choices[s->story_flags[10] ? 13 : 14] : s->script.choices[16];
        if (!armor && s->story_flags[12] == 6) choice = s->script.choices[17]+6u;
        if (!armor && s->story_flags[12] == 9) choice = s->script.choices[18]+9u;
        if (s->entry_slot != (armor ? 4 : 3) || !choice ||
            choice > (armor ? 5u : 11u) ||
            (!armor && s->story_flags[12] != 0 && s->story_flags[12] != 6 && s->story_flags[12] != 9)) {
            unsupported(s); return;
        }
        uint32_t price = armor ? armor_prices[choice] : weapon_prices[choice-1];
        s->story_flags[11] = 0;
        if (s->credits >= price) {
            s->credits -= price; s->story_flags[11] = 1;
            if (armor) { s->armor = (uint8_t)choice; s->armor_points = protection[choice]; }
            else s->weapon = (uint8_t)choice;
            if (s->npc.enabled) s->npc.allowance_pending = (uint8_t)btp_economy_below_cap(s);
        }
        break;
    }
    default: unsupported(s); return;
    }
    btp_script_native_return(&s->script,b,s->story_flags);
}

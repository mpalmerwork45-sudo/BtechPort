#include "core/shop.h"
#include "core/economy.h"
#include "core/party.h"

static void unsupported(BtpState *s)
{
    s->script.status = BTP_SCRIPT_ERROR; s->script.error = BTP_SCRIPT_NATIVE_CONTEXT;
    s->script.fault_pc = s->script.pc >= 2 ? (uint16_t)(s->script.pc-2) : 0;
}
void btp_shop_native(BtpState *s, const BtpResources *r)
{
    const BtpBld *b = btp_state_bld(r,s);
    unsigned kind=btp_building_kind(r,s);
    if (!b || (s->recruitment && kind!=5 && kind!=9) || (kind != 3 && kind != 4 && kind != 5 && kind!=8 && kind!=12 && kind!=9)) {
        unsupported(s); return;
    }
    switch (s->script.native_action) {
    case 28: case 46:
        if (kind!=8) { unsupported(s);return; }
        if (s->party.enabled) for (unsigned i=0;i<4;++i) {
            uint8_t *mech=btp_party_mech(s,i);
            if (s->script.native_action==28) { if (mech[0]!=255 && (i || s->campaign.owned)) s->party.mech_types[i]=mech[0];mech[0]=255; }
            else if (s->party.mech_types[i]!=255) {
                mech[0]=s->party.mech_types[i];
                for (unsigned crew=121;crew<=122;++crew) if (mech[crew]<8 && s->party.people[mech[crew]][0]!=255)
                    s->party.people[mech[crew]][12]=(uint8_t)i;
            }
        }
        if (s->script.native_action==28 && s->party.enabled) for (unsigned i=0;i<8;++i) s->party.people[i][12]=8;
        s->campaign.mounted=(uint8_t)(s->script.native_action==46 && s->campaign.owned && s->campaign.mech[121]==0);break;
    case 14: /* 14D3:0AF2: other party members; Jason is slot zero. */
        if (kind!=5) { unsupported(s);return; }
        s->story_flags[14]=0;break;
    case 16:
        if (kind!=5) { unsupported(s);return; }
        s->story_flags[15]=s->party.enabled ? s->party.people[s->party.selected][16]&1u : s->apprentice;break;
    case 15:
        if (kind!=5 || (s->party.enabled ? s->party.people[s->party.selected][16]&1u : s->apprentice)) { unsupported(s);return; }
        s->story_flags[14]=0;
        if (s->credits>=500) {
            s->credits-=500;s->story_flags[14]=1;
            if (s->party.enabled && s->party.selected) { ++s->party.people[s->party.selected][9];s->party.people[s->party.selected][16]|=1; }
            else { ++s->technician;s->apprentice=1; }
            if (s->npc.enabled) s->npc.allowance_pending=(uint8_t)btp_economy_below_cap(s);
        }
        break;
    case 17: case 29:
        /* Training loans do not create owned or stored mechs. */
        if (kind!=5 && kind!=8) { unsupported(s);return; }
        s->story_flags[16]=s->campaign.owned;break;
    case 20: case 44:
        /* Original 09B8:0925 / 1762 restore the building presentation. */
        if (kind!=5) { unsupported(s);return; }
        break;
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
        if (kind != (armor ? 4 : 3) || !choice ||
            choice > (armor ? 5u : 11u) ||
            (!armor && s->story_flags[12] != 0 && s->story_flags[12] != 6 && s->story_flags[12] != 9)) {
            unsupported(s); return;
        }
        uint32_t price = armor ? armor_prices[choice] : weapon_prices[choice-1];
        s->story_flags[11] = 0;
        if (s->credits >= price) {
            s->credits -= price; s->story_flags[11] = 1;
            if (s->party.enabled && s->party.selected) {
                uint8_t *person=s->party.people[s->party.selected];
                if (armor) { person[13]=(uint8_t)choice;person[14]=protection[choice]; } else person[11]=(uint8_t)choice;
            } else if (armor) { s->armor = (uint8_t)choice; s->armor_points = protection[choice]; }
            else s->weapon = (uint8_t)choice;
            if (s->npc.enabled) s->npc.allowance_pending = (uint8_t)btp_economy_below_cap(s);
        }
        break;
    }
    default: unsupported(s); return;
    }
    btp_script_native_return(&s->script,b,s->story_flags);
}

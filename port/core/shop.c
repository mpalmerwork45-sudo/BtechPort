#include "core/shop.h"

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
        /* Factual prices/one-member assignments from image 156F7..15817,
           9305..9317 and 94F4..9504. Other goods/party contexts are deferred. */
        int armor = s->script.native_action == 9;
        unsigned choice = armor ? s->script.choices[s->story_flags[10] ? 13 : 14] : s->script.choices[16];
        if (s->entry_slot != (armor ? 4 : 3) || choice != 1 || (!armor && s->story_flags[12])) {
            unsupported(s); return;
        }
        uint32_t price = armor ? 50u : 2u;
        s->story_flags[11] = 0;
        if (s->credits >= price) {
            s->credits -= price; s->story_flags[11] = 1;
            if (armor) { s->armor = 1; s->armor_points = 25; }
            else s->weapon = 1;
            if (s->npc.enabled) s->npc.allowance_pending = (uint8_t)(s->credits < s->allowance_cap);
        }
        break;
    }
    default: unsupported(s); return;
    }
    btp_script_native_return(&s->script,b,s->story_flags);
}

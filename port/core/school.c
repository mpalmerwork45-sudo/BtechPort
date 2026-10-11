#include "core/school.h"
#include "core/economy.h"
#include <stdio.h>
#include <string.h>

unsigned btp_school_price(unsigned rank) { return rank*125u+75u; }
static void fault(BtpState *s)
{
    s->script.status = BTP_SCRIPT_ERROR; s->script.error = BTP_SCRIPT_NATIVE_CONTEXT;
    s->script.fault_pc = s->script.pc >= 2 ? (uint16_t)(s->script.pc-2) : 0;
}
void btp_school_native(BtpState *s, const BtpResources *r)
{
    BtpScriptState *v = &s->script;
    if (s->entry_slot != 1 || s->story_flags[4] || !r->dialogue.length) { fault(s); return; }
    for (unsigned i = 0; i < 3; ++i) if (s->skills[i] > 4) { fault(s); return; }
    s->school = (BtpSchoolState){0};
    if (v->native_action == 4 && v->pc == 0xf05 && v->text_count == 1) {
        s->school.phase = BTP_SCHOOL_PRICES;
    } else if (v->native_action == 5 && v->pc == 0xf6c && s->story_flags[8] < 3 && !v->text_count) {
        unsigned course = s->story_flags[8], rank = s->skills[course];
        s->school = (BtpSchoolState){BTP_SCHOOL_TRANSCRIPT,(uint8_t)course,(uint8_t)rank,BTP_SCHOOL_TRAINED};
        s->story_flags[9] = 0;
        if (rank == 4) s->school.outcome = BTP_SCHOOL_MASTERED;
        else if (s->credits < btp_school_price(rank)) s->school.outcome = BTP_SCHOOL_NO_FUNDS;
        else {
            s->credits -= btp_school_price(rank); ++s->skills[course]; s->story_flags[9] = 1;
            if (s->npc.enabled) s->npc.allowance_pending = (uint8_t)btp_economy_below_cap(s);
        }
    } else { fault(s); return; }
    btp_script_native_return(v,&r->citadel,s->story_flags);
}
int btp_school_valid(const BtpState *s)
{
    const BtpSchoolState *c = &s->school; const BtpScriptState *v = &s->script;
    for (unsigned i = 0; i < 3; ++i) if (s->skills[i] > 4 || s->checkpoint_skills[i] > 4) return 0;
    if (c->phase > BTP_SCHOOL_TRANSCRIPT || c->course >= 3 || c->before > 4 || c->outcome > BTP_SCHOOL_MASTERED) return 0;
    if (!c->phase) return !c->course && !c->before && !c->outcome &&
        !(v->status == BTP_SCRIPT_MENU && v->menu_id == 9);
    if (s->mode != BTP_BUILDING || s->entry_slot != 1 || s->story_flags[4] || s->bank.phase || s->talk.phase) return 0;
    if (c->phase == BTP_SCHOOL_PRICES) return !c->course && !c->before && !c->outcome &&
        v->status == BTP_SCRIPT_MENU && v->menu_id == 9 && v->pc == 0xf0f && v->native_action == 4 &&
        v->text_count == 1 && v->text[0].offset == 0xe72;
    if (!s->checkpoint_valid || v->status != BTP_SCRIPT_WAIT || v->native_action != 5 || v->text_count ||
        c->course != s->story_flags[8] || c->before != s->checkpoint_skills[c->course] ||
        (c->outcome == BTP_SCHOOL_TRAINED ? v->pc != 0xf75 : v->pc != 0x10da)) return 0;
    int trained = c->outcome == BTP_SCHOOL_TRAINED;
    if (s->story_flags[9] != trained || s->credits != s->checkpoint_credits-(trained ? btp_school_price(c->before) : 0u)) return 0;
    if (trained && (c->before == 4 || s->checkpoint_credits < btp_school_price(c->before))) return 0;
    if (c->outcome == BTP_SCHOOL_MASTERED && c->before != 4) return 0;
    if (c->outcome == BTP_SCHOOL_NO_FUNDS && (c->before == 4 || s->checkpoint_credits >= btp_school_price(c->before))) return 0;
    for (unsigned i = 0; i < 3; ++i)
        if (s->skills[i] != s->checkpoint_skills[i]+(trained && i == c->course ? 1u : 0u)) return 0;
    return 1;
}
static int append(uint8_t *out, size_t cap, size_t *n, const uint8_t *p, size_t length)
{
    if (*n >= cap || length >= cap-*n) return 0;
    memcpy(out+*n,p,length); *n += length; out[*n] = 0; return 1;
}
static int literal(const BtpResources *r, unsigned id, uint8_t *out, size_t cap, size_t *n)
{
    const BtpDialogue *d = &r->dialogue;
    if (id >= BTP_TALK_STRINGS || d->offset[id] >= d->length || d->length > BTP_TALK_MAX ||
        d->size[id] >= d->length-d->offset[id] || d->bytes[d->offset[id]+d->size[id]]) return 0;
    return append(out,cap,n,d->bytes+d->offset[id],d->size[id]);
}
int btp_school_text(const BtpState *s, const BtpResources *r, uint8_t *out, size_t cap, size_t *n)
{
    *n = 0; if (!cap) return 0; out[0] = 0;
    if (s->school.phase == BTP_SCHOOL_PRICES) {
        if (!btp_script_text(&s->script,&r->citadel,out,cap)) return 0;
        *n = strlen((char *)out);
        for (unsigned i = 0; i < 3; ++i) {
            char price[8]; int length = snprintf(price,sizeof price,"%u",btp_school_price(s->skills[i]));
            if (length <= 0 || !append(out,cap,n,(const uint8_t *)price,(size_t)length)) return 0;
        }
        return 1;
    }
    if (s->school.phase != BTP_SCHOOL_TRANSCRIPT) return 0;
    return literal(r,BTP_SCHOOL_STR_INTRO,out,cap,n) && literal(r,BTP_SCHOOL_STR_RANK+s->school.before,out,cap,n) &&
        literal(r,BTP_SCHOOL_STR_SUBJECT+s->school.course,out,cap,n) &&
        (s->school.outcome == BTP_SCHOOL_TRAINED ||
            (s->school.outcome == BTP_SCHOOL_MASTERED ? literal(r,BTP_SCHOOL_STR_MASTERED,out,cap,n) :
                literal(r,BTP_SCHOOL_STR_NO_FUNDS,out,cap,n) && literal(r,BTP_SCHOOL_STR_COME_BACK,out,cap,n)));
}

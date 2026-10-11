#include "core/bank.h"
#include "core/economy.h"
#include <string.h>
#include <stdio.h>
#include <inttypes.h>

static void fault(BtpState *s, BtpScriptError error)
{
    s->script.status = BTP_SCRIPT_ERROR; s->script.error = (uint8_t)error;
    s->script.fault_pc = s->script.pc >= 2 ? (uint16_t)(s->script.pc-2) : 0;
}
static uint32_t input_value(const char input[8])
{
    uint32_t value = 0;
    for (unsigned i = 0; i < 7 && input[i]; ++i) value = value*10u+(unsigned)(input[i]-'0');
    return value;
}
static int input_valid(const char input[8])
{
    const char *end = memchr(input,0,8);
    if (!end || (input[0] == '0' && input[1])) return 0;
    for (const char *p = input; p < end; ++p) if (*p < '0' || *p > '9') return 0;
    for (const char *p = end; p < input+8; ++p) if (*p) return 0;
    return 1;
}
static void complete(BtpState *s, const BtpResources *r)
{
    /* Native handler returns to F8 02CD, F2, FB. The receipt remains visible
       until that bytecode wait is resumed; it is not an extra native pause. */
    s->bank.phase = BTP_BANK_MESSAGE;
    if (s->npc.enabled) s->npc.allowance_pending = (uint8_t)btp_economy_below_cap(s);
    btp_script_native_return(&s->script,&r->comstar,s->story_flags);
}
void btp_bank_native(BtpState *s, const BtpResources *r)
{
    if (s->entry_slot != 2 || s->story_flags[4] || !r->comstar.length) {
        fault(s,BTP_SCRIPT_NATIVE_CONTEXT); return;
    }
    if (!r->dialogue.length) { fault(s,BTP_SCRIPT_NATIVE_DATA); return; }
    s->bank = (BtpBankState){0};
    if (s->script.native_action == 6) {
        if (s->script.text_count != 1 || s->script.has_cash || s->script.has_accounts) {
            fault(s,BTP_SCRIPT_NATIVE_CONTEXT); return;
        }
        s->script.has_accounts = 1;
        btp_script_native_return(&s->script,&r->comstar,s->story_flags);
    } else if (s->script.native_action == 7) {
        if (!s->credits) { s->bank.outcome = BTP_BANK_NO_CASH; complete(s,r); }
        else s->bank.phase = BTP_BANK_MENU;
    } else if (s->script.native_action == 8) {
        if (!(s->investments[0] || s->investments[1] || s->investments[2])) {
            s->bank.outcome = BTP_BANK_NO_STOCK; complete(s,r);
        } else s->bank.phase = BTP_BANK_MENU;
    } else fault(s,BTP_SCRIPT_NATIVE_CONTEXT);
}
void btp_bank_input(BtpState *s, const BtpResources *r, BtpAction a)
{
    BtpBankState *b = &s->bank;
    if (b->phase == BTP_BANK_MENU) {
        uint8_t *choice = &s->script.choices[7];
        if (a == BTP_UP) *choice = (uint8_t)((*choice+2u)%3u);
        if (a == BTP_DOWN) *choice = (uint8_t)((*choice+1u)%3u);
        if (a != BTP_ACCEPT) return;
        b->company = *choice;
        b->available = s->script.native_action == 7 ? s->credits : s->investments[b->company];
        if (!b->available) { b->outcome = BTP_BANK_NOT_OWNED; complete(s,r); return; }
        b->phase = BTP_BANK_AMOUNT; b->input[0] = '0';
    } else if (b->phase == BTP_BANK_AMOUNT) {
        size_t n = strlen(b->input);
        if (a >= BTP_DIGIT_0 && a <= BTP_DIGIT_9 && n < 7) {
            if (b->input[0] == '0') { memset(b->input,0,sizeof b->input); n = 0; }
            b->input[n] = (char)('0'+a-BTP_DIGIT_0); b->input[n+1] = 0;
        } else if (a == BTP_CANCEL && n) b->input[n-1] = 0;
        else if (a == BTP_CLEAR_INPUT) { memset(b->input,0,sizeof b->input); b->input[0] = '0'; }
        else if (a == BTP_ACCEPT) {
            uint32_t requested = input_value(b->input);
            b->clamped = (uint8_t)(requested > b->available);
            b->amount = b->clamped ? b->available : requested;
            if (!b->amount) b->outcome = BTP_BANK_ZERO;
            else if (s->script.native_action == 7) {
                s->credits -= b->amount; s->investments[b->company] += b->amount;
            } else {
                s->investments[b->company] -= b->amount; s->credits += b->amount;
            }
            complete(s,r);
        }
    }
}
int btp_bank_valid(const BtpState *s)
{
    const BtpBankState *b = &s->bank; const BtpScriptState *v = &s->script;
    if (v->has_accounts > 1 || b->phase > BTP_BANK_MESSAGE || b->company >= 3 ||
        b->outcome > BTP_BANK_ZERO || b->clamped > 1 || !input_valid(b->input)) return 0;
    if (v->has_accounts && (s->entry_slot != 2 || s->mode != BTP_BUILDING ||
        v->status != BTP_SCRIPT_MENU || v->menu_id != 11 || v->native_action != 6 ||
        v->text_count != 2 || v->text[0].offset != 0x2d1 || v->has_cash)) return 0;
    if (!b->phase) return !b->company && !b->outcome && !b->clamped && !b->available &&
        !b->amount && !b->input[0] && !(v->status == BTP_SCRIPT_NATIVE && v->native_action != 12 &&
            !(v->native_action == 1 && s->mode == BTP_MISSION));
    if (s->mode != BTP_BUILDING || s->entry_slot != 2 || s->story_flags[4] ||
        !s->checkpoint_valid || v->has_accounts || (v->native_action != 7 && v->native_action != 8)) return 0;
    int buy = v->native_action == 7;
    if (b->phase != BTP_BANK_MESSAGE && v->status != BTP_SCRIPT_NATIVE) return 0;
    if (b->phase == BTP_BANK_MENU) return !b->company && !b->outcome && !b->clamped &&
        !b->available && !b->amount && !b->input[0];
    if (b->phase == BTP_BANK_AMOUNT) return b->company == v->choices[7] && b->available &&
        b->available == (buy ? s->credits : s->investments[b->company]) &&
        !b->amount && !b->outcome && !b->clamped;
    if (v->status != BTP_SCRIPT_WAIT || v->pc != 0x2cf || v->last_opcode != 0xfb) return 0;
    if (b->outcome == BTP_BANK_NO_CASH || b->outcome == BTP_BANK_NO_STOCK || b->outcome == BTP_BANK_NOT_OWNED) {
        if (b->available || b->amount || b->clamped || b->input[0]) return 0;
        if (b->outcome == BTP_BANK_NO_CASH) return buy && !s->credits && !b->company;
        if (b->outcome == BTP_BANK_NO_STOCK) return !buy && !b->company &&
            !(s->investments[0] || s->investments[1] || s->investments[2]);
        return !buy && b->company == v->choices[7] && !s->investments[b->company];
    }
    uint32_t requested = input_value(b->input);
    if (b->company != v->choices[7] || !b->available || b->clamped != (requested > b->available) ||
        b->amount != (b->clamped ? b->available : requested)) return 0;
    if (b->outcome == BTP_BANK_ZERO) return !b->amount;
    if (!b->amount || b->outcome != BTP_BANK_TRADED ||
        b->available != (buy ? s->checkpoint_credits : s->checkpoint_investments[b->company]) ||
        s->credits != (buy ? s->checkpoint_credits-b->amount : s->checkpoint_credits+b->amount)) return 0;
    for (unsigned i = 0; i < 3; ++i) {
        uint32_t expected = s->checkpoint_investments[i];
        if (i == b->company) expected = buy ? expected+b->amount : expected-b->amount;
        if (s->investments[i] != expected) return 0;
    }
    return 1;
}

static int append(uint8_t *out, size_t capacity, size_t *n, const uint8_t *p, size_t length)
{
    if (*n >= capacity || length >= capacity-*n) return 0;
    memcpy(out+*n,p,length); *n += length; out[*n] = 0; return 1;
}
static int literal(const BtpResources *r, unsigned id, uint8_t *out, size_t cap, size_t *n)
{
    const BtpDialogue *d = &r->dialogue;
    if (id >= BTP_TALK_STRINGS || !d->length || d->length > BTP_TALK_MAX ||
        d->offset[id] >= d->length || d->size[id] >= d->length-d->offset[id] ||
        d->bytes[d->offset[id]+d->size[id]]) return 0;
    return append(out,cap,n,d->bytes+d->offset[id],d->size[id]);
}
static int number(uint32_t value, uint8_t *out, size_t cap, size_t *n)
{
    char text[11]; int length = snprintf(text,sizeof text,"%" PRIu32,value);
    return length > 0 && append(out,cap,n,(const uint8_t *)text,(size_t)length);
}
int btp_bank_text(const BtpState *s, const BtpResources *r, uint8_t *out, size_t cap, size_t *n)
{
    *n = 0; if (!cap) return 0; out[0] = 0;
    const BtpScriptState *v = &s->script; const BtpBankState *b = &s->bank;
    if (v->has_accounts) {
        uint8_t validated[BTP_BLD_MAX+1];
        if (!btp_script_text(v,&r->comstar,validated,sizeof validated)) return 0;
        for (unsigned i = 0; i < v->text_count; ++i) {
            BtpTextSpan span = v->text[i];
            if (!append(out,cap,n,r->comstar.bytes+span.offset,span.length)) return 0;
            if (i) continue;
            if (!number(s->credits,out,cap,n)) return 0;
            unsigned count = 0;
            for (unsigned j = 0; j < 3; ++j) if (s->investments[j]) {
                if (!literal(r,BTP_BANK_STR_COMPANY+j,out,cap,n) || !number(s->investments[j],out,cap,n)) return 0;
                ++count;
            }
            if (!count && !literal(r,BTP_BANK_STR_NONE,out,cap,n)) return 0;
        }
        return 1;
    }
    int buy = v->native_action == 7;
    if (b->phase == BTP_BANK_MESSAGE && (b->outcome == BTP_BANK_NO_CASH || b->outcome == BTP_BANK_NO_STOCK)) {
        if (!btp_script_text(v,&r->comstar,out,cap)) return 0;
        *n = strlen((char *)out);
        return literal(r,buy ? BTP_BANK_STR_NO_CASH : BTP_BANK_STR_NO_STOCK,out,cap,n);
    }
    if (!literal(r,buy ? BTP_BANK_STR_BUY_MENU : BTP_BANK_STR_SELL_MENU,out,cap,n)) return 0;
    for (unsigned i = 0; i < 3; ++i) if (!literal(r,BTP_BANK_STR_COMPANY+i,out,cap,n)) return 0;
    if (b->phase == BTP_BANK_MENU) return 1;
    if (b->outcome == BTP_BANK_NOT_OWNED) return literal(r,BTP_BANK_STR_NOT_OWNED,out,cap,n);
    if (!literal(r,buy ? BTP_BANK_STR_BUY_AMOUNT : BTP_BANK_STR_SELL_AMOUNT,out,cap,n) ||
        !append(out,cap,n,(const uint8_t *)b->input,strlen(b->input)) ||
        !literal(r,buy ? BTP_BANK_STR_CASH_ACCOUNT : BTP_BANK_STR_STOCK_ACCOUNT,out,cap,n) ||
        !number(b->available,out,cap,n)) return 0;
    if (b->phase == BTP_BANK_AMOUNT) return 1;
    if (b->clamped && !literal(r,buy ? BTP_BANK_STR_BUY_CLAMP : BTP_BANK_STR_SELL_CLAMP,out,cap,n)) return 0;
    if (b->outcome == BTP_BANK_ZERO) return literal(r,buy ? BTP_BANK_STR_BUY_ZERO : BTP_BANK_STR_SELL_ZERO,out,cap,n) &&
        literal(r,BTP_BANK_STR_NOTHING,out,cap,n);
    return literal(r,buy ? BTP_BANK_STR_BOUGHT : BTP_BANK_STR_SOLD,out,cap,n) && number(b->amount,out,cap,n) &&
        literal(r,buy ? BTP_BANK_STR_IN : BTP_BANK_STR_OF,out,cap,n) &&
        literal(r,BTP_BANK_STR_COMPANY+b->company,out,cap,n) &&
        literal(r,buy ? BTP_BANK_STR_BUY_BALANCE : BTP_BANK_STR_SELL_BALANCE,out,cap,n) &&
        number(s->investments[b->company],out,cap,n) &&
        literal(r,buy ? BTP_BANK_STR_BUY_PERIOD : BTP_BANK_STR_SELL_PERIOD,out,cap,n);
}

#include "core/script.h"
#include "core/party.h"
#include <string.h>
#include <stdio.h>
#include <inttypes.h>

unsigned btp_menu_count(unsigned id)
{
    switch (id) {
    case 8: case 14: return 5;
    case 9: case 12: case 15: case 17: return 4;
    case 13: case 21: return 6;
    case 16: return 7;
    case 7: case 10: case 11: case 18: case 19: case 30: case 32: return 3;
    case 24: case 29: return 2;
    case 25:return 5;
    case 26:return 8;
    case 27:return 6;
    case 28:return 7;
    case 31:case 35:case 36:return 2;
    default: return 0;
    }
}
int btp_native_supported(unsigned action)
{
    return (action>=1 && action<=26) || action==28 || action==29 || action==30 || action==36 || action==37 || action==38 || action==39 || action==41 || action==42 || action==43 || action==44 || action==45 || action==46 || action==47;
}

static void fault(BtpScriptState *s, BtpScriptError error, uint16_t pc)
{
    s->status = BTP_SCRIPT_ERROR; s->error = (uint8_t)error; s->fault_pc = pc;
}
static uint16_t word(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1] << 8); }
static int available(BtpScriptState *s, const BtpBld *b, unsigned n, uint16_t op_pc)
{
    if (!b || b->length > BTP_BLD_MAX || s->pc > b->length || n > (unsigned)(b->length - s->pc)) {
        fault(s, BTP_SCRIPT_TRUNCATED, op_pc); return 0;
    }
    return 1;
}
static int jump(BtpScriptState *s, const BtpBld *b, uint16_t target, uint16_t op_pc)
{
    if (target >= b->length) { fault(s, BTP_SCRIPT_TARGET, op_pc); return 0; }
    s->pc = target; return 1;
}

static int state_index(BtpScriptState *s, uint8_t *story, unsigned index, uint16_t op_pc)
{
    /* Original indexes use CBW. Sparse modeled bytes must never alias another
       core field: D30C[0..22] and the shop refusal byte at index 39 only. */
    if (!story || index>=BTP_STORY_BYTES) {
        fault(s, BTP_SCRIPT_STATE_INDEX, op_pc); return 0;
    }
    return 1;
}
static void run(BtpScriptState *s, const BtpBld *b, uint8_t story[BTP_STORY_BYTES])
{
    /* Independently written from decoded original bytes and observed path.
       Addresses are relative to payload start, excluding the size word.
       Bounded Citadel and two-shop paths are verified; unknown actions fault. */
    for (unsigned budget = 0; budget < 256; ++budget) {
        uint16_t op_pc = s->pc;
        if (!available(s, b, 1, op_pc)) return;
        uint8_t op = b->bytes[s->pc++]; s->last_opcode = op;
        switch (op) {
        case 0xe4:
            if (!available(s,b,1,op_pc)) return;
            s->money_amount=b->bytes[s->pc++];s->status=BTP_SCRIPT_EFFECT;return;
        case 0xeb:case 0xec:
            if (!available(s,b,2,op_pc)) return;
            s->money_kind=op;s->money_target=word(b->bytes+s->pc);s->pc=(uint16_t)(s->pc+2);
            if (s->money_target>=b->length) { fault(s,BTP_SCRIPT_TARGET,op_pc);return; }
            s->status=BTP_SCRIPT_CONDITION;return;
        case 0xe9:
            if (!available(s,b,1,op_pc)) return;
            s->money_amount=b->bytes[s->pc++];s->status=BTP_SCRIPT_RECRUIT;return;
        case 0xe8: case 0xed:
            if (!available(s,b,op==0xe8 ? 3u : 4u,op_pc)) return;
            s->money_kind=op;s->money_amount=b->bytes[s->pc++];
            if (op==0xed) s->money_amount=(uint16_t)(s->money_amount|((unsigned)b->bytes[s->pc++]<<8));
            s->money_target=word(b->bytes+s->pc);s->pc=(uint16_t)(s->pc+2);
            if (s->money_target>=b->length) { fault(s,BTP_SCRIPT_TARGET,op_pc);return; }
            s->status=BTP_SCRIPT_CONDITION;return;
        case 0xe6:
            if (!available(s,b,4,op_pc)) return;
            s->position_x=word(b->bytes+s->pc);s->position_y=word(b->bytes+s->pc+2);
            s->pc=(uint16_t)(s->pc+4);s->has_position=1;break;
        case 0xe5:case 0xee: case 0xef:
            if (!available(s,b,op==0xee ? 2u : 4u,op_pc)) return;
            s->money_kind=op;s->money_amount=word(b->bytes+s->pc);s->pc=(uint16_t)(s->pc+2);
            if (op==0xef) {
                s->money_target=word(b->bytes+s->pc);s->pc=(uint16_t)(s->pc+2);
                if (s->money_target>=b->length) { fault(s,BTP_SCRIPT_TARGET,op_pc);return; }
            }
            s->status=BTP_SCRIPT_MONEY;return;
        case 0xfe: /* Font/presentation configuration; glyphs remain approximate. */
            if (!available(s, b, 1, op_pc)) return;
            s->font = b->bytes[s->pc++];
            if (s->font != 6 && s->font != 3 && s->font != 4) { fault(s, BTP_SCRIPT_FONT, op_pc); return; }
            break;
        case 0xfd: /* Clear text panel. */
            s->text_offset = s->text_length = s->text_count = 0;
            memset(s->text, 0, sizeof s->text);
            memset(s->text_column,0,sizeof s->text_column); memset(s->text_row,0,sizeof s->text_row);
            s->column = s->row = s->has_cash = s->cash_after = s->has_accounts = 0; s->cash_value = 0;
            s->mech_result = s->mech_after = 0;s->has_name=s->name_after=s->name_id=0; break;
        case 0xfa: /* Explicit scene request, supported scene zero only. */
            if (!available(s, b, 1, op_pc)) return;
            s->scene = b->bytes[s->pc++];
            if (s->scene != 0) { fault(s, BTP_SCRIPT_SCENE, op_pc); return; }
            break;
        case 0xfc: {
            uint16_t start = s->pc;
            while (s->pc < b->length && b->bytes[s->pc]) ++s->pc;
            if (s->pc == b->length) { fault(s, BTP_SCRIPT_TRUNCATED, op_pc); return; }
            unsigned length = (unsigned)(s->pc - start);
            if (s->text_count >= BTP_TEXT_SPANS || length + s->text_length > BTP_BLD_MAX) {
                fault(s, BTP_SCRIPT_TEXT_LIMIT, op_pc); return;
            }
            if (!s->text_count) s->text_offset = start;
            s->text_column[s->text_count] = s->column; s->text_row[s->text_count] = s->row;
            s->text[s->text_count++] = (BtpTextSpan){start, (uint16_t)length};
            s->text_length = (uint16_t)(s->text_length + length); ++s->pc;
            break;
        }
        case 0xf1: case 0xf4: {
            if (!available(s, b, 2, op_pc)) return;
            unsigned index = b->bytes[s->pc++];
            uint8_t value = b->bytes[s->pc++];
            if (!state_index(s, story, index, op_pc)) return;
            /* Original machine instructions write exactly one byte. */
            story[index] = op == 0xf4 ? value : (uint8_t)(story[index] + value);
            break;
        }
        case 0xf3: {
            if (!available(s, b, 1, op_pc)) return;
            unsigned index = b->bytes[s->pc++];
            if (!state_index(s, story, index, op_pc)) return;
            int value = story[index] < 128 ? story[index] : (int)story[index] - 256;
            int at = (int)s->pc + 2 * value; /* Original CBW, then SHL. */
            if (at < 0 || at + 2 > b->length) { fault(s, BTP_SCRIPT_TARGET, op_pc); return; }
            if (!jump(s, b, word(b->bytes + at), op_pc)) return;
            break;
        }
        case 0xf7: {
            if (!available(s, b, 3, op_pc)) return;
            unsigned index = b->bytes[s->pc++];
            uint16_t target = word(b->bytes + s->pc); s->pc = (uint16_t)(s->pc + 2);
            if (!state_index(s, story, index, op_pc)) return;
            if (story[index] && !jump(s, b, target, op_pc)) return;
            break;
        }
        case 0xf0: /* Verified column zero: shops 14/22, ComStar 15. */
            if (!available(s,b,2,op_pc)) return;
            s->column = b->bytes[s->pc++]; s->row = b->bytes[s->pc++];
            if (s->column>26 || s->row>24) { fault(s,BTP_SCRIPT_SCENE,op_pc); return; }
            break;
        case 0xf6:
            if (!available(s,b,2,op_pc)) return;
            s->confirm_target = word(b->bytes+s->pc); s->pc = (uint16_t)(s->pc+2);
            if (s->confirm_target >= b->length) { fault(s,BTP_SCRIPT_TARGET,op_pc); return; }
            s->confirm_selected = 0; s->status = BTP_SCRIPT_CONFIRM; return;
        case 0xf5:
            if (!available(s, b, 1, op_pc)) return;
            s->native_action = b->bytes[s->pc++];
            if (!btp_native_supported(s->native_action)) { fault(s, BTP_SCRIPT_OPCODE, op_pc); return; }
            if (s->native_action == 12) {
                s->text_offset = s->text_length = s->text_count = 0;
                memset(s->text, 0, sizeof s->text);
                memset(s->text_column,0,sizeof s->text_column); memset(s->text_row,0,sizeof s->text_row);
                s->column = s->row = s->has_cash = s->cash_after = s->has_accounts = 0; s->cash_value = 0;
            }
            s->pause_units = 0;
            s->status = BTP_SCRIPT_NATIVE; return;
        case 0xf2: /* Original software delay(50), then keyboard flush.
                       Model records the request; native pacing is approximate. */
            s->pause_units = 50; break;
        case 0xea: /* Yield until original sequence playback finishes. */
            if (!available(s,b,2,op_pc)) return;
            s->animation_kind = b->bytes[s->pc++]; s->animation_flags = b->bytes[s->pc++];
            /* THEATER.BLD also invokes the existing O0..O9 films, often
               with the original forced-play flag 2. The game layer checks
               the building context before starting the decoded animation. */
            if (s->animation_kind>=22 || s->animation_flags>2) { fault(s,BTP_SCRIPT_SCENE,op_pc); return; }
            s->pause_units = 0; s->status = BTP_SCRIPT_ANIMATION; return;
        case 0xfb:
            s->status = BTP_SCRIPT_WAIT; return;
        case 0xf8:
            if (!available(s, b, 2, op_pc)) return;
            if (!jump(s, b, word(b->bytes + s->pc), op_pc)) return;
            break;
        case 0xf9:
            if (!available(s, b, 1, op_pc)) return;
            s->menu_id = b->bytes[s->pc++];
            unsigned count = btp_menu_count(s->menu_id);
            if (!count) { fault(s, BTP_SCRIPT_MENU_ID, op_pc); return; }
            if (!available(s, b, 2*count, op_pc)) return;
            s->menu_table = s->pc;
            for (unsigned i = 0; i < count; ++i)
                if (word(b->bytes + s->pc + 2 * i) >= b->length) {
                    fault(s, BTP_SCRIPT_TARGET, op_pc); return;
                }
            s->pc = (uint16_t)(s->pc + 2*count);
            s->selected = s->choices[s->menu_id];
            if (s->selected >= count) { fault(s,BTP_SCRIPT_MENU_ID,op_pc); return; }
            s->status = BTP_SCRIPT_MENU; return;
        case 0xff:
            s->status = BTP_SCRIPT_END; return;
        default:
            fault(s, BTP_SCRIPT_OPCODE, op_pc); return;
        }
    }
    fault(s, BTP_SCRIPT_BUDGET, s->pc);
}

void btp_script_start(BtpScriptState *s, const BtpBld *b, uint8_t story[BTP_STORY_BYTES])
{
    *s = (BtpScriptState){0}; run(s, b, story);
}
void btp_script_resume(BtpScriptState *s, const BtpBld *b, uint8_t story[BTP_STORY_BYTES])
{
    if (s->status != BTP_SCRIPT_WAIT) return;
    s->status = BTP_SCRIPT_RUNNING; s->pause_units = 0; run(s, b, story);
}
void btp_script_native_return(BtpScriptState *s, const BtpBld *b, uint8_t story[BTP_STORY_BYTES])
{
    if (s->status != BTP_SCRIPT_NATIVE) return;
    s->status = BTP_SCRIPT_RUNNING; s->pause_units = 0; run(s, b, story);
}
void btp_script_animation_return(BtpScriptState *s, const BtpBld *b, uint8_t story[BTP_STORY_BYTES])
{
    if (s->status != BTP_SCRIPT_ANIMATION) return;
    /* Original Barracks wake-up screenshot retains the text preceding EA and
       appends the announcement after it; animation completion is not F2. */
    s->status = BTP_SCRIPT_RUNNING; s->pause_units = 0; run(s,b,story);
}
void btp_script_money_return(BtpScriptState *s,const BtpBld *b,uint8_t story[BTP_STORY_BYTES],uint32_t *credits)
{
    if (s->status!=BTP_SCRIPT_MONEY || !credits) return;
    if (s->money_kind==0xef) {
        if (*credits>=s->money_amount) s->pc=s->money_target;
    } else if (s->money_kind==0xee) *credits=*credits>=s->money_amount ? *credits-s->money_amount : 0;
    else if (s->money_kind==0xe5) { int32_t amount=s->money_amount<32768 ? s->money_amount : (int32_t)s->money_amount-65536;*credits+=(uint32_t)amount; }
    else { fault(s,BTP_SCRIPT_OPCODE,s->pc);return; }
    s->money_kind=0;s->money_amount=s->money_target=0;s->status=BTP_SCRIPT_RUNNING;run(s,b,story);
}
void btp_script_condition_return(BtpScriptState *s,const BtpBld *b,uint8_t story[BTP_STORY_BYTES],int yes)
{
    if (s->status!=BTP_SCRIPT_CONDITION && s->status!=BTP_SCRIPT_RECRUIT) return;
    if (yes && s->status==BTP_SCRIPT_CONDITION) s->pc=s->money_target;
    s->money_kind=0;s->money_amount=s->money_target=0;s->status=BTP_SCRIPT_RUNNING;run(s,b,story);
}
int btp_script_choose(BtpScriptState *s, const BtpBld *b, unsigned choice, uint8_t story[BTP_STORY_BYTES])
{
    unsigned count = btp_menu_count(s->menu_id);
    if (s->status != BTP_SCRIPT_MENU || !count || choice >= count) return 0;
    s->selected = (uint8_t)choice;
    s->choices[s->menu_id] = (uint8_t)choice;
    if (!b || b->length > BTP_BLD_MAX || s->menu_table > b->length || (unsigned)(b->length - s->menu_table) < 2*count) {
        fault(s, BTP_SCRIPT_TRUNCATED, s->menu_table); return 0;
    }
    if (!jump(s, b, word(b->bytes + s->menu_table + 2 * choice), s->menu_table)) return 0;
    s->status = BTP_SCRIPT_RUNNING; s->pause_units = 0; run(s, b, story);
    return s->status != BTP_SCRIPT_ERROR;
}
void btp_script_confirm(BtpScriptState *s, const BtpBld *b, int yes, uint8_t story[BTP_STORY_BYTES])
{
    if (s->status != BTP_SCRIPT_CONFIRM) return;
    if (yes && !jump(s,b,s->confirm_target,(uint16_t)(s->pc-3))) return;
    s->status = BTP_SCRIPT_RUNNING; run(s,b,story);
}
int btp_script_text(const BtpScriptState *s, const BtpBld *b, uint8_t *out, size_t capacity)
{
    if (!s || !b || !out || b->length > BTP_BLD_MAX || s->text_count > BTP_TEXT_SPANS ||
        s->text_length > BTP_BLD_MAX || capacity <= s->text_length) return 0;
    if ((!s->text_count && (s->text_offset || s->text_length)) ||
        (s->text_count && s->text_offset != s->text[0].offset)) return 0;
    size_t length = 0, literal_length = 0;
    if (s->has_cash > 1 || s->cash_after > s->text_count) return 0;
    if (s->has_name>1 || s->name_after>s->text_count || s->name_id>=10) return 0;
    const char *name=btp_character_name(s->name_id);size_t name_size=strlen(name);
    if (s->has_name && !s->name_after) { if (name_size>=capacity) return 0;memcpy(out,name,name_size);length=name_size; }
    for (unsigned i = 0; i < s->text_count; ++i) {
        BtpTextSpan span = s->text[i];
        if (span.offset >= b->length || span.length >= b->length - span.offset ||
            b->bytes[span.offset + span.length] || literal_length + span.length > s->text_length ||
            length + span.length >= capacity) return 0;
        memcpy(out + length, b->bytes + span.offset, span.length); length += span.length;
        literal_length += span.length;
        if (s->has_name && s->name_after==i+1u) { if (name_size>=capacity-length) return 0;memcpy(out+length,name,name_size);length+=name_size; }
        if (s->has_cash && s->cash_after == i+1) {
            char number[11]; int n = snprintf(number,sizeof number,"%" PRIu32,s->cash_value);
            if (n < 1 || (size_t)n >= capacity-length) return 0;
            memcpy(out+length,number,(size_t)n); length += (size_t)n;
        }
    }
    if (literal_length != s->text_length || (s->has_cash && !s->cash_after)) return 0;
    out[length] = 0; return 1;
}
int btp_script_menu_text(const BtpScriptState *s, const BtpBld *b, uint8_t *out, size_t capacity, size_t *length)
{
    uint8_t validated[BTP_BLD_MAX+1];
    if (!out || !length || !capacity || !btp_script_text(s,b,validated,sizeof validated)) return 0;
    *length = 0;
    for (unsigned i = 0; i < s->text_count; ++i) {
        if (s->text_row[i] == 22) continue; /* cash is drawn separately in the sidebar */
        BtpTextSpan span = s->text[i];
        if (span.length >= capacity-*length) return 0;
        memcpy(out+*length,b->bytes+span.offset,span.length); *length += span.length;
    }
    out[*length] = 0; return 1;
}
const char *btp_script_error_name(unsigned error)
{
    static const char *names[] = {"none", "truncated bytecode", "unsupported opcode",
        "invalid jump target", "unsupported menu", "unsupported scene", "instruction budget", "unsupported font",
        "unsupported state index", "text span limit", "native dialogue data missing",
        "unsupported native dialogue context"};
    return error <= BTP_SCRIPT_NATIVE_CONTEXT ? names[error] : "invalid error";
}

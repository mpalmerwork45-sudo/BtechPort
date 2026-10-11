#include "core/script.h"
#include <string.h>

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
    /* Original indexes use CBW. Negative or out-of-window indexes are outside
       this milestone's modeled D30C[0..22] state, and must not alias memory. */
    if (!story || index >= BTP_STORY_BYTES) {
        fault(s, BTP_SCRIPT_STATE_INDEX, op_pc); return 0;
    }
    return 1;
}
static void run(BtpScriptState *s, const BtpBld *b, uint8_t story[BTP_STORY_BYTES])
{
    /* Independently written from decoded original bytes and observed path.
       Addresses are relative to payload start, excluding the size word.
       Citadel menu, Hall, first Katrina visit and untrained repeat are verified. */
    for (unsigned budget = 0; budget < 256; ++budget) {
        uint16_t op_pc = s->pc;
        if (!available(s, b, 1, op_pc)) return;
        uint8_t op = b->bytes[s->pc++]; s->last_opcode = op;
        switch (op) {
        case 0xfe: /* Font/presentation configuration; glyphs remain approximate. */
            if (!available(s, b, 1, op_pc)) return;
            s->font = b->bytes[s->pc++];
            if (s->font != 6) { fault(s, BTP_SCRIPT_FONT, op_pc); return; }
            break;
        case 0xfd: /* Clear text panel. */
            s->text_offset = s->text_length = s->text_count = 0;
            memset(s->text, 0, sizeof s->text); break;
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
        case 0xf5:
            if (!available(s, b, 1, op_pc)) return;
            if (b->bytes[s->pc++] != 0x0c) { fault(s, BTP_SCRIPT_OPCODE, op_pc); return; }
            s->text_offset = s->text_length = s->text_count = 0;
            memset(s->text, 0, sizeof s->text);
            s->pause_units = 0;
            s->status = BTP_SCRIPT_NATIVE; return;
        case 0xf2: /* Original software delay(50), then keyboard flush.
                       Model records the request; native pacing is approximate. */
            s->pause_units = 50; break;
        case 0xfb:
            s->status = BTP_SCRIPT_WAIT; return;
        case 0xf8:
            if (!available(s, b, 2, op_pc)) return;
            if (!jump(s, b, word(b->bytes + s->pc), op_pc)) return;
            break;
        case 0xf9:
            if (!available(s, b, 1, op_pc)) return;
            s->menu_id = b->bytes[s->pc++];
            if (s->menu_id != 8) { fault(s, BTP_SCRIPT_MENU_ID, op_pc); return; }
            if (!available(s, b, 10, op_pc)) return;
            s->menu_table = s->pc;
            for (unsigned i = 0; i < 5; ++i)
                if (word(b->bytes + s->pc + 2 * i) >= b->length) {
                    fault(s, BTP_SCRIPT_TARGET, op_pc); return;
                }
            s->pc = (uint16_t)(s->pc + 10);
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
int btp_script_choose(BtpScriptState *s, const BtpBld *b, unsigned choice, uint8_t story[BTP_STORY_BYTES])
{
    if (s->status != BTP_SCRIPT_MENU || choice >= 5) return 0;
    s->selected = (uint8_t)choice;
    if (!b || b->length > BTP_BLD_MAX || s->menu_table > b->length || b->length - s->menu_table < 10) {
        fault(s, BTP_SCRIPT_TRUNCATED, s->menu_table); return 0;
    }
    if (!jump(s, b, word(b->bytes + s->menu_table + 2 * choice), s->menu_table)) return 0;
    s->status = BTP_SCRIPT_RUNNING; s->pause_units = 0; run(s, b, story);
    return s->status != BTP_SCRIPT_ERROR;
}
int btp_script_text(const BtpScriptState *s, const BtpBld *b, uint8_t *out, size_t capacity)
{
    if (!s || !b || !out || b->length > BTP_BLD_MAX || s->text_count > BTP_TEXT_SPANS ||
        s->text_length > BTP_BLD_MAX || capacity <= s->text_length) return 0;
    if ((!s->text_count && (s->text_offset || s->text_length)) ||
        (s->text_count && s->text_offset != s->text[0].offset)) return 0;
    size_t length = 0;
    for (unsigned i = 0; i < s->text_count; ++i) {
        BtpTextSpan span = s->text[i];
        if (span.offset >= b->length || span.length >= b->length - span.offset ||
            b->bytes[span.offset + span.length] || length + span.length > s->text_length) return 0;
        memcpy(out + length, b->bytes + span.offset, span.length); length += span.length;
    }
    if (length != s->text_length) return 0;
    out[length] = 0; return 1;
}
const char *btp_script_error_name(unsigned error)
{
    static const char *names[] = {"none", "truncated bytecode", "unsupported opcode",
        "invalid jump target", "unsupported menu", "unsupported scene", "instruction budget", "unsupported font",
        "unsupported state index", "text span limit", "native dialogue data missing",
        "unsupported native dialogue context"};
    return error <= BTP_SCRIPT_NATIVE_CONTEXT ? names[error] : "invalid error";
}

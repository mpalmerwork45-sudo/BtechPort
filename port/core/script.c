#include "core/script.h"

static void fault(BtpScriptState *s, BtpScriptError error, uint16_t pc)
{
    s->status = BTP_SCRIPT_ERROR; s->error = (uint8_t)error; s->fault_pc = pc;
}
static uint16_t word(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1] << 8); }
static int available(BtpScriptState *s, const BtpBld *b, unsigned n, uint16_t op_pc)
{
    if (s->pc > b->length || n > (unsigned)(b->length - s->pc)) {
        fault(s, BTP_SCRIPT_TRUNCATED, op_pc); return 0;
    }
    return 1;
}
static int jump(BtpScriptState *s, const BtpBld *b, uint16_t target, uint16_t op_pc)
{
    if (target >= b->length) { fault(s, BTP_SCRIPT_TARGET, op_pc); return 0; }
    s->pc = target; return 1;
}

static void run(BtpScriptState *s, const BtpBld *b)
{
    /* Independently written from decoded original bytes and observed path.
       Addresses are relative to payload start, excluding the size word.
       Only the Citadel menu, Hall of Legends and exit subset is supported. */
    for (unsigned budget = 0; budget < 256; ++budget) {
        uint16_t op_pc = s->pc;
        if (!available(s, b, 1, op_pc)) return;
        uint8_t op = b->bytes[s->pc++]; s->last_opcode = op;
        switch (op) {
        case 0xfe: /* Font/presentation configuration; glyphs remain approximate. */
            if (!available(s, b, 1, op_pc)) return;
            s->font = b->bytes[s->pc++]; break;
        case 0xfd: /* Clear text panel. */
            s->text_offset = s->text_length = 0; break;
        case 0xfa: /* Explicit scene request, supported scene zero only. */
            if (!available(s, b, 1, op_pc)) return;
            s->scene = b->bytes[s->pc++];
            if (s->scene != 0) { fault(s, BTP_SCRIPT_SCENE, op_pc); return; }
            break;
        case 0xfc: {
            s->text_offset = s->pc;
            while (s->pc < b->length && b->bytes[s->pc]) ++s->pc;
            if (s->pc == b->length) { fault(s, BTP_SCRIPT_TRUNCATED, op_pc); return; }
            s->text_length = (uint16_t)(s->pc - s->text_offset); ++s->pc;
            break;
        }
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

void btp_script_start(BtpScriptState *s, const BtpBld *b)
{
    *s = (BtpScriptState){0}; run(s, b);
}
void btp_script_resume(BtpScriptState *s, const BtpBld *b)
{
    if (s->status != BTP_SCRIPT_WAIT) return;
    s->status = BTP_SCRIPT_RUNNING; s->pause_units = 0; run(s, b);
}
int btp_script_choose(BtpScriptState *s, const BtpBld *b, unsigned choice)
{
    if (s->status != BTP_SCRIPT_MENU || choice >= 5) return 0;
    s->selected = (uint8_t)choice;
    if (s->menu_table > b->length || b->length - s->menu_table < 10) {
        fault(s, BTP_SCRIPT_TRUNCATED, s->menu_table); return 0;
    }
    if (!jump(s, b, word(b->bytes + s->menu_table + 2 * choice), s->menu_table)) return 0;
    s->status = BTP_SCRIPT_RUNNING; s->pause_units = 0; run(s, b);
    return s->status != BTP_SCRIPT_ERROR;
}
const char *btp_script_error_name(unsigned error)
{
    static const char *names[] = {"none", "truncated bytecode", "unsupported opcode",
        "invalid jump target", "unsupported menu", "unsupported scene", "instruction budget"};
    return error <= BTP_SCRIPT_BUDGET ? names[error] : "invalid error";
}

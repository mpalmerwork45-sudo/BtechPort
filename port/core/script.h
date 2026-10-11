#ifndef BTP_SCRIPT_H
#define BTP_SCRIPT_H
#include "data/resources.h"

typedef enum { BTP_SCRIPT_RUNNING, BTP_SCRIPT_MENU, BTP_SCRIPT_WAIT,
    BTP_SCRIPT_END, BTP_SCRIPT_ERROR } BtpScriptStatus;
typedef enum { BTP_SCRIPT_OK, BTP_SCRIPT_TRUNCATED, BTP_SCRIPT_OPCODE,
    BTP_SCRIPT_TARGET, BTP_SCRIPT_MENU_ID, BTP_SCRIPT_SCENE, BTP_SCRIPT_BUDGET,
    BTP_SCRIPT_FONT, BTP_SCRIPT_STATE_INDEX, BTP_SCRIPT_TEXT_LIMIT } BtpScriptError;
enum { BTP_STORY_BYTES = 23, BTP_TEXT_SPANS = 8 };
typedef struct { uint16_t offset, length; } BtpTextSpan;
typedef struct {
    uint16_t pc, text_offset, text_length, menu_table, fault_pc;
    uint16_t pause_units;
    uint8_t status, selected, menu_id, font, scene, last_opcode, error;
    uint8_t text_count;
    BtpTextSpan text[BTP_TEXT_SPANS];
} BtpScriptState;

void btp_script_start(BtpScriptState *state, const BtpBld *script, uint8_t story[BTP_STORY_BYTES]);
void btp_script_resume(BtpScriptState *state, const BtpBld *script, uint8_t story[BTP_STORY_BYTES]);
int btp_script_choose(BtpScriptState *state, const BtpBld *script, unsigned choice, uint8_t story[BTP_STORY_BYTES]);
int btp_script_text(const BtpScriptState *state, const BtpBld *script, uint8_t *output, size_t capacity);
const char *btp_script_error_name(unsigned error);
#endif

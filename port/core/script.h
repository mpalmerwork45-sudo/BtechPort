#ifndef BTP_SCRIPT_H
#define BTP_SCRIPT_H
#include "data/resources.h"

typedef enum { BTP_SCRIPT_RUNNING, BTP_SCRIPT_MENU, BTP_SCRIPT_WAIT,
    BTP_SCRIPT_END, BTP_SCRIPT_ERROR, BTP_SCRIPT_NATIVE, BTP_SCRIPT_CONFIRM } BtpScriptStatus;
typedef enum { BTP_SCRIPT_OK, BTP_SCRIPT_TRUNCATED, BTP_SCRIPT_OPCODE,
    BTP_SCRIPT_TARGET, BTP_SCRIPT_MENU_ID, BTP_SCRIPT_SCENE, BTP_SCRIPT_BUDGET,
    BTP_SCRIPT_FONT, BTP_SCRIPT_STATE_INDEX, BTP_SCRIPT_TEXT_LIMIT,
    BTP_SCRIPT_NATIVE_DATA, BTP_SCRIPT_NATIVE_CONTEXT } BtpScriptError;
/* Sparse modeled window: D30C[0..22] plus shop refusal D333[39].
   Index 23's loop timer lives in BtpNpcState; 23..38 are unsupported here. */
enum { BTP_STORY_PREFIX = 23, BTP_STORY_BYTES = 40, BTP_TEXT_SPANS = 8, BTP_MENUS = 31 };
typedef struct { uint16_t offset, length; } BtpTextSpan;
typedef struct {
    uint16_t pc, text_offset, text_length, menu_table, fault_pc;
    uint16_t pause_units;
    uint8_t status, selected, menu_id, font, scene, last_opcode, error;
    uint8_t text_count;
    BtpTextSpan text[BTP_TEXT_SPANS];
    uint8_t choices[BTP_MENUS], native_action, confirm_selected;
    uint16_t confirm_target;
    uint8_t column, row, text_column[BTP_TEXT_SPANS], text_row[BTP_TEXT_SPANS];
    uint8_t has_cash, cash_after;
    uint32_t cash_value;
    uint8_t has_accounts;
} BtpScriptState;

void btp_script_start(BtpScriptState *state, const BtpBld *script, uint8_t story[BTP_STORY_BYTES]);
void btp_script_resume(BtpScriptState *state, const BtpBld *script, uint8_t story[BTP_STORY_BYTES]);
void btp_script_native_return(BtpScriptState *state, const BtpBld *script, uint8_t story[BTP_STORY_BYTES]);
int btp_script_choose(BtpScriptState *state, const BtpBld *script, unsigned choice, uint8_t story[BTP_STORY_BYTES]);
void btp_script_confirm(BtpScriptState *state, const BtpBld *script, int yes, uint8_t story[BTP_STORY_BYTES]);
unsigned btp_menu_count(unsigned id);
int btp_script_text(const BtpScriptState *state, const BtpBld *script, uint8_t *output, size_t capacity);
int btp_script_menu_text(const BtpScriptState *state, const BtpBld *script, uint8_t *output, size_t capacity, size_t *length);
const char *btp_script_error_name(unsigned error);
#endif

#include "core/game.h"
#include <string.h>

void btp_start(BtpState *s)
{
    *s = (BtpState){.x_half = 69, .y_half = 25, .map_id = 1, .gate = 85};
}

void btp_tick(BtpState *s, const BtpMap *m, BtpAction a)
{
    ++s->tick; /* Explicit unsigned wrapping; no clock or graphics dependency. */
    if (a < BTP_UP || a > BTP_RIGHT) return;
    s->facing = (uint8_t)a;
    int x = s->x_half, y = s->y_half;
    if (a == BTP_UP) --y;
    if (a == BTP_DOWN) ++y;
    if (a == BTP_LEFT) --x;
    if (a == BTP_RIGHT) ++x;
    if (x < 0 || y < 0 || x >= 2 * m->width || y >= 2 * m->height) {
        s->blocked = BTP_EDGE;
        return;
    }
    /* The reference trace includes x=68 -> 67 (free) -> 66 (blocked).
       Collision samples the player's offset position, not the cursor's tile:
       ceil(x_half/2), floor(y_half/2). Multi-unit footprints are deferred. */
    int tile_x = (x + 1) / 2, tile_y = y / 2;
    if (tile_x >= m->width) { s->blocked = BTP_EDGE; return; }
    if (btp_map_tile(m, tile_x, tile_y) >= s->gate) {
        s->blocked = BTP_WALL;
        return;
    }
    s->x_half = (uint16_t)x; s->y_half = (uint16_t)y; s->blocked = BTP_CLEAR;
}

int btp_entrance(const BtpState *s, const BtpMap *m)
{
    for (int i = 0; i < 8; ++i)
        if (s->x_half == (m->entrance_x[i] & 127) &&
            s->y_half == (m->entrance_y[i] & 127)) return i;
    return -1;
}

static void finish_script(BtpState *s, const BtpMap *m)
{
    if (s->script.status == BTP_SCRIPT_ERROR) {
        /* Prototype recovery: roll back the entire failed menu choice,
           including writes before a dialogue pause, not an original rule. */
        if (s->checkpoint_valid) memcpy(s->story_flags, s->story_checkpoint, BTP_STORY_BYTES);
        s->mode = BTP_SCRIPT_FAULT;
    } else if (s->script.status == BTP_SCRIPT_END) {
        /* The original commits the pending outdoor step after FF. */
        s->x_half = m->entrance_x[s->entry_slot] & 127;
        s->y_half = m->entrance_y[s->entry_slot] & 127;
        s->mode = BTP_EXPLORE;
    }
    if (s->script.status == BTP_SCRIPT_ERROR || s->script.status == BTP_SCRIPT_MENU ||
        s->script.status == BTP_SCRIPT_END) {
        s->checkpoint_valid = 0; memset(s->story_checkpoint, 0, BTP_STORY_BYTES);
    }
}
void btp_game_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    if (s->mode == BTP_EXPLORE) {
        BtpState moved = *s;
        btp_tick(&moved, &r->map, a);
        if (a >= BTP_UP && a <= BTP_RIGHT && !moved.blocked &&
            (moved.x_half != s->x_half || moved.y_half != s->y_half) &&
            btp_entrance(&moved, &r->map) == 1) {
            moved.x_half = s->x_half; moved.y_half = s->y_half;
            moved.mode = BTP_ENTRY; moved.entry_slot = 1; moved.entry_selected = 0;
        }
        *s = moved; return;
    }
    ++s->tick;
    if (s->mode == BTP_ENTRY) {
        if (a == BTP_LEFT || a == BTP_UP) s->entry_selected = 0;
        if (a == BTP_RIGHT || a == BTP_DOWN) s->entry_selected = 1;
        if (a == BTP_CANCEL || (a == BTP_ACCEPT && s->entry_selected)) {
            s->x_half = r->map.entrance_x[s->entry_slot] & 127;
            s->y_half = r->map.entrance_y[s->entry_slot] & 127;
            s->mode = BTP_EXPLORE;
        } else if (a == BTP_ACCEPT) {
            uint8_t selected = s->script.selected;
            s->story_flags[10] = 1;
            s->mode = BTP_BUILDING;
            btp_script_start(&s->script, &r->citadel, s->story_flags);
            s->script.selected = selected; /* Original retains menu highlight on re-entry. */
            finish_script(s, &r->map);
        }
        return;
    }
    if (s->mode == BTP_SCRIPT_FAULT) {
        if (a == BTP_CANCEL) {
            /* Explicit prototype recovery; finish_script rolled back the choice. */
            uint8_t selected = s->script.selected;
            btp_script_start(&s->script, &r->citadel, s->story_flags);
            s->script.selected = selected; s->mode = BTP_BUILDING;
            finish_script(s, &r->map);
        }
        return;
    }
    if (s->script.status == BTP_SCRIPT_MENU) {
        if (a == BTP_UP) s->script.selected = (uint8_t)((s->script.selected + 4) % 5);
        if (a == BTP_DOWN) s->script.selected = (uint8_t)((s->script.selected + 1) % 5);
        if (a == BTP_ACCEPT) {
            memcpy(s->story_checkpoint, s->story_flags, BTP_STORY_BYTES); s->checkpoint_valid = 1;
            (void)btp_script_choose(&s->script, &r->citadel, s->script.selected, s->story_flags);
        }
    } else if (s->script.status == BTP_SCRIPT_WAIT && a == BTP_ACCEPT)
        btp_script_resume(&s->script, &r->citadel, s->story_flags);
    finish_script(s, &r->map);
}

static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1] << 8); }

void btp_state_encode(const BtpState *s, uint8_t b[BTP_STATE_BYTES])
{
    memset(b, 0, BTP_STATE_BYTES);
    memcpy(b, "BTP3", 4); b[4] = 3;
    for (unsigned i = 0; i < 4; ++i) b[8+i] = (uint8_t)(s->tick >> (8 * i));
    b[12] = (uint8_t)s->x_half; b[13] = (uint8_t)(s->x_half >> 8);
    b[14] = (uint8_t)s->y_half; b[15] = (uint8_t)(s->y_half >> 8);
    b[16] = s->map_id; b[17] = s->gate; b[18] = s->facing; b[19] = s->blocked;
    b[20] = s->mode; b[21] = s->entry_selected; b[22] = s->entry_slot;
    memcpy(b + 24, s->story_flags, 16);
    put16(b + 40, s->script.pc); put16(b + 42, s->script.text_offset);
    put16(b + 44, s->script.text_length); put16(b + 46, s->script.menu_table);
    put16(b + 48, s->script.fault_pc); put16(b + 50, s->script.pause_units);
    b[52] = s->script.status; b[53] = s->script.selected; b[54] = s->script.menu_id;
    b[55] = s->script.font; b[56] = s->script.scene; b[57] = s->script.last_opcode; b[58] = s->script.error;
    memcpy(b + 59, s->story_flags + 16, BTP_STORY_BYTES - 16);
    b[66] = s->script.text_count;
    for (unsigned i = 0; i < BTP_TEXT_SPANS; ++i) {
        put16(b + 68 + 4*i, s->script.text[i].offset);
        put16(b + 70 + 4*i, s->script.text[i].length);
    }
    memcpy(b + 100, s->story_checkpoint, BTP_STORY_BYTES); b[123] = s->checkpoint_valid;
}

int btp_state_decode(const uint8_t *b, size_t n, const BtpMap *m, const BtpBld *script, BtpState *s)
{
    if (!b || !m || !s || n < 24) return 0;
    int version = n == 24 && !memcmp(b, "BTP1", 4) && b[4] == 1 ? 1 :
        n == 64 && !memcmp(b, "BTP2", 4) && b[4] == 2 ? 2 :
        n == BTP_STATE_BYTES && !memcmp(b, "BTP3", 4) && b[4] == 3 ? 3 : 0;
    if (!version) return 0;
    for (unsigned i = 5; i < 8; ++i) if (b[i]) return 0;
    if (version == 1) { for (unsigned i = 20; i < 24; ++i) if (b[i]) return 0; }
    else {
        if (b[23]) return 0;
        if (version == 2) { for (unsigned i = 59; i < 64; ++i) if (b[i]) return 0; }
        else {
            if (b[67]) return 0;
            for (unsigned i = 124; i < BTP_STATE_BYTES; ++i) if (b[i]) return 0;
        }
    }
    BtpState result = {0};
    for (unsigned i = 0; i < 4; ++i) result.tick |= (uint32_t)b[8+i] << (8 * i);
    result.x_half = (uint16_t)(b[12] | (uint16_t)b[13] << 8);
    result.y_half = (uint16_t)(b[14] | (uint16_t)b[15] << 8);
    result.map_id = b[16]; result.gate = b[17]; result.facing = b[18]; result.blocked = b[19];
    if (result.map_id != 1 || result.gate != 85 || result.facing > BTP_RIGHT ||
        result.blocked > BTP_EDGE || result.x_half >= 2 * m->width || result.y_half >= 2 * m->height)
        return 0;
    if (version > 1) {
        result.mode = b[20]; result.entry_selected = b[21]; result.entry_slot = b[22];
        memcpy(result.story_flags, b + 24, 16);
        result.script = (BtpScriptState){.pc=get16(b+40),.text_offset=get16(b+42),
            .text_length=get16(b+44),.menu_table=get16(b+46),.fault_pc=get16(b+48),.pause_units=get16(b+50),
            .status=b[52],.selected=b[53],.menu_id=b[54],.font=b[55],.scene=b[56],.last_opcode=b[57],.error=b[58]};
        BtpScriptState *v = &result.script;
        if (version == 3) {
            memcpy(result.story_flags + 16, b + 59, BTP_STORY_BYTES - 16);
            v->text_count = b[66];
            for (unsigned i = 0; i < BTP_TEXT_SPANS; ++i)
                v->text[i] = (BtpTextSpan){get16(b+68+4*i),get16(b+70+4*i)};
            memcpy(result.story_checkpoint, b + 100, BTP_STORY_BYTES); result.checkpoint_valid = b[123];
        } else {
            if (v->text_offset || v->text_length) {
                v->text_count = 1; v->text[0] = (BtpTextSpan){v->text_offset,v->text_length};
            }
            if (v->status == BTP_SCRIPT_WAIT) {
                result.checkpoint_valid = 1;
                memcpy(result.story_checkpoint, result.story_flags, BTP_STORY_BYTES);
            }
        }
        if (result.mode > BTP_SCRIPT_FAULT || result.entry_selected > 1 || result.entry_slot > 7 ||
            v->status > BTP_SCRIPT_ERROR || v->selected > 4 || v->error > BTP_SCRIPT_TEXT_LIMIT ||
            v->text_count > BTP_TEXT_SPANS || result.checkpoint_valid > 1) return 0;
        for (unsigned i = v->text_count; i < BTP_TEXT_SPANS; ++i)
            if (v->text[i].offset || v->text[i].length) return 0;
        if (result.checkpoint_valid) {
            if (result.mode != BTP_BUILDING || v->status != BTP_SCRIPT_WAIT) return 0;
        } else for (unsigned i = 0; i < BTP_STORY_BYTES; ++i)
            if (result.story_checkpoint[i]) return 0;
        if (result.mode != BTP_EXPLORE && result.entry_slot != 1) return 0;
        if (result.mode == BTP_BUILDING && v->status != BTP_SCRIPT_MENU && v->status != BTP_SCRIPT_WAIT) return 0;
        if ((result.mode == BTP_SCRIPT_FAULT) != (v->status == BTP_SCRIPT_ERROR) ||
            (v->status == BTP_SCRIPT_ERROR) != (v->error != 0)) return 0;
        if ((result.mode == BTP_EXPLORE || result.mode == BTP_ENTRY) &&
            v->status != BTP_SCRIPT_RUNNING && v->status != BTP_SCRIPT_END) return 0;
        if (v->pc || v->text_offset || v->text_length || v->text_count || v->status != BTP_SCRIPT_RUNNING) {
            if (!script || script->length > BTP_BLD_MAX || v->pc > script->length || v->fault_pc > script->length) return 0;
            uint8_t text[BTP_BLD_MAX + 1];
            if (!btp_script_text(v, script, text, sizeof text)) return 0;
            if (v->status == BTP_SCRIPT_MENU && (v->menu_id != 8 ||
                v->menu_table > script->length || script->length - v->menu_table < 10)) return 0;
            if (v->status == BTP_SCRIPT_MENU)
                for (unsigned i = 0; i < 5; ++i)
                    if (get16(script->bytes + v->menu_table + 2*i) >= script->length) return 0;
        }
    }
    *s = result;
    return 1;
}

const char *btp_action_name(BtpAction a)
{
    static const char *names[] = {"idle", "up", "down", "left", "right", "accept", "cancel"};
    return a >= BTP_IDLE && a <= BTP_CANCEL ? names[a] : "invalid";
}
int btp_action_parse(const char *name, BtpAction *a)
{
    for (int i = BTP_IDLE; i <= BTP_CANCEL; ++i)
        if (!strcmp(name, btp_action_name((BtpAction)i))) { *a = (BtpAction)i; return 1; }
    return 0;
}
const char *btp_mode_name(unsigned mode)
{
    static const char *names[] = {"local-exploration", "entry-confirm", "building", "script-error"};
    return mode <= BTP_SCRIPT_FAULT ? names[mode] : "invalid";
}

#include "core/game.h"
#include "core/talk.h"
#include "core/npc.h"
#include "core/shop.h"
#include "core/bank.h"
#include "core/economy.h"
#include "core/school.h"
#include <string.h>

void btp_start(BtpState *s)
{
    *s = (BtpState){.x_half = 69, .y_half = 25, .map_id = 1, .gate = 85,
        .credits=35,.allowance_cap=50};
    static const uint8_t packed[8] = {99,81,53,99,18,4,4,70};
    for (unsigned i = 0; i < 8; ++i) s->npc_pairs[i][0] = packed[i];
    s->npc = (BtpNpcState){.enabled=1,.phase=1,.rng={31,66,171},.search=99,
        .loop_timer=249,.allowance_pending=1};
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
const BtpBld *btp_building_bld(const BtpResources *r, unsigned slot)
{
    return !r ? NULL : slot == 1 ? &r->citadel : slot == 2 ? &r->comstar :
        slot == 3 ? &r->weapon : slot == 4 ? &r->armor : NULL;
}
static void start_building(BtpState *s, const BtpResources *r)
{
    uint8_t choices[BTP_MENUS]; memcpy(choices,s->script.choices,sizeof choices);
    btp_script_start(&s->script,btp_building_bld(r,s->entry_slot),s->story_flags);
    memcpy(s->script.choices,choices,sizeof choices);
    if (s->script.status == BTP_SCRIPT_MENU) s->script.selected = choices[s->script.menu_id];
}

static void finish_script(BtpState *s, const BtpMap *m)
{
    if (s->script.status == BTP_SCRIPT_ERROR) {
        /* Prototype recovery: roll back the entire failed menu choice,
           including writes before a dialogue pause, not an original rule. */
        if (s->checkpoint_valid) {
            memcpy(s->story_flags, s->story_checkpoint, BTP_STORY_BYTES);
            s->talk_result = s->checkpoint_talk_result;
            s->credits = s->checkpoint_credits; s->weapon = s->checkpoint_weapon;
            memcpy(s->investments,s->checkpoint_investments,sizeof s->investments);
            memcpy(s->skills,s->checkpoint_skills,sizeof s->skills);
            s->armor = s->checkpoint_armor; s->armor_points = s->checkpoint_armor_points;
            if (s->npc.enabled) s->npc.allowance_pending = (uint8_t)btp_economy_below_cap(s);
        }
        s->bank = (BtpBankState){0};
        s->school = (BtpSchoolState){0};
        s->script.has_accounts = 0;
        s->mode = BTP_SCRIPT_FAULT;
    } else if (s->script.status == BTP_SCRIPT_END) {
        /* The original commits the pending outdoor step after FF. */
        s->x_half = m->entrance_x[s->entry_slot] & 127;
        s->y_half = m->entrance_y[s->entry_slot] & 127;
        s->mode = BTP_EXPLORE;
        s->bank = (BtpBankState){0};
        s->school = (BtpSchoolState){0};
        s->script.has_accounts = 0;
    }
    if (s->script.status == BTP_SCRIPT_ERROR || s->script.status == BTP_SCRIPT_MENU ||
        s->script.status == BTP_SCRIPT_END) {
        s->checkpoint_valid = 0; memset(s->story_checkpoint, 0, BTP_STORY_BYTES);
        s->checkpoint_talk_result = 0;
        s->checkpoint_credits = 0;
        memset(s->checkpoint_investments,0,sizeof s->checkpoint_investments);
        memset(s->checkpoint_skills,0,sizeof s->checkpoint_skills);
        s->checkpoint_weapon = s->checkpoint_armor = s->checkpoint_armor_points = 0;
    }
}
void btp_game_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    if (s->mode == BTP_EXPLORE) {
        if (s->npc.fault) { ++s->tick; return; }
        BtpState moved = *s;
        btp_tick(&moved, &r->map, a);
        int entrance = btp_entrance(&moved,&r->map);
        if (a >= BTP_UP && a <= BTP_RIGHT && !moved.blocked &&
            (moved.x_half != s->x_half || moved.y_half != s->y_half) &&
            (entrance >= 1 && entrance <= 4)) {
            moved.x_half = s->x_half; moved.y_half = s->y_half;
            moved.mode = BTP_ENTRY; moved.entry_slot = (uint8_t)entrance; moved.entry_selected = 0;
            uint8_t choices[BTP_MENUS]; memcpy(choices,moved.script.choices,sizeof choices);
            moved.script = (BtpScriptState){.selected=s->script.selected};
            memcpy(moved.script.choices,choices,sizeof choices);
        }
        *s = moved;
        if (s->mode == BTP_EXPLORE) btp_npc_tick(s,&r->map);
        return;
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
            s->story_flags[10] = 1;
            s->mode = BTP_BUILDING;
            start_building(s,r);
            finish_script(s, &r->map);
        }
        return;
    }
    if (s->mode == BTP_SCRIPT_FAULT) {
        if (a == BTP_CANCEL) {
            /* Explicit prototype recovery; finish_script rolled back the choice. */
            start_building(s,r); s->mode = BTP_BUILDING;
            finish_script(s, &r->map);
        }
        return;
    }
    if (s->script.status == BTP_SCRIPT_MENU) {
        unsigned count = btp_menu_count(s->script.menu_id);
        if (a == BTP_UP && count) s->script.selected = (uint8_t)((s->script.selected + count-1) % count);
        if (a == BTP_DOWN && count) s->script.selected = (uint8_t)((s->script.selected + 1u) % count);
        s->script.choices[s->script.menu_id] = s->script.selected;
        if (a == BTP_ACCEPT) {
            memcpy(s->story_checkpoint, s->story_flags, BTP_STORY_BYTES); s->checkpoint_valid = 1;
            s->checkpoint_talk_result = s->talk_result;
            s->checkpoint_credits = s->credits; s->checkpoint_weapon = s->weapon;
            memcpy(s->checkpoint_investments,s->investments,sizeof s->investments);
            memcpy(s->checkpoint_skills,s->skills,sizeof s->skills);
            s->checkpoint_armor = s->armor; s->checkpoint_armor_points = s->armor_points;
            s->school = (BtpSchoolState){0};
            (void)btp_script_choose(&s->script, btp_building_bld(r,s->entry_slot), s->script.selected, s->story_flags);
        }
    } else if (s->script.status == BTP_SCRIPT_WAIT && a == BTP_ACCEPT) {
        s->bank = (BtpBankState){0};
        s->school = (BtpSchoolState){0};
        btp_script_resume(&s->script, btp_building_bld(r,s->entry_slot), s->story_flags);
    }
    else if (s->script.status == BTP_SCRIPT_CONFIRM) {
        if (a == BTP_LEFT || a == BTP_UP) s->script.confirm_selected = 0;
        if (a == BTP_RIGHT || a == BTP_DOWN) s->script.confirm_selected = 1;
        if (a == BTP_ACCEPT) btp_script_confirm(&s->script,btp_building_bld(r,s->entry_slot),
            !s->script.confirm_selected,s->story_flags);
    }
    else if (s->script.status == BTP_SCRIPT_NATIVE) {
        if (s->script.native_action == 12) btp_talk_input(s,r,a);
        else if (s->bank.phase) btp_bank_input(s,r,a);
    }
    for (unsigned service = 0; service < 16 && s->script.status == BTP_SCRIPT_NATIVE; ++service) {
        if (s->script.native_action == 12) { if (!s->talk.phase) btp_talk_begin(s,r); break; }
        if (s->script.native_action == 4 || s->script.native_action == 5) btp_school_native(s,r);
        else if (s->script.native_action >= 6 && s->script.native_action <= 8) {
            if (!s->bank.phase) btp_bank_native(s,r);
            if (s->script.status == BTP_SCRIPT_NATIVE) break;
        } else btp_shop_native(s,r);
    }
    if (s->script.status == BTP_SCRIPT_NATIVE && s->script.native_action != 12 && !s->bank.phase) {
        s->script.status = BTP_SCRIPT_ERROR; s->script.error = BTP_SCRIPT_BUDGET;
        s->script.fault_pc = s->script.pc;
    }
    finish_script(s, &r->map);
}

static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1] << 8); }

void btp_state_encode(const BtpState *s, uint8_t b[BTP_STATE_BYTES])
{
    memset(b, 0, BTP_STATE_BYTES);
    memcpy(b, "BTP8", 4); b[4] = 8;
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
    memcpy(b + 59, s->story_flags + 16, BTP_STORY_PREFIX - 16);
    b[66] = s->script.text_count;
    for (unsigned i = 0; i < BTP_TEXT_SPANS; ++i) {
        put16(b + 68 + 4*i, s->script.text[i].offset);
        put16(b + 70 + 4*i, s->script.text[i].length);
    }
    memcpy(b + 100, s->story_checkpoint, BTP_STORY_PREFIX); b[123] = s->checkpoint_valid;
    b[124] = s->talk.phase; b[125] = s->talk.selected; b[126] = s->talk.count; b[127] = s->talk.mask;
    memcpy(b+128,s->npc_pairs,16);
    b[144] = s->talk.room; b[145] = s->talk.actor; b[146] = s->talk_result; b[147] = s->recruitment;
    b[148] = s->checkpoint_talk_result; b[149] = s->conversation_checkpoint;
    b[150] = s->npc.enabled; b[151] = s->npc.phase; b[152] = s->npc.clock;
    memcpy(b+153,s->npc.rng,3); put16(b+156,s->npc.search);
    b[158] = s->npc.bias; b[159] = s->npc.fault;
    for (unsigned i = 0; i < 8; ++i) {
        put16(b+160+5*i,s->npc.actor[i].x); put16(b+162+5*i,s->npc.actor[i].y);
        b[164+5*i] = s->npc.actor[i].direction;
    }
    b[200] = s->npc.loop_timer;
    b[201] = s->npc.allowance_pending;
    for (unsigned i = 0; i < 4; ++i) {
        b[224+i] = (uint8_t)(s->credits >> (8*i));
        b[238+i] = (uint8_t)(s->script.cash_value >> (8*i));
        b[294+i] = (uint8_t)(s->checkpoint_credits >> (8*i));
    }
    put16(b+228,s->allowance_cap); b[230] = s->weapon; b[231] = s->armor; b[232] = s->armor_points;
    b[233] = s->story_flags[39]; b[234] = s->story_checkpoint[39];
    b[235] = s->script.confirm_selected; b[236] = s->script.native_action; b[237] = s->script.cash_after;
    memcpy(b+242,s->script.choices,BTP_MENUS); put16(b+273,s->script.confirm_target);
    b[275] = s->script.column; b[276] = s->script.row; b[277] = s->script.has_cash;
    memcpy(b+278,s->script.text_column,BTP_TEXT_SPANS); memcpy(b+286,s->script.text_row,BTP_TEXT_SPANS);
    b[298] = s->checkpoint_weapon; b[299] = s->checkpoint_armor; b[300] = s->checkpoint_armor_points;
    for (unsigned i = 0; i < 3; ++i) for (unsigned j = 0; j < 4; ++j) {
        b[320+4*i+j] = (uint8_t)(s->investments[i] >> (8*j));
        b[332+4*i+j] = (uint8_t)(s->checkpoint_investments[i] >> (8*j));
    }
    b[344] = s->bank.phase; b[345] = s->bank.company; b[346] = s->bank.outcome; b[347] = s->bank.clamped;
    for (unsigned i = 0; i < 4; ++i) {
        b[348+i] = (uint8_t)(s->bank.available >> (8*i));
        b[352+i] = (uint8_t)(s->bank.amount >> (8*i));
    }
    memcpy(b+356,s->bank.input,8); b[364] = s->script.has_accounts;
    memcpy(b+384,s->skills,3); memcpy(b+387,s->checkpoint_skills,3);
    b[390] = s->school.phase; b[391] = s->school.course;
    b[392] = s->school.before; b[393] = s->school.outcome;
}

int btp_state_decode(const uint8_t *b, size_t n, const BtpMap *m, const BtpBld *script, BtpState *s)
{
    if (!b || !m || !s || n < 24) return 0;
    int version = n == 24 && !memcmp(b, "BTP1", 4) && b[4] == 1 ? 1 :
        n == 64 && !memcmp(b, "BTP2", 4) && b[4] == 2 ? 2 :
        n == 128 && !memcmp(b, "BTP3", 4) && b[4] == 3 ? 3 :
        n == 160 && !memcmp(b, "BTP4", 4) && b[4] == 4 ? 4 :
        n == 224 && !memcmp(b, "BTP5", 4) && b[4] == 5 ? 5 :
        n == 320 && !memcmp(b, "BTP6", 4) && b[4] == 6 ? 6 :
        n == 384 && !memcmp(b, "BTP7", 4) && b[4] == 7 ? 7 :
        n == BTP_STATE_BYTES && !memcmp(b, "BTP8", 4) && b[4] == 8 ? 8 : 0;
    if (!version) return 0;
    for (unsigned i = 5; i < 8; ++i) if (b[i]) return 0;
    if (version == 1) { for (unsigned i = 20; i < 24; ++i) if (b[i]) return 0; }
    else {
        if (b[23]) return 0;
        if (version == 2) { for (unsigned i = 59; i < 64; ++i) if (b[i]) return 0; }
        else {
            if (b[67]) return 0;
            unsigned end = version >= 6 ? 224u : (unsigned)n;
            for (unsigned i = version == 3 ? 124u : version == 4 ? 150u : 202u; i < end; ++i) if (b[i]) return 0;
            if (version >= 6) for (unsigned i = 301; i < 320; ++i) if (b[i]) return 0;
            if (version >= 7) for (unsigned i = 365; i < 384; ++i) if (b[i]) return 0;
            if (version == 8) for (unsigned i = 394; i < n; ++i) if (b[i]) return 0;
        }
    }
    BtpState result = {.credits=35,.allowance_cap=50};
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
        if (version >= 3) {
            memcpy(result.story_flags + 16, b + 59, BTP_STORY_PREFIX - 16);
            v->text_count = b[66];
            for (unsigned i = 0; i < BTP_TEXT_SPANS; ++i)
                v->text[i] = (BtpTextSpan){get16(b+68+4*i),get16(b+70+4*i)};
            memcpy(result.story_checkpoint, b + 100, BTP_STORY_PREFIX); result.checkpoint_valid = b[123];
            if (version >= 4) {
                result.talk = (BtpTalkState){.phase=b[124],.selected=b[125],.count=b[126],.mask=b[127],
                    .room=b[144],.actor=b[145]};
                memcpy(result.npc_pairs,b+128,16);
                result.talk_result = b[146]; result.recruitment = b[147];
                result.checkpoint_talk_result = b[148]; result.conversation_checkpoint = b[149];
                if (version >= 5) {
                    result.npc.enabled = b[150]; result.npc.phase = b[151]; result.npc.clock = b[152];
                    memcpy(result.npc.rng,b+153,3); result.npc.search = get16(b+156);
                    result.npc.bias = b[158]; result.npc.fault = b[159];
                    result.npc.loop_timer = b[200];
                    result.npc.allowance_pending = b[201];
                    if (version == 5 && result.npc.enabled && !result.npc.allowance_pending) result.credits = 50;
                    for (unsigned i = 0; i < 8; ++i) result.npc.actor[i] =
                        (BtpNpc){get16(b+160+5*i),get16(b+162+5*i),b[164+5*i]};
                }
            }
        } else {
            if (v->text_offset || v->text_length) {
                v->text_count = 1; v->text[0] = (BtpTextSpan){v->text_offset,v->text_length};
            }
            if (v->status == BTP_SCRIPT_WAIT) {
                result.checkpoint_valid = 1;
                memcpy(result.story_checkpoint, result.story_flags, BTP_STORY_BYTES);
            }
        }
        if (version >= 6) {
            result.credits = result.checkpoint_credits = 0;
            for (unsigned i = 0; i < 4; ++i) {
                result.credits |= (uint32_t)b[224+i] << (8*i);
                v->cash_value |= (uint32_t)b[238+i] << (8*i);
                result.checkpoint_credits |= (uint32_t)b[294+i] << (8*i);
            }
            result.allowance_cap = get16(b+228); result.weapon = b[230]; result.armor = b[231]; result.armor_points = b[232];
            result.story_flags[39] = b[233]; result.story_checkpoint[39] = b[234];
            v->confirm_selected = b[235]; v->native_action = b[236]; v->cash_after = b[237];
            memcpy(v->choices,b+242,BTP_MENUS); v->confirm_target = get16(b+273);
            v->column = b[275]; v->row = b[276]; v->has_cash = b[277];
            memcpy(v->text_column,b+278,BTP_TEXT_SPANS); memcpy(v->text_row,b+286,BTP_TEXT_SPANS);
            result.checkpoint_weapon = b[298]; result.checkpoint_armor = b[299]; result.checkpoint_armor_points = b[300];
            if (version >= 7) {
                for (unsigned i = 0; i < 3; ++i) for (unsigned j = 0; j < 4; ++j) {
                    result.investments[i] |= (uint32_t)b[320+4*i+j] << (8*j);
                    result.checkpoint_investments[i] |= (uint32_t)b[332+4*i+j] << (8*j);
                }
                result.bank = (BtpBankState){.phase=b[344],.company=b[345],.outcome=b[346],.clamped=b[347]};
                for (unsigned i = 0; i < 4; ++i) {
                    result.bank.available |= (uint32_t)b[348+i] << (8*i);
                    result.bank.amount |= (uint32_t)b[352+i] << (8*i);
                }
                memcpy(result.bank.input,b+356,8); v->has_accounts = b[364];
            }
            if (version == 8) {
                memcpy(result.skills,b+384,3); memcpy(result.checkpoint_skills,b+387,3);
                result.school = (BtpSchoolState){b[390],b[391],b[392],b[393]};
            }
            if (result.allowance_cap != 50 || result.weapon > 1 || result.armor > 1 ||
                result.armor_points != (result.armor ? 25 : 0) || result.checkpoint_weapon > 1 || result.checkpoint_armor > 1 ||
                result.checkpoint_armor_points != (result.checkpoint_armor ? 25 : 0) ||
                v->confirm_selected > 1 || v->has_cash > 1 || v->cash_after > v->text_count ||
                (!v->has_cash && (v->cash_after || v->cash_value)) || (v->has_cash && !v->cash_after) ||
                v->column || (v->row && v->row != 14 && v->row != 22 && !(version >= 7 && v->row == 15)) ||
                (v->native_action && (v->native_action < (version == 8 ? 4 : version == 7 ? 6 : 9) || v->native_action > 12) &&
                    !(v->status == BTP_SCRIPT_ERROR && v->error == BTP_SCRIPT_OPCODE && v->last_opcode == 0xf5)) ||
                (result.npc.enabled && result.npc.allowance_pending != btp_economy_below_cap(&result))) return 0;
            for (unsigned i = 0; i < BTP_TEXT_SPANS; ++i)
                if (v->text_column[i] || (v->text_row[i] && v->text_row[i] != 14 && v->text_row[i] != 22 &&
                    !(version >= 7 && v->text_row[i] == 15)) ||
                    (i >= v->text_count && v->text_row[i])) return 0;
            for (unsigned i = 0; i < BTP_MENUS; ++i) {
                unsigned count = btp_menu_count(i);
                if (count ? v->choices[i] >= count : v->choices[i] != 0) return 0;
            }
        } else {
            if (v->menu_id == 8) v->choices[8] = v->selected;
            if (v->status == BTP_SCRIPT_NATIVE) v->native_action = 12;
            if (result.checkpoint_valid) result.checkpoint_credits = result.credits;
        }
        if (result.mode > BTP_SCRIPT_FAULT || result.entry_selected > 1 || result.entry_slot > 7 ||
            v->status > (version >= 6 ? BTP_SCRIPT_CONFIRM : version >= 4 ? BTP_SCRIPT_NATIVE : BTP_SCRIPT_ERROR) || v->selected > (version >= 6 ? 6 : 4) ||
            v->error > (version >= 4 ? BTP_SCRIPT_NATIVE_CONTEXT : BTP_SCRIPT_TEXT_LIMIT) ||
            v->text_count > BTP_TEXT_SPANS || result.checkpoint_valid > 1) return 0;
        for (unsigned i = v->text_count; i < BTP_TEXT_SPANS; ++i)
            if (v->text[i].offset || v->text[i].length) return 0;
        if (result.checkpoint_valid) {
            if (result.mode != BTP_BUILDING || (v->status != BTP_SCRIPT_WAIT && v->status != BTP_SCRIPT_NATIVE &&
                v->status != BTP_SCRIPT_CONFIRM)) return 0;
        } else {
            if (result.checkpoint_talk_result || result.checkpoint_credits || result.checkpoint_weapon ||
                result.checkpoint_armor || result.checkpoint_armor_points) return 0;
            for (unsigned i = 0; i < 3; ++i) if (result.checkpoint_investments[i] || result.checkpoint_skills[i]) return 0;
            for (unsigned i = 0; i < BTP_STORY_BYTES; ++i) if (result.story_checkpoint[i]) return 0;
        }
        if (result.mode != BTP_EXPLORE && result.entry_slot != 1 &&
            !(version >= 6 && (result.entry_slot == 3 || result.entry_slot == 4)) &&
            !(version >= 7 && result.entry_slot == 2)) return 0;
        if (result.mode == BTP_BUILDING && v->status != BTP_SCRIPT_MENU && v->status != BTP_SCRIPT_WAIT &&
            v->status != BTP_SCRIPT_NATIVE && v->status != BTP_SCRIPT_CONFIRM) return 0;
        if ((result.mode == BTP_SCRIPT_FAULT) != (v->status == BTP_SCRIPT_ERROR) ||
            (v->status == BTP_SCRIPT_ERROR) != (v->error != 0)) return 0;
        if ((result.mode == BTP_EXPLORE || result.mode == BTP_ENTRY) &&
            v->status != BTP_SCRIPT_RUNNING && v->status != BTP_SCRIPT_END) return 0;
        if (v->pc || v->text_offset || v->text_length || v->text_count || v->status != BTP_SCRIPT_RUNNING) {
            if (!script || script->length > BTP_BLD_MAX || v->pc > script->length || v->fault_pc > script->length) return 0;
            uint8_t text[BTP_BLD_MAX + 1];
            if (!btp_script_text(v, script, text, sizeof text)) return 0;
            if (v->status == BTP_SCRIPT_NATIVE && (v->pc < 2 || script->bytes[v->pc-2] != 0xf5 ||
                script->bytes[v->pc-1] != v->native_action || v->pause_units ||
                (v->native_action == 12 ? v->text_count != 0 :
                    version < 7 || (v->native_action != 7 && v->native_action != 8)))) return 0;
            if (v->status == BTP_SCRIPT_CONFIRM && (v->pc < 3 || script->bytes[v->pc-3] != 0xf6 ||
                v->confirm_target != get16(script->bytes+v->pc-2) || v->confirm_target >= script->length)) return 0;
            unsigned count = btp_menu_count(v->menu_id);
            if (v->status == BTP_SCRIPT_MENU && (!count || v->selected >= count ||
                v->menu_table < 2 || v->menu_table > script->length || (unsigned)(script->length - v->menu_table) < 2*count ||
                script->bytes[v->menu_table-2] != 0xf9 || script->bytes[v->menu_table-1] != v->menu_id ||
                v->pc != v->menu_table+2*count || v->selected != v->choices[v->menu_id])) return 0;
            if (v->status == BTP_SCRIPT_MENU)
                for (unsigned i = 0; i < count; ++i)
                    if (get16(script->bytes + v->menu_table + 2*i) >= script->length) return 0;
        }
        if (!btp_talk_valid(&result,m) || !btp_npc_valid(&result,m) || !btp_bank_valid(&result) ||
            !btp_school_valid(&result)) return 0;
    }
    *s = result;
    return 1;
}

const char *btp_action_name(BtpAction a)
{
    static const char *names[] = {"idle", "up", "down", "left", "right", "accept", "cancel",
        "0","1","2","3","4","5","6","7","8","9","clear"};
    return a >= BTP_IDLE && a <= BTP_CLEAR_INPUT ? names[a] : "invalid";
}
int btp_action_parse(const char *name, BtpAction *a)
{
    for (int i = BTP_IDLE; i <= BTP_CLEAR_INPUT; ++i)
        if (!strcmp(name, btp_action_name((BtpAction)i))) { *a = (BtpAction)i; return 1; }
    return 0;
}
const char *btp_mode_name(unsigned mode)
{
    static const char *names[] = {"local-exploration", "entry-confirm", "building", "script-error"};
    return mode <= BTP_SCRIPT_FAULT ? names[mode] : "invalid";
}

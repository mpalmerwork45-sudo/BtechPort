#include "frontend/pixels.h"
#include "core/bank.h"
#include "core/school.h"
#include "core/training.h"
#include "data/sprites.h"
#include <stdio.h>
#include <string.h>

const uint32_t btp_palette[16] = {
    0xff000000,0xff0000aa,0xff00aa00,0xff00aaaa,0xffaa0000,0xffaa00aa,0xffaa5500,0xffaaaaaa,
    0xff555555,0xff5555ff,0xff55ff55,0xff55ffff,0xffff5555,0xffff55ff,0xffffff55,0xffffffff
};
/* VERIFIED for MAP1 terrain in the captured VGA reference frames. Resource
   indices stay unchanged; this is a display palette mapping, not decoding. */
static const uint8_t terrain_palette[16] = {0,1,2,3,4,9,6,7,8,1,10,11,12,13,14,15};
static const uint8_t sprite_palette[16] = {0,0,2,3,4,9,6,7,8,1,10,11,12,13,14,15};

int btp_draw_sprite(const BtpGraphic *atlas, unsigned id, int x, int y,
                    unsigned hidden_rows, int clip_left, uint32_t f[BTP_PIXELS])
{
    BtpSpriteRect r;
    if (!atlas || !f || atlas->format != 2 || !btp_sprite_rect(id,&r) ||
        hidden_rows > r.height || clip_left < 0 || clip_left > 320) return 0;
    /* Clip before addition, including malicious diagnostic coordinates. */
    if (x <= -(int)r.width || x >= 320 || y <= -(int)r.height || y >= 200) return 1;
    for (unsigned row = 0; row < r.height-hidden_rows; ++row) {
        int dy = y+(int)row;
        if (dy < 0 || dy >= 200) continue;
        for (unsigned col = 0; col < r.width; ++col) {
            int dx = x+(int)col;
            if (dx < clip_left || dx >= 320) continue;
            unsigned color = atlas->pixels[(r.y+row)*320+r.x+col] & 15u;
            if (color) f[dy*320+dx] = btp_palette[sprite_palette[color]];
        }
    }
    return 1;
}
static unsigned hidden_rows(const BtpMap *m, unsigned x, unsigned y)
{
    /* Original 0665/091C: water quadrants hide two or four bottom rows.
       The sprite anchor is eight pixels east of the cursor coordinate. */
    static const unsigned masks[4] = {3,9,6,12};
    unsigned tile = btp_map_tile(m,(int)((x+1)/2),(int)(y/2));
    return tile < 48 && (tile & masks[(x&1u)+2*(y&1u)]) ? ((tile&0xf0u) == 32 ? 4u : 2u) : 0;
}

/* Small independently drawn 5x7 diagnostic font; no BIOS/reference font copied. */
static const char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:./- ,';!?()$\"abcdefghijklmnopqrstuvwxyz";
static const uint8_t glyphs[][7] = {
 {14,17,17,31,17,17,17},{30,17,17,30,17,17,30},{14,17,16,16,16,17,14},
 {30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16},
 {14,17,16,23,17,17,15},{17,17,17,31,17,17,17},{14,4,4,4,4,4,14},
 {7,2,2,2,2,18,12},{17,18,20,24,20,18,17},{16,16,16,16,16,16,31},
 {17,27,21,21,17,17,17},{17,25,21,19,17,17,17},{14,17,17,17,17,17,14},
 {30,17,17,30,16,16,16},{14,17,17,17,21,18,13},{30,17,17,30,20,18,17},
 {15,16,16,14,1,1,30},{31,4,4,4,4,4,4},{17,17,17,17,17,17,14},
 {17,17,17,17,17,10,4},{17,17,17,21,21,21,10},{17,17,10,4,10,17,17},
 {17,17,10,4,4,4,4},{31,1,2,4,8,16,31},{14,17,19,21,25,17,14},
 {4,12,4,4,4,4,14},{14,17,1,2,4,8,31},{30,1,1,14,1,1,30},
 {2,6,10,18,31,2,2},{31,16,16,30,1,1,30},{14,16,16,30,17,17,14},
 {31,1,2,4,8,8,8},{14,17,17,14,17,17,14},{14,17,17,15,1,1,14},
 {0,4,4,0,4,4,0},{0,0,0,0,0,4,4},{1,2,2,4,8,8,16},
 {0,0,0,31,0,0,0},{0,0,0,0,0,0,0},
 {0,0,0,0,0,4,8},{4,4,8,0,0,0,0},{0,4,0,0,4,4,8},
 {4,4,4,4,4,0,4},{14,17,1,2,4,0,4},{2,4,8,8,8,4,2},
 {8,4,2,2,2,4,8},{4,15,20,14,5,30,4},{10,10,0,0,0,0,0},
 {0,0,14,1,15,17,15},{16,16,30,17,17,17,30},{0,0,14,16,16,17,14},
 {1,1,15,17,17,17,15},{0,0,14,17,31,16,14},{6,8,28,8,8,8,8},
 {0,0,15,17,15,1,14},{16,16,30,17,17,17,17},{4,0,12,4,4,4,14},
 {2,0,6,2,2,18,12},{16,16,18,20,24,20,18},{12,4,4,4,4,4,14},
 {0,0,26,21,21,21,21},{0,0,30,17,17,17,17},{0,0,14,17,17,17,14},
 {0,0,30,17,30,16,16},{0,0,15,17,15,1,1},{0,0,22,25,16,16,16},
 {0,0,15,16,14,1,30},{8,8,28,8,8,9,6},{0,0,17,17,17,19,13},
 {0,0,17,17,17,10,4},{0,0,17,17,21,21,10},{0,0,17,10,4,10,17},
 {0,0,17,17,15,1,14},{0,0,31,2,4,8,31}
};
static void pixel(uint32_t *f, int x, int y, uint32_t color)
{
    if (x >= 0 && x < 320 && y >= 0 && y < 200) f[y * 320 + x] = color;
}
static void text(uint32_t *f, int x, int y, const char *str, unsigned color)
{
    for (; *str; ++str, x += 6) {
        const char *p = strchr(alphabet, *str);
        if (!p) continue;
        size_t i = (size_t)(p - alphabet);
        for (int row = 0; row < 7; ++row)
            for (int col = 0; col < 5; ++col)
                if ((glyphs[i][row] >> (4 - col)) & 1) pixel(f, x + col, y + row, btp_palette[color]);
    }
}
static void rectangle(uint32_t *f, int x, int y, int w, int h, unsigned color)
{
    for (int row = y; row < y + h; ++row)
        for (int col = x; col < x + w; ++col) pixel(f, col, row, btp_palette[color]);
}
/* Independent fixed-column text layout; original glyphs/layout are approximate.
   Verified Hall/Katrina messages fit. Overflow is visible, never silently hidden. */
static int wrapped(uint32_t *f, int y, const uint8_t *bytes, size_t n, unsigned color)
{
    uint8_t clean[BTP_BLD_MAX+1]; size_t used = 0;
    if (n > BTP_BLD_MAX) { text(f,110,y,"INVALID TEXT BOUNDS",12); return y; }
    for (size_t i = 0; i < n; ++i) {
        if (bytes[i] == 6 && i+1 < n && (bytes[i+1] == 15 || bytes[i+1] == 14)) { ++i; continue; }
        clean[used++] = bytes[i];
    }
    bytes = clean; n = used;
    size_t at = 0;
    while (at < n && y <= 173) {
        char line[35]; size_t count = 0, start = at;
        while (at < n && bytes[at] != '\r' && count < 34) line[count++] = (char)bytes[at++];
        if (at < n && bytes[at] == '\r') ++at;
        else if (at < n && count == 34 && bytes[at] != ' ') {
            size_t space = count;
            while (space && line[space - 1] != ' ') --space;
            if (space) { count = space - 1; at = start + space; }
        }
        while (at < n && bytes[at] == ' ') ++at;
        line[count] = 0; text(f, 110, y, line, color); y += 9;
    }
    if (at < n) text(f, 110, 180, "TEXT OVERFLOW - UNSUPPORTED LAYOUT", 12);
    return y;
}
static const uint8_t *bank_literal(const BtpResources *r, unsigned id, size_t *n)
{
    const BtpDialogue *d = &r->dialogue;
    if (id >= BTP_TALK_STRINGS || d->length > BTP_TALK_MAX || d->offset[id] >= d->length ||
        d->size[id] >= d->length-d->offset[id] || d->bytes[d->offset[id]+d->size[id]]) return NULL;
    *n = d->size[id]; return d->bytes+d->offset[id];
}
static void bank_panel(const BtpResources *r, const BtpState *s, const uint8_t *body, size_t length, uint32_t *f)
{
    const BtpScriptState *v = &s->script; const BtpBankState *b = &s->bank;
    char value[16];
    if (v->has_accounts) {
        BtpTextSpan first = v->text[0], menu = v->text[1];
        (void)wrapped(f,9,r->comstar.bytes+first.offset,first.length,15);
        snprintf(value,sizeof value,"%u",s->credits); text(f,260,9,value,10);
        int y = 54; unsigned count = 0;
        for (unsigned i = 0; i < 3; ++i) if (s->investments[i]) {
            size_t n; const uint8_t *p = bank_literal(r,BTP_BANK_STR_COMPANY+i,&n);
            if (!p) return;
            (void)wrapped(f,y,p,n ? n-1 : 0,15);
            snprintf(value,sizeof value,"%u",s->investments[i]); text(f,260,y,value,10); y += 9; ++count;
        }
        if (!count) {
            size_t n; const uint8_t *p = bank_literal(r,BTP_BANK_STR_NONE,&n);
            if (!p) return;
            (void)wrapped(f,45,p,n,15);
        }
        const uint8_t *p = r->comstar.bytes+menu.offset;
        size_t at = 0; y = 123;
        for (unsigned i = 0; i < 4 && at < menu.length; ++i) {
            size_t end = at; while (end < menu.length && p[end] != '\r') ++end;
            if (i && i-1 == v->selected) rectangle(f,109,y-1,206,9,14);
            (void)wrapped(f,y,p+at,end-at,i && i-1 == v->selected ? 0u : 15u);
            at = end+1; y += 9;
        }
        return;
    }
    if (b->phase == BTP_BANK_MESSAGE && (b->outcome == BTP_BANK_NO_CASH || b->outcome == BTP_BANK_NO_STOCK)) {
        (void)wrapped(f,9,body,length,15);
    } else {
        int buy = v->native_action == 7; size_t header_length;
        const uint8_t *header = bank_literal(r,buy ? BTP_BANK_STR_BUY_MENU : BTP_BANK_STR_SELL_MENU,&header_length);
        if (!header) return;
        int y = wrapped(f,9,header,header_length && header[header_length-1] == '\r' ? header_length-1 : header_length,15);
        size_t prefix = header_length;
        for (unsigned i = 0; i < 3; ++i) {
            size_t n; const uint8_t *p = bank_literal(r,BTP_BANK_STR_COMPANY+i,&n);
            if (!p) return;
            int selected = b->phase == BTP_BANK_MENU && s->script.choices[7] == i;
            if (selected) rectangle(f,109,y-1,206,9,14);
            (void)wrapped(f,y,p,n ? n-1 : 0,selected ? 0u : 15u); y += 9; prefix += n;
        }
        if (b->phase != BTP_BANK_MENU && prefix <= length) {
            uint8_t details[BTP_BLD_MAX+1]; size_t out = 0, label_size;
            const uint8_t *label = bank_literal(r,buy ? BTP_BANK_STR_CASH_ACCOUNT : BTP_BANK_STR_STOCK_ACCOUNT,&label_size);
            if (!label) return;
            /* The original places the available-balance label at row 23. */
            for (size_t at = prefix; at < length;) {
                if (label_size <= length-at && !memcmp(body+at,label,label_size)) {
                    at += label_size;
                    snprintf(value,sizeof value,"%u",b->available);
                    size_t digits = strlen(value);
                    if (digits <= length-at && !memcmp(body+at,value,digits)) at += digits;
                    text(f,110,169,(const char *)label,15); text(f,260,169,value,10);
                } else details[out++] = body[at++];
            }
            (void)wrapped(f,y,details,out,15);
        }
    }
    text(f,110,185,b->phase == BTP_BANK_AMOUNT ? "DIGITS / BACKSPACE / ENTER" :
        b->phase == BTP_BANK_MENU ? "ARROWS / ENTER" : "ENTER / SPACE TO CONTINUE",14);
}
static void school_panel(const BtpResources *r, const BtpState *s, uint32_t *f)
{
    uint8_t body[BTP_BLD_MAX+1];
    if (!btp_script_text(&s->script,&r->citadel,body,sizeof body)) {
        text(f,110,12,"INVALID CLASS TEXT",12); return;
    }
    size_t n = strlen((char *)body), header = n, course = n;
    for (size_t i = 0; i+1 < n; ++i) if (body[i] == 6) {
        if (body[i+1] == 14) header = i;
        if (body[i+1] == 15) { course = i+2; break; }
    }
    if (header >= course || course >= n) { text(f,110,12,"INVALID CLASS LAYOUT",12); return; }
    int y = wrapped(f,9,body,header,15);
    y = wrapped(f,y,body+header,course-header,14);
    size_t at = course;
    for (unsigned i = 0; i < 4; ++i) {
        size_t end = at; while (end < n && body[end] != '\r') ++end;
        if (end-at >= 35 || at >= n || (i < 3 && end == n) || (i == 3 && end != n)) {
            text(f,110,180,"INVALID CLASS LAYOUT",12); return;
        }
        char option[35]; memcpy(option,body+at,end-at); option[end-at] = 0;
        unsigned color = i == s->script.selected ? 0u : 15u;
        if (i == s->script.selected) rectangle(f,109,y-1,206,9,14);
        text(f,110,y,option,color);
        if (i < 3) {
            char price[8]; snprintf(price,sizeof price,"%u",btp_school_price(s->skills[i]));
            text(f,280,y,price,color);
        }
        at = end+1; y += 9;
    }
}
static void story_panel(const BtpResources *r, const BtpState *s, uint32_t *f)
{
    rectangle(f, 104, 0, 216, 200, 7); rectangle(f, 108, 4, 208, 192, 0);
    if (s->mode == BTP_SCRIPT_FAULT) {
        text(f, 110, 12, "UNSUPPORTED STORY ACTION", 12);
        text(f, 110, 30, btp_script_error_name(s->script.error), 15);
        char line[40];
        snprintf(line, sizeof line, "PC %04X OPCODE %02X", s->script.fault_pc, s->script.last_opcode);
        text(f, 110, 48, line, 14); text(f, 110, 84, "BACKSPACE RETURNS TO BUILDING MENU", 7);
        return;
    }
    const BtpScriptState *v = &s->script;
    uint8_t bytes[BTP_BLD_MAX + 1];
    size_t length;
    if (!btp_game_text(s, r, bytes, sizeof bytes, &length)) {
        text(f, 110, 12, "INVALID TEXT BOUNDS", 12); return;
    }
    if (s->bank.phase || v->has_accounts) { bank_panel(r,s,bytes,length,f); return; }
    if (s->school.phase == BTP_SCHOOL_PRICES) { school_panel(r,s,f); return; }
    if (v->status == BTP_SCRIPT_MENU || s->talk.phase == BTP_TALK_MENU) {
        if (!s->talk.phase && !btp_script_menu_text(v,btp_building_bld(r,s->entry_slot),bytes,sizeof bytes,&length)) {
            text(f,110,12,"INVALID MENU TEXT",12); return;
        }
        unsigned count = s->talk.phase == BTP_TALK_MENU ? (unsigned)s->talk.count+1 : btp_menu_count(v->menu_id);
        unsigned selected = s->talk.phase == BTP_TALK_MENU ? s->talk.selected : v->selected;
        size_t starts[9]; unsigned found = 0;
        if (count > 9) { text(f, 110, 12, "INVALID MENU COUNT", 12); return; }
        for (size_t i = length; i && found < count; --i)
            if (bytes[i - 1] == '\r') starts[count-1-found++] = i;
        if (found != count) { text(f, 110, 12, "UNSUPPORTED MENU TEXT LAYOUT", 12); return; }
        int y = wrapped(f, 9, bytes, starts[0], 15);
        for (unsigned i = 0; i < count; ++i) {
            size_t end = i+1 == count ? length : starts[i + 1] - 1;
            char option[35]; size_t n = end - starts[i];
            if (n >= sizeof option || y > 177) {
                text(f, 110, 180, "UNSUPPORTED MENU TEXT LAYOUT", 12); return;
            }
            memcpy(option, bytes + starts[i], n); option[n] = 0;
            if (i == selected) rectangle(f, 109, y - 1, 206, 9, 14);
            text(f, 110, y, option, i == selected ? 0u : 15u); y += 9;
        }
    } else {
        int y = wrapped(f, 9, bytes, length, 15);
        if (v->status == BTP_SCRIPT_CONFIRM) {
            if (y > 177) y = 177;
            text(f,110,y,"Yes",v->confirm_selected == 0 ? 14u : 7u);
            text(f,140,y,"No",v->confirm_selected == 1 ? 14u : 7u);
        } else text(f, 110, 185, "ENTER / SPACE TO CONTINUE", 14);
    }
}

void btp_render(const BtpResources *r, const BtpState *s, int debug, uint32_t f[BTP_PIXELS])
{
    if (s->mode == BTP_QUIZ && s->quiz.phase == BTP_QUIZ_QUESTION) {
        for (unsigned i = 0; i < BTP_PIXELS; ++i) f[i] = btp_palette[terrain_palette[r->quiz_diagram.pixels[i]&15u]];
        rectangle(f,0,0,128,200,0);
        text(f,3,2,"Identify this",15); text(f,3,10,"'Mech part:",15);
        for (unsigned i = 0; i < BTP_QUIZ_PARTS; ++i) {
            size_t n; const uint8_t *p = bank_literal(r,58u+i,&n);
            if (!p || n > 20) continue;
            char label[21]; memcpy(label,p,n); label[n] = 0;
            int y = 28+(int)i*8;
            if (s->quiz.selected == i) rectangle(f,0,y-1,127,8,14);
            text(f,3,y,label,s->quiz.selected == i ? 0u : 15u);
        }
        int x = btp_quiz_x[s->quiz.point]-3, y = btp_quiz_y[s->quiz.point]-3;
        rectangle(f,x,y,9,1,15); rectangle(f,x,y+8,9,1,15);
        rectangle(f,x,y,1,9,15); rectangle(f,x+8,y,1,9,15);
        return;
    }
    int camera_x = (int)s->x_half * 8 - 96, camera_y = (int)s->y_half * 8 - 96;
    for (int y = 0; y < 200; ++y)
        for (int x = 0; x < 320; ++x) {
            uint32_t color = btp_palette[0];
            if (x >= 104) {
                int wx = camera_x + x - 104, wy = camera_y + y;
                if (wx >= 0 && wy >= 0 && wx < r->map.width * 16 && wy < r->map.height * 16) {
                    unsigned tile = btp_map_tile(&r->map, wx / 16, wy / 16);
                    if (s->mission.phase && wx/16 == 61 && wy/16 == 61) tile = 0;
                    if (tile < 250) {
                        unsigned index = tile * 256 + (unsigned)(wy % 16) * 16 + (unsigned)(wx % 16);
                        unsigned value = r->tiles.pixels[index] & 15;
                        color = btp_palette[terrain_palette[value]];
                        if (debug && tile >= s->gate && (wx % 16 == 0 || wy % 16 == 0))
                            color = btp_palette[13];
                    }
                }
            } else if (x < 3 || x >= 100 || y < 3 || y >= 197 || y == 100 || y == 101)
                color = btp_palette[7];
            f[y * 320 + x] = color;
        }
    if (s->mission.phase) (void)btp_draw_sprite(&r->sprites,
        (s->story_flags[2] ? 146u : 0u)+s->mission.walk,200,64,btp_mission_terrain(s,&r->map),104,f);
    else (void)btp_draw_sprite(&r->sprites,166u+s->player_walk,208,96,
        hidden_rows(&r->map,s->x_half,s->y_half),104,f);
    /* Original 051B draws the party before the eight outdoor NPC slots. */
    if ((s->mode == BTP_EXPLORE || s->mode == BTP_MISSION) && s->npc.enabled == 2) for (unsigned i = 0; i < 8; ++i) {
        const BtpNpc *n = &s->npc.actor[i];
        if (!n->x) continue;
        unsigned x = n->x & 127u, y = n->y & 127u;
        int nx = 208+((int)x-s->x_half)*8, ny = 96+((int)y-s->y_half)*8;
        (void)btp_draw_sprite(&r->sprites,270u+s->npc_walk[i],nx,ny,
            hidden_rows(&r->map,x,y),104,f);
    }
    text(f, 8, 9, "BtechPort M2j", 15);
    char place[17]; memcpy(place,r->map.places[s->entry_slot],16); place[16] = 0;
    text(f, 8, 24, s->mode != BTP_EXPLORE ? place : "Training", 14);
    text(f, 8, 36, s->conversation_checkpoint ? "TALK CHECKPOINT" :
        s->mode >= BTP_BUILDING ? "DIALOGUE" : "SCHOOL", 14);
    text(f, 8, 57, s->mode == BTP_EXPLORE || s->mode == BTP_MISSION ? "ARROWS MOVE" : "ARROWS SELECT", 7);
    text(f, 8, 69, "F3 DEBUG", 7);
    text(f, 8, 81, "R RESTART", 7);
    char cash[32]; snprintf(cash,sizeof cash,"C-bills %u",s->credits); text(f,8,92,cash,10);
    text(f, 8, 111, "MAP 1", 15);
    char line[64];
    snprintf(line, sizeof line, "X %u.%u", s->x_half / 2, (s->x_half % 2) * 5);
    text(f, 8, 125, line, 15);
    snprintf(line, sizeof line, "Y %u.%u", s->y_half / 2, (s->y_half % 2) * 5);
    text(f, 8, 137, line, 15);
    text(f,8,189,"F5 SAVE F9 LOAD",7);
    if (s->blocked) text(f, 8, 151, s->blocked == BTP_EDGE ? "MAP EDGE" : "BLOCKED", 12);
    if (s->npc.fault) { text(f,8,151,"NPC DATA ERROR",12); return; }
    if (s->mode == BTP_MISSION) {
        text(f,8,151,s->story_flags[2] == 0 ? "Locust" : s->story_flags[2] == 1 ? "Wasp" : "Chameleon",14);
        if (s->mission.phase == BTP_MISSION_WARNING || s->mission.phase == BTP_MISSION_CORNER) {
            uint8_t message[256]; size_t n;
            rectangle(f,104,72,216,58,7); rectangle(f,108,76,208,50,0);
            if (btp_game_text(s,r,message,sizeof message,&n)) (void)wrapped(f,79,message,n,15);
        }
        if (debug) { snprintf(line,sizeof line,"TIME %u",s->mission.elapsed); text(f,8,166,line,14); }
    } else if (s->mode == BTP_BUILDING || s->mode == BTP_SCRIPT_FAULT || s->mode == BTP_QUIZ) {
        text(f, 8, 151, "ENTER SPACE", 14);
        if (debug) {
            snprintf(line, sizeof line, "PC %04X", s->script.pc); text(f, 8, 166, line, 14);
            snprintf(line, sizeof line, "OP %02X", s->script.last_opcode); text(f, 8, 178, line, 14);
            if (s->script.animation_kind) { snprintf(line,sizeof line,"ANM %u",s->script.animation_kind); text(f,8,36,line,14); }
        }
        story_panel(r, s, f);
    } else if (s->mode == BTP_ENTRY) {
        rectangle(f, 104, 73, 216, 55, 7); rectangle(f, 108, 77, 208, 46, 0);
        char question[40]; snprintf(question,sizeof question,"Enter %s?",place);
        text(f, 110, 81, question, 15);
        text(f, 110, 99, "YES", s->entry_selected == 0 ? 14u : 7u);
        text(f, 140, 99, "NO", s->entry_selected == 1 ? 14u : 7u);
        text(f, 110, 113, "ENTER SELECTS - BACKSPACE DECLINES", 7);
    } else if (btp_entrance(s, &r->map) == 5) {
        text(f, 8, 166, "INTERIOR", 14); text(f, 8, 178, "UNAVAILABLE", 14);
    } else if (debug) {
        snprintf(line, sizeof line, "GATE %u", s->gate); text(f, 8, 166, line, 14);
        snprintf(line, sizeof line, "TICK %u", s->tick); text(f, 8, 178, line, 14);
    }
}

void btp_sprite_preview(const BtpResources *r, unsigned tick, uint32_t f[BTP_PIXELS])
{
    for (unsigned i = 0; i < BTP_PIXELS; ++i) f[i] = btp_palette[2];
    text(f,8,5,"Original sprite preview",15);
    text(f,8,17,"All walking frames - Esc exits",15);
    const unsigned bases[] = {0,146,166,270};
    const char *labels[] = {"Locust", "Commando", "Jason", "Cadets"};
    for (unsigned row = 0; row < 4; ++row) {
        int y = row < 2 ? 30+(int)row*56 : 144+(int)(row-2)*24;
        text(f,8,y,labels[row],15);
        for (unsigned n = 0; n < 16; ++n) {
            int x = 72+(int)(n%8)*30;
            (void)btp_draw_sprite(&r->sprites,bases[row]+n,x,y+(int)(n/8)*(row < 2 ? 26 : 10),0,0,f);
        }
    }
    /* The separate large preview cycles four raw frames per facing. */
    (void)btp_draw_sprite(&r->sprites,(tick/6)%16,12,58,0,0,f);
    (void)btp_draw_sprite(&r->sprites,146+(tick/6)%16,12,98,0,0,f);
}

int btp_write_ppm(const char *path, const uint32_t f[BTP_PIXELS])
{
    FILE *out = fopen(path, "wb");
    if (!out) return 0;
    int ok = fprintf(out, "P6\n320 200\n255\n") > 0;
    for (unsigned i = 0; i < BTP_PIXELS && ok; ++i) {
        uint8_t rgb[] = {(uint8_t)(f[i] >> 16), (uint8_t)(f[i] >> 8), (uint8_t)f[i]};
        ok = fwrite(rgb, 1, 3, out) == 3;
    }
    if (fclose(out)) ok = 0;
    return ok;
}

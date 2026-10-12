#include "frontend/pixels.h"
#include "core/animation.h"
#include "core/world.h"
#include "core/bank.h"
#include "core/school.h"
#include "core/training.h"
#include "core/combat.h"
#include "core/effects.h"
#include "data/sprites.h"
#include "core/party.h"
#include "core/service.h"
#include "core/menu.h"
#include "data/anm.h"
#include <stdio.h>
#include <stdlib.h>
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
static void text(const BtpResources *r, uint32_t *f, int x, int y, const char *str, unsigned color)
{
    if (r->dialogue.length && x == 110) x = 112;
    if (r->dialogue.length && x == 140) x = 144;
    for (; *str; ++str, x += r->dialogue.length ? 8 : 6) {
        if (r->dialogue.length) {
            const uint8_t *glyph = r->dialogue.font+8u*(uint8_t)*str;
            for (int row = 0; row < 8; ++row) for (int col = 0; col < 8; ++col)
                if (glyph[row] & (128u>>col)) pixel(f,x+col,y+row,btp_palette[color]);
            continue;
        }
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
/* BTBORDER.CMP: nine 8x8 cells across its first eight scanlines.
   Original VGA snapshots establish the 13-column left frame, row-12 divider,
   and 27-column dialogue frame. The map viewport itself is unframed. */
static void border_panel(const BtpResources *r, uint32_t *f, int x, int y, int w, int h, int split)
{
    if (r->border.format != 1) return;
    int columns = w/8, rows = h/8;
    for (int row = 0; row < rows; ++row) for (int col = 0; col < columns; ++col) {
        unsigned tile;
        if (!row) tile = !col ? 0u : col == columns-1 ? 1u : 4u;
        else if (row == rows-1) tile = !col ? 6u : col == columns-1 ? 7u : 4u;
        else if (split && row == 12) tile = !col ? 2u : col == columns-1 ? 3u : 4u;
        else if (!col || col == columns-1) tile = 5;
        else continue;
        for (int dy = 0; dy < 8; ++dy) for (int dx = 0; dx < 8; ++dx)
            pixel(f,x+8*col+dx,y+8*row+dy,btp_palette[r->border.pixels[320u*(unsigned)dy+tile*8u+(unsigned)dx]&15u]);
    }
}
/* Original glyphs, with independent word wrapping. Layout remains approximate;
   oversized messages produce a visible diagnostic. */
static int wrapped_at(const BtpResources *r, uint32_t *f, int x, int y,unsigned columns, const uint8_t *bytes, size_t n, unsigned color)
{
    uint8_t clean[BTP_BLD_MAX+1]; size_t used = 0;
    if (n > BTP_BLD_MAX) { text(r,f,110,y,"INVALID TEXT BOUNDS",12); return y; }
    for (size_t i = 0; i < n; ++i) {
        if (bytes[i] == 6 && i+1 < n && (bytes[i+1] == 15 || bytes[i+1] == 14)) { ++i; continue; }
        clean[used++] = bytes[i];
    }
    bytes = clean; n = used;
    size_t at = 0;
    while (at < n && y <= 184) {
        char line[35]; size_t count = 0, start = at;
        while (at < n && bytes[at] != '\r' && count < columns) line[count++] = (char)bytes[at++];
        if (at < n && bytes[at] == '\r') ++at;
        else if (at < n && count == columns && bytes[at] != ' ') {
            size_t space = count;
            while (space && line[space - 1] != ' ') --space;
            if (space) { count = space - 1; at = start + space; }
        }
        while (at < n && bytes[at] == ' ') ++at;
        line[count] = 0; text(r,f,x,y,line,color); y += r->dialogue.length ? 8 : 9;
    }
    if (at < n) text(r,f, 112, 180, "Text layout overflow", 12);
    return y;
}
static int wrapped(const BtpResources *r,uint32_t *f,int y,const uint8_t *bytes,size_t n,unsigned color)
{
    return wrapped_at(r,f,r->dialogue.length ? 112 : 110,y,r->dialogue.length ? 25u : 34u,bytes,n,color);
}
static const uint8_t *bank_literal(const BtpResources *r, unsigned id, size_t *n)
{
    const BtpDialogue *d = &r->dialogue;
    if (id >= BTP_TALK_STRINGS || d->length > BTP_TALK_MAX || d->offset[id] >= d->length ||
        d->size[id] >= d->length-d->offset[id] || d->bytes[d->offset[id]+d->size[id]]) return NULL;
    *n = d->size[id]; return d->bytes+d->offset[id];
}
static void mech_blocks(uint32_t *f,int column,int row,unsigned count,int working)
{
    /* 05AB:1858: five indicators per row, green before the working count,
       red afterwards. Each indicator is an inclusive three-pixel square. */
    for (unsigned i=0;i<count;++i)
        rectangle(f,8*(column+(int)(i%5u))+2,8*(row+(int)(i/5u))+3,3,3,
            (int)i<working ? 2u : 4u);
}
static void mech_bar(uint32_t *f,int x,int bottom,unsigned working,unsigned structure,unsigned color)
{
    /* 05AB:164C: a six-pixel-wide structure segment beneath the armour.
       The original displays the stored point counts directly, one pixel each. */
    if (structure) { rectangle(f,x,bottom-(int)structure+1,6,(int)structure,color);bottom-=(int)structure; }
    if (working) rectangle(f,x,bottom-(int)working+1,6,(int)working,2);
}
void btp_mech_screen(const BtpResources *r,const uint8_t m[125],const char *pilot,
    const char *rider,unsigned heat,unsigned tick,uint32_t f[BTP_PIXELS])
{
    for (unsigned i=0;i<BTP_PIXELS;++i) f[i]=btp_palette[terrain_palette[r->quiz_diagram.pixels[i]&15u]];
    rectangle(f,0,0,128,200,0);
    size_t n;const uint8_t *label=bank_literal(r,108,&n);
    if (label) (void)wrapped_at(r,f,0,0,16,label,n,15);
    char name[9],weight[4];memcpy(name,m,8);name[8]=0;snprintf(weight,sizeof weight,"%u",m[16]);
    text(r,f,48,0,name,14);text(r,f,48,8,weight,14);
    if (pilot) {
        text(r,f,48,16,pilot,14);
        label=bank_literal(r,114,&n);text(r,f,48,24,rider ? rider : label ? (const char *)label : "None",14);
    }
    mech_blocks(f,37,0,3,3-(int)m[117]);mech_blocks(f,37,1,2,2-(int)m[118]);mech_blocks(f,37,2,2,2-(int)m[119]);
    unsigned sinks=m[38];for (unsigned i=51;i<=85;++i) sinks+=m[i]==34;
    mech_blocks(f,34,6,10,(int)sinks);
    static const char *const locations[]={"LA","LT","RA","RT","LL","RL","CT","H"};
    int row=6;
    for (unsigned i=51;i<=85;++i) {
        unsigned component=m[i]&127u;if (component<16 || component>32) continue;
        unsigned part=i>=85 ? 7u : i>=83 ? 6u : i>=81 ? 5u : i>=79 ? 4u : i>=72 ? 3u : i>=65 ? 2u : i>=58 ? 1u : 0u;
        char weapon[12];memcpy(weapon,r->combat.weapons[component-1],11);weapon[11]=0;
        unsigned color=m[i]&128u ? 8u : 14u;
        text(r,f,0,8*row,weapon,color);text(r,f,88,8*row,locations[part],color);++row;
    }
    label=bank_literal(r,109,&n);if (label) (void)wrapped_at(r,f,0,152,16,label,n,15);
    label=bank_literal(r,110,&n);if (label) (void)wrapped_at(r,f,0,160,16,label,n,15);
    for (unsigned i=0;i<4;++i) {
        unsigned value=m[36+(i&1u)],maximum=m[105+(i&1u)];
        value=i<2 ? value&15u : value&240u;maximum=i<2 ? 15u : maximum&240u;
        unsigned status=value==maximum ? 111u : value ? 112u : 113u;
        label=bank_literal(r,status,&n);if (label) text(r,f,80,160+8*(int)i,(const char *)label,status==113 ? 8u : 15u);
    }
    /* Original DS:1306/131C/1332, read by 05AB:210F..2179. */
    static const uint8_t structure[]={28,29,30,31,32,33,34,35,0,0,0};
    static const uint16_t x[]={248,208,224,192,192,136,176,160,272,288,304};
    static const uint8_t y[]={87,55,151,31,71,87,55,151,135,143,135};
    for (unsigned i=0;i<11;++i) mech_bar(f,x[i],y[i],m[17+i],structure[i] ? m[structure[i]] : 0u,4);
    if (heat>30) heat=30;
    mech_bar(f,256,183,30u-heat,heat,(tick/(11u-heat/6u))&1u ? 4u : 14u);
}
static void bank_panel(const BtpResources *r, const BtpState *s, const uint8_t *body, size_t length, uint32_t *f)
{
    const BtpScriptState *v = &s->script; const BtpBankState *b = &s->bank;
    char value[16];
    if (v->has_accounts) {
        BtpTextSpan first = v->text[0], menu = v->text[1];
        (void)wrapped(r,f,9,r->comstar.bytes+first.offset,first.length,15);
        snprintf(value,sizeof value,"%u",s->credits); text(r,f,260,9,value,10);
        int y = 54; unsigned count = 0;
        for (unsigned i = 0; i < 3; ++i) if (s->investments[i]) {
            size_t n; const uint8_t *p = bank_literal(r,BTP_BANK_STR_COMPANY+i,&n);
            if (!p) return;
            (void)wrapped(r,f,y,p,n ? n-1 : 0,15);
            snprintf(value,sizeof value,"%u",s->investments[i]); text(r,f,260,y,value,10); y += 9; ++count;
        }
        if (!count) {
            size_t n; const uint8_t *p = bank_literal(r,BTP_BANK_STR_NONE,&n);
            if (!p) return;
            (void)wrapped(r,f,45,p,n,15);
        }
        const uint8_t *p = r->comstar.bytes+menu.offset;
        size_t at = 0; y = 123;
        for (unsigned i = 0; i < 4 && at < menu.length; ++i) {
            size_t end = at; while (end < menu.length && p[end] != '\r') ++end;
            if (i && i-1 == v->selected) rectangle(f,109,y-1,206,9,14);
            (void)wrapped(r,f,y,p+at,end-at,i && i-1 == v->selected ? 0u : 15u);
            at = end+1; y += 9;
        }
        return;
    }
    if (b->phase == BTP_BANK_MESSAGE && (b->outcome == BTP_BANK_NO_CASH || b->outcome == BTP_BANK_NO_STOCK)) {
        (void)wrapped(r,f,9,body,length,15);
    } else {
        int buy = v->native_action == 7; size_t header_length;
        const uint8_t *header = bank_literal(r,buy ? BTP_BANK_STR_BUY_MENU : BTP_BANK_STR_SELL_MENU,&header_length);
        if (!header) return;
        int y = wrapped(r,f,9,header,header_length && header[header_length-1] == '\r' ? header_length-1 : header_length,15);
        size_t prefix = header_length;
        for (unsigned i = 0; i < 3; ++i) {
            size_t n; const uint8_t *p = bank_literal(r,BTP_BANK_STR_COMPANY+i,&n);
            if (!p) return;
            int selected = b->phase == BTP_BANK_MENU && s->script.choices[7] == i;
            if (selected) rectangle(f,109,y-1,206,9,14);
            (void)wrapped(r,f,y,p,n ? n-1 : 0,selected ? 0u : 15u); y += 9; prefix += n;
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
                    text(r,f,110,169,(const char *)label,15); text(r,f,260,169,value,10);
                } else details[out++] = body[at++];
            }
            (void)wrapped(r,f,y,details,out,15);
        }
    }
    text(r,f,112,184,b->phase == BTP_BANK_AMOUNT ? "Digits / Enter" :
        b->phase == BTP_BANK_MENU ? "Arrows / Enter" : "Enter / Space",14);
}
static void school_panel(const BtpResources *r, const BtpState *s, uint32_t *f)
{
    uint8_t body[BTP_BLD_MAX+1];
    if (!btp_script_text(&s->script,&r->citadel,body,sizeof body)) {
        text(r,f,110,12,"INVALID CLASS TEXT",12); return;
    }
    size_t n = strlen((char *)body), header = n, course = n;
    for (size_t i = 0; i+1 < n; ++i) if (body[i] == 6) {
        if (body[i+1] == 14) header = i;
        if (body[i+1] == 15) { course = i+2; break; }
    }
    if (header >= course || course >= n) { text(r,f,110,12,"INVALID CLASS LAYOUT",12); return; }
    int y = wrapped(r,f,9,body,header,15);
    y = wrapped(r,f,y,body+header,course-header,14);
    size_t at = course;
    for (unsigned i = 0; i < 4; ++i) {
        size_t end = at; while (end < n && body[end] != '\r') ++end;
        if (end-at >= 35 || at >= n || (i < 3 && end == n) || (i == 3 && end != n)) {
            text(r,f,110,180,"INVALID CLASS LAYOUT",12); return;
        }
        char option[35]; memcpy(option,body+at,end-at); option[end-at] = 0;
        unsigned color = i == s->script.selected ? 0u : 15u;
        if (i == s->script.selected) rectangle(f,109,y-1,206,9,14);
        text(r,f,110,y,option,color);
        if (i < 3) {
            char price[8]; snprintf(price,sizeof price,"%u",btp_school_price(s->skills[i]));
            text(r,f,280,y,price,color);
        }
        at = end+1; y += 9;
    }
}
static void combat_route(const BtpResources *r, const BtpState *s, int cx, int cy, uint32_t *f)
{
    const BtpCombatState *c=&s->combat;
    BtpMap map;btp_combat_map(r,s,&map);
    int8_t steps[12][2];unsigned first=0;
    int selecting=c->phase==BTP_COMBAT_MOVE;
    if (!selecting && !c->goal_active) return;
    int tx=selecting && !c->goal_active ? c->cursor_x : c->goal_x;
    int ty=selecting && !c->goal_active ? c->cursor_y : c->goal_y;
    if (c->phase==BTP_COMBAT_ROUND) { memcpy(steps,c->path[c->active_unit],sizeof steps);first=c->path_index[c->active_unit]; }
    else if (c->goal_active) btp_combat_route(&map,s->gate,c,steps);
    else btp_combat_plan(&map,s->gate,&c->unit[c->active_unit],&c->unit[1],tx,ty,
        selecting ? c->selected : c->movement,0,steps);
    /* 103B:18D2..18FB draws these original font glyphs at each planned step.
       Preview uses exactly the movement planner; resolving uses the saved path. */
    static const uint8_t arrows[3][3]={{8,1,2},{7,0,3},{6,5,4}};
    int x=c->unit[c->active_unit].x, y=c->unit[c->active_unit].y;
    for (unsigned i=first;i<12;++i) {
        int mx=steps[i][0],my=steps[i][1];
        if (mx==2 || my==2 || (!mx && !my)) break;
        x+=mx;y+=my;
        int px=208+(x-cx)*8, py=72+(y+2-cy)*8;
        if (px>=104 && px<=312 && py>=0 && py<=192) {
            char arrow[2]={(char)arrows[my+1][mx+1],0};text(r,f,px,py,arrow,15);
        }
    }
    if (c->goal_active) {
        for (unsigned i=0;i<=c->waypoint_count;++i) {
            int wx=i ? c->waypoint_x[i-1] : c->goal_x,wy=i ? c->waypoint_y[i-1] : c->goal_y;
            int px=200+(wx-cx)*8,py=64+(wy+2-cy)*8;unsigned color=i ? 7 : 14;
            rectangle(f,px,py,24,1,color);rectangle(f,px,py+23,24,1,color);
            rectangle(f,px,py,1,24,color);rectangle(f,px+23,py,1,24,color);
        }
    }
}
static void combat_flash(const BtpResources *r, const BtpState *s, int cx, int cy, uint32_t *f)
{
    const BtpCombatState *c=&s->combat;
    if (!c->graphics || !s->effects.count || s->effects.stage<BTP_EFFECT_ATTACK || c->phase!=BTP_COMBAT_ROUND) return;
    const BtpCombatEffect *e=&s->effects.shots[0];unsigned frame=s->effects.age/2u;
    const uint8_t *pose=r->combat.poses[e->group][e->direction];unsigned count=pose[0];
    int x=200+((int)e->x-cx)*8,y=64+((int)e->y+2-cy)*8;
    int tx=200+((int)e->tx-cx)*8,ty=64+((int)e->ty+2-cy)*8;
    if (frame<count) {
        (void)btp_draw_sprite(&r->sprites,e->base+pose[1+frame],x,y,0,104,f);
        /* DS:2E3C is the personal hit program. Adding it to the 146-frame
           mech family selects Jason's human sprites (178..181). Mechs keep
           their current pose under the separately drawn impact. */
        if (e->hit && c->unit[e->target].infantry) (void)btp_draw_sprite(&r->sprites,e->target_base+r->combat.reaction[frame&3u],tx,ty,0,104,f);
        /* The original poses, projectile artwork and impact order are data
           driven. Beam interpolation and native cadence remain approximate. */
        if (e->weapon!=32 && frame+1==count) {
            int ax=x+(e->base==254 ? 4 : 12),ay=y+12,bx=tx+12,by=ty+12;
            int dx=bx-ax,dy=by-ay,steps=abs(dx)>abs(dy) ? abs(dx) : abs(dy);
            if ((e->weapon>=15 && e->weapon<=18) || e->weapon==12 || e->weapon==13) {
                for (int i=0;i<=steps;++i) {
                    int px=ax+(steps ? dx*i/steps : 0),py=ay+(steps ? dy*i/steps : 0);
                    if (px>=104) pixel(f,px,py,btp_palette[e->actor ? 5 : 12]);
                }
            } else {
                (void)btp_draw_sprite(&r->sprites,130+2u*e->direction+(s->effects.age&1u),
                    (ax+bx)/2,(ay+by)/2,0,104,f);
            }
        }
    } else if (e->hit && e->weapon>=7 && frame<count+3) {
        (void)btp_draw_sprite(&r->sprites,250u+r->combat.impact[frame-count],tx+4,ty+6,0,104,f);
    }
}
static int left_message(const BtpResources *r,uint32_t *f,const uint8_t *message,size_t n)
{
    size_t at=0;int y=104;
    while (at<n && y<192) {
        size_t end=at;while (end<n && end-at<11 && message[end]!=13) ++end;
        if (end<n && message[end]!=13 && message[end]!=' ') {
            size_t space=end;while (space>at && message[space]!=' ') --space;
            if (space>at) end=space;
        }
        char row[12];memcpy(row,message+at,end-at);row[end-at]=0;text(r,f,8,y,row,15);y+=8;
        at=end;while (at<n && (message[at]==' ' || message[at]==13)) ++at;
    }
    return y;
}
static void combat_panel(const BtpResources *r, const BtpState *s, uint32_t *f)
{
    const BtpCombatState *c=&s->combat;char line[40];
    static const char *commands[10]={"Walk","Run","Jump","Use Weapons","Kick","Computer","Scan","Next","Flee","Begin Fight"};
    rectangle(f,0,0,104,200,0);
    if (c->phase>=BTP_COMBAT_CONTROL && c->phase<=BTP_COMBAT_GRAPHICS) {
        unsigned id=87u+c->phase-BTP_COMBAT_CONTROL;
        const uint8_t *message=r->dialogue.bytes+r->dialogue.offset[id];
        size_t n=r->dialogue.size[id];
        if (c->phase==BTP_COMBAT_MESSAGES) n=16; /* Original prompt, before option lines. */
        int y=left_message(r,f,message,n);
        if (c->phase==BTP_COMBAT_MESSAGES) {
            static const char *const choices[]={"None","Brief","Verbose"};
            for (unsigned i=0;i<3;++i) {
                if (c->selected==i) rectangle(f,8,y+(int)i*8,88,8,14);
                text(r,f,8,y+(int)i*8,choices[i],c->selected==i ? 0u : 15u);
            }
        } else {
            if (c->selected==0) rectangle(f,8,y,24,8,14);else rectangle(f,40,y,16,8,14);
            text(r,f,8,y,"Yes",c->selected==0 ? 0u : 15u);text(r,f,40,y,"No",c->selected==1 ? 0u : 15u);
        }
        return;
    }
    const BtpCombatUnit *active=&c->unit[c->active_unit];
    text(r,f,8,8,c->friends ? active->infantry ? btp_party_name(&s->party,c->ids[c->active_unit]-4u) : "Owned 'Mech" : s->story_flags[2]==0 ? "Locust" : s->story_flags[2]==1 ? "Wasp" : "Chameleon",15);
    snprintf(line,sizeof line,"Heat %u",c->unit[c->active_unit].heat);text(r,f,8,24,line,14);
    snprintf(line,sizeof line,"Turn %u",c->round);text(r,f,8,40,line,15);
    if (c->goal_active) { snprintf(line,sizeof line,"Route %u",1u+c->waypoint_count);text(r,f,8,56,line,14); }
    for (unsigned i=0;i<10;++i) {
        int selected=c->phase==BTP_COMBAT_MENU && c->selected==i;
        if (selected) rectangle(f,8,104+(int)i*8,88,8,14);
        text(r,f,8,104+(int)i*8,commands[i],selected ? 0u : 15u);
    }
    if (c->phase==BTP_COMBAT_PICK) {
        rectangle(f,104,64,216,96,0);border_panel(r,f,104,64,216,96,0);
        text(r,f,112,72,"Choose a friendly unit:",15);
        unsigned id=c->ids[c->scan_unit];text(r,f,112,96,id>=4 ? btp_party_name(&s->party,id-4) : "Owned 'Mech",14);
        text(r,f,112,128,"Arrows / Enter / Backspace",7);
    } else if (c->phase==BTP_COMBAT_MOVE) {
        rectangle(f,200,64,24,1,14);rectangle(f,200,87,24,1,14);
        rectangle(f,200,64,1,24,14);rectangle(f,223,64,1,24,14);
        rectangle(f,104,168,216,32,0);border_panel(r,f,104,168,216,32,0);
        text(r,f,112,176,"Arrows: destination",15);text(r,f,112,184,"Enter: set route",14);
    } else if (c->phase==BTP_COMBAT_WEAPONS || c->phase==BTP_COMBAT_TARGET || c->phase==BTP_COMBAT_KICK) {
        rectangle(f,104,72,216,128,0);border_panel(r,f,104,72,216,128,0);
        if (c->phase==BTP_COMBAT_TARGET || c->phase==BTP_COMBAT_KICK) {
            snprintf(line,sizeof line,c->unit[c->target_unit].infantry ? c->friends ? "Enemy soldier %u" : "Labor robot %u" : "Enemy 'Mech",c->target_unit);
            text(r,f,112,80,c->phase==BTP_COMBAT_KICK ? "Choose the enemy to kick:" : "Choose a target:",15);
            text(r,f,112,88,line,15);
            static const char *choices[3]={"Target here","Next target","Cancel"};
            for (unsigned i=0;i<3;++i) {
                if (i==c->target_selected) rectangle(f,112,104+(int)i*8,200,8,14);
                text(r,f,112,104+(int)i*8,choices[i],i==c->target_selected ? 0u : 15u);
            }
        } else {
            text(r,f,112,80,"Weapon        Ammo Target",15);
            unsigned count=btp_combat_weapon_count(&c->unit[c->active_unit]);
            for (unsigned i=0;i<=count && i<12;++i) {
                if (i==count) snprintf(line,sizeof line,"Done");
                else {
                    unsigned w=btp_combat_weapon(&c->unit[c->active_unit],i);char name[12]={0},ammo[5];
                    if (w<33) memcpy(name,r->combat.weapons[w],10);else memcpy(name,"Unavailable",11);
                    if (c->unit[c->active_unit].record[39+i]==255) snprintf(ammo,sizeof ammo," --");
                    else snprintf(ammo,sizeof ammo,"%3u",c->unit[c->active_unit].record[39+i]);
                    unsigned target=btp_combat_target(c,c->orders[i]);char label[9]={0};
                    if (target<c->count) snprintf(label,sizeof label,c->unit[target].infantry ? "Robot %u" : "Locust",target);
                    snprintf(line,sizeof line,"%-11.11s %s %s",name,ammo,label);
                }
                if (i==c->weapon_selected) rectangle(f,112,88+(int)i*8,200,8,14);
                text(r,f,112,88+(int)i*8,line,i==c->weapon_selected ? 0u : 15u);
            }
        }
    } else if (c->phase==BTP_COMBAT_SCAN) {
        const BtpCombatUnit *u=&c->unit[c->scan_unit];
        rectangle(f,104,72,216,128,0);border_panel(r,f,104,72,216,128,0);
        text(r,f,112,80,u->infantry ? "Labor robot" : c->scan_unit ? "Enemy Locust" : "Jason's 'Mech",14);
        if (u->infantry) {
            char weapon[12]={0};memcpy(weapon,r->combat.weapons[u->record[11]],10);
            snprintf(line,sizeof line,"Health %u  Armor %u",u->record[15],u->record[14]);text(r,f,112,104,line,15);
            text(r,f,112,120,weapon,15);text(r,f,112,184,"Arrows: next Enter: close",14);return;
        }
        text(r,f,112,96,"Part       Armor Internal",15);
        static const char *parts[8]={"Left arm","Left torso","Left leg","Head","Center","Right arm","Right torso","Right leg"};
        for (unsigned i=0;i<8;++i) {
            snprintf(line,sizeof line,"%-11s %3u   %3u",parts[i],u->record[17+i],u->record[28+i]);
            text(r,f,112,104+(int)i*8,line,15);
        }
        text(r,f,112,184,"Arrows: next Enter: close",14);
    } else if (c->phase==BTP_COMBAT_REPLACE) {
        rectangle(f,104,64,216,96,0);border_panel(r,f,104,64,216,96,0);
        text(r,f,112,72,"Change movement mode?",15);
        text(r,f,112,80,"Clear the previous route?",15);
        for (unsigned i=0;i<2;++i) {
            if (c->target_selected==i) rectangle(f,112,104+(int)i*8,200,8,14);
            text(r,f,112,104+(int)i*8,i ? "No" : "Yes",c->target_selected==i ? 0u : 15u);
        }
    } else if (c->phase<=BTP_COMBAT_GRAPHICS || c->phase==BTP_COMBAT_NOTICE) {
        rectangle(f,104,64,216,96,0);border_panel(r,f,104,64,216,96,0);
        if (c->phase==BTP_COMBAT_NOTICE) {
            const char *message=c->notice==2 ? "No movement points for this order.\rEnter to return." :
                c->notice==3 ? "Damaged legs prevent kicking.\rEnter to return." :
                c->notice==4 ? "All twelve waypoints are assigned.\rEnter to return." :
                c->notice==5 ? "You cannot escape these Jenners!\rReach the southern exit." :
                "This command is outside the verified weapons-training slice.\rEnter to return.";
            (void)wrapped(r,f,72,(const uint8_t *)message,strlen(message),15);
        } else {
            text(r,f,112,72,c->phase==BTP_COMBAT_CONTROL ? "Computer control?" :
                c->phase==BTP_COMBAT_MESSAGES ? "Combat messages" : "Combat graphics?",15);
            unsigned count=c->phase==BTP_COMBAT_MESSAGES ? 3u : 2u;
            static const char *verbosity[3]={"None","Brief","Verbose"};
            for (unsigned i=0;i<count;++i) {
                if (c->selected==i) rectangle(f,112,96+(int)i*8,200,8,14);
                text(r,f,112,96+(int)i*8,c->phase==BTP_COMBAT_MESSAGES ? verbosity[i] : i ? "No" : "Yes",c->selected==i ? 0u : 15u);
            }
        }
    } else if (c->last_event && (c->messages || c->last_event>=4)) {
        rectangle(f,104,168,216,32,0);border_panel(r,f,104,168,216,32,0);
        if (c->last_event==1) snprintf(line,sizeof line,"Hit: %u damage",c->shot.damage);
        else snprintf(line,sizeof line,"%s",c->last_event==2 ? "Miss" : c->last_event==3 ? "Line of sight blocked" :
            c->last_event==4 ? "LOS beyond verified grid" : "Terrain fire unsupported");
        text(r,f,112,176,line,c->last_event>=4 ? 12u : 15u);
        if (c->last_event>=4) text(r,f,112,184,"Move / change target",14);
    }
}
static void story_panel(const BtpResources *r, const BtpState *s, uint32_t *f)
{
    rectangle(f, 104, 0, 216, 200, 7); rectangle(f, 108, 4, 208, 192, 0);
    if (r->border.format == 1) rectangle(f,104,0,216,200,0);
    if (s->service.phase) {
        const BtpServiceState *v=&s->service;char info[40];
        text(r,f,112,8,v->action==44 ? "Ammunition" : v->action==13 ? "Choose a character" : v->action==18 ? "Mechit-Lube repairs" : "Speed Shop",14);
        snprintf(info,sizeof info,"C-bills: %u",s->credits);text(r,f,112,24,info,15);
        if (v->phase==1) for (unsigned i=0;i<5;++i) {
            char name[18]="Done";
            if (i<4) {
                const uint8_t *m=i ? s->party.mechs[i-1] : s->campaign.mech;
                if (s->party.mech_types[i]==255) snprintf(name,sizeof name,"Empty bay %u",i+1);
                else { memcpy(name,m+1,16);name[16]=0; }
            }
            text(r,f,112,48+(int)i*16,name,i==v->selected ? 14u : 15u);
        } else if (v->phase==8) {
            text(r,f,112,56,btp_party_name(&s->party,v->mech),15);text(r,f,112,72,"has joined the group.",15);
        } else if (v->phase==2 && v->action==18) {
            static const char *const rows[]={"Armour: 4 per point","Structure: 9 per point","Heat sink: 800","Weapon component: 300","Leg mechanisms: 200","Done"};
            for (unsigned i=0;i<6;++i) text(r,f,112,48+(int)i*16,rows[i],i==v->selected ? 14u : 15u);
        } else if (v->phase==7) {
            for (unsigned i=0;i<btp_party_count(&s->party);++i) text(r,f,112,48+(int)i*8,btp_party_name(&s->party,btp_party_slot(&s->party,i)),i==v->selected ? 14u : 15u);
        } else if (v->phase==6) {
            for (unsigned i=0;i<18;++i) {
                char name[12]="Done";if (i<17) { memcpy(name,r->combat.weapons[i+15],10);name[10]=0; }
                text(r,f,112,40+(int)i*8,name,i==v->selected ? 14u : 15u);
            }
        } else if (v->phase==2) {
            const uint8_t *m=v->mech ? s->party.mechs[v->mech-1] : s->campaign.mech;
            for (unsigned i=0;i<11;++i) { if (i==10) snprintf(info,sizeof info,"Done");else snprintf(info,sizeof info,"Bin %u: %u / %u",i+1,m[39+i],m[107+i]);text(r,f,112,48+(int)i*10,info,i==v->selected ? 14u : 15u); }
        } else if (v->phase==5) {
            text(r,f,112,56,"Rounds to purchase:",15);text(r,f,112,80,v->input[0] ? v->input : "0",14);
        } else if (v->phase==3) {
            if (v->action==20) {
                const uint8_t *m=v->mech ? s->party.mechs[v->mech-1] : s->campaign.mech;
                unsigned choice=m[123]+(m[124]==1 ? 4u : 0u);
                snprintf(info,sizeof info,"Upgrade: %u C-bills",choice<8 ? r->combat.refit_prices[choice] : 0);text(r,f,112,56,info,15);
            } else text(r,f,112,56,"Proceed with repairs?",15);
            text(r,f,112,88,"Yes",v->selected ? 7u : 14u);text(r,f,152,88,"No",v->selected ? 14u : 7u);
        } else {
            text(r,f,112,56,v->outcome ? "Service completed." : "No purchase made.",v->outcome ? 15u : 14u);
            snprintf(info,sizeof info,"Units: %u",v->amount);text(r,f,112,80,info,15);
        }
        text(r,f,112,184,"Enter / Backspace",7);return;
    }
    if (s->mode == BTP_SCRIPT_FAULT) {
        text(r,f, 110, 12, "UNSUPPORTED STORY ACTION", 12);
        text(r,f, 110, 30, btp_script_error_name(s->script.error), 15);
        char line[40];
        snprintf(line, sizeof line, "PC %04X OPCODE %02X", s->script.fault_pc, s->script.last_opcode);
        text(r,f, 110, 48, line, 14); (void)wrapped(r,f,84,(const uint8_t *)"Backspace returns to the building menu",38,7);
        return;
    }
    const BtpScriptState *v = &s->script;
    uint8_t bytes[BTP_BLD_MAX + 1];
    size_t length;
    if (!btp_game_text(s, r, bytes, sizeof bytes, &length)) {
        text(r,f, 110, 12, "INVALID TEXT BOUNDS", 12); return;
    }
    if (s->bank.phase || v->has_accounts) { bank_panel(r,s,bytes,length,f); return; }
    if (s->school.phase == BTP_SCHOOL_PRICES) { school_panel(r,s,f); return; }
    if (v->status == BTP_SCRIPT_MENU || s->talk.phase == BTP_TALK_MENU) {
        if (!s->talk.phase && !btp_script_menu_text(v,btp_state_bld(r,s),bytes,sizeof bytes,&length)) {
            text(r,f,110,12,"INVALID MENU TEXT",12); return;
        }
        unsigned count = s->talk.phase == BTP_TALK_MENU ? (unsigned)s->talk.count+1 : btp_menu_count(v->menu_id);
        unsigned selected = s->talk.phase == BTP_TALK_MENU ? s->talk.selected : v->selected;
        size_t starts[9]; unsigned found = 0;
        if (count > 9) { text(r,f, 110, 12, "INVALID MENU COUNT", 12); return; }
        for (size_t i = length; i && found < count; --i)
            if (bytes[i - 1] == '\r') starts[count-1-found++] = i;
        if (found != count) { text(r,f, 110, 12, "UNSUPPORTED MENU TEXT LAYOUT", 12); return; }
        int y = wrapped(r,f, r->dialogue.length ? 8 : 9, bytes, starts[0], 15);
        for (unsigned i = 0; i < count; ++i) {
            size_t end = i+1 == count ? length : starts[i + 1] - 1;
            char option[35]; size_t n = end - starts[i];
            if (n >= sizeof option || y > 177) {
                text(r,f, 110, 180, "UNSUPPORTED MENU TEXT LAYOUT", 12); return;
            }
            memcpy(option, bytes + starts[i], n); option[n] = 0;
            if (i == selected) rectangle(f, 109, y - 1, 206, 9, 14);
            text(r,f, 110, y, option, i == selected ? 0u : 15u); y += 9;
        }
    } else {
        int y = wrapped(r,f, r->dialogue.length ? 8 : 9, bytes, length, 15);
        if (v->status == BTP_SCRIPT_CONFIRM) {
            if (y > 177) y = 177;
            text(r,f,110,y,"Yes",v->confirm_selected == 0 ? 14u : 7u);
            text(r,f,140,y,"No",v->confirm_selected == 1 ? 14u : 7u);
        }
    }
}

void btp_render(const BtpResources *r, const BtpState *s, int debug, uint32_t f[BTP_PIXELS])
{
    if (s->mode==BTP_ACTIONS && s->campaign.ui==BTP_MENU_MAP) {
        btp_world_preview(r,s,f);return;
    }
    if (s->mode==BTP_GAME_OVER) {
        rectangle(f,0,0,320,200,0);text(r,f,112,80,"Jason has been killed.",15);text(r,f,112,104,"Load a saved game to continue.",15);return;
    }
    if (s->mode==BTP_LOGO || s->mode==BTP_TITLE) {
        /* Original VGA title capture: index 1 is black, as in sprite art. */
        const BtpGraphic *g=s->mode==BTP_LOGO ? &r->logo : &r->title;
        for (unsigned i=0;i<BTP_PIXELS;++i) f[i]=btp_palette[sprite_palette[g->pixels[i]&15u]];
        return;
    }
    if (s->mode==BTP_BEGIN) {
        rectangle(f,0,0,320,200,0);border_panel(r,f,0,0,104,200,1);border_panel(r,f,104,0,216,200,0);
        uint8_t notice[512];size_t used=0;
        for (unsigned i=115;i<119;++i) { size_t n;const uint8_t *p=bank_literal(r,i,&n);if (p && n<=sizeof notice-used) { memcpy(notice+used,p,n);used+=n; } }
        (void)wrapped(r,f,8,notice,used,15);
        (void)wrapped(r,f,136,(const uint8_t *)"Have you played BattleTech before?",33,15);
        int y=152;
        rectangle(f,s->entry_selected ? 144 : 112,y,s->entry_selected ? 16 : 24,8,14);
        text(r,f,112,y,"Yes",s->entry_selected ? 15u : 0u);text(r,f,144,y,"No",s->entry_selected ? 0u : 15u);return;
    }
    if ((s->combat.phase==BTP_COMBAT_SCAN && !s->combat.unit[s->combat.scan_unit].infantry) ||
        (s->mode==BTP_ACTIONS && s->campaign.ui==BTP_MENU_MECH)) {
        const uint8_t *m;unsigned heat=0,id;
        if (s->combat.phase) { const BtpCombatUnit *u=&s->combat.unit[s->combat.scan_unit];m=u->record;heat=u->heat;id=btp_combat_id(&s->combat,s->combat.scan_unit); }
        else { id=s->campaign.member;m=id ? s->party.mechs[id-1] : s->campaign.mech; }
        const char *pilot=id<4 && m[121]<8 ? btp_party_name(&s->party,m[121]) : NULL;
        const char *rider=id<4 && m[122]<8 ? btp_party_name(&s->party,m[122]) : NULL;
        btp_mech_screen(r,m,pilot,rider,heat,s->tick,f);return;
    }
    if (s->mode == BTP_QUIZ && s->quiz.phase == BTP_QUIZ_QUESTION) {
        for (unsigned i = 0; i < BTP_PIXELS; ++i) f[i] = btp_palette[terrain_palette[r->quiz_diagram.pixels[i]&15u]];
        rectangle(f,0,0,128,200,0);
        text(r,f,3,2,"Identify this",15); text(r,f,3,10,"'Mech part:",15);
        for (unsigned i = 0; i < BTP_QUIZ_PARTS; ++i) {
            size_t n; const uint8_t *p = bank_literal(r,58u+i,&n);
            if (!p || n > 20) continue;
            char label[21]; memcpy(label,p,n); label[n] = 0;
            int y = 28+(int)i*8;
            if (s->quiz.selected == i) rectangle(f,0,y-1,127,8,14);
            text(r,f,3,y,label,s->quiz.selected == i ? 0u : 15u);
        }
        int x = btp_quiz_x[s->quiz.point]-3, y = btp_quiz_y[s->quiz.point]-3;
        rectangle(f,x,y,9,1,15); rectangle(f,x,y+8,9,1,15);
        rectangle(f,x,y,1,9,15); rectangle(f,x+8,y,1,9,15);
        /* physical D0A9..D0C6: a white bar extends from the left of the diagram
           to the outlined part, covering five scanlines. */
        rectangle(f,128,y+2,x-128+1,5,15);
        return;
    }
    int cx=s->x_half,cy=s->y_half;
    if (s->combat.phase) {
        const BtpCombatState *c=&s->combat;
        unsigned focus=c->phase==BTP_COMBAT_TARGET || c->phase==BTP_COMBAT_KICK ? c->target_unit : c->phase==BTP_COMBAT_SCAN ? c->scan_unit : c->active_unit;
        cx=c->phase==BTP_COMBAT_MOVE ? c->cursor_x : c->unit[focus].x;
        cy=(c->phase==BTP_COMBAT_MOVE ? c->cursor_y : c->unit[focus].y)+2;
    }
    BtpMap encounter_map;
    const BtpMap *map=btp_active_map(r,s);
    if (s->campaign.encounter) { btp_combat_map(r,s,&encounter_map);map=&encounter_map; }
    int camera_x = cx * 8 - 96, camera_y = cy * 8 - 96;
    for (int y = 0; y < 200; ++y)
        for (int x = 0; x < 320; ++x) {
            uint32_t color = btp_palette[0];
            if (x >= 104) {
                int wx = camera_x + x - 104, wy = camera_y + y;
                if ((!s->campaign.encounter && r->world.loaded) || (wx >= 0 && wy >= 0 && ((!s->map_id && !s->campaign.encounter) || (wx < map->width * 16 && wy < map->height * 16)))) {
                    int tx=wx>=0 ? wx/16 : (wx-15)/16,ty=wy>=0 ? wy/16 : (wy-15)/16;
                    unsigned tile;
                    if (s->campaign.encounter || (s->map_id && tx>=0 && ty>=0 && tx<map->width && ty<map->height)) tile=btp_mission_tile(s,map,tx,ty);
                    else {
                        int ox=s->map_id ? (int)(map->entrance_x[0]>>8)*64 : 0,oy=s->map_id ? (int)(map->entrance_y[0]>>12)*64 : 0;
                        tile=btp_world_tile(r,s,ox+tx,oy+ty);
                    }
                    if (tile < 250) {
                        /* 320B skips ANIMATE's first blank tile; 240B swaps
                           three pages into these ten map tile slots. The
                           saved fixed clock supplies a deterministic phase. */
                        unsigned frame=btp_terrain_frame(tile,s->tick/4u);
                        const BtpGraphic *sheet=frame && r->terrain_animation.format==1 ? &r->terrain_animation : &r->tiles;
                        unsigned index = (sheet==&r->tiles ? tile : frame) * 256 + ((unsigned)wy&15u)*16 + ((unsigned)wx&15u);
                        unsigned value = sheet->pixels[index] & 15;
                        color = btp_palette[terrain_palette[value]];
                        if (debug && tile >= s->gate && (wx % 16 == 0 || wy % 16 == 0))
                            color = btp_palette[13];
                    }
                }
            } else if (x < 3 || x >= 100 || y < 3 || y >= 197 || y == 100 || y == 101)
                color = btp_palette[7];
            f[y * 320 + x] = color;
        }
    for (unsigned i=0;i<64;++i) {
        const BtpTerrainMark *mark=&s->terrain_marks[i];
        if (mark->sprite && mark->map==s->map_id)
            (void)btp_draw_sprite(&r->sprites,(mark->sprite&254u)==124 ? 124u+(s->tick&1u) : mark->sprite,
                200+((int)mark->x-cx)*8,64+((int)mark->y+2-cy)*8,0,104,f);
    }
    if (s->combat.phase) {
        for (unsigned i=0;i<s->combat.count;++i) if (s->combat.unit[i].record[0]!=255) {
            const BtpCombatUnit *u=&s->combat.unit[i];unsigned terrain;
            if (s->combat.graphics && s->effects.count && s->effects.stage>=BTP_EFFECT_ATTACK) {
                const BtpCombatEffect *e=&s->effects.shots[0];
                unsigned pose=r->combat.poses[e->group][e->direction][0];
                if (s->effects.age/2u<pose && (i==e->actor || (e->hit && i==e->target && u->infantry))) continue;
            }
            unsigned base=u->infantry ? s->combat.friends && i<s->combat.friends ? btp_combat_id(&s->combat,i)==4 ? 166u : 270u : 270u : s->combat.friends ? u->record[0]=='L' ? 0u : 146u : i==0 && s->story_flags[2] ? 146u : 0u;
            (void)btp_draw_sprite(&r->sprites,base+s->combat.walk[i],
                200+((int)u->x-cx)*8,64+((int)u->y+2-cy)*8,btp_combat_cover(map,u,&terrain),104,f);
        }
        combat_route(r,s,cx,cy,f);combat_flash(r,s,cx,cy,f);
    } else if (s->mission.phase) (void)btp_draw_sprite(&r->sprites,
        (s->story_flags[2] ? 146u : 0u)+s->mission.walk,200,64,btp_mission_terrain(s,&r->map),104,f);
    else if (s->campaign.mounted) (void)btp_draw_sprite(&r->sprites,
        ((s->party.people[0][12] ? s->party.mechs[s->party.people[0][12]-1][0] : s->campaign.mech[0])=='L' ? 0u : 146u)+s->campaign.mech_walk,200,64,0,104,f);
    else (void)btp_draw_sprite(&r->sprites,166u+s->player_walk,208,96,
        hidden_rows(map,s->x_half,s->y_half),104,f);
    if (!s->combat.phase && s->story_flags[4]) {
        for (unsigned i=1;i<8;++i) if (s->party.people[i][0]!=255 && (s->party.people[i][12]>=4 || btp_party_mech((BtpState *)s,s->party.people[i][12])[121]==i)) {
            unsigned mount=s->party.people[i][12];
            const uint8_t *m=mount<4 ? mount ? s->party.mechs[mount-1] : s->campaign.mech : NULL;
            unsigned base=m ? m[0]=='L' ? 0u : 146u : 270u;
            (void)btp_draw_sprite(&r->sprites,base+s->party.walk[i],(m ? 200 : 208)+((int)s->party.x[i]-s->campaign.world_x)*8,
                (m ? 64 : 96)+((int)s->party.y[i]-s->campaign.world_y)*8,0,104,f);
        }
    }
    /* Original 051B draws the party before the eight outdoor NPC slots. */
    if (!s->combat.phase && (s->mode == BTP_EXPLORE || s->mode == BTP_MISSION) && s->npc.enabled == 2) for (unsigned i = 0; i < 8; ++i) {
        const BtpNpc *n = &s->npc.actor[i];
        if (!n->x) continue;
        unsigned x = n->x & 127u, y = n->y & 127u;
        int nx = 208+((int)x-s->x_half)*8, ny = 96+((int)y-s->y_half)*8;
        (void)btp_draw_sprite(&r->sprites,270u+s->npc_walk[i],nx,ny,
            hidden_rows(&r->map,x,y),104,f);
    }
    char place[17]; memcpy(place,map->places[s->entry_slot&15u],16); place[16] = 0;
    char line[64];
    if (r->border.format == 1) rectangle(f,0,0,104,200,0);
    /* The original status fields use these positions. The movement log and
       four graphical rank bars remain outside this bounded UI restoration. */
    if (!(s->entry_slot == 0 && s->mode >= BTP_BUILDING)) {
        text(r,f,8,112,"Jason",15);
        text(r,f,8,176,"C-Bills:",15);
        snprintf(line,sizeof line,"%u",s->credits); text(r,f,8,184,line,10);
    }
    if (debug) {
        text(r,f,8,8,"BtechPort",15);
        snprintf(line,sizeof line,"X %u Y %u",s->x_half,s->y_half); text(r,f,8,24,line,15);
        snprintf(line,sizeof line,"Tick %u",s->tick); text(r,f,8,40,line,7);
        text(r,f,8,56,"F5 Save",7); text(r,f,8,64,"F9 Load",7);
        if (s->blocked) text(r,f,8,80,s->blocked == BTP_EDGE ? "Map edge" : "Blocked",12);
    }
    if (s->npc.fault) text(r,f,8,80,"NPC fault",12);
    if (s->combat.phase && s->cutscene.active!=2) combat_panel(r,s,f);
    else if (s->mode==BTP_MISSION && s->mission.phase==BTP_MISSION_RETURN) {
        uint8_t message[256];size_t n;
        rectangle(f,104,72,216,56,0);border_panel(r,f,104,72,216,56,0);
        if (btp_game_text(s,r,message,sizeof message,&n)) (void)wrapped(r,f,80,message,n,15);
    } else if (s->mode == BTP_MISSION) {
        text(r,f,8,151,s->story_flags[2] == 0 ? "Locust" : s->story_flags[2] == 1 ? "Wasp" : "Chameleon",14);
        if (s->mission.phase != BTP_MISSION_DRIVE && s->mission.phase != BTP_MISSION_RESULT) {
            uint8_t message[256]; size_t n;
            rectangle(f,104,72,216,58,7); rectangle(f,108,76,208,50,0);
            if (btp_game_text(s,r,message,sizeof message,&n)) (void)wrapped(r,f,79,message,n,15);
        }
        if (s->mission.assignment>=2) text(r,f,8,166,s->combat.won ? "Completed" : s->combat.lost ? "Defeated" : "Withdrew",14);
        else if (s->mission.assignment) text(r,f,8,166,s->mission.corner && s->story_flags[2] ? "Carrying" : "Rubble",14);
        else if (debug) { snprintf(line,sizeof line,"TIME %u",s->mission.elapsed); text(r,f,8,166,line,14); }
    } else if (s->mode == BTP_BUILDING || s->mode == BTP_SCRIPT_FAULT || s->mode == BTP_QUIZ) {
        if (debug) {
            text(r,f, 8, 151, "Enter/Space", 14);
            snprintf(line, sizeof line, "PC %04X", s->script.pc); text(r,f, 8, 166, line, 14);
            snprintf(line, sizeof line, "OP %02X", s->script.last_opcode); text(r,f, 8, 178, line, 14);
            if (s->script.animation_kind) { snprintf(line,sizeof line,"ANM %u",s->script.animation_kind); text(r,f,8,36,line,14); }
        }
        story_panel(r, s, f);
    } else if (s->mode == BTP_ENTRY) {
        rectangle(f, 104, 73, 216, 55, 7); rectangle(f, 108, 77, 208, 46, 0);
        char question[48]; snprintf(question,sizeof question,"%s?",place);
        text(r,f,112,80,"Will you enter the",15);text(r,f,112,88,question,15);
        if (s->entry_selected==0) rectangle(f,112,96,24,8,14);else rectangle(f,144,96,16,8,14);
        text(r,f,112,96,"Yes",s->entry_selected==0 ? 0u : 15u);
        text(r,f,144,96,"No",s->entry_selected==1 ? 0u : 15u);
    } else if (debug) {
        snprintf(line, sizeof line, "GATE %u", s->gate); text(r,f, 8, 166, line, 14);
        snprintf(line, sizeof line, "TICK %u", s->tick); text(r,f, 8, 178, line, 14);
    }
    unsigned building=btp_building_kind(r,s),portrait=building<26 ? r->combat.building_portraits[building] : 0;
    if (s->cutscene.active || (s->mode == BTP_BUILDING && (s->script.animation_kind || portrait))) {
        unsigned kind = s->cutscene.active ? s->cutscene.kind : s->script.animation_kind ? s->script.animation_kind : portrait;
        unsigned step = s->cutscene.active ? s->cutscene.step : r->animations[kind].count-1u;
        uint8_t packed[BTP_ANM_PACKED];
        if (btp_anm_frame(&r->animations[kind],step,packed)) {
            if (s->cutscene.active == 2) rectangle(f,104,0,216,200,0);
            for (unsigned i = 0; i < 88u*88u; ++i) {
                unsigned value = i&1u ? packed[i/2u]&15u : packed[i/2u]>>4;
                /* Original VGA dream crop: source index 1 is black, as in
                   the sprite palette; it is not terrain's dark blue. */
                f[(8u+i/88u)*320u+8u+i%88u] = btp_palette[sprite_palette[value]];
            }
        } else text(r,f,8,9,"ANM data error",12);
    }
    if (s->mode==BTP_ACTIONS) {
        const BtpCampaignState *c=&s->campaign;
        if (c->ui==BTP_MENU_INSPECT) {
            uint8_t p[17];btp_menu_person(s,c->member,p);
            rectangle(f,104,0,216,200,0);border_panel(r,f,104,0,216,200,0);
            text(r,f,112,8,"Name  :",10);text(r,f,176,8,btp_character_name(p[0]),15);
            text(r,f,112,16,"Weapon:",10);char weapon[12];memcpy(weapon,r->combat.weapons[p[11]],11);weapon[11]=0;text(r,f,176,16,weapon,15);
            text(r,f,112,24,"Armor :",10);
            size_t n;const uint8_t *armor=bank_literal(r,102u+p[13],&n);
            if (armor) text(r,f,176,24,(const char *)armor,15);
            text(r,f,112,40,"Health:",10);
            unsigned health=p[1] ? p[15]/p[1] : 0;if (health>10) health=10;
            const uint8_t *condition=bank_literal(r,91u+health,&n);
            if (condition) {
                char message[128];snprintf(message,sizeof message,"%s%s",btp_character_name(p[0]),(const char *)condition);
                (void)wrapped_at(r,f,176,40,17,(const uint8_t *)message,strlen(message),15);
            }
            text(r,f,112,96,"Skills:",10);
            static const char *const subjects[]={"Bow & Blade","Pistol","Rifle","Gunnery","Piloting","Tech","Medical"};
            static const char *const ranks[]={"Unskilled","Amateur","Adequate","Good","Excellent"};
            for (unsigned i=0;i<7;++i) {
                text(r,f,112,112+(int)i*8,subjects[i],10);text(r,f,208,112+(int)i*8,ranks[p[4+i]>4 ? 4 : p[4+i]],15);
            }
            text(r,f,112,176,"MedKit:",10);text(r,f,176,176,s->party.medical_kit ? "Yes" : "No",15);
            text(r,f,208,176,"Mapper:",10);text(r,f,272,176,s->story_flags[49] ? "Yes" : "No",15);
            text(r,f,112,184,"Field Surgery Kit:",10);text(r,f,264,184,s->party.advanced_kit ? "Yes" : "No",15);
        } else if (c->ui==BTP_MENU_MESSAGE) {
            rectangle(f,104,72,216,88,0);border_panel(r,f,104,72,216,88,0);
            const char *message=s->menu.notice==1 ? "Save failed. Your previous save is intact." : s->menu.notice==2 ?
                "Load failed. This slot is empty or invalid." : s->menu.notice==3 ? (s->story_flags[25] ? "Field treatment completed. Allow time before treating again." : "Everyone is healthy.") :
                "Crew allocation requires open terrain and a qualified pilot for each active 'Mech.";
            (void)wrapped(r,f,80,(const uint8_t *)message,strlen(message),15);
        } else if (c->ui==BTP_MENU_LOAD || c->ui==BTP_MENU_SAVE) {
            rectangle(f,0,104,104,88,0);text(r,f,8,104,c->ui==BTP_MENU_LOAD ? "Load Game:" : "Save Game:",15);
            for (unsigned i=0;i<7;++i) {
                int y=112+8*(int)i;
                if (i==c->selected) rectangle(f,8,y,88,8,14);
                text(r,f,8,y,btp_actions_label(s,i),i==c->selected ? 0u : 15u);
            }
        } else if (c->ui!=BTP_MENU_MAP) {
            unsigned count=btp_actions_count(s);
            int top=c->ui==BTP_MENU_ROOT ? 168-8*(int)(count+2u) : 72;
            rectangle(f,104,top,216,8*(int)(count+2u),0);border_panel(r,f,104,top,216,8*(int)(count+2u),0);
            for (unsigned i=0;i<count;++i) {
                int y=top+8+8*(int)i;
                if (i==c->selected) rectangle(f,112,y,200,8,14);
                text(r,f,112,y,btp_actions_label(s,i),i==c->selected ? 0u : 15u);
            }
        }
    }
    if (s->aftermath.phase) {
        const BtpAftermathState *v=&s->aftermath;char message[320];
        if (v->phase==1) snprintf(message,sizeof message,"%s is a qualified pilot without a 'Mech. Do you want to salvage one of the wrecks?",btp_party_name(&s->party,v->pilot));
        else if (v->phase==2) snprintf(message,sizeof message,"%s",v->notice==2 ? "There are no more salvageable 'Mechs on the battlefield." : v->notice ? "No chance to salvage this 'Mech." : "The 'Mech is salvaged.");
        else if (v->phase==3) snprintf(message,sizeof message,"You dig through the soldiers' pockets and find %u C-bills in cash%s",v->cash,v->notice ? ", and confiscate their weapons." : ".");
        else snprintf(message,sizeof message,"Recovered weapon. %s",btp_party_count(&s->party)==1 ? "Do you want to exchange your weapon?" : "Choose who receives it.");
        rectangle(f,104,0,216,200,0);border_panel(r,f,104,0,216,200,0);int y=wrapped(r,f,16,(const uint8_t *)message,strlen(message),15)+16;
        if (v->phase==1 || (v->phase==4 && btp_party_count(&s->party)==1)) {
            text(r,f,112,y,"Yes",v->selected==0 ? 14u : 15u);text(r,f,152,y,"No",v->selected==1 ? 14u : 15u);
        } else if (v->phase==4) for (unsigned i=0;i<=btp_party_count(&s->party);++i) text(r,f,112,y+(int)i*8,i==btp_party_count(&s->party) ? "Done" : btp_party_name(&s->party,btp_party_slot(&s->party,i)),i==v->selected ? 14u : 15u);
    }
    border_panel(r,f,0,0,104,200,1);
    if (s->mode == BTP_BUILDING || s->mode == BTP_SCRIPT_FAULT ||
        (s->mode == BTP_QUIZ && s->quiz.phase != BTP_QUIZ_QUESTION) || (s->cutscene.active && s->cutscene.active!=3))
        border_panel(r,f,104,0,216,200,0);
    else if (s->mode == BTP_ENTRY) border_panel(r,f,104,72,216,56,0);
    else if (s->mode == BTP_MISSION && s->mission.phase != BTP_MISSION_DRIVE && s->mission.phase != BTP_MISSION_RESULT && s->mission.phase!=BTP_MISSION_RETURN)
        border_panel(r,f,104,72,216,64,0);
}

void btp_world_preview(const BtpResources *r,const BtpState *s,uint32_t f[BTP_PIXELS])
{
    rectangle(f,0,0,320,200,0);
    unsigned wx=s->story_flags[4] ? s->campaign.world_x : 1536u+s->x_half;
    unsigned wy=s->story_flags[4] ? s->campaign.world_y : 1536u+s->y_half;
    unsigned center_x=s->mode==BTP_ACTIONS && s->campaign.ui==BTP_MENU_MAP ? s->menu.map_x : wx;
    unsigned center_y=s->mode==BTP_ACTIONS && s->campaign.ui==BTP_MENU_MAP ? s->menu.map_y : wy;
    int ox=(int)(center_x/128u)-2,oy=(int)(center_y/128u)-1;
    if (ox<0) ox=0;
    if (oy<0) oy=0;
    if (ox>11) ox=11;
    if (oy>13) oy=13;
    ox*=8;oy*=8;
    for (unsigned row=0;row<24;++row) for (unsigned col=0;col<40;++col) {
        unsigned x=(unsigned)ox+col,y=(unsigned)oy+row;
        if (!btp_world_seen(s,x,y)) continue;
        unsigned id=btp_world_mini(r,s,x,y);
        for (unsigned dy=0;dy<8;++dy) for (unsigned dx=0;dx<8;++dx) {
            int tx=(int)(8*x+dx),ty=(int)(8*y+dy);
            unsigned place=(unsigned)btp_world_location(r,s,tx,ty),value;
            if (place) {
                unsigned tile=btp_world_tile(r,s,tx,ty);
                value=r->world.mini_colors[tile&255u];
            } else value=id<66 ? r->tinyland.pixels[(id/40u*8u+dy)*320u+(id%40u*8u+dx)] : 0u;
            pixel(f,(int)(8*col+dx),(int)(8*row+dy),btp_palette[sprite_palette[value&15u]]);
        }
    }
    if (s->story_flags[47] && !s->story_flags[58] && !(wx/128u==10 && wy/128u==8)) {
        /* 0000:43D6..4446: the device directs you to packed 0A38/8038,
           and disappears on arrival in the Starport sector. */
        unsigned direction=btp_combat_direction((int)wx,(int)wy,1336,1080);
        static const uint8_t x[]={20,23,23,23,20,16,16,16},y[]={8,8,12,15,15,15,12,8};
        if (direction<8) { char arrow[2]={(char)(direction+1u),0};text(r,f,8*x[direction],8*y[direction],arrow,15); }
    }
    int px=((int)(wx/16u)-ox)*8,py=((int)(wy/16u)-oy)*8;
    if (px>=0 && px<320 && py>=0 && py<192) {
        rectangle(f,px+2,py+2,4,1,15);rectangle(f,px+2,py+5,4,1,15);
        rectangle(f,px+2,py+2,1,4,15);rectangle(f,px+5,py+2,1,4,15);
    }
    text(r,f,0,192,"Press any key to return to game.",15);
}
void btp_sprite_preview(const BtpResources *r, unsigned tick, uint32_t f[BTP_PIXELS])
{
    for (unsigned i = 0; i < BTP_PIXELS; ++i) f[i] = btp_palette[2];
    text(r,f,8,5,"Original sprite preview",15);
    text(r,f,8,17,"Frames - Ctrl+Shift+Esc exits",15);
    const unsigned bases[] = {0,146,166,270};
    const char *labels[] = {"Locust", "Commando", "Jason", "Cadets"};
    for (unsigned row = 0; row < 4; ++row) {
        int y = row < 2 ? 30+(int)row*56 : 144+(int)(row-2)*24;
        text(r,f,8,y,labels[row],15);
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

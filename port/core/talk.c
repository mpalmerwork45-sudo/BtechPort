#include "core/talk.h"
#include "core/bank.h"
#include "core/school.h"
#include "core/training.h"
#include <string.h>

static void native_fault(BtpState *s, BtpScriptError error)
{
    s->script.error = (uint8_t)error; s->script.status = BTP_SCRIPT_ERROR;
    s->script.fault_pc = s->script.pc >= 2 ? (uint16_t)(s->script.pc-2) : 0;
    uint8_t selected = s->talk.selected;
    s->talk = (BtpTalkState){.selected=selected};
}
static unsigned present(const BtpState *s, unsigned room)
{
    unsigned mask = 0;
    for (unsigned i = 0; i < 8; ++i)
        if (s->npc_pairs[i][1] && ((s->npc_pairs[i][0] >> 4) & 7u) == room) mask |= 1u << i;
    return mask;
}
static unsigned count_bits(unsigned mask)
{
    unsigned n = 0;
    for (; mask; mask >>= 1) n += mask & 1u;
    return n;
}
void btp_start_conversation_checkpoint(BtpState *s)
{
    /* Explicit handler test precondition, not a simulated NPC arrival. */
    static const uint8_t pairs[8][2] = {{99,0},{18,1},{53,0},{99,0},{18,0},{4,0},{4,0},{70,0}};
    btp_start(s); memcpy(s->npc_pairs,pairs,sizeof pairs);
    s->npc = (BtpNpcState){0};
    s->talk_result = s->story_flags[46] = 91; s->conversation_checkpoint = 1;
}
void btp_start_shop_conversation_checkpoint(BtpState *s, const BtpResources *r, unsigned slot)
{
    btp_start(s);
    if (slot != 3 && slot != 4) return;
    /* Explicit two-occupant original-handler snapshots. Normal exploration
       never injects these pairs or disables travel. See the M2f fixtures. */
    s->npc = (BtpNpcState){0}; s->conversation_checkpoint = 1;
    s->credits = 50; s->talk_result = s->story_flags[46] = 91;
    s->mode = BTP_BUILDING; s->entry_slot = (uint8_t)slot;
    s->x_half = r->map.entrance_x[slot]&127;
    s->y_half = (uint16_t)((r->map.entrance_y[slot]&127)+1);
    s->story_flags[10] = 1; s->story_flags[13] = (uint8_t)slot;
    s->npc_pairs[1][0] = (uint8_t)((slot<<4)|((slot+1)%8)); s->npc_pairs[1][1] = 5;
    s->npc_pairs[4][0] = (uint8_t)((slot<<4)|((slot+2)%8)); s->npc_pairs[4][1] = 7;
    btp_script_start(&s->script,btp_building_bld(r,slot),s->story_flags);
    if (slot == 3) s->script.choices[12] = 3; /* Earlier Armor visit in this trace. */
    s->script.selected = (uint8_t)(slot == 3 ? 1 : 2);
    s->script.choices[s->script.menu_id] = s->script.selected;
}
void btp_talk_begin(BtpState *s, const BtpResources *r)
{
    unsigned room = 0;
    while (room < 8 && r->map.room_map[room] != s->story_flags[13]) ++room;
    unsigned mask = present(s,room), count = count_bits(mask);
    uint8_t selected = s->talk.selected;
    s->talk = (BtpTalkState){.phase=count ? BTP_TALK_MENU : BTP_TALK_EMPTY,
        .selected=selected,.room=(uint8_t)room,.count=(uint8_t)count,.mask=(uint8_t)mask};
    if (count && selected > count) s->talk.selected = 0;
    if (!r->dialogue.length) { native_fault(s,BTP_SCRIPT_NATIVE_DATA); return; }
    if (s->story_flags[4] || room >= 8 || room != s->entry_slot) {
        native_fault(s,BTP_SCRIPT_NATIVE_CONTEXT); return;
    }
    uint8_t body[BTP_BLD_MAX+1]; size_t length;
    if (!btp_game_text(s,r,body,sizeof body,&length)) native_fault(s,BTP_SCRIPT_NATIVE_DATA);
}
static void native_return(BtpState *s, const BtpResources *r)
{
    uint8_t selected = s->talk.selected;
    s->talk = (BtpTalkState){.selected=selected};
    s->story_flags[46] = s->talk_result;
    btp_script_native_return(&s->script,btp_building_bld(r,s->entry_slot),s->story_flags);
}
void btp_talk_input(BtpState *s, const BtpResources *r, BtpAction action)
{
    if (s->talk.phase == BTP_TALK_MENU) {
        unsigned n = (unsigned)s->talk.count+1;
        if (action == BTP_UP) s->talk.selected = (uint8_t)((s->talk.selected+n-1)%n);
        if (action == BTP_DOWN) s->talk.selected = (uint8_t)((s->talk.selected+1u)%n);
        if (action == BTP_ACCEPT) {
            if (s->talk.selected == s->talk.count) { native_return(s,r); return; }
            unsigned choice = s->talk.selected, actor = 0;
            for (; actor < 8; ++actor) if (s->talk.mask & (1u << actor)) {
                if (!choice) break;
                --choice;
            }
            if (actor == 8) { native_fault(s,BTP_SCRIPT_NATIVE_CONTEXT); return; }
            /* Original room-7 Rick shortcut, before the ordinary reply. */
            if (s->talk.room == 7 && s->recruitment && !s->talk.selected && actor == 0) {
                s->talk_result = 1; s->npc_pairs[0][1] = 0;
                native_return(s,r); return;
            }
            s->talk.actor = (uint8_t)actor; s->talk.phase = BTP_TALK_REPLY;
            /* Ordinary local replies reset the result without recruitment. */
            s->talk_result = 0;
            s->story_flags[46] = 0;
            uint8_t body[BTP_BLD_MAX+1]; size_t length;
            if (!btp_game_text(s,r,body,sizeof body,&length)) native_fault(s,BTP_SCRIPT_NATIVE_DATA);
        }
    } else if ((s->talk.phase == BTP_TALK_EMPTY || s->talk.phase == BTP_TALK_REPLY) && action == BTP_ACCEPT)
        native_return(s,r);
}
int btp_talk_valid(const BtpState *s, const BtpMap *map)
{
    const BtpTalkState *t = &s->talk;
    if (t->phase > BTP_TALK_REPLY || t->selected > 8 || s->conversation_checkpoint > 1) return 0;
    if (!t->phase) return !t->count && !t->mask && !t->room && !t->actor &&
        !(s->script.status == BTP_SCRIPT_NATIVE && s->script.native_action == 12);
    if (s->mode != BTP_BUILDING || s->script.status != BTP_SCRIPT_NATIVE ||
        s->script.last_opcode != 0xf5 || s->script.native_action != 12 || s->story_flags[4] ||
        t->room >= 8 || t->room != s->entry_slot ||
        map->room_map[t->room] != s->story_flags[13] || !s->checkpoint_valid) return 0;
    unsigned mask = present(s,t->room);
    if (mask != t->mask || count_bits(mask) != t->count) return 0;
    if (t->phase == BTP_TALK_EMPTY) return !mask && !t->actor;
    if (!mask || t->selected > t->count) return 0;
    if (t->phase == BTP_TALK_MENU) return !t->actor;
    if (t->selected == t->count || t->actor >= 8 || !(mask & (1u << t->actor)) || s->talk_result) return 0;
    unsigned preceding = count_bits(mask & ((1u << t->actor)-1));
    return preceding == t->selected;
}

static int append(uint8_t *out, size_t capacity, size_t *length, const uint8_t *p, size_t n)
{
    if (*length >= capacity || n >= capacity-*length) return 0;
    memcpy(out+*length,p,n); *length += n; out[*length] = 0; return 1;
}
static int literal(const BtpDialogue *d, unsigned id, uint8_t *out, size_t capacity, size_t *length)
{
    if (id >= BTP_TALK_STRINGS || !d->length || d->length > BTP_TALK_MAX ||
        d->offset[id] >= d->length || d->size[id] >= d->length-d->offset[id] ||
        d->bytes[d->offset[id]+d->size[id]]) return 0;
    return append(out,capacity,length,d->bytes+d->offset[id],d->size[id]);
}
static int name(const uint8_t p[16], uint8_t *out, size_t capacity, size_t *length)
{
    const uint8_t *end = memchr(p,0,16);
    if (!end || end == p) return 0;
    for (const uint8_t *at = p; at < end; ++at) if (*at < 32 || *at >= 127) return 0;
    return append(out,capacity,length,p,(size_t)(end-p));
}
int btp_game_text(const BtpState *s, const BtpResources *r, uint8_t *out, size_t capacity, size_t *length)
{
    if (!s || !r || !out || !length || !capacity) return 0;
    *length = 0; out[0] = 0;
    if (s->mode == BTP_QUIZ || s->mode == BTP_MISSION || s->script.mech_result)
        return btp_training_text(s,r,out,capacity,length);
    if (!s->talk.phase) {
        if (s->school.phase) return btp_school_text(s,r,out,capacity,length);
        if (s->bank.phase || s->script.has_accounts) return btp_bank_text(s,r,out,capacity,length);
        int ok = btp_script_text(&s->script,btp_building_bld(r,s->entry_slot),out,capacity);
        if (ok) *length = strlen((const char *)out);
        return ok;
    }
    const BtpDialogue *d = &r->dialogue;
    if (s->talk.phase == BTP_TALK_EMPTY) return literal(d,0,out,capacity,length);
    if (s->talk.phase == BTP_TALK_MENU) {
        if (!literal(d,1,out,capacity,length)) return 0;
        for (unsigned i = 0; i < 8; ++i) if (s->talk.mask & (1u << i)) {
            static const uint8_t newline = '\r';
            if (!name(r->map.npc_names[i],out,capacity,length) ||
                !append(out,capacity,length,&newline,1)) return 0;
        }
        return literal(d,2,out,capacity,length);
    }
    if (s->talk.phase != BTP_TALK_REPLY || s->talk.actor >= 8 || s->story_flags[13] >= 11) return 0;
    unsigned destination = s->npc_pairs[s->talk.actor][0] & 7u;
    return literal(d,3,out,capacity,length) && literal(d,6u+s->story_flags[13],out,capacity,length) &&
        literal(d,4,out,capacity,length) && name(r->map.places[destination],out,capacity,length) &&
        literal(d,5,out,capacity,length);
}

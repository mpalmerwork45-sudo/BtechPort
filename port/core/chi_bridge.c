#include "core/chi_bridge.h"
#include "core/events.h"
#include "core/original_actions.h"
#include "core/party.h"
#include "core/economy.h"
#include "core/mission_state.h"
#include "core/battle_mission.h"
#include "core/world.h"
#include "core/npc.h"
#include "data/project.h"
#include <string.h>

/* Only control and presentation are suspended. Money, crew, damage, story
   and RNG belong to the campaign and are never restored from an old frame. */
void btp_bridge_clear_checkpoint(BtpState *s)
{
    s->checkpoint_valid=0;memset(s->story_checkpoint,0,sizeof s->story_checkpoint);
    s->checkpoint_talk_result=0;s->checkpoint_credits=0;s->checkpoint_allowance_cap=0;
    memset(s->checkpoint_investments,0,sizeof s->checkpoint_investments);
    memset(s->checkpoint_skills,0,sizeof s->checkpoint_skills);
    memset(s->checkpoint_mech_skills,0,sizeof s->checkpoint_mech_skills);
    s->checkpoint_technician=s->checkpoint_apprentice=0;
    s->campaign.checkpoint_owned=0;memset(s->campaign.checkpoint_mech,0,125);
    s->party_checkpoint=(BtpPartyState){0};
    s->checkpoint_weapon=s->checkpoint_armor=s->checkpoint_armor_points=0;
}
void btp_bridge_initialize(BtpState *s,const BtpResources *r)
{
    if (!r->project || !r->project->chi_bridge || s->bridge.enabled) return;
    s->bridge=(BtpBridgeState){.enabled=1,.call=255};
    s->event=(BtpEventState){.origin_entry=255};memset(s->event.people,255,8);
    btp_mission_initialize(s,btp_adventure(r));
    if (btp_adventure(r)->combat_missions) s->battle_mission=(BtpBattleMissionState){.enabled=1,.encounter=255};
}
void btp_bridge_capture(const BtpState *s,BtpBridgePosition *p)
{
    *p=(BtpBridgePosition){.x=s->x_half,.y=s->y_half,.world_x=s->campaign.world_x,.world_y=s->campaign.world_y,
        .map=s->event.map,.native_map=s->map_id,.scene=s->bridge.scene,.entry=s->entry_slot,.action=s->entry_action,
        .building=s->campaign.building,.disk=s->disk_origin};
}
void btp_bridge_scene(BtpState *s,unsigned scene)
{
    if (!s->bridge.enabled || scene==s->bridge.scene) return;
    BtpBridgeState *b=&s->bridge;
    if (scene) {
        memcpy(b->native_explored,s->explored,2048);memcpy(s->explored,b->quest_explored,2048);
        b->parked_npc=s->npc;s->npc=(BtpNpcState){.rng={s->npc.rng[0],s->npc.rng[1],s->npc.rng[2]}};
        memcpy(b->native_marks,s->terrain_marks,sizeof b->native_marks);b->native_mark_next=s->terrain_next;
        memset(s->terrain_marks,0,sizeof s->terrain_marks);s->terrain_next=0;
    } else {
        memcpy(b->quest_explored,s->explored,2048);memcpy(s->explored,b->native_explored,2048);
        memcpy(b->parked_npc.rng,s->npc.rng,3);s->npc=b->parked_npc;b->parked_npc=(BtpNpcState){0};
        memcpy(s->terrain_marks,b->native_marks,sizeof b->native_marks);s->terrain_next=b->native_mark_next;
        memset(b->native_marks,0,sizeof b->native_marks);b->native_mark_next=0;
        if (s->npc.enabled) s->npc.allowance_pending=(uint8_t)btp_economy_below_cap(s);
    }
    b->scene=(uint8_t)scene;
}
void btp_bridge_restore(BtpState *s,const BtpBridgePosition *p)
{
    btp_bridge_scene(s,p->scene);s->x_half=p->x;s->y_half=p->y;s->map_id=p->native_map;
    s->campaign.world_x=p->world_x;s->campaign.world_y=p->world_y;s->event.map=p->map;
    s->entry_slot=p->entry;s->entry_action=p->action;s->campaign.building=p->building;s->disk_origin=p->disk;
}
static void scene_fields(BtpState *s,const BtpResources *r)
{
    if (s->bridge.scene) {
        const BtpScene *m=&btp_adventure(r)->maps[s->event.map];
        s->event.planet=(uint8_t)m->world;s->event.explore_offset=(uint16_t)m->explore_offset;
        s->event.explore_width=(uint8_t)m->explore_width;s->event.explore_height=(uint8_t)m->explore_height;
    } else s->event.planet=s->event.explore_width=s->event.explore_height=0,s->event.explore_offset=0;
}
static int clean(const BtpState *s)
{
    return !s->campaign.invasion && !s->campaign.encounter && !s->combat.phase && !s->mission.phase &&
        !s->cache.active && !s->yard.active && !s->quiz.phase && !s->bank.phase && !s->service.phase &&
        !s->talk.phase && !s->cutscene.active && !s->audio.sound_count && !s->disk_origin;
}
static BtpBridgeFrame *push(BtpState *s,unsigned kind)
{
    if (s->bridge.depth>=BTP_BRIDGE_DEPTH) return NULL;
    BtpBridgeFrame *f=&s->bridge.frames[s->bridge.depth++];
    *f=(BtpBridgeFrame){.kind=(uint8_t)kind,.node=s->event.node,.call=s->bridge.call};
    btp_bridge_capture(s,&f->position);return f;
}
static void enter_event(BtpState *s,unsigned event)
{
    btp_party_init(s);btp_bridge_clear_checkpoint(s);s->script=(BtpScriptState){0};s->school=(BtpSchoolState){0};
    s->campaign.building=0;s->entry_slot=0;s->disk_origin=0;s->event.enabled=1;
    btp_events_jump(s,event);s->mode=BTP_EVENT;
}
int btp_bridge_entrance(BtpState *s,const BtpResources *r)
{
    if (!s->bridge.enabled || s->bridge.depth || !clean(s)) return 0;
    const BtpChiBridge *b=r->project->chi_bridge;
    for (unsigned i=0;i<b->binding_count;++i) if (b->bindings[i].map==s->map_id && b->bindings[i].entrance==s->entry_slot) {
        if (!push(s,BTP_BRIDGE_ENTRANCE)) return 0;
        enter_event(s,b->bindings[i].event);return 1;
    }
    return 0;
}
int btp_bridge_script(BtpState *s,const BtpResources *r)
{
    if (s->script.status!=BTP_SCRIPT_EVENT) return 0;
    unsigned event=s->script.money_amount;
    if (!s->bridge.enabled || !clean(s) || event>=btp_adventure(r)->node_count || s->bridge.depth>=BTP_BRIDGE_DEPTH) {
        btp_script_event_return(&s->script,btp_state_bld(r,s),s->story_flags,1);return 1;
    }
    BtpBridgeFrame *f=push(s,BTP_BRIDGE_BLD);f->script=s->script;f->program=(uint8_t)btp_building_kind(r,s);
    enter_event(s,event);return 1;
}
int btp_bridge_call(BtpState *s,const BtpResources *r,unsigned native)
{
    const BtpEventNode *e=&btp_adventure(r)->nodes[s->event.node];
    if (!s->bridge.enabled || !s->bridge.depth || s->bridge.depth>=BTP_BRIDGE_DEPTH) goto failed;
    if (!native) {
        /* Reject a repeated call site before it can exhaust a C stack or
           become a persistent infinite continuation cycle. */
        for (unsigned i=0;i<s->bridge.depth;++i)
            if (s->bridge.frames[i].kind==BTP_BRIDGE_EVENT_CALL && s->bridge.frames[i].node==s->event.node) goto failed;
        (void)push(s,BTP_BRIDGE_EVENT_CALL);btp_events_jump(s,e->argument);return 1;
    }
    if (s->bridge.call!=255 || !clean(s) || e->argument>=r->project->chi_bridge->call_count) goto failed;
    const BtpChiCall *c=&r->project->chi_bridge->calls[e->argument];
    (void)push(s,BTP_BRIDGE_NATIVE);
    /* A borrowed service runs in the saved native environment, even if the
       quest has travelled to a separate authored battlefield. */
    if (s->bridge.scene) btp_bridge_restore(s,&s->bridge.frames[0].position);
    s->bridge.call=(uint8_t)e->argument;s->bridge.outcome=0;s->event.enabled=0;
    s->event.phase=BTP_EVENT_INACTIVE;
    s->mode=BTP_BUILDING;s->campaign.building=c->building;s->entry_slot=c->building<8 ? c->building : 0;
    btp_original_checkpoint(s);
    btp_script_start_call(&s->script,btp_state_bld(r,s),s->story_flags,c->entry,c->end);
    return 1;
failed:
    btp_events_jump(s,e->next[1]);return 0;
}
void btp_bridge_return(BtpState *s,const BtpResources *r,unsigned outcome)
{
    if (!s->bridge.depth) { s->event.phase=BTP_EVENT_FAULT;s->mode=BTP_EVENT;return; }
    BtpBridgeFrame f=s->bridge.frames[--s->bridge.depth];
    if (f.kind==BTP_BRIDGE_NATIVE && s->bridge.call<r->project->chi_bridge->call_count) {
        const BtpChiCall *c=&r->project->chi_bridge->calls[s->bridge.call];
        btp_script_observe_bridge(btp_state_bld(r,s),c->entry,c->end,outcome);
    }
    memset(&s->bridge.frames[s->bridge.depth],0,sizeof f);
    btp_bridge_clear_checkpoint(s);s->bank=(BtpBankState){0};s->service=(BtpServiceState){0};s->school=(BtpSchoolState){0};
    s->script=(BtpScriptState){0};s->bridge.call=f.call;s->bridge.outcome=0;
    btp_bridge_restore(s,&f.position);scene_fields(s,r);
    if (outcome>2) outcome=1;
    if (f.kind==BTP_BRIDGE_EVENT_CALL || f.kind==BTP_BRIDGE_NATIVE) {
        s->event.enabled=1;s->mode=BTP_EVENT;btp_events_jump(s,btp_adventure(r)->nodes[f.node].next[outcome]);
    } else {
        s->event.enabled=0;s->event.phase=BTP_EVENT_INACTIVE;s->event.page=s->event.selected=0;
        if (f.kind==BTP_BRIDGE_BLD) {
            s->script=f.script;s->mode=BTP_BUILDING;
            /* Refresh rollback AFTER quest effects. An ensuing BLD fault
               must not undo cash while retaining its once-only event bit. */
            btp_original_checkpoint(s);
            btp_script_event_return(&s->script,btp_state_bld(r,s),s->story_flags,outcome);
            btp_game_script_finish(s,r);
        } else {
            s->mode=s->party.people[0][0]==255 ? BTP_GAME_OVER : BTP_EXPLORE;
            s->campaign.building=0;s->entry_slot=0;btp_party_recover(s,r,1);btp_world_reveal(s);
        }
    }
}
int btp_bridge_cancel(BtpState *s,const BtpResources *r,BtpAction action)
{
    /* Amount entry keeps the original Backspace meaning of Escape. Only
       the top-level service selector gets an explicit bridge cancellation. */
    if (!s->bridge.enabled || s->bridge.call==255 || action!=BTP_CANCEL || s->bank.phase!=BTP_BANK_MENU) return 0;
    btp_bridge_return(s,r,2);return 1;
}
void btp_bridge_pump(BtpState *s,const BtpResources *r)
{
    if (!s->bridge.enabled) return;
    for (unsigned budget=0;budget<16;++budget) {
        scene_fields(s,r);
        if (s->npc.enabled) s->npc.allowance_pending=(uint8_t)btp_economy_below_cap(s);
        if (s->event.enabled) {
            if (s->event.phase!=BTP_EVENT_INACTIVE || s->mode!=BTP_EVENT) return;
            btp_events_continue(s,r);continue;
        }
        if (s->script.status==BTP_SCRIPT_EVENT) { btp_bridge_script(s,r);continue; }
        if (s->bridge.call==255) return;
        if (s->bank.phase==BTP_BANK_MESSAGE)
            s->bridge.outcome=(uint8_t)(s->bank.outcome==BTP_BANK_TRADED ? 0 : s->bank.outcome==BTP_BANK_ZERO ? 2 : 1);
        if (s->script.status==BTP_SCRIPT_RETURN || s->script.status==BTP_SCRIPT_ERROR || s->script.status==BTP_SCRIPT_END) {
            btp_bridge_return(s,r,s->script.status==BTP_SCRIPT_RETURN ? s->bridge.outcome : 1u);continue;
        }
        if (s->script.status==BTP_SCRIPT_NATIVE && !s->bank.phase && !s->service.phase) {
            const BtpChiCall *c=&r->project->chi_bridge->calls[s->bridge.call];
            if (s->script.native_action!=c->action) { btp_bridge_return(s,r,1);continue; }
            btp_original_services(s,r);btp_game_script_finish(s,r);continue;
        }
        return;
    }
    /* A tight call/return loop also needs a budget. Preserve an actual event
       caller before yielding a recoverable fault; a settled native menu at
       the exact budget boundary is already safe and needs no invented owner. */
    if (!s->event.enabled && s->script.status==BTP_SCRIPT_EVENT) btp_bridge_script(s,r);
    if (s->bridge.call!=255) btp_bridge_return(s,r,1);
    if (s->bridge.depth && s->event.enabled && s->event.phase==BTP_EVENT_INACTIVE) {
        s->bridge.fault=1;s->event.phase=BTP_EVENT_FAULT;s->mode=BTP_EVENT;
    }
}

static const BtpMap *native_map(const BtpResources *r,unsigned id)
{ return id==15 ? &r->maproom : id==11 ? &r->destroyed : id>=2 && id<=14 ? &r->local[id-1] : &r->map; }

static int suspended_script(const BtpScriptState *s,const BtpBld *p,unsigned nodes)
{
    if (s->status!=BTP_SCRIPT_EVENT || s->last_opcode!=0xe3 || s->error || s->fault_pc || s->pause_units || s->stopping || s->stop_pc ||
        s->pc<9 || s->pc>p->length || p->bytes[s->pc-9]!=0xe3 || s->money_amount>=nodes ||
        s->money_amount!=(p->bytes[s->pc-8]|(unsigned)p->bytes[s->pc-7]<<8) || s->text_count>BTP_TEXT_SPANS ||
        s->menu_id>=BTP_MENUS || s->selected>7 || (s->font && s->font!=3 && s->font!=4 && s->font!=6) || s->scene ||
        s->confirm_selected>1 || s->has_cash>1 || s->has_accounts>1 || s->has_position>1 || s->has_name>1 ||
        s->cash_after>s->text_count || s->mech_after>s->text_count || s->name_after>s->text_count) return 0;
    for (unsigned i=0;i<BTP_MENUS;++i) if (s->choices[i]>=btp_menu_count(i) && s->choices[i]) return 0;
    for (unsigned i=s->text_count;i<BTP_TEXT_SPANS;++i) if(s->text[i].offset || s->text[i].length) return 0;
    uint8_t text[BTP_BLD_MAX+1];return btp_script_text(s,p,text,sizeof text);
}

static int position_valid(const BtpBridgePosition *p,const BtpResources *r)
{
    if (p->scene>1 || p->entry>15 || p->building>25 || p->disk || p->action>BTP_CREDIT_10000) return 0;
    if (p->scene) return p->map<btp_adventure(r)->map_count && p->native_map==(p->map<239 ? 16+p->map : 255) &&
        p->x<2*btp_adventure(r)->maps[p->map].visual.width && p->y<2*btp_adventure(r)->maps[p->map].visual.height;
    return p->native_map<=15 && p->x<(p->native_map ? 128u : 2048u) && p->y<(p->native_map ? 128u : 2048u) && p->world_x<2048 && p->world_y<2048;
}
int btp_bridge_valid(const BtpState *s,const BtpResources *r)
{
    const BtpBridgeState *b=&s->bridge;const BtpAdventure *a=btp_adventure(r);const BtpEventState *v=&s->event;
    if (!b->enabled || !r->project || !r->project->chi_bridge || !a || b->depth>4 || b->scene>1 || b->fault>1 || b->outcome>2 ||
        (b->call!=255 && b->call>=r->project->chi_bridge->call_count) || v->node>=a->node_count || v->phase>BTP_EVENT_PRESENTATION ||
        (!b->depth && (v->enabled || b->scene || b->call!=255 || b->fault)) || (b->depth && !s->party.enabled)) return 0;
    if (!btp_mission_valid(s,a) || !btp_battle_mission_valid(s,a)) return 0;
    for (unsigned i=a->flag_count;i<64;++i) if (v->flags[i]) return 0;
    for (unsigned i=0;i<BTP_EVENT_NODES;++i) if ((v->done[i/8]&(1u<<(i%8))) &&
        (i>=a->node_count || (a->nodes[i].op!=BTP_EVENT_REWARD && a->nodes[i].op!=BTP_EVENT_RECRUIT && a->nodes[i].op!=BTP_EVENT_SALVAGE &&
        !(a->nodes[i].op==BTP_EVENT_VARIABLE && a->nodes[i].y)))) return 0;
    for (unsigned i=0;i<8;++i) if (v->people[i]!=255 && (v->people[i]>=a->person_count ||
        (s->party.people[i][0]!=255 && a->people[v->people[i]].record[0]!=s->party.people[i][0]))) return 0;
    for (unsigned i=0;i<4;++i) {
        const BtpBridgeFrame *f=&b->frames[i];
        if (i>=b->depth) { BtpBridgeFrame zero={0};if (memcmp(f,&zero,sizeof zero)) return 0;continue; }
        if (!position_valid(&f->position,r) || f->kind<1 || f->kind>4 || f->node>=a->node_count ||
            (f->call!=255 && f->call>=r->project->chi_bridge->call_count)) return 0;
        if ((!i && f->kind!=BTP_BRIDGE_BLD && f->kind!=BTP_BRIDGE_ENTRANCE) ||
            (i && f->kind!=BTP_BRIDGE_EVENT_CALL && f->kind!=BTP_BRIDGE_NATIVE) || f->call!=255) return 0;
        if (f->kind==BTP_BRIDGE_EVENT_CALL && a->nodes[f->node].op!=BTP_EVENT_CALL) return 0;
        if (f->kind==BTP_BRIDGE_NATIVE && (a->nodes[f->node].op!=BTP_EVENT_CHI_NATIVE || i+1!=b->depth || v->enabled || b->call==255)) return 0;
        if (f->kind==BTP_BRIDGE_BLD) {
            unsigned k=f->program;if(k>=26)return 0;
            const BtpBld *p=k<8 ? btp_building_bld(r,k) : &r->buildings[k];
            if (f->position.scene || !suspended_script(&f->script,p,a->node_count) ||
                k!=(f->position.native_map ? native_map(r,f->position.native_map)->room_map[f->position.entry] : f->position.building)) return 0;
        } else { BtpScriptState zero={0};if (f->program || memcmp(&f->script,&zero,sizeof zero)) return 0; }
        if (f->kind==BTP_BRIDGE_ENTRANCE) {
            const BtpChiBridge *config=r->project->chi_bridge;unsigned j=0;
            while(j<config->binding_count && (config->bindings[j].map!=f->position.native_map || config->bindings[j].entrance!=f->position.entry))++j;
            if(f->position.scene || j==config->binding_count)return 0;
        }
    }
    if (b->scene) {
        if (!btp_npc_valid_saved(s,native_map(r,b->frames[0].position.native_map),r,&b->parked_npc) || b->native_mark_next>63) return 0;
        for (unsigned i=0;i<64;++i) {
            const BtpTerrainMark *m=&b->native_marks[i];
            if ((m->sprite && (m->sprite<124 || m->sprite>129)) || m->x>127 || m->y>127)return 0;
        }
    } else {
        BtpNpcState zero={0};if(memcmp(&b->parked_npc,&zero,sizeof zero) || b->native_mark_next)return 0;
        for(unsigned i=0;i<64;++i)if(b->native_marks[i].sprite || b->native_marks[i].sector || b->native_marks[i].x || b->native_marks[i].y)return 0;
    }
    if (b->call!=255) {
        const BtpChiCall *c=&r->project->chi_bridge->calls[b->call];
        if (!b->depth || b->frames[b->depth-1].kind!=BTP_BRIDGE_NATIVE || b->scene || v->enabled ||
            a->nodes[b->frames[b->depth-1].node].argument!=b->call ||
            !s->script.stopping || s->script.stop_pc!=c->end || s->campaign.building!=c->building || s->mode!=BTP_BUILDING) return 0;
    } else if (s->script.stopping || s->script.stop_pc) return 0;
    if (!v->enabled) return !b->scene && v->phase==BTP_EVENT_INACTIVE;
    if (s->script.pc || s->script.status || s->checkpoint_valid || s->mission.phase || s->campaign.invasion || s->cache.active || s->yard.active) return 0;
    const BtpEventNode *e=&a->nodes[v->node];
    if (b->scene) {
        const BtpScene *m=btp_scene(r,s);if (!m || s->npc.enabled || s->map_id!=(v->map<239 ? 16+v->map : 255) ||
            s->x_half>=2*m->visual.width || s->y_half>=2*m->visual.height || v->planet!=m->world || v->explore_offset!=m->explore_offset ||
            v->explore_width!=m->explore_width || v->explore_height!=m->explore_height) return 0;
    } else if (v->planet || v->explore_offset || v->explore_width || v->explore_height) return 0;
    if (v->phase==BTP_EVENT_TEXT) {
        char lines[96][28];if ((e->op!=BTP_EVENT_SAY && e->op!=BTP_EVENT_PICTURE) || v->selected ||
            (e->op==BTP_EVENT_PICTURE ? v->page!=0 : v->page*20u>=btp_event_lines(e->text,lines))) return 0;
    } else if (v->page) return 0;
    if (v->phase==BTP_EVENT_SELECT && (e->op!=BTP_EVENT_CHOICE || v->selected>=e->count)) return 0;
    if (v->phase==BTP_EVENT_PRESENTATION && (v->selected ||
        (e->op==BTP_EVENT_CHI_FILM ? s->cutscene.active!=8 || s->cutscene.kind!=e->argument : e->op!=BTP_EVENT_CHI_SOUND))) return 0;
    if (v->phase==BTP_EVENT_FIGHTING || s->battle_mission.in_hook) {
        const BtpEventNode *be=s->battle_mission.in_hook ? &a->nodes[s->battle_mission.node] : e;
        return b->scene && be->op==BTP_EVENT_BATTLE && s->campaign.encounter==5 &&
            v->map==a->battles[be->argument].map && position_valid(&b->battle_return,r) &&
            s->mode==(s->battle_mission.in_hook ? BTP_EVENT : BTP_ENCOUNTER);
    }
    if (s->combat.phase || s->campaign.encounter) return 0;
    if (v->phase==BTP_EVENT_TRADING) return e->op==BTP_EVENT_SHOP && s->mode==BTP_ACTIONS;
    return s->mode==BTP_EVENT && (v->phase==BTP_EVENT_TEXT || v->phase==BTP_EVENT_SELECT || v->phase==BTP_EVENT_FAULT || v->phase==BTP_EVENT_PRESENTATION);
}

/* Fixed little-endian tail. Never persist pointers, padding, or compiler
   layout. The same bytes are checked on Linux and Windows. */
typedef struct { uint8_t *out;const uint8_t *in;unsigned at; } Codec;
static void field(Codec *c,void *p,unsigned width)
{
    unsigned value=0;if(c->out) { if(width==1)value=*(uint8_t *)p;else if(width==2)value=*(uint16_t *)p;else value=*(uint32_t *)p; }
    for(unsigned i=0;i<width;++i) { if(c->out)c->out[c->at]=(uint8_t)(value>>(8*i));else value|=(unsigned)c->in[c->at]<<(8*i);++c->at; }
    if(!c->out) { if(width==1)*(uint8_t *)p=(uint8_t)value;else if(width==2)*(uint16_t *)p=(uint16_t)value;else *(uint32_t *)p=value; }
}
#define F(x) field(c,&(x),sizeof(x))
#define A(x) do { for(unsigned ai=0;ai<sizeof(x);++ai)field(c,(uint8_t *)(x)+ai,1); } while(0)
static void script_codec(Codec *c,BtpScriptState *s)
{
    F(s->pc);F(s->text_offset);F(s->text_length);F(s->menu_table);F(s->fault_pc);F(s->pause_units);
    F(s->status);F(s->selected);F(s->menu_id);F(s->font);F(s->scene);F(s->last_opcode);F(s->error);F(s->text_count);
    for(unsigned i=0;i<BTP_TEXT_SPANS;++i){F(s->text[i].offset);F(s->text[i].length);}
    A(s->choices);F(s->native_action);F(s->confirm_selected);F(s->confirm_target);F(s->column);F(s->row);
    A(s->text_column);A(s->text_row);F(s->has_cash);F(s->cash_after);F(s->cash_value);F(s->has_accounts);
    F(s->animation_kind);F(s->animation_flags);F(s->mech_result);F(s->mech_after);F(s->money_kind);F(s->has_position);
    F(s->money_amount);F(s->money_target);F(s->position_x);F(s->position_y);F(s->has_name);F(s->name_after);F(s->name_id);F(s->stop_pc);F(s->stopping);
}
static void position_codec(Codec *c,BtpBridgePosition *p)
{ F(p->x);F(p->y);F(p->world_x);F(p->world_y);F(p->map);F(p->native_map);F(p->scene);F(p->entry);F(p->action);F(p->building);F(p->disk); }
static void bridge_codec(Codec *c,BtpState *s)
{
    BtpBridgeState *b=&s->bridge;F(b->enabled);F(b->depth);F(b->scene);F(b->call);F(b->fault);F(b->outcome);
    F(s->script.stop_pc);F(s->script.stopping);
    for(unsigned i=0;i<4;++i){ BtpBridgeFrame *f=&b->frames[i];F(f->kind);F(f->call);F(f->program);F(f->node);position_codec(c,&f->position);script_codec(c,&f->script); }
    position_codec(c,&b->battle_return);A(b->native_explored);A(b->quest_explored);
    BtpNpcState *n=&b->parked_npc;F(n->enabled);F(n->phase);A(n->rng);F(n->bias);F(n->fault);F(n->loop_timer);F(n->allowance_pending);F(n->search);F(n->clock);
    for(unsigned i=0;i<8;++i){F(n->actor[i].x);F(n->actor[i].y);F(n->actor[i].direction);}
    for(unsigned i=0;i<64;++i){F(b->native_marks[i].sprite);F(b->native_marks[i].sector);F(b->native_marks[i].x);F(b->native_marks[i].y);}F(b->native_mark_next);
}
#undef A
#undef F
void btp_bridge_encode(const BtpState *s,uint8_t bytes[BTP_BRIDGE_BYTES])
{
    memset(bytes,0,BTP_BRIDGE_BYTES);memcpy(bytes,"CB01",4);Codec c={.out=bytes,.at=4};
    /* The encoder only reads fields; retain one shared field-order routine. */
    bridge_codec(&c,(BtpState *)s);
}
int btp_bridge_decode(BtpState *s,const uint8_t bytes[BTP_BRIDGE_BYTES])
{
    if(memcmp(bytes,"CB01",4))return 0;
    s->bridge=(BtpBridgeState){0};Codec c={.in=bytes,.at=4};bridge_codec(&c,s);
    for(unsigned i=c.at;i<BTP_BRIDGE_BYTES;++i)if(bytes[i])return 0;
    return s->bridge.enabled==1 && s->bridge.depth<=4 && s->bridge.scene<=1 && s->bridge.fault<=1 && s->bridge.outcome<=2 && s->bridge.native_mark_next<64;
}

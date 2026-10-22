#include "core/events.h"
#include "data/project.h"
#include "core/commands.h"
#include "core/party.h"
#include "core/combat.h"
#include "core/campaign.h"
#include "core/animation.h"
#include "core/menu.h"
#include "core/roster_game.h"
#include "core/world.h"
#include "core/lua_events.h"
#include "core/authored_services.h"
#include "core/mission_state.h"
#include "core/battle_mission.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static BtpEventObserver observer;
static void *observer_context;
static BtpBattleObserver battle_observer;
static void *battle_observer_context;
void btp_events_observe(BtpEventObserver callback,void *context) { observer=callback;observer_context=context; }
void btp_events_observe_battles(BtpBattleObserver callback,void *context)
{ battle_observer=callback;battle_observer_context=context; }
unsigned btp_journal_count(const BtpState *s,const BtpResources *r)
{
    const BtpAdventure *a=btp_adventure(r);unsigned count=0;
    if (a) for (unsigned i=0;i<a->objective_count;++i) count+=btp_objective_state(s,a,i)!=BTP_OBJECTIVE_INACTIVE;
    return count;
}
void btp_journal_text(const BtpState *s,const BtpResources *r,unsigned page,char out[1024])
{
    const BtpAdventure *a=btp_adventure(r);unsigned count=btp_journal_count(s,r),at=0;
    strcpy(out,"No objectives discovered.");
    if (!a || !count) return;
    for (unsigned i=0;i<a->objective_count;++i) {
        const BtpObjective *o=&a->objectives[i];
        unsigned state=btp_objective_state(s,a,i);
        if (!state) continue;
        if (at++==page%count) { snprintf(out,1024,"%u/%u %s. %s. %s",page%count+1u,count,state==BTP_OBJECTIVE_COMPLETE ? "Complete" : state==BTP_OBJECTIVE_FAILED ? "Failed" : "Active",o->title,o->text);return; }
    }
}

const BtpAdventure *btp_adventure(const BtpResources *r)
{ return r->project && r->project->adventure.loaded ? &r->project->adventure : NULL; }
const BtpScene *btp_scene(const BtpResources *r,const BtpState *s)
{
    const BtpAdventure *a=btp_adventure(r);
    unsigned map=s->event.map;
    return a && s->event.enabled && map<a->map_count ? &a->maps[map] : NULL;
}
static void aliases(BtpState *s)
{
    const uint8_t *p=s->party.people[0];
    memcpy(s->skills,p+4,3);memcpy(s->mech_skills,p+7,2);
    s->technician=p[9];s->weapon=p[11];s->armor=p[13];s->armor_points=p[14];
    s->campaign.mounted=(uint8_t)(p[12]<4);s->campaign.owned=(uint8_t)(btp_broker_count(s)!=0);
}
static void position(BtpState *s,const BtpScene *m,unsigned map,unsigned x,unsigned y)
{
    /* Planet maps may reuse coordinates. Clear only the transient debris
       cache when travelling between them; discovery has separate bit ranges. */
    if (s->event.planet!=m->world) { memset(s->terrain_marks,0,sizeof s->terrain_marks);s->terrain_next=0; }
    s->event.planet=(uint8_t)m->world;s->event.explore_offset=(uint16_t)m->explore_offset;
    s->event.explore_width=(uint8_t)m->explore_width;s->event.explore_height=(uint8_t)m->explore_height;
    s->event.map=(uint16_t)map;
    s->map_id=(uint8_t)(map<239 ? BTP_AUTHORED_MAP_FIRST+map : 255);s->x_half=(uint16_t)x;s->y_half=(uint16_t)y;
    s->campaign.world_x=(uint16_t)(2*m->origin_x+x);s->campaign.world_y=(uint16_t)(2*m->origin_y+y);
}
static int place(BtpState *s,const BtpResources *r,unsigned map,unsigned x,unsigned y)
{
    const BtpAdventure *a=btp_adventure(r);const BtpScene *m=&a->maps[map];BtpState candidate=*s;
    if (m->world) {
        unsigned wx=2*m->origin_x+x,wy=2*m->origin_y+y;
        int at=btp_adventure_world_at(a,m->world,(int)(wx/2),(int)(wy/2));if (at<0) return 0;
        map=(unsigned)at;m=&a->maps[map];x=wx-2*m->origin_x;y=wy-2*m->origin_y;
    }
    position(&candidate,m,map,x,y);
    if (!btp_party_can_stand(&candidate,r,candidate.campaign.world_x,candidate.campaign.world_y)) return 0;
    *s=candidate;s->mode=BTP_EXPLORE;btp_party_recover(s,r,1);btp_world_reveal(s);return 1;
}
static int battle(BtpState *s,const BtpResources *r,const BtpSceneBattle *b)
{
    BtpState candidate=*s;unsigned old_map=s->map_id,old_x=s->x_half,old_y=s->y_half;
    unsigned back=s->event.map;
    /* Battles retain a finite local tactical map even when its city is also
       placed over the world. Return uses the independent 16-bit scene ID. */
    position(&candidate,&btp_adventure(r)->maps[b->map],b->map,b->x,b->y);
    if (!btp_party_can_stand(&candidate,r,candidate.campaign.world_x,candidate.campaign.world_y)) return 0;
    candidate.mode=BTP_EXPLORE;btp_party_recover(&candidate,r,1);
    btp_campaign_begin(&candidate,r,5);
    const BtpScene *m=&btp_adventure(r)->maps[b->map];BtpCampaignState *v=&candidate.campaign;BtpCombatState *c=&candidate.combat;
    v->return_map=(uint8_t)old_map;v->return_x=(uint16_t)old_x;v->return_y=(uint16_t)old_y;
    candidate.event.return_map=(uint16_t)back;
    v->battle_x=(uint16_t)(2*m->origin_x);v->battle_y=(uint16_t)(2*m->origin_y);
    unsigned mech=0,person=0;
    for (unsigned i=0;i<c->friends;++i) {
        BtpCombatUnit *u=&c->unit[i];unsigned at=u->infantry ? person++ : mech++;
        u->x=(uint8_t)((int)b->x+(u->infantry ? r->combat.formation_x[at] : r->combat.mech_formation_x[at]));
        u->y=(uint8_t)((int)b->y+(u->infantry ? r->combat.formation_y[at] : r->combat.mech_formation_y[at]));
    }
    mech=person=0;
    for (unsigned i=0;i<b->count;++i) {
        const BtpSceneEnemy *e=&b->enemies[i];
        for (unsigned k=0;k<c->friends;++k) if (abs((int)e->x-c->unit[k].x)<3 && abs((int)e->y-c->unit[k].y)<3) return 0;
        unsigned slot=c->count++;BtpCombatUnit *u=&c->unit[slot];u->x=e->x;u->y=e->y;u->direction=6;u->infantry=e->infantry;
        if (e->infantry) { memcpy(u->record,btp_adventure(r)->people[e->definition].record,17);c->ids[slot]=(uint8_t)(16+person++); }
        else { memcpy(u->record,r->roster.mechs[e->definition].record,125);c->ids[slot]=(uint8_t)(12+mech++); }
        c->plan_direction[slot]=255;
    }
    candidate.x_half=c->unit[0].x;candidate.y_half=(uint16_t)(c->unit[0].y+(c->unit[0].infantry ? 0u : 2u));
    candidate.event.phase=BTP_EVENT_FIGHTING;
    if (!btp_battle_mission_begin(&candidate,r,(unsigned)(b-btp_adventure(r)->battles))) return 0;
    *s=candidate;return 1;
}
static void advance(BtpState *s,unsigned node)
{ s->event.node=(uint16_t)node;s->event.selected=s->event.page=0;s->event.phase=BTP_EVENT_INACTIVE; }
static void run(BtpState *s,const BtpResources *r)
{
    const BtpAdventure *a=btp_adventure(r);BtpEventState *v=&s->event;
    /* Bounded synchronous commands. Pure-branch cycles fault visibly instead
       of hanging the player/editor; all UI and combat yield explicitly. */
    for (unsigned budget=0;budget<64;++budget) {
        const BtpEventNode *e=&a->nodes[v->node];unsigned n=v->node;
        unsigned done=v->done[n/8u]&(1u<<(n%8u)),target=e->next[0];
        if (observer) observer(observer_context,s,r,e);
        s->mode=BTP_EVENT;
        switch (e->op) {
        case BTP_EVENT_REINFORCE:
            if (!btp_battle_reinforce(s,r,e->argument,e->value)) target=e->next[1];
            break;
        case BTP_EVENT_BATTLE_END:
            if (!s->battle_mission.active || !s->battle_mission.in_hook ||
                (s->battle_mission.outcome && s->battle_mission.outcome!=e->value+1 && e->value!=1)) target=e->next[1];
            else s->battle_mission.outcome=(uint8_t)(e->value+1);
            break;
        case BTP_EVENT_CHECK:target=e->next[btp_mission_check(s,a,e) ? 0 : 1];break;
        case BTP_EVENT_OBJECTIVE:if (!btp_mission_objective(s,a,e)) target=e->next[1];break;
        case BTP_EVENT_VARIABLE:
            if (!e->y || !done) {
                if (!btp_mission_variable(s,a,e)) target=e->next[1];
                else if (e->y) v->done[n/8u]|=(uint8_t)(1u<<(n%8u));
            }
            break;
        case BTP_EVENT_REPAIR:case BTP_EVENT_REARM:case BTP_EVENT_HEAL:case BTP_EVENT_SALVAGE: {
            unsigned outcome=e->op==BTP_EVENT_SALVAGE && done ? 2u : btp_authored_service(s,r,e);
            if (!outcome && e->op==BTP_EVENT_SALVAGE) v->done[n/8u]|=(uint8_t)(1u<<(n%8u));
            target=e->next[outcome];break;
        }
        case BTP_EVENT_FINISH:v->phase=BTP_EVENT_TEXT;return;
        case BTP_EVENT_LUA: {
            char error[256];
            if (!btp_lua_event(r,s,&target,error)) { fprintf(stderr,"%s\n",error);target=e->next[5]; }break;
        }
        case BTP_EVENT_END:
            if (s->battle_mission.in_hook) {
                /* Resume the saved battle instruction, never a C/Lua stack.
                   Other queued hooks are dispatched on subsequent ticks. */
                s->battle_mission.in_hook=0;advance(s,s->battle_mission.node);
                v->phase=BTP_EVENT_FIGHTING;s->mode=BTP_ENCOUNTER;return;
            }
            target=btp_mission_trigger(s,a);
            if (target<BTP_EVENT_NODES) break;
            v->phase=BTP_EVENT_INACTIVE;s->mode=(uint8_t)(s->party.people[0][0]==255 ? BTP_GAME_OVER : BTP_EXPLORE);btp_party_recover(s,r,1);return;
        case BTP_EVENT_SAY:case BTP_EVENT_PICTURE:v->phase=BTP_EVENT_TEXT;return;
        case BTP_EVENT_CHOICE:v->phase=BTP_EVENT_SELECT;return;
        case BTP_EVENT_IF:target=e->next[v->flags[e->argument]==e->value ? 0 : 1];break;
        case BTP_EVENT_FLAG:v->flags[e->argument]=(uint8_t)e->value;break;
        case BTP_EVENT_REWARD:
            if (!done) {
                if (!btp_grant_credits(s,e->value)) { target=e->next[1];break; }
                v->done[n/8u]|=(uint8_t)(1u<<(n%8u));
            }break;
        case BTP_EVENT_RECRUIT:
            if (!done) {
                int slot=btp_recruit_person(s,a->people[e->argument].record);
                if (!slot) { target=e->next[1];break; }
                v->people[(unsigned)slot-1u]=(uint8_t)e->argument;v->done[n/8u]|=(uint8_t)(1u<<(n%8u));
            }break;
        case BTP_EVENT_TRANSFER:
            if (!place(s,r,e->argument,e->x,e->y)) target=e->next[1];
            break;
        case BTP_EVENT_SHOP:v->phase=BTP_EVENT_TRADING;btp_broker_open(s);return;
        case BTP_EVENT_BATTLE:if (battle(s,r,&a->battles[e->argument])) return;target=e->next[3];break;
        }
        advance(s,target);
    }
    s->mode=BTP_EVENT;v->phase=BTP_EVENT_FAULT;
}
static void initialize(BtpState *s,const BtpResources *r,int preview,const uint8_t seed[3])
{
    const BtpAdventure *a=btp_adventure(r);if (!a) return;
    s->event=(BtpEventState){.enabled=1,.node=(uint16_t)a->start_event,.origin_map=(uint16_t)a->start_map,.origin_entry=255};
    btp_mission_initialize(s,a);
    s->battle_mission=(BtpBattleMissionState){0};
    if (a->combat_missions) s->battle_mission=(BtpBattleMissionState){.enabled=1,.encounter=255};
    memset(s->event.people,255,8);s->npc=(BtpNpcState){.rng={31,66,171}};
    if(seed)memcpy(s->npc.rng,seed,3);
    s->story_flags[4]=1;s->credits=a->credits;memset(s->explored,0,sizeof s->explored);
    btp_party_init(s);memset(s->party.people,0,sizeof s->party.people);
    for (unsigned i=0;i<8;++i) s->party.people[i][0]=255;
    unsigned bay=0;
    for (unsigned i=0;i<a->party_count;++i) {
        memcpy(s->party.people[i],a->people[a->party[i]].record,17);s->event.people[i]=a->party[i];
        if (a->mechs[i]<256) {
            uint8_t *m=btp_party_mech(s,bay);memcpy(m,r->roster.mechs[a->mechs[i]].record,125);
            s->party.mech_types[bay]=m[0];m[121]=(uint8_t)i;m[122]=255;s->party.people[i][12]=(uint8_t)bay++;
        }
    }
    aliases(s);position(s,&a->maps[a->start_map],a->start_map,a->start_x,a->start_y);
    s->mode=BTP_EXPLORE;
    if (!place(s,r,a->start_map,a->start_x,a->start_y)) { s->mode=BTP_EVENT;s->event.phase=BTP_EVENT_FAULT;return; }
    if (!preview) run(s,r);
}
void btp_events_start(BtpState *s,const BtpResources *r) { initialize(s,r,0,NULL); }
void btp_events_start_seeded(BtpState *s,const BtpResources *r,const uint8_t seed[3]) { initialize(s,r,0,seed); }
int btp_events_preview(BtpState *s,const BtpResources *r,const char *map,unsigned x,unsigned y)
{
    const BtpAdventure *a=btp_adventure(r);if (!a) return 0;
    unsigned i=0;while (i<a->map_count && strcmp(a->maps[i].id,map)) ++i;
    if (i==a->map_count) return 0;
    /* A fresh playtest skips start-event side effects. No normal campaign
       state or save is loaded, and the full formation must fit here. */
    initialize(s,r,1,NULL);
    if (!place(s,r,i,x,y)) { s->mode=BTP_EVENT;s->event.phase=BTP_EVENT_FAULT;return 0; }
    btp_mission_preview(s,a);
    s->event.phase=BTP_EVENT_INACTIVE;s->event.origin_map=(uint16_t)i;return 1;
}
static void result(BtpState *s,const BtpResources *r)
{
    BtpCombatState *c=&s->combat;const BtpEventNode *e=&btp_adventure(r)->nodes[s->event.node];
    unsigned next_node=e->next[c->fled ? 2 : c->lost ? 1 : 0];
    if(battle_observer)battle_observer(battle_observer_context,s,r,&btp_adventure(r)->battles[e->argument]);
    for (unsigned i=0;i<c->friends;++i) {
        unsigned id=c->ids[i];
        if (id<4) memcpy(btp_party_mech(s,id),c->unit[i].record,125);
        else if (id<12) memcpy(s->party.people[id-4],c->unit[i].record,17);
    }
    unsigned map=s->event.return_map,x=s->campaign.return_x,y=s->campaign.return_y;
    s->campaign.encounter=0;s->combat=(BtpCombatState){0};s->effects=(BtpEffectsState){0};s->aftermath=(BtpAftermathState){0};
    s->battle_mission.active=s->battle_mission.in_hook=s->battle_mission.stage=0;
    aliases(s);position(s,&btp_adventure(r)->maps[map],map,x,y);
    advance(s,next_node);run(s,r);
}
void btp_events_tick(BtpState *s,const BtpResources *r,BtpAction action)
{
    const BtpAdventure *a=btp_adventure(r);BtpEventState *v=&s->event;
    if (s->mode==BTP_GAME_OVER) { ++s->tick;return; }
    if (v->phase==BTP_EVENT_COMPLETE) { ++s->tick;if (action==BTP_ACCEPT || action==BTP_OPEN_MENU) s->menu.quit=1;return; }
    if (s->mode==BTP_ACTIONS) {
        ++s->tick;btp_menu_input(s,r,action==BTP_OPEN_MENU ? BTP_ACCEPT : action);
        if (s->mode!=BTP_ACTIONS && v->phase==BTP_EVENT_TRADING) { advance(s,a->nodes[v->node].next[0]);run(s,r); }
        return;
    }
    ++s->tick;
    if (v->phase==BTP_EVENT_FIGHTING) {
        if (s->battle_mission.active && !s->effects.count && !s->presentation.count && !s->audio.sound_count && !s->cutscene.active) {
            btp_battle_observe(s,a);
            unsigned hook=btp_battle_hook(s,a);
            if (hook<BTP_EVENT_NODES) { s->battle_mission.in_hook=1;advance(s,hook);run(s,r);return; }
        }
        btp_combat_tick(s,r,action);if (!s->combat.phase) result(s,r);return;
    }
    if (s->mode==BTP_EXPLORE) {
        if (action==BTP_OPEN_MENU || action==BTP_ACCEPT) { btp_menu_open(s);return; }
        if (!btp_action_moves(action)) return;
        unsigned previous=s->facing;s->facing=(uint8_t)action;
        s->player_walk=btp_walk_next(s->player_walk,btp_player_direction(previous),btp_player_direction((unsigned)action));
        s->campaign.mech_walk=(uint8_t)btp_combat_walk_frame(s->campaign.mech_walk,s->campaign.mech_direction,btp_player_direction((unsigned)action),0);
        s->campaign.mech_direction=(uint8_t)btp_player_direction((unsigned)action);
        uint8_t walk[8],directions[8];memcpy(walk,s->party.walk,8);memcpy(directions,s->party.direction,8);
        for (unsigned step=0;step<s->menu.steps;++step) {
            const BtpScene *m=btp_scene(r,s);unsigned map=s->event.map;
            int x=(int)s->x_half+btp_action_dx(action),y=(int)s->y_half+btp_action_dy(action);
            int wx=(int)(2*m->origin_x)+x,wy=(int)(2*m->origin_y)+y;
            if (m->world) {
                int at=btp_adventure_world_at(a,m->world,wx>=0 ? wx/2 : -1,wy>=0 ? wy/2 : -1);
                if (at<0) { s->blocked=BTP_EDGE;break; }
                map=(unsigned)at;m=&a->maps[map];x=wx-(int)(2*m->origin_x);y=wy-(int)(2*m->origin_y);
            }
            BtpState probe=*s;position(&probe,m,map,(unsigned)x,(unsigned)y);
            unsigned door_map=map;int entrance=btp_party_entrance_scene(&probe,r,&m->rules,x,y,&door_map);
            if (entrance>=0) {
                v->origin_map=(uint16_t)door_map;v->origin_entry=(uint8_t)entrance;
                advance(s,a->maps[door_map].entrances[entrance].event);v->phase=BTP_EVENT_ENTRY;s->mode=BTP_EVENT;break;
            }
            if (!btp_party_can_stand(s,r,wx,wy)) { s->blocked=BTP_WALL;break; }
            uint16_t ox=s->campaign.world_x,oy=s->campaign.world_y;
            position(s,m,map,(unsigned)x,(unsigned)y);s->blocked=BTP_CLEAR;
            btp_party_follow(s,r,ox,oy);btp_world_reveal(s);
            unsigned trigger=btp_mission_trigger(s,a);
            if (trigger<BTP_EVENT_NODES) { advance(s,trigger);run(s,r);break; }
        }
        for (unsigned i=1;i<8;++i) if (s->party.people[i][0]!=255) {
            unsigned dir=btp_player_direction((unsigned)action);
            s->party.walk[i]=s->party.people[i][12]<4 ? (uint8_t)btp_combat_walk_frame(walk[i],directions[i],dir,0) : btp_walk_next(walk[i],directions[i],dir);
            s->party.direction[i]=(uint8_t)dir;
        }
        return;
    }
    if (action==BTP_OPEN_MENU) action=BTP_ACCEPT;
    const BtpEventNode *e=&a->nodes[v->node];
    if (v->phase==BTP_EVENT_ENTRY) {
        if (action==BTP_LEFT || action==BTP_UP) v->selected=0;
        if (action==BTP_RIGHT || action==BTP_DOWN) v->selected=1;
        if (action==BTP_CANCEL || (action==BTP_ACCEPT && v->selected)) {
            v->phase=BTP_EVENT_INACTIVE;v->selected=0;s->mode=BTP_EXPLORE;
            /* DOS No resumes the interrupted wall test. The saved facing
               retains this pending half-step while the Yes/No prompt is up;
               do not re-trigger the marker or add another animation frame. */
            const BtpScene *m=btp_scene(r,s);BtpAction pending=(BtpAction)s->facing;
            int x=(int)s->x_half+btp_action_dx(pending),y=(int)s->y_half+btp_action_dy(pending);
            int wx=(int)(2*m->origin_x)+x,wy=(int)(2*m->origin_y)+y;
            if (btp_action_moves(pending) && btp_party_can_stand(s,r,wx,wy)) {
                if (m->world) {
                    int at=btp_adventure_world_at(a,m->world,wx/2,wy/2);if (at<0) return;
                    const BtpScene *target=&a->maps[at];position(s,target,(unsigned)at,(unsigned)(wx-2*(int)target->origin_x),(unsigned)(wy-2*(int)target->origin_y));
                } else position(s,m,s->event.map,(unsigned)x,(unsigned)y);
                s->blocked=BTP_CLEAR;
                btp_party_recover(s,r,1);btp_world_reveal(s);
                unsigned trigger=btp_mission_trigger(s,a);
                if (trigger<BTP_EVENT_NODES) { advance(s,trigger);run(s,r); }
            } else s->blocked=BTP_WALL;
        }
        else if (action==BTP_ACCEPT) run(s,r);
    } else if (v->phase==BTP_EVENT_TEXT && action==BTP_ACCEPT) {
        if (e->op==BTP_EVENT_PICTURE) { advance(s,e->next[0]);run(s,r);return; }
        char lines[96][28];unsigned count=btp_event_lines(e->text,lines);
        if ((v->page+1u)*20u<count) ++v->page;
        else if (e->op==BTP_EVENT_FINISH) { v->page=0;v->phase=BTP_EVENT_COMPLETE;s->mode=BTP_ENDING; }
        else { advance(s,e->next[0]);run(s,r); }
    } else if (v->phase==BTP_EVENT_SELECT) {
        if (action==BTP_UP) v->selected=(uint8_t)((v->selected+e->count-1u)%e->count);
        if (action==BTP_DOWN) v->selected=(uint8_t)((v->selected+1u)%e->count);
        if (action==BTP_ACCEPT || action==BTP_CANCEL) { advance(s,e->next[action==BTP_CANCEL ? 5 : v->selected]);run(s,r); }
    } else if (v->phase==BTP_EVENT_FAULT && action==BTP_CANCEL) {
        if (s->battle_mission.in_hook) {
            /* A faulty combat hook cannot strand a live encounter in walking
               mode. Cancel aborts this attempt through its normal loss route. */
            s->battle_mission.in_hook=0;s->battle_mission.outcome=2;
            memset(s->battle_mission.pending,0,sizeof s->battle_mission.pending);
            advance(s,s->battle_mission.node);v->phase=BTP_EVENT_FIGHTING;s->mode=BTP_ENCOUNTER;
        } else { v->phase=BTP_EVENT_INACTIVE;s->mode=BTP_EXPLORE; }
    }
}
unsigned btp_events_catalogue(const BtpState *s,const BtpResources *r,unsigned weight,unsigned limit,unsigned indices[256])
{
    unsigned count=btp_roster_catalogue(&r->roster,weight,limit,indices);
    if (!s->event.enabled || s->event.phase!=BTP_EVENT_TRADING) return count;
    unsigned out=0;for (unsigned i=0;i<count;++i) if (btp_events_stock(s,r,indices[i])) indices[out++]=indices[i];return out;
}
int btp_events_stock(const BtpState *s,const BtpResources *r,unsigned definition)
{
    const BtpAdventure *a=btp_adventure(r);
    if (!a || !s->event.enabled || s->event.phase!=BTP_EVENT_TRADING || s->event.node>=a->node_count) return 0;
    const BtpEventNode *e=&a->nodes[s->event.node];if (e->op!=BTP_EVENT_SHOP) return 0;
    const BtpSceneShop *shop=&a->shops[e->argument];
    for (unsigned i=0;i<shop->count;++i) if (shop->stock[i]==definition) return 1;
    return 0;
}
void btp_events_encode(const BtpState *s,uint8_t b[128])
{
    const BtpEventState *v=&s->event;memset(b,0,128);
    b[0]=v->enabled;b[1]=v->phase;b[2]=(uint8_t)v->node;b[3]=(uint8_t)(v->node>>8);
    b[4]=v->selected;b[5]=v->page;b[6]=(uint8_t)v->origin_map;b[7]=v->origin_entry;
    memcpy(b+8,v->flags,64);memcpy(b+72,v->done,32);memcpy(b+104,v->people,8);
    b[112]=(uint8_t)v->map;b[113]=(uint8_t)(v->map>>8);
    b[114]=(uint8_t)v->return_map;b[115]=(uint8_t)(v->return_map>>8);
    b[116]=(uint8_t)(v->origin_map>>8);b[127]=2;
    b[117]=(uint8_t)v->explore_offset;b[118]=(uint8_t)(v->explore_offset>>8);
    b[119]=v->explore_width;b[120]=v->explore_height;b[121]=v->planet;
}
int btp_events_decode(BtpState *s,const uint8_t b[128])
{
    BtpEventState *v=&s->event;
    *v=(BtpEventState){.enabled=b[0],.phase=b[1],.node=(uint16_t)(b[2]|(unsigned)b[3]<<8),.selected=b[4],.page=b[5],.origin_map=b[6],.origin_entry=b[7]};
    memcpy(v->flags,b+8,64);memcpy(v->done,b+72,32);memcpy(v->people,b+104,8);
    if (b[127]>2) return 0;
    if (b[127]) {
        v->map=(uint16_t)(b[112]|(unsigned)b[113]<<8);v->return_map=(uint16_t)(b[114]|(unsigned)b[115]<<8);v->origin_map|=(uint16_t)((unsigned)b[116]<<8);
    }
    if (b[127]==2) {
        v->explore_offset=(uint16_t)(b[117]|(unsigned)b[118]<<8);v->explore_width=b[119];v->explore_height=b[120];v->planet=b[121];
        if (v->planet>BTP_WORLDS || v->explore_width>128 || v->explore_height>128 || v->explore_offset+(unsigned)v->explore_width*v->explore_height>16384) return 0;
    }
    for (unsigned i=b[127]==2 ? 122u : b[127] ? 117u : 112u;i<127;++i) if (b[i]) return 0;
    for (unsigned i=0;i<64;++i) if (v->flags[i]>1) return 0;
    return v->enabled==1 && v->phase<=BTP_EVENT_COMPLETE && v->node<BTP_EVENT_NODES && v->selected<6 && v->page<5 &&
        v->origin_map<BTP_SCENES && v->map<BTP_SCENES && v->return_map<BTP_SCENES;
}
int btp_events_valid(const BtpState *s,const BtpResources *r)
{
    const BtpAdventure *a=btp_adventure(r);const BtpEventState *v=&s->event;
    if (!v->enabled) return !a;
    if (!a || !s->project || !btp_scene(r,s) || v->node>=a->node_count || v->origin_map>=a->map_count ||
        (v->origin_entry!=255 && v->origin_entry>=a->maps[v->origin_map].entrance_count) || !s->party.enabled || s->npc.enabled ||
        s->campaign.invasion || s->cache.active || s->yard.active || s->checkpoint_valid || s->script.status ||
        s->script.pc || s->mission.phase || s->campaign.building || s->entry_slot) return 0;
    if (!btp_mission_valid(s,a) || !btp_battle_mission_valid(s,a)) return 0;
    for (unsigned i=a->flag_count;i<64;++i) if (v->flags[i]) return 0;
    for (unsigned i=0;i<BTP_EVENT_NODES;++i) if ((v->done[i/8u]&(1u<<(i%8u))) &&
        (i>=a->node_count || (a->nodes[i].op!=BTP_EVENT_REWARD && a->nodes[i].op!=BTP_EVENT_RECRUIT && a->nodes[i].op!=BTP_EVENT_SALVAGE &&
         !(a->nodes[i].op==BTP_EVENT_VARIABLE && a->nodes[i].y)))) return 0;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 &&
        (v->people[i]>=a->person_count || a->people[v->people[i]].record[0]!=s->party.people[i][0])) return 0;
    const BtpEventNode *e=&a->nodes[v->node];
    const BtpScene *scene=btp_scene(r,s);
    if (s->campaign.ui==BTP_MENU_JOURNAL && s->campaign.member>=(btp_journal_count(s,r) ? btp_journal_count(s,r) : 1u)) return 0;
    if (v->planet!=scene->world || v->explore_offset!=scene->explore_offset || v->explore_width!=scene->explore_width || v->explore_height!=scene->explore_height) return 0;
    if (s->map_id!=(v->map<239 ? BTP_AUTHORED_MAP_FIRST+v->map : 255)) return 0;
    if (s->x_half>=2*scene->visual.width || s->y_half>=2*scene->visual.height) return 0;
    if (v->phase==BTP_EVENT_FIGHTING || s->battle_mission.in_hook) {
        const BtpEventNode *battle_node=s->battle_mission.in_hook ? &a->nodes[s->battle_mission.node] : e;
        if (battle_node->op!=BTP_EVENT_BATTLE || (s->mode!=BTP_ENCOUNTER && !(s->battle_mission.in_hook && s->mode==BTP_EVENT)) || s->campaign.encounter!=5 ||
            v->return_map>=a->map_count || v->map!=a->battles[battle_node->argument].map ||
            s->campaign.battle_x!=2*scene->origin_x || s->campaign.battle_y!=2*scene->origin_y) return 0;
        const BtpScene *back=&a->maps[v->return_map];
        if (s->campaign.return_x>=2*back->visual.width || s->campaign.return_y>=2*back->visual.height) return 0;
    } else if (s->campaign.encounter || s->combat.phase) return 0;
    if (v->phase==BTP_EVENT_TRADING && (e->op!=BTP_EVENT_SHOP || s->mode!=BTP_ACTIONS || !btp_broker_page(s->campaign.ui))) return 0;
    if (v->phase==BTP_EVENT_TEXT) {
        char lines[96][28];if (e->op==BTP_EVENT_PICTURE) { if (v->page || v->selected) return 0; }
        else if ((e->op!=BTP_EVENT_SAY && e->op!=BTP_EVENT_FINISH) || v->page*20u>=btp_event_lines(e->text,lines) || v->selected) return 0;
    } else if (v->page) return 0;
    if (v->phase==BTP_EVENT_SELECT && (e->op!=BTP_EVENT_CHOICE || v->selected>=e->count)) return 0;
    if (v->phase==BTP_EVENT_ENTRY && (v->selected>1 || v->origin_entry==255 || a->maps[v->origin_map].entrances[v->origin_entry].event!=v->node)) return 0;
    if ((v->phase==BTP_EVENT_COMPLETE)!=(s->mode==BTP_ENDING) || (v->phase==BTP_EVENT_COMPLETE && e->op!=BTP_EVENT_FINISH)) return 0;
    if ((v->phase==BTP_EVENT_ENTRY || v->phase==BTP_EVENT_TEXT || v->phase==BTP_EVENT_SELECT || v->phase==BTP_EVENT_FAULT)!=(s->mode==BTP_EVENT)) return 0;
    return 1;
}

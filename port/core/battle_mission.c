#include "core/battle_mission.h"
#include "core/combat.h"
#include "data/unit_data.h"
#include <stdlib.h>
#include <string.h>

/* Stable identities are allocated once, including reserves. Empty reserve
   records cannot fight or occupy terrain, and are never recycled casualties. */
static unsigned first_id(const BtpAdventure *a,unsigned group)
{
    unsigned battle=a->groups[group].battle,id=12+a->battles[battle].count;
    for (unsigned i=0;i<group;++i) if (a->groups[i].battle==battle) id+=a->groups[i].count;
    return id;
}
static unsigned group_for(const BtpAdventure *a,unsigned battle,unsigned id)
{
    for (unsigned i=0;i<a->group_count;++i) if (a->groups[i].battle==battle) {
        unsigned first=first_id(a,i);
        if (id>=first && id<first+a->groups[i].count) return i;
    }
    return BTP_COMBAT_GROUPS;
}
unsigned btp_battle_side(const BtpState *s,const BtpAdventure *a,unsigned index)
{
    (void)a;
    if (index<s->combat.friends) return BTP_SIDE_FRIENDLY;
    unsigned id=btp_combat_id(&s->combat,index);
    return s->battle_mission.active && id>=12 && id<24 ? s->battle_mission.sides[id-12] : BTP_SIDE_HOSTILE;
}
int btp_battle_hostile(const BtpState *s,unsigned actor,unsigned target)
{
    if (!s->battle_mission.active) {
        unsigned friends=s->combat.friends ? s->combat.friends : 1u;
        return (actor<friends)!=(target<friends);
    }
    unsigned from=btp_battle_side(s,NULL,actor),to=btp_battle_side(s,NULL,target);
    return from==BTP_SIDE_HOSTILE ? to!=BTP_SIDE_HOSTILE : from==BTP_SIDE_FRIENDLY && to==BTP_SIDE_HOSTILE;
}
unsigned btp_battle_hostiles(const BtpState *s)
{
    unsigned count=0;
    for (unsigned i=s->combat.friends;i<s->combat.count;++i)
        if (s->combat.unit[i].record[0]!=255 && btp_battle_side(s,NULL,i)==BTP_SIDE_HOSTILE) ++count;
    return count;
}
static BtpCombatUnit actor_unit(const BtpResources *r,const BtpMissionActor *actor)
{
    const BtpSceneEnemy *e=&actor->unit;BtpCombatUnit unit={.x=e->x,.y=e->y,.direction=6,.infantry=e->infantry};
    if (e->infantry) memcpy(unit.record,btp_adventure(r)->people[e->definition].record,17);
    else {
        memcpy(unit.record,r->roster.mechs[e->definition].record,125);
        /* Mission actors have no ownership/pilot alias into the player's party. */
        unit.record[121]=unit.record[122]=255;
    }
    return unit;
}
static int vacant(const BtpState *s,const BtpScene *scene,const BtpCombatUnit *u,int x,int y)
{
    if (!btp_scene_stand(scene,x,y,!u->infantry)) return 0;
    unsigned vehicle=u->infantry ? 0u : btp_vehicle_kind(u->record);
    if (vehicle && (!btp_vehicle_terrain(vehicle,btp_map_tile(&scene->rules,x/2,y/2)) ||
        !btp_vehicle_terrain(vehicle,btp_map_tile(&scene->rules,x/2+1,y/2)))) return 0;
    for (unsigned i=0;i<s->combat.count;++i) {
        const BtpCombatUnit *other=&s->combat.unit[i];
        if (other->record[0]!=255 && y==other->y && abs(x-other->x)<1+!u->infantry+!other->infantry) return 0;
    }
    return 1;
}
int btp_battle_reinforce(BtpState *s,const BtpResources *r,unsigned group,unsigned radius)
{
    const BtpAdventure *a=btp_adventure(r);BtpBattleMissionState *m=&s->battle_mission;
    if (!a || !m->active || group>=a->group_count || radius>8 ||
        a->groups[group].battle!=m->encounter || (m->deployed&(1u<<group))) return 0;
    const BtpCombatGroup *g=&a->groups[group];const BtpScene *scene=&a->maps[a->battles[g->battle].map];
    /* Stage every unit in a copy so a blocked final spawn cannot leave a
       partially deployed wave. No RNG draws or mutable script stack involved. */
    BtpState *candidate=malloc(sizeof *candidate);if (!candidate) return 0;*candidate=*s;
    unsigned first=first_id(a,group);int ok=1;
    for (unsigned i=0;i<g->count && ok;++i) {
        BtpCombatUnit u=actor_unit(r,&g->actors[i]);unsigned slot=btp_combat_target(&candidate->combat,first+i);int found=0;
        if (slot>=candidate->combat.count) { ok=0;break; }
        for (int distance=0;distance<=(int)radius && !found;++distance)
            for (int dy=-distance;dy<=distance && !found;++dy) for (int dx=-distance;dx<=distance && !found;++dx) {
                if (abs(dx)!=distance && abs(dy)!=distance) continue;
                int x=(int)u.x+dx,y=(int)u.y+dy;
                if (vacant(candidate,scene,&u,x,y)) {
                    u.x=(uint8_t)x;u.y=(uint8_t)y;candidate->combat.unit[slot]=u;
                    candidate->battle_mission.units[first+i-12]=1;found=1;
                }
            }
        if (!found) ok=0;
    }
    if (ok) { candidate->battle_mission.deployed|=(uint16_t)(1u<<group);*s=*candidate; }
    free(candidate);return ok;
}
void btp_battle_signal(BtpState *s,const BtpAdventure *a,unsigned when,unsigned group)
{
    BtpBattleMissionState *m=&s->battle_mission;if (!m->active) return;
    for (unsigned i=0;i<a->hook_count;++i) {
        const BtpCombatHook *h=&a->hooks[i];
        if (h->battle!=m->encounter || h->when!=when ||
            (h->group<BTP_COMBAT_GROUPS && h->group!=group) || (!h->repeat && (m->fired&(UINT32_C(1)<<i)))) continue;
        if ((when==BTP_HOOK_ROUND_START || when==BTP_HOOK_ROUND_END) &&
            (m->round<h->first || (h->every ? (m->round-h->first)%h->every!=0 : m->round!=h->first))) continue;
        /* A microstep can destroy up to 24 units. Dispatch drains completely
           before another simulation boundary, keeping this queue bounded. */
        if (m->pending[i]<24) ++m->pending[i];
    }
}
int btp_battle_mission_begin(BtpState *s,const BtpResources *r,unsigned battle)
{
    const BtpAdventure *a=btp_adventure(r);if (!a->combat_missions) return 1;
    s->battle_mission=(BtpBattleMissionState){.enabled=1,.active=1,.encounter=(uint8_t)battle,.node=s->event.node};
    BtpCombatState *c=&s->combat;
    for (unsigned i=c->friends;i<c->count;++i) {
        unsigned id=12+i-c->friends;c->ids[i]=(uint8_t)id;s->battle_mission.units[id-12]=1;
        if (!c->unit[i].infantry) c->unit[i].record[121]=c->unit[i].record[122]=255;
    }
    for (unsigned i=0;i<a->group_count;++i) if (a->groups[i].battle==battle) {
        const BtpCombatGroup *g=&a->groups[i];unsigned first=first_id(a,i);
        for (unsigned j=0;j<g->count;++j) {
            if (c->count>=BTP_COMBAT_UNITS) return 0;
            unsigned slot=c->count++;c->unit[slot]=actor_unit(r,&g->actors[j]);c->unit[slot].record[0]=255;
            c->ids[slot]=(uint8_t)(first+j);c->plan_direction[slot]=255;
            s->battle_mission.sides[first+j-12]=(uint8_t)g->side;
        }
    }
    for (unsigned i=0;i<a->group_count;++i) if (a->groups[i].battle==battle && !a->groups[i].reserve)
        if (!btp_battle_reinforce(s,r,i,0)) return 0;
    btp_battle_signal(s,a,BTP_HOOK_START,BTP_COMBAT_GROUPS);return 1;
}
unsigned btp_battle_group_value(const BtpState *s,const BtpAdventure *a,unsigned group,unsigned kind)
{
    const BtpBattleMissionState *m=&s->battle_mission;
    if (!m->enabled || group>=a->group_count || a->groups[group].battle!=m->encounter) return 0;
    if (kind==BTP_CONDITION_GROUP_DEPLOYED) return (m->deployed>>group)&1u;
    unsigned count=0,first=first_id(a,group)-12;
    for (unsigned i=0;i<a->groups[group].count;++i) {
        unsigned value=m->units[first+i];
        if (kind==BTP_CONDITION_GROUP_ALIVE ? value==1 || value==3 :
            kind==BTP_CONDITION_GROUP_DESTROYED ? value==2 : value==3) ++count;
    }
    return count;
}
void btp_battle_observe(BtpState *s,const BtpAdventure *a)
{
    BtpBattleMissionState *m=&s->battle_mission;if (!m->active) return;
    for (unsigned i=0;i<s->combat.count;++i) {
        unsigned id=btp_combat_id(&s->combat,i),group=group_for(a,m->encounter,id);
        if (id>=24) continue;
        if (s->combat.unit[i].record[0]==255 && !(m->seen_dead&(UINT32_C(1)<<id)) &&
            (id<12 || m->units[id-12]==1 || m->units[id-12]==3)) {
            m->seen_dead|=UINT32_C(1)<<id;if (id>=12) m->units[id-12]=2;
            btp_battle_signal(s,a,BTP_HOOK_DESTROYED,group);
        }
        if (id>=12 && m->units[id-12]==1 && group<BTP_COMBAT_GROUPS) {
            const BtpMissionActor *actor=&a->groups[group].actors[id-first_id(a,group)];
            unsigned step=m->waypoint[id-12];
            while (step<actor->waypoint_count && s->combat.unit[i].x==actor->waypoints[step][0] &&
                s->combat.unit[i].y==actor->waypoints[step][1]) ++step;
            m->waypoint[id-12]=(uint8_t)step;
            if (actor->waypoint_count && step==actor->waypoint_count) {
                /* Arriving does not despawn a transport or make it immortal.
                   Authors can finish combat or require continued survival. */
                m->units[id-12]=3;btp_battle_signal(s,a,BTP_HOOK_ARRIVAL,group);
            }
        }
    }
}
unsigned btp_battle_hook(BtpState *s,const BtpAdventure *a)
{
    BtpBattleMissionState *m=&s->battle_mission;
    for (unsigned i=0;i<a->hook_count;++i) if (m->pending[i]) {
        --m->pending[i];
        if (!a->hooks[i].repeat && (m->fired&(UINT32_C(1)<<i))) continue;
        m->fired|=UINT32_C(1)<<i;return a->hooks[i].event;
    }
    return BTP_EVENT_NODES;
}
int btp_battle_actor_plan(BtpState *s,const BtpResources *r,const BtpMap *map,unsigned index)
{
    const BtpAdventure *a=btp_adventure(r);BtpCombatState *c=&s->combat;
    unsigned id=btp_combat_id(c,index),group=group_for(a,s->battle_mission.encounter,id);
    if (group==BTP_COMBAT_GROUPS || a->groups[group].side==BTP_SIDE_HOSTILE) return 0;
    const BtpMissionActor *actor=&a->groups[group].actors[id-first_id(a,group)];
    unsigned step=s->battle_mission.waypoint[id-12];
    if (!actor->waypoint_count && a->groups[group].side==BTP_SIDE_FRIENDLY) return 0; /* ordinary allied guard */
    uint8_t *mode=index==1 ? &c->enemy_movement : &c->enemy_modes[index-2];*mode=255;
    memset(c->enemy_orders[index-1],255,12);memset(c->path[index],2,sizeof c->path[index]);
    if (step<actor->waypoint_count) {
        *mode=(uint8_t)actor->movement;
        btp_combat_plan_actor(map,s,index,actor->waypoints[step][0],actor->waypoints[step][1],*mode,c->path[index]);
    }
    /* Friendly escorts follow their route while returning fire; neutral
       transports move only. Neither is a selectable owned party member. */
    if (a->groups[group].side==BTP_SIDE_FRIENDLY) {
        unsigned target=BTP_COMBAT_UNITS,distance=UINT32_MAX;
        for (unsigned i=0;i<c->count;++i) if (btp_battle_hostile(s,index,i) && c->unit[i].record[0]!=255) {
            unsigned next=btp_combat_distance(c->unit[index].x,c->unit[index].y,c->unit[i].x,c->unit[i].y);
            if (next<distance) { distance=next;target=i; }
        }
        if (target<c->count) {
            for (unsigned i=0;i<btp_combat_weapon_count(&c->unit[index]);++i) c->enemy_orders[index-1][i]=(uint8_t)btp_combat_id(c,target);
        }
    }
    return 1;
}
int btp_battle_mission_valid(const BtpState *s,const BtpAdventure *a)
{
    const BtpBattleMissionState *m=&s->battle_mission;
    if (m->enabled!=a->combat_missions || m->active>1 || m->in_hook>1 || m->stage>2 || m->outcome>3) return 0;
    if (!m->enabled) { BtpBattleMissionState zero={0};return !memcmp(m,&zero,sizeof zero); }
    if (m->encounter==255) {
        BtpBattleMissionState empty={.enabled=1,.encounter=255};return !memcmp(m,&empty,sizeof empty);
    }
    if (m->encounter>=a->battle_count || m->node>=a->node_count ||
        a->nodes[m->node].op!=BTP_EVENT_BATTLE || a->nodes[m->node].argument!=m->encounter ||
        (m->in_hook && !m->active) || (!m->active && m->stage)) return 0;
    unsigned total=a->battles[m->encounter].count;
    uint16_t groups=0;uint32_t hooks=0;
    for (unsigned i=0;i<a->group_count;++i) if (a->groups[i].battle==m->encounter) { total+=a->groups[i].count;groups|=(uint16_t)(1u<<i); }
    for (unsigned i=0;i<32;++i) {
        if (i<a->hook_count && a->hooks[i].battle==m->encounter) hooks|=UINT32_C(1)<<i;
        if (m->pending[i]>24 || (!(hooks&(UINT32_C(1)<<i)) && m->pending[i])) return 0;
    }
    if (m->deployed&~groups || m->fired&~hooks || m->seen_dead&UINT32_C(0xff000000)) return 0;
    for (unsigned i=0;i<12;++i) {
        unsigned group=group_for(a,m->encounter,12+i);
        if (m->units[i]>3 || m->sides[i]!=(group<BTP_COMBAT_GROUPS ? a->groups[group].side : 0u) ||
            (i>=total && (m->units[i] || m->waypoint[i]))) return 0;
        if (group<BTP_COMBAT_GROUPS) {
            unsigned member=i+12-first_id(a,group);
            if (m->waypoint[i]>a->groups[group].actors[member].waypoint_count ||
                (!!m->units[i]!=!!(m->deployed&(1u<<group)))) return 0;
        } else if (m->waypoint[i]) return 0;
        if (m->active && i<total) {
            unsigned slot=btp_combat_target(&s->combat,12+i);if (slot>=s->combat.count) return 0;
            if ((m->units[i]==0 || m->units[i]==2) && s->combat.unit[slot].record[0]!=255) return 0;
        }
    }
    return !m->active || m->round==s->combat.round;
}
static void put32(uint8_t *b,uint32_t v) { for (unsigned i=0;i<4;++i) b[i]=(uint8_t)(v>>(8*i)); }
static uint32_t get32(const uint8_t *b) { return b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24; }
void btp_battle_mission_encode(const BtpState *s,uint8_t b[BTP_BATTLE_MISSION_BYTES])
{
    const BtpBattleMissionState *m=&s->battle_mission;memset(b,0,BTP_BATTLE_MISSION_BYTES);
    b[0]=1;b[1]=m->active;b[2]=m->in_hook;b[3]=m->encounter;b[4]=m->stage;b[5]=m->outcome;
    b[6]=(uint8_t)m->node;b[7]=(uint8_t)(m->node>>8);b[8]=(uint8_t)m->round;b[9]=(uint8_t)(m->round>>8);
    b[10]=(uint8_t)m->deployed;b[11]=(uint8_t)(m->deployed>>8);put32(b+12,m->fired);put32(b+16,m->seen_dead);
    memcpy(b+20,m->pending,32);memcpy(b+52,m->units,12);memcpy(b+64,m->waypoint,12);memcpy(b+76,m->sides,12);
}
int btp_battle_mission_decode(BtpState *s,const uint8_t b[BTP_BATTLE_MISSION_BYTES])
{
    if (b[0]!=1 || b[1]>1 || b[2]>1 || b[4]>2 || b[5]>3) return 0;
    for (unsigned i=88;i<BTP_BATTLE_MISSION_BYTES;++i) if (b[i]) return 0;
    BtpBattleMissionState *m=&s->battle_mission;
    *m=(BtpBattleMissionState){.enabled=1,.active=b[1],.in_hook=b[2],.encounter=b[3],.stage=b[4],.outcome=b[5],
        .node=(uint16_t)(b[6]|(unsigned)b[7]<<8),.round=(uint16_t)(b[8]|(unsigned)b[9]<<8),.deployed=(uint16_t)(b[10]|(unsigned)b[11]<<8),
        .fired=get32(b+12),.seen_dead=get32(b+16)};
    memcpy(m->pending,b+20,32);memcpy(m->units,b+52,12);memcpy(m->waypoint,b+64,12);memcpy(m->sides,b+76,12);
    return 1;
}

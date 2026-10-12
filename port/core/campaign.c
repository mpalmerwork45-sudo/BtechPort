#include "core/campaign.h"
#include "core/party.h"
#include "core/world.h"
#include "core/combat.h"
#include "core/npc.h"
#include <string.h>
static void begin(BtpState *s,const BtpResources *r,unsigned event)
{
    BtpCampaignState *v=&s->campaign;
    v->return_map=s->map_id;v->return_x=s->x_half;v->return_y=s->y_half;
    v->battle_x=(uint16_t)(v->world_x&~127u);v->battle_y=(uint16_t)(v->world_y&~127u);v->encounter=(uint8_t)event;
    BtpCombatState *c=&s->combat;
    *c=(BtpCombatState){.phase=BTP_COMBAT_CONTROL,.selected=1,.messages=2,.graphics=1,.movement=255,.kick_target=255,.enemy_movement=255};
    memset(c->orders,255,11);memset(c->enemy_orders,255,sizeof c->enemy_orders);memset(c->enemy_modes,255,sizeof c->enemy_modes);
    btp_party_init(s);btp_party_sync(s);
    unsigned formed=0;
    for (unsigned i=0;i<4;++i) if (s->party.mech_types[i]!=255 && btp_party_mech(s,i)[0]!=255) {
        unsigned pilot=btp_party_mech(s,i)[121];
        if (pilot>=8 || s->party.people[pilot][0]==255 || s->party.people[pilot][12]!=i) continue;
        BtpCombatUnit *u=&c->unit[c->count];memcpy(u->record,btp_party_mech(s,i),125);
        u->x=(uint8_t)((v->world_x-v->battle_x+r->combat.mech_formation_x[formed])&127);u->y=(uint8_t)((v->world_y-v->battle_y+r->combat.mech_formation_y[formed])&127);c->ids[c->count++]=(uint8_t)i;++formed;
    }
    formed=0;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][12]>=8) {
        BtpCombatUnit *u=&c->unit[c->count];u->infantry=1;memcpy(u->record,s->party.people[i],17);
        /* Original 103B:01DC formations assign fresh encounter positions. */
        u->x=(uint8_t)((v->world_x-v->battle_x+r->combat.formation_x[formed])&127);u->y=(uint8_t)((v->world_y-v->battle_y+r->combat.formation_y[formed])&127);++formed;
        c->ids[c->count++]=(uint8_t)(4+i);
    }
    c->friends=c->count;c->target_unit=c->friends;c->last_target=c->friends;
    for (unsigned i=0;i<c->friends;++i) {
        c->plans[i].movement=255;c->plans[i].kick=255;memset(c->plans[i].orders,255,11);
    }
    s->mode=BTP_ENCOUNTER;s->x_half=c->unit[0].x;s->y_half=(uint16_t)(c->unit[0].y+(!c->unit[0].infantry ? 2u : 0u));
}
void btp_campaign_rex(BtpState *s,const BtpResources *r)
{
    btp_party_init(s);BtpPartyState *p=&s->party;uint8_t *rex=p->people[1];
    memset(rex,0,17);rex[0]=p->next_id++;rex[1]=12;rex[2]=9;rex[3]=8;
    memcpy(rex+4,r->combat.rex_skills,7);rex[11]=7;rex[12]=8;rex[15]=120;
    for (unsigned i=0;i<4;++i) if (p->mech_types[i]==255) {
        uint8_t *m=btp_party_mech(s,i);memcpy(m,r->combat.commando,125);m[0]=255;m[121]=1;p->mech_types[i]='C';
        if (!i) s->campaign.owned=1;
        break;
    }
    s->campaign.world_x=1385;s->campaign.world_y=1118;s->x_half=105;s->y_half=94;
    s->script.position_x=0x0a69;s->script.position_y=0x805e;
    s->campaign.mounted=0;for (unsigned i=0;i<8;++i) p->people[i][12]=8;
    begin(s,r,2);BtpCombatState *c=&s->combat;
    unsigned x=114+(btp_rng_next(s->npc.rng)&1u),y=93+(btp_rng_next(s->npc.rng)&1u);
    unsigned count=2+(btp_rng_next(s->npc.rng)&3u);
    for (unsigned i=0;i<count;++i) {
        unsigned slot=c->count++;BtpCombatUnit *u=&c->unit[slot];u->infantry=1;u->record[12]=8;
        u->x=(uint8_t)(x+r->combat.rex_x[i]);u->y=(uint8_t)(y+r->combat.rex_y[i]);u->direction=6;c->ids[slot]=(uint8_t)(16+i);
        for (unsigned k=4;k<=9;++k) u->record[k]=(uint8_t)(btp_rng_next(s->npc.rng)&1u);
        u->record[1]=(uint8_t)btp_combat_dice(s->npc.rng);u->record[15]=(uint8_t)(u->record[1]*10);
        u->record[11]=(uint8_t)(btp_rng_next(s->npc.rng)%8u);
    }
}
unsigned btp_campaign_candidates(BtpState *s,const BtpResources *r,BtpCombatUnit candidates[12],uint8_t ids[12],int *dx_out,int *dy_out)
{
    btp_party_init(s);
    int dx=10+(int)(btp_rng_next(s->npc.rng)&7u);if (btp_rng_next(s->npc.rng)&1u) dx=-dx;
    int dy=10+(int)(btp_rng_next(s->npc.rng)&7u);if (btp_rng_next(s->npc.rng)&1u) dy=-dy;
    memset(candidates,0,12*sizeof *candidates);memset(ids,0,12);unsigned count=0;
    for (unsigned i=0;i<8;++i) if (btp_rng_next(s->npc.rng)&1u) {
        BtpCombatUnit *u=&candidates[count];u->infantry=1;u->record[0]=1;u->record[12]=8;ids[count++]=(uint8_t)(16+i);
        unsigned weapon=0;for (unsigned j=0;j<7;++j) weapon+=btp_rng_next(s->npc.rng)&3u;
        u->record[11]=r->combat.encounter_weapons[weapon];
        u->record[1]=(uint8_t)btp_combat_dice(s->npc.rng);u->record[15]=(uint8_t)(10*u->record[1]);
        u->record[2]=(uint8_t)btp_combat_dice(s->npc.rng);
        for (unsigned j=4;j<=10;++j) u->record[j]=(uint8_t)(btp_rng_next(s->npc.rng)&3u);
        u->record[13]=(uint8_t)(btp_rng_next(s->npc.rng)&3u);
        u->record[14]=(uint8_t)(btp_combat_dice(s->npc.rng)+btp_combat_dice(s->npc.rng));
    }
    for (unsigned i=0;i<4;++i) if ((btp_rng_next(s->npc.rng)&1u) && btp_party_mech(s,i)[0]!=255 && s->party.mech_types[i]!=255) {
        unsigned kind=btp_rng_next(s->npc.rng)%3u;
        memcpy(candidates[count].record,r->combat.encounter_mechs[kind],125);ids[count++]=(uint8_t)(12+i);
    }
    *dx_out=dx;*dy_out=dy;return count;
}
int btp_campaign_random(BtpState *s,const BtpResources *r)
{
    BtpCombatUnit candidates[12];uint8_t ids[12];int dx,dy;
    unsigned count=btp_campaign_candidates(s,r,candidates,ids,&dx,&dy);
    if (!count) return 0;
    begin(s,r,1);BtpCombatState *c=&s->combat;
    int start_x=(int)c->unit[0].x+dx,start_y=(int)c->unit[0].y+dy,x=start_x,y=start_y,scanned=0;
    for (unsigned i=0;i<count;++i) {
        int placed=0;
        for (;scanned<17*24;++scanned,++x) {
            if (x>start_x+16) { x=start_x;++y; }
            unsigned tile=btp_world_tile(r,s,s->campaign.battle_x/2+x/2,s->campaign.battle_y/2+y/2);
            unsigned second=btp_world_tile(r,s,s->campaign.battle_x/2+x/2+1,s->campaign.battle_y/2+y/2);
            if (x>=0 && y>=2 && x<126 && y<128 && tile>15 && tile<85 &&
                (candidates[i].infantry || (second>15 && second<85))) { placed=1;break; }
        }
        if (!placed) continue;
        unsigned at=c->count++;c->unit[at]=candidates[i];c->unit[at].x=(uint8_t)x;c->unit[at].y=(uint8_t)y;c->unit[at].direction=6;c->ids[at]=ids[i];++x;++scanned;
    }
    if (c->count==c->friends) { s->mode=BTP_EXPLORE;s->x_half=s->campaign.return_x;s->y_half=s->campaign.return_y;s->campaign.encounter=0;s->combat=(BtpCombatState){0};return 0; }
    return 1;
}
void btp_campaign_result(BtpState *s,const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    if (c->phase || s->aftermath.phase) return;
    if (!s->aftermath.applied) {
    for (unsigned i=0;i<c->friends;++i) {
        unsigned id=c->ids[i];
        if (id<4) memcpy(btp_party_mech(s,id),c->unit[i].record,125);
        else if (id<12) { memcpy(s->party.people[id-4],c->unit[i].record,17);s->party.x[id-4]=(uint16_t)(s->campaign.battle_x+c->unit[i].x);s->party.y[id-4]=(uint16_t)(s->campaign.battle_y+c->unit[i].y); }
    }
        s->aftermath.applied=1;
        if (c->lost) { s->mode=BTP_GAME_OVER;return; }
        uint8_t wrecks[4][125]={{0}},marked[4]={0};
        for (unsigned i=0;i<4;++i) {
            unsigned at=btp_combat_target(c,12+i);
            if (at<c->count && s->aftermath.wrecks[12+i]) { marked[i]=1;memcpy(wrecks[i],c->unit[at].record,125); }
        }
        (void)btp_party_field_salvage(s,(const uint8_t (*)[125])wrecks,marked);
        /* 103B:0C4C calls salvage before pocket cash, including withdrawal. */
        unsigned wreck=0,empty=0;
        for (unsigned i=0;i<4;++i) { wreck|=s->aftermath.wrecks[i] || s->aftermath.wrecks[12+i];empty|=btp_party_mech(s,i)[0]==255; }
        for (unsigned i=0;i<8 && wreck && empty && !btp_world_populated(r,s);++i) if (s->party.people[i][0]!=255 && s->party.people[i][8] && s->party.people[i][12]>=8) {
            s->aftermath.pilot=(uint8_t)i;s->aftermath.phase=1;return;
        }
        s->aftermath.pilot=8;btp_aftermath_input(s,r,BTP_IDLE);if (s->aftermath.phase) return;
    }
    unsigned event=s->campaign.encounter;s->campaign.encounter=0;
    s->x_half=s->campaign.return_x;s->y_half=s->campaign.return_y;s->map_id=s->campaign.return_map;
    s->combat=(BtpCombatState){0};s->effects=(BtpEffectsState){0};
    s->aftermath=(BtpAftermathState){0};
    s->campaign.mounted=(uint8_t)(s->party.people[0][12]<4);
    s->campaign.owned=0;for (unsigned i=0;i<4;++i) s->campaign.owned|=(uint8_t)(s->party.mech_types[i]!=255);
    memcpy(s->skills,s->party.people[0]+4,3);memcpy(s->mech_skills,s->party.people[0]+7,2);
    s->technician=s->party.people[0][9];s->weapon=s->party.people[0][11];s->armor=s->party.people[0][13];s->armor_points=s->party.people[0][14];
    if (event==2) { s->mode=BTP_BUILDING;btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags); }
    else s->mode=BTP_EXPLORE;
}

unsigned btp_aftermath_cash(uint8_t rng[3],unsigned count)
{
    unsigned amount=0;for (unsigned i=0;i<count;++i) amount+=(btp_rng_next(rng)&15u)+3u;
    return amount<2 ? 2 : amount;
}
int btp_salvage_eligible(const uint8_t m[125],unsigned skill)
{
    return skill>=4 || (m[117]!=3 && m[118]!=2 && m[31]!=0);
}
void btp_salvage_copy(BtpState *s,unsigned slot,unsigned pilot,const uint8_t m[125],unsigned kind)
{
    if (slot>=4 || pilot>=8) return;
    uint8_t *dest=btp_party_mech(s,slot);memmove(dest+1,m+1,124);dest[0]=(uint8_t)kind;
    dest[121]=(uint8_t)pilot;s->party.people[pilot][12]=(uint8_t)slot;
    dest[117]=dest[118]=1;if (!dest[31]) dest[31]=1;if (!dest[32]) dest[32]=1;
    s->party.mech_types[slot]=(uint8_t)kind;s->campaign.owned=1;
}
void btp_campaign_destroy(BtpState *s,unsigned unit)
{
    BtpCombatState *c=&s->combat;BtpCombatUnit *u=&c->unit[unit];unsigned id=c->ids[unit];
    s->aftermath.wrecks[id]=(uint8_t)(u->infantry ? 128 : u->record[0]);u->record[0]=255;
    if (id<4) s->aftermath.eject|=(uint16_t)(1u<<id);
    if (id==4) s->effects.pending=2;
    for (unsigned i=0;i<c->count;++i) {
        for (unsigned j=0;j<11;++j) {
            if (c->plans[i].orders[j]==id) c->plans[i].orders[j]=255;
            if (i && c->enemy_orders[i-1][j]==id) c->enemy_orders[i-1][j]=255;
            if (c->orders[j]==id) c->orders[j]=255;
        }
        if (c->plans[i].kick==id) c->plans[i].kick=255;
        if (i && c->enemy_orders[i-1][11]==id) c->enemy_orders[i-1][11]=255;
    }
    if (c->kick_target==id) c->kick_target=255;
}
void btp_campaign_eject(BtpState *s)
{
    BtpCombatState *c=&s->combat;
    for (unsigned id=0;id<4;++id) if (s->aftermath.eject&(1u<<id)) {
        unsigned dead=btp_combat_target(c,id);if (dead>=c->count) continue;
        const BtpCombatUnit wreck=c->unit[dead];
        for (unsigned crew=0;crew<2;++crew) {
            unsigned p=wreck.record[121+crew];if (p>=8 || s->party.people[p][0]==255 || c->count>=24) continue;
            s->party.people[p][12]=8;s->party.x[p]=(uint16_t)(s->campaign.battle_x+wreck.x+crew);s->party.y[p]=(uint16_t)(s->campaign.battle_y+wreck.y);
            unsigned at=c->friends;
            /* Unit IDs stay original; only native array indexes shift. No
               visual effects remain at this insertion boundary. */
            for (unsigned k=c->count;k>at;--k) {
                c->unit[k]=c->unit[k-1];c->ids[k]=c->ids[k-1];c->plans[k]=c->plans[k-1];
                memcpy(c->path[k],c->path[k-1],sizeof c->path[k]);c->moved[k]=c->moved[k-1];c->path_index[k]=c->path_index[k-1];c->walk[k]=c->walk[k-1];c->plan_direction[k]=c->plan_direction[k-1];c->fallback[k]=c->fallback[k-1];
                memcpy(c->enemy_orders[k-1],c->enemy_orders[k-2],12);c->enemy_fired[k-1]=c->enemy_fired[k-2];
                if (k==2) c->enemy_modes[0]=c->enemy_movement;else c->enemy_modes[k-2]=c->enemy_modes[k-3];
            }
            c->unit[at]=(BtpCombatUnit){.infantry=1,.x=(uint8_t)((wreck.x+crew)&127),.y=wreck.y,.direction=wreck.direction};memcpy(c->unit[at].record,s->party.people[p],17);
            c->ids[at]=(uint8_t)(4+p);c->plans[at]=(BtpCombatPlan){.movement=255,.kick=255};memset(c->plans[at].orders,255,11);
            memset(c->path[at],0,sizeof c->path[at]);c->moved[at]=c->path_index[at]=c->walk[at]=c->plan_direction[at]=c->fallback[at]=0;
            memset(c->enemy_orders[at-1],255,12);c->enemy_fired[at-1]=0;if (at==1) c->enemy_movement=255;else c->enemy_modes[at-2]=255;
            if (c->last_attacker>=at) ++c->last_attacker;
            if (c->last_target>=at) ++c->last_target;
            if (c->target_unit>=at) ++c->target_unit;
            if (c->scan_unit>=at) ++c->scan_unit;
            ++c->friends;++c->count;
        }
        if (c->active_unit==dead) for (unsigned i=0;i<c->friends;++i) if (c->unit[i].record[0]!=255) { btp_combat_select(c,i);break; }
    }
    s->aftermath.eject=0;
}
static void pockets(BtpState *s)
{
    BtpAftermathState *v=&s->aftermath;unsigned dead=0,any=0,weapon=0;
    for (unsigned i=0;i<8;++i) {
        any|=v->wrecks[4+i] || v->wrecks[16+i];
        if (v->wrecks[16+i]) {
            ++dead;
            /* Primary 05AB:09A1 samples C6EB+17*(4+i), which overlaps
               owned-mech bytes. Preserve this original classifier quirk. */
            unsigned byte=11u+17u*i;weapon|=btp_party_mech(s,byte/125u)[byte%125u]!=0;
        }
    }
    if (!any) { v->phase=0;return; }
    v->cash=(uint16_t)btp_aftermath_cash(s->npc.rng,dead);s->credits+=v->cash;v->phase=3;v->notice=(uint8_t)weapon;v->unit=16;
}
static void next_pilot(BtpState *s)
{
    BtpAftermathState *v=&s->aftermath;
    for (unsigned i=v->pilot+1u;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][8] && s->party.people[i][12]>=8) {
        v->pilot=(uint8_t)i;v->phase=1;v->selected=0;return;
    }
    v->pilot=8;pockets(s);
}
static void next_weapon(BtpState *s)
{
    BtpAftermathState *v=&s->aftermath;
    while (v->unit<24) {
        unsigned at=btp_combat_target(&s->combat,v->unit);
        if (v->wrecks[v->unit] && at<s->combat.count && s->combat.unit[at].record[11]) { v->phase=4;v->selected=0;return; }
        ++v->unit;
    }
    v->phase=0;
}
void btp_aftermath_input(BtpState *s,const BtpResources *r,BtpAction a)
{
    (void)r;BtpAftermathState *v=&s->aftermath;
    if (!v->phase) { pockets(s);return; }
    unsigned count=v->phase==1 || (v->phase==4 && btp_party_count(&s->party)==1) ? 2u : v->phase==4 ? 9u : 1u;
    if (a==BTP_UP || a==BTP_LEFT) v->selected=(uint8_t)((v->selected+count-1)%count);
    if (a==BTP_DOWN || a==BTP_RIGHT) v->selected=(uint8_t)((v->selected+1)%count);
    if (a!=BTP_ACCEPT && a!=BTP_CANCEL) return;
    if (v->phase==1) {
        if (v->selected || a==BTP_CANCEL) { next_pilot(s);return; }
        unsigned id=btp_rng_next(s->npc.rng)&3u;id+=12u*(btp_rng_next(s->npc.rng)&1u);unsigned found=24;
        for (unsigned i=0;i<16;++i) if (v->wrecks[(id+i)&15u] && ((id+i)&15u)<16) { found=(id+i)&15u;break; }
        if (found==24) { v->phase=2;v->notice=2;return; }
        unsigned kind=v->wrecks[found];v->wrecks[found]=0;unsigned at=btp_combat_target(&s->combat,found),skill=0,slot=0;
        for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][9]>skill) skill=s->party.people[i][9];
        while (slot<4 && btp_party_mech(s,slot)[0]!=255) ++slot;
        if (at>=s->combat.count || kind==128 || slot==4 || !btp_salvage_eligible(s->combat.unit[at].record,skill)) { v->phase=2;v->notice=1;return; }
        btp_salvage_copy(s,slot,v->pilot,s->combat.unit[at].record,kind);v->phase=2;v->notice=0;
    } else if (v->phase==2) next_pilot(s);
    else if (v->phase==3) { if (v->notice) next_weapon(s);else v->phase=0; }
    else if (v->phase==4) {
        unsigned p=btp_party_count(&s->party)==1 ? 0u : v->selected;
        if (a==BTP_ACCEPT && (btp_party_count(&s->party)==1 ? !v->selected : p<8) && s->party.people[p][0]!=255) {
            unsigned at=btp_combat_target(&s->combat,v->unit);s->party.people[p][11]=s->combat.unit[at].record[11];if (!p) s->weapon=s->party.people[p][11];
        }
        ++v->unit;next_weapon(s);
    }
}
int btp_aftermath_valid(const BtpState *s)
{
    const BtpAftermathState *v=&s->aftermath;
    if (v->eject>15 || v->phase>4 || v->selected>8 || v->pilot>8 || v->unit>24 || v->notice>2 || v->applied>1 || v->cash>144) return 0;
    if ((v->eject || v->phase || v->applied) && !s->campaign.encounter) return 0;
    if (v->phase && (s->mode!=BTP_ENCOUNTER || s->combat.phase || !v->applied)) return 0;
    for (unsigned i=0;i<24;++i) if (v->wrecks[i] && (!s->campaign.encounter || (i>=4 && i<12 ? v->wrecks[i]!=128 : i>=16 ? v->wrecks[i]!=128 : v->wrecks[i]>=128))) return 0;
    return 1;
}

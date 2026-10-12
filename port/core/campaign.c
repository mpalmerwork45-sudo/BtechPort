#include "core/campaign.h"
#include "core/party.h"
#include "core/world.h"
#include "core/combat.h"
#include "core/npc.h"
#include <string.h>
static void begin(BtpState *s,unsigned event)
{
    BtpCampaignState *v=&s->campaign;
    v->return_map=s->map_id;v->return_x=s->x_half;v->return_y=s->y_half;
    v->battle_x=(uint16_t)(v->world_x&~127u);v->battle_y=(uint16_t)(v->world_y&~127u);v->encounter=(uint8_t)event;
    BtpCombatState *c=&s->combat;
    *c=(BtpCombatState){.phase=BTP_COMBAT_CONTROL,.selected=1,.messages=2,.graphics=1,.movement=255,.kick_target=255,.enemy_movement=255};
    memset(c->orders,255,11);memset(c->enemy_orders,255,sizeof c->enemy_orders);memset(c->enemy_modes,255,sizeof c->enemy_modes);
    btp_party_init(s);btp_party_sync(s);
    for (unsigned i=0;i<4;++i) if (s->party.mech_types[i]!=255 && btp_party_mech(s,i)[0]!=255) {
        unsigned pilot=btp_party_mech(s,i)[121];
        if (pilot>=8 || s->party.people[pilot][0]==255 || s->party.people[pilot][12]!=i) continue;
        BtpCombatUnit *u=&c->unit[c->count];memcpy(u->record,btp_party_mech(s,i),125);
        u->x=(uint8_t)(v->world_x-v->battle_x);u->y=(uint8_t)(v->world_y-v->battle_y-2u);c->ids[c->count++]=(uint8_t)i;
    }
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][12]>=8) {
        BtpCombatUnit *u=&c->unit[c->count];u->infantry=1;memcpy(u->record,s->party.people[i],17);
        /* Original 103B:01DC formations assign fresh encounter positions. */
        u->x=(uint8_t)((v->world_x-v->battle_x+2*(i%3))&127u);u->y=(uint8_t)((v->world_y-v->battle_y+2*(i/3))&127u);
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
    begin(s,2);BtpCombatState *c=&s->combat;
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
    begin(s,1);BtpCombatState *c=&s->combat;
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
    if (c->phase || c->lost) return;
    for (unsigned i=0;i<c->friends;++i) {
        unsigned id=c->ids[i];
        if (id<4) memcpy(btp_party_mech(s,id),c->unit[i].record,125);
        else if (id<12) { memcpy(s->party.people[id-4],c->unit[i].record,17);s->party.x[id-4]=(uint16_t)(s->campaign.battle_x+c->unit[i].x);s->party.y[id-4]=(uint16_t)(s->campaign.battle_y+c->unit[i].y); }
    }
    unsigned event=s->campaign.encounter;s->campaign.encounter=0;
    s->x_half=s->campaign.return_x;s->y_half=s->campaign.return_y;s->map_id=s->campaign.return_map;
    s->combat=(BtpCombatState){0};s->effects=(BtpEffectsState){0};
    if (event==2) { s->mode=BTP_BUILDING;btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags); }
    else s->mode=BTP_EXPLORE;
}

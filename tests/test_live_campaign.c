#include "core/combat.h"
#include "core/audio.h"
#include "core/party.h"
#include "core/world.h"
#include "data/save.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,failures;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static uint64_t hash(const uint8_t *b,unsigned n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);
    return h;
}
static void step(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;btp_state_encode(s,a);
    if (!btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&copy)) {
        fprintf(stderr,"Live restore failed: phase=%u step=%u effects=%u/%u friends=%u units=%u combat=%d\n",
            s->combat.phase,s->combat.step,s->effects.count,s->effects.stage,s->combat.friends,s->combat.count,btp_combat_valid(s));CHECK(0);
    }
    btp_combat_tick(s,r,action);btp_audio_samples(&s->audio,r,BTP_AUDIO_TICK_SAMPLES,NULL);
    btp_combat_tick(&copy,r,action);btp_audio_samples(&copy.audio,r,BTP_AUDIO_TICK_SAMPLES,NULL);
    btp_state_encode(s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    FILE *f=fopen("tests/fixtures/live-campaign-primary.txt","r");CHECK(f);char line[700];
    BtpState s;unsigned current=0,unit_count=0,waves=0;
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='B') {
            unsigned seed,bx,by,friends,count;CHECK(sscanf(line+1,"%u %u %u %u %u %u",&current,&seed,&bx,&by,&friends,&count)==6);
            CHECK(btp_save_load("Original DOS/GAME3",&s,r,&e));s.map_id=0;s.mode=BTP_ENCOUNTER;s.campaign.encounter=1;
            s.campaign.battle_x=(uint16_t)bx;s.campaign.battle_y=(uint16_t)by;s.campaign.world_x=1263;s.campaign.world_y=1675;
            s.campaign.mech[122]=255;s.party.people[3][12]=8;s.menu.sound=0;s.menu.outtakes=0;
            s.story_flags[37]=4;s.story_flags[38]=s.story_flags[39]=s.spy_discovered=(uint8_t)(current!=0);
            if (current) { s.party.mechs[0][122]=(uint8_t)((current==1 || current==3) ? 4 : 1);if (current==2 || current==4) s.party.mechs[0][121]=4; }
            s.combat=(BtpCombatState){.phase=BTP_COMBAT_MENU,.selected=9,.friends=(uint8_t)friends,.count=(uint8_t)count,
                .target_unit=(uint8_t)friends,.last_target=(uint8_t)friends,.movement=255,.kick_target=255,.enemy_movement=255};
            s.combat.automatic=(1u<<friends)-1u;memset(s.combat.orders,255,11);
            memset(s.combat.enemy_orders,255,sizeof s.combat.enemy_orders);memset(s.combat.enemy_modes,255,sizeof s.combat.enemy_modes);
            for (unsigned i=0;i<count;++i) { s.combat.plans[i].movement=s.combat.plans[i].kick=255;memset(s.combat.plans[i].orders,255,11); }
            for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));
            unit_count=0;
        } else if (line[0]=='M') {
            unsigned id;int used;CHECK(sscanf(line+1,"%u%n",&id,&used)==1 && id<4);char *at=line+1+used;
            for (unsigned i=0;i<125;++i) { unsigned b;CHECK(sscanf(at,"%u%n",&b,&used)==1 && b<256);at+=used;btp_party_mech(&s,id)[i]=(uint8_t)b; }
        } else if (line[0]=='P' || line[0]=='H') {
            unsigned id;int used;CHECK(sscanf(line+1,"%u%n",&id,&used)==1);char *at=line+1+used;uint8_t record[17];
            for (unsigned i=0;i<17;++i) { unsigned b;CHECK(sscanf(at,"%u%n",&b,&used)==1 && b<256);at+=used;record[i]=(uint8_t)b; }
            if (line[0]=='P') { CHECK(id<8);memcpy(s.party.people[id],record,17); }
            else { unsigned slot=btp_combat_target(&s.combat,id);CHECK(slot<s.combat.count);memcpy(s.combat.unit[slot].record,record,17); }
        } else if (line[0]=='I') {
            unsigned id,x,y,face,fallback,walk,heat,heading;uint64_t expected;
            CHECK(sscanf(line+1,"%u %u %u %u %u %u %u %u %" SCNx64,&id,&x,&y,&face,&fallback,&walk,&heat,&heading,&expected)==9 && unit_count<24);
            unsigned at=unit_count++;BtpCombatUnit *u=&s.combat.unit[at];s.combat.ids[at]=(uint8_t)id;
            u->x=(uint8_t)x;u->y=(uint8_t)y;u->direction=(uint8_t)face;u->heat=(uint8_t)heat;
            if (!at) { s.x_half=(uint16_t)x;s.y_half=(uint16_t)(y+2); }
            s.combat.fallback[at]=(uint8_t)fallback;s.combat.plan_direction[at]=(uint8_t)heading;s.combat.walk[at]=(uint8_t)walk;
            if (id<4) memcpy(u->record,btp_party_mech(&s,id),125);
            else if (id<12) { u->infantry=1;memcpy(u->record,s.party.people[id-4],17); }
            else if (id<16) memcpy(u->record,r->combat.loans[0],125);
            else u->infantry=1;
            if (id<16) CHECK(hash(u->record,u->infantry ? 17u : 125u)==expected);
        } else if (line[0]=='T') {
            unsigned turn,rng,count;CHECK(sscanf(line+1,"%u %u %u %u",&current,&turn,&rng,&count)==4);
            s.combat.phase=BTP_COMBAT_MENU;s.combat.selected=9;step(&s,r,BTP_ACCEPT);
            unsigned ticks=0;
            while (s.combat.phase==BTP_COMBAT_ROUND && ticks++<8192) { step(&s,r,BTP_IDLE); }
            if (s.combat.phase==BTP_COMBAT_SPY) {
                step(&s,r,BTP_ACCEPT);
                while (s.combat.phase==BTP_COMBAT_ROUND && ticks++<8192) step(&s,r,BTP_IDLE);
            }
            CHECK(ticks<8192);unsigned actual=s.npc.rng[0]+256u*s.npc.rng[1]+65536u*s.npc.rng[2];++waves;
            if (actual!=rng || s.combat.count!=count) { fprintf(stderr,"Live case=%u wave=%u rng=%u/%u units=%u/%u\n",current,turn,actual,rng,s.combat.count,count);++failures; }
        } else if (line[0]=='U') {
            unsigned id;int x,y;unsigned face,heat;uint64_t expected;
            CHECK(sscanf(line+1,"%u %d %d %u %u %" SCNx64,&id,&x,&y,&face,&heat,&expected)==6);
            unsigned at=btp_combat_target(&s.combat,id);CHECK(at<s.combat.count);const BtpCombatUnit *u=&s.combat.unit[at];
            if (hash(u->record,u->infantry ? 17u : 125u)!=expected || (u->record[0]!=255 && (u->x!=x || u->y!=y || u->direction!=face || u->heat!=heat))) {
                fprintf(stderr,"Live case=%u wave=%u id=%u pos=%u,%u/%d,%d face=%u/%u heat=%u/%u record=%016" PRIx64 "/%016" PRIx64 "\n",
                    current,s.combat.round,id,u->x,u->y,x,y,u->direction,face,u->heat,heat,hash(u->record,u->infantry ? 17u : 125u),expected);++failures;
            }
        } else if (line[0]=='Z') {
            unsigned won,lost;CHECK(sscanf(line+1,"%u %u %u",&current,&won,&lost)==3);
            if (s.combat.won!=won || s.combat.lost!=lost) { fprintf(stderr,"Live outcome=%u won=%u/%u lost=%u/%u\n",current,s.combat.won,won,s.combat.lost,lost);++failures; }
        } else CHECK(0);
    }
    fclose(f);free(r);CHECK(waves==25);printf("Live campaign: %u complete waves, %u checks, %u differences\n",waves,checks,failures);return failures!=0;
}

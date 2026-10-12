#include "core/yard.h"
#include "core/combat.h"
#include "core/animation.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static uint64_t fingerprint(const uint8_t *b,size_t n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (size_t i=0;i<n;++i) { h^=b[i];h*=UINT64_C(1099511628211); }return h;
}
static unsigned rng(const BtpState *s)
{
    return s->npc.rng[0]+((unsigned)s->npc.rng[1]<<8)+((unsigned)s->npc.rng[2]<<16);
}
static void input(BtpState *s,const BtpResources *r,BtpAction a)
{
    BtpState copy;uint8_t bytes[BTP_STATE_BYTES],after[BTP_STATE_BYTES];btp_state_encode(s,bytes);
    if (!btp_state_decode(bytes,sizeof bytes,btp_active_map(r,s),btp_state_bld(r,s),&copy)) {
        fprintf(stderr,"Theft restore: tick=%u mode=%u phase=%u count=%u yard=%u/%u combat-valid=%d yard-valid=%d script=%u/%u checkpoint=%u pos=%u,%u map=%u menu=%u/%u\n",
            s->tick,s->mode,s->combat.phase,s->combat.count,s->yard.active,s->yard.phase,btp_combat_valid(s),btp_yard_valid(s),
            s->script.status,s->script.pc,s->checkpoint_valid,s->x_half,s->y_half,s->map_id,s->menu.from_story,s->campaign.ui);CHECK(0);
    }
    btp_game_tick(s,r,a);btp_game_tick(&copy,r,a);btp_state_encode(s,bytes);btp_state_encode(&copy,after);CHECK(!memcmp(bytes,after,sizeof bytes));
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    for (unsigned i=0;i<11;++i) CHECK(btp_mech_sprite_base(r->combat.arena_mechs[i][0],1)==r->combat.arena_levels[i]);
    FILE *f=fopen("tests/fixtures/theft-primary.txt","r");CHECK(f);char line[512];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        BtpState s;btp_start(&s);unsigned seed,expected,i,x,y,difficulty,rental,base,walk;int used;
        if (line[0]=='P') {
            CHECK(sscanf(line+1,"%u %u %u %u %u%n",&seed,&expected,&i,&x,&y,&used)==5);
            s.x_half=16;s.y_half=36;s.npc.rng[0]=(uint8_t)seed;s.npc.rng[1]=(uint8_t)(seed>>8);s.npc.rng[2]=(uint8_t)(seed>>16);
            btp_yard_begin_guards(&s,r);const BtpCombatUnit *u=&s.combat.unit[1+i];char *at=line+1+used;
            CHECK(rng(&s)==expected);CHECK(1664u+u->x==(x>>8)*128u+(x&127u));CHECK(896u+u->y==(y>>12)*128u+(y&127u));
            for (unsigned k=0;k<17;++k) { unsigned value;CHECK(sscanf(at,"%u%n",&value,&used)==1);at+=used;CHECK(u->record[k]==value); }
        } else {
            unsigned long long h;CHECK(sscanf(line+1,"%u %u %u %u %u %u %u %u %u %llx",&seed,&difficulty,&rental,&expected,&i,&x,&y,&base,&walk,&h)==10);
            s.story_flags[3]=(uint8_t)difficulty;s.yard.rental=(uint8_t)rental;memcpy(s.yard.types,(uint8_t[]){76,67,83,255},4);
            s.npc.rng[0]=(uint8_t)seed;s.npc.rng[1]=(uint8_t)(seed>>8);s.npc.rng[2]=(uint8_t)(seed>>16);btp_yard_begin_arena(&s,r);
            const BtpCombatUnit *u=&s.combat.unit[1+i];CHECK(rng(&s)==expected);
            CHECK(1216u+u->x==(x>>8)*128u+(x&127u));CHECK(1024u+u->y==(y>>12)*128u+(y&127u));
            CHECK(btp_mech_sprite_base(u->record[0],1)==base);CHECK((i && rental ? 16u : s.combat.walk[1+i])==walk);
            if (fingerprint(u->record,125)!=(uint64_t)h) fprintf(stderr,"arena seed=%u difficulty=%u rental=%u unit=%u actual=%016llx expected=%016llx\n",seed,difficulty,rental,i,(unsigned long long)fingerprint(u->record,125),h);
            CHECK(fingerprint(u->record,125)==(uint64_t)h);
        }
        ++cases;
    }
    fclose(f);CHECK(cases==68);
    const char *routes[]={"prison-theft","arena-theft"};
    BtpState prison_start={0};
    for (unsigned route=0;route<2;++route) {
        BtpState s;char path[180];if (route) CHECK(btp_save_load("Original DOS/GAME3",&s,r,&e));else btp_start(&s);
        snprintf(path,sizeof path,"tests/fixtures/ordinary-%s.actions",routes[route]);f=fopen(path,"r");CHECK(f);
        unsigned yard=0,alarm=0,ticks=0,owned_four=0;
        while (fgets(line,sizeof line,f)) { line[strcspn(line,"\r\n")]=0;BtpAction a;CHECK(btp_action_parse(line,&a));input(&s,r,a);
            if (!route && !yard && s.mode==BTP_YARD) prison_start=s;
            yard|=s.yard.active;alarm|=s.yard.alarm!=0;
            owned_four|=s.party.mech_types[3]!=255 && !s.yard.active;CHECK(s.audio.sound_count<=1);++ticks; }
        fclose(f);CHECK(ticks>200 && s.mode==BTP_EXPLORE && yard);
        if (route) CHECK(alarm && owned_four && s.party.mech_types[0]=='L');else CHECK(s.party.mech_types[2]=='S' && s.party.people[0][12]==2 && s.campaign.mounted);
    }
    CHECK(prison_start.yard.active==1);
    for (unsigned i=0;i<1024 && prison_start.mode==BTP_YARD;++i) input(&prison_start,r,BTP_IDLE);
    CHECK(prison_start.mode==BTP_ENCOUNTER && prison_start.campaign.encounter==3 && prison_start.combat.count==9);
    for (unsigned i=0;i<3;++i) input(&prison_start,r,BTP_ACCEPT);
    CHECK(prison_start.combat.phase==BTP_COMBAT_MENU);
    while (prison_start.combat.selected!=8) input(&prison_start,r,BTP_DOWN);
    input(&prison_start,r,BTP_ACCEPT);
    CHECK(prison_start.combat.phase==BTP_COMBAT_NOTICE && prison_start.combat.notice==6);input(&prison_start,r,BTP_ACCEPT);
    input(&prison_start,r,BTP_DOWN);input(&prison_start,r,BTP_ACCEPT);
    for (unsigned i=0;i<8192 && prison_start.mode==BTP_ENCOUNTER && prison_start.combat.phase==BTP_COMBAT_ROUND;++i) input(&prison_start,r,BTP_IDLE);
    CHECK(prison_start.combat.phase!=BTP_COMBAT_ROUND);
    free(r);printf("PASS: %u theft checks, 68 primary setup cases and two saved input routes\n",checks);return 0;
}

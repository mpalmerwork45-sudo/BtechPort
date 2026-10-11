#include "core/combat.h"
#include "core/shop.h"
#include "core/npc.h"
#include "core/economy.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static uint64_t fingerprint(const uint8_t *b,size_t n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (size_t i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);
    return h;
}
static void input(BtpState *s,const BtpResources *r,BtpAction a)
{
    uint8_t bytes[BTP_STATE_BYTES],again[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,bytes);
    int decoded=btp_state_decode(bytes,sizeof bytes,&r->map,btp_building_bld(r,s->entry_slot),&copy);
    if (!decoded) fprintf(stderr,"decode: credits=%u mode=%u slot=%u status=%u pc=%u rows=%u/%u native=%u pending=%u checkpoint=%u technician=%u apprentice=%u\n",
        s->credits,s->mode,s->entry_slot,s->script.status,s->script.pc,s->script.row,s->script.text_row[0],
        s->script.native_action,s->npc.allowance_pending,s->checkpoint_valid,s->technician,s->apprentice);
    CHECK(decoded);
    btp_game_tick(s,r,a);btp_game_tick(&copy,r,a);
    btp_state_encode(s,bytes);btp_state_encode(&copy,again);CHECK(!memcmp(bytes,again,sizeof bytes));
}
static void enter(BtpState *s,const BtpResources *r)
{
    s->x_half=(uint16_t)((r->map.entrance_x[5]&127)-1);s->y_half=r->map.entrance_y[5]&127;
    input(s,r,BTP_RIGHT);CHECK(s->mode==BTP_ENTRY);input(s,r,BTP_ACCEPT);
    CHECK(s->script.menu_id==21);
}
static void command(BtpState *s,const BtpResources *r,unsigned n)
{
    CHECK(s->combat.phase==BTP_COMBAT_MENU);
    while (s->combat.selected!=n) input(s,r,BTP_DOWN);
    input(s,r,BTP_ACCEPT);
}
static void attacks(const BtpState *start,BtpResources *r)
{
    BtpState s=*start;BtpMap map=r->map;memset(r->map.tiles,64,sizeof r->map.tiles);
    s.combat.unit[0].x=64;s.combat.unit[0].y=77;s.x_half=64;s.y_half=79;
    s.combat.unit[1].x=65;s.combat.unit[1].y=77;s.combat.unit[1].heat=30;
    s.combat.goal_active=0;s.combat.movement=255;memset(s.combat.orders,255,sizeof s.combat.orders);
    uint8_t ammo[10];memcpy(ammo,s.combat.unit[0].record+39,sizeof ammo);
    command(&s,r,4);CHECK(s.combat.phase==BTP_COMBAT_KICK);input(&s,r,BTP_ACCEPT);
    CHECK(s.combat.kick_target==12);command(&s,r,9);input(&s,r,BTP_IDLE);
    CHECK((s.combat.fired&2048u) && s.combat.last_weapon==11 && s.combat.last_attacker==0);
    CHECK(!memcmp(ammo,s.combat.unit[0].record+39,sizeof ammo));
    CHECK(!s.combat.unit[0].heat && !s.combat.goal_active);
    s=*start;s.combat.unit[0].record[36]&=(uint8_t)~8u;
    command(&s,r,4);CHECK(s.combat.phase==BTP_COMBAT_NOTICE && s.combat.notice==3);
    input(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_MENU);
    s=*start;s.story_flags[2]=0;memcpy(s.combat.unit[0].record,r->combat.loans[0],125);
    command(&s,r,2);CHECK(s.combat.phase==BTP_COMBAT_NOTICE && s.combat.notice==2);
    input(&s,r,BTP_ACCEPT);
    r->map=map;
}
static void movement(const BtpState *start,BtpResources *r)
{
    BtpMap map=r->map;memset(r->map.tiles,64,sizeof r->map.tiles);
    for (unsigned mode=0;mode<3;++mode) {
        BtpState s=*start;s.combat.unit[1].x=120;s.combat.unit[1].y=120;
        memset(s.combat.orders,255,sizeof s.combat.orders);s.combat.kick_target=255;
        s.combat.unit[0].record[38]=0;
        for (unsigned i=51;i<=85;++i) if (s.combat.unit[0].record[i]==34) s.combat.unit[0].record[i]=0;
        command(&s,r,mode);input(&s,r,BTP_RIGHT);input(&s,r,BTP_ACCEPT);command(&s,r,9);
        while (s.combat.phase==BTP_COMBAT_ROUND) input(&s,r,BTP_IDLE);
        /* 12E8:0F03 pops an arrived waypoint before heat cleanup. */
        CHECK(s.combat.moved[0]==1 && s.combat.unit[0].heat==0 && !s.combat.goal_active);
    }
    r->map=map;
}
static void route_controls(const BtpState *start,BtpResources *r)
{
    BtpState s=*start;BtpCombatState *c=&s.combat;
    command(&s,r,0);input(&s,r,BTP_RIGHT);input(&s,r,BTP_ACCEPT);
    unsigned first_x=c->goal_x,first_y=c->goal_y;
    for (unsigned i=0;i<11;++i) CHECK(btp_combat_waypoint(c,first_x+1+i,first_y,0));
    input(&s,r,BTP_IDLE);CHECK(c->waypoint_count==11);
    CHECK(btp_combat_waypoint(c,first_x,first_y,0) && c->waypoint_count==11);
    command(&s,r,0);
    for (unsigned i=0;i<13;++i) input(&s,r,BTP_RIGHT);
    input(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_NOTICE && c->notice==4);
    input(&s,r,BTP_ACCEPT);command(&s,r,1);CHECK(c->phase==BTP_COMBAT_REPLACE);
    input(&s,r,BTP_RIGHT);input(&s,r,BTP_ACCEPT);
    CHECK(c->phase==BTP_COMBAT_MENU && c->movement==0 && c->waypoint_count==11);
    command(&s,r,1);input(&s,r,BTP_ACCEPT);
    CHECK(c->phase==BTP_COMBAT_MOVE && !c->goal_active && !c->waypoint_count);
    input(&s,r,BTP_RIGHT);input(&s,r,BTP_ACCEPT);
    CHECK(c->goal_active && c->movement==1);
    command(&s,r,2);CHECK(c->phase==BTP_COMBAT_REPLACE);input(&s,r,BTP_CANCEL);
    CHECK(c->goal_active && c->movement==1 && !c->waypoint_count);
}
static void failures(const BtpState *start,BtpResources *r)
{
    BtpState s=*start;command(&s,r,8);
    for (unsigned i=0;i<4;++i) input(&s,r,BTP_LEFT);
    input(&s,r,BTP_IDLE);
    CHECK(s.mode==BTP_BUILDING && s.story_flags[0]==4 && !s.story_flags[1] && s.allowance_cap==1000);
    BtpMap map=r->map;memset(r->map.tiles,64,sizeof r->map.tiles);s=*start;
    s.combat.unit[0].x=64;s.combat.unit[0].y=77;s.combat.unit[1].x=67;s.combat.unit[1].y=77;
    s.x_half=64;s.y_half=79;s.combat.goal_active=0;s.combat.movement=255;s.combat.kick_target=255;
    memset(s.combat.orders,255,sizeof s.combat.orders);memset(s.combat.unit[0].record+17,1,19);
    for (unsigned n=0;n<16 && s.combat.phase;++n) {
        command(&s,r,9);
        while (s.combat.phase==BTP_COMBAT_ROUND) input(&s,r,BTP_IDLE);
    }
    CHECK(s.combat.lost && !s.combat.won && s.x_half==60 && s.y_half==79);
    input(&s,r,BTP_IDLE);
    CHECK(s.mode==BTP_BUILDING && s.story_flags[0]==4 && !s.story_flags[1] && s.allowance_cap==1000 && !s.recruitment);
    r->map=map;
}
static void bad_save(const BtpState *s,const BtpResources *r,unsigned offset,unsigned value)
{
    uint8_t bytes[BTP_STATE_BYTES];BtpState untouched=*s;
    btp_state_encode(s,bytes);bytes[offset]=(uint8_t)value;
    CHECK(!btp_state_decode(bytes,sizeof bytes,&r->map,btp_building_bld(r,s->entry_slot),&untouched));
    CHECK(!memcmp(&untouched,s,sizeof *s));
}
static void ordinary(const char *path,BtpResources *r)
{
    FILE *f=fopen(path,"r");CHECK(f);char line[40];BtpState s,robots={0},duel={0};btp_start(&s);
    unsigned ticks=0,robot_shots=0,enemy_shots=0;
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")]=0;BtpAction a;CHECK(btp_action_parse(line,&a));
        if (s.combat.phase==BTP_COMBAT_MENU && s.mission.assignment==3 && !robots.combat.phase) robots=s;
        if (s.combat.phase==BTP_COMBAT_MENU && s.mission.assignment==4 && !duel.combat.phase) duel=s;
        input(&s,r,a);++ticks;
        if (s.combat.flash && s.combat.last_attacker) {
            if (s.mission.assignment==3) ++robot_shots;else if (s.mission.assignment==4) ++enemy_shots;
        }
    }
    fclose(f);CHECK(ticks>1000 && robots.combat.count>=4 && duel.combat.count==2);
    CHECK(s.mode==BTP_EXPLORE && s.story_flags[0]==5 && s.story_flags[1] && s.allowance_cap==2000);
    CHECK(s.technician==1 && s.apprentice==1 && s.recruitment==1 && s.npc_pairs[0][0]==112);
    CHECK(robot_shots && enemy_shots);input(&s,r,BTP_IDLE);
    attacks(&duel,r);movement(&duel,r);route_controls(&duel,r);failures(&duel,r);
    command(&robots,r,4);input(&robots,r,BTP_DOWN);input(&robots,r,BTP_ACCEPT);
    CHECK(robots.combat.target_unit==2);input(&robots,r,BTP_UP);input(&robots,r,BTP_ACCEPT);
    CHECK(robots.combat.kick_target==17);command(&robots,r,4);input(&robots,r,BTP_CANCEL);
    CHECK(robots.combat.kick_target==255);
    bad_save(&duel,r,896,8);bad_save(&duel,r,899,2);bad_save(&duel,r,1535,1);
    bad_save(&s,r,897,1);bad_save(&s,r,452,5);bad_save(&s,r,453,2);
}
int main(int argc,char **argv)
{
    if (argc!=6) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;
    CHECK(r && btp_resources_load(argv[1],r,&e) && btp_combat_data_load(argv[2],&r->combat,&e));
    FILE *f=fopen(argv[3],"r");CHECK(f);char line[512];
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='#') continue;
        if (line[0]=='B') {
            unsigned mission,seed,loan,count,after;int at=0;
            CHECK(sscanf(line+1,"%u %u %u %u %u%n",&mission,&seed,&loan,&count,&after,&at)==5);
            BtpState s;btp_start(&s);s.mission.assignment=(uint8_t)mission;s.story_flags[2]=(uint8_t)loan;
            s.npc.rng[0]=(uint8_t)seed;s.npc.rng[1]=(uint8_t)(seed>>8);s.npc.rng[2]=(uint8_t)(seed>>16);
            btp_combat_begin(&s,r);CHECK(s.combat.count==count);
            CHECK(s.npc.rng[0]+256u*s.npc.rng[1]+65536u*s.npc.rng[2]==after);
            const char *p=line+1+at;
            for (unsigned i=1;i<count;++i) {
                unsigned x,y,frame;uint64_t hash;
                CHECK(sscanf(p,"%u %u %" SCNx64 " %u%n",&x,&y,&hash,&frame,&at)==4);p+=at;
                BtpCombatUnit *u=&s.combat.unit[i];
                if (u->x!=x || u->y!=y || fingerprint(u->record,mission==3 ? 17 : 125)!=hash) {
                    fprintf(stderr,"mission %u seed %u unit %u got %u,%u hash %016" PRIx64 " expected %u,%u %016" PRIx64 "\n",
                        mission,seed,i,u->x,u->y,fingerprint(u->record,mission==3 ? 17 : 125),x,y,hash);CHECK(0);
                }
                CHECK(u->direction==6 && u->infantry==(mission==3));
                CHECK(s.combat.walk[i]==frame);
            }
        } else if (line[0]=='E') {
            unsigned credits,after,rank,flag,result;
            CHECK(sscanf(line+1,"%u %u %u %u %u",&credits,&after,&rank,&flag,&result)==5);
            BtpState s;btp_start(&s);s.credits=credits;s.npc.allowance_pending=(uint8_t)btp_economy_below_cap(&s);enter(&s,r);
            input(&s,r,BTP_ACCEPT);CHECK(s.script.status==BTP_SCRIPT_CONFIRM);
            input(&s,r,BTP_ACCEPT);
            CHECK(s.credits==after && s.technician==rank && s.apprentice==(flag&1u) && s.story_flags[14]==result);
            input(&s,r,BTP_ACCEPT);CHECK(s.script.status==BTP_SCRIPT_MENU);
            if (rank) {
                input(&s,r,BTP_ACCEPT);CHECK(s.script.status==BTP_SCRIPT_WAIT);
                CHECK(s.credits==after && s.technician==rank);input(&s,r,BTP_ACCEPT);
            }
            btp_start(&s);s.credits=credits;s.npc.allowance_pending=(uint8_t)btp_economy_below_cap(&s);enter(&s,r);
            input(&s,r,BTP_ACCEPT);input(&s,r,BTP_RIGHT);input(&s,r,BTP_ACCEPT);
            CHECK(s.credits==credits && !s.technician && !s.apprentice);
        } else CHECK(0);
    }
    fclose(f);CHECK(btp_dialogue_load(argv[4],&r->dialogue,&e));ordinary(argv[5],r);
    free(r);printf("PASS: %u original setup, physical/movement UI, five-mission route and save-continuation assertions\n",checks);return 0;
}

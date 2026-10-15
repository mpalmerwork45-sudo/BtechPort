#include "core/combat.h"
#include "core/animation.h"
#include "core/campaign.h"
#include "core/party.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static uint64_t left_hash(const uint32_t *pixels)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned y=0;y<200;++y) for (unsigned x=0;x<104;++x) for (int shift=16;shift>=0;shift-=8)
        h=(h^(uint8_t)(pixels[y*320+x]>>shift))*UINT64_C(1099511628211);
    return h;
}
static uint64_t region_hash(const uint32_t *pixels,unsigned x,unsigned y,unsigned w,unsigned h)
{
    uint64_t value=UINT64_C(14695981039346656037);
    for (unsigned row=y;row<y+h;++row) for (unsigned col=x;col<x+w;++col) for (int shift=16;shift>=0;shift-=8)
        value=(value^(uint8_t)(pixels[row*320+col]>>shift))*UINT64_C(1099511628211);
    return value;
}
static void setup(BtpState *s,const BtpResources *r)
{
    BtpError e;CHECK(btp_save_load("Original DOS/GAME3",s,r,&e));
    s->party.people[3][12]=8;s->campaign.mech[122]=255;
    s->campaign.encounter=1;s->mode=BTP_ENCOUNTER;s->x_half=64;s->y_half=66;
    s->combat=(BtpCombatState){.phase=BTP_COMBAT_MENU,.selected=9,.count=6,.friends=4,.target_unit=4,
        .last_target=4,.movement=255,.kick_target=255,.enemy_movement=255};
    BtpCombatState *c=&s->combat;memset(c->orders,255,11);memset(c->enemy_orders,255,sizeof c->enemy_orders);
    memset(c->enemy_modes,255,sizeof c->enemy_modes);
    for (unsigned i=0;i<4;++i) {
        c->plans[i].movement=c->plans[i].kick=255;memset(c->plans[i].orders,255,11);
        c->ids[i]=(uint8_t)(i==3 ? 7 : i);c->unit[i].x=(uint8_t)(64+2*i);c->unit[i].y=64;
        memcpy(c->unit[i].record,i==3 ? s->party.people[3] : btp_party_mech(s,i),i==3 ? 17u : 125u);
    }
    c->unit[3].infantry=1;c->unit[3].x=64;c->ids[4]=13;c->ids[5]=17;
    memcpy(c->unit[4].record,r->combat.loans[0],125);c->unit[4].x=47;c->unit[4].y=47;
    /* The source's first visible enemy human is ID17 with a Shortbow and
       full health. Equivalent relative coordinates retain its NW bearing. */
    const uint8_t human[17]={1,12,6,0,1,3,1,3,1,0,0,4,8,3,12,120,0};
    memcpy(c->unit[5].record,human,17);c->unit[5].infantry=1;c->unit[5].x=47;c->unit[5].y=47;
    s->campaign.battle_x=1152;s->campaign.battle_y=1664;
}
static void step(BtpState *s,const BtpResources *r,BtpAction a)
{
    uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,before);CHECK(btp_state_decode(before,sizeof before,btp_active_map(r,s),btp_state_bld(r,s),&copy));
    BtpState space=copy;
    int compare_space=a==BTP_ACCEPT && s->combat.phase && s->combat.phase!=BTP_COMBAT_ROUND && !s->cutscene.active;
    btp_game_tick(s,r,a);btp_game_tick(&copy,r,a);
    btp_state_encode(s,before);btp_state_encode(&copy,after);CHECK(!memcmp(before,after,sizeof before));
    /* Every actual command, weapon/target choice and held warning exercised
       below must behave identically with Space, including after a reload. */
    if (compare_space) {
        btp_game_tick(&space,r,BTP_OPEN_MENU);btp_state_encode(&space,after);
        CHECK(!memcmp(before,after,sizeof before));
    }
}
static void command(BtpState *s,const BtpResources *r,unsigned wanted)
{
    CHECK(s->combat.phase==BTP_COMBAT_MENU);
    for (unsigned i=0;i<10 && s->combat.selected!=wanted;++i) step(s,r,BTP_DOWN);
    CHECK(s->combat.selected==wanted);step(s,r,BTP_ACCEPT);
}
static unsigned weapon_warnings(const BtpResources *r,uint32_t *frame)
{
    FILE *f=fopen("tests/fixtures/weapon-warnings-primary.txt","r");CHECK(f);
    unsigned actor,heat,sensors,opened,automatic,disabled,waits,messages,first,cases=0;char line[200];
    while (fgets(line,sizeof line,f)) {
        CHECK(sscanf(line,"G %u %u %u %u %u %u %u %u %u",&actor,&heat,&sensors,&opened,&automatic,&disabled,&waits,&messages,&first)==9);
        BtpState s;setup(&s,r);BtpCombatState *c=&s.combat;
        for (unsigned i=0;i<4;++i) { c->unit[i].infantry=0;memcpy(c->unit[i].record,r->combat.loans[0],125);c->ids[i]=(uint8_t)i; }
        c->ids[4]=12;c->ids[5]=13;btp_combat_select(c,actor);
        c->unit[actor].heat=(uint8_t)heat;c->unit[actor].record[119]=(uint8_t)sensors;
        c->automatic=1u<<actor;c->auto_run=1;c->orders[0]=12;c->orders[1]=13;c->kick_target=12;
        c->weapon_selected=11; /* Retained other-mech cursor is bounded only on opening. */
        command(&s,r,3);CHECK(c->automatic==automatic && c->auto_run==1);
        uint16_t *fired=actor ? &c->enemy_fired[actor-1] : &c->fired;
        CHECK(!*fired && c->orders[0]==12 && c->orders[1]==13 && c->kick_target==12);
        if (waits) {
            CHECK(waits==1 && c->phase==BTP_COMBAT_NOTICE);
            CHECK(first==(c->notice==20 ? 0x2904u : c->notice==21 ? 0x292du : 0x2964u));
            uint8_t bytes[BTP_STATE_BYTES];BtpState copy;btp_state_encode(&s,bytes);
            memcpy(bytes,"BTPZ",4);bytes[4]=35;
            CHECK(!btp_state_decode(bytes,sizeof bytes,btp_active_map(r,&s),btp_state_bld(r,&s),&copy));
            step(&s,r,BTP_IDLE);CHECK(c->phase==BTP_COMBAT_NOTICE && !*fired);
            step(&s,r,BTP_OPEN_MENU);
        } else CHECK(first==0x29a3);
        CHECK(c->phase==(opened ? BTP_COMBAT_WEAPONS : BTP_COMBAT_MENU) && *fired==disabled);
        CHECK(messages==waits+opened && c->orders[0]==12 && c->orders[1]==13 && c->kick_target==12);
        if (heat==30) {
            c->unit[actor].heat=0;c->unit[actor].record[119]=0;command(&s,r,3);
            CHECK(c->phase==BTP_COMBAT_WEAPONS && *fired==(1u<<11) && c->orders[0]==12 && c->orders[1]==13);
        }
        /* v35 ordinary command saves still migrate without changing orders. */
        c->phase=BTP_COMBAT_MENU;uint8_t bytes[BTP_STATE_BYTES];BtpState copy;btp_state_encode(&s,bytes);
        memcpy(bytes,"BTPZ",4);bytes[4]=35;
        CHECK(btp_state_decode(bytes,sizeof bytes,btp_active_map(r,&s),btp_state_bld(r,&s),&copy));
        CHECK(copy.combat.orders[0]==12 && copy.combat.orders[1]==13);++cases;
    }
    fclose(f);CHECK(cases==36);
    f=fopen("tests/fixtures/weapon-warning-ui-primary.txt","r");CHECK(f);
    unsigned page,x,y,w,h,current=99,regions=0;uint64_t expected;
    BtpState s;setup(&s,r);BtpCombatState *c=&s.combat;BtpError e;
    c->unit[4].x=54;c->unit[4].y=49;c->unit[5].x=47;c->unit[5].y=49;
    c->weapon_selected=9;c->orders[0]=13;
    while (fscanf(f," W %u %u %u %u %u %" SCNx64,&page,&x,&y,&w,&h,&expected)==6) {
        if (page!=current) {
            current=page;
            if (page==0 || page==2 || page==4 || page==6) {
                if (page==2) step(&s,r,BTP_ACCEPT); /* Done after the damaged warning. */
                c->unit[0].heat=(uint8_t)(page==4 ? 30 : 0);
                c->unit[0].record[119]=(uint8_t)(page==0 ? 1 : page==2 ? 2 : 0);
                command(&s,r,3);
            } else step(&s,r,BTP_ACCEPT);
        }
        btp_render(r,&s,0,frame);uint64_t actual=region_hash(frame,x,y,w,h);
        if (actual!=expected) {
            fprintf(stderr,"Original weapon warning %u region %u,%u: %016" PRIx64 " / %016" PRIx64 "\n",page,x,y,actual,expected);
            CHECK(btp_write_ppm("work/weapon-warning-failed.ppm",frame));
        }
        CHECK(actual==expected);++regions;
        if (page==0 || page==2 || page==4) {
            char path[80];snprintf(path,sizeof path,"work/weapon-warning-%u.btp",page);CHECK(btp_save_write(path,&s,r,&e));
        }
    }
    fclose(f);CHECK(regions==9 && c->orders[0]==13 && !c->fired);return regions;
}
static unsigned weapon_pages(const BtpResources *r,uint32_t *frame)
{
    BtpState s;setup(&s,r);BtpCombatState *c=&s.combat;BtpError e;
    c->unit[4].x=54;c->unit[4].y=49;c->unit[5].x=47;c->unit[5].y=49;c->unit[3].y=66;
    c->unit[0].record[40]=0;c->unit[0].record[59]|=128;
    command(&s,r,3);
    FILE *f=fopen("tests/fixtures/weapon-menu-primary.txt","r");CHECK(f);
    unsigned page,x,y,w,h,current=0,regions=0;uint64_t expected;
    while (fscanf(f," W %u %u %u %u %u %" SCNx64,&page,&x,&y,&w,&h,&expected)==6) {
        if (page!=current) {
            CHECK(page==current+1);current=page;
            switch (page) {
            case 1: step(&s,r,BTP_ACCEPT);step(&s,r,BTP_ACCEPT);CHECK(c->orders[0]==13 && !c->weapon_selected && c->weapon_ui==3);break;
            case 2: step(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_OVERRIDE);break;
            case 3: step(&s,r,BTP_RIGHT);break;
            case 4: step(&s,r,BTP_OPEN_MENU);CHECK(c->orders[0]==13 && c->phase==BTP_COMBAT_WEAPONS);break;
            case 5: step(&s,r,BTP_ACCEPT);step(&s,r,BTP_ACCEPT);CHECK(c->orders[0]==255 && c->phase==BTP_COMBAT_TARGET);break;
            case 6: step(&s,r,BTP_DOWN);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);break;
            case 7: step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);CHECK(c->notice==19 && c->orders[1]==255);break;
            case 8: step(&s,r,BTP_ACCEPT);break;
            case 9: step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);CHECK(c->notice==18 && c->orders[2]==255);break;
            case 10: step(&s,r,BTP_ACCEPT);break;
            case 11:
                for (unsigned i=0;i<7;++i) step(&s,r,BTP_DOWN);
                step(&s,r,BTP_ACCEPT);command(&s,r,4);CHECK(c->phase==BTP_COMBAT_KICK);break;
            case 12: step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);break;
            case 13:
                step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);
                for (unsigned i=0;i<3;++i) command(&s,r,7);
                CHECK(c->active_unit==3 && c->weapon_selected==9);break;
            case 14: command(&s,r,3);CHECK(c->phase==BTP_COMBAT_TARGET && c->target_selected==2);break;
            case 15: step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);CHECK(c->orders[0]==17 && c->selected==0);break;
            case 16: command(&s,r,3);CHECK(c->phase==BTP_COMBAT_OVERRIDE);break;
            case 17: step(&s,r,BTP_RIGHT);step(&s,r,BTP_ACCEPT);CHECK(c->orders[0]==17);break;
            case 18: command(&s,r,3);step(&s,r,BTP_ACCEPT);CHECK(c->orders[0]==17 && c->target_selected==2);break;
            case 19: step(&s,r,BTP_ACCEPT);CHECK(c->orders[0]==255);break;
            default: CHECK(0);
            }
        }
        btp_render(r,&s,0,frame);uint64_t actual=region_hash(frame,x,y,w,h);
        if (actual!=expected) {
            fprintf(stderr,"Original weapon page %u region %u,%u: %016" PRIx64 " / %016" PRIx64 "\n",page,x,y,actual,expected);
            CHECK(btp_write_ppm("work/weapon-menu-failed.ppm",frame));
        }
        CHECK(actual==expected);++regions;
        if (x==0 && (page==2 || page==7 || page==9 || page==11 || page==14 || page==16)) {
            char path[80];snprintf(path,sizeof path,"work/weapon-ui-%u.btp",page);
            CHECK(btp_save_write(path,&s,r,&e));
        }
    }
    fclose(f);CHECK(current==19 && regions==30);
    /* v34 had no weapon-window flags. Reject corrupt v35 bits and preserve
       the old ordinary command state when upgrading its version header. */
    uint8_t bytes[BTP_STATE_BYTES];BtpState copy;btp_state_encode(&s,bytes);
    bytes[10233]=4;CHECK(!btp_state_decode(bytes,sizeof bytes,btp_active_map(r,&s),btp_state_bld(r,&s),&copy));
    bytes[10233]=0;memcpy(bytes,"BTPY",4);bytes[4]=34;
    CHECK(btp_state_decode(bytes,sizeof bytes,btp_active_map(r,&s),btp_state_bld(r,&s),&copy));
    CHECK(!copy.combat.weapon_ui && copy.combat.active_unit==3 && copy.combat.weapon_selected==9);
    for (unsigned done=0;done<2;++done) {
        c->phase=BTP_COMBAT_WEAPONS;c->weapon_selected=(uint8_t)done;btp_state_encode(&s,bytes);
        memcpy(bytes,"BTPY",4);bytes[4]=34;
        CHECK(btp_state_decode(bytes,sizeof bytes,btp_active_map(r,&s),btp_state_bld(r,&s),&copy));
        CHECK(copy.combat.phase==(done ? BTP_COMBAT_MENU : BTP_COMBAT_TARGET) && copy.combat.selected==3);
    }
    setup(&s,r);c->unit[0].record[36]&=(uint8_t)~8u;command(&s,r,4);
    CHECK(c->notice==3);step(&s,r,BTP_OPEN_MENU);CHECK(c->phase==BTP_COMBAT_MENU && !c->paused);
    return regions;
}
static void computer_commands(const BtpResources *r)
{
    BtpState s;setup(&s,r);s.menu.sound=0;s.menu.outtakes=0;
    s.combat.selected=5;
    BtpError error;CHECK(btp_save_write("work/computer-control-start.btp",&s,r,&error));
    FILE *f=fopen("tests/fixtures/computer-control-primary.txt","r");CHECK(f);
    char line[100];unsigned observations=0;
    while (fgets(line,sizeof line,f) && line[0]=='C') {
        unsigned sequence,row,flags,run;CHECK(sscanf(line,"C %u %u %u %u",&sequence,&row,&flags,&run)==4);
        uint32_t actual=0;
        for (unsigned i=0;i<s.combat.friends;++i)
            if (s.combat.automatic&(1u<<i)) actual|=1u<<s.combat.ids[i];
        CHECK(actual==flags && s.combat.auto_run==run && !s.combat.round);
        unsigned choice=btp_combat_menu_command(&s.combat,row);
        command(&s,r,choice);++observations;
        if (choice!=9) {
            CHECK(s.combat.phase==BTP_COMBAT_MENU);
            step(&s,r,BTP_IDLE);CHECK(!s.combat.round);
        }
    }
    CHECK(observations==10 && s.combat.phase==BTP_COMBAT_ROUND);
    fclose(f);
    /* The opening Yes enables continuous rounds. Space stops that global
       run at the wave boundary; individual assignments and saves survive. */
    s.combat.auto_run=1;
    step(&s,r,BTP_OPEN_MENU);CHECK(!s.combat.auto_run && s.combat.automatic==15 && s.combat.paused);
    unsigned ticks=0;
    while (s.combat.phase==BTP_COMBAT_ROUND && ticks++<4096) step(&s,r,BTP_IDLE);
    CHECK(ticks<4096 && s.combat.phase==BTP_COMBAT_MENU && s.combat.automatic==15);
    unsigned round=s.combat.round;step(&s,r,BTP_IDLE);CHECK(s.combat.round==round);
    command(&s,r,3);CHECK(s.combat.automatic==14); /* Manual weapons affect only Jason. */
    step(&s,r,BTP_CANCEL);command(&s,r,7);command(&s,r,0);
    CHECK(s.combat.automatic==12); /* Manual movement affects only Rex. */
    setup(&s,r);s.menu.sound=0;s.combat.phase=BTP_COMBAT_ROUND;
    s.combat.auto_run=1;s.combat.automatic=15;
    CHECK(btp_cutscene_begin(&s,r,4,3));step(&s,r,BTP_OPEN_MENU);
    CHECK(s.combat.paused && !s.combat.auto_run && s.combat.automatic==15);
    ticks=0;while (s.cutscene.active && ticks++<2048) step(&s,r,BTP_IDLE);
    CHECK(ticks<2048 && s.combat.paused && !s.combat.auto_run && s.combat.automatic==15);
}
static void space_commands(const BtpResources *r)
{
    for (unsigned foot=0;foot<2;++foot) {
        BtpState initial;setup(&initial,r);
        if (foot) btp_combat_select(&initial.combat,3);
        unsigned count=btp_combat_menu_count(&initial.combat);
        for (unsigned row=0;row<count;++row) {
            BtpState s=initial;s.menu.sound=s.menu.outtakes=0;
            unsigned choice=btp_combat_menu_command(&s.combat,row);
            command(&s,r,choice); /* step compares Enter with Space. */
            if (s.combat.phase==BTP_COMBAT_MOVE) {
                step(&s,r,BTP_RIGHT);step(&s,r,BTP_ACCEPT);
                CHECK(s.combat.goal_active && s.combat.phase==BTP_COMBAT_MENU);
                /* Changing movement modes asks whether to replace orders;
                   Space must accept that Yes/No choice too. */
                if (!foot) {
                    command(&s,r,choice ? 0u : 1u);
                    CHECK(s.combat.phase==BTP_COMBAT_REPLACE);
                    step(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_MOVE);
                }
            }
        }
    }
}
static void battle_reports(const BtpResources *r,uint32_t *frame)
{
    FILE *f=fopen("tests/fixtures/battle-text-primary.txt","r");CHECK(f);unsigned cases=0;
    unsigned mode,actor,target,weapon,weak,seed,hit,location,criticals;uint64_t text_hash,pixel_hash;
    while (fscanf(f," T %u %u %u %u %u %u %u %u %u %" SCNx64 " %" SCNx64,
        &mode,&actor,&target,&weapon,&weak,&seed,&hit,&location,&criticals,&text_hash,&pixel_hash)==11) {
        if (!actor && target==12 && weapon!=32) {
            /* Tie the printed critical count to actual structural damage,
               rather than testing the presentation record in isolation. */
            BtpCombatUnit a={.x=64,.y=64},t={.x=68,.y=64,.direction=2};
            memcpy(a.record,r->combat.loans[0],125);memcpy(t.record,r->combat.loans[0],125);
            memset(a.record+51,0,35);a.record[51]=(uint8_t)(weapon+1);a.record[39]=200;a.record[121]=0;
            if (weak) { memset(t.record+17,1,19);t.record[36]=t.record[37]=0; }
            uint8_t rng[3]={(uint8_t)seed,(uint8_t)(seed>>8),(uint8_t)(seed>>16)};
            BtpShot result=btp_combat_attack(&a,&t,&r->combat,0,0,0,1,rng);
            CHECK(result.hit==hit && result.location==location && result.criticals==criticals);
        }
        BtpState s;setup(&s,r);s.combat.phase=BTP_COMBAT_ROUND;s.combat.messages=(uint8_t)mode;
        s.effects.shown=(BtpBattleText){1,(uint8_t)actor,(uint8_t)target,0,0,(uint8_t)weapon,
            (uint8_t)hit,(uint8_t)location,(uint8_t)criticals,0};
        uint8_t message[1024];size_t n=btp_battle_text(r,&s.effects.shown,mode,message);
        uint64_t h=UINT64_C(14695981039346656037);
        for (size_t i=0;i<n;++i) if (message[i]!=1) h=(h^message[i])*UINT64_C(1099511628211);
        if (h!=text_hash) fprintf(stderr,"Battle text case %u: %u/%u/%u/%u/%u/%u %016" PRIx64 "/%016" PRIx64 "\n",
            cases,mode,actor,target,weapon,weak,seed,h,text_hash);
        CHECK(h==text_hash);
        btp_render(r,&s,0,frame);h=region_hash(frame,8,8,88,88);
        if (h!=pixel_hash) { fprintf(stderr,"Battle pixels case %u: %016" PRIx64 "/%016" PRIx64 "\n",cases,h,pixel_hash);CHECK(btp_write_ppm("work/m4-audit/battle-text-failed.ppm",frame)); }
        CHECK(h==pixel_hash);
        /* Every held report roundtrips independently of later numeric shots. */
        uint8_t bytes[BTP_STATE_BYTES];BtpState copy;btp_state_encode(&s,bytes);
        CHECK(btp_state_decode(bytes,sizeof bytes,btp_active_map(r,&s),btp_state_bld(r,&s),&copy));
        btp_render(r,&copy,0,frame);CHECK(region_hash(frame,8,8,88,88)==pixel_hash);
        if (!actor && target==12 && weapon==16 && weak && seed==1) {
            BtpError error;CHECK(btp_save_write(mode==1 ? "work/battle-report-brief.btp" : "work/battle-report-verbose.btp",&s,r,&error));
        }
        ++cases;
    }
    fclose(f);CHECK(cases==256);
    /* Replacement recruitment cycles through all ten names, independently
       of the eight party slots. Rusty/Hunter reports must remain saveable. */
    BtpState names;setup(&names,r);names.combat.phase=BTP_COMBAT_ROUND;
    names.effects.shown=(BtpBattleText){.active=1,.actor=7,.target=0,.actor_name=8,.target_name=9,.weapon=7,.hit=1,.location=17};
    uint8_t bytes[BTP_STATE_BYTES];BtpState copy;btp_state_encode(&names,bytes);
    CHECK(btp_state_decode(bytes,sizeof bytes,btp_active_map(r,&names),btp_state_bld(r,&names),&copy));
    CHECK(copy.effects.shown.actor_name==8 && copy.effects.shown.target_name==9);
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame);CHECK(frame);
    FILE *f=fopen("tests/fixtures/combat-ui-primary.txt","r");CHECK(f);unsigned index,cases=0;uint64_t expected;
    while (fscanf(f," U %u %" SCNx64,&index,&expected)==2) {
        BtpState s;setup(&s,r);BtpCombatState *c=&s.combat;
        if (index==1 || index==2) { btp_combat_select(c,index);c->selected=7; }
        if (index>=3) { btp_combat_select(c,3);c->selected=7; }
        if (index==4 || index==7) { c->phase=BTP_COMBAT_SCAN_CHOICE;c->selected=0; }
        if (index==5 || index==6 || index==8) {
            c->phase=BTP_COMBAT_SCAN;c->selected=0;c->scan_unit=(uint8_t)(index==5 ? 0 : index==6 ? 3 : 5);
            c->target_selected=(uint8_t)(index==8);
        }
        if (index==7) { c->phase=BTP_COMBAT_NOTICE;c->notice=15;c->notice_return=BTP_COMBAT_SCAN_CHOICE;c->selected=c->target_selected=1; }
        btp_render(r,&s,0,frame);uint64_t actual=left_hash(frame);
        if (actual!=expected) { fprintf(stderr,"Original UI case %u: %016" PRIx64 " / %016" PRIx64 "\n",index,actual,expected);CHECK(btp_write_ppm("work/combat-ui-failed.ppm",frame)); }
        CHECK(actual==expected);++cases;
    }
    fclose(f);CHECK(cases==9);
    f=fopen("tests/fixtures/target-ui-primary.txt","r");CHECK(f);unsigned x,y,w,h,target_cases=0;
    while (fscanf(f," T %u %u %u %u %u %" SCNx64,&index,&x,&y,&w,&h,&expected)==6) {
        BtpState v;setup(&v,r);BtpCombatState *c=&v.combat;
        /* The captured actor is at (1263,1675); enemy ID13 at (1253,1660),
           ID17 at (1246,1660). Preserve those relative ranges across sectors. */
        c->unit[4].x=54;c->unit[4].y=49;c->unit[5].x=47;c->unit[5].y=49;
        c->selected=3;c->phase=BTP_COMBAT_WEAPONS;
        if (index==1 || index==2) { c->phase=BTP_COMBAT_TARGET;c->target_unit=(uint8_t)(index==1 ? 4 : 5);c->target_selected=(uint8_t)(index==2); }
        if (index==3) c->orders[0]=17;
        if (index>=4 && index<=6) {
            c->phase=0;c->fled=1;v.aftermath=(BtpAftermathState){.phase=(uint8_t)(index==4 ? 6 : 7),.applied=3};
            v.credits=15342507;
        }
        btp_render(r,&v,0,frame);uint64_t actual=region_hash(frame,x,y,w,h);
        if (actual!=expected) { fprintf(stderr,"Original target UI case %u: %016" PRIx64 " / %016" PRIx64 "\n",index,actual,expected);CHECK(btp_write_ppm("work/target-ui-failed.ppm",frame)); }
        CHECK(actual==expected);++target_cases;
        if (!index) CHECK(btp_save_write("work/target-ui-start.btp",&v,r,&e));
    }
    fclose(f);CHECK(target_cases==8);
    /* Exercise the displayed pages through ordinary input, restoring before
       every step. Withdrawal must hold both notices and award no money. */
    BtpState target;CHECK(btp_save_load("work/target-ui-start.btp",&target,r,&e));
    step(&target,r,BTP_ACCEPT);CHECK(target.combat.phase==BTP_COMBAT_TARGET);
    CHECK(btp_save_write("work/target-ui-target.btp",&target,r,&e));
    step(&target,r,BTP_DOWN);step(&target,r,BTP_ACCEPT);CHECK(target.combat.ids[target.combat.target_unit]==17);
    step(&target,r,BTP_UP);step(&target,r,BTP_ACCEPT);CHECK(target.combat.orders[0]==17);
    step(&target,r,BTP_CANCEL);CHECK(target.combat.phase==BTP_COMBAT_MENU);
    for (unsigned i=0;i<11 && target.combat.selected!=8;++i) step(&target,r,BTP_DOWN);
    CHECK(target.combat.selected==8);
    unsigned cash=target.credits;step(&target,r,BTP_ACCEPT);CHECK(target.aftermath.phase==6 && target.credits==cash);
    CHECK(btp_save_write("work/target-ui-withdrawal.btp",&target,r,&e));
    step(&target,r,BTP_ACCEPT);CHECK(target.aftermath.phase==7 && target.credits==cash);
    CHECK(btp_save_write("work/target-ui-return.btp",&target,r,&e));
    step(&target,r,BTP_ACCEPT);CHECK(target.mode==BTP_EXPLORE && target.credits==cash);
    BtpState s;setup(&s,r);BtpCombatState *c=&s.combat;btp_combat_select(c,3);
    CHECK(btp_combat_menu_count(c)==8);c->selected=9;step(&s,r,BTP_DOWN);CHECK(c->selected==0);
    step(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_MOVE);step(&s,r,BTP_RIGHT);step(&s,r,BTP_ACCEPT);CHECK(c->goal_active);
    c->selected=10;step(&s,r,BTP_ACCEPT);CHECK(!c->goal_active && !c->waypoint_count && c->movement==255 && !c->plans[3].active);
    c->selected=6;step(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_SCAN_CHOICE);step(&s,r,BTP_ACCEPT);
    CHECK(c->phase==BTP_COMBAT_SCAN && c->scan_unit==0);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);
    CHECK(c->phase==BTP_COMBAT_SCAN_DETAIL);step(&s,r,BTP_OPEN_MENU);CHECK(c->phase==BTP_COMBAT_SCAN);
    for (unsigned i=0;i<3;++i) step(&s,r,BTP_ACCEPT);
    CHECK(c->scan_unit==3 && !btp_combat_scan_detail(c));
    step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_MENU && c->selected==6);
    step(&s,r,BTP_ACCEPT);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_NOTICE && c->notice==15);
    step(&s,r,BTP_OPEN_MENU);CHECK(c->phase==BTP_COMBAT_SCAN && c->scan_unit==5);step(&s,r,BTP_ACCEPT);CHECK(c->scan_unit==5);
    step(&s,r,BTP_CANCEL);CHECK(c->phase==BTP_COMBAT_MENU);
    btp_combat_select(c,0);c->unit[0].record[119]=2;c->selected=6;step(&s,r,BTP_ACCEPT);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);
    CHECK(c->phase==BTP_COMBAT_NOTICE && c->notice==16);step(&s,r,BTP_ACCEPT);CHECK(c->scan_unit==5);
    setup(&s,r);btp_combat_select(&s.combat,3);s.combat.selected=7;
    CHECK(btp_save_write("work/combat-ui-start.btp",&s,r,&e));
    unsigned weapon_regions=weapon_pages(r,frame);
    computer_commands(r);space_commands(r);battle_reports(r,frame);
    unsigned warning_regions=weapon_warnings(r,frame);
    free(frame);free(r);printf("PASS: %u checks; nine menu/scan, eight target/withdrawal, %u weapon and %u warning regions; 36 warning gates, saved modal inputs\n",checks,weapon_regions,warning_regions);return 0;
}

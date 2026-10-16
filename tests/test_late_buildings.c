#include "core/story.h"
#include "core/party.h"
#include "core/animation.h"
#include "core/combat.h"
#include "core/npc.h"
#include "core/bank.h"
#include "core/training.h"
#include "core/service.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,before);
    if (!btp_state_decode(before,sizeof before,btp_active_map(r,s),btp_state_bld(r,s),&copy)) {
        fprintf(stderr,"Late building save failed: tick %u mode %u script %u PC %u building %u service %u animation %u/%u audio %u\n",
            s->tick,s->mode,s->script.status,s->script.pc,s->campaign.building,s->service.phase,s->cutscene.active,s->cutscene.kind,s->audio.sound_count);
        fprintf(stderr,"Checks combat=%d NPC=%d bank=%d training=%d service=%d coordinate=%u,%u map=%u friends=%u count=%u\n",
            btp_combat_valid(s),btp_npc_valid(s,btp_active_map(r,s)),btp_bank_valid(s),btp_training_valid(s),btp_service_valid(s),
            s->x_half,s->y_half,s->map_id,s->combat.friends,s->combat.count);
        for (unsigned i=0;i<s->combat.count;++i) fprintf(stderr,"unit %u id %u kind %u infantry %u at %u,%u health %u constitution %u weapons %u\n",
            i,btp_combat_id(&s->combat,i),s->combat.unit[i].record[0],s->combat.unit[i].infantry,s->combat.unit[i].x,s->combat.unit[i].y,
            s->combat.unit[i].record[15],s->combat.unit[i].record[1],btp_combat_weapon_count(&s->combat.unit[i]));
        CHECK(0);
    }
    btp_game_tick(s,r,action);btp_game_tick(&copy,r,action);
    btp_state_encode(s,before);btp_state_encode(&copy,after);CHECK(!memcmp(before,after,sizeof before));
}
static void prerequisite(BtpState *s,unsigned people,unsigned seed)
{
    btp_start(s);s->map_id=0;s->story_flags[4]=1;s->weapon=9;s->mech_skills[1]=1;
    s->npc=(BtpNpcState){.rng={(uint8_t)seed,(uint8_t)(seed>>8),(uint8_t)(seed>>16)}};btp_party_init(s);
    for (unsigned i=0;i<8;++i) {
        const uint8_t p[]={0,8,9,7,0,0,0,0,1,0,0,9,8,0,0,80,0};
        memcpy(s->party.people[i],p,17);s->party.people[i][0]=(uint8_t)(i<people ? i : 255);
    }
}
static uint64_t append_byte(uint64_t hash,unsigned byte)
{
    return (hash^(byte&255u))*UINT64_C(1099511628211);
}
static unsigned alternate_services(const BtpResources *r)
{
    FILE *f=fopen("tests/fixtures/alternate-services-primary.txt","r");CHECK(f);
    char line[512];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        unsigned kind,count,cash,bought,spy,viewer,mapper,viewed,product,yes,money,flags[7],waits;
        uint64_t menu_hash,wait_hash;
        CHECK(sscanf(line,"S %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %" SCNx64 " %" SCNx64,
            &kind,&count,&cash,&bought,&spy,&viewer,&mapper,&viewed,&product,&yes,&money,
            &flags[0],&flags[1],&flags[2],&flags[3],&flags[4],&flags[5],&flags[6],&waits,&menu_hash,&wait_hash)==21);
        BtpState s;prerequisite(&s,count,42);s.credits=cash;
        s.story_flags[30]=(uint8_t)bought;s.story_flags[39]=(uint8_t)spy;
        s.story_flags[48]=(uint8_t)viewer;s.story_flags[49]=(uint8_t)mapper;s.story_flags[50]=(uint8_t)viewed;
        btp_game_building(&s,r,kind);btp_game_tick(&s,r,BTP_IDLE);
        uint64_t mh=UINT64_C(14695981039346656037),wh=mh;
        unsigned pages=0,visits=0,ticks=0;
        /* Feed the same decisions to the real supplied BLD and restore
           before every input. Original wait-PC hashes also check the order
           of refusal, insufficient-funds and repeat-purchase messages. */
        while (s.mode==BTP_BUILDING && ticks++<1000) {
            CHECK(s.script.status!=BTP_SCRIPT_ERROR);
            if (s.cutscene.active || s.audio.sound_count) { input(&s,r,BTP_IDLE);continue; }
            if (s.script.status==BTP_SCRIPT_WAIT) {
                wh=append_byte(wh,s.script.pc);wh=append_byte(wh,s.script.pc>>8);++pages;
            } else if (s.script.status==BTP_SCRIPT_MENU) {
                unsigned menu=s.script.menu_id,choice;
                if (menu==29 || menu==35) { choice=visits>0 || product==2;++visits; }
                else { CHECK(menu==36);choice=product; }
                mh=append_byte(mh,menu);mh=append_byte(mh,choice);
                while (s.script.selected!=choice) input(&s,r,BTP_DOWN);
            } else if (s.script.status==BTP_SCRIPT_CONFIRM && !yes) input(&s,r,BTP_RIGHT);
            input(&s,r,BTP_ACCEPT);
        }
        if (s.mode!=BTP_EXPLORE || s.credits!=money || mh!=menu_hash || wh!=wait_hash || pages!=waits)
            fprintf(stderr,"Alternate service %u kind=%u people=%u cash=%u choices=%u/%u: mode=%u cash=%u/%u menus=%016" PRIx64 "/%016" PRIx64 " waits=%u/%u %016" PRIx64 "/%016" PRIx64 "\n",
                cases,kind,count,cash,product,yes,s.mode,s.credits,money,mh,menu_hash,pages,waits,wh,wait_hash);
        CHECK(ticks<1000 && s.mode==BTP_EXPLORE && s.credits==money);
        CHECK(mh==menu_hash && wh==wait_hash && pages==waits);
        const unsigned indices[]={14,30,36,39,48,49,50};
        for (unsigned i=0;i<7;++i) CHECK(s.story_flags[indices[i]]==flags[i]);
        ++cases;
    }
    CHECK(!fclose(f) && cases==928);return cases;
}
static unsigned story_branches(const BtpResources *r)
{
    FILE *f=fopen("tests/fixtures/story-branches-primary.txt","r");CHECK(f);
    char line[512];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        unsigned kind,count,cash,repeat,tech,medic,health,choice,yes,money,flags[4],waits;
        uint64_t expected_menu,expected_wait,expected_event,expected_people;
        CHECK(sscanf(line,"B %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %" SCNx64 " %" SCNx64 " %" SCNx64 " %" SCNx64,
            &kind,&count,&cash,&repeat,&tech,&medic,&health,&choice,&yes,&money,&flags[0],&flags[1],&flags[2],&flags[3],&waits,
            &expected_menu,&expected_wait,&expected_event,&expected_people)==19);
        BtpState s;prerequisite(&s,count,42);s.credits=cash;s.party.people[count-1][9]=(uint8_t)tech;
        s.party.people[0][10]=(uint8_t)medic;s.party.people[0][15]=(uint8_t)health;
        s.technician=(uint8_t)(count==1 ? tech : 0);
        s.story_flags[kind==14 ? 43 : 53]=(uint8_t)repeat;
        btp_game_building(&s,r,kind);btp_game_tick(&s,r,BTP_IDLE);
        uint64_t mh=UINT64_C(14695981039346656037),wh=mh,eh=mh,ph=mh;
        unsigned pages=0,visits=0,ticks=0,last_animation=0,last_effect=0;
        /* Every actual wait, answer, movie frame and sound continuation is
           saved before input. Compare the VM's complete branch outcome. */
        while (s.mode==BTP_BUILDING && ticks++<10000) {
            CHECK(s.script.status!=BTP_SCRIPT_ERROR && s.audio.sound_count<=1);
            unsigned animation=s.cutscene.active ? s.script.pc : 0;
            unsigned effect=s.script.status==BTP_SCRIPT_EFFECT ? s.script.pc : 0;
            if (animation && animation!=last_animation) {
                eh=append_byte(eh,1);eh=append_byte(eh,s.cutscene.kind);eh=append_byte(eh,s.script.animation_flags);
            }
            if (effect && effect!=last_effect) { CHECK(s.audio.sound_count==1);eh=append_byte(eh,0);eh=append_byte(eh,s.audio.sounds[0]); }
            last_animation=animation;last_effect=effect;
            if (s.cutscene.active || s.audio.sound_count) { input(&s,r,BTP_IDLE);continue; }
            if (s.script.status==BTP_SCRIPT_WAIT) { wh=append_byte(wh,s.script.pc);wh=append_byte(wh,s.script.pc>>8);++pages; }
            else if (s.script.status==BTP_SCRIPT_MENU) {
                CHECK(s.script.menu_id==32);unsigned item=visits++ ? 2u : choice;
                mh=append_byte(mh,32);mh=append_byte(mh,item);
                while (s.script.selected!=item) input(&s,r,BTP_DOWN);
            } else if (s.script.status==BTP_SCRIPT_CONFIRM && !yes) input(&s,r,BTP_RIGHT);
            input(&s,r,BTP_ACCEPT);
        }
        for (unsigned i=0;i<8*17;++i) ph=append_byte(ph,((const uint8_t *)s.party.people)[i]);
        if (s.credits!=money || mh!=expected_menu || wh!=expected_wait || eh!=expected_event || ph!=expected_people)
            fprintf(stderr,"Story branch %u kind %u: money %u/%u waits %u/%u menu %016" PRIx64 "/%016" PRIx64 " wait %016" PRIx64 "/%016" PRIx64 " event %016" PRIx64 "/%016" PRIx64 " people %016" PRIx64 "/%016" PRIx64 "\n",
                cases,kind,s.credits,money,pages,waits,mh,expected_menu,wh,expected_wait,eh,expected_event,ph,expected_people);
        CHECK(ticks<10000 && s.mode==BTP_EXPLORE && s.credits==money && pages==waits);
        CHECK(mh==expected_menu && wh==expected_wait && eh==expected_event && ph==expected_people);
        const unsigned indices[]={14,43,53,54};for (unsigned i=0;i<4;++i) CHECK(s.story_flags[indices[i]]==flags[i]);
        ++cases;
    }
    CHECK(!fclose(f) && cases==248);return cases;
}
static void theater_pixels(const BtpResources *r)
{
    BtpState s;prerequisite(&s,1,42);s.credits=5;
    btp_game_building(&s,r,16);btp_game_tick(&s,r,BTP_IDLE);
    FILE *f=fopen("tests/fixtures/theater-text-primary.txt","r");CHECK(f);
    unsigned cases=0,last_animation=0,ticks=0;uint32_t frame[BTP_PIXELS];
    while (s.mode==BTP_BUILDING && ticks++<10000) {
        unsigned animation=s.cutscene.active ? s.script.pc : 0;
        int held=!s.cutscene.active && !s.audio.sound_count && s.script.status==BTP_SCRIPT_WAIT;
        if (s.script.pc>=659 && (held || (animation && animation!=last_animation))) {
            char event;unsigned pc,scroll;uint64_t expected;
            CHECK(fscanf(f," %c %u %u %" SCNx64,&event,&pc,&scroll,&expected)==4);
            CHECK(event==(held ? 'W' : 'A') && pc==s.script.pc);
            btp_render(r,&s,0,frame);uint64_t hash=UINT64_C(14695981039346656037);
            char path[96];snprintf(path,sizeof path,"work/m4-audit/theater-native-%c-%u.ppm",event,pc);
            FILE *out=fopen(path,"wb");CHECK(out);fprintf(out,"P6\n200 184\n255\n");
            for (unsigned y=8;y<192;++y) for (unsigned x=112;x<312;++x) {
                uint32_t color=frame[y*320+x];
                const uint8_t rgb[]={(uint8_t)(color>>16),(uint8_t)(color>>8),(uint8_t)color};
                for (unsigned j=0;j<3;++j) hash=append_byte(hash,rgb[j]);
                CHECK(fwrite(rgb,1,3,out)==3);
            }
            CHECK(!fclose(out));
            if (hash!=expected) fprintf(stderr,"Theater %c PC %u (%u scrolls): %016" PRIx64 "/%016" PRIx64 "\n",event,pc,scroll,hash,expected);
            CHECK(hash==expected);
            if (pc==988 || pc==1125) {
                BtpError error;snprintf(path,sizeof path,"work/m4-audit/theater-%u.btp",pc);
                CHECK(btp_save_write(path,&s,r,&error));
            }
            ++cases;
        }
        last_animation=animation;
        input(&s,r,s.cutscene.active || s.audio.sound_count ? BTP_IDLE : BTP_ACCEPT);
    }
    CHECK(ticks<10000 && s.mode==BTP_EXPLORE && cases==17);
    char extra;CHECK(fscanf(f," %c",&extra)==EOF);CHECK(!fclose(f));
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    BtpBld originals[3]={r->buildings[14],r->buildings[15],r->buildings[16]};
    FILE *f=fopen("tests/fixtures/late-story-primary.txt","r");CHECK(f);char line[512];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        BtpState s;unsigned n,seed,yes,rng;int used;
        if (line[0]=='L') {
            CHECK(sscanf(line+1,"%u %u %u %u%n",&n,&seed,&yes,&rng,&used)==4);prerequisite(&s,n,seed);
            r->buildings[15]=(BtpBld){.length=3,.bytes={0xf5,41,0xff}};btp_game_building(&s,r,15);btp_game_tick(&s,r,BTP_IDLE);
            if (n==1) { if (!yes) input(&s,r,BTP_RIGHT);input(&s,r,BTP_ACCEPT); }
            else for (unsigned i=0;i<n;++i) {
                while (s.service.selected!=i) input(&s,r,BTP_DOWN);
                input(&s,r,BTP_ACCEPT);while (s.service.selected!=n) input(&s,r,BTP_DOWN);input(&s,r,BTP_ACCEPT);
            }
            char *at=line+1+used;
            for (unsigned i=0;i<n;++i) {
                unsigned weapon,health;CHECK(sscanf(at,"%u %u%n",&weapon,&health,&used)==2);at+=used;
                CHECK(s.party.people[i][11]==weapon && s.party.people[i][15]==health);
            }
            CHECK((unsigned)s.npc.rng[0]+((unsigned)s.npc.rng[1]<<8)+((unsigned)s.npc.rng[2]<<16)==rng);
        } else if (line[0]=='M') {
            unsigned health,after;CHECK(sscanf(line+1,"%u %u",&health,&after)==2);prerequisite(&s,1,42);
            s.party.people[0][15]=(uint8_t)health;r->buildings[14]=(BtpBld){.length=3,.bytes={0xf5,47,0xff}};
            btp_game_building(&s,r,14);btp_game_tick(&s,r,BTP_IDLE);CHECK(s.party.people[0][15]==after);
        } else if (line[0]=='C') {
            unsigned x,y,after;CHECK(sscanf(line+1,"%u %u %u%n",&x,&y,&after,&used)==3);prerequisite(&s,1,42);
            s.x_half=s.campaign.world_x=(uint16_t)((x>>8)*128u+(x&127u));
            s.y_half=s.campaign.world_y=(uint16_t)((y>>12)*128u+(y&127u));
            r->buildings[16]=(BtpBld){.length=3,.bytes={0xf5,42,0xff}};
            btp_game_building(&s,r,16);btp_game_tick(&s,r,BTP_IDLE);
            CHECK(s.campaign.world_y==(after>>12)*128u+(after&127u));char *at=line+1+used;
            for (unsigned i=0;i<8;++i) {
                unsigned room,counter;CHECK(sscanf(at,"%u %u%n",&room,&counter,&used)==2);at+=used;
                CHECK(s.npc_pairs[i][0]==room && s.npc_pairs[i][1]==counter);
            }
        } else CHECK(0);
        input(&s,r,BTP_IDLE);++cases;
    }
    fclose(f);CHECK(cases==46);
    for (unsigned i=0;i<3;++i) r->buildings[14+i]=originals[i];
    f=fopen("tests/fixtures/campaign-checkpoints-primary.txt","r");CHECK(f);unsigned disk_cases=0;
    while (fgets(line,sizeof line,f)) if (line[0]=='D') {
        unsigned kind,n,viewer,viewed,child;CHECK(sscanf(line+1,"%u %u %u %u %u",&kind,&n,&viewer,&viewed,&child)==5);
        BtpBld parent=r->buildings[kind];r->buildings[kind]=(BtpBld){.length=1,.bytes={0xff}};
        BtpState s;prerequisite(&s,n,42);s.story_flags[48]=(uint8_t)viewer;s.story_flags[50]=(uint8_t)viewed;
        btp_game_building(&s,r,kind);CHECK((s.disk_origin!=0)==child);
        if (child) CHECK(s.disk_origin==kind && btp_building_kind(r,&s)==18);
        input(&s,r,BTP_IDLE);r->buildings[kind]=parent;++disk_cases;
    }
    fclose(f);CHECK(disk_cases==24);
    const char *routes[]={"mayor-newspaper","mayor-holodisk","mayor-chow","cinema","inventor","inventor-qualified","laser-guns","alternate-services"};
    for (unsigned route=0;route<8;++route) {
        BtpState s;CHECK(btp_save_load(route==5 ? "Original DOS/GAME5" : "Original DOS/GAME3",&s,r,&e));
        char path[180];snprintf(path,sizeof path,"tests/fixtures/ordinary-%s.actions",routes[route]);f=fopen(path,"r");CHECK(f);
        unsigned ticks=0,films=0,house_menu=0,laser_menu=0,electronics=0,clothing=0;
        while (fgets(line,sizeof line,f)) {
            line[strcspn(line,"\r\n")]=0;BtpAction action;CHECK(btp_action_parse(line,&action));
            input(&s,r,action);++ticks;
            if (s.campaign.building==16 && s.cutscene.active) films|=1u<<s.cutscene.kind;
            house_menu|=s.mode==BTP_BUILDING && s.script.status==BTP_SCRIPT_MENU && s.script.menu_id==32;
            laser_menu|=s.service.action==41 && s.service.phase==10;
            electronics|=s.campaign.building==17 && s.script.status==BTP_SCRIPT_MENU;
            clothing|=s.campaign.building==12;
            CHECK(s.audio.sound_count<=1); /* E4 calls finish before the following film/effect. */
        }
        fclose(f);CHECK(ticks>200 && s.mode==BTP_EXPLORE);
        if (route<3) CHECK(house_menu);
        if (route==2) CHECK(s.party.people[0][15]==76);
        if (route==3) CHECK(films==927); /* THEATER.BLD uses O0..O4 and O7..O9. */
        if (route==4) CHECK(!s.story_flags[53] && !s.story_flags[54]);
        if (route==5) CHECK(s.story_flags[53] && s.story_flags[54]);
        if (route==6) { CHECK(laser_menu && s.party.people[0][11]==13);for (unsigned i=1;i<4;++i) CHECK(s.party.people[i][11]>=12); }
        if (route==7) CHECK(electronics && clothing && s.credits==15342507 && s.story_flags[30] && s.story_flags[48] && s.story_flags[49]);
    }
    unsigned alternatives=alternate_services(r)+story_branches(r);theater_pixels(r);
    free(r);printf("PASS: %u late-building checks, 46 native and %u complete BLD primary cases, eight saved ordinary routes\n",checks,alternatives);return 0;
}

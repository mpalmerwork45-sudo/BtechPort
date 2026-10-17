#include "data/content.h"
#include "data/save.h"
#include "core/menu.h"
#include "core/combat.h"
#include "core/combat_ai.h"
#include "core/npc.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static BtpError error;
static void same(const BtpState *a,const BtpState *b)
{
    uint8_t x[BTP_STATE_BYTES],y[BTP_STATE_BYTES];btp_state_encode(a,x);btp_state_encode(b,y);CHECK(!memcmp(x,y,sizeof x));
}
static void roundtrip(BtpState *s,const BtpResources *r)
{
    BtpState restored;CHECK(btp_save_write("work/lrm/held.btp",s,r,&error));
    CHECK(btp_save_is_updated("work/lrm/held.btp"));CHECK(btp_save_load("work/lrm/held.btp",&restored,r,&error));
    same(s,&restored);CHECK(!remove("work/lrm/held.btp"));
}
static void profiles(BtpResources *r)
{
    BtpState s,restored;btp_start(&s);btp_npc_init(&s,&r->map);
    uint8_t original[BTP_STATE_BYTES];btp_state_encode(&s,original);CHECK(original[4]==44);
    CHECK(r->combat_profile.fingerprint && !s.combat_profile);roundtrip(&s,r);
    CHECK(btp_set_combat_profile(&s,r,1));CHECK(btp_active_combat_profile(&s,r));
    for (unsigned slot=0;slot<6;++slot) {
        char path[256];s.menu.slot=(uint8_t)slot;
        CHECK(btp_save_edition_slot_path("work/lrm/slots.btp",slot,r,path,sizeof path,&error));
        CHECK(btp_save_write(path,&s,r,&error));CHECK(btp_save_load(path,&restored,r,&error));same(&s,&restored);CHECK(!remove(path));
    }
    CHECK(btp_save_write("work/lrm/held.btp",&s,r,&error));
    uint32_t fingerprint=r->combat_profile.fingerprint;r->combat_profile.fingerprint^=1;
    restored=s;CHECK(!btp_save_load("work/lrm/held.btp",&restored,r,&error));same(&s,&restored);
    r->combat_profile.fingerprint=fingerprint;CHECK(!remove("work/lrm/held.btp"));
    s.combat.phase=BTP_COMBAT_MENU;CHECK(!btp_set_combat_profile(&s,r,0));CHECK(s.combat_profile==1);s.combat.phase=0;
    CHECK(btp_set_combat_profile(&s,r,0));btp_state_encode(&s,original);CHECK(original[4]==44);
    btp_menu_open(&s);btp_menu_input(&s,r,BTP_DOWN);btp_menu_input(&s,r,BTP_ACCEPT);
    CHECK(s.campaign.ui==BTP_MENU_UPDATED_SETTINGS && btp_actions_count(&s)==7);roundtrip(&s,r);
    for (unsigned i=0;i<4;++i) btp_menu_input(&s,r,BTP_DOWN);
    btp_menu_input(&s,r,BTP_OPEN_MENU);CHECK(s.campaign.ui==BTP_MENU_COMBAT_RULES);roundtrip(&s,r);
    btp_menu_input(&s,r,BTP_UP);btp_menu_input(&s,r,BTP_OPEN_MENU);CHECK(s.combat_profile==1);roundtrip(&s,r);
    btp_menu_close(&s);CHECK(btp_set_combat_profile(&s,r,0));
    BtpRoster roster=r->roster;r->roster=(BtpRoster){0};CHECK(!btp_set_combat_profile(&s,r,1));
    btp_menu_open(&s);btp_menu_input(&s,r,BTP_DOWN);btp_menu_input(&s,r,BTP_ACCEPT);
    CHECK(s.campaign.ui==BTP_MENU_SETTINGS && btp_actions_count(&s)==6);r->roster=roster;
}
static void parser(const BtpCombatProfile *expected)
{
    BtpCombatProfile p=*expected;
    CHECK(btp_combat_profile_load("work/lrm/no-pack/roster.json",&p,error.text) && !p.fingerprint);
    const char *prefix="{\"format\":\"btp-combat-v1\",\"profile\":\"chi-updated-lrm-v1\",\"planner\":\"weapon-aware-v1\",";
    const char *cases[]={
        "\"distance_scale\":3,\"minimum_range\":6,\"short_range\":7,\"medium_range\":14,\"long_range\":21,\"weapons\":[\"lrm20\",\"lrm5\",\"lrm15\",\"lrm10\"]}",
        "\"distance_scale\":0,\"minimum_range\":6,\"short_range\":7,\"medium_range\":14,\"long_range\":21,\"weapons\":[\"lrm5\",\"lrm10\",\"lrm15\",\"lrm20\"]}",
        "\"distance_scale\":3,\"distance_scale\":3}","\"unknown\":1}","}","\"distance_scale\":03}",
        "\"distance_scale\":3,\"minimum_range\":6,\"short_range\":7,\"medium_range\":14,\"long_range\":21,\"weapons\":[\"lrm5\",\"lrm10\",\"lrm15\",\"lrm15\"]}"};
    for (unsigned i=0;i<sizeof cases/sizeof cases[0];++i) {
        FILE *f=fopen("work/lrm/combat.json","wb");CHECK(f);CHECK(fputs(prefix,f)>=0 && fputs(cases[i],f)>=0 && !fclose(f));
        p=*expected;int ok=btp_combat_profile_load("work/lrm/roster.json",&p,error.text);CHECK(ok==(i==0));CHECK(p.fingerprint==expected->fingerprint);
    }
    CHECK(!remove("work/lrm/combat.json"));
}
static void queries(BtpResources *r)
{
    static const unsigned footprint[][3]={{106,64,20},{108,64,21},{20,64,21},{64,108,21},{64,20,22},{80,80,21},{48,48,23},{81,79,21}};
    for (unsigned i=0;i<sizeof footprint/sizeof footprint[0];++i) {
        BtpCombatUnit a={.x=64,.y=64},b={.x=(uint8_t)footprint[i][0],.y=(uint8_t)footprint[i][1]};
        CHECK(btp_combat_shot_distance(&a,&b)==footprint[i][2]);
    }
    /* Independent expected boundaries. Infantry anchors bypass the original
       vehicle footprint; further scenarios exercise that adjustment. */
    static const unsigned distances[]={0,2,5,6,8,9,11,12,14,15,17,18,20,21,23,24,44,45,65,66};
    static const unsigned penalty[]={6,6,6,5,5,4,4,3,3,2,2,1,1,0,0,0,0,0,0,0};
    for (unsigned w=25;w<=28;++w) for (unsigned j=0;j<sizeof distances/sizeof distances[0];++j) {
        BtpCombatUnit a={.x=32,.y=32},b={.x=(uint8_t)(32+2*distances[j]),.y=32,.infantry=1};
        memcpy(a.record,r->combat.loans[0],125);memset(a.record+51,0,35);a.record[51]=(uint8_t)(w+1);a.record[39]=10;
        b.record[15]=80;BtpCombatUnit before=a,target=b;unsigned p=99;
        unsigned band=btp_combat_profile_range(&r->combat,&r->combat_profile,w,&a,&b,&p);
        CHECK(p==penalty[j]);CHECK(band==(j<15 ? 0u : j<17 ? 1u : j<19 ? 2u : 3u));
        BtpAttackQuery q=btp_combat_query(&a,&b,&r->combat,&r->combat_profile,0,-1,0,0,0,NULL);
        CHECK(!memcmp(&a,&before,sizeof a) && !memcmp(&b,&target,sizeof b));CHECK(q.valid==(band<3));
        if (q.valid) CHECK(q.needed==(int)(4+2*band+p));
        uint8_t rng[3]={1,2,3};BtpShot shot=btp_combat_attack_profile(&a,&b,&r->combat,0,-1,0,0,0,NULL,rng,&r->combat_profile);
        if (q.valid) { CHECK(shot.needed==q.needed);CHECK(a.record[39]==9 && a.pool==q.heat); }
        else CHECK(!memcmp(&a,&before,sizeof a));
    }
    for (unsigned w=15;w<33;++w) if (!btp_combat_profile_lrm(w)) {
        BtpCombatUnit a={.x=32,.y=32},b;memcpy(a.record,r->combat.loans[0],125);b=a;b.x=44;b.y=36;
        memset(a.record+51,0,35);a.record[51]=(uint8_t)(w+1);a.record[39]=10;
        unsigned index=w==32 ? 11u : 0u;
        BtpAttackQuery old=btp_combat_query(&a,&b,&r->combat,NULL,index,0,4,2,0,NULL);
        BtpAttackQuery newq=btp_combat_query(&a,&b,&r->combat,&r->combat_profile,index,0,4,2,0,NULL);CHECK(!memcmp(&old,&newq,sizeof old));
    }
}
static void battle_base(BtpState *s,const BtpResources *r)
{
    btp_start(s);btp_npc_init(s,&r->map);
    FILE *f=fopen("tests/fixtures/ordinary-combat.actions","r");CHECK(f);char line[128];
    while (s->combat.phase!=BTP_COMBAT_MENU && fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")]=0;BtpAction a;CHECK(btp_action_parse(line,&a));btp_game_tick(s,r,a);
    }
    CHECK(!fclose(f));CHECK(s->combat.phase==BTP_COMBAT_MENU);
}
static void manual_rules(BtpResources *r)
{
    BtpState base,s;battle_base(&base,r);BtpMap saved_map=r->map;memset(r->map.tiles,64,sizeof r->map.tiles);
    for (unsigned enhanced=0;enhanced<2;++enhanced) {
        s=base;s.combat_profile=(uint8_t)enhanced;s.combat_fingerprint=enhanced ? r->combat_profile.fingerprint : 0;
        BtpCombatState *c=&s.combat;c->unit[0].x=64;c->unit[0].y=64;c->unit[1].x=80;c->unit[1].y=64;
        c->unit[0].record[51]=26;c->unit[0].record[39]=10;s.mech_skills[0]=0;
        c->automatic=0;c->auto_run=0;c->graphics=0;s.menu.sound=0;s.menu.speed=0;
        c->phase=BTP_COMBAT_TARGET;c->weapon_selected=0;c->target_unit=1;c->target_selected=0;
        if (enhanced) CHECK(btp_save_write("work/lrm/target.btp",&s,r,&error));
        roundtrip(&s,r);c->phase=BTP_COMBAT_MENU;c->selected=9;
        memset(c->orders,255,sizeof c->orders);c->orders[0]=(uint8_t)btp_combat_id(c,1);c->kick_target=255;
        btp_combat_tick(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_ROUND);
        for (unsigned tick=0;tick<128 && !c->fired;++tick) btp_game_tick(&s,r,BTP_IDLE);
        CHECK(c->fired&1u);CHECK(c->shot.needed==(enhanced ? 9 : 4));CHECK(c->unit[0].record[39]==9);
        roundtrip(&s,r);
    }
    r->map=saved_map;
}
static void tactics(BtpResources *r)
{
    BtpState base,s,before;battle_base(&base,r);BtpMap map=r->map;memset(map.tiles,64,sizeof map.tiles);
    base.combat_profile=1;base.combat_fingerprint=r->combat_profile.fingerprint;
    static const unsigned models[]={2,4,10,14,15,16,21};
    for (unsigned i=0;i<sizeof models/sizeof models[0];++i) for (unsigned empty=0;empty<2;++empty) {
        s=base;BtpCombatUnit *a=&s.combat.unit[0],*t=&s.combat.unit[1];
        memcpy(a->record,r->roster.mechs[models[i]].record,125);a->x=32;a->y=64;a->heat=a->pool=0;
        memcpy(t->record,r->combat.jenner,125);t->x=(uint8_t)(empty ? 100 : 48);t->y=64;t->heat=t->pool=0;
        if (empty) for (unsigned w=0;w<10;++w) if (a->record[39+w]!=255) a->record[39+w]=0;
        before=s;BtpAiPlan p;CHECK(btp_combat_ai_plan(&s,r,&map,0,&p));same(&s,&before);
        unsigned distance=btp_combat_distance(p.x,p.y,t->x,t->y),start=btp_combat_distance(a->x,a->y,t->x,t->y),shots=0;
        for (unsigned w=0;w<12;++w) shots+=p.orders[w]!=255;
        printf("plan %-16.16s empty=%u distance=%u->%u mode=%u steps=%u shots=%u score=%d\n",a->record,empty,start,distance,p.movement,p.steps,shots,p.score);
        CHECK(p.candidates<=85 && p.steps<=12);
        if (i<3) CHECK(empty ? distance<start : distance>start);
        memset(map.tiles,255,sizeof map.tiles);CHECK(btp_combat_ai_plan(&s,r,&map,0,&p));CHECK(!p.steps);memset(map.tiles,64,sizeof map.tiles);
    }
}
int main(int argc,char **argv)
{
    CHECK(argc==2);BtpContent content={0};
    BtpOriginalContentPaths paths={argv[1],"work/talk-data.bin","work/combat-data.bin","work/world-data.bin"};
    CHECK(btp_content_load_original(&content,&paths,&error));
    CHECK(btp_content_select(&content,BTP_CONTENT_UPDATED,"content/updated/roster.json",&error));
    profiles(content.resources);parser(&content.resources->combat_profile);queries(content.resources);manual_rules(content.resources);tactics(content.resources);
    btp_content_close(&content);printf("Updated combat: %u checks passed\n",checks);return 0;
}

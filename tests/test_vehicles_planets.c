#include "core/events.h"
#include "core/combat.h"
#include "core/world.h"
#include "core/party.h"
#include "core/roster_game.h"
#include "core/menu.h"
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "data/unit_data.h"
#include "frontend/pixels.h"
#include "authored_walk.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static BtpError error;
static const char *capture;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"%s:%d %s: %s\n",__FILE__,__LINE__,#x,error.text);exit(1); } } while(0)
static void snapshot(const BtpState *s,const BtpResources *r,const char *label)
{
    if (capture) { char path[4096];snprintf(path,sizeof path,"%s-%s.btp",capture,label);CHECK(btp_save_write(path,s,r,&error)); }
}
static void action(BtpState *s,const BtpResources *r,BtpAction a)
{ btp_game_tick(s,r,a);CHECK(btp_events_valid(s,r)); }
static void roundtrip(BtpState *s,const BtpResources *r)
{
    BtpState copy;uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];
    CHECK(btp_save_write("vehicles-planets.btp",s,r,&error));CHECK(btp_save_load("vehicles-planets.btp",&copy,r,&error));
    btp_state_encode(s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));*s=copy;
}
static void rules(const BtpResources *r)
{
    const BtpDefinitions *d=&r->project->definitions;
    for (unsigned i=0;i<d->mech_count;++i) {
        BtpCombatUnit u={.x=40,.y=40},t={.x=42,.y=40,.direction=6};
        memcpy(u.record,r->roster.mechs[i].record,125);memcpy(t.record,r->roster.mechs[0].record,125);
        CHECK(btp_vehicle_kind(u.record)==d->mechs[i].vehicle);
        CHECK(btp_combat_points(&u,0)==(int)d->mechs[i].walk);
        CHECK(btp_combat_points(&u,1)==(int)((3*d->mechs[i].walk+1)/2));
        CHECK(!btp_combat_points(&u,2) && !btp_combat_can_kick(&u));
        CHECK(btp_combat_weapon_count(&u)==d->mechs[i].count);
        u.record[118]=2;CHECK(!btp_combat_points(&u,0));u.record[118]=0;
        u.heat=20;u.pool=15;btp_combat_cool(&u,1,8,0);CHECK(!u.heat && !u.pool);
        for (unsigned k=0;k<d->mechs[i].count;++k) CHECK(!btp_unit_weapon_definition(&r->combat,&u,k).heat);
        unsigned hits=0;
        for (unsigned seed=1;seed<70;++seed) {
            memcpy(t.record,r->roster.mechs[0].record,125);
            memset(t.record+17,1,19);u.record[39]=200;uint8_t rng[3]={(uint8_t)seed,11,53};
            BtpShot shot=btp_combat_attack_profile(&u,&t,&r->combat,0,0,0,4,0,NULL,rng,NULL);
            if (shot.hit) { ++hits;CHECK(shot.location==17 || shot.location==18 || shot.location==21 || shot.location==22 || shot.location==23);CHECK(!shot.toppled); }
        }
        CHECK(hits);
    }
    CHECK(btp_vehicle_terrain(3,15) && !btp_vehicle_terrain(1,15) && !btp_vehicle_terrain(2,15));
    CHECK(btp_vehicle_terrain(1,47) && !btp_vehicle_terrain(2,47) && !btp_vehicle_terrain(3,47));
    CHECK(btp_vehicle_terrain(1,31) && !btp_vehicle_terrain(2,31));
    for (unsigned k=1;k<=3;++k) CHECK(!btp_vehicle_terrain(k,85));
    BtpMap map={.width=64,.height=64,.authored=1};memset(map.tiles,15,sizeof map.tiles);
    for (unsigned i=0;i<4;i+=2) {
        BtpCombatUnit u={.x=40,.y=40},other={.x=60,.y=60};memcpy(u.record,r->roster.mechs[i].record,125);
        int8_t path[12][2];btp_combat_plan(&map,85,&u,&other,46,40,0,0,path);
        CHECK(i==2 ? path[0][0] || path[0][1] : !path[0][0] && !path[0][1]);
    }
}
int main(int argc,char **argv)
{
    CHECK(argc>=2 && argc<=4);capture=argc==4 ? argv[3] : NULL;
    BtpContent content={0};CHECK(btp_content_load_project(&content,argv[1],NULL,&error));const BtpResources *r=content.resources;
    CHECK(r->project->adventure.world_count==2);rules(r);
    BtpState *s=calloc(1,sizeof *s);CHECK(s);btp_start(s);s->project=1;CHECK(btp_set_combat_profile(s,r,1));btp_events_start(s,r);action(s,r,BTP_ACCEPT);
    CHECK(s->event.planet==1 && btp_world_seen(s,9,10));
    snapshot(s,r,"town");
    action(s,r,BTP_OPEN_MENU);action(s,r,BTP_UP);action(s,r,BTP_ACCEPT);
    CHECK(s->campaign.ui==BTP_MENU_MAP);snapshot(s,r,"overview");action(s,r,BTP_ACCEPT);
    action(s,r,BTP_OPEN_MENU);action(s,r,BTP_DOWN);action(s,r,BTP_DOWN);action(s,r,BTP_DOWN);
    action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);
    CHECK(s->campaign.ui==BTP_MENU_MECH);snapshot(s,r,"inspection");action(s,r,BTP_ACCEPT);
    /* Mark a distant discovery on planet one, then travel through an actual
       entrance. Planet two has a city at exactly the same coordinates. */
    s->explored[0]|=128;uint16_t origin=s->event.map;roundtrip(s,r);
    CHECK(authored_walk_to(s,r,"lab:shuttle-door",action));action(s,r,BTP_ACCEPT);CHECK(s->event.planet==2 && s->event.map!=origin);
    CHECK(!btp_world_seen(s,0,0));CHECK(s->explored[0]&128);action(s,r,BTP_ACCEPT);roundtrip(s,r);
    snapshot(s,r,"planet");
    if (argc>=3) { uint32_t *pixels=malloc(BTP_PIXELS*sizeof *pixels);CHECK(pixels);btp_render(r,s,0,pixels);CHECK(btp_write_ppm(argv[2],pixels));free(pixels); }
    CHECK(authored_walk_to(s,r,"lab:range-door",action));action(s,r,BTP_ACCEPT);
    CHECK(s->event.phase==BTP_EVENT_FIGHTING && s->event.planet==2);CHECK(s->combat.friends==3 && s->combat.count==5);roundtrip(s,r);
    snapshot(s,r,"combat");
    /* Enable normal computer orders via the three opening combat menus. */
    action(s,r,BTP_UP);action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);
    unsigned ticks=0;
    while (s->event.phase==BTP_EVENT_FIGHTING && ticks++<30000) {
        action(s,r,s->combat.phase==BTP_COMBAT_NOTICE ? BTP_ACCEPT : BTP_IDLE);
        if (!(ticks%128)) roundtrip(s,r);
    }
    CHECK(ticks<30000 && s->event.phase==BTP_EVENT_TEXT);CHECK(!strcmp(r->project->adventure.nodes[s->event.node].id,"lab:won"));roundtrip(s,r);snapshot(s,r,"victory");action(s,r,BTP_ACCEPT);
    CHECK(authored_walk_to(s,r,"lab:return-door",action));action(s,r,BTP_ACCEPT);
    CHECK(s->event.planet==1 && btp_world_seen(s,0,0));roundtrip(s,r);
    CHECK(authored_walk_to(s,r,"lab:depot-door",action));action(s,r,BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_TRADING);
    snapshot(s,r,"depot");
    /* Vehicles use a single scrollable catalogue and never leak into mech
       weight classes. Back returns directly to the Vehicles hub item. */
    action(s,r,BTP_ACCEPT);CHECK(s->campaign.ui==BTP_MENU_BROKER_CLASSES);
    for (unsigned cls=1;cls<=4;++cls) {
        unsigned indices[BTP_ROSTER_MAX];CHECK(!btp_events_catalogue(s,r,cls,r->roster.count,indices));
    }
    action(s,r,BTP_CANCEL);action(s,r,BTP_DOWN);action(s,r,BTP_OPEN_MENU);
    CHECK(s->campaign.ui==BTP_MENU_BROKER && s->menu.broker_class==BTP_ROSTER_VEHICLES);
    CHECK(s->menu.map_x==10);roundtrip(s,r);snapshot(s,r,"vehicle-catalogue");
    for (unsigned i=0;i<9;++i) action(s,r,BTP_DOWN);
    CHECK(s->campaign.member>0);roundtrip(s,r);
    action(s,r,BTP_CANCEL);CHECK(s->campaign.ui==BTP_MENU_BROKER_HUB && s->campaign.selected==1);
    CHECK(btp_broker_buy(s,r,1)==BTP_BROKER_BOUGHT);roundtrip(s,r);
    CHECK(!remove("vehicles-planets.btp"));free(s);btp_content_close(&content);
    puts("PASS: vehicle rules, terrain, two planets, ordinary transfers/combat/shop, independent discovery and save/load.");return 0;
}

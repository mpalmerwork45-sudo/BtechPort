#include "core/animation.h"
#include "core/combat.h"
#include "core/events.h"
#include "core/party.h"
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static BtpError error;
static BtpState *s,*saved,*loaded;
static BtpResources *r;
static BtpScene *scene,*original;
static uint8_t *encoded,*restored;
static unsigned speech;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"%s:%d: %s (%s) xy=%u,%u mode=%u phase=%u blocked=%u\n",__FILE__,__LINE__,#x,error.text,s?s->x_half:0,s?s->y_half:0,s?s->mode:0,s?s->event.phase:0,s?s->blocked:0);exit(1); } } while (0)

static void formation(void)
{
    /* Check actual saved drawing positions as well as the cursor gate. A
       follower can otherwise remain legal while silently falling behind. */
    CHECK(btp_party_can_stand(s,r,s->campaign.world_x,s->campaign.world_y));
    unsigned foot=0,mech=0;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][12]>=8) {
        int x=(int)s->campaign.world_x+r->combat.formation_x[foot];
        int y=(int)s->campaign.world_y+r->combat.formation_y[foot++];
        CHECK(s->party.x[i]==x && s->party.y[i]==y);
        CHECK(btp_party_walkable(s,r,x,y,0));
    }
    for (unsigned i=0;i<4;++i) if (btp_party_mech(s,i)[0]!=255) {
        int x=(int)s->campaign.world_x+r->combat.mech_formation_x[mech];
        int y=(int)s->campaign.world_y+r->combat.mech_formation_y[mech++];
        CHECK(s->party.mech_x[i]==x && s->party.mech_y[i]==y);
        CHECK(btp_party_walkable(s,r,x,y,1));
    }
    CHECK(foot+mech>=2);
}
static void fresh(unsigned x,unsigned y,unsigned mechs,unsigned foot)
{
    /* Only the loaded heap scene is modified. Its declarations and strict
       package digest stay intact; no fixture or game asset is rewritten. */
    *scene=*original;memset(scene->rules.tiles,64,sizeof scene->rules.tiles);scene->entrance_count=0;
    btp_start(s);s->project=1;CHECK(btp_set_combat_profile(s,r,1));
    CHECK(btp_events_preview(s,r,scene->id,x,y));s->menu.steps=1;
    CHECK(btp_party_count(&s->party)==2);
    for (unsigned i=2;i<mechs;++i) {
        uint8_t *m=btp_party_mech(s,i);memcpy(m,s->campaign.mech,125);
        m[121]=m[122]=255;s->party.mech_types[i]=m[0];
    }
    for (unsigned i=0;i<foot;++i) btp_party_allocate(s,i,4,121);
    btp_party_recover(s,r,1);formation();
}
static void door(unsigned x,unsigned y)
{
    scene->entrance_count=1;
    scene->entrances[0]=(BtpSceneEntrance){.x=(uint8_t)x,.y=(uint8_t)y,.person=255,.event=(uint16_t)speech};
    strcpy(scene->entrances[0].id,"test:door");strcpy(scene->entrances[0].name,"Movement test");
}
static void wall(unsigned x,unsigned y)
{ CHECK(x<scene->rules.width && y<scene->rules.height);scene->rules.tiles[y*scene->rules.width+x]=255; }
static void tick(BtpAction action)
{ btp_game_tick(s,r,action); }
static void walk(BtpAction action,unsigned steps,unsigned count)
{
    s->menu.steps=(uint8_t)steps;
    while (count--) {
        unsigned x=s->x_half,y=s->y_half;
        tick(action);CHECK(s->mode==BTP_EXPLORE && s->blocked==BTP_CLEAR);
        CHECK((int)s->x_half==(int)x+(int)steps*btp_action_dx(action));
        CHECK((int)s->y_half==(int)y+(int)steps*btp_action_dy(action));formation();
    }
}
static void held_entry(void)
{
    CHECK(s->mode==BTP_EVENT && s->event.phase==BTP_EVENT_ENTRY);
    CHECK(btp_save_write("authored-movement-roundtrip.btp",s,r,&error));
    CHECK(btp_save_load("authored-movement-roundtrip.btp",loaded,r,&error));
    btp_state_encode(s,encoded);btp_state_encode(loaded,restored);
    CHECK(!memcmp(encoded,restored,BTP_STATE_BYTES));
}
static void same_continuation(BtpAction action)
{
    /* The entry payload already contains its origin/door. Replaying Yes or
       No after loading must commit exactly the same pending half-step. */
    held_entry();tick(action);*saved=*s;*s=*loaded;tick(action);
    btp_state_encode(s,encoded);btp_state_encode(saved,restored);
    CHECK(!memcmp(encoded,restored,BTP_STATE_BYTES));
}
static void movement(void)
{
    fresh(14,14,4,0);
    /* Cross 16-half-step terrain boundaries repeatedly. Authored scenes
       must never consult the generated world underneath their own roads. */
    walk(BTP_RIGHT,1,4);walk(BTP_RIGHT,2,4);walk(BTP_RIGHT,4,4);
    walk(BTP_DOWN,1,4);walk(BTP_DOWN,2,4);walk(BTP_DOWN,4,4);
    walk(BTP_UP_LEFT,4,4);walk(BTP_DOWN_RIGHT,2,5);walk(BTP_UP_LEFT,1,8);
    walk(BTP_LEFT,4,4);walk(BTP_UP,4,4);
    CHECK(s->x_half==12 && s->y_half==12);
    /* A legal but detached follower should rejoin on an ordinary accepted
       move, without needing the space menu or a scene-transition recovery. */
    s->party.mech_x[1]=(uint16_t)(s->party.mech_x[1]+10);
    CHECK(btp_party_walkable(s,r,s->party.mech_x[1],s->party.mech_y[1],1));
    walk(BTP_RIGHT,1,1);
    fresh(24,30,4,0);
    /* Only the third mech's outer footprint meets this vertical wall strip.
       The leading mech remains clear, but the complete step is rejected. */
    wall(15,15);wall(15,16);wall(15,17);
    CHECK(btp_party_walkable(s,r,(int)s->campaign.world_x+1,(int)s->campaign.world_y-2,1));
    CHECK(!btp_party_can_stand(s,r,(int)s->campaign.world_x+1,s->campaign.world_y));
    *saved=*s;s->menu.steps=4;tick(BTP_RIGHT);
    CHECK(s->x_half==saved->x_half && s->y_half==saved->y_half && s->blocked==BTP_WALL);
    CHECK(!memcmp(s->party.mech_x,saved->party.mech_x,sizeof s->party.mech_x));
    CHECK(!memcmp(s->party.mech_y,saved->party.mech_y,sizeof s->party.mech_y));formation();
    /* A four-step key must stop at the intermediate blocked step, rather
       than checking only its final cursor or leaving one vehicle behind. */
    fresh(24,30,4,0);wall(16,15);s->menu.steps=4;tick(BTP_RIGHT);
    CHECK(s->x_half==26 && s->y_half==30 && s->blocked==BTP_WALL);formation();
    /* Foot soldiers use their own compact offsets even while active mechs
       accompany them, and every displayed person must move with the group. */
    fresh(14,14,2,2);walk(BTP_RIGHT,4,5);walk(BTP_DOWN_RIGHT,2,4);walk(BTP_UP_LEFT,1,4);
}
static void gait(void)
{
    static const unsigned steps[]={1,2,4};
    for (unsigned i=0;i<3;++i) for (unsigned blocked=0;blocked<2;++blocked) {
        fresh(25,30,2,0);s->menu.steps=(uint8_t)steps[i];
        s->facing=BTP_RIGHT;s->campaign.mech_direction=2;s->campaign.mech_walk=6;
        s->player_walk=4;s->party.direction[1]=2;s->party.walk[1]=6;
        if (blocked) wall(14,14);
        tick(BTP_RIGHT);
        CHECK(s->campaign.mech_walk==7 && s->party.walk[1]==7 && s->player_walk==5);
        CHECK(s->party.direction[1]==2 && s->campaign.mech_direction==2);
        CHECK(s->x_half==25+(blocked ? 0 : steps[i]));
        if (!blocked) formation();
    }
    for (unsigned i=0;i<3;++i) {
        fresh(24,30,2,2);s->menu.steps=(uint8_t)steps[i];
        s->facing=BTP_RIGHT;s->player_walk=4;s->party.direction[1]=2;s->party.walk[1]=4;
        tick(BTP_RIGHT);CHECK(s->player_walk==5 && s->party.walk[1]==5);formation();
    }
}
static void entrances(void)
{
    /* The second mech, six half-steps behind the first ground anchor, can
       touch a door with either edge. A cursor-only test misses this door. */
    fresh(24,30,2,0);door(26,34);s->menu.steps=4;tick(BTP_RIGHT);
    CHECK(s->event.phase==BTP_EVENT_ENTRY && s->event.origin_entry==0 && s->x_half==24);
    unsigned leader_walk=s->campaign.mech_walk,follower_walk=s->party.walk[1];
    same_continuation(BTP_CANCEL);
    CHECK(s->mode==BTP_EXPLORE && s->x_half==25 && s->y_half==30);formation();
    CHECK(s->campaign.mech_walk==leader_walk && s->party.walk[1]==follower_walk);
    /* Accepting uses the same held continuation, without walking through a
       building to make the event fire. */
    fresh(24,30,2,0);door(24,34);tick(BTP_RIGHT);
    same_continuation(BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_TEXT && s->event.node==speech && s->x_half==24);
    /* The member's doorway is checked before its own wall. Declining the
       prompt must still respect the complete formation collision test. */
    fresh(25,30,2,0);door(27,34);wall(14,17);tick(BTP_RIGHT);
    CHECK(s->event.phase==BTP_EVENT_ENTRY);same_continuation(BTP_CANCEL);
    CHECK(s->mode==BTP_EXPLORE && s->x_half==25 && s->y_half==30);
    /* Infantry require exact contact: a one-half-step horizontal near miss
       must not receive the wider mech-door treatment. */
    fresh(24,30,2,2);door(26,29);tick(BTP_RIGHT);
    CHECK(s->mode==BTP_EXPLORE && s->x_half==25);formation();
    fresh(24,30,2,2);door(25,29);tick(BTP_RIGHT);
    CHECK(s->event.phase==BTP_EVENT_ENTRY && s->x_half==24);
    same_continuation(BTP_CANCEL);CHECK(s->x_half==25);formation();
    /* A blocked earlier infantry member ends the original drawing-order
       scan, so a later mech may not activate a door across that obstacle. */
    fresh(24,30,2,2);door(26,34);wall(13,15);tick(BTP_RIGHT);
    CHECK(s->mode==BTP_EXPLORE && s->event.phase==BTP_EVENT_INACTIVE && s->x_half==24 && s->blocked==BTP_WALL);
    /* Once an NPC has joined, its stationary map marker cannot open another
       conversation merely because the party touches its old location. */
    fresh(24,30,2,0);door(26,34);scene->entrances[0].person=s->event.people[1];tick(BTP_RIGHT);
    CHECK(s->mode==BTP_EXPLORE && s->x_half==25);formation();
}
int main(int argc,char **argv)
{
    CHECK(argc==6);BtpOriginalContentPaths paths={argv[1],argv[2],argv[3],argv[4]};BtpContent content={0};
    CHECK(btp_content_load_project(&content,argv[5],&paths,&error));r=content.resources;
    s=calloc(1,sizeof *s);saved=malloc(sizeof *saved);loaded=malloc(sizeof *loaded);
    original=malloc(sizeof *original);encoded=malloc(BTP_STATE_BYTES);restored=malloc(BTP_STATE_BYTES);
    CHECK(s && saved && loaded && original && encoded && restored);
    scene=&r->project->adventure.maps[0];*original=*scene;
    speech=0;while (speech<r->project->adventure.node_count && r->project->adventure.nodes[speech].op!=BTP_EVENT_SAY) ++speech;
    CHECK(speech<r->project->adventure.node_count);
    /* These offsets are independently captured in field-primary.txt; the
       controlled wall/door placements below depend on that original layout. */
    CHECK(r->combat.formation_x[0]==0 && r->combat.formation_y[0]==0 && r->combat.formation_x[1]==0 && r->combat.formation_y[1]==-1);
    CHECK(r->combat.mech_formation_x[0]==0 && r->combat.mech_formation_y[0]==-2 && r->combat.mech_formation_x[1]==0 && r->combat.mech_formation_y[1]==4);
    CHECK(r->combat.mech_formation_x[2]==3 && r->combat.mech_formation_y[2]==1);
    movement();gait();entrances();*scene=*original;
    CHECK(!remove("authored-movement-roundtrip.btp"));
    free(restored);free(encoded);free(original);free(loaded);free(saved);free(s);btp_content_close(&content);
    puts("PASS: authored compact formations, all-member walls, per-key gait, ground-anchor doors and saved entry continuations.");return 0;
}

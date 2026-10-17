#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "data/unit_data.h"
#include "data/digest.h"
#include "core/roster_game.h"
#include "core/party.h"
#include "core/npc.h"
#include "core/menu.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s (%s)\n",__FILE__,__LINE__,#x,error.text);exit(1); } } while (0)
static BtpError error;
static void same(const BtpState *a,const BtpState *b)
{
    uint8_t x[BTP_STATE_BYTES],y[BTP_STATE_BYTES];btp_state_encode(a,x);btp_state_encode(b,y);CHECK(!memcmp(x,y,sizeof x));
}
static void roundtrip(BtpState *s,BtpState *copy,const BtpResources *r)
{
    CHECK(btp_save_write("project-test-save.btp",s,r,&error));
    CHECK(btp_save_load("project-test-save.btp",copy,r,&error));same(s,copy);
    CHECK(!remove("project-test-save.btp"));
}
static void export_equivalence(BtpContent *c,const char *roster)
{
    CHECK(btp_content_select(c,BTP_CONTENT_UPDATED,roster,&error));
    BtpResources *r=c->resources;
    CHECK(btp_definitions_export("project-test-content.json",&r->roster,&r->combat,&r->combat_profile,error.text));
    BtpDefinitions *d=calloc(1,sizeof *d);BtpRoster *compiled=calloc(1,sizeof *compiled);CHECK(d && compiled);
    CHECK(btp_definitions_load("project-test-content.json",d,error.text));CHECK(btp_definitions_compile(d,compiled,error.text));
    CHECK(compiled->count==r->roster.count && compiled->count==31);
    CHECK(d->rules.fingerprint==r->combat_profile.fingerprint);
    r->combat.definitions=d;
    for (unsigned i=0;i<r->roster.count;++i) {
        const BtpRosterMech *old=&r->roster.mechs[i],*now=&compiled->mechs[i];
        CHECK(!strcmp(old->id,now->id) && old->price==now->price);
        CHECK(!memcmp(old->record,now->record,123) && !memcmp(old->ammo_cost,now->ammo_cost,10));
        CHECK(btp_mech_record_sprite(old->record,0)==btp_mech_record_sprite(now->record,0));
        BtpCombatUnit a={.x=10,.y=60},b=a,target={.y=60};memcpy(a.record,old->record,125);memcpy(b.record,now->record,125);memcpy(target.record,r->combat.loans[0],125);
        unsigned mounts=btp_combat_weapon_count(&a);CHECK(mounts==btp_combat_weapon_count(&b));
        for (unsigned policy=0;policy<2;++policy) for (unsigned mount=0;mount<mounts;++mount) for (unsigned distance=1;distance<100;distance+=3) {
            target.x=(uint8_t)(10+distance);const BtpCombatProfile *p=policy ? &r->combat_profile : NULL;
            BtpAttackQuery x=btp_combat_query(&a,&target,&r->combat,p,mount,0,0,2,0,NULL);
            BtpAttackQuery y=btp_combat_query(&b,&target,&r->combat,p,mount,0,0,2,0,NULL);
            CHECK(x.valid==y.valid && x.band==y.band && x.minimum==y.minimum && x.needed==y.needed && x.heat==y.heat && x.hit36==y.hit36 && x.damage36==y.damage36);
        }
    }
    r->combat.definitions=NULL;CHECK(!remove("project-test-content.json"));free(d);free(compiled);
}
static void custom_rules(BtpResources *r)
{
    BtpCombatUnit actor={.x=10,.y=10},target={.x=12,.y=10};memcpy(actor.record,r->roster.mechs[0].record,125);memcpy(target.record,r->combat.loans[0],125);
    BtpWeaponDefinition hot=btp_unit_weapon_definition(&r->combat,&actor,0),cool=btp_unit_weapon_definition(&r->combat,&actor,1);
    CHECK(!strcmp((const char *)hot.name,"Ember Beam") && !strcmp((const char *)cool.name,"Cool Beam"));
    CHECK(hot.damage==7 && hot.heat==4 && cool.damage==2 && !cool.heat);
    /* Same behavior family, independently authored stats; neither mount may
       patch the original medium laser or the other mount's definition. */
    CHECK(btp_combat_weapon(&actor,0)==btp_combat_weapon(&actor,1));
    CHECK(btp_weapon_definition(&r->combat,16).damage==5);
    BtpBattleText report={.active=1,.actor=0,.target=12,.weapon=16,.hit=1,.location=17,.authored=1,.content_weapon=0};
    uint8_t message[1024];size_t length=btp_battle_text(r,&report,1,message);message[length]=0;
    CHECK(strstr((const char *)message,"Ember Beam") && !strstr((const char *)message,"Med Laser"));
    uint8_t rng[3]={31,66,171};
    BtpShot shot=btp_combat_attack_profile(&actor,&target,&r->combat,0,-1,0,20,0,NULL,rng,NULL);
    CHECK(shot.hit && shot.damage==7 && actor.pool==4);
    shot=btp_combat_attack_profile(&actor,&target,&r->combat,1,-1,0,20,0,NULL,rng,NULL);
    CHECK(shot.hit && shot.damage==2 && actor.pool==4);
    target.x=54;CHECK(btp_combat_mount_range(&r->combat,NULL,&actor,&target,0,NULL)==2);
    CHECK(btp_combat_mount_range(&r->combat,NULL,&actor,&target,1,NULL)==3);
}
int main(int argc,char **argv)
{
    CHECK(argc==7);BtpOriginalContentPaths paths={argv[1],argv[2],argv[3],argv[4]};BtpContent c={0};
    BtpDigest hash;uint8_t digest[32];btp_digest_start(&hash);btp_digest_add(&hash,"abc",3);btp_digest_finish(&hash,digest);
    const uint8_t known[]={0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};CHECK(!memcmp(digest,known,32));
    CHECK(btp_content_load_original(&c,&paths,&error));export_equivalence(&c,argv[5]);
    CHECK(btp_content_load_project(&c,argv[6],&paths,&error));BtpResources *r=c.resources;CHECK(c.profile==BTP_CONTENT_PROJECT && r->project && r->roster.count==2);
    custom_rules(r);
    BtpResources *before=c.resources;CHECK(!btp_content_load_project(&c,"no-such-project",&paths,&error));CHECK(c.resources==before && c.profile==BTP_CONTENT_PROJECT);
    BtpState *s=calloc(1,sizeof *s),*copy=calloc(1,sizeof *copy);CHECK(s && copy);
    btp_start(s);s->project=1;btp_npc_init(s,&r->map);CHECK(btp_set_combat_profile(s,r,1));roundtrip(s,copy,r);
    s->effects.shown=(BtpBattleText){.active=1,.actor=0,.target=12,.weapon=16,.hit=1,.location=17,.authored=1,.content_weapon=1};
    roundtrip(s,copy,r);s->effects.shown=(BtpBattleText){0};
    CHECK(btp_save_write("project-test-save.btp",s,r,&error));
    r->project->digest[0]^=1;*copy=*s;copy->credits=999;BtpState *snapshot=malloc(sizeof *snapshot);CHECK(snapshot);*snapshot=*copy;
    CHECK(!btp_save_load("project-test-save.btp",copy,r,&error));same(snapshot,copy);
    CHECK(!btp_save_write("project-test-save.btp",copy,r,&error));r->project->digest[0]^=1;
    CHECK(btp_save_load("project-test-save.btp",copy,r,&error));same(s,copy);CHECK(!remove("project-test-save.btp"));free(snapshot);
    for (unsigned slot=0;slot<6;++slot) {
        char path[128];CHECK(btp_save_edition_slot_path("party.btp",slot,r,path,sizeof path,&error));CHECK(strstr(path,"-project-workshop"));
    }
    /* The high catalogue handle (including 200, an original salvage sentinel)
       must work independently of the old 160..191 save-code range. */
    BtpDefinitions *d=&r->project->definitions;
    for (unsigned i=2;i<256;++i) { d->mechs[i]=d->mechs[0];snprintf(d->mechs[i].id,64,"workshop:unit-%u",i); }
    d->mech_count=256;CHECK(btp_definitions_compile(d,&r->roster,error.text));
    btp_start(s);s->project=1;s->story_flags[4]=1;s->story_flags[36]=127;s->map_id=2;s->x_half=54;s->y_half=51;
    s->campaign.world_x=1334;s->campaign.world_y=1075;s->credits=200000;btp_npc_enter(s,&r->local[1]);btp_party_init(s);
    btp_game_tick(s,r,BTP_UP);CHECK(s->mode==BTP_ENTRY);btp_game_tick(s,r,BTP_ACCEPT);CHECK(btp_broker_available(s,r));
    CHECK(btp_broker_buy(s,r,255)==BTP_BROKER_BOUGHT);CHECK(btp_roster_definition(&r->roster,s->campaign.mech)==&r->roster.mechs[255]);roundtrip(s,copy,r);
    s->campaign.ui=BTP_MENU_BROKER;s->campaign.member=249;s->campaign.selected=6;s->menu.map_x=256;s->menu.map_y=255;
    roundtrip(s,copy,r);btp_game_tick(s,r,BTP_DOWN);roundtrip(s,copy,r);btp_game_tick(s,r,BTP_UP);roundtrip(s,copy,r);
    CHECK(btp_content_select(&c,BTP_CONTENT_ORIGINAL_DOS_103,NULL,&error));CHECK(!c.resources->project && !c.resources->combat.definitions);
    free(s);free(copy);btp_content_close(&c);printf("PASS: %u project/content checks\n",checks);return 0;
}

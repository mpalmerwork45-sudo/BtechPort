/* Synthetic campaign settings/mechanics. No original assets required. */
#include "data/chi_missions.h"
#include "data/project.h"
#include "core/training.h"
#include "core/combat.h"
#include "core/campaign.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static BtpError error;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"CHI mission line %d: %s (%s)\n",__LINE__,#x,error.text);exit(1); } } while (0)
static int load(BtpResources *r,BtpChiMissions *c,const char *body)
{
    memset(c,0,sizeof *c);FILE *f=fopen("chi-missions-test.json","wb");CHECK(f);
    fprintf(f,"{\"format\":\"btp-chi-missions-v1\",\"schema_version\":1,\"parameters\":{%s}}",body);CHECK(!fclose(f));
    BtpDigest digest;btp_digest_start(&digest);error.text[0]=0;
    int ok=btp_chi_missions_load(".","chi-missions-test.json",c,r,&digest,&error);CHECK(!remove("chi-missions-test.json"));return ok;
}
int main(void)
{
    BtpResources *r=calloc(1,sizeof *r);BtpProject *p=calloc(1,sizeof *p);BtpChiMissions *c=calloc(1,sizeof *c);BtpState *s=calloc(1,sizeof *s);
    CHECK(r && p && c && s);r->project=p;p->chi_missions=c;
    for (unsigned i=0;i<7;++i) r->combat.cache_password[i]=(uint16_t)i;
    r->map.width=r->map.height=64;memset(r->map.tiles,64,sizeof r->map.tiles);r->combat.loans[0][0]='L';r->combat.jenner[0]='J';
    CHECK(load(r,c,"\"training.4.enemy_count\":2,\"training.4.control_prompt\":1,\"training.4.start_x\":68,\"training.4.return_x\":70,\"training.4.pass_on_retreat\":1,\"encounter.cash_base\":40,\"encounter.cash_mask\":0,\"quiz.rounds\":4"));
    CHECK(btp_chi_training(r,4,BTP_TRAIN_START_X)==68 && btp_chi_training(r,3,BTP_TRAIN_START_X)==64);
    btp_start(s);s->mode=BTP_MISSION;s->mission.phase=BTP_MISSION_DRIVE;s->mission.assignment=4;
    btp_combat_begin(s,r);CHECK(s->combat.count==3 && s->combat.phase==BTP_COMBAT_CONTROL && s->combat.unit[0].x==68);
    CHECK(s->combat.unit[2].x==s->combat.unit[1].x+4 && s->combat.unit[2].y==s->combat.unit[1].y);
    s->combat.phase=0;s->combat.fled=1;s->mission.corner=1;s->x_half=70;s->y_half=77;
    CHECK(btp_mission_tick(s,r,BTP_IDLE) && s->story_flags[1] && s->mission.phase==BTP_MISSION_RESULT);
    uint8_t rng[3]={31,66,171};CHECK(btp_aftermath_cash_resources(rng,8,r)==320);
    char text[64];CHECK(btp_chi_service_expand(r,"{mission:training.4.enemy_count}",text,sizeof text));CHECK(!strcmp(text,"2"));
    CHECK(!btp_chi_service_expand(r,"{mission:missing}",text,sizeof text));
    strcpy(c->units[BTP_MUNIT_TRAINING_4_ENEMY_0],"native:jenner.0");
    CHECK(btp_chi_missions_resolve(c,r,&r->roster,&error));CHECK(btp_chi_mission_unit(r,BTP_MUNIT_TRAINING_4_ENEMY_0)[0]=='J');
    strcpy(c->units[BTP_MUNIT_TRAINING_4_ENEMY_0],"unknown:unit");CHECK(!btp_chi_missions_resolve(c,r,&r->roster,&error));
    const char *bad[]={"\"training.4.enemy_count\":7","\"training.4.enemy_count\":4,\"training.4.count_mask\":3", "\"training.0.invasion\":2",
        "\"quiz.rounds\":0","\"training.4.return_y_min\":90","\"cache.door.0.x\":3", "\"cache.password.1\":0",
        "\"arena.escape_min\":1300","\"arena.rental_roll_base\":10","\"arena.spawn_y\":118,\"guards.offset.0.y\":8","\"encounter.offer\":true","\"start.credits\":-1","\"unknown\":0",
        "\"start.credits\":1,\"start.credits\":2","\"training.3.shell\":1","\"training.2.shell_x\":124,\"training.2.enemy.0.x\":10"};
    for (unsigned i=0;i<sizeof bad/sizeof *bad;++i) CHECK(!load(r,c,bad[i]));
    free(s);free(c);free(p);free(r);puts("Native mission contracts, count/control/formation/outcome changes, rewards, unit references and bounded failures pass.");return 0;
}

#include "core/training.h"
#include "core/combat.h"
#include "core/npc.h"
#include "core/world.h"
#include "data/save.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static uint64_t hash(const uint8_t *b,size_t n) {
    uint64_t h=UINT64_C(14695981039346656037);
    for (size_t i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);
    return h;
}
int main(int argc,char **argv)
{
    if (argc!=3) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r);
    CHECK(btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    FILE *f=fopen("tests/fixtures/invasion-setup.txt","r");CHECK(f);char row[600];unsigned cases=0;
    while (fgets(row,sizeof row,f)) if (row[0]=='P') {
        unsigned assignment,seed,invasion,count,rng;int used;
        CHECK(sscanf(row+1,"%u %u %u %u %u%n",&assignment,&seed,&invasion,&count,&rng,&used)==5);
        BtpState s;btp_start(&s);s.story_flags[0]=(uint8_t)assignment;
        s.script=(BtpScriptState){.status=BTP_SCRIPT_NATIVE,.native_action=1};
        for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));
        btp_training_native(&s,r);
        CHECK(s.campaign.invasion==invasion && s.combat.count==count);
        CHECK((unsigned)s.npc.rng[0]+((unsigned)s.npc.rng[1]<<8)+((unsigned)s.npc.rng[2]<<16)==rng);
        char *at=row+1+used;
        for (unsigned i=1;i<count;++i) {
            unsigned x,y;uint64_t record;CHECK(sscanf(at,"%u %u %" SCNx64 "%n",&x,&y,&record,&used)==3);at+=used;
            CHECK(s.combat.unit[i].x==x+(invasion ? 64u : 0u) && s.combat.unit[i].y==y+(invasion ? 64u : 0u));
            CHECK(hash(s.combat.unit[i].record,125)==record);
        }
        if (invasion) {
            BtpMap terrain;btp_combat_map(r,&s,&terrain);CHECK(terrain.width==128 && terrain.height==128);
            CHECK(btp_map_tile(&terrain,32+56,32+63)==btp_map_tile(&r->map,56,63));
            CHECK(btp_map_tile(&terrain,100,100)==btp_world_tile(r,&s,836,836));
        }
        ++cases;
    }
    fclose(f);CHECK(cases==16);
    f=fopen("tests/fixtures/movement-obstacles-primary.txt","r");CHECK(f);unsigned obstacle_cases=0;
    while (fgets(row,sizeof row,f)) {
        if (row[0]=='P') {
            unsigned tile,mode;uint64_t expected;CHECK(sscanf(row+1,"%u %u %" SCNx64,&tile,&mode,&expected)==3);
            BtpMap m={.width=64,.height=64};memset(m.tiles,64,4096);
            for (unsigned y=0;y<64;++y) m.tiles[y*64+49]=m.tiles[y*64+50]=(uint8_t)tile;
            BtpCombatUnit u={.x=96,.y=93,.direction=2};memcpy(u.record,r->combat.loans[2],125);int8_t path[12][2];
            btp_combat_plan(&m,85,&u,NULL,105,93,mode,0,path);CHECK(hash((const uint8_t *)path,sizeof path)==expected);
        } else {
            unsigned x,y,result;CHECK(sscanf(row+1,"%u %u %u",&x,&y,&result)==3);
            CHECK(btp_invasion_outside(x,y)==(result==2));
        }
        ++obstacle_cases;
    }
    fclose(f);CHECK(obstacle_cases==40);
    BtpState s;btp_start(&s);f=fopen(argv[2],"r");CHECK(f);
    uint8_t saved[BTP_STATE_BYTES],again[BTP_STATE_BYTES];unsigned actions=0,animation=0,invasion_popups=0,destroyed_during_fight=0,migration=0;
    while (fgets(row,sizeof row,f)) {
        row[strcspn(row,"\r\n")]=0;BtpAction a;CHECK(btp_action_parse(row,&a));
        btp_game_tick(&s,r,a);animation|=s.cutscene.kind==9;
        if (!migration && s.campaign.invasion && s.combat.phase==BTP_COMBAT_MENU) {
            /* Re-encode this real held invasion in the v29 cropped frame.
               Both current and parked per-actor orders must migrate. */
            BtpState modern=s;BtpCombatState *c=&modern.combat;
            /* This fixture isolates coordinate migration. Pre-v34 decorative
               marks have no recoverable world origin and migrate to empty. */
            memset(modern.terrain_marks,0,sizeof modern.terrain_marks);modern.terrain_next=0;
            /* v29 also predates saved battle reports. Omit those new fields
               from both sides of this coordinate-only migration fixture. */
            memset(modern.effects.text,0,sizeof modern.effects.text);
            modern.effects.shown=(BtpBattleText){0};c->shot.criticals=0;
            c->phase=BTP_COMBAT_MOVE;c->movement=1;c->goal_active=1;c->goal_x=130;c->goal_y=140;
            c->cursor_x=132;c->cursor_y=142;c->waypoint_count=1;c->waypoint_x[0]=136;c->waypoint_y[0]=146;
            c->plans[0].active=1;c->plans[0].movement=1;c->plans[0].x=130;c->plans[0].y=140;
            c->plans[0].count=1;c->plans[0].wx[0]=136;c->plans[0].wy[0]=146;
            c->plans[1].x=140;c->plans[1].y=150;
            BtpState old=modern;old.x_half-=64;old.y_half-=64;old.campaign.battle_x=old.campaign.battle_y=1536;
            c=&old.combat;c->goal_x-=64;c->goal_y-=64;c->cursor_x-=64;c->cursor_y-=64;c->waypoint_x[0]-=64;c->waypoint_y[0]-=64;
            for (unsigned i=0;i<c->count;++i) {
                c->unit[i].x-=64;c->unit[i].y-=64;
                if (c->plans[i].active || c->plans[i].x || c->plans[i].y) { c->plans[i].x-=64;c->plans[i].y-=64; }
                for (unsigned j=0;j<c->plans[i].count;++j) { c->plans[i].wx[j]-=64;c->plans[i].wy[j]-=64; }
            }
            btp_state_encode(&old,saved);memcpy(saved,"BTPT",4);saved[4]=29;
            BtpState upgraded;CHECK(btp_state_decode(saved,sizeof saved,btp_active_map(r,&old),btp_state_bld(r,&old),&upgraded));
            btp_state_encode(&modern,saved);btp_state_encode(&upgraded,again);CHECK(!memcmp(saved,again,sizeof saved));
            const BtpAction continuation[4]={BTP_RIGHT,BTP_DOWN,BTP_ACCEPT,BTP_CANCEL};
            for (unsigned j=0;j<4;++j) {
                btp_game_tick(&modern,r,continuation[j]);btp_game_tick(&upgraded,r,continuation[j]);
                btp_state_encode(&modern,saved);btp_state_encode(&upgraded,again);CHECK(!memcmp(saved,again,sizeof saved));
            }
            migration=1;
        }
        if (s.late.invasion_popup) invasion_popups|=1u<<s.late.invasion_popup;
        if (s.campaign.invasion && s.late.invasion_event>=3) {
            CHECK(btp_active_map(r,&s)==&r->destroyed);destroyed_during_fight=1;
        }
        BtpState restored;btp_state_encode(&s,saved);
        if (!btp_state_decode(saved,sizeof saved,btp_active_map(r,&s),btp_state_bld(r,&s),&restored)) {
            fprintf(stderr,"save failed tick %u input %s mode %u pc %x mission %u combat %u pos %u,%u inv %u owned %u effect %u,%u step %u\n",
                actions+1,row,s.mode,s.script.pc,s.mission.phase,s.combat.phase,s.x_half,s.y_half,
                s.campaign.invasion,s.campaign.owned,s.effects.count,s.effects.pending,s.combat.step);
            CHECK(0);
        }
        btp_state_encode(&restored,again);CHECK(!memcmp(saved,again,sizeof saved));s=restored;++actions;
    }
    fclose(f);CHECK(s.story_flags[4] && s.mode==BTP_EXPLORE && !s.campaign.invasion);
    CHECK(invasion_popups==126 && destroyed_during_fight && migration);
    CHECK(animation ? !s.campaign.owned : s.campaign.owned);
    char save_path[256];const char *leaf=strrchr(argv[2],'/'),*back=strrchr(argv[2],'\\');
    if (back && (!leaf || back>leaf)) leaf=back;
    leaf=leaf ? leaf+1 : argv[2];
    CHECK(snprintf(save_path,sizeof save_path,"work/campaign-%s.btp",leaf)>0);
    CHECK(btp_save_write(save_path,&s,r,&e));
    BtpState loaded;CHECK(btp_save_load(save_path,&loaded,r,&e));
    CHECK(remove(save_path)==0);
    free(r);printf("PASS: %u checks; %u ordinary invasion inputs, %s branch\n",checks,actions,animation ? "mech lost" : "mech retained");return 0;
}

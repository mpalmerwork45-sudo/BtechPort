#include "core/combat.h"
#include "core/audio.h"
#include "core/party.h"
#include "core/world.h"
#include "core/campaign.h"
#include "core/yard.h"
#include "data/save.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,failures;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static uint64_t hash(const uint8_t *b,unsigned n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);
    return h;
}
static void step(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;btp_state_encode(s,a);
    if (!btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&copy)) {
        fprintf(stderr,"Live restore failed: phase=%u step=%u effects=%u/%u friends=%u units=%u combat=%d\n",
            s->combat.phase,s->combat.step,s->effects.count,s->effects.stage,s->combat.friends,s->combat.count,btp_combat_valid(s));CHECK(0);
    }
    btp_combat_tick(s,r,action);btp_audio_samples(&s->audio,r,BTP_AUDIO_TICK_SAMPLES,NULL);
    btp_combat_tick(&copy,r,action);btp_audio_samples(&copy.audio,r,BTP_AUDIO_TICK_SAMPLES,NULL);
    btp_state_encode(s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));
}
int main(int argc,char **argv)
{
    if (argc!=2 && argc!=3) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    FILE *f=fopen(argc==3 ? argv[2] : "tests/fixtures/live-campaign-primary.txt","r");CHECK(f);char line[700];
    BtpState s;unsigned current=0,unit_count=0,waves=0,placement_seed=0;
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='B') {
            unsigned seed,bx,by,friends,count,town=0,x=1263,y=1675,spy=0;
            placement_seed=0;
            int fields=sscanf(line+1,"%u %u %u %u %u %u %u %u %u %u %u",&current,&seed,&bx,&by,&friends,&count,&town,&x,&y,&spy,&placement_seed);CHECK(fields==6 || fields==11);
            if (fields==6) spy=current!=0;
            CHECK(btp_save_load("Original DOS/GAME3",&s,r,&e));s.map_id=(uint8_t)town;s.mode=BTP_ENCOUNTER;s.campaign.encounter=1;
            s.campaign.battle_x=(uint16_t)bx;s.campaign.battle_y=(uint16_t)by;s.campaign.world_x=(uint16_t)x;s.campaign.world_y=(uint16_t)y;
            s.campaign.mech[122]=255;s.party.people[3][12]=8;s.menu.sound=0;s.menu.outtakes=0;
            s.story_flags[37]=(uint8_t)(spy ? 4 : 255);s.story_flags[38]=s.story_flags[39]=s.spy_discovered=(uint8_t)spy;
            if (spy) { s.party.mechs[0][122]=(uint8_t)((current==1 || current==3) ? 4 : 1);if (current==2 || current==4) s.party.mechs[0][121]=4; }
            s.combat=(BtpCombatState){.phase=BTP_COMBAT_MENU,.selected=9,.friends=(uint8_t)friends,.count=(uint8_t)count,
                .target_unit=(uint8_t)friends,.last_target=(uint8_t)friends,.movement=255,.kick_target=255,.enemy_movement=255};
            s.combat.automatic=(1u<<friends)-1u;memset(s.combat.orders,255,11);
            memset(s.combat.enemy_orders,255,sizeof s.combat.enemy_orders);memset(s.combat.enemy_modes,255,sizeof s.combat.enemy_modes);
            for (unsigned i=0;i<count;++i) { s.combat.plans[i].movement=s.combat.plans[i].kick=255;memset(s.combat.plans[i].orders,255,11); }
            for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));
            unit_count=0;
        } else if (line[0]=='E') {
            unsigned kind,rental,difficulty;
            CHECK(sscanf(line+1,"%u %u %u",&kind,&rental,&difficulty)==3);
            CHECK((kind==1 || kind==3 || kind==4) && rental<=1 && difficulty<=6);
            s.campaign.encounter=(uint8_t)kind;s.story_flags[3]=(uint8_t)difficulty;
            s.gate=85;s.story_flags[35]=0;
            /* The arena's suspended building caller is needed for a valid
               save at every tactical boundary, including pilot ejection. */
            if (kind==4) {
                s.campaign.building=10;s.script.status=BTP_SCRIPT_NATIVE;s.script.native_action=35;
                s.yard.active=2;s.yard.phase=BTP_YARD_FIGHT;s.yard.rental=(uint8_t)rental;s.checkpoint_valid=1;
                s.checkpoint_allowance_cap=s.allowance_cap;
                const BtpBld *bld=btp_state_bld(r,&s);CHECK(bld);
                for (unsigned i=1;i<bld->length;++i) if (bld->bytes[i-1]==0xf5 && bld->bytes[i]==35) { s.script.pc=(uint16_t)(i+1);break; }
                CHECK(s.script.pc);
            }
        } else if (line[0]=='M') {
            unsigned id;int used;CHECK(sscanf(line+1,"%u%n",&id,&used)==1 && id<4);char *at=line+1+used;
            for (unsigned i=0;i<125;++i) { unsigned b;CHECK(sscanf(at,"%u%n",&b,&used)==1 && b<256);at+=used;btp_party_mech(&s,id)[i]=(uint8_t)b; }
        } else if (line[0]=='P' || line[0]=='H' || line[0]=='V') {
            unsigned id;int used;CHECK(sscanf(line+1,"%u%n",&id,&used)==1);char *at=line+1+used;uint8_t record[17];
            if (line[0]=='V') {
                unsigned slot=btp_combat_target(&s.combat,id);CHECK(slot<s.combat.count);
                for (unsigned i=0;i<125;++i) { unsigned b;CHECK(sscanf(at,"%u%n",&b,&used)==1 && b<256);at+=used;s.combat.unit[slot].record[i]=(uint8_t)b; }
                continue;
            }
            for (unsigned i=0;i<17;++i) { unsigned b;CHECK(sscanf(at,"%u%n",&b,&used)==1 && b<256);at+=used;record[i]=(uint8_t)b; }
            if (line[0]=='P') { CHECK(id<8);memcpy(s.party.people[id],record,17); }
            else { unsigned slot=btp_combat_target(&s.combat,id);CHECK(slot<s.combat.count);memcpy(s.combat.unit[slot].record,record,17); }
        } else if (line[0]=='I') {
            unsigned id,x,y,face,fallback,walk,heat,heading;uint64_t expected;
            CHECK(sscanf(line+1,"%u %u %u %u %u %u %u %u %" SCNx64,&id,&x,&y,&face,&fallback,&walk,&heat,&heading,&expected)==9 && unit_count<24);
            unsigned at=unit_count++;BtpCombatUnit *u=&s.combat.unit[at];s.combat.ids[at]=(uint8_t)id;
            u->x=(uint8_t)x;u->y=(uint8_t)y;u->direction=(uint8_t)face;u->heat=(uint8_t)heat;
            if (!at) { s.x_half=(uint16_t)x;s.y_half=(uint16_t)(y+2); }
            s.combat.fallback[at]=(uint8_t)fallback;s.combat.plan_direction[at]=(uint8_t)heading;s.combat.walk[at]=(uint8_t)walk;
            if (id<4) memcpy(u->record,btp_party_mech(&s,id),125);
            else if (id<12) { u->infantry=1;memcpy(u->record,s.party.people[id-4],17); }
            else if (id<16) memcpy(u->record,r->combat.loans[0],125);
            else u->infantry=1;
            if (id<12 || (id<16 && argc==2)) CHECK(hash(u->record,u->infantry ? 17u : 125u)==expected);
        } else if (line[0]=='T') {
            unsigned turn,rng,count;CHECK(sscanf(line+1,"%u %u %u %u",&current,&turn,&rng,&count)==4);
            if (turn==1 && placement_seed && s.map_id!=2) {
                /* Compare actual native setup before using the separately
                   observed original combat prerequisite for wave checks. */
                BtpState placed=s;placed.mode=BTP_EXPLORE;placed.campaign.encounter=0;
                placed.campaign.mounted=(uint8_t)(placed.party.people[0][12]<8);
                placed.x_half=placed.campaign.world_x&127u;placed.y_half=placed.campaign.world_y&127u;
                for (unsigned b=0;b<3;++b) placed.npc.rng[b]=(uint8_t)(placement_seed>>(8*b));
                CHECK(btp_campaign_random(&placed,r));
                if (placed.combat.count!=s.combat.count) {
                    fprintf(stderr,"Placement case %u friends=%u/%u count=%u/%u\n",current,placed.combat.friends,s.combat.friends,placed.combat.count,s.combat.count);
                    for (unsigned j=0;j<placed.combat.count;++j) fprintf(stderr,"id %u at %u,%u\n",placed.combat.ids[j],placed.combat.unit[j].x,placed.combat.unit[j].y);
                }
                CHECK(placed.combat.count==s.combat.count);
                CHECK(!memcmp(placed.npc.rng,s.npc.rng,3));
                for (unsigned i=s.combat.friends;i<s.combat.count;++i) {
                    unsigned j=btp_combat_target(&placed.combat,s.combat.ids[i]);CHECK(j<placed.combat.count);
                    CHECK(placed.combat.unit[j].x==s.combat.unit[i].x && placed.combat.unit[j].y==s.combat.unit[i].y);
                    CHECK(!memcmp(placed.combat.unit[j].record,s.combat.unit[i].record,s.combat.unit[i].infantry ? 17 : 125));
                }
            }
            s.combat.phase=BTP_COMBAT_MENU;s.combat.selected=9;step(&s,r,BTP_ACCEPT);
            unsigned ticks=0;
            while (s.combat.phase==BTP_COMBAT_ROUND && ticks++<8192) { step(&s,r,BTP_IDLE); }
            if (s.combat.phase==BTP_COMBAT_SPY) {
                step(&s,r,BTP_ACCEPT);
                while (s.combat.phase==BTP_COMBAT_ROUND && ticks++<8192) step(&s,r,BTP_IDLE);
            }
            CHECK(ticks<8192);unsigned actual=s.npc.rng[0]+256u*s.npc.rng[1]+65536u*s.npc.rng[2];++waves;
            if (actual!=rng || s.combat.count!=count) { fprintf(stderr,"Live case=%u wave=%u rng=%u/%u units=%u/%u\n",current,turn,actual,rng,s.combat.count,count);++failures; }
        } else if (line[0]=='U') {
            unsigned id;int x,y;unsigned face,heat;uint64_t expected;
            CHECK(sscanf(line+1,"%u %d %d %u %u %" SCNx64,&id,&x,&y,&face,&heat,&expected)==6);
            unsigned at=btp_combat_target(&s.combat,id);CHECK(at<s.combat.count);const BtpCombatUnit *u=&s.combat.unit[at];
            if (hash(u->record,u->infantry ? 17u : 125u)!=expected || (u->record[0]!=255 && (u->x!=x || u->y!=y || u->direction!=face || u->heat!=heat))) {
                fprintf(stderr,"Live case=%u wave=%u id=%u pos=%u,%u/%d,%d face=%u/%u heat=%u/%u record=%016" PRIx64 "/%016" PRIx64 "\n",
                    current,s.combat.round,id,u->x,u->y,x,y,u->direction,face,u->heat,heat,hash(u->record,u->infantry ? 17u : 125u),expected);++failures;
            }
        } else if (line[0]=='Z') {
            unsigned won,lost;CHECK(sscanf(line+1,"%u %u %u",&current,&won,&lost)==3);
            if (s.combat.won!=won || s.combat.lost!=lost) { fprintf(stderr,"Live outcome=%u won=%u/%u lost=%u/%u\n",current,s.combat.won,won,s.combat.lost,lost);++failures; }
        } else CHECK(0);
    }
    fclose(f);free(r);CHECK(argc==3 ? waves>=4 : waves==25);printf("Original encounters: %u complete waves, %u checks, %u differences\n",waves,checks,failures);return failures!=0;
}

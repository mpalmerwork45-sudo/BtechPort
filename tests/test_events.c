#include "core/campaign.h"
#include "core/combat.h"
#include "core/effects.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void input(BtpState *s,const BtpResources *r,BtpAction a)
{
    BtpState copy;uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];btp_state_encode(s,before);
    CHECK(btp_state_decode(before,sizeof before,btp_active_map(r,s),btp_state_bld(r,s),&copy));
    btp_game_tick(s,r,a);btp_game_tick(&copy,r,a);btp_state_encode(s,before);btp_state_encode(&copy,after);CHECK(!memcmp(before,after,sizeof before));
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    FILE *f=fopen("tests/fixtures/event-audit-primary.txt","r");CHECK(f);char line[180];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        unsigned w,visible,hit,n;int used;
        if (line[0]=='S') {
            CHECK(sscanf(line+1,"%u %u %u %u%n",&w,&visible,&hit,&n,&used)==4);
            unsigned sounds[2],count=0,fire=btp_effects_fire_sound(w,(int)visible);if (fire) sounds[count++]=fire;if (hit) sounds[count++]=4;
            CHECK(count==n);char *at=line+1+used;
            for (unsigned i=0;i<n;++i) { unsigned effect;CHECK(sscanf(at,"%u%n",&effect,&used)==1);at+=used;CHECK(sounds[i]==effect); }
        } else if (line[0]=='D') {
            unsigned effect;CHECK(sscanf(line+1,"%u",&effect)==1);BtpState s;btp_start(&s);
            s.campaign.encounter=(uint8_t)(effect==7 ? 4 : 1);s.combat.ids[1]=13;s.combat.count=2;s.combat.friends=1;
            s.effects.count=1;s.effects.stage=BTP_EFFECT_IMPACT;s.effects.shots[0]=(BtpCombatEffect){.target=1,.hit=1,.dead=1};
            s.effects.age=(uint8_t)btp_effects_length(&s.effects.shots[0],&r->combat);btp_effects_tick(&s,r);
            CHECK(s.effects.stage==BTP_EFFECT_DEATH_SOUND && s.audio.sound_count==1 && s.audio.sounds[0]==effect);
            btp_effects_tick(&s,r);CHECK(s.audio.sound_count==1 && s.effects.count==1); /* A pending clip is never appended twice. */
        } else if (line[0]=='E') {
            unsigned seed,yes,evaded,next;CHECK(sscanf(line+1,"%u %u %u %u",&seed,&yes,&evaded,&next)==4);
            BtpState s;CHECK(btp_save_load("Original DOS/GAME3",&s,r,&e));
            /* Explicit open-ground prerequisite for the bounded decision
               comparison; candidate generation and placement still run. */
            s.map_id=0;s.x_half=s.campaign.world_x=1200;s.y_half=s.campaign.world_y=1200;
            unsigned attempts=0;while (!btp_campaign_random(&s,r) && ++attempts<32) {}CHECK(attempts<32);
            CHECK(s.combat.phase==BTP_COMBAT_OFFER);unsigned cash=s.credits;BtpPartyState party=s.party;
            for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));
            if (!yes) input(&s,r,BTP_RIGHT);input(&s,r,BTP_ACCEPT);
            CHECK((s.mode==BTP_EXPLORE)==(evaded!=0));CHECK(s.credits==cash && !memcmp(&party,&s.party,sizeof party) && !s.aftermath.phase);
            CHECK(((unsigned)s.npc.rng[0]|(unsigned)s.npc.rng[1]<<8|(unsigned)s.npc.rng[2]<<16)==next);
            if (!evaded) { CHECK(s.combat.phase==(yes ? BTP_COMBAT_CONTROL : BTP_COMBAT_AVOID));if (!yes) input(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_CONTROL); }
            input(&s,r,BTP_IDLE);
        } else CHECK(0);
        ++cases;
    }
    fclose(f);CHECK(cases==154);free(r);printf("PASS: %u event checks, 154 executed-primary sound/encounter cases\n",checks);return 0;
}

#include "data/anm.h"
#include "core/animation.h"
#include "core/combat.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)
static void timing(const BtpResources *r)
{
    FILE *f=fopen("tests/fixtures/presentation-timing-primary.txt","r");CHECK(f);
    for (unsigned case_id=0;case_id<66;++case_id) {
        char type;unsigned kind,flags,count,n,total,sounds,delay[256],sound[2];uint64_t expected;
        CHECK(fscanf(f," %c %u %u %u %u %u %u %" SCNx64,&type,&kind,&flags,&count,&n,&total,&sounds,&expected)==8);
        CHECK(type=='A' && kind<BTP_ANM_COUNT && flags<3 && n<256 && sounds<=1);
        for (unsigned i=0;i<n;++i) CHECK(fscanf(f," %u",&delay[i])==1);
        for (unsigned i=0;i<sounds;++i) CHECK(fscanf(f," %u",&sound[i])==1 && sound[i]==12);
        const BtpAnm *a=&r->animations[kind];unsigned at=0,sum=0,frames=0;
        uint64_t hash=UINT64_C(14695981039346656037);uint8_t packed[BTP_ANM_PACKED];
        for (unsigned cycle=0;cycle<(kind==8 ? 7u : 1u);++cycle) for (unsigned frame=0;frame<a->count;++frame) {
            CHECK(at<n && delay[at]==a->units[frame]);sum+=delay[at++];++frames;
            CHECK(btp_anm_frame(a,frame,packed));
            for (unsigned i=0;i<sizeof packed;++i) hash=(hash^packed[i])*UINT64_C(1099511628211);
            if (!frame && kind!=8) { CHECK(at<n && delay[at]==50);sum+=delay[at++]; }
        }
        if (!flags) { CHECK(at<n && delay[at]==60);sum+=delay[at++]; }
        CHECK(at==n && sum==total && frames==count && hash==expected && sounds==(!flags && !kind ? 1u : 0u));
        /* Exercise contexts actually dispatched by the native game. Flags
           one/two on battle-only outtakes have no native caller. */
        if ((flags && kind>=15) || (!flags && kind==8)) continue;
        BtpState s;btp_start(&s);s.menu.sound=0;
        unsigned active=!flags ? kind ? 3u : 2u : 1u;
        if (flags) {
            s.mode=BTP_BUILDING;s.campaign.building=(uint8_t)(kind<10 ? 16 : 25);s.cache.active=(uint8_t)(kind>=10);
        }
        CHECK(btp_cutscene_begin(&s,r,kind,active));unsigned ticks=0;
        while (s.cutscene.active) { CHECK(++ticks<10000);btp_cutscene_tick(&s,r); }
        /* 32 ms scheduling rounds a requested 70 Hz duration up by less
           than one logical tick; fractional retraces persist in saves. */
        CHECK(ticks==(total*100u+223u)/224u);
    }
    for (unsigned speed=0;speed<6;++speed) {
        char type;unsigned actual,keys,n,delay=0;
        CHECK(fscanf(f," %c %u %u %u",&type,&actual,&keys,&n)==4 && type=='S' && actual==speed);
        if (n) CHECK(fscanf(f," %u",&delay)==1);
        CHECK(keys==(speed==5) && n==(speed!=5) && delay==(speed<5 ? 12*speed : 0));
        unsigned ticks=btp_combat_delay_ticks(speed);
        if (delay) CHECK((ticks+1u)*224u>=delay*100u && ticks*224u<delay*100u);
        else CHECK(!ticks);
    }
    CHECK(!fclose(f));
    for (unsigned kind=6;kind<=9;kind+=3) {
        BtpState s;btp_start(&s);s.mode=BTP_BUILDING;s.checkpoint_valid=1;s.campaign.invasion=(uint8_t)(kind==9);
        s.campaign.building=(uint8_t)(kind==6 ? 5 : 0);s.entry_slot=0;
        s.script.status=BTP_SCRIPT_ANIMATION;s.script.animation_kind=(uint8_t)kind;s.script.animation_flags=1;
        CHECK(btp_cutscene_begin(&s,r,kind,1) && btp_cutscene_valid(&s));
        while (s.cutscene.active) { btp_cutscene_tick(&s,r);if (s.cutscene.active) CHECK(btp_cutscene_valid(&s)); }
    }
}
int main(int argc, char **argv)
{
    BtpAnm a, untouched; BtpError error;
    uint8_t packet[59] = {'A',0}; packet[32]=1; packet[50]=10;
    packet[51]=0; packet[52]=0x0f; packet[53]=0x20; packet[54]=0x37;
    CHECK(btp_anm_decode(packet,55,&a,&error)); CHECK(a.count == 1 && a.end[0] == 55 && a.units[0] == 7);
    uint8_t packed[BTP_ANM_PACKED]; CHECK(btp_anm_frame(&a,0,packed));
    for (unsigned i=0;i<sizeof packed;++i) CHECK(packed[i] == 0x37);
    CHECK(!btp_anm_frame(&a,1,packed));
    untouched=a;
    for (unsigned n=0;n<55;++n) {
        CHECK(!btp_anm_decode(packet,n,&a,&error)); CHECK(!memcmp(&a,&untouched,sizeof a));
    }
    packet[53]=0x21; CHECK(btp_anm_decode(packet,55,&a,&error));
    packet[52]=packet[53]=0; CHECK(btp_anm_decode(packet,55,&a,&error));
    packet[0]='S'; CHECK(!btp_anm_decode(packet,55,&a,&error));
    if (argc > 1) {
        BtpResources *r = malloc(sizeof *r); CHECK(r && btp_resources_load(argv[1],r,&error));
        FILE *export = argc > 2 ? fopen(argv[2],"wb") : NULL;
        if (argc > 2) CHECK(export);
        for (unsigned kind=0;kind<BTP_ANM_COUNT;++kind) {
            const BtpAnm *original=&r->animations[kind];
            CHECK(original->count && original->count <= 31);
            for (unsigned i=0;i<original->count;++i) {
                CHECK(btp_anm_frame(original,i,packed));
                if (export) CHECK(fwrite(packed,1,sizeof packed,export) == sizeof packed);
            }
        }
        if (export) CHECK(!fclose(export));
        BtpState s; btp_start(&s); CHECK(btp_cutscene_begin(&s,r,8,1));
        unsigned ticks=0, cycles=0;
        while (s.cutscene.active) { cycles |= 1u<<s.cutscene.cycle; CHECK(++ticks <= 66); btp_cutscene_tick(&s,r); }
        CHECK(ticks == 66 && cycles == 127);
        /* Isolate visual cadence here. The integrated launch waits for its
           startup sound and is covered by the game/audio continuation tests. */
        s.menu.sound=0;
        CHECK(btp_cutscene_begin(&s,r,0,2)); ticks=0;
        while (s.cutscene.active) { CHECK(++ticks <= 90); btp_cutscene_tick(&s,r); }
        CHECK(ticks == 90);timing(r);free(r);
    }
    printf("PASS: %u ANM bounds, delta, sequence, repeat and timing assertions.\n",checks);
    return 0;
}

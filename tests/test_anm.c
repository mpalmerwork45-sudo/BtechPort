#include "data/anm.h"
#include "core/animation.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)
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
        CHECK(btp_cutscene_begin(&s,r,0,2)); ticks=0;
        while (s.cutscene.active) { CHECK(++ticks <= 90); btp_cutscene_tick(&s,r); }
        CHECK(ticks == 90); free(r);
    }
    printf("PASS: %u ANM bounds, delta, sequence, repeat and timing assertions.\n",checks);
    return 0;
}

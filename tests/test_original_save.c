#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s (%s)\n",__FILE__,__LINE__,#x,e.text);return 1; } } while (0)
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpError e={0};BtpResources *r=calloc(1,sizeof *r);CHECK(r);
    CHECK(btp_resources_load(argv[1],r,&e));CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    const unsigned cash[6]={50876,91,15342507,15341261,15264251,170};
    for (unsigned i=0;i<6;++i) {
        char path[512];snprintf(path,sizeof path,"%s/GAME%u",argv[1],i+1);
        uint8_t *original;size_t n;CHECK(btp_read_file(path,&original,&n,&e));
        BtpState s,copy;btp_start(&s);CHECK(btp_save_load(path,&s,r,&e));CHECK(s.original.valid && s.credits==cash[i]);
        uint8_t exported[BTP_ORIGINAL_BYTES];CHECK(btp_original_encode(&s,exported,&e));CHECK(n==sizeof exported && !memcmp(original,exported,n));
        CHECK(btp_save_write("work/original-roundtrip.btp",&s,r,&e));CHECK(btp_save_load("work/original-roundtrip.btp",&copy,r,&e));
        CHECK(btp_original_encode(&copy,exported,&e) && !memcmp(original,exported,n));
        CHECK(remove("work/original-roundtrip.btp")==0);
        for (unsigned step=0;step<16;++step) {
            uint8_t saved[BTP_STATE_BYTES],again[BTP_STATE_BYTES];btp_state_encode(&s,saved);
            CHECK(btp_state_decode(saved,sizeof saved,btp_active_map(r,&s),btp_state_bld(r,&s),&copy));
            btp_game_tick(&s,r,BTP_IDLE);btp_game_tick(&copy,r,BTP_IDLE);btp_state_encode(&s,saved);btp_state_encode(&copy,again);
            CHECK(!memcmp(saved,again,sizeof saved));
        }
        CHECK(btp_original_decode(original,n,&s,r,&e));s.credits+=100;
        CHECK(btp_original_encode(&s,exported,&e));
        CHECK(btp_original_decode(exported,sizeof exported,&copy,r,&e) && copy.credits==cash[i]+100);
        for (unsigned j=0;j<n;++j) if (j<0xd5d || j>=0xd61) CHECK(original[j]==exported[j]);
        CHECK(btp_original_write("work/original-update.btp",&s,&e));
        CHECK(btp_save_load("work/original-update.btp",&copy,r,&e) && copy.credits==s.credits);
        CHECK(remove("work/original-update.btp")==0);
        BtpState before=s;exported[0]=11;CHECK(!btp_original_decode(exported,sizeof exported,&s,r,&e));CHECK(!memcmp(&s,&before,sizeof s));
        CHECK(!btp_original_decode(original,n-1,&s,r,&e));CHECK(!memcmp(&s,&before,sizeof s));free(original);
    }
    BtpState fresh;btp_start(&fresh);uint8_t b[BTP_ORIGINAL_BYTES];CHECK(!btp_original_encode(&fresh,b,&e));
    free(r);printf("PASS: %u checks; all six original GAME imports, byte-exact roundtrips, native saved continuation and modeled updates\n",checks);return 0;
}

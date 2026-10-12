#include "core/world.h"
#include "frontend/pixels.h"
#include "data/save.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static uint64_t fingerprint(const uint8_t *b,size_t n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (size_t i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);
    return h;
}
int main(int argc,char **argv)
{
    if (argc!=4) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;
    CHECK(r && btp_resources_load(argv[1],r,&e) && btp_world_data_load(argv[2],&r->world,&e));
    FILE *f=fopen(argv[3],"r");CHECK(f);char line[200];unsigned cases=0;
    while (fgets(line,sizeof line,f)) if (line[0]=='W') {
        unsigned x,y,seed;uint64_t expected;uint8_t sector[4096];
        CHECK(sscanf(line+1,"%u %u %u %" SCNx64,&x,&y,&seed,&expected)==4);
        CHECK(x>=11 && x<=13 && y>=11 && y<=13 && seed==r->world.seed);
        for (unsigned row=0;row<64;++row)
            memcpy(sector+64*row,r->world.tiles+((y-11)*64+row)*192+(x-11)*64,64);
        CHECK(fingerprint(sector,sizeof sector)==expected);++cases;
    }
    fclose(f);CHECK(cases==9);
    uint8_t *raw;size_t n;CHECK(btp_read_file(argv[2],&raw,&n,&e));
    BtpWorldData untouched=r->world;
    CHECK(!btp_world_data_decode(raw,n-1,&r->world,&e) && !memcmp(&untouched,&r->world,sizeof untouched));
    const unsigned corrupt[]={0,4,8,12,16,80};
    for (unsigned i=0;i<sizeof corrupt/sizeof corrupt[0];++i) {
        unsigned at=corrupt[i];uint8_t old=raw[at];raw[at]=255;
        if (at==12) raw[15]=255;
        CHECK(!btp_world_data_decode(raw,n,&r->world,&e) && !memcmp(&untouched,&r->world,sizeof untouched));
        raw[at]=old;if (at==12) raw[15]=0;
    }
    free(raw);
    BtpState s;btp_start(&s);
    for (unsigned y=0;y<64;++y) for (unsigned x=0;x<64;++x)
        CHECK(btp_world_tile(r,&s,(int)x+768,(int)y+768)==btp_map_tile(&r->map,(int)x,(int)y));
    CHECK(btp_world_tile(r,&s,703,768)==255 && btp_world_tile(r,&s,896,768)==255);
    uint32_t *a=malloc(BTP_PIXELS*sizeof *a),*b=malloc(BTP_PIXELS*sizeof *b);CHECK(a && b);
    btp_render(r,&s,0,a);btp_render(r,&s,0,b);CHECK(!memcmp(a,b,BTP_PIXELS*sizeof *a));
    /* MAP1's border is deliberately closed during this early campaign. */
    for (unsigned pos=0;pos<64;++pos) {
        CHECK(btp_map_tile(&r->map,0,(int)pos)>=85);
        CHECK(btp_map_tile(&r->map,63,(int)pos)>=85);
        CHECK(btp_map_tile(&r->map,(int)pos,0)>=85);
        CHECK(btp_map_tile(&r->map,(int)pos,63)>=85);
    }
    uint8_t saved[BTP_STATE_BYTES];BtpState restored;
    s.tick=37;btp_world_preview(r,&s,a);btp_state_encode(&s,saved);
    CHECK(btp_state_decode(saved,sizeof saved,&r->map,&r->citadel,&restored));
    btp_world_preview(r,&restored,b);CHECK(!memcmp(a,b,BTP_PIXELS*sizeof *a));
    BtpState before=s;btp_world_preview(r,&s,a);CHECK(!memcmp(&before,&s,sizeof s));
    const char *slot="work/world-test.btp";
    CHECK(btp_save_write(slot,&s,r,&e));CHECK(btp_save_load(slot,&restored,r,&e));
    btp_world_preview(r,&restored,b);CHECK(!memcmp(a,b,BTP_PIXELS*sizeof *a));
    CHECK(remove(slot)==0);
    free(a);free(b);free(r);
    printf("PASS: %u world cache, original sector, MAP1 overlay, barrier and saved-clock assertions\n",checks);
    return 0;
}

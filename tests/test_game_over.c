#include "core/game.h"
#include "core/party.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static BtpError error;
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"Death popup %d: %s (%s)\n",__LINE__,#x,error.text);return 1; } } while(0)
static uint64_t pixels_hash(const uint32_t *frame)
{
    uint64_t h=UINT64_C(0xcbf29ce484222325);
    for(unsigned y=80;y<120;++y)for(unsigned x=112;x<312;++x)for(int c=16;c>=0;c-=8)
        h=(h^((frame[y*320+x]>>c)&255u))*UINT64_C(0x100000001b3);
    return h;
}
int main(int argc,char **argv)
{
    CHECK(argc==4 || argc==5);
    BtpResources *r=calloc(1,sizeof *r);BtpState *s=calloc(1,sizeof *s),*copy=calloc(1,sizeof *copy);
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame),*restored=malloc(BTP_PIXELS*sizeof *restored);CHECK(r && s && copy && frame && restored);
    CHECK(btp_resources_load(argv[1],r,&error) && btp_dialogue_load(argv[2],&r->dialogue,&error));CHECK(r->dialogue.count==375);
    FILE *facts=fopen(argv[3],"r");CHECK(facts);unsigned victim;uint64_t text_hash,pixel_hash;unsigned count=0;
    while(fscanf(facts,"%u %" SCNx64 " %" SCNx64,&victim,&text_hash,&pixel_hash)==3) {
        CHECK(victim<2);btp_start_content(s,r);btp_party_init(s);s->party.people[victim][0]=255;s->party.people[victim][15]=0;
        btp_game_over(s);btp_render(r,s,0,frame);CHECK(pixels_hash(frame)==pixel_hash);
        unsigned visible=0;for(unsigned y=0;y<64;++y)for(unsigned x=104;x<320;++x)visible+=frame[y*320+x]!=btp_palette[0];CHECK(visible>100);
        if(argc==5 && !victim) {
            char saved[4096];CHECK(snprintf(saved,sizeof saved,"%s.btp",argv[4])<(int)sizeof saved);
            CHECK(btp_write_ppm(argv[4],frame) && btp_save_write(saved,s,r,&error));
        }
        CHECK(btp_save_write("game-over-test.btp",s,r,&error) && btp_save_load("game-over-test.btp",copy,r,&error));
        btp_render(r,copy,0,restored);CHECK(!memcmp(frame,restored,BTP_PIXELS*sizeof *frame));
        btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_GAME_OVER && s->menu.notice==1);
        CHECK(btp_save_write("game-over-test.btp",s,r,&error) && btp_save_load("game-over-test.btp",copy,r,&error));CHECK(copy->menu.notice==1);
        btp_game_tick(copy,r,BTP_RIGHT);btp_game_tick(copy,r,BTP_ACCEPT);CHECK(copy->menu.quit);
        btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_BEGIN && !s->menu.quit && !s->party.enabled);
        CHECK(!remove("game-over-test.btp"));++count;
    }
    CHECK(count==2 && !fclose(facts));free(r);free(s);free(copy);free(frame);free(restored);
    puts("Original Jason/Rex death popup pixels, retained view, held save/reload and replay/quit choices match declared cases.");return 0;
}

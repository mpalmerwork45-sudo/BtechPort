#include "frontend/pixels.h"
#include "data/sprites.h"
#include "core/animation.h"
#include "data/project.h"
#include "core/events.h"
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)
static void fill(uint32_t *f) { for (unsigned i=0;i<BTP_PIXELS;++i) f[i]=btp_palette[2]; }
int main(void)
{
    BtpResources *r = calloc(1,sizeof *r); uint32_t *f = malloc(BTP_PIXELS*sizeof *f);
    CHECK(r && f); r->sprites.format=2;
    for (unsigned id=0;id<BTP_SPRITE_COUNT;++id) {
        BtpSpriteRect rect; CHECK(btp_sprite_rect(id,&rect));
        CHECK(rect.width && rect.height && rect.x+rect.width<=320 && rect.y+rect.height<=200);
    }
    BtpSpriteRect rect; CHECK(!btp_sprite_rect(376,&rect)); CHECK(!btp_sprite_rect(UINT_MAX,&rect));
    CHECK(!btp_sprite_rect(0,NULL));
    /* Synthetic colors distinguish transparency from the opaque black outline. */
    CHECK(btp_sprite_rect(166,&rect));
    unsigned at=rect.y*320+rect.x;
    r->sprites.pixels[at+1]=1; r->sprites.pixels[at+2]=5; r->sprites.pixels[at+3]=9;
    r->sprites.pixels[at+7*320]=14;
    fill(f); CHECK(btp_draw_sprite(&r->sprites,166,104,0,0,104,f));
    CHECK(f[104]==btp_palette[2] && f[105]==btp_palette[0] && f[106]==btp_palette[9] && f[107]==btp_palette[1]);
    CHECK(f[7*320+104]==btp_palette[14]);
    fill(f); CHECK(btp_draw_sprite(&r->sprites,166,102,0,2,104,f));
    CHECK(f[103]==btp_palette[2] && f[104]==btp_palette[9] && f[105]==btp_palette[1]);
    CHECK(f[7*320+102]==btp_palette[2]);
    fill(f); CHECK(btp_draw_sprite(&r->sprites,166,318,199,0,104,f));
    CHECK(f[199*320+319]==btp_palette[0] && f[198*320+319]==btp_palette[2]);
    CHECK(btp_draw_sprite(&r->sprites,166,-1,-1,0,0,f));
    CHECK(btp_draw_sprite(&r->sprites,0,INT_MIN,INT_MIN,0,0,f));
    CHECK(btp_draw_sprite(&r->sprites,0,INT_MAX,INT_MAX,0,0,f));
    CHECK(!btp_draw_sprite(&r->sprites,0,0,0,25,0,f));
    CHECK(!btp_draw_sprite(&r->sprites,0,0,0,0,-1,f));
    /* A 24x24 mech must clip with the same mask and preserve the left panel. */
    r->sprites.pixels[0]=1; r->sprites.pixels[23*320+23]=14;
    fill(f); CHECK(btp_draw_sprite(&r->sprites,0,100,190,0,104,f));
    CHECK(f[190*320+100]==btp_palette[2]);
    fill(f); CHECK(btp_draw_sprite(&r->sprites,0,104,0,0,104,f));
    CHECK(f[104]==btp_palette[0] && f[23*320+127]==btp_palette[14]);
    /* Recorded original direction programs; all eight, including diagonal resets. */
    static const uint8_t original[8][4]={{24,25,26,27},{20,21,22,23},{20,21,22,23},{20,21,22,23},
        {16,17,18,19},{28,29,30,31},{28,29,30,31},{28,29,30,31}};
    for (unsigned d=0;d<8;++d) {
        uint8_t frame=btp_walk_next(3,99,d);
        for (unsigned i=0;i<8;++i) {
            CHECK(frame+16==original[d][i%4]); frame=btp_walk_next(frame,d,d);
        }
    }
    r->map.width=r->map.height=64;
    memset(r->map.tiles,64,sizeof r->map.tiles);
    BtpState s; btp_start(&s); uint8_t saved[BTP_STATE_BYTES]; BtpState copy;
    for (unsigned i=0;i<6;++i) btp_tick(&s,&r->map,BTP_RIGHT);
    CHECK(s.player_walk==5); btp_state_encode(&s,saved);
    CHECK(btp_state_decode(saved,sizeof saved,&r->map,NULL,&copy)); CHECK(copy.player_walk==5);
    /* Old saves retain logical progress; the missing gait starts at a facing's first frame. */
    memcpy(saved,"BTP8",4); saved[4]=8; memset(saved+394,0,22);
    CHECK(btp_state_decode(saved,416,&r->map,NULL,&copy)); CHECK(copy.player_walk==4 && copy.x_half==s.x_half);
    btp_state_encode(&s,saved); saved[394]=16;
    CHECK(!btp_state_decode(saved,sizeof saved,&r->map,NULL,&copy));
    btp_state_encode(&s,saved); saved[402]=16;
    CHECK(!btp_state_decode(saved,sizeof saved,&r->map,NULL,&copy));
    btp_state_encode(&s,saved); saved[434]=1;
    CHECK(!btp_state_decode(saved,sizeof saved,&r->map,NULL,&copy));
    /* The terrain rule clips only matching water quadrants, not grass. */
    btp_start(&s); r->sprites.pixels[at+6*320]=14;
    r->map.tiles[12*64+35]=38; /* lower left quadrant (odd,odd), depth 4 */
    btp_render(r,&s,0,f); CHECK(f[102*320+208]!=btp_palette[14]);
    r->map.tiles[12*64+35]=64;
    btp_render(r,&s,0,f); CHECK(f[102*320+208]==btp_palette[14]);
    /* Animated map art shares the saved clock, without changing collision. */
    r->map.tiles[12*64+35]=105;r->terrain_animation.format=1;
    uint32_t *restored_frame=malloc(BTP_PIXELS*sizeof *restored_frame);CHECK(restored_frame);
    for (unsigned phase=0;phase<3;++phase) {
        unsigned frame=btp_terrain_frame(105,phase);CHECK(frame==16+phase);
        memset(r->terrain_animation.pixels+frame*256,(int)(10+phase),256);
    }
    for (unsigned phase=0;phase<6;++phase) {
        btp_start(&s);s.tick=4*phase;btp_render(r,&s,0,f);
        CHECK(f[88*320+208]==btp_palette[10+phase%3]);
        btp_state_encode(&s,saved);CHECK(btp_state_decode(saved,sizeof saved,&r->map,NULL,&copy));
        btp_render(r,&copy,0,restored_frame);CHECK(!memcmp(f,restored_frame,BTP_PIXELS*sizeof *f));
        btp_tick(&s,&r->map,BTP_RIGHT);CHECK(s.blocked==BTP_WALL && s.x_half==69 && s.y_half==25);
    }
    CHECK(!btp_terrain_frame(64,0) && !btp_terrain_frame(UINT_MAX,UINT_MAX));
    /* Authored CHI terrain used to suppress every animation substitution.
       The source bank, not the presence of a custom map, decides the loop. */
    r->project=calloc(1,sizeof *r->project);CHECK(r->project);
    BtpAdventure *a=&r->project->adventure;a->loaded=1;a->map_count=1;a->tile_count=1;
    BtpScene *scene=&a->maps[0];scene->rules=scene->visual=r->map;
    a->tiles[0]=(BtpSceneTile){.graphic=105,.sheet=0,.terrain=4};
    btp_start(&s);s.event.enabled=1;s.map_id=16;
    for (unsigned tick=0;tick<24;++tick) {
        s.tick=tick;btp_render(r,&s,0,f);CHECK(f[88*320+208]==btp_palette[10+(tick/4)%3]);
        CHECK(!btp_scene_stand(scene,70,25,0));
    }
    a->tiles[0].sheet=1;memset(r->destroyed_tiles.pixels+105*256,14,256);
    for (unsigned phase=0;phase<3;++phase) {
        s.tick=phase*4;btp_render(r,&s,0,f);CHECK(f[88*320+208]==btp_palette[14]);
    }
    /* Owned tiles use their saved duration in both game presentations; an
       omitted duration keeps the existing eight-tick package default. */
    a->tiles[0].sheet=3;a->tiles[0].graphic=0;
    BtpArt *art=&r->project->graphics;art->count=1;
    art->images[0]=(BtpArtImage){.width=16,.height=16,.count=3,.frame_ticks=4,.frames={0,256,512}};
    for (unsigned i=0;i<768;++i) art->pixels[i]=btp_palette[10+i/256];
    for (unsigned tick=0;tick<24;++tick) {
        s.tick=tick;btp_render(r,&s,0,f);CHECK(f[88*320+208]==btp_palette[10+(tick/4)%3]);
    }
    art->images[0].frame_ticks=0;
    CHECK(btp_art_tile_frame(art,0,7)==0 && btp_art_tile_frame(art,0,8)==1 && btp_art_tile_frame(art,0,24)==0);
    /* Independent games must apply the same timing, even with no CHI assets. */
    art->images[0].frame_ticks=4;r->project->independent.loaded=1;
    for (unsigned tick=0;tick<24;++tick) {
        s.tick=tick;btp_render(r,&s,0,f);CHECK(f[20*320+20]==btp_palette[10+(tick/4)%3]);
    }
    free(r->project);
    free(restored_frame);
    free(f); free(r); printf("PASS: %u sprite bounds, compositing, gait and migration assertions.\n",checks);
    return 0;
}

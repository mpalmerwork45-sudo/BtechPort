#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "data/sprites.h"
#include "core/world.h"
#include "core/npc.h"
#include "core/cache.h"
#include "core/combat.h"
#include "core/training.h"
#include "core/animation.h"
#include "core/yard.h"
#include "core/audio.h"
#include "core/roster_game.h"
#include "data/art.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static BtpError error;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"CHI spatial %d: %s (%s)\n",__LINE__,#x,error.text);exit(1); } } while (0)
static const BtpMap *map(const BtpResources *r,unsigned id)
{ return id==1 ? &r->map : id==11 ? &r->destroyed : id==15 ? &r->maproom : &r->local[id-1]; }
static void render_equal(const BtpResources *a,const BtpResources *b,const BtpState *s)
{
    uint32_t *x=malloc(64000u*sizeof *x),*y=malloc(64000u*sizeof *y);CHECK(x && y);
    btp_render(a,s,0,x);btp_render(b,s,0,y);CHECK(!memcmp(x,y,64000u*sizeof *x));free(x);free(y);
}
static void spatial(const BtpResources *a,const BtpResources *b)
{
    CHECK(b->project->chi_spatial);CHECK(!memcmp(&a->world,&b->world,sizeof a->world));
    BtpState *s=calloc(1,sizeof *s);CHECK(s);
    for (unsigned id=1;id<=15;++id) {
        const BtpMap *m=map(a,id);CHECK(!memcmp(m,map(b,id),sizeof *m));
        for (unsigned y=0;y<m->height;++y) for (unsigned x=0;x<m->width;++x) {
            const BtpChiTile *t=btp_chi_map_cell(b,id,(int)x,(int)y);CHECK(t && t->rule==btp_map_tile(m,(int)x,(int)y));
            CHECK(t->graphic==t->rule && t->sheet==(id==11 ? 1u : id==14 ? 2u : id==15 ? 3u : 0u));
        }
        for (unsigned corner=0;corner<5;++corner) {
            btp_start(s);s->project=1;s->map_id=(uint8_t)id;s->story_flags[4]=(uint8_t)(id!=1);
            s->x_half=(uint16_t)(corner==4 ? m->width : corner&1u ? 2u*m->width-5u : 3u);
            s->y_half=(uint16_t)(corner==4 ? m->height : corner&2u ? 2u*m->height-5u : 3u);
            const BtpMap *origin=id==11 ? &a->map : m;
            s->campaign.world_x=(uint16_t)((origin->entrance_x[0]>>8)*128+s->x_half);s->campaign.world_y=(uint16_t)((origin->entrance_y[0]>>12)*128+s->y_half);
            if (id>=14) { s->cache.active=1;s->story_flags[66]=(uint8_t)(id==15);memcpy(s->cache.maproom,m->tiles,768);s->mode=BTP_CACHE;s->gate=(uint8_t)(id==15 ? 139 : 33); }
            render_equal(a,b,s);
        }
    }
    btp_start(s);s->project=1;s->mode=BTP_MISSION;s->mission.assignment=7;s->campaign.invasion=1;btp_combat_begin(s,a);
    render_equal(a,b,s);s->late.invasion_event=3;render_equal(a,b,s);
    free(s);
}
static void seeds(BtpResources *a,BtpResources *b)
{
    const unsigned seeds[]={0x020304u,1u,0xabcdefu};BtpState *s=calloc(1,sizeof *s);CHECK(s);
    for (unsigned k=0;k<3;++k) {
        CHECK(btp_world_generate(&a->world,seeds[k]) && btp_world_generate(&b->world,seeds[k]));
        CHECK(!memcmp(&a->world,&b->world,sizeof a->world));
        for (unsigned ruined=0;ruined<2;++ruined) {
            s->story_flags[4]=(uint8_t)ruined;
            for (int y=0;y<1024;++y) for (int x=0;x<1024;++x) CHECK(btp_world_tile(a,s,x,y)==btp_world_tile(b,s,x,y));
            for (unsigned y=0;y<2048;y+=16) for (unsigned x=0;x<2048;x+=16)
                CHECK(btp_world_deep_crossing(a,s,x,y,-1,-1)==btp_world_deep_crossing(b,s,x,y,-1,-1));
        }
    }
    free(s);puts("Compared 1,048,576 world cells and a 16-half-step depth-crossing grid for each of three seeds, before/after invasion.");
}
static void proof(const char *kind,const BtpResources *a,const BtpResources *b)
{
    BtpState *s=calloc(1,sizeof *s);CHECK(s);btp_start_content(s,b);s->project=1;
    if (!strcmp(kind,"block")) {
        BtpState *base=malloc(sizeof *base);CHECK(base);*base=*s;
        btp_game_tick(base,a,BTP_LEFT);btp_game_tick(s,b,BTP_LEFT);
        CHECK(base->x_half!=s->x_half && s->blocked==BTP_WALL);free(base);
    } else if (!strcmp(kind,"town")) {
        const BtpMap *m=&b->local[2];int x=(m->entrance_x[0]>>8)*64,y=(m->entrance_y[0]>>12)*64;
        CHECK(btp_world_location(b,s,x,y)==3 && btp_world_location(a,s,x,y)!=3);
        CHECK(btp_chi_preview(s,b,b->project->chi_spatial->maps[2].id,27,56));
        CHECK(s->campaign.world_x==(unsigned)x*2+27 && s->campaign.world_y==(unsigned)y*2+56);
        btp_game_tick(s,b,BTP_LEFT);CHECK(!s->npc.fault);
    } else if (!strcmp(kind,"door")) {
        const BtpMap *m=&b->map;s->x_half=m->entrance_x[3]&127;s->y_half=m->entrance_y[3]&127;
        CHECK(btp_entrance(s,m)==3 && btp_entrance(s,&a->map)!=3);
    } else if (!strcmp(kind,"routes")) CHECK(b->map.npc_routes[0]==1 && a->map.npc_routes[0]!=1);
    else if (!strcmp(kind,"starport")) {
        CHECK(btp_chi_map_offset(b,2,0));btp_yard_begin_arena(s,b);
        CHECK(s->campaign.battle_x==1216+btp_chi_map_offset(b,2,0));
        unsigned ox=(b->local[1].entrance_x[0]>>8)*128u,oy=(b->local[1].entrance_y[0]>>12)*128u;
        CHECK(btp_world_device_direction_resources(b,ox+56u,oy+56u)==0);
    } else if (!strcmp(kind,"broker")) {
        const BtpChiSpatial *c=b->project->chi_spatial;CHECK(c->broker_configured && c->broker_enabled);
        s->map_id=2;s->story_flags[4]=1;s->campaign.mounted=0;
        CHECK(btp_broker_door(s,b,c->broker_x,c->broker_y));CHECK(!btp_broker_door(s,b,54,50));
    } else if (!strcmp(kind,"jigsaw")) {
        int found=0;
        for (int y=0;y<1024 && !found;++y) for (int x=0;x<1024;++x) if (!btp_world_location(b,s,x,y) &&
            btp_world_tile(b,s,x,y)==85 && btp_world_tile(a,s,x,y)<85) { found=1;break; }
        CHECK(found);
    } else if (!strcmp(kind,"sprite")) {
        CHECK(b->sprites.pixels[0]==15 && b->sprites.pixels[0]!=a->sprites.pixels[0]);
    } else if (!strcmp(kind,"screen")) {
        CHECK(b->title.pixels[0]==15 && b->title.pixels[0]!=a->title.pixels[0]);s->mode=BTP_TITLE;
        uint32_t *frame=malloc(64000u*sizeof *frame);CHECK(frame);btp_render(b,s,0,frame);CHECK(frame[0]==btp_palette[15]);free(frame);
    } else if (!strcmp(kind,"film")) {
        CHECK(b->project->chi_animations[0]);CHECK(b->animations[0].units[0]==a->animations[0].units[0]+7u);
        s->mode=BTP_MISSION;CHECK(btp_cutscene_begin(s,b,0,2));CHECK(s->cutscene.remaining==b->animations[0].units[0]+50u);
        uint32_t *frame=malloc(64000u*sizeof *frame);CHECK(frame);btp_render(b,s,0,frame);CHECK(frame[8u*320+8]==btp_palette[15]);free(frame);
    } else if (!strcmp(kind,"font")) CHECK(b->dialogue.font[65u*8]==255);
    else if (!strcmp(kind,"citadel")) {
        CHECK(btp_citadel_origin(s,0)!=(a->map.entrance_x[0]>>8)*128u);
        s->mission.assignment=7;s->campaign.invasion=1;btp_combat_begin(s,b);
        CHECK(s->campaign.battle_x==btp_citadel_origin(s,0)-64u);
    } else if (!strcmp(kind,"audio")) {
        CHECK(b->sound_map[0]==2 && b->sound_speed==125);
        BtpResources *source=malloc(sizeof *source);CHECK(source);*source=*a;source->sound_speed=125;
        BtpAudioState x={.sound_count=1,.sounds={2}},y={.sound_count=1,.sounds={1}};
        int16_t left[4096],right[4096];btp_audio_samples(&x,source,4096,left);btp_audio_samples(&y,b,4096,right);
        CHECK(!memcmp(left,right,sizeof left));free(source);
    } else if (!strcmp(kind,"portrait")) {
        CHECK(b->project->chi_portraits[6]);s->mode=BTP_BUILDING;s->map_id=0;s->campaign.building=9;
        uint32_t *f=malloc(64000u*sizeof *f);CHECK(f);btp_render(b,s,0,f);CHECK(f[8u*320+8]==UINT32_C(0xffff55ff));free(f);
    } else if (!strcmp(kind,"forcefield")) {
        const BtpChiSpatial *c=b->project->chi_spatial;unsigned tile=0;
        while (tile<c->tile_count && strcmp(c->tiles[tile].id,"chi:land-106")) ++tile;
        CHECK(tile<c->tile_count && c->tiles[tile].sheet==4);
        unsigned cell=0;while (cell<4096 && c->maps[0].cells[cell]!=tile) ++cell;CHECK(cell<4096);
        s->x_half=(uint16_t)(2u*(cell%64));s->y_half=(uint16_t)(2u*(cell/64));
        const BtpArtImage *im=&b->project->graphics.images[c->tiles[tile].graphic];CHECK(im->count==3 && im->frame_ticks==4);
        unsigned at=0;while (at<256 && (at%16>=8 || b->project->graphics.pixels[im->frames[1]+at]==btp_palette[15])) ++at;CHECK(at<256);
        unsigned pixel=(96+at/16)*320+200+at%16;uint32_t *f=malloc(64000u*sizeof *f);CHECK(f);
        s->tick=0;btp_render(b,s,0,f);CHECK(f[pixel]==btp_palette[15]);s->tick=4;btp_render(b,s,0,f);CHECK(f[pixel]!=btp_palette[15]);free(f);
    }
    else CHECK(0);
    free(s);printf("Verified effective native edit: %s\n",kind);
}
int main(int argc,char **argv)
{
    if (argc==5 && !strcmp(argv[1],"--moved-route")) {
        BtpContent a={0},b={0};CHECK(btp_content_load_project(&a,argv[2],NULL,&error));CHECK(btp_content_load_project(&b,argv[3],NULL,&error));
        BtpState *x=calloc(1,sizeof *x),*y=calloc(1,sizeof *y);CHECK(x && y);
        btp_start_content(x,a.resources);btp_start_content(y,b.resources);x->project=y->project=1;
        btp_npc_init(x,&a.resources->map);btp_npc_init(y,&b.resources->map);
        FILE *f=fopen(argv[4],"r");CHECK(f);char line[128];unsigned ticks=0;
        while (fgets(line,sizeof line,f)) {
            line[strcspn(line,"\r\n")]=0;if (!*line || *line=='#') continue;BtpAction action;CHECK(btp_action_parse(line,&action));
            btp_game_tick(x,a.resources,action);btp_game_tick(y,b.resources,action);++ticks;
            CHECK(x->x_half==y->x_half && x->y_half==y->y_half && x->map_id==y->map_id && x->mode==y->mode && x->blocked==y->blocked);
            CHECK(x->credits==y->credits && x->script.pc==y->script.pc && x->script.status==y->script.status);
            CHECK(!memcmp(x->story_flags,y->story_flags,sizeof x->story_flags) && !memcmp(x->npc.rng,y->npc.rng,3));
        }
        CHECK(!fclose(f));printf("Verified %u local gameplay/RNG ticks after moving the Citadel.\n",ticks);
        free(x);free(y);btp_content_close(&a);btp_content_close(&b);return 0;
    }
    if (argc==5 && !strcmp(argv[1],"--held-film")) {
        BtpContent c={0};CHECK(btp_content_load_project(&c,argv[2],NULL,&error));
        BtpState *s=calloc(1,sizeof *s),*back=calloc(1,sizeof *back);CHECK(s && back);btp_start_content(s,c.resources);s->project=1;btp_npc_init(s,&c.resources->map);
        FILE *f=fopen(argv[3],"r");CHECK(f);char line[128];int found=0;
        while (fgets(line,sizeof line,f)) {
            line[strcspn(line,"\r\n")]=0;if (!*line || *line=='#') continue;BtpAction action;CHECK(btp_action_parse(line,&action));btp_game_tick(s,c.resources,action);
            if (s->cutscene.active==2) { found=1;break; }
        }
        CHECK(!fclose(f) && found);CHECK(btp_save_write(argv[4],s,c.resources,&error));CHECK(btp_save_load(argv[4],back,c.resources,&error));
        uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];btp_state_encode(s,a);btp_state_encode(back,b);CHECK(!memcmp(a,b,sizeof a));
        free(s);free(back);btp_content_close(&c);puts("Verified edited startup film held-save/reload through the real training route.");return 0;
    }
    if (argc==5 && !strcmp(argv[1],"--proof")) {
        BtpContent a={0},b={0};CHECK(btp_content_load_project(&a,argv[2],NULL,&error));CHECK(btp_content_load_project(&b,argv[3],NULL,&error));
        proof(argv[4],a.resources,b.resources);btp_content_close(&a);btp_content_close(&b);return 0;
    }
    CHECK(argc==6);BtpOriginalContentPaths paths={argv[1],argv[2],argv[3],argv[4]};BtpContent a={0},b={0};
    CHECK(btp_content_load_original(&a,&paths,&error));CHECK(btp_content_load_project(&b,argv[5],NULL,&error));
    spatial(a.resources,b.resources);seeds(a.resources,b.resources);
    btp_content_close(&a);btp_content_close(&b);puts("Verified all 15 native maps, all graphics-bank edge crops, generator tables, world cells and depth joins.");return 0;
}

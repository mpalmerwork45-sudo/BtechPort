#include "chi_resources.h"
#include "data/content.h"
#include "data/project.h"
#include "data/chi_presentation.h"
#include "data/anm.h"
#include "data/sprites.h"
#include "core/world.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

static int number(const char *text,unsigned max,unsigned *out)
{
    char *end;unsigned long v=strtoul(text,&end,10);
    if (!*text || *end || v>max) return 0;
    *out=(unsigned)v;return 1;
}
int btp_tool_chi_resource(int argc,char **argv)
{
    if (argc!=7) { fputs("Usage: btp-project chi-resource PROJECT tile|sprite|screen|animation|font RESOURCE INDEX COUNT\n",stderr);return 2; }
    BtpContent content={0};BtpError error={0};unsigned first,count;int ok=0;
    if (!number(argv[5],375,&first) || !number(argv[6],31,&count) || !count || !btp_content_load_project(&content,argv[2],NULL,&error)) goto done;
    BtpResources *r=content.resources;if (!r->project->chi_edition) goto done;
    const char *kind=argv[3],*resource=argv[4];BtpGraphic *g=btp_chi_graphic(r,resource);unsigned w=0,h=0,palette=0;
    BtpSpriteRect rect;
    if (!strcmp(kind,"sprite") && !strcmp(resource,"MECHSHAP.CMP") && first+count<=BTP_SPRITE_COUNT) {
        if (!btp_sprite_rect(first,&rect)) goto done;
        w=rect.width;h=rect.height;palette=1;
        for (unsigned i=1;i<count;++i) { BtpSpriteRect next;btp_sprite_rect(first+i,&next);if (next.width!=w || next.height!=h) goto done; }
    } else if (!strcmp(kind,"tile") && g && g->format==1 && first+count<=250) w=h=16;
    else if (!strcmp(kind,"screen") && g && !first && count==1) {
        w=320;h=200;palette=!strcmp(resource,"ENDMECH.CMP") ? 3u : !strcmp(resource,"BTTITLE.CMP") || !strcmp(resource,"INFOCOM.CMP") ? 4u : !strcmp(resource,"BTBORDER.CMP") ? 2u : 0u;
    } else if (!strcmp(kind,"animation") && !strcmp(resource,"O.ANM") && first<22) { w=h=88;palette=1;count=r->animations[first].count; }
    else if (!strcmp(kind,"portrait") && !strcmp(resource,"PORTRAITS") && first<BTP_PORTRAIT_COUNT && r->portraits.image[first].count) { w=h=88;palette=1;count=r->portraits.image[first].count; }
    else if (!strcmp(kind,"font") && !strcmp(resource,"BTTA.FONT") && !first && count==1) { w=h=128;palette=2; }
    else goto done;
    printf("{\"id\":\"chi:resource-preview\",\"name\":\"Original %s %s %u\",\"kind\":\"%s\",\"width\":%u,\"height\":%u,\"frames\":[",kind,resource,first,
        !strcmp(kind,"tile") ? "tile" : !strcmp(kind,"sprite") ? "sprite" : "screen",w,h);
    for (unsigned f=0;f<count;++f) {
        uint8_t packed[BTP_ANM_PACKED]={0};
        if (!strcmp(kind,"sprite")) btp_sprite_rect(first+f,&rect);
        unsigned custom=!strcmp(kind,"animation") ? r->project->chi_animations[first] : !strcmp(kind,"portrait") ? r->project->chi_portraits[first] : 0;
        const BtpAnm *animation=!strcmp(kind,"portrait") ? &r->portraits.image[first] : first<22 ? &r->animations[first] : NULL;
        if ((!strcmp(kind,"animation") || !strcmp(kind,"portrait")) && !custom && !btp_anm_frame(animation,f,packed)) goto done;
        printf("%s[",f ? "," : "");
        for (unsigned y=0;y<h;++y) {
            printf("%s\"",y ? "," : "");
            for (unsigned x=0;x<w;++x) {
                unsigned index=0,alpha=255;uint32_t color;
                if (!strcmp(kind,"sprite")) { index=g->pixels[(rect.y+y)*320+rect.x+x];if (!index) alpha=0; }
                else if (!strcmp(kind,"tile")) index=g->pixels[(first+f)*256+y*16+x];
                else if (!strcmp(kind,"screen")) index=g->pixels[y*320+x];
                else if (!strcmp(kind,"font")) { unsigned glyph=y/8*16+x/8;index=r->dialogue.font[glyph*8+y%8]&(128u>>(x%8)) ? 15u : 0u; }
                else { unsigned at=y*88+x;index=at&1u ? packed[at/2]&15u : packed[at/2]>>4; }
                color=btp_palette[btp_chi_palette(palette,index)];
                if (custom) {
                    const BtpArt *art=&r->project->graphics;const BtpArtImage *im=&art->images[custom-1];
                    color=art->pixels[im->frames[f]+y*w+x];alpha=color>>24;
                }
                printf("%06x%02x",color&0xffffffu,alpha);
            }
            putchar('"');
        }
        putchar(']');
    }
    printf("]");
    if (!strcmp(kind,"animation")) {
        printf(",\"native_units\":[");for (unsigned i=0;i<count;++i) printf("%s%u",i ? "," : "",r->animations[first].units[i]);putchar(']');
    }
    puts("}");ok=!ferror(stdout);
done:if (!ok) fprintf(stderr,"%s\n",error.text[0] ? error.text : "Invalid native resource/frame range; import or repair this project's local CHI resources.");
    btp_content_close(&content);return ok ? 0 : 1;
}
int btp_tool_chi_world(int argc,char **argv)
{
    unsigned ruined;if (argc!=4 || !number(argv[3],1,&ruined)) return 2;
    BtpContent c={0};BtpError e={0};if (!btp_content_load_project(&c,argv[2],NULL,&e)) { fprintf(stderr,"%s\n",e.text);return 1; }
    BtpState *s=calloc(1,sizeof *s);if (!s || !c.resources->project->chi_edition) { free(s);btp_content_close(&c);return 1; }
    s->story_flags[4]=(uint8_t)ruined;
    printf("{\"width\":128,\"height\":128,\"rows\":[");
    for (unsigned y=0;y<128;++y) {
        printf("%s\"",y ? "," : "");
        for (unsigned x=0;x<128;++x) {
            unsigned mini=btp_world_mini(c.resources,s,x,y),color=c.resources->world.mini_colors[mini&255u]&15u;
            printf("%06x",btp_palette[btp_chi_palette(1,color)]&0xffffffu);
        }
        putchar('"');
    }
    puts("]}");free(s);btp_content_close(&c);return ferror(stdout) ? 1 : 0;
}
int btp_tool_chi_grid(int argc,char **argv)
{
    unsigned underlay;if (argc!=4 || !number(argv[3],1,&underlay)) return 2;
    BtpContent c={0};BtpError e={0};int ok=0;
    if (!btp_content_load_project(&c,argv[2],NULL,&e)) goto done;
    BtpResources *r=c.resources;
    if (!r->project->chi_spatial) { snprintf(e.text,sizeof e.text,"Enable CHI map editing before requesting a native grid");goto done; }
    BtpState *s=calloc(1,sizeof *s);if (!s) goto done;
#ifdef _WIN32
    if (_setmode(_fileno(stdout),_O_BINARY)==-1) { free(s);goto done; }
#endif
    ok=fwrite("BTG1",1,4,stdout)==4;
    for (int y=0;y<1024 && ok;++y) {
        uint8_t row[2048];
        for (int x=0;x<1024;++x) {
            const BtpChiTile *tile=NULL;unsigned id=underlay ? 0u : (unsigned)btp_world_location(r,s,x,y);
            if (id) {
                const BtpMap *m=id==1 ? &r->map : &r->local[id-1];
                tile=btp_chi_map_cell(r,id,x-(m->entrance_x[0]>>8)*64,y-(m->entrance_y[0]>>12)*64);
            } else tile=btp_chi_generated_cell(r,underlay ? btp_generated_tile(&r->world,x,y) : btp_world_generated(r,s,x,y));
            unsigned handle=tile ? (unsigned)(tile-r->project->chi_spatial->tiles) : 65535u;
            row[2*x]=(uint8_t)handle;row[2*x+1]=(uint8_t)(handle>>8);
        }
        ok=fwrite(row,1,sizeof row,stdout)==sizeof row;
    }
    free(s);if (fflush(stdout)) ok=0;
done:if (!ok) fprintf(stderr,"%s\n",e.text[0] ? e.text : "Cannot export bounded native world grid");btp_content_close(&c);return ok ? 0 : 1;
}

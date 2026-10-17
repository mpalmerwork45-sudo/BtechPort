#include "frontend/art.h"
#include "data/project.h"
#include "core/events.h"
#include "core/world.h"
#include "frontend/pixels.h"

static uint32_t blend(uint32_t above,uint32_t below)
{
    unsigned alpha=above>>24;if (!alpha) return below;if (alpha==255) return above;
    uint32_t result=UINT32_C(0xff000000);
    for (unsigned shift=0;shift<24;shift+=8) {
        unsigned a=(above>>shift)&255u,b=(below>>shift)&255u;
        result|=((a*alpha+b*(255u-alpha)+127u)/255u)<<shift;
    }
    return result;
}
uint32_t btp_art_pixel(const BtpResources *r,unsigned id,unsigned frame,unsigned x,unsigned y,uint32_t below)
{
    if (!r->project || id>=r->project->graphics.count) return below;
    const BtpArt *a=&r->project->graphics;const BtpArtImage *im=&a->images[id];
    if (x>=im->width || y>=im->height) return below;
    return blend(a->pixels[im->frames[frame%im->count]+y*im->width+x],below);
}
int btp_art_draw(const BtpResources *r,unsigned id,unsigned frame,int x,int y,int left,int top,int right,int bottom,uint32_t f[BTP_PIXELS])
{
    if (!r->project || id>=r->project->graphics.count) return 0;
    const BtpArtImage *im=&r->project->graphics.images[id];
    for (unsigned yy=0;yy<im->height;++yy) for (unsigned xx=0;xx<im->width;++xx) {
        int px=x+(int)xx,py=y+(int)yy;
        if (px>=left && px<right && py>=top && py<bottom && px>=0 && px<320 && py>=0 && py<200)
            f[py*320+px]=btp_art_pixel(r,id,frame,xx,yy,f[py*320+px]);
    }
    return 1;
}
int btp_art_sprite(const BtpResources *r,unsigned slot,unsigned frame,int x,int y,int left,int top,int right,int bottom,uint32_t f[BTP_PIXELS])
{
    if (!r->project || slot>=BTP_ART_BINDINGS) return 0;
    return btp_art_draw(r,r->project->graphics.bindings[slot],frame,x,y,left,top,right,bottom,f);
}
int btp_art_picture(const BtpResources *r,const BtpState *s,uint32_t f[BTP_PIXELS])
{
    const BtpAdventure *a=btp_adventure(r);if (!a || s->event.phase!=BTP_EVENT_TEXT) return 0;
    const BtpEventNode *e=&a->nodes[s->event.node];if (e->op!=BTP_EVENT_PICTURE || e->picture==BTP_ART_NONE) return 0;
    const BtpArtImage *im=&r->project->graphics.images[e->picture];
    for (unsigned i=0;i<BTP_PIXELS;++i) f[i]=UINT32_C(0xff000000);
    return btp_art_draw(r,e->picture,s->tick/8u,(320-(int)im->width)/2,(200-(int)im->height)/2,0,0,320,200,f);
}
int btp_art_world_map(const BtpResources *r,const BtpState *s,uint32_t f[BTP_PIXELS])
{
    const BtpAdventure *a=btp_adventure(r);const BtpScene *m=btp_scene(r,s);
    if (!a || !m || !m->world) return 0;
    unsigned w=a->world_width/8,h=a->world_height/8,scale=280/w;
    if (scale>160/h) scale=160/h;
    if (scale>4) scale=4;
    int ox=(320-(int)(w*scale))/2,oy=(184-(int)(h*scale))/2;
    const uint32_t *palette=r->project->independent.loaded ? r->project->independent.palette : btp_palette;
    for (unsigned y=0;y<h;++y) for (unsigned x=0;x<w;++x) {
        const BtpSceneTile *t=btp_scene_tile(a,m,(int)(8*x+4)-(int)m->origin_x,(int)(8*y+4)-(int)m->origin_y);
        uint32_t color=t && btp_world_seen(s,x,y) ? palette[t->color] : palette[0];
        for (unsigned yy=0;yy<scale;++yy) for (unsigned xx=0;xx<scale;++xx) f[(oy+(int)(y*scale+yy))*320+ox+(int)(x*scale+xx)]=color;
    }
    int px=ox+(int)(s->campaign.world_x/16u*scale),py=oy+(int)(s->campaign.world_y/16u*scale);
    for (int d=-2;d<=2;++d) {
        if (px+d>=0 && px+d<320 && py>=0 && py<200) f[py*320+px+d]=palette[15];
        if (py+d>=0 && py+d<200 && px>=0 && px<320) f[(py+d)*320+px]=palette[15];
    }
    return 1;
}

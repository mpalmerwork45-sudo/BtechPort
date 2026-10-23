#include "data/chi_presentation.h"
#include "data/sprites.h"
#include <string.h>
#include <stdio.h>

BtpGraphic *btp_chi_graphic(BtpResources *r,const char *name)
{
    const char *const names[]={"BTTLTECH.ICN","DESTRUCT.ICN","ANIMATE.ICN","MECHSHAP.CMP","BTSTATS.CMP",
        "BTBORDER.CMP","BTTITLE.CMP","INFOCOM.CMP","TINYLAND.CMP","STARLEAG.ICN","MAP.ICN","ENDMECH.CMP"};
    BtpGraphic *graphics[]={&r->tiles,&r->destroyed_tiles,&r->terrain_animation,&r->sprites,&r->quiz_diagram,
        &r->border,&r->title,&r->logo,&r->tinyland,&r->cache_tiles,&r->maproom_tiles,&r->phoenix};
    for (unsigned i=0;i<12;++i) if (!strcmp(name,names[i])) return graphics[i];
    return NULL;
}
unsigned btp_chi_palette(unsigned palette,unsigned index)
{
    static const uint8_t maps[5][16]={
        {0,1,2,3,4,9,6,7,8,1,10,11,12,13,14,15},
        {0,0,2,3,4,9,6,7,8,1,10,11,12,13,14,15},
        {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15},
        {0,0,2,3,4,5,6,7,8,1,10,11,12,9,14,15},
        {0,0,2,3,4,9,6,7,8,1,10,11,12,13,14,15}};
    return maps[palette<5 ? palette : 0][index&15u];
}
static unsigned rgb(unsigned index)
{
    static const unsigned colors[]={0x000000,0x0000aa,0x00aa00,0x00aaaa,0xaa0000,0xaa00aa,0xaa5500,0xaaaaaa,
        0x555555,0x5555ff,0x55ff55,0x55ffff,0xff5555,0xff55ff,0xffff55,0xffffff};
    return colors[index&15u];
}
static unsigned quantize(uint32_t color,unsigned palette,int transparent)
{
    if (transparent && (color>>24)<128) return 0;
    unsigned best=0,distance=UINT32_MAX;
    for (unsigned i=transparent ? 1u : 0u;i<16;++i) {
        unsigned native=rgb(btp_chi_palette(palette,i)),d=0;
        for (unsigned shift=0;shift<24;shift+=8) { int delta=(int)((color>>shift)&255u)-(int)((native>>shift)&255u);d+=(unsigned)(delta*delta); }
        if (d<distance) { distance=d;best=i; }
    }
    return best;
}
static int text(BtpJson *j,unsigned n,const char *key,char *out,size_t size)
{ return btp_json_string(j,btp_json_field(j,n,key),out,size); }
static int num(BtpJson *j,unsigned n,const char *key,unsigned lo,unsigned hi,unsigned *v)
{ return btp_json_uint(j,btp_json_field(j,n,key),lo,hi,v); }
int btp_chi_presentation_load(const char *root,const char *file,BtpProject *p,BtpPortraits *portraits,BtpDigest *digest,BtpError *e)
{
    char path[4096],format[64];BtpJson j={0};unsigned version;int ok=0;BtpResources *r=p->chi_resources;
    if (!r || !btp_project_path(root,file,path,e) || !btp_json_load(&j,path,e->text)) goto done;
    btp_digest_add(digest,j.source_digest,32);
    if (!text(&j,1,"format",format,sizeof format) || strcmp(format,"btp-chi-presentation-v1") ||
        !num(&j,1,"schema_version",1,1,&version)) goto done;
    unsigned list=btp_json_field(&j,1,"bindings"),count=0;uint8_t animations[22]={0};
    if (!btp_json_type(&j,list,'[')) goto done;
    for (unsigned n=j.nodes[list].first;n;n=j.nodes[n].next) {
        char kind[24],image[64],resource[64],palette[24];unsigned index;
        if (++count>1024 || !text(&j,n,"kind",kind,sizeof kind) || !text(&j,n,"image",image,sizeof image) ||
            !num(&j,n,"index",0,375,&index) || !text(&j,n,"resource",resource,sizeof resource) || !text(&j,n,"palette",palette,sizeof palette)) goto done;
        unsigned at=btp_art_find(&p->graphics,image);if (at==BTP_ART_NONE) { btp_json_error(&j,n,"binding image is missing");goto done; }
        const BtpArtImage *im=&p->graphics.images[at];unsigned pal=0;
        const char *const palettes[]={"terrain","sprite","direct","phoenix","title"};
        while (pal<5 && strcmp(palette,palettes[pal])) ++pal;
        if (pal==5) { btp_json_error(&j,n,"unsupported native palette");goto done; }
        if (!strcmp(kind,"portrait")) {
            if (strcmp(resource,"PORTRAITS") || index>=BTP_PORTRAIT_COUNT || im->width!=88 || im->height!=88 || im->count>31 || p->chi_portraits[index]) {
                btp_json_error(&j,n,"portrait requires a unique slot and 88x88 frames");goto done;
            }
            p->chi_portraits[index]=(uint16_t)(at+1);portraits->image[index].count=(uint8_t)im->count;
        } else if (!strcmp(kind,"animation")) {
            if (strcmp(resource,"O.ANM") || index>=22 || animations[index] || im->width!=88 || im->height!=88 || im->count!=r->animations[index].count) {
                btp_json_error(&j,n,"animation binding requires the native frame count and 88x88 frames");goto done;
            }
            animations[index]=1;p->chi_animations[index]=(uint16_t)(at+1);
            unsigned units=btp_json_field(&j,n,"units"),i=0;if (!btp_json_type(&j,units,'[')) goto done;
            for (unsigned u=j.nodes[units].first;u;u=j.nodes[u].next,++i) {
                unsigned ticks;if (i==im->count || !btp_json_uint(&j,u,0,16300,&ticks)) goto done;r->animations[index].units[i]=(uint16_t)ticks;
            }
            if (i!=im->count) { btp_json_error(&j,units,"one duration in retraces per frame required");goto done; }
        } else if (!strcmp(kind,"font")) {
            if (strcmp(resource,"BTTA.FONT") || index || im->width!=128 || im->height!=128 || im->count!=1) { btp_json_error(&j,n,"font is one 128x128 image of 256 8x8 glyphs");goto done; }
            for (unsigned glyph=0;glyph<256;++glyph) for (unsigned y=0;y<8;++y) {
                unsigned bits=0;
                for (unsigned x=0;x<8;++x) {
                    uint32_t c=p->graphics.pixels[im->frames[0]+(glyph/16*8+y)*128+glyph%16*8+x];
                    if ((c>>24)>=128 && (c&0xffffffu)) bits|=128u>>x;
                }
                r->dialogue.font[glyph*8+y]=(uint8_t)bits;
            }
        } else {
            BtpGraphic *sheet=btp_chi_graphic(r,resource);unsigned x=0,y=0,stride=0;
            if (!sheet) { btp_json_error(&j,n,"unknown native graphic resource");goto done; }
            if (!strcmp(kind,"sprite")) {
                if (strcmp(resource,"MECHSHAP.CMP") || index+im->count>BTP_SPRITE_COUNT) goto bad_size;
                for (unsigned f=0;f<im->count;++f) {
                    BtpSpriteRect rect;btp_sprite_rect(index+f,&rect);
                    if (rect.width!=im->width || rect.height!=im->height) goto bad_size;
                    for (unsigned yy=0;yy<im->height;++yy) for (unsigned xx=0;xx<im->width;++xx)
                        sheet->pixels[(rect.y+yy)*320+rect.x+xx]=(uint8_t)quantize(p->graphics.pixels[im->frames[f]+yy*im->width+xx],pal,1);
                }
            } else {
                if (!strcmp(kind,"tile") && sheet->format==1 && index<250 && im->width==16 && im->height==16 && im->count==1) { y=index*16;stride=16; }
                else if (!strcmp(kind,"screen") && im->width==320 && im->height==200 && im->count==1 && !index) stride=320;
                else goto bad_size;
                for (unsigned yy=0;yy<im->height;++yy) for (unsigned xx=0;xx<im->width;++xx)
                    sheet->pixels[(y+yy)*stride+x+xx]=(uint8_t)quantize(p->graphics.pixels[im->frames[0]+yy*im->width+xx],pal,0);
            }
        }
        if (!btp_json_done(&j,n)) goto done;
        continue;
bad_size:btp_json_error(&j,n,"native graphic dimensions/frame range do not match the target");goto done;
    }
    unsigned sounds=btp_json_field(&j,1,"sounds"),i=0;if (!btp_json_type(&j,sounds,'[')) goto done;
    for (unsigned n=j.nodes[sounds].first;n;n=j.nodes[n].next,++i) {
        unsigned source;if (i==18 || !btp_json_uint(&j,n,1,18,&source)) goto done;r->sound_map[i]=(uint8_t)source;
    }
    unsigned speed,enabled;
    if (i!=18 || !num(&j,1,"sound_speed",25,400,&speed) || !num(&j,1,"music",0,1,&enabled) || !btp_json_done(&j,1)) goto done;
    r->sound_speed=(uint16_t)speed;if (!enabled) r->music_length=0;ok=1;
done:if (!ok && !e->text[0]) snprintf(e->text,sizeof e->text,"Invalid CHI presentation bindings");btp_json_close(&j);return ok;
}

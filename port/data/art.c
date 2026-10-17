#include "data/art.h"
#include "data/json.h"
#include <stdlib.h>
#include <string.h>

unsigned btp_art_find(const BtpArt *a,const char *id)
{
    for (unsigned i=0;i<a->count;++i) if (!strcmp(a->images[i].id,id)) return i;
    return BTP_ART_NONE;
}
static int hex(unsigned char c)
{ return c>='0' && c<='9' ? c-'0' : c>='a' && c<='f' ? c-'a'+10 : -1; }
int btp_art_load(const char *path,BtpArt *out,char error[256])
{
    BtpArt *a=calloc(1,sizeof *a);BtpJson j={0};int ok=0;char text[96];unsigned v;
    if (!a) { if (error) strcpy(error,"graphics allocation failed");return 0; }
    for (unsigned i=0;i<BTP_ART_BINDINGS;++i) a->bindings[i]=BTP_ART_NONE;
    if (!btp_json_load_large(&j,path,error)) goto done;
    if (!btp_json_string(&j,btp_json_field(&j,1,"format"),text,sizeof text) || strcmp(text,"btp-art-v1") ||
        !btp_json_uint(&j,btp_json_field(&j,1,"schema_version"),1,1,&v)) { btp_json_error(&j,1,"expected btp-art-v1 schema 1");goto done; }
    unsigned images=btp_json_field(&j,1,"images");if (!btp_json_type(&j,images,'[')) goto done;
    for (unsigned n=j.nodes[images].first;n;n=j.nodes[n].next) {
        if (a->count==BTP_ART_IMAGES) { btp_json_error(&j,n,"at most 4096 images");goto done; }
        BtpArtImage *im=&a->images[a->count];unsigned w,h;
        if (!btp_json_string(&j,btp_json_field(&j,n,"id"),im->id,sizeof im->id) || !btp_content_id(im->id,1) ||
            !btp_json_string(&j,btp_json_field(&j,n,"name"),im->name,sizeof im->name) ||
            !btp_json_uint(&j,btp_json_field(&j,n,"width"),1,320,&w) ||
            !btp_json_uint(&j,btp_json_field(&j,n,"height"),1,200,&h) ||
            !btp_json_string(&j,btp_json_field(&j,n,"kind"),text,sizeof text)) goto done;
        const char *const kinds[]={"tile","sprite","icon","screen"};
        unsigned kind=0;while (kind<4 && strcmp(text,kinds[kind])) ++kind;
        if (kind==4 || (kind==0 && (w!=16 || h!=16)) ||
            ((kind==1 || kind==2) && (w>64 || h>64))) { btp_json_error(&j,n,"tile is 16x16; sprite/icon at most 64x64; screen at most 320x200");goto done; }
        if (btp_art_find(a,im->id)!=BTP_ART_NONE) { btp_json_error(&j,n,"duplicate image ID");goto done; }
        im->width=(uint16_t)w;im->height=(uint16_t)h;im->kind=(uint16_t)kind;
        unsigned frames=btp_json_field(&j,n,"frames");if (!btp_json_type(&j,frames,'[')) goto done;
        for (unsigned f=j.nodes[frames].first;f;f=j.nodes[f].next) {
            if (im->count==BTP_ART_FRAMES || a->used+w*h>BTP_ART_PIXELS || !btp_json_type(&j,f,'[')) { btp_json_error(&j,f,"graphics frame/total pixel budget exceeded");goto done; }
            im->frames[im->count++]=a->used;unsigned y=0;
            for (unsigned r=j.nodes[f].first;r;r=j.nodes[r].next) {
                char row[2561];
                if (y==h || !btp_json_string(&j,r,row,sizeof row) || strlen(row)!=w*8u) { btp_json_error(&j,r,"expected eight RGBA hex digits per pixel, exact image dimensions");goto done; }
                for (unsigned x=0;x<w;++x) {
                    uint32_t rgba=0;
                    for (unsigned k=0;k<8;++k) { int z=hex((unsigned char)row[x*8+k]);if (z<0) { btp_json_error(&j,r,"pixels use lowercase RGBA hexadecimal");goto done; }rgba=(rgba<<4)|(unsigned)z; }
                    a->pixels[a->used++]=(rgba>>8)|(rgba<<24);
                }
                ++y;
            }
            if (y!=h) { btp_json_error(&j,f,"incorrect image height");goto done; }
        }
        if (!im->count || !btp_json_done(&j,n)) { btp_json_error(&j,n,"image needs frames");goto done; }
        ++a->count;
    }
    unsigned bindings=btp_json_field(&j,1,"bindings");if (!btp_json_type(&j,bindings,'[')) goto done;
    const char *const slots[]={"player","npc","enemy","locust","stinger","wreck"};
    for (unsigned n=j.nodes[bindings].first;n;n=j.nodes[n].next) {
        char id[64];
        if (!btp_json_string(&j,btp_json_field(&j,n,"slot"),text,sizeof text) ||
            !btp_json_string(&j,btp_json_field(&j,n,"image"),id,sizeof id) || !btp_json_done(&j,n)) goto done;
        unsigned slot=0;while (slot<BTP_ART_BINDINGS && strcmp(text,slots[slot])) ++slot;
        unsigned im=btp_art_find(a,id);
        if (slot==BTP_ART_BINDINGS || a->bindings[slot]!=BTP_ART_NONE || im==BTP_ART_NONE || a->images[im].kind!=1) { btp_json_error(&j,n,"binding needs a unique supported slot and a sprite image");goto done; }
        a->bindings[slot]=(uint16_t)im;
    }
    if (!btp_json_done(&j,1)) goto done;
    a->loaded=1;memcpy(a->source_digest,j.source_digest,32);*out=*a;ok=1;
done:
    btp_json_close(&j);free(a);return ok;
}

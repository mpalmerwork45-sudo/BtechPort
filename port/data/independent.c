#include "data/independent.h"
#include "data/project.h"
#include "data/json.h"
#include <stdlib.h>
#include <string.h>

static unsigned array(BtpJson *j,unsigned parent,const char *key)
{ unsigned n=btp_json_field(j,parent,key);return btp_json_type(j,n,'[') ? n : 0; }
static int num(BtpJson *j,unsigned p,const char *key,unsigned lo,unsigned hi,unsigned *v)
{ return btp_json_uint(j,btp_json_field(j,p,key),lo,hi,v); }
static int hex(unsigned char c)
{ return c>='0' && c<='9' ? c-'0' : c>='a' && c<='f' ? c-'a'+10 : -1; }
static int image(BtpJson *j,unsigned n,unsigned w,unsigned h,uint8_t *pixels)
{
    if (!btp_json_type(j,n,'[')) return 0;
    unsigned y=0;char row[65];
    for (unsigned k=j->nodes[n].first;k;k=j->nodes[k].next) {
        if (y==h || !btp_json_string(j,k,row,sizeof row) || strlen(row)!=w) return btp_json_error(j,k,"incorrect bitmap dimensions");
        for (unsigned x=0;x<w;++x) { int v=hex((unsigned char)row[x]);if (v<0) return btp_json_error(j,k,"pixels must be lowercase hexadecimal palette indices");pixels[y*w+x]=(uint8_t)v; }
        ++y;
    }
    return y==h || btp_json_error(j,n,"incorrect bitmap height");
}
static int formation(BtpJson *j,const char *key,unsigned count,int8_t *xs,int8_t *ys)
{
    unsigned n=array(j,1,key),i=0;if (!n) return 0;
    for (unsigned k=j->nodes[n].first;k;k=j->nodes[k].next) {
        if (i==count || !btp_json_type(j,k,'[')) return btp_json_error(j,k,"incorrect formation length");
        unsigned a=j->nodes[k].first,b=a ? j->nodes[a].next : 0,x,y;
        if (!a || !b || j->nodes[b].next || !btp_json_uint(j,a,0,16,&x) || !btp_json_uint(j,b,0,16,&y)) return btp_json_error(j,k,"formation is [x+8,y+8], within 0..16");
        xs[i]=(int8_t)((int)x-8);ys[i++]=(int8_t)((int)y-8);
    }
    return i==count || btp_json_error(j,n,"incorrect formation length");
}
int btp_independent_load(const char *path,BtpIndependent *out,char error[256])
{
    BtpIndependent *v=calloc(1,sizeof *v);BtpJson j={0};int ok=0;unsigned n,i=0,a;char text[96];
    if (!v || !btp_json_load(&j,path,error)) goto done;
    if (!btp_json_string(&j,btp_json_field(&j,1,"format"),text,sizeof text) || strcmp(text,"btp-presentation-v1") ||
        !num(&j,1,"schema_version",1,1,&a)) { btp_json_error(&j,1,"expected btp-presentation-v1 schema 1");goto done; }
    n=array(&j,1,"palette");if (!n) goto done;
    for (unsigned k=j.nodes[n].first;k;k=j.nodes[k].next) {
        if (i==16 || !btp_json_string(&j,k,text,sizeof text) || strlen(text)!=6) { btp_json_error(&j,k,"palette needs sixteen six-digit RGB values");goto done; }
        uint32_t c=0xff000000u;for (unsigned z=0;z<6;++z) { int h=hex((unsigned char)text[z]);if (h<0) { btp_json_error(&j,k,"invalid RGB value");goto done; }c|=(uint32_t)h<<((5u-z)*4u); }v->palette[i++]=c;
    }
    if (i!=16) { btp_json_error(&j,n,"palette needs sixteen colors");goto done; }
    n=array(&j,1,"font");i=0;if (!n) goto done;
    for (unsigned k=j.nodes[n].first;k;k=j.nodes[k].next) {
        if (i==96 || !btp_json_string(&j,k,text,sizeof text) || strlen(text)!=14) { btp_json_error(&j,k,"font needs 96 glyphs of seven two-digit rows");goto done; }
        for (unsigned y=0;y<7;++y) { int h=hex((unsigned char)text[2*y]),l=hex((unsigned char)text[2*y+1]);if (h<0 || l<0 || h*16+l>31) { btp_json_error(&j,k,"font rows contain five bits");goto done; }v->font[i][y]=(uint8_t)(h*16+l); }++i;
    }
    if (i!=96) { btp_json_error(&j,n,"font needs 96 glyphs");goto done; }
    n=array(&j,1,"tiles");if (!n) goto done;
    for (unsigned k=j.nodes[n].first;k;k=j.nodes[k].next) {
        if (v->tile_count==64 || !image(&j,k,16,16,v->tiles[v->tile_count++])) goto done;
    }
    if (!v->tile_count) { btp_json_error(&j,n,"at least one tile required");goto done; }
    n=array(&j,1,"sprites");i=0;if (!n) goto done;
    for (unsigned k=j.nodes[n].first;k;k=j.nodes[k].next) {
        if (i==5 || !btp_json_type(&j,k,'[')) { btp_json_error(&j,k,"five sprite families required");goto done; }
        unsigned frame=0;for (unsigned z=j.nodes[k].first;z;z=j.nodes[z].next) {
            if (frame==4 || !image(&j,z,16,16,v->sprites[i][frame++])) goto done;
        }
        if (frame!=4) { btp_json_error(&j,k,"each sprite has four walk frames");goto done; }++i;
    }
    if (i!=5) { btp_json_error(&j,n,"five sprite families required");goto done; }
    n=array(&j,1,"portraits");i=0;if (!n) goto done;
    for (unsigned k=j.nodes[n].first;k;k=j.nodes[k].next) if (i==2 || !image(&j,k,64,64,v->portraits[i++])) goto done;
    if (i!=2) { btp_json_error(&j,n,"two 64x64 portraits required");goto done; }
    n=array(&j,1,"hit_locations");i=0;if (!n) goto done;
    for (unsigned k=j.nodes[n].first;k;k=j.nodes[k].next) { if (i==11 || !btp_json_uint(&j,k,0,7,&a)) goto done;v->locations[i++]=(uint8_t)a; }
    if (i!=11 || !formation(&j,"people_formation",8,v->people_x,v->people_y) || !formation(&j,"mech_formation",4,v->mechs_x,v->mechs_y)) goto done;
    n=btp_json_field(&j,1,"personal_weapon");
    if (!btp_json_string(&j,btp_json_field(&j,n,"label"),v->personal_label,sizeof v->personal_label) ||
        !num(&j,n,"damage",1,15,&v->personal_damage) || !num(&j,n,"range",3,31,&v->personal_range) || !btp_json_done(&j,n)) goto done;
    n=array(&j,1,"sounds");i=0;if (!n) goto done;
    for (unsigned k=j.nodes[n].first;k;k=j.nodes[k].next) {
        if (i==18 || !btp_json_type(&j,k,'[')) { btp_json_error(&j,k,"eighteen sound programs required");goto done; }
        unsigned tone=0,total=0;
        for (unsigned z=j.nodes[k].first;z;z=j.nodes[z].next) {
            unsigned hz,ms;if (tone==8 || !num(&j,z,"hz",50,4000,&hz) || !num(&j,z,"ms",1,400,&ms) || !btp_json_done(&j,z)) goto done;
            total+=ms;v->sound_hz[i][tone]=(uint16_t)hz;v->sound_ms[i][tone++]=(uint16_t)ms;
        }
        if (!tone || total>1200) { btp_json_error(&j,k,"sound must last 1..1200 milliseconds");goto done; }v->sound_count[i++]=(uint8_t)tone;
    }
    if (i!=18 || !btp_json_done(&j,1)) goto done;
    memcpy(v->source_digest,j.source_digest,32);v->loaded=1;*out=*v;ok=1;
done:
    if (!ok && error && !*error) btp_json_error(&j,1,"invalid independent presentation");
    btp_json_close(&j);free(v);return ok;
}
void btp_independent_resources(BtpResources *r)
{
    const BtpIndependent *v=&r->project->independent;BtpCombatData *c=&r->combat;
    /* Independently authored tactical defaults for the shared anatomy adapter.
       No original tables, pictures, speaker programs or cache files are read. */
    memcpy(c->formation_x,v->people_x,8);memcpy(c->formation_y,v->people_y,8);
    memcpy(c->mech_formation_x,v->mechs_x,4);memcpy(c->mech_formation_y,v->mechs_y,4);
    for (unsigned i=0;i<46;++i) c->locations[i]=(uint8_t)(17u+v->locations[i%11u]);
    /* Deterministic authored cluster schedule, independent of facing. */
    for (unsigned i=0;i<93;++i) c->clusters[i]=1;
    static const uint8_t starts[]={51,58,79,85,83,65,72,81},counts[]={7,7,2,1,2,7,7,2};
    memcpy(c->critical_start,starts,8);memcpy(c->critical_count,counts,8);
    for (unsigned i=0;i<33;++i) {
        memset(c->weapons[i],' ',11);memcpy(c->weapons[i],v->personal_label,strlen(v->personal_label));
        c->weapons[i][11]=(uint8_t)v->personal_damage;c->weapons[i][12]=129;
        c->weapons[i][14]=(uint8_t)(32u+v->personal_range/2u);c->weapons[i][15]=(uint8_t)v->personal_range;c->weapons[i][16]=0;
    }
    for (unsigned i=0;i<18;++i) {
        c->sound_count[i]=v->sound_count[i];
        for (unsigned k=0;k<v->sound_count[i];++k) c->sound[i][k]=(BtpSpeakerEvent){.clocks=1193u*v->sound_ms[i][k],.divisor=(uint16_t)(1193182u/v->sound_hz[i][k]),.type=1};
    }
}

#include "data/chi_spatial.h"
#include "data/project.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static int text(BtpJson *j,unsigned n,const char *key,char *out,size_t size)
{ return btp_json_string(j,btp_json_field(j,n,key),out,size); }
static int num(BtpJson *j,unsigned n,const char *key,unsigned lo,unsigned hi,unsigned *out)
{ return btp_json_uint(j,btp_json_field(j,n,key),lo,hi,out); }
static int pair(BtpJson *j,unsigned n,unsigned max,unsigned *x,unsigned *y)
{
    if (!btp_json_type(j,n,'[')) return 0;
    unsigned a=j->nodes[n].first,b=a ? j->nodes[a].next : 0;
    if (!b || j->nodes[b].next) return btp_json_error(j,n,"expected [x, y]");
    return btp_json_uint(j,a,0,max,x) && btp_json_uint(j,b,0,max,y);
}
static int bytes(BtpJson *j,unsigned n,uint8_t *out,unsigned count,unsigned max)
{
    unsigned i=0;if (!btp_json_type(j,n,'[')) return 0;
    for (unsigned p=j->nodes[n].first;p;p=j->nodes[p].next) {
        unsigned v;if (i==count || !btp_json_uint(j,p,0,max,&v)) return btp_json_error(j,p,"invalid table length/value");
        out[i++]=(uint8_t)v;
    }
    return i==count || btp_json_error(j,n,"incomplete table");
}
static int ref(BtpJson *j,unsigned n,BtpChiSpatial *s,unsigned *out)
{
    char id[64];if (!btp_json_string(j,n,id,sizeof id)) return 0;
    for (unsigned i=0;i<s->tile_count;++i) if (!strcmp(id,s->tiles[i].id)) { *out=i;return 1; }
    return btp_json_error(j,n,"unresolved tile ID");
}
static BtpMap *map(BtpResources *r,unsigned id)
{ return id==1 ? &r->map : id==11 ? &r->destroyed : id==15 ? &r->maproom : &r->local[id-1]; }
static int label(BtpJson *j,unsigned n,uint8_t out[16])
{
    char name[17];uint8_t raw[16];
    unsigned field=btp_json_field(j,n,"name");
    if (!btp_json_type(j,field,'"') || strlen(j->nodes[field].text)>16 || !bytes(j,btp_json_field(j,n,"label_bytes"),raw,16,255)) return 0;
    strcpy(name,j->nodes[field].text);
    char original[17];memcpy(original,raw,16);original[16]=0;
    for (unsigned i=0;i<16 && original[i];++i) if ((unsigned char)original[i]<32 || (unsigned char)original[i]>=127) original[i]='?';
    /* Unedited imports retain every original padding/string-table byte.
       Renaming replaces this slot alone, leaving adjacent slots untouched. */
    memcpy(out,raw,16);
    if (strcmp(original,name)) { memset(out,0,16);memcpy(out,name,strlen(name)); }
    return 1;
}
static int tiles(BtpJson *j,BtpChiSpatial *s)
{
    unsigned a=btp_json_field(j,1,"tiles");if (!btp_json_type(j,a,'[')) return 0;
    for (unsigned n=j->nodes[a].first;n;n=j->nodes[n].next) {
        if (s->tile_count==BTP_CHI_TILES) return btp_json_error(j,n,"at most 4096 tile definitions");
        BtpChiTile *t=&s->tiles[s->tile_count];char sheet[32];unsigned value;
        if (!text(j,n,"id",t->id,sizeof t->id) || !btp_content_id(t->id,1) ||
            !text(j,n,"name",t->name,sizeof t->name) || !text(j,n,"sheet",sheet,sizeof sheet) ||
            !num(j,n,"rule",0,249,&value)) return 0;
        t->rule=(uint8_t)value;
        t->water=2;unsigned water=btp_json_optional(j,n,"water");
        if (water) { if (!btp_json_uint(j,water,0,2,&value)) return 0;t->water=(uint8_t)value; }
        t->mini_color=255;unsigned mini=btp_json_optional(j,n,"mini_color");
        if (mini) { if (!btp_json_uint(j,mini,0,15,&value)) return 0;t->mini_color=(uint8_t)value; }
        for (unsigned i=0;i<s->tile_count;++i) if (!strcmp(t->id,s->tiles[i].id)) return btp_json_error(j,n,"duplicate tile ID");
        const char *banks[]={"chi:land","chi:destroyed","chi:cache","chi:maproom","package:art"};
        unsigned k=0;while (k<5 && strcmp(sheet,banks[k])) ++k;
        if (k==5) return btp_json_error(j,n,"unsupported tile sheet");
        t->sheet=(uint8_t)k;
        if (k==4) { if (!text(j,n,"graphic",t->image,sizeof t->image)) return 0; }
        else { if (!num(j,n,"graphic",0,249,&value)) return 0;t->graphic=(uint16_t)value; }
        if (!btp_json_done(j,n)) return 0;
        ++s->tile_count;
    }
    if (!s->tile_count) return btp_json_error(j,a,"tiles cannot be empty");
    return 1;
}
static int rows(BtpJson *j,unsigned a,BtpChiSpatial *s,BtpChiMap *m,BtpMap *out,unsigned ox,unsigned oy,int overlay)
{
    if (!btp_json_type(j,a,'[')) return 0;
    unsigned w=0,h=0;
    for (unsigned r=j->nodes[a].first;r;r=j->nodes[r].next) {
        unsigned x=0;if (!btp_json_type(j,r,'[') || oy+h>=out->height) return btp_json_error(j,r,"rows exceed map height");
        for (unsigned c=j->nodes[r].first;c;c=j->nodes[c].next,++x) {
            unsigned t;if (ox+x>=out->width) return btp_json_error(j,c,"row exceeds map width");
            if (overlay && j->nodes[c].type=='"' && !strcmp(j->nodes[c].text," ")) continue;
            if (!ref(j,c,s,&t)) return 0;
            m->cells[(oy+h)*out->width+ox+x]=(uint16_t)t;out->tiles[(oy+h)*out->width+ox+x]=s->tiles[t].rule;
        }
        if (!x || (h && x!=w) || (!overlay && x!=out->width)) return btp_json_error(j,r,"rows must be rectangular");
        w=x;++h;
    }
    return (h && (overlay || h==out->height)) || btp_json_error(j,a,"incomplete map rows");
}
static int maps(BtpJson *j,BtpChiSpatial *s,BtpResources *r)
{
    unsigned a=btp_json_field(j,1,"maps"),seen=0,id_count=0;const char *identities[360];
    if (!btp_json_type(j,a,'[')) return 0;
    for (unsigned n=j->nodes[a].first;n;n=j->nodes[n].next) {
        unsigned slot,w,h,x,y;if (!num(j,n,"slot",1,15,&slot)) return 0;
        if (seen&(1u<<slot)) return btp_json_error(j,n,"duplicate native map slot");
        seen|=1u<<slot;BtpMap *out=map(r,slot);BtpChiMap *m=&s->maps[slot-1];
        m->original_x=(uint16_t)((out->entrance_x[0]>>8)*64u);m->original_y=(uint16_t)((out->entrance_y[0]>>12)*64u);
        m->source_width=out->width;m->source_height=out->height;
        if (!text(j,n,"id",m->id,sizeof m->id) || !btp_content_id(m->id,1) || !text(j,n,"name",m->name,sizeof m->name) ||
            !num(j,n,"width",8,64,&w) || !num(j,n,"height",8,64,&h) || w%8 || h%8 ||
            !pair(j,btp_json_field(j,n,"origin"),960,&x,&y) || x%64 || y%64)
            return btp_json_error(j,n,"map dimensions/origin must align to native 8/64-tile grids");
        for (unsigned i=0;i<15;++i) if (i!=slot-1 && s->maps[i].id[0] && !strcmp(m->id,s->maps[i].id)) return btp_json_error(j,n,"duplicate map ID");
        out->width=m->width=(uint8_t)w;out->height=m->height=(uint8_t)h;
        if (((slot==1 || slot==2 || slot==11 || slot==14) && (w!=64 || h!=64)) || (slot==15 && (w!=32 || h!=24)))
            return btp_json_error(j,n,"Citadel/starport/corridors retain 64x64 bounds; map room retains 32x24");
        if ((slot==1 || slot==11) && (x<64 || y<64)) return btp_json_error(j,n,"Citadel needs a surrounding sector for its invasion battlefield");
        if (slot==2 && x<64) return btp_json_error(j,n,"starport needs a western sector for the arena escape band");
        if (slot>=14 && (x || y)) return btp_json_error(j,n,"cache interiors use local room coordinates, with origin [0,0]");
        if (!rows(j,btp_json_field(j,n,"rows"),s,m,out,0,0,0)) return 0;
        unsigned overlays=btp_json_field(j,n,"overlays");if (!btp_json_type(j,overlays,'[')) return 0;
        unsigned overlay_count=0;
        for (unsigned o=j->nodes[overlays].first;o;o=j->nodes[o].next) {
            if (++overlay_count>32) return btp_json_error(j,o,"at most 32 overlays per map");
            char id[64],name[64];unsigned xx,yy;
            unsigned id_field=btp_json_optional(j,o,"id"),name_field=btp_json_optional(j,o,"name");
            if ((id_field && !btp_json_string(j,id_field,id,sizeof id)) || (name_field && !btp_json_string(j,name_field,name,sizeof name)) ||
                !pair(j,btp_json_field(j,o,"at"),63,&xx,&yy) || !rows(j,btp_json_field(j,o,"rows"),s,m,out,xx,yy,1) || !btp_json_done(j,o)) return 0;
        }
        unsigned doors=btp_json_field(j,n,"entrances"),count=0;if (!btp_json_type(j,doors,'[')) return 0;
        memset(out->entrance_x,0,sizeof out->entrance_x);memset(out->entrance_y,0,sizeof out->entrance_y);
        for (unsigned d=j->nodes[doors].first;d;d=j->nodes[d].next) {
            unsigned k,dx,dy,room,active,px,py;char id[64];
            if (!num(j,d,"slot",0,15,&k) || (count&(1u<<k)) || !text(j,d,"id",id,sizeof id) ||
                !label(j,d,out->places[k]) || !pair(j,btp_json_field(j,d,"half"),127,&dx,&dy) ||
                !num(j,d,"active",0,1,&active) || !pair(j,btp_json_field(j,d,"packed"),65535,&px,&py) ||
                (active && (dx>=2*w || dy>=2*h)) || !num(j,d,"room",0,255,&room) || !btp_json_done(j,d)) return btp_json_error(j,d,"invalid entrance slot/position/name (16 characters)");
            if (room>=26 && room!=255) return btp_json_error(j,d,"room must reference a native building 0..25 or 255");
            if (!btp_content_id(id,1)) return btp_json_error(j,d,"entrance needs a stable namespaced ID");
            for (unsigned i=0;i<id_count;++i) if (!strcmp(identities[i],id)) return btp_json_error(j,d,"duplicate native actor/entrance ID");
            identities[id_count++]=j->nodes[btp_json_field(j,d,"id")].text;
            if (slot<=10 && k<8 && !active) return btp_json_error(j,d,"native town walkers require active door slots 0..7");
            if (active && btp_map_tile(out,(int)(dx+1)/2,(int)dy/2)>=85) return btp_json_error(j,d,"entrance must be on accessible ground in front of the building");
            if (!active && (px || py)) return btp_json_error(j,d,"disabled entrance must have zero packed coordinates");
            count|=1u<<k;out->entrance_x[k]=(uint16_t)(active ? (x/64)*256+dx : 0);out->entrance_y[k]=(uint16_t)(active ? (y/64)*4096+dy : 0);
            out->room_map[k]=(uint8_t)room;
        }
        if (count!=65535u) return btp_json_error(j,doors,"all 16 native entrance slots are required");
        unsigned npcs=btp_json_field(j,n,"npcs"),actors=0;if (!btp_json_type(j,npcs,'[')) return 0;
        memset(out->npc_names,0,sizeof out->npc_names);
        for (unsigned d=j->nodes[npcs].first;d;d=j->nodes[d].next) {
            unsigned k,route;char id[64];
            if (!num(j,d,"slot",0,7,&k) || (actors&(1u<<k)) || !text(j,d,"id",id,sizeof id) ||
                !label(j,d,out->npc_names[k]) || !num(j,d,"route",0,7,&route) || !btp_json_done(j,d)) return btp_json_error(j,d,"invalid NPC route/name");
            actors|=1u<<k;out->npc_routes[k]=(uint8_t)route;
            if (!btp_content_id(id,1)) return btp_json_error(j,d,"NPC route needs a stable namespaced ID");
            for (unsigned i=0;i<id_count;++i) if (!strcmp(identities[i],id)) return btp_json_error(j,d,"duplicate native actor/entrance ID");
            identities[id_count++]=j->nodes[btp_json_field(j,d,"id")].text;
        }
        if (actors!=255u) return btp_json_error(j,npcs,"all eight native NPC route slots are required");
        if (!btp_json_done(j,n)) return 0;
    }
    if (seen!=65534u) return btp_json_error(j,a,"all 15 native map slots are required");
    /* MAP11 changes art/state, never the physical Citadel's origin. */
    if ((r->destroyed.entrance_x[0]>>8)!=(r->map.entrance_x[0]>>8) ||
        (r->destroyed.entrance_y[0]>>12)!=(r->map.entrance_y[0]>>12)) return btp_json_error(j,a,"ruined Citadel must share Citadel origin");
    return 1;
}
static int level(BtpJson *j,unsigned n,unsigned *out)
{
    return (num(j,n,"level",0,112,out) && !(*out%16)) ||
        btp_json_error(j,n,"terrain level must be 0, 16, ..., 112");
}
static unsigned piece_tile(const BtpWorldData *w,const uint16_t cells[64],unsigned height,unsigned flip,unsigned x,unsigned y)
{
    /* Same selector transform as generate.c, without selecting a different
       join piece: a placed jigsaw explicitly chooses that piece. Absolute
       pieces were encoded as full handles and bypass selector arithmetic. */
    if (height==16) return cells[8*y+x];
    if (flip&2) x=7-x;
    if (flip&1) y=7-y;
    unsigned tile=cells[8*y+x],base=height ? height-16 : 0;
    if (base>48) base=48;
    if (tile<64) {
        if (flip&1) tile=w->flips[32+tile];
        if (flip&2) tile=w->flips[tile];
        tile=(tile&15u)+base;
    }
    return tile;
}
static int world_edits(BtpJson *j,unsigned n,BtpChiSpatial *s,BtpWorldData *w,
    const char (*ids)[64],const uint16_t (*cells)[64],unsigned count)
{
    unsigned field=btp_json_optional(j,n,"terrain");
    uint8_t *seen=calloc(1024u*1024u,1);if (!seen) return btp_json_error(j,n,"allocation failed");
    int ok=0;
    if (field) {
        if (!btp_json_type(j,field,'[')) goto done;
        for (unsigned p=j->nodes[field].first;p;p=j->nodes[p].next) {
            unsigned x,y,height;
            if (!pair(j,btp_json_field(j,p,"at"),127,&x,&y) || !level(j,p,&height) || !btp_json_done(j,p)) goto done;
            if (seen[y*128+x]++) { btp_json_error(j,p,"duplicate terrain block");goto done; }
            w->heights[(y+8)*144+x+8]=(uint8_t)height;
        }
    }
    memset(seen,0,128u*128u);field=btp_json_optional(j,n,"placements");
    if (field) {
        if (!btp_json_type(j,field,'[')) goto done;
        for (unsigned p=j->nodes[field].first;p;p=j->nodes[p].next) {
            unsigned x,y,height,flip=0;char identity[64];
            if (!pair(j,btp_json_field(j,p,"at"),127,&x,&y) || !level(j,p,&height) ||
                !text(j,p,"jigsaw",identity,sizeof identity)) goto done;
            unsigned f=btp_json_optional(j,p,"flip");if ((f && !btp_json_uint(j,f,0,3,&flip)) || !btp_json_done(j,p)) goto done;
            if (seen[y*128+x]++) { btp_json_error(j,p,"duplicate jigsaw placement");goto done; }
            unsigned piece=0;while (piece<count && strcmp(ids[piece],identity)) ++piece;
            if (piece==count) { btp_json_error(j,p,"unresolved placed jigsaw");goto done; }
            w->heights[(y+8)*144+x+8]=(uint8_t)height;
            for (unsigned yy=0;yy<8;++yy) for (unsigned xx=0;xx<8;++xx) {
                unsigned tile=piece_tile(w,cells[piece],height,flip,xx,yy);
                unsigned index=tile<250 ? s->land[tile] : tile-256;
                s->world_cells[(y*8+yy)*1024+x*8+xx]=(uint16_t)(index+1);
            }
        }
    }
    memset(seen,0,1024u*1024u);field=btp_json_optional(j,n,"patches");
    if (field) {
        unsigned patches=0;if (!btp_json_type(j,field,'[')) goto done;
        for (unsigned p=j->nodes[field].first;p;p=j->nodes[p].next) {
            unsigned x,y,tile;
            if (++patches>32768) { btp_json_error(j,p,"at most 32768 literal world tile patches");goto done; }
            if (!pair(j,btp_json_field(j,p,"at"),1023,&x,&y) || !ref(j,btp_json_field(j,p,"tile"),s,&tile) || !btp_json_done(j,p)) goto done;
            if (seen[y*1024+x]++) { btp_json_error(j,p,"duplicate world tile patch");goto done; }
            s->world_cells[y*1024+x]=(uint16_t)(tile+1);
        }
    }
    ok=1;
done:free(seen);return ok;
}
static int world(BtpJson *j,BtpChiSpatial *s,BtpResources *r)
{
    unsigned n=btp_json_field(j,1,"world"),v;char id[64],name[64];BtpWorldData *w=&r->world;
    if (!text(j,n,"id",id,sizeof id) || !text(j,n,"name",name,sizeof name) ||
        !num(j,n,"width",1024,1024,&v) || !num(j,n,"height",1024,1024,&v) ||
        !num(j,n,"seed",1,16777215,&v) || !bytes(j,btp_json_field(j,n,"coarse"),w->coarse,336,127) ||
        !bytes(j,btp_json_field(j,n,"flips"),w->flips,96,255) ||
        !bytes(j,btp_json_field(j,n,"mini_colors"),w->mini_colors,256,15)) return 0;
    unsigned seed=v;
    unsigned land=btp_json_field(j,1,"land"),i=0;if (!btp_json_type(j,land,'[')) return 0;
    for (unsigned p=j->nodes[land].first;p;p=j->nodes[p].next,++i) {
        unsigned t;if (i==250 || !ref(j,p,s,&t)) return 0;s->land[i]=(uint16_t)t;
        for (unsigned k=0;k<i;++k) if (s->land[k]==t) return btp_json_error(j,p,"generated land slots require distinct tile IDs; share artwork instead");
    }
    if (i!=250) return btp_json_error(j,land,"250 generated-land bindings required");
    for (unsigned k=0;k<96;++k) if (w->flips[k]>=64) return btp_json_error(j,n,"all 96 flip lookup entries must remain within 0..63");
    unsigned pieces=btp_json_field(j,n,"jigsaws"),count=0;uint16_t (*cells)[64]=calloc(BTP_CHI_PIECES,sizeof *cells);
    char (*ids)[64]=calloc(BTP_CHI_PIECES,sizeof *ids);int ok=0;
    if (!cells || !ids || !btp_json_type(j,pieces,'[')) goto done;
    for (unsigned p=j->nodes[pieces].first;p;p=j->nodes[p].next) {
        char title[96];if (count==BTP_CHI_PIECES || !text(j,p,"id",ids[count],64) || !btp_content_id(ids[count],1) ||
            !text(j,p,"name",title,sizeof title)) goto done;
        for (unsigned k=0;k<count;++k) if (!strcmp(ids[k],ids[count])) { btp_json_error(j,p,"duplicate jigsaw ID");goto done; }
        unsigned mode=btp_json_optional(j,p,"mode");char mode_name[16]="terrain";
        if (mode && (!btp_json_string(j,mode,mode_name,sizeof mode_name) ||
            (strcmp(mode_name,"terrain") && strcmp(mode_name,"absolute")))) { btp_json_error(j,p,"jigsaw mode must be terrain or absolute");goto done; }
        unsigned rows=btp_json_field(j,p,"rows"),y=0;if (!btp_json_type(j,rows,'[')) goto done;
        for (unsigned z=j->nodes[rows].first;z;z=j->nodes[z].next,++y) {
            unsigned x=0;if (y==8 || !btp_json_type(j,z,'[')) goto done;
            for (unsigned c=j->nodes[z].first;c;c=j->nodes[c].next,++x) {
                unsigned t;if (x==8 || !ref(j,c,s,&t)) goto done;
                /* Native low IDs participate in terrain flips/base offsets;
                   custom handles remain whole tile identities. */
                unsigned native=0;while (native<250 && s->land[native]!=t) ++native;
                cells[count][y*8+x]=(uint16_t)(!strcmp(mode_name,"terrain") && native<250 ? native : 256+t);
            }
            if (x!=8) { btp_json_error(j,z,"jigsaw must be 8x8");goto done; }
        }
        if (y!=8 || !btp_json_done(j,p)) { btp_json_error(j,p,"jigsaw must be 8x8");goto done; }++count;
    }
    unsigned bindings=btp_json_field(j,n,"joins"),k=0;if (!btp_json_type(j,bindings,'[')) goto done;
    for (unsigned p=j->nodes[bindings].first;p;p=j->nodes[p].next,++k) {
        char refid[64];if (k==17 || !btp_json_string(j,p,refid,sizeof refid)) goto done;
        unsigned z=0;while (z<count && strcmp(ids[z],refid)) ++z;
        if (z==count) { btp_json_error(j,p,"unresolved terrain join jigsaw");goto done; }
        memcpy(k==16 ? w->special : w->textures+64*k,cells[z],128);
    }
    if (k!=17) { btp_json_error(j,n,"17 terrain join bindings required");goto done; }
    /* Sparse authored levels are applied after deterministic generation.
       They therefore survive seed changes, while untouched blocks still use
       the original generator and town descriptors retain their precedence. */
    ok=btp_world_generate(w,seed) && world_edits(j,n,s,w,(const char (*)[64])ids,(const uint16_t (*)[64])cells,count) && btp_json_done(j,n);
done:free(ids);free(cells);return ok;
}
int btp_chi_spatial_load(const char *root,const char *file,BtpChiSpatial *s,BtpResources *r,BtpDigest *digest,BtpError *e)
{
    char path[4096],format[64];unsigned v;BtpJson j={0};int ok=0;
    if (!btp_project_path(root,file,path,e) || !btp_json_load_large(&j,path,e->text)) goto done;
    btp_digest_add(digest,j.source_digest,32);
    if (!text(&j,1,"format",format,sizeof format) || strcmp(format,"btp-chi-spatial-v1") ||
        !num(&j,1,"schema_version",1,1,&v) || !tiles(&j,s) || !maps(&j,s,r) || !world(&j,s,r)) goto done;
    s->start_x=69;s->start_y=25;unsigned start=btp_json_optional(&j,1,"start");
    if (start) {
        unsigned x,y;char id[64];
        if (!text(&j,start,"map",id,sizeof id) || strcmp(id,s->maps[0].id) || !pair(&j,btp_json_field(&j,start,"half"),127,&x,&y) ||
            btp_map_tile(&r->map,(int)(x+1)/2,(int)y/2)>=85 || !btp_json_done(&j,start)) {
            btp_json_error(&j,start,"native campaign starts on accessible Citadel ground; later starts need C4 story state");goto done;
        }
        s->start_x=(uint8_t)x;s->start_y=(uint8_t)y;
    }
    unsigned services=btp_json_optional(&j,1,"services");
    if (services) {
        unsigned broker=btp_json_field(&j,services,"broker"),x,y,enabled;char id[64],where[64];
        if (!btp_resources_feature(r,BTP_FEATURE_BROKER) || !text(&j,broker,"id",id,sizeof id) || strcmp(id,"chi:broker") ||
            !text(&j,broker,"map",where,sizeof where) || strcmp(where,s->maps[1].id) || !text(&j,broker,"name",s->broker_name,sizeof s->broker_name) ||
            !pair(&j,btp_json_field(&j,broker,"half"),127,&x,&y) || !num(&j,broker,"enabled",0,1,&enabled) ||
            !btp_json_done(&j,broker) || !btp_json_done(&j,services)) {
            btp_json_error(&j,services,"broker service requires Updated and a starport movement coordinate");goto done;
        }
        if (enabled && btp_map_tile(&r->local[1],(int)(x+1)/2,(int)y/2)>=85) { btp_json_error(&j,broker,"broker entrance must be on accessible ground");goto done; }
        s->broker_configured=1;s->broker_enabled=(uint8_t)enabled;s->broker_x=(uint8_t)x;s->broker_y=(uint8_t)y;
    }
    if (!btp_json_done(&j,1)) goto done;
    /* Keep duplicate native lookup slots consistent for old service callers. */
    r->local[10]=r->destroyed;s->loaded=1;ok=1;
done:if (!ok && !e->text[0]) snprintf(e->text,sizeof e->text,"Invalid CHI spatial document");btp_json_close(&j);return ok;
}
const BtpChiTile *btp_chi_map_cell(const BtpResources *r,unsigned id,int x,int y)
{
    if (!r->project || !r->project->chi_spatial || id<1 || id>15) return NULL;
    const BtpChiSpatial *s=r->project->chi_spatial;const BtpChiMap *m=&s->maps[id-1];
    return x>=0 && y>=0 && x<m->width && y<m->height ? &s->tiles[m->cells[y*m->width+x]] : NULL;
}
const BtpChiTile *btp_chi_generated_cell(const BtpResources *r,unsigned tile)
{
    if (!r->project || !r->project->chi_spatial) return NULL;
    const BtpChiSpatial *s=r->project->chi_spatial;
    unsigned at=tile<250 ? s->land[tile] : tile>=256 ? tile-256 : BTP_CHI_TILES;
    return at<s->tile_count ? &s->tiles[at] : NULL;
}
unsigned btp_chi_world_rule(const BtpResources *r,unsigned tile)
{ const BtpChiTile *t=btp_chi_generated_cell(r,tile);return t ? t->rule : tile; }
unsigned btp_chi_world_override(const BtpResources *r,int x,int y)
{
    if (!r->project || !r->project->chi_spatial || x<0 || y<0 || x>=1024 || y>=1024) return 0;
    unsigned cell=r->project->chi_spatial->world_cells[(unsigned)y*1024+(unsigned)x];
    return cell ? 255+cell : 0;
}
void btp_chi_position(const BtpResources *r,unsigned *x,unsigned *y)
{
    if (!r->project || !r->project->chi_spatial) return;
    const BtpChiSpatial *s=r->project->chi_spatial;
    for (unsigned i=0;i<13;++i) if (i!=10) {
        const BtpChiMap *m=&s->maps[i];const BtpMap *n=i ? &r->local[i] : &r->map;
        unsigned ox=2u*m->original_x,oy=2u*m->original_y;
        if (*x>=ox && *y>=oy && *x<ox+2u*m->source_width && *y<oy+2u*m->source_height) {
            *x=*x-ox+(n->entrance_x[0]>>8)*128;*y=*y-oy+(n->entrance_y[0]>>12)*128;return;
        }
    }
}
int btp_chi_map_offset(const BtpResources *r,unsigned id,unsigned axis)
{
    if (!r->project || !r->project->chi_spatial || id<1 || id>13) return 0;
    const BtpChiMap *old=&r->project->chi_spatial->maps[id-1];
    const BtpMap *now=id==1 || id==11 ? &r->map : &r->local[id-1];
    return (int)(axis ? (now->entrance_y[0]>>12)*128u : (now->entrance_x[0]>>8)*128u)-(int)(2u*(axis ? old->original_y : old->original_x));
}

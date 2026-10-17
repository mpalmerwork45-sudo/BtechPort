#include "data/adventure.h"
#include "data/json.h"
#include <string.h>
#include <stdlib.h>

static int string(BtpJson *j,unsigned n,const char *key,char *out,size_t size)
{ return btp_json_string(j,btp_json_field(j,n,key),out,size); }
static int number(BtpJson *j,unsigned n,const char *key,unsigned lo,unsigned hi,unsigned *out)
{ return btp_json_uint(j,btp_json_field(j,n,key),lo,hi,out); }
static int option(BtpJson *j,unsigned n,const char *key,const char *const *names,unsigned count,unsigned *out)
{
    char text[64];unsigned field=btp_json_field(j,n,key);
    if (!btp_json_string(j,field,text,sizeof text)) return 0;
    for (unsigned i=0;i<count;++i) if (!strcmp(text,names[i])) { *out=i;return 1; }
    return btp_json_error(j,field,"unsupported option");
}
static int ids(BtpJson *j,const char *key,void *base,size_t stride,unsigned maximum,unsigned *count,unsigned *nodes)
{
    unsigned array=btp_json_field(j,1,key);if (!btp_json_type(j,array,'[')) return 0;
    for (unsigned n=j->nodes[array].first;n;n=j->nodes[n].next) {
        if (*count==maximum) return btp_json_error(j,n,"too many definitions");
        char *id=(char *)base+stride * *count;
        if (!string(j,n,"id",id,64)) return 0;
        if (!btp_content_id(id,1)) return btp_json_error(j,n,"expected namespaced stable ID");
        for (unsigned i=0;i<*count;++i) if (!strcmp((char *)base+stride*i,id)) return btp_json_error(j,n,"duplicate ID");
        nodes[(*count)++]=n;
    }
    return 1;
}
static int reference(BtpJson *j,unsigned field,const void *base,size_t stride,unsigned count,unsigned *out)
{
    char id[64];if (!btp_json_string(j,field,id,sizeof id)) return 0;
    for (unsigned i=0;i<count;++i) if (!strcmp((const char *)base+stride*i,id)) { *out=i;return 1; }
    return btp_json_error(j,field,"unresolved ID");
}
#define REF(j,n,key,base,count,out) reference(j,btp_json_field(j,n,key),base,sizeof *(base),count,out)
static int next(BtpJson *j,unsigned n,const char *key,const BtpAdventure *a,uint16_t *out)
{ unsigned v;if (!REF(j,n,key,a->nodes,a->node_count,&v)) return 0;*out=(uint16_t)v;return 1; }
static int pair(BtpJson *j,unsigned node,unsigned max,unsigned *x,unsigned *y)
{
    if (!btp_json_type(j,node,'[')) return 0;
    unsigned a=j->nodes[node].first,b=a ? j->nodes[a].next : 0;
    if (!a || !b || j->nodes[b].next) return btp_json_error(j,node,"expected [x, y]");
    return btp_json_uint(j,a,0,max,x) && btp_json_uint(j,b,0,max,y);
}
static int rows(BtpJson *j,unsigned field,BtpAdventure *a,BtpScene *m,unsigned ox,unsigned oy,int overlay)
{
    if (!btp_json_type(j,field,'[')) return 0;
    unsigned width=0,height=0;
    for (unsigned n=j->nodes[field].first;n;n=j->nodes[n].next) {
        char row[65];if (!btp_json_string(j,n,row,sizeof row)) return 0;
        unsigned len=(unsigned)strlen(row);
        if (!len || (height && len!=width) || oy+height>=64 || ox+len>64 ||
            (overlay && (oy+height>=m->visual.height || ox+len>m->visual.width))) return btp_json_error(j,n,"rows must form a rectangle inside the map (maximum 64 x 64)");
        width=len;
        for (unsigned x=0;x<len;++x) {
            if (overlay && row[x]==' ') continue;
            unsigned t=0;while (t<a->tile_count && a->tiles[t].key!=(unsigned char)row[x]) ++t;
            if (t==a->tile_count) return btp_json_error(j,n,"row contains an undefined tile key");
            m->cells[(oy+height)*64+ox+x]=(uint8_t)t;
        }
        ++height;
    }
    if (!height || (!overlay && (height<16 || width<16))) return btp_json_error(j,field,"map must be 16..64 tiles in each dimension");
    if (!overlay) { m->visual.width=(uint8_t)width;m->visual.height=(uint8_t)height; }
    return 1;
}
int btp_scene_stand(const BtpScene *m,int x,int y,int mech)
{
    if (x<0 || y<0 || x>=2*m->rules.width-2 || y>=2*m->rules.height-(mech ? 2 : 0)) return 0;
    unsigned tile=btp_map_tile(&m->rules,mech ? x/2 : (x+1)/2,y/2);
    return tile<85 && (!mech || btp_map_tile(&m->rules,x/2+1,y/2)<85);
}
int btp_adventure_load(const char *path,const BtpDefinitions *d,BtpAdventure *out,char error[256])
{
    BtpAdventure *a=calloc(1,sizeof *a);BtpJson j={0};int ok=0;char text[64];unsigned v;
    unsigned tiles[64],maps[16],people[16],shops[16],battles[16],nodes[256];
    if (!a) return 0;
    if (!btp_json_load(&j,path,error)) goto done;
    if (!string(&j,1,"format",text,sizeof text) || strcmp(text,"btp-adventure-v1") ||
        !number(&j,1,"schema_version",1,1,&v)) { btp_json_error(&j,1,"expected btp-adventure-v1, schema_version 1");goto done; }
    if (!ids(&j,"tiles",a->tiles,sizeof *a->tiles,64,&a->tile_count,tiles) ||
        !ids(&j,"maps",a->maps,sizeof *a->maps,16,&a->map_count,maps) ||
        !ids(&j,"people",a->people,sizeof *a->people,16,&a->person_count,people) ||
        !ids(&j,"shops",a->shops,sizeof *a->shops,16,&a->shop_count,shops) ||
        !ids(&j,"encounters",a->battles,sizeof *a->battles,16,&a->battle_count,battles) ||
        !ids(&j,"events",a->nodes,sizeof *a->nodes,256,&a->node_count,nodes)) goto done;
    if (!a->tile_count || !a->map_count || !a->person_count || !a->node_count) { btp_json_error(&j,1,"tiles, maps, people and events cannot be empty");goto done; }
    unsigned flags=btp_json_field(&j,1,"flags");if (!btp_json_type(&j,flags,'[')) goto done;
    for (unsigned n=j.nodes[flags].first;n;n=j.nodes[n].next) {
        if (a->flag_count==64) { btp_json_error(&j,n,"too many flags");goto done; }
        char *id=a->flags[a->flag_count];if (!btp_json_string(&j,n,id,64)) goto done;
        if (!btp_content_id(id,1)) { btp_json_error(&j,n,"expected namespaced flag ID");goto done; }
        for (unsigned k=0;k<a->flag_count;++k) if (!strcmp(id,a->flags[k])) { btp_json_error(&j,n,"duplicate flag ID");goto done; }
        ++a->flag_count;
    }
    for (unsigned i=0;i<a->tile_count;++i) {
        unsigned n=tiles[i];BtpSceneTile *t=&a->tiles[i];char key[2];
        const char *const sheets[]={"chi:land","chi:destroyed","package:tiles"},*const terrain[]={"clear","rough","water","woods","wall"};
        if (!string(&j,n,"key",key,sizeof key) || key[0]==' ' || !number(&j,n,"graphic",0,249,&v)) goto done;
        t->key=(uint8_t)key[0];t->graphic=(uint8_t)v;
        for (unsigned k=0;k<i;++k) if (a->tiles[k].key==t->key) { btp_json_error(&j,n,"duplicate tile key");goto done; }
        if (!option(&j,n,"sheet",sheets,3,&v)) goto done;
        t->sheet=(uint8_t)v;
        if (!option(&j,n,"terrain",terrain,5,&v)) goto done;
        t->terrain=(uint8_t)v;
        if (!number(&j,n,"mini_color",0,15,&v) || !btp_json_done(&j,n)) goto done;
        t->color=(uint8_t)v;
    }
    for (unsigned i=0;i<a->map_count;++i) {
        unsigned n=maps[i];BtpScene *m=&a->maps[i];
        if (!string(&j,n,"name",m->name,sizeof m->name) || !pair(&j,btp_json_field(&j,n,"origin"),960,&m->origin_x,&m->origin_y) ||
            !rows(&j,btp_json_field(&j,n,"rows"),a,m,0,0,0)) goto done;
        unsigned overlays=btp_json_field(&j,n,"overlays");if (!btp_json_type(&j,overlays,'[')) goto done;
        unsigned count=0;
        for (unsigned o=j.nodes[overlays].first;o;o=j.nodes[o].next) {
            unsigned x,y;if (++count>32) { btp_json_error(&j,o,"at most 32 overlays per map");goto done; }
            if (!pair(&j,btp_json_field(&j,o,"at"),63,&x,&y) || !rows(&j,btp_json_field(&j,o,"rows"),a,m,x,y,1) || !btp_json_done(&j,o)) goto done;
        }
        m->rules.width=m->visual.width;m->rules.height=m->visual.height;m->rules.authored=1;
        const unsigned rule[]={0,31,15,47,85};
        for (unsigned y=0;y<m->visual.height;++y) for (unsigned x=0;x<m->visual.width;++x) {
            BtpSceneTile *t=&a->tiles[m->cells[y*64+x]];unsigned at=y*m->visual.width+x;
            m->visual.tiles[at]=t->graphic;m->rules.tiles[at]=(uint8_t)rule[t->terrain];
        }
        for (unsigned k=0;k<i;++k) {
            const BtpScene *b=&a->maps[k];
            if (m->origin_x<b->origin_x+b->visual.width && b->origin_x<m->origin_x+m->visual.width &&
                m->origin_y<b->origin_y+b->visual.height && b->origin_y<m->origin_y+m->visual.height) { btp_json_error(&j,n,"world map extents overlap; use local overlays instead");goto done; }
        }
        unsigned doors=btp_json_field(&j,n,"entrances");if (!btp_json_type(&j,doors,'[')) goto done;
        for (unsigned door=j.nodes[doors].first;door;door=j.nodes[door].next) {
            if (m->entrance_count==16) { btp_json_error(&j,door,"at most 16 entrances per map");goto done; }
            BtpSceneEntrance *e=&m->entrances[m->entrance_count++];unsigned x,y;
            e->person=255;
            if (!string(&j,door,"id",e->id,64) || !btp_content_id(e->id,1) || !string(&j,door,"name",e->name,sizeof e->name) ||
                !pair(&j,btp_json_field(&j,door,"at"),127,&x,&y) || !next(&j,door,"event",a,&e->event)) goto done;
            unsigned person=btp_json_optional(&j,door,"person");
            if (person) { if (!reference(&j,person,a->people,sizeof *a->people,a->person_count,&v)) goto done;e->person=(uint8_t)v; }
            if (!btp_json_done(&j,door)) goto done;
            e->x=(uint8_t)x;e->y=(uint8_t)y;
            if (!btp_scene_stand(m,(int)x,(int)y,0)) { btp_json_error(&j,door,"entrance must be on accessible ground in front of the building");goto done; }
            for (unsigned k=0;k+1<m->entrance_count;++k) if (!strcmp(e->id,m->entrances[k].id) || (e->x==m->entrances[k].x && e->y==m->entrances[k].y)) { btp_json_error(&j,door,"duplicate entrance ID/position");goto done; }
        }
        if (!btp_json_done(&j,n)) goto done;
    }
    for (unsigned i=0;i<a->person_count;++i) {
        unsigned n=people[i];uint8_t *p=a->people[i].record;
        const char *const names[]={"chi:jason","chi:rex","chi:edward","chi:russ","chi:rick","chi:zeke","chi:possum","chi:marco","chi:rusty","chi:hunter"};
        unsigned identity=btp_json_field(&j,n,"identity");
        if (!btp_json_string(&j,identity,text,sizeof text)) goto done;
        for (v=0;v<10 && strcmp(text,names[v]);++v) {}
        if (v==10) {
            if (strlen(text)!=7 || strncmp(text,"actor:",6) || text[6]<'0' || text[6]>'9') { btp_json_error(&j,identity,"unsupported actor identity");goto done; }
            v=(unsigned)(text[6]-'0');
        }
        unsigned name=btp_json_optional(&j,n,"name");
        if (name && !btp_json_string(&j,name,a->people[i].name,sizeof a->people[i].name)) goto done;
        p[0]=(uint8_t)v;
        const char *const keys[]={"attributes","skills"};
        for (unsigned k=0;k<2;++k) {
            unsigned array=btp_json_field(&j,n,keys[k]),count=0;
            if (!btp_json_type(&j,array,'[')) goto done;
            for (unsigned z=j.nodes[array].first;z;z=j.nodes[z].next) {
                if (count==(k ? 7u : 3u) || !btp_json_uint(&j,z,k ? 0u : 2u,k ? 4u : 12u,&v)) { btp_json_error(&j,z,"invalid attributes/skills array");goto done; }
                p[(k ? 4u : 1u)+count++]=(uint8_t)v;
            }
            if (count!=(k ? 7u : 3u)) { btp_json_error(&j,array,"wrong attributes/skills count");goto done; }
        }
        if (!number(&j,n,"weapon",0,13,&v)) goto done;
        p[11]=(uint8_t)v;
        if (!number(&j,n,"armor",0,5,&v) || !btp_json_done(&j,n)) goto done;
        static const uint8_t armor[]={0,25,40,30,50,50};p[12]=8;p[13]=(uint8_t)v;p[14]=armor[v];p[15]=(uint8_t)(10*p[1]);
    }
    for (unsigned i=0;i<a->shop_count;++i) {
        unsigned n=shops[i],array=btp_json_field(&j,n,"stock");BtpSceneShop *s=&a->shops[i];
        if (!btp_json_type(&j,array,'[')) goto done;
        for (unsigned z=j.nodes[array].first;z;z=j.nodes[z].next) {
            if (s->count==256 || !reference(&j,z,d->mechs,sizeof *d->mechs,d->mech_count,&v)) goto done;
            for (unsigned k=0;k<s->count;++k) if (s->stock[k]==v) { btp_json_error(&j,z,"duplicate stock ID");goto done; }
            s->stock[s->count++]=(uint16_t)v;
        }
        if (!s->count || !btp_json_done(&j,n)) { btp_json_error(&j,n,"shop stock cannot be empty");goto done; }
    }
    for (unsigned i=0;i<a->battle_count;++i) {
        unsigned n=battles[i];BtpSceneBattle *b=&a->battles[i];
        if (!REF(&j,n,"map",a->maps,a->map_count,&b->map) || !pair(&j,btp_json_field(&j,n,"party_at"),127,&b->x,&b->y)) goto done;
        BtpScene *m=&a->maps[b->map];
        if (!btp_scene_stand(m,(int)b->x,(int)b->y,0) || !btp_scene_stand(m,(int)b->x,(int)b->y-2,1)) { btp_json_error(&j,n,"party spawn is blocked");goto done; }
        unsigned array=btp_json_field(&j,n,"enemies"),mechs=0,infantry=0;
        if (!btp_json_type(&j,array,'[')) goto done;
        for (unsigned z=j.nodes[array].first;z;z=j.nodes[z].next) {
            if (b->count==12) { btp_json_error(&j,z,"at most 12 enemies");goto done; }
            BtpSceneEnemy *e=&b->enemies[b->count++];const char *const types[]={"mech","person"};unsigned x,y;
            if (!option(&j,z,"kind",types,2,&v)) goto done;
        e->infantry=(uint8_t)v;
            if (!reference(&j,btp_json_field(&j,z,"definition"),v ? (const void *)a->people : (const void *)d->mechs,
                v ? sizeof *a->people : sizeof *d->mechs,v ? a->person_count : d->mech_count,&v) ||
                !pair(&j,btp_json_field(&j,z,"at"),127,&x,&y) || !btp_json_done(&j,z)) goto done;
            e->definition=(uint16_t)v;e->x=(uint8_t)x;e->y=(uint8_t)y;
            if (!btp_scene_stand(m,(int)x,(int)y,!e->infantry) || (e->infantry ? ++infantry>8 : ++mechs>4)) { btp_json_error(&j,z,"enemy spawn blocked or exceeds 4 mechs / 8 infantry");goto done; }
            for (unsigned k=0;k+1<b->count;++k) if (abs((int)x-b->enemies[k].x)<3 && abs((int)y-b->enemies[k].y)<3) { btp_json_error(&j,z,"enemy spawns overlap");goto done; }
        }
        if (!b->count || !btp_json_done(&j,n)) { btp_json_error(&j,n,"encounter needs enemies");goto done; }
    }
    for (unsigned i=0;i<a->node_count;++i) {
        unsigned n=nodes[i];BtpEventNode *e=&a->nodes[i];
        const char *const ops[]={"end","say","choice","if","flag","reward","recruit","transfer","shop","battle","lua","finish"};
        if (!option(&j,n,"op",ops,12,&e->op)) goto done;
        unsigned portrait=btp_json_optional(&j,n,"portrait");
        if (portrait) {
            const char *const art[]={"none","broker","training","lounge","prison","inventor","cinema","hospital","comstar","clothes","video-hut","mayor"};
            if (!option(&j,n,"portrait",art,12,&e->portrait)) goto done;
        }
        if (e->op==BTP_EVENT_SAY || e->op==BTP_EVENT_FINISH || e->op==BTP_EVENT_CHOICE) if (!string(&j,n,"text",e->text,e->op==BTP_EVENT_CHOICE ? 241 : sizeof e->text)) goto done;
        if (e->op==BTP_EVENT_CHOICE) {
            unsigned options=btp_json_field(&j,n,"options");if (!btp_json_type(&j,options,'[')) goto done;
            for (unsigned z=j.nodes[options].first;z;z=j.nodes[z].next) {
                if (e->count==5) { btp_json_error(&j,z,"at most five choices plus cancel");goto done; }
                if (!string(&j,z,"label",e->labels[e->count],25) || !next(&j,z,"next",a,&e->next[e->count]) || !btp_json_done(&j,z)) goto done;
                ++e->count;
            }
            if (!e->count || !next(&j,n,"cancel",a,&e->next[5])) goto done;
        } else if (e->op!=BTP_EVENT_END && e->op!=BTP_EVENT_FINISH && e->op!=BTP_EVENT_LUA && e->op!=BTP_EVENT_IF && e->op!=BTP_EVENT_BATTLE) {
            if (!next(&j,n,"next",a,&e->next[0])) goto done;
        }
        switch (e->op) {
        case BTP_EVENT_LUA: {
            /* Resolve the package script after all manifest inputs load. */
            if (!string(&j,n,"script",e->text,64) || !btp_content_id(e->text,1) || !next(&j,n,"failure",a,&e->next[5])) goto done;
            unsigned routes=btp_json_field(&j,n,"routes");if (!btp_json_type(&j,routes,'[')) goto done;
            for (unsigned z=j.nodes[routes].first;z;z=j.nodes[z].next) {
                if (e->count==5) { btp_json_error(&j,z,"at most five Lua routes");goto done; }
                if (!reference(&j,z,a->nodes,sizeof *a->nodes,a->node_count,&v)) goto done;
                e->next[e->count++]=(uint16_t)v;
            }
            if (!e->count) { btp_json_error(&j,routes,"Lua needs declared command routes");goto done; }break;
        }
        case BTP_EVENT_IF:case BTP_EVENT_FLAG:
            if (!REF(&j,n,"flag",a->flags,a->flag_count,&e->argument) || !number(&j,n,"value",0,1,&e->value)) goto done;
            if (e->op==BTP_EVENT_IF && (!next(&j,n,"then",a,&e->next[0]) || !next(&j,n,"else",a,&e->next[1]))) goto done;
            break;
        case BTP_EVENT_REWARD:
            if (!number(&j,n,"credits",1,999999,&e->value) || !next(&j,n,"failure",a,&e->next[1])) goto done;
            break;
        case BTP_EVENT_RECRUIT:
            if (!REF(&j,n,"person",a->people,a->person_count,&e->argument) || !next(&j,n,"failure",a,&e->next[1])) goto done;
            break;
        case BTP_EVENT_TRANSFER:
            if (!REF(&j,n,"map",a->maps,a->map_count,&e->argument) || !pair(&j,btp_json_field(&j,n,"at"),127,&e->x,&e->y) || !next(&j,n,"failure",a,&e->next[1])) goto done;
            if (!btp_scene_stand(&a->maps[e->argument],(int)e->x,(int)e->y,0)) { btp_json_error(&j,n,"transfer destination is blocked");goto done; }break;
        case BTP_EVENT_SHOP:if (!REF(&j,n,"shop",a->shops,a->shop_count,&e->argument)) goto done;
            break;
        case BTP_EVENT_BATTLE:
            if (!REF(&j,n,"encounter",a->battles,a->battle_count,&e->argument) || !next(&j,n,"win",a,&e->next[0]) ||
                !next(&j,n,"loss",a,&e->next[1]) || !next(&j,n,"flee",a,&e->next[2]) || !next(&j,n,"failure",a,&e->next[3])) goto done;
            break;
        default:break;
        }
        if (e->op==BTP_EVENT_SAY || e->op==BTP_EVENT_FINISH || e->op==BTP_EVENT_CHOICE) {
            char lines[96][28];unsigned count=btp_event_lines(e->text,lines);
            if (!count || (e->op==BTP_EVENT_CHOICE && count+e->count>21)) { btp_json_error(&j,n,"text/choices exceed the event panel; split into a say node first");goto done; }
        }
        if (!btp_json_done(&j,n)) goto done;
    }
    unsigned start=btp_json_field(&j,1,"start");
    if (!REF(&j,start,"map",a->maps,a->map_count,&a->start_map) || !pair(&j,btp_json_field(&j,start,"at"),127,&a->start_x,&a->start_y) ||
        !REF(&j,start,"event",a->nodes,a->node_count,&a->start_event) || !number(&j,start,"credits",0,999999,&a->credits)) goto done;
    unsigned party=btp_json_field(&j,start,"party"),mech_count=0;
    if (!btp_json_type(&j,party,'[')) goto done;
    for (unsigned n=j.nodes[party].first;n;n=j.nodes[n].next) {
        unsigned person,mech;
        if (a->party_count==8 || !REF(&j,n,"person",a->people,a->person_count,&person) || !string(&j,n,"mech",text,sizeof text)) goto done;
        if (!strcmp(text,"none")) mech=256;
        else if (!REF(&j,n,"mech",d->mechs,d->mech_count,&mech)) goto done;
        for (unsigned k=0;k<a->party_count;++k) if (a->people[a->party[k]].record[0]==a->people[person].record[0]) { btp_json_error(&j,n,"duplicate party identity");goto done; }
        if ((!a->party_count && a->people[person].record[0]) || (mech<256 && (++mech_count>4 || !a->people[person].record[8]))) { btp_json_error(&j,n,"CHI party needs Jason first, at most four mechs and trained pilots");goto done; }
        a->party[a->party_count]=(uint8_t)person;a->mechs[a->party_count++]=(uint16_t)mech;
        if (!btp_json_done(&j,n)) goto done;
    }
    if (!a->party_count || !btp_scene_stand(&a->maps[a->start_map],(int)a->start_x,(int)a->start_y,0)) { btp_json_error(&j,start,"party/start position invalid");goto done; }
    if (!btp_json_done(&j,start) || !btp_json_done(&j,1)) goto done;
    a->loaded=1;memcpy(a->source_digest,j.source_digest,32);*out=*a;ok=1;
done:
    if (!ok && error && !*error) btp_json_error(&j,1,"invalid or excessive adventure definition");
    btp_json_close(&j);free(a);return ok;
}
unsigned btp_event_lines(const char *input,char lines[96][28])
{
    unsigned count=0;
    while (*input && count<96) {
        while (*input==' ') ++input;
        if (!*input) break;
        size_t n=strlen(input);
        if (n>25) { n=25;while (n && input[n]!=' ') --n;if (!n) n=25; }
        memcpy(lines[count],input,n);lines[count++][n]=0;input+=n;
    }
    return count;
}

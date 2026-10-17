#include "data/definitions.h"
#include "data/json.h"
#include "data/unit_data.h"
#include "data/file.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *const bodies[]={"left_arm","left_torso","left_leg","head","center_torso","right_arm","right_torso","right_leg","left_rear","center_rear","right_rear"};
static const char *const behaviors[]={"small_laser","medium_laser","large_laser","ppc","ac2","ac5","ac10","ac20","machine_gun","flamer","lrm5","lrm10","lrm15","lrm20","srm2","srm4","srm6"};
static const unsigned starts[]={51,58,79,85,83,65,72,81},slots[]={7,7,2,1,2,7,7,2};
const char *btp_behavior_name(unsigned i) { return i<17 ? behaviors[i] : ""; }
const char *btp_body_name(unsigned i) { return i<11 ? bodies[i] : ""; }
static int str(BtpJson *j,unsigned obj,const char *key,char *out,size_t cap) { return btp_json_string(j,btp_json_field(j,obj,key),out,cap); }
static int num(BtpJson *j,unsigned obj,const char *key,unsigned lo,unsigned hi,unsigned *out) { return btp_json_uint(j,btp_json_field(j,obj,key),lo,hi,out); }
static int fixed(BtpJson *j,unsigned obj,const char *key,const char *expected)
{
    unsigned n=btp_json_field(j,obj,key);char text[96];
    return btp_json_string(j,n,text,sizeof text) && (!strcmp(text,expected) || btp_json_error(j,n,"unsupported format/behavior"));
}
static int id(BtpJson *j,unsigned obj,char *out,size_t size,int ns)
{
    unsigned n=btp_json_field(j,obj,"id");
    return btp_json_string(j,n,out,size) && (btp_content_id(out,ns) || btp_json_error(j,n,"invalid stable ID"));
}
static int reference(BtpJson *j,unsigned node,const char *value,const void *table,unsigned count,size_t stride,unsigned *index)
{
    for (unsigned i=0;i<count;++i) if (!strcmp(value,(const char *)table+i*stride)) { *index=i;return 1; }
    return btp_json_error(j,node,"unresolved definition ID");
}
static int unique(BtpJson *j,unsigned node,const void *table,unsigned count,size_t stride)
{
    const char *last=(const char *)table+(count-1u)*stride;
    for (unsigned i=0;i+1<count;++i) if (!strcmp(last,(const char *)table+i*stride)) return btp_json_error(j,node,"duplicate definition ID");
    return 1;
}
static unsigned array(BtpJson *j,unsigned obj,const char *key)
{
    unsigned n=btp_json_field(j,obj,key);return btp_json_type(j,n,'[') ? n : 0;
}
static int body(BtpJson *j,unsigned obj,const char *key,unsigned *out,unsigned count,unsigned lo,unsigned hi)
{
    unsigned n=btp_json_field(j,obj,key);
    for (unsigned i=0;i<count;++i) if (!num(j,n,bodies[i],lo,hi,&out[i])) return 0;
    return btp_json_done(j,n);
}
static int rules(BtpJson *j,unsigned n,BtpCombatProfile *p)
{
    char name[64];if (!id(j,n,name,sizeof name,1)) return 0;
    if (!strcmp(name,"chi:legacy-v1")) return btp_json_done(j,n);
    if (strcmp(name,"chi:updated-lrm-v1")) return btp_json_error(j,n,"unsupported rule profile");
    const char *const keys[]={"distance_scale","minimum_range","short_range","medium_range","long_range"};
    uint8_t *out[]={&p->scale,&p->minimum,&p->short_range,&p->medium_range,&p->long_range};
    for (unsigned i=0;i<5;++i) { unsigned v;if (!num(j,n,keys[i],1,63,&v)) return 0;*out[i]=(uint8_t)v; }
    if (p->scale>6 || p->minimum>12 || p->minimum>=p->short_range || p->short_range>=p->medium_range ||
        p->medium_range>=p->long_range || p->scale*(p->long_range+1u)>255) return btp_json_error(j,n,"inconsistent LRM ranges");
    /* Same policy identity as released Updated saves. Project compatibility
       additionally binds the complete definitions through its own envelope. */
    uint32_t h=UINT32_C(2166136261);
    for (const char *s="chi-updated-lrm-v1/weapon-aware-v1";*s;++s) h=(h^(unsigned char)*s)*UINT32_C(16777619);
    for (unsigned i=0;i<5;++i) h=(h^*out[i])*UINT32_C(16777619);
    p->fingerprint=h ? h : 1;return btp_json_done(j,n);
}
static int parse(BtpJson *j,BtpDefinitions *d)
{
    unsigned version;
    if (!fixed(j,1,"format","btp-content-v1") || !num(j,1,"schema_version",1,1,&version) ||
        !str(j,1,"package_id",d->id,sizeof d->id) || !btp_content_id(d->id,0) ||
        !str(j,1,"content_version",d->version,sizeof d->version) || !rules(j,btp_json_field(j,1,"rules"),&d->rules)) return 0;
    unsigned services=btp_json_field(j,1,"services"),broker=btp_json_field(j,services,"broker"),reload=btp_json_field(j,services,"reload");
    if (!id(j,broker,d->broker,sizeof d->broker,1) || !fixed(j,broker,"behavior","chi-broker-v1") || !btp_json_done(j,broker) ||
        !id(j,reload,d->reload,sizeof d->reload,1) || !fixed(j,reload,"behavior","chi-reload-v1") || !btp_json_done(j,reload) || !btp_json_done(j,services)) return 0;
    unsigned a=array(j,1,"ammunition");if (!a) return 0;
    for (unsigned n=j->nodes[a].first;n;n=j->nodes[n].next) {
        if (d->ammo_count==BTP_DEFINITION_LIMIT) return btp_json_error(j,n,"at most 256 ammunition definitions");
        BtpAmmoDefinition *v=&d->ammo[d->ammo_count++];
        if (!id(j,n,v->id,sizeof v->id,1) || !num(j,n,"price_per_shot",1,254,&v->price) || !btp_json_done(j,n) ||
            !unique(j,n,d->ammo,d->ammo_count,sizeof *v)) return 0;
    }
    a=array(j,1,"presentations");if (!a) return 0;
    for (unsigned n=j->nodes[a].first;n;n=j->nodes[n].next) {
        if (d->presentation_count==BTP_DEFINITION_LIMIT) return btp_json_error(j,n,"at most 256 presentation definitions");
        BtpPresentationDefinition *v=&d->presentations[d->presentation_count++];char source[64];
        if (!id(j,n,v->id,sizeof v->id,1) || !str(j,n,"source",source,sizeof source) || !btp_json_done(j,n) ||
            !unique(j,n,d->presentations,d->presentation_count,sizeof *v)) return 0;
        if (strcmp(source,"chi:locust") && strcmp(source,"chi:red-stinger") && strcmp(source,"package:walker-a") && strcmp(source,"package:walker-b")) return btp_json_error(j,n,"unsupported sprite source");
        v->sprite=(unsigned)(!strcmp(source,"chi:red-stinger") || !strcmp(source,"package:walker-b"));
        v->independent=(unsigned)!strncmp(source,"package:",8);
    }
    a=array(j,1,"weapons");if (!a) return 0;
    for (unsigned n=j->nodes[a].first;n;n=j->nodes[n].next) {
        if (d->weapon_count==BTP_DEFINITION_LIMIT) return btp_json_error(j,n,"at most 256 weapon definitions");
        BtpAuthoredWeapon *v=&d->weapons[d->weapon_count++];char behavior[64];
        if (!id(j,n,v->id,sizeof v->id,1) || !str(j,n,"name",v->name,sizeof v->name) || !str(j,n,"label",v->label,sizeof v->label) ||
            !str(j,n,"behavior",behavior,sizeof behavior) || !str(j,n,"ammunition",v->ammunition,sizeof v->ammunition) ||
            !num(j,n,"damage",1,20,&v->damage) || !num(j,n,"projectiles",1,20,&v->projectiles) || !num(j,n,"heat",0,15,&v->heat)) return 0;
        for (v->behavior=0;v->behavior<17 && strcmp(behavior,behaviors[v->behavior]);++v->behavior) {}
        if (v->behavior==17) return btp_json_error(j,n,"unsupported weapon behavior/equipment");
        const unsigned projectiles[]={1,1,1,1,1,1,1,1,1,1,5,10,15,20,2,4,6};
        if (v->projectiles!=projectiles[v->behavior]) return btp_json_error(j,n,"projectile count must match supported behavior");
        if (v->damage*v->projectiles>255) return btp_json_error(j,n,"maximum volley damage exceeds current combat capacity");
        int consumes=(v->behavior>=4 && v->behavior<=8) || v->behavior>=10;
        unsigned ammo;
        if (consumes ? !reference(j,n,v->ammunition,d->ammo,d->ammo_count,sizeof d->ammo[0],&ammo) : strcmp(v->ammunition,"none"))
            return btp_json_error(j,n,"ammunition does not match weapon behavior");
        unsigned ranges=btp_json_field(j,n,"ranges");
        if (!num(j,ranges,"short",1,255,&v->near_range) || !num(j,ranges,"medium",1,255,&v->medium_range) ||
            !num(j,ranges,"long",1,255,&v->far_range) || !btp_json_done(j,ranges) || !btp_json_done(j,n) ||
            !unique(j,n,d->weapons,d->weapon_count,sizeof *v)) return 0;
        if (v->near_range>v->medium_range || v->medium_range>v->far_range) return btp_json_error(j,ranges,"ranges must be ascending");
    }
    a=array(j,1,"mechs");if (!a) return 0;
    for (unsigned n=j->nodes[a].first;n;n=j->nodes[n].next) {
        if (d->mech_count==BTP_DEFINITION_LIMIT) return btp_json_error(j,n,"at most 256 mech definitions");
        BtpMechDefinition *v=&d->mechs[d->mech_count++];char presentation[64];
        if (!id(j,n,v->id,sizeof v->id,1) || !str(j,n,"name",v->name,sizeof v->name) || !str(j,n,"label",v->label,sizeof v->label) ||
            !str(j,n,"presentation",presentation,sizeof presentation) || !reference(j,n,presentation,d->presentations,d->presentation_count,sizeof d->presentations[0],&v->presentation) ||
            !num(j,n,"mass_tons",20,100,&v->mass) || !num(j,n,"price",1,999999,&v->price) || !num(j,n,"engine_heat_sinks",0,30,&v->sinks)) return 0;
        if (v->label[0]<'A' || v->label[0]>'Z') return btp_json_error(j,n,"short label must start with an uppercase letter");
        unsigned movement=btp_json_field(j,n,"movement");
        if (!num(j,movement,"walk",1,12,&v->walk) || !num(j,movement,"jump",0,12,&v->jump) || !btp_json_done(j,movement) ||
            !body(j,n,"armor",v->armor,11,0,83) || !body(j,n,"structure",v->structure,8,1,40) || !body(j,n,"external_heat_sinks",v->external_sinks,8,0,7)) return 0;
        unsigned act=btp_json_field(j,n,"actuators"),la,ra,ll,rl;
        if (!num(j,act,"left_arm",0,15,&la) || !num(j,act,"right_arm",0,15,&ra) || !num(j,act,"left_leg",0,15,&ll) || !num(j,act,"right_leg",0,15,&rl) || !btp_json_done(j,act)) return 0;
        v->actuators[0]=la*16+ll;v->actuators[1]=ra*16+rl;
        unsigned loadout=array(j,n,"loadout");if (!loadout) return 0;
        for (unsigned m=j->nodes[loadout].first;m;m=j->nodes[m].next) {
            if (v->count==10) return btp_json_error(j,m,"CHI campaign supports at most ten mounted weapons");
            BtpMountDefinition *mount=&v->mounts[v->count++];char weapon[64],location[32];
            if (!str(j,m,"weapon",weapon,sizeof weapon) || !reference(j,m,weapon,d->weapons,d->weapon_count,sizeof d->weapons[0],&mount->weapon) ||
                !str(j,m,"location",location,sizeof location) || !num(j,m,"ammunition",0,254,&mount->ammo) || !btp_json_done(j,m)) return 0;
            for (mount->location=0;mount->location<8 && strcmp(location,bodies[mount->location]);++mount->location) {}
            if (mount->location==8) return btp_json_error(j,m,"unknown body location");
            if (!!mount->ammo == !strcmp(d->weapons[mount->weapon].ammunition,"none")) return btp_json_error(j,m,"ammunition capacity disagrees with weapon");
        }
        if (!v->count || !btp_json_done(j,n) || !unique(j,n,d->mechs,d->mech_count,sizeof *v)) return btp_json_error(j,n,"mech needs a supported loadout");
        unsigned used[8]={0},sinks=v->sinks;
        for (unsigned i=0;i<v->count;++i) ++used[v->mounts[i].location];
        for (unsigned i=0;i<8;++i) {
            sinks+=v->external_sinks[i];
            if (used[i]+v->external_sinks[i]>slots[i]) return btp_json_error(j,n,"loadout/heat sinks exceed body location capacity");
            if (v->armor[i]>2*v->structure[i]+(i==3 ? 3u : 0u)) return btp_json_error(j,n,"armor exceeds structure capacity");
        }
        if (sinks>30 || v->armor[1]+v->armor[8]>2*v->structure[1] || v->armor[4]+v->armor[9]>2*v->structure[4] ||
            v->armor[6]+v->armor[10]>2*v->structure[6]) return btp_json_error(j,n,"heat sink or torso armor capacity exceeded");
    }
    if (!d->mech_count) return btp_json_error(j,a,"project needs at least one mech");
    return btp_json_done(j,1);
}
int btp_definitions_load(const char *path,BtpDefinitions *out,char error[256])
{
    BtpJson j={0};BtpDefinitions *d=calloc(1,sizeof *d);int ok=0;
    if (!d) { snprintf(error,256,"Definitions allocation failed");return 0; }
    if (btp_json_load(&j,path,error)) ok=parse(&j,d);
    if (!ok && !error[0]) snprintf(error,256,"%.180s: invalid content definition",path);
    if (ok) { memcpy(d->source_digest,j.source_digest,32);*out=*d; }
    btp_json_close(&j);free(d);return ok;
}
int btp_definitions_compile(BtpDefinitions *d,BtpRoster *r,char error[256])
{
    /* This is the only new-content -> CHI record boundary. Handles are local
       to a validated package; saves bind that package before decoding them.
       Stable authoring IDs and full names never become DOS field offsets. */
    memset(r,0,sizeof *r);memcpy(r->package,d->id,sizeof r->package);memcpy(r->version,d->version,sizeof r->version);r->count=d->mech_count;
    for (unsigned i=0;i<d->mech_count;++i) {
        BtpMechDefinition *m=&d->mechs[i];BtpRosterMech *v=&r->mechs[i];uint8_t *b=v->record;
        memcpy(v->id,m->id,sizeof v->id);v->price=m->price;
        memset(b,' ',15);memcpy(b,m->label,strlen(m->label));b[16]=(uint8_t)m->mass;b[38]=(uint8_t)m->sinks;
        b[49]=(uint8_t)m->walk;b[50]=(uint8_t)m->jump;b[120]=1;b[121]=b[122]=255;
        b[123]=(uint8_t)i;b[124]=(uint8_t)(192u|d->presentations[m->presentation].sprite);
        for (unsigned k=0;k<11;++k) b[17+k]=(uint8_t)m->armor[k];
        for (unsigned k=0;k<8;++k) b[28+k]=(uint8_t)m->structure[k];
        for (unsigned k=0;k<2;++k) b[36+k]=(uint8_t)m->actuators[k];
        unsigned bin=0;
        for (unsigned at=51;at<86;) {
            unsigned loc=0;while (starts[loc]!=at) ++loc;unsigned used=0;
            for (unsigned k=0;k<m->count;++k) if (m->mounts[k].location==loc) {
                const BtpMountDefinition *mount=&m->mounts[k];const BtpAuthoredWeapon *w=&d->weapons[mount->weapon];
                b[at+used++]=(uint8_t)(w->behavior+16u);b[39+bin]=(uint8_t)(mount->ammo ? mount->ammo : 255);
                for (unsigned a=0;a<d->ammo_count;++a) if (!strcmp(d->ammo[a].id,w->ammunition)) v->ammo_cost[bin]=(uint8_t)d->ammo[a].price;
                d->mount_weapon[i][bin++]=(uint16_t)mount->weapon;
            }
            for (unsigned k=0;k<m->external_sinks[loc];++k) b[at+used++]=34;
            at+=slots[loc];
        }
        memcpy(b+86,b+17,21);memcpy(b+107,b+39,10);
    }
    if (error) error[0]=0;
    return 1;
}
const BtpAuthoredWeapon *btp_authored_weapon(const BtpDefinitions *d,const uint8_t m[125],unsigned mount)
{
    if (!d || (m[124]!=192 && m[124]!=193) || m[123]>=d->mech_count || mount>=d->mechs[m[123]].count) return NULL;
    return &d->weapons[d->mount_weapon[m[123]][mount]];
}

static void quoted(FILE *f,const char *s)
{
    fputc('"',f);for (;*s;++s) { if (*s=='"' || *s=='\\') fputc('\\',f);fputc(*s,f); }fputc('"',f);
}
static void export_body(FILE *f,const char *key,const uint8_t *values,unsigned count)
{
    fprintf(f,"      \"%s\": {",key);
    for (unsigned i=0;i<count;++i) fprintf(f,"%s\"%s\": %u",i ? ", " : "",bodies[i],values[i]);
    fputs("},\n",f);
}
int btp_definitions_export(const char *path,const BtpRoster *r,const BtpCombatData *combat,const BtpCombatProfile *p,char error[256])
{
    /* Export symbolic definitions and effective ranges, never original binary
       assets or mutable party records. The caller creates a new directory. */
    FILE *f=fopen(path,"rb");if (f) { fclose(f);snprintf(error,256,"Export file already exists: %.180s",path);return 0; }
    f=btp_file_create(path);if (!f) { snprintf(error,256,"Cannot create %.200s",path);return 0; }
    unsigned char used[17][255]={{0}};
    for (unsigned i=0;i<r->count;++i) for (unsigned at=51,bin=0;at<86;++at) {
        unsigned type=r->mechs[i].record[at];if (type>=16 && type<=32) used[type-16][r->mechs[i].ammo_cost[bin++]]=1;
    }
    fprintf(f,"{\n  \"format\": \"btp-content-v1\",\n  \"schema_version\": 1,\n  \"package_id\": \"%s\",\n  \"content_version\": \"%s\",\n",r->package,r->version);
    fputs("  \"rules\": {\"id\": ",f);
    if (p->fingerprint) fprintf(f,"\"chi:updated-lrm-v1\", \"distance_scale\": %u, \"minimum_range\": %u, \"short_range\": %u, \"medium_range\": %u, \"long_range\": %u},\n",p->scale,p->minimum,p->short_range,p->medium_range,p->long_range);
    else fputs("\"chi:legacy-v1\"},\n",f);
    fprintf(f,"  \"services\": {\"broker\": {\"id\": \"%s:broker\", \"behavior\": \"chi-broker-v1\"}, \"reload\": {\"id\": \"%s:reload\", \"behavior\": \"chi-reload-v1\"}},\n",r->package,r->package);
    fputs("  \"ammunition\": [",f);unsigned count=0;
    for (unsigned w=0;w<17;++w) for (unsigned price=1;price<255;++price) if (used[w][price])
        fprintf(f,"%s\n    {\"id\": \"chi:ammo-%s-%u\", \"price_per_shot\": %u}",count++ ? "," : "",behaviors[w],price,price);
    fputs("\n  ],\n  \"presentations\": [{\"id\": \"chi:locust\", \"source\": \"chi:locust\"}, {\"id\": \"chi:red-stinger\", \"source\": \"chi:red-stinger\"}],\n  \"weapons\": [",f);count=0;
    for (unsigned w=0;w<17;++w) for (unsigned price=0;price<255;++price) if (used[w][price]) {
        BtpWeaponDefinition v=btp_weapon_definition(combat,w+15);char name[12];memcpy(name,v.name,11);name[11]=0;
        const unsigned missiles[]={0,1,2,4,5,6,10,15,20};
        fprintf(f,"%s\n    {\"id\": \"chi:weapon-%s-%u\", \"name\": ",count++ ? "," : "",behaviors[w],price);quoted(f,name);fputs(", \"label\": ",f);quoted(f,name);
        fprintf(f,", \"behavior\": \"%s\", \"ammunition\": ",behaviors[w]);
        if (price) fprintf(f,"\"chi:ammo-%s-%u\"",behaviors[w],price);else fputs("\"none\"",f);
        fprintf(f,", \"damage\": %u, \"projectiles\": %u, \"heat\": %u, \"ranges\": {\"short\": %u, \"medium\": %u, \"long\": %u}}",v.damage,missiles[v.projectiles],v.heat,v.near_range*3,v.medium_range*3,v.far_range);
    }
    fputs("\n  ],\n  \"mechs\": [\n",f);
    for (unsigned i=0;i<r->count;++i) {
        const BtpRosterMech *v=&r->mechs[i];const uint8_t *m=v->record;char name[16];memcpy(name,m,15);name[15]=0;
        for (unsigned k=15;k && name[k-1]==' ';--k) name[k-1]=0;
        fprintf(f,"%s    {\n      \"id\": \"%s\", \"name\": ",i ? ",\n" : "",v->id);quoted(f,name);fputs(", \"label\": ",f);quoted(f,name);
        fprintf(f,",\n      \"mass_tons\": %u, \"price\": %u, \"presentation\": \"chi:%s\",\n      \"movement\": {\"walk\": %u, \"jump\": %u}, \"engine_heat_sinks\": %u,\n",m[16],v->price,m[124]&1u ? "red-stinger" : "locust",m[49],m[50],m[38]);
        export_body(f,"armor",m+17,11);export_body(f,"structure",m+28,8);
        fprintf(f,"      \"actuators\": {\"left_arm\": %u, \"right_arm\": %u, \"left_leg\": %u, \"right_leg\": %u},\n",m[36]>>4,m[37]>>4,m[36]&15u,m[37]&15u);
        uint8_t sinks[8]={0};for (unsigned loc=0;loc<8;++loc) for (unsigned k=0;k<slots[loc];++k) if (m[starts[loc]+k]==34) ++sinks[loc];
        export_body(f,"external_heat_sinks",sinks,8);fputs("      \"loadout\": [",f);unsigned bin=0;
        for (unsigned at=51;at<86;++at) if (m[at]>=16 && m[at]<=32) {
            unsigned loc=0;while (!(at>=starts[loc] && at<starts[loc]+slots[loc])) ++loc;
            fprintf(f,"%s{\"weapon\": \"chi:weapon-%s-%u\", \"location\": \"%s\", \"ammunition\": %u}",bin ? ", " : "",behaviors[m[at]-16],v->ammo_cost[bin],bodies[loc],m[39+bin]==255 ? 0u : m[39+bin]);++bin;
        }
        fputs("]\n    }",f);
    }
    fputs("\n  ]\n}\n",f);int ok=!ferror(f);if (fclose(f)) ok=0;
    if (!ok) snprintf(error,256,"Cannot write %.200s",path);
    return ok;
}

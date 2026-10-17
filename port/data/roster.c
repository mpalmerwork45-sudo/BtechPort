#include "data/roster.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

unsigned btp_roster_class(unsigned tons)
{
    return tons<=35 ? BTP_ROSTER_LIGHT : tons<=55 ? BTP_ROSTER_MEDIUM :
        tons<=75 ? BTP_ROSTER_HEAVY : BTP_ROSTER_ASSAULT;
}
const char *btp_roster_class_name(unsigned weight_class)
{
    static const char *const names[]={"All","Light","Medium","Heavy","Assault"};
    return weight_class<=BTP_ROSTER_ASSAULT ? names[weight_class] : "";
}
static int catalogue_before(const BtpRosterMech *a,const BtpRosterMech *b)
{
    if (a->record[16]!=b->record[16]) return a->record[16]<b->record[16];
    int name=memcmp(a->record,b->record,15);
    return name ? name<0 : strcmp(a->id,b->id)<0;
}
unsigned btp_roster_catalogue(const BtpRoster *r,unsigned weight_class,
    unsigned limit,unsigned indices[BTP_ROSTER_MAX])
{
    if (weight_class>BTP_ROSTER_ASSAULT) return 0;
    if (limit>r->count) limit=r->count;
    if (limit>BTP_ROSTER_MAX) limit=BTP_ROSTER_MAX;
    unsigned count=0;
    for (unsigned i=0;i<limit;++i) {
        if (weight_class && btp_roster_class(r->mechs[i].record[16])!=weight_class) continue;
        unsigned at=count++;
        while (weight_class && at && catalogue_before(&r->mechs[i],&r->mechs[indices[at-1]])) {
            indices[at]=indices[at-1];--at;
        }
        indices[at]=i;
    }
    return count;
}

/* A deliberately small JSON contract: bounded objects/arrays, unsigned
   integers and printable ASCII strings. No recursive generic parser, locale
   conversions, implicit coercions, ignored keys, or executable content. */
typedef struct { const char *start,*at,*end; char *error; } Reader;
static int bad(Reader *p,const char *message)
{
    if (!p->error[0]) snprintf(p->error,256,"Roster byte %lu: %s",(unsigned long)(p->at-p->start),message);
    return 0;
}
static void space(Reader *p)
{
    while (p->at<p->end && (*p->at==' ' || *p->at=='\n' || *p->at=='\r' || *p->at=='\t')) ++p->at;
}
static int take(Reader *p,char c)
{
    space(p);if (p->at==p->end || *p->at!=c) return bad(p,"unexpected token");
    ++p->at;return 1;
}
static int string(Reader *p,char *out,size_t capacity)
{
    if (!take(p,'"')) return 0;
    size_t n=0;
    while (p->at<p->end && *p->at!='"') {
        unsigned c=(unsigned char)*p->at++;
        if (c<32 || c>126 || c=='\\' || n+1>=capacity) return bad(p,"string must fit its field and use plain ASCII");
        out[n++]=(char)c;
    }
    out[n]=0;return take(p,'"');
}
static int number(Reader *p,unsigned max,unsigned *out)
{
    space(p);unsigned n=0;const char *begin=p->at;
    while (p->at<p->end && *p->at>='0' && *p->at<='9') {
        unsigned digit=(unsigned)(*p->at++-'0');
        if (n>max/10u || (n==max/10u && digit>max%10u)) return bad(p,"integer exceeds field limit");
        n=10u*n+digit;
    }
    if (begin==p->at || (p->at-begin>1 && *begin=='0')) return bad(p,"expected unsigned integer");
    *out=n;return 1;
}
static int list(Reader *p,uint8_t *out,unsigned count)
{
    if (!take(p,'[')) return 0;
    for (unsigned i=0;i<count;++i) {
        unsigned n;if ((i && !take(p,',')) || !number(p,255,&n)) return 0;
        out[i]=(uint8_t)n;
    }
    return take(p,']');
}
static int field(Reader *p,const char *const *names,unsigned count,uint32_t *seen,unsigned *id)
{
    char name[40];if (!string(p,name,sizeof name) || !take(p,':')) return 0;
    for (unsigned i=0;i<count;++i) if (!strcmp(name,names[i])) {
        if (*seen&(UINT32_C(1)<<i)) return bad(p,"duplicate field");
        *seen|=UINT32_C(1)<<i;*id=i;return 1;
    }
    return bad(p,"unknown field");
}
static int next(Reader *p,char closing,int *more)
{
    space(p);*more=p->at<p->end && *p->at!=closing;
    return !*more || take(p,',');
}
static int identifier(const char *s,int namespaced)
{
    unsigned colons=0;
    if (*s<'a' || *s>'z') return 0;
    for (;*s;++s) {
        if (*s==':') { ++colons;if (s[1]<'a' || s[1]>'z') return 0; }
        else if (!(*s>='a' && *s<='z') && !(*s>='0' && *s<='9') && *s!='-' && *s!='_' && *s!='.') return 0;
    }
    return colons==(unsigned)namespaced;
}
static const char *const locations[]={"left_arm","left_torso","left_leg","head","center_torso","right_arm","right_torso","right_leg"};
static const uint8_t starts[]={51,58,79,85,83,65,72,81},counts[]={7,7,2,1,2,7,7,2};
static const char *const weapons[]={"small_laser","medium_laser","large_laser","ppc","ac2","ac5","ac10","ac20","machine_gun","flamer","lrm5","lrm10","lrm15","lrm20","srm2","srm4","srm6"};
typedef struct { uint8_t location,weapon,ammo,cost; } Mount;
static int mount(Reader *p,Mount *m)
{
    const char *const names[]={"location","weapon","ammo","ammo_cost"};
    uint32_t seen=0;int more=1;
    if (!take(p,'{')) return 0;
    while (more) {
        unsigned id,n=0;if (!field(p,names,4,&seen,&id)) return 0;
        if (id<2) {
            char name[32];if (!string(p,name,sizeof name)) return 0;
            unsigned count=id ? 17u : 8u;
            const char *const *table=id ? weapons : locations;
            for (;n<count && strcmp(name,table[n]);++n) {}
            if (n==count) return bad(p,"unsupported weapon or body location");
            if (id) m->weapon=(uint8_t)(n+16u);else m->location=(uint8_t)n;
        } else {
            if (!number(p,254,&n)) return 0;
            if (id==2) m->ammo=(uint8_t)n;else m->cost=(uint8_t)n;
        }
        if (!next(p,'}',&more)) return 0;
    }
    if (!take(p,'}') || seen!=15) return bad(p,"incomplete weapon mount");
    int ammunition=(m->weapon>=20 && m->weapon<=24) || m->weapon>=26;
    return (ammunition ? m->ammo && m->cost : !m->ammo && !m->cost) || bad(p,"ammunition and price must match weapon type");
}
static int mech(Reader *p,BtpRosterMech *m)
{
    const char *const names[]={"id","name","save_code","mass_tons","walk","jump","engine_heat_sinks",
        "sprite","price","armor","structure","actuators","external_heat_sinks","loadout"};
    uint32_t seen=0;int more=1;Mount mounts[10]={{0}};unsigned nmounts=0;
    uint8_t sinks[8]={0};char name[16]={0};uint8_t *b=m->record;
    if (!take(p,'{')) return 0;
    while (more) {
        unsigned id,n;if (!field(p,names,14,&seen,&id)) return 0;
        switch (id) {
        case 0:if (!string(p,m->id,sizeof m->id)) return 0;break;
        case 1:if (!string(p,name,sizeof name)) return 0;break;
        case 7: {
            char sprite[16];if (!string(p,sprite,sizeof sprite)) return 0;
            if (strcmp(sprite,"locust") && strcmp(sprite,"red_stinger")) return bad(p,"unsupported sprite family");
            /* Original records can also contain values such as 176 in byte
               123 (UrbanMech). A separate high-bit marker distinguishes an
               external definition from original refit/model bytes. */
            b[124]=(uint8_t)(128u|(!strcmp(sprite,"red_stinger") ? 1u : 0u));break;
        }
        case 9:if (!list(p,b+17,11)) return 0;break;
        case 10:if (!list(p,b+28,8)) return 0;break;
        case 11:if (!list(p,b+36,2)) return 0;break;
        case 12:if (!list(p,sinks,8)) return 0;break;
        case 13: {
            if (!take(p,'[')) return 0;
            int another=1;
            while (another) {
                if (nmounts==10) return bad(p,"at most ten weapons fit the CHI adapter");
                if (!mount(p,&mounts[nmounts++]) || !next(p,']',&another)) return 0;
            }
            if (!take(p,']')) return 0;
            break;
        }
        default:
            if (!number(p,id==8 ? 999999u : 255u,&n)) return 0;
            if (id==8) m->price=n;
            else b[id==2 ? 123 : id==3 ? 16 : id==4 ? 49 : id==5 ? 50 : 38]=(uint8_t)n;
            break;
        }
        if (!next(p,'}',&more)) return 0;
    }
    if (!take(p,'}') || seen!=16383) return bad(p,"incomplete mech definition");
    if (!identifier(m->id,1) || !name[0] || name[0]<'A' || name[0]>'Z' ||
        b[123]<BTP_ROSTER_CODE || b[123]>=BTP_ROSTER_CODE+BTP_ROSTER_MAX ||
        b[16]<20 || b[16]>100 || !b[49] || b[49]>12 || b[50]>12 || b[38]>30 || !m->price)
        return bad(p,"invalid mech identity, weight, movement, heat or price");
    for (unsigned i=0;i<8;++i) if (!b[28+i] || b[28+i]>40 || b[17+i]>2u*b[28+i]+(i==3 ? 3u : 0u))
        return bad(p,"invalid armor or internal structure");
    if (b[18]+b[25]>2u*b[29] || b[21]+b[26]>2u*b[32] || b[23]+b[27]>2u*b[34])
        return bad(p,"front and rear torso armor exceed capacity");
    memset(b,' ',15);memcpy(b,name,strlen(name));b[120]=1;b[121]=b[122]=255;
    /* CHI uses one component descriptor per weapon, rather than tabletop
       critical-slot footprints. Sort by physical record offset so ammunition
       indices agree with combat, repairs, inspection and salvage. */
    unsigned weapon=0,total_sinks=b[38];
    for (unsigned at=51;at<86;) {
        unsigned loc=0;while (loc<8 && starts[loc]!=at) ++loc;
        if (loc==8) return bad(p,"invalid component mapping");
        unsigned used=0;
        for (unsigned i=0;i<nmounts;++i) if (mounts[i].location==loc) {
            if (used>=counts[loc]) return bad(p,"too many components at a location");
            b[at+used++]=mounts[i].weapon;
            b[39+weapon]=mounts[i].ammo ? mounts[i].ammo : 255;
            m->ammo_cost[weapon++]=mounts[i].cost;
        }
        if (sinks[loc]>counts[loc]-used) return bad(p,"heat sinks exceed component capacity");
        for (unsigned i=0;i<sinks[loc];++i) b[at+used++]=34;
        total_sinks+=sinks[loc];at+=counts[loc];
    }
    if (total_sinks>30) return bad(p,"too many heat sinks for CHI heat rules");
    memcpy(b+86,b+17,21);memcpy(b+107,b+39,10);
    return 1;
}
static void hash(uint32_t *h,const void *bytes,size_t n)
{
    const uint8_t *b=bytes;for (size_t i=0;i<n;++i) *h=(*h^b[i])*UINT32_C(16777619);
}
static void hash_mech(uint32_t *h,const BtpRosterMech *m)
{
    hash(h,m->id,sizeof m->id);hash(h,m->record,125);hash(h,m->ammo_cost,10);
    for (unsigned j=0;j<4;++j) { uint8_t b=(uint8_t)(m->price>>(8*j));hash(h,&b,1); }
}
unsigned btp_roster_saved_count(const BtpRoster *r,const uint8_t package[32],
    const uint8_t version[32],uint32_t fingerprint)
{
    if (!r || !r->count || memcmp(package,r->package,32)) return 0;
    if (!memcmp(version,r->version,32) && fingerprint==r->fingerprint) return r->count;
    /* The original save binds every old ID, byte, ammunition price and sale
       price. Recompute that fingerprint using its saved version and each
       shorter prefix: only appending definitions is compatible. This never
       accepts a changed existing definition or a version-only edit. */
    uint32_t h=UINT32_C(2166136261);hash(&h,r->package,32);hash(&h,version,32);
    for (unsigned i=0;i+1u<r->count;++i) {
        hash_mech(&h,&r->mechs[i]);if (h==fingerprint) return i+1u;
    }
    return 0;
}
static int compare(const void *a,const void *b)
{
    return (int)((const BtpRosterMech *)a)->record[123]-(int)((const BtpRosterMech *)b)->record[123];
}
static int decode(Reader *p,BtpRoster *r)
{
    const char *const names[]={"format","package_id","content_version","mechs"};
    uint32_t seen=0;int more=1;if (!take(p,'{')) return 0;
    while (more) {
        unsigned id;if (!field(p,names,4,&seen,&id)) return 0;
        if (!id) {
            char format[32];if (!string(p,format,sizeof format)) return 0;
            if (strcmp(format,"btp-chi-roster-v1")) return bad(p,"unsupported roster format");
        } else if (id==1) { if (!string(p,r->package,sizeof r->package)) return 0; }
        else if (id==2) { if (!string(p,r->version,sizeof r->version)) return 0; }
        else {
            int another=1;if (!take(p,'[')) return 0;
            while (another) {
                if (r->count==BTP_ROSTER_MAX) return bad(p,"too many mech definitions");
                if (!mech(p,&r->mechs[r->count++]) || !next(p,']',&another)) return 0;
            }
            if (!take(p,']')) return 0;
        }
        if (!next(p,'}',&more)) return 0;
    }
    if (!take(p,'}')) return 0;
    space(p);
    if (seen!=15 || p->at!=p->end || !identifier(r->package,0) || !r->version[0]) return bad(p,"incomplete package or trailing input");
    qsort(r->mechs,r->count,sizeof r->mechs[0],compare);
    r->fingerprint=UINT32_C(2166136261);
    hash(&r->fingerprint,r->package,32);hash(&r->fingerprint,r->version,32);
    for (unsigned i=0;i<r->count;++i) {
        BtpRosterMech *m=&r->mechs[i];size_t prefix=strlen(r->package);
        if (strncmp(m->id,r->package,prefix) || m->id[prefix]!=':') return bad(p,"mech ID must belong to this package");
        for (unsigned j=0;j<i;++j) if (!strcmp(m->id,r->mechs[j].id) || m->record[123]==r->mechs[j].record[123]) return bad(p,"duplicate mech ID or save code");
        hash_mech(&r->fingerprint,m);
    }
    return 1;
}
int btp_roster_load(const char *path,BtpRoster *roster,char error[256])
{
    if (!path || !roster || !error) return 0;
    error[0]=0;FILE *f=fopen(path,"rb");
    if (!f) { snprintf(error,256,"Cannot open updated roster: %.190s",path);return 0; }
    enum { LIMIT=65536 };
    char *bytes=malloc(LIMIT+1);BtpRoster *candidate=calloc(1,sizeof *candidate);
    if (!bytes || !candidate) { fclose(f);free(bytes);free(candidate);snprintf(error,256,"Roster allocation failed");return 0; }
    size_t n=fread(bytes,1,LIMIT+1,f);int ok=!ferror(f);if (fclose(f)) ok=0;
    Reader p={bytes,bytes,bytes+n,error};
    if (!ok || n>LIMIT) ok=bad(&p,"cannot read roster or size exceeds 64 KiB");
    else ok=decode(&p,candidate);
    if (ok) *roster=*candidate;
    free(bytes);free(candidate);return ok;
}
int btp_roster_custom(const uint8_t m[125])
{
    return m && (m[124]==128 || m[124]==129) &&
        m[123]>=BTP_ROSTER_CODE && m[123]<BTP_ROSTER_CODE+BTP_ROSTER_MAX;
}
const BtpRosterMech *btp_roster_definition(const BtpRoster *r,const uint8_t m[125])
{
    if (r && btp_roster_custom(m)) for (unsigned i=0;i<r->count;++i) if (r->mechs[i].record[123]==m[123]) return &r->mechs[i];
    return NULL;
}

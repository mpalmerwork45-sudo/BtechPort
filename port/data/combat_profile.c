#include "data/file.h"
#include "data/combat_profile.h"
#include <errno.h>
#include <stdio.h>
#include <string.h>

/* A bounded, nonrecursive JSON reader for this small contract. Unknown and
   duplicate fields fail rather than silently selecting different game rules. */
typedef struct { const char *at,*end;char *error; } Reader;
static int bad(Reader *p,const char *why)
{
    if (!p->error[0]) snprintf(p->error,256,"Updated combat rules: %s",why);
    return 0;
}
static void space(Reader *p) { while (p->at<p->end && (*p->at==' ' || *p->at=='\t' || *p->at=='\n' || *p->at=='\r')) ++p->at; }
static int token(Reader *p,char c)
{
    space(p);if (p->at==p->end || *p->at!=c) return bad(p,"unexpected token");
    ++p->at;return 1;
}
static int string(Reader *p,char value[48])
{
    if (!token(p,'"')) return 0;
    unsigned n=0;
    while (p->at<p->end && *p->at!='"') {
        unsigned c=(unsigned char)*p->at++;
        if (c<32 || c>126 || c=='\\' || n==47) return bad(p,"invalid string");
        value[n++]=(char)c;
    }
    value[n]=0;return token(p,'"');
}
static int number(Reader *p,uint8_t *value)
{
    space(p);const char *start=p->at;unsigned n=0;
    while (p->at<p->end && *p->at>='0' && *p->at<='9') {
        n=n*10u+(unsigned)(*p->at++-'0');if (n>63) return bad(p,"number exceeds 63");
    }
    if (p->at==start || (p->at-start>1 && *start=='0')) return bad(p,"expected unsigned integer");
    *value=(uint8_t)n;return 1;
}
int btp_combat_profile_lrm(unsigned w) { return w>=25 && w<=28; }
int btp_combat_profile_load(const char *roster_path,BtpCombatProfile *out,char error[256])
{
    if (!roster_path || !out || !error) return 0;
    error[0]=0;char path[4096];size_t prefix=0;
    for (const char *s=roster_path;*s;++s) if (*s=='/' || *s=='\\') prefix=(size_t)(s-roster_path)+1u;
    if (prefix+sizeof "combat.json">sizeof path) { snprintf(error,256,"Updated combat path too long");return 0; }
    memcpy(path,roster_path,prefix);memcpy(path+prefix,"combat.json",sizeof "combat.json");
    FILE *f=btp_fopen(path,"rb");
    if (!f) {
        if (errno==ENOENT) { *out=(BtpCombatProfile){0};return 1; }
        snprintf(error,256,"Cannot open Updated combat rules");return 0;
    }
    char bytes[4097];size_t n=fread(bytes,1,sizeof bytes,f);int failed=ferror(f);if (fclose(f)) failed=1;
    if (failed || n==sizeof bytes) { snprintf(error,256,"Cannot read Updated combat rules (limit 4096 bytes)");return 0; }
    Reader p={bytes,bytes+n,error};BtpCombatProfile v={0};unsigned seen=0;
    const char *const keys[]={"format","profile","planner","distance_scale","minimum_range","short_range","medium_range","long_range","weapons"};
    const char *const fixed[]={"btp-combat-v1","chi-updated-lrm-v1","weapon-aware-v1"};
    if (!token(&p,'{')) return 0;
    for (;;) {
        char key[48];if (!string(&p,key) || !token(&p,':')) return 0;
        unsigned k=0;while (k<9 && strcmp(key,keys[k])) ++k;
        if (k==9 || (seen&(1u<<k))) return bad(&p,"unknown or duplicate field");
        seen|=1u<<k;
        if (k<3) { char value[48];if (!string(&p,value)) return 0;if (strcmp(value,fixed[k])) return bad(&p,"unsupported schema, profile or planner"); }
        else if (k==8) {
            static const char *const names[]={"lrm5","lrm10","lrm15","lrm20"};unsigned weapons=0;
            if (!token(&p,'[')) return 0;
            for (unsigned i=0;i<4;++i) {
                char name[48];if ((i && !token(&p,',')) || !string(&p,name)) return 0;
                unsigned w=0;while (w<4 && strcmp(name,names[w])) ++w;
                if (w==4 || (weapons&(1u<<w))) return bad(&p,"weapons must name each of the four standard LRMs once");
                weapons|=1u<<w;
            }
            if (!token(&p,']')) return 0;
        } else {
            uint8_t *fields[]={&v.scale,&v.minimum,&v.short_range,&v.medium_range,&v.long_range};
            if (!number(&p,fields[k-3])) return 0;
        }
        space(&p);if (p.at<p.end && *p.at=='}') { ++p.at;break; }
        if (!token(&p,',')) return 0;
    }
    space(&p);
    if (p.at!=p.end || seen!=511 || !v.scale || v.scale>6 || !v.minimum || v.minimum>12 ||
        v.minimum>=v.short_range || v.short_range>=v.medium_range || v.medium_range>=v.long_range ||
        (unsigned)v.scale*(v.long_range+1u)>255) return bad(&p,"incomplete or inconsistent range definition");
    /* Hash canonical gameplay values and the fixed v1 policy identity, never
       JSON whitespace/order or cosmetic assets. Future algorithms get new IDs. */
    uint32_t h=UINT32_C(2166136261);
    for (const char *s="chi-updated-lrm-v1/weapon-aware-v1";*s;++s) h=(h^(unsigned char)*s)*UINT32_C(16777619);
    const uint8_t fields[]={v.scale,v.minimum,v.short_range,v.medium_range,v.long_range};
    for (unsigned i=0;i<sizeof fields;++i) h=(h^fields[i])*UINT32_C(16777619);
    v.fingerprint=h ? h : 1u;*out=v;return 1;
}

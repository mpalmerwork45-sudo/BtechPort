#include "data/chi_services.h"
#include "data/project.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

const BtpChiParameter btp_chi_parameters[BTP_SVC_COUNT]={
#include "data/chi_service_parameters.inc"
};
const BtpChiAction btp_chi_actions[47]={
#include "data/chi_service_actions.inc"
};
static unsigned original(const BtpResources *r,unsigned id)
{
    if (id>=BTP_SVC_COUNT) return 0;
    const BtpChiParameter *p=&btp_chi_parameters[id];
    if (p->source==BTP_SVC_SOURCE_CONSTANT || !r) return p->initial;
    if (p->source==BTP_SVC_SOURCE_AMMO) return r->combat.ammo_prices[p->index];
    if (p->source==BTP_SVC_SOURCE_REFIT) return r->combat.refit_prices[p->index];
    if (p->source==BTP_SVC_SOURCE_MEDICAL_PRICE) return r->combat.medical_prices[p->index];
    return r->combat.medical[p->index/4][p->index%4];
}
unsigned btp_chi_service_default(const BtpResources *r,unsigned id)
{
    return id>=BTP_SVC_COUNT ? 0 : r && r->project && r->project->chi_services ? r->project->chi_services->defaults[id] : original(r,id);
}
unsigned btp_chi_service(const BtpResources *r,unsigned id)
{
    return id>=BTP_SVC_COUNT ? 0 : r && r->project && r->project->chi_services ? r->project->chi_services->values[id] : original(r,id);
}
int btp_chi_services_load(const char *root,const char *file,BtpChiServices *c,BtpResources *r,BtpDigest *digest,BtpError *e)
{
    char path[4096],format[64];BtpJson j={0};unsigned version;int ok=0;uint8_t seen[BTP_SVC_COUNT]={0};
    if (!btp_project_path(root,file,path,e) || !btp_json_load(&j,path,e->text)) goto done;
    btp_digest_add(digest,j.source_digest,32);btp_digest_add(digest,"chi-services-v1",15);
    if (!btp_json_string(&j,btp_json_field(&j,1,"format"),format,sizeof format) || strcmp(format,"btp-chi-services-v1") ||
        !btp_json_uint(&j,btp_json_field(&j,1,"schema_version"),1,1,&version)) goto done;
    for (unsigned i=0;i<BTP_SVC_COUNT;++i) c->values[i]=c->defaults[i]=original(r,i);
    unsigned parameters=btp_json_field(&j,1,"parameters");if (!btp_json_type(&j,parameters,'{')) goto done;
    for (unsigned n=j.nodes[parameters].first;n;n=j.nodes[n].next) {
        unsigned id=0;while (id<BTP_SVC_COUNT && strcmp(j.nodes[n].key,btp_chi_parameters[id].id)) ++id;
        if (id==BTP_SVC_COUNT || seen[id]++) { btp_json_error(&j,n,"unknown or duplicate native service parameter");goto done; }
        j.nodes[n].used=1;
        const BtpChiParameter *p=&btp_chi_parameters[id];unsigned value;
        if (!btp_json_uint(&j,n,p->low,p->high,&value)) goto done;
        if (id==BTP_SVC_RECRUIT_SPY_CHANCE && value!=0 && value!=50 && value!=100) { btp_json_error(&j,n,"spy chance must be 0, 50 or 100 percent to retain the native RNG draw");goto done; }
        c->values[id]=value;
    }
    unsigned stock=btp_json_optional(&j,1,"broker_stock");
    if (stock) {
        if (!btp_json_type(&j,stock,'[')) goto done;
        c->stock_limited=1;
        for (unsigned n=j.nodes[stock].first;n;n=j.nodes[n].next) {
            if (c->stock_count==256 || !btp_json_string(&j,n,c->stock_ids[c->stock_count],64)) goto done;
            for (unsigned i=0;i<c->stock_count;++i) if (!strcmp(c->stock_ids[i],c->stock_ids[c->stock_count])) { btp_json_error(&j,n,"duplicate broker unit ID");goto done; }
            ++c->stock_count;
        }
    }
    if (!btp_json_done(&j,parameters) || !btp_json_done(&j,1)) goto done;
    /* Cache-backed prices/programs are consumed by the existing mechanics and
       renderer. Never change the immutable cache files or saved game layout. */
    for (unsigned i=0;i<BTP_SVC_COUNT;++i) {
        const BtpChiParameter *p=&btp_chi_parameters[i];unsigned v=c->values[i];
        if (p->source==BTP_SVC_SOURCE_AMMO) r->combat.ammo_prices[p->index]=(uint8_t)v;
        if (p->source==BTP_SVC_SOURCE_REFIT) r->combat.refit_prices[p->index]=(uint16_t)v;
        if (p->source==BTP_SVC_SOURCE_MEDICAL_PRICE) r->combat.medical_prices[p->index]=(uint16_t)v;
        if (p->source==BTP_SVC_SOURCE_MEDICAL_CODE) r->combat.medical[p->index/4][p->index%4]=(uint8_t)v;
    }
    ok=1;
done:if (!ok && !*e->text) snprintf(e->text,sizeof e->text,"%s: invalid native service settings",file);btp_json_close(&j);return ok;
}
int btp_chi_services_stock(BtpChiServices *c,const BtpRoster *r,BtpError *e)
{
    if (!c || !c->stock_limited) return 1;
    for (unsigned i=0;i<c->stock_count;++i) {
        unsigned at=0;while (at<r->count && strcmp(r->mechs[at].id,c->stock_ids[i])) ++at;
        if (at==r->count) { snprintf(e->text,sizeof e->text,"chi-services.json: $.broker_stock[%u]: unknown unit ID %.63s",i,c->stock_ids[i]);return 0; }
        c->stock[at]=1;
    }
    return 1;
}
int btp_chi_broker_stock(const BtpResources *r,unsigned definition)
{
    const BtpChiServices *c=r && r->project ? r->project->chi_services : NULL;
    return !c || !c->stock_limited || (definition<256 && c->stock[definition]);
}
int btp_chi_service_reference(const BtpResources *r,const char *id,unsigned *value)
{
    if (!r || !r->project || !r->project->chi_services) return 0;
    for (unsigned i=0;i<BTP_SVC_COUNT;++i) if (!strcmp(id,btp_chi_parameters[i].id)) { *value=btp_chi_service(r,i);return 1; }
    return 0;
}
int btp_chi_service_expand(const BtpResources *r,const char *source,char *out,size_t cap)
{
    size_t used=0;
    while (*source) {
        if (!strncmp(source,"{service:",9)) {
            const char *end=strchr(source+9,'}');char key[96],number[32];unsigned value;
            if (!end || (size_t)(end-source-9)>=sizeof key) return 0;
            memcpy(key,source+9,(size_t)(end-source-9));key[end-source-9]=0;
            char *comma=strstr(key,":comma");if (comma && strcmp(comma,":comma")) return 0;if (comma) *comma=0;
            if (!btp_chi_service_reference(r,key,&value)) return 0;
            snprintf(number,sizeof number,"%u",value);size_t n=strlen(number);
            for (size_t i=0;i<n;++i) {
                if (comma && i && !((n-i)%3)) { if (used+1>=cap) return 0;out[used++]=','; }
                if (used+1>=cap) return 0;
                out[used++]=number[i];
            }
            source=end+1;
        } else { if (used+1>=cap) return 0;out[used++]=*source++; }
    }
    if (used>=cap) return 0;
    out[used]=0;return 1;
}
int btp_chi_service_dialogue(BtpResources *r,BtpError *e)
{
    BtpDialogue *rebuilt=calloc(1,sizeof *rebuilt);if (!rebuilt) return 0;
    memcpy(rebuilt->font,r->dialogue.font,sizeof rebuilt->font);
    for (unsigned i=0;i<BTP_TALK_STRINGS;++i) {
        char text[BTP_TALK_MAX];const char *source=(const char *)r->dialogue.bytes+r->dialogue.offset[i];
        if (!btp_chi_service_expand(r,source,text,sizeof text) || strlen(text)+1>(size_t)BTP_TALK_MAX-rebuilt->length) {
            snprintf(e->text,sizeof e->text,"campaign.json: $.dialogue_overrides[%u]: invalid service reference or native text budget exceeded",i);free(rebuilt);return 0;
        }
        size_t size=strlen(text);rebuilt->offset[i]=rebuilt->length;rebuilt->size[i]=(uint16_t)size;
        memcpy(rebuilt->bytes+rebuilt->length,text,size+1);rebuilt->length+=(uint16_t)(size+1);
    }
    r->dialogue=*rebuilt;free(rebuilt);return 1;
}
void btp_chi_services_catalogue(const BtpResources *r)
{
    fputs("{\"format\":\"btp-chi-service-catalogue-v1\",\"parameters\":[",stdout);
    for (unsigned i=0;i<BTP_SVC_COUNT;++i) {
        const BtpChiParameter *p=&btp_chi_parameters[i];
        printf("%s{\"id\":\"%s\",\"label\":\"%s\",\"group\":\"%s\",\"minimum\":%u,\"maximum\":%u,\"default\":%u,\"value\":%u}",i ? "," : "",p->id,p->label,p->group,p->low,p->high,btp_chi_service_default(r,i),btp_chi_service(r,i));
    }
    fputs("],\"actions\":[",stdout);
    for (unsigned i=0;i<47;++i) {
        const BtpChiAction *a=&btp_chi_actions[i];
        printf("%s{\"action\":%u,\"id\":\"%s\",\"name\":\"%s\",\"group\":\"%s\",\"consumer\":\"%s\",\"requirements\":\"%s\",\"outputs\":\"%s\",\"mutations\":\"%s\",\"yield\":\"%s\",\"errors\":\"%s\",\"buildings\":[",i ? "," : "",a->action,a->id,a->name,a->group,a->consumer,a->requires,a->outputs,a->mutations,a->yields,a->errors);
        unsigned count=0;for (unsigned b=0;b<26;++b) if (a->buildings&(1u<<b)) printf("%s%u",count++ ? "," : "",b);
        fputs("]}",stdout);
    }
    puts("]}");
}

#include "data/chi_bridge.h"
#include "data/project.h"
#include "data/json.h"
#include <stdio.h>
#include <string.h>

static int text(BtpJson *j,unsigned n,const char *key,char *out,size_t size)
{ return btp_json_string(j,btp_json_field(j,n,key),out,size); }
static int number(BtpJson *j,unsigned n,const char *key,unsigned lo,unsigned hi,unsigned *out)
{ return btp_json_uint(j,btp_json_field(j,n,key),lo,hi,out); }
static int fail(BtpError *e,const char *id,const char *message)
{ snprintf(e->text,sizeof e->text,"chi-bridge.json: $[%.90s]: %.125s",id,message);return 0; }
int btp_chi_bridge_action(unsigned action)
{
    /* These services own bounded menus/receipts and return through their BLD.
       Training, theft, arena and cache operations require larger native scene
       contracts and are rejected as callable services, not guessed at. */
    return action==7 || action==8;
}
static int call_path(const BtpChiProgram *p,const BtpBld *b,const BtpChiCall *c)
{
    /* Include the original receipt; reject another owner, story writes,
       an early END or a cycle. More adapters need explicit owner contracts. */
    if (c->building!=2 || c->end!=btp_bld_after(b,0x2cf)) return 0;
    unsigned pc=c->entry;
    for (unsigned budget=0;budget<p->count;++budget) {
        if (pc==c->end) return 1;
        unsigned i=0;while(i<p->count && p->nodes[i].offset!=pc)++i;
        if(i==p->count)return 0;
        const BtpChiInstruction *v=&p->nodes[i];unsigned op=v->opcode;
        if(op==0xf5) { if(pc!=c->entry || b->bytes[pc+1]!=c->action)return 0; }
        else if(op!=0xfe && op!=0xfd && op!=0xfc && op!=0xf0 && op!=0xf2 && op!=0xfb && op!=0xf8)return 0;
        pc=op==0xf8 ? b->bytes[pc+1]|(unsigned)b->bytes[pc+2]<<8 : pc+v->length;
    }
    return 0;
}
int btp_chi_bridge_load(const char *root,const char *file,BtpProject *p,BtpDigest *digest,BtpError *error)
{
    char path[4096],format[64];BtpJson j={0};unsigned version;int ok=0;
    if (!btp_project_path(root,file,path,error) || !btp_json_load(&j,path,error->text)) goto done;
    if (!text(&j,1,"format",format,sizeof format) || strcmp(format,"btp-chi-bridge-v1") ||
        !number(&j,1,"schema_version",1,1,&version)) goto done;
    BtpChiBridge *b=p->chi_bridge;unsigned list=btp_json_field(&j,1,"entrances");
    if (!btp_json_type(&j,list,'[')) goto done;
    for (unsigned n=j.nodes[list].first;n;n=j.nodes[n].next) {
        if (b->binding_count==BTP_CHI_BINDINGS) { btp_json_error(&j,n,"at most 64 native entrance bindings");goto done; }
        BtpChiBinding *v=&b->bindings[b->binding_count];char map[64],event[64],expected[64];unsigned slot,found=0;
        if (!text(&j,n,"id",v->id,sizeof v->id) || !btp_content_id(v->id,1) ||
            !text(&j,n,"map",map,sizeof map) || !text(&j,n,"event",event,sizeof event) ||
            !number(&j,n,"entrance",0,11,&slot) || !btp_json_done(&j,n)) goto done;
        for (unsigned i=1;i<=13;++i) { snprintf(expected,sizeof expected,"chi:map-%02u",i);if (!strcmp(map,expected)) found=i; }
        /* MAP14/15 are cache-owned interiors, and native doorway detection
           only visits the first twelve slots. Reject unreachable bindings. */
        if (!found) { btp_json_error(&j,n,"binding requires a native outdoor map ID chi:map-01..13");goto done; }
        v->map=(uint8_t)found;v->entrance=(uint8_t)slot;found=BTP_EVENT_NODES;
        for (unsigned i=0;i<p->adventure.node_count;++i) if (!strcmp(event,p->adventure.nodes[i].id)) found=i;
        if (found==BTP_EVENT_NODES) { btp_json_error(&j,n,"unknown quest event");goto done; }v->event=(uint16_t)found;
        for (unsigned i=0;i<b->binding_count;++i) if (!strcmp(v->id,b->bindings[i].id) ||
            (v->map==b->bindings[i].map && v->entrance==b->bindings[i].entrance)) {
            btp_json_error(&j,n,"duplicate entrance binding ID or location");goto done;
        }
        ++b->binding_count;
    }
    list=btp_json_field(&j,1,"native_calls");if (!btp_json_type(&j,list,'[')) goto done;
    for (unsigned n=j.nodes[list].first;n;n=j.nodes[n].next) {
        if (b->call_count==BTP_CHI_CALLS) { btp_json_error(&j,n,"at most 64 native calls");goto done; }
        BtpChiCall *c=&b->calls[b->call_count];
        if (!text(&j,n,"id",c->id,sizeof c->id) || !btp_content_id(c->id,1) ||
            !text(&j,n,"program",c->program,sizeof c->program) || !text(&j,n,"entry",c->label,sizeof c->label)) goto done;
        /* Resolve the return label after all source programs are compiled. */
        char end[64];if (!text(&j,n,"return",end,sizeof end) || !btp_content_id(end,1) || !btp_json_done(&j,n)) goto done;
        strcpy(c->return_label,end);
        for (unsigned i=0;i<b->call_count;++i) if (!strcmp(c->id,b->calls[i].id)) { btp_json_error(&j,n,"duplicate native call ID");goto done; }
        ++b->call_count;
    }
    if (!btp_json_done(&j,1)) goto done;
    btp_digest_add(digest,j.source_digest,32);ok=1;
done:
    if (!ok && !*error->text) btp_json_error(&j,1,"invalid native quest bridge");
    btp_json_close(&j);return ok;
}
int btp_chi_bridge_resolve(BtpProject *p,BtpError *error)
{
    if (!p->chi_bridge) {
        for (unsigned i=0;i<p->adventure.node_count;++i) if (p->adventure.nodes[i].op>=BTP_EVENT_CALL)
            return fail(error,p->adventure.nodes[i].id,"bridge operations require an imported campaign with chi_bridge");
        return 1;
    }
    if (!p->chi_edition || !p->chi_spatial || !p->chi_scripts || !p->adventure.loaded)
        return fail(error,"capabilities","bridge requires CHI maps, labelled scripts and quest events");
    BtpChiBridge *b=p->chi_bridge;
    for (unsigned i=0;i<b->binding_count;++i) {
        const BtpChiBinding *v=&b->bindings[i];const BtpMap *m=v->map==1 ? &p->chi_resources->map :
            v->map==15 ? &p->chi_resources->maproom : v->map==11 ? &p->chi_resources->destroyed : &p->chi_resources->local[v->map-1];
        if (!m->entrance_x[v->entrance] || !m->entrance_y[v->entrance])
            return fail(error,v->id,"binding refers to an unused entrance; place its doorway in CHI maps first");
    }
    for (unsigned i=0;i<b->call_count;++i) {
        BtpChiCall *c=&b->calls[i];const BtpChiProgram *program=NULL;
        for (unsigned k=0;k<26;++k) if (!strcmp(c->program,p->chi_scripts->programs[k].id)) { program=&p->chi_scripts->programs[k];c->building=(uint8_t)k; }
        if (!program) return fail(error,c->id,"unknown BLD program");
        const BtpChiInstruction *entry=NULL,*end=NULL;
        for (unsigned k=0;k<program->count;++k) {
            if (!strcmp(c->label,program->nodes[k].id)) entry=&program->nodes[k];
            if (!strcmp(c->return_label,program->nodes[k].id)) end=&program->nodes[k];
        }
        if (!entry || entry->opcode!=0xf5 || !end || !end->opcode || entry==end)
            return fail(error,c->id,"call requires a native-action entry and a different instruction return label");
        c->entry=entry->offset;c->end=end->offset;
        c->action=p->chi_resources->buildings[c->building].bytes[c->entry+1u];
        if (!btp_chi_bridge_action(c->action)) return fail(error,c->id,"this native action has no bridge service adapter");
        if (!call_path(program,&p->chi_resources->buildings[c->building],c))
            return fail(error,c->id,"bank call must reach its original post-receipt label through only presentation instructions");
    }
    for (unsigned i=0;i<p->adventure.node_count;++i) {
        BtpEventNode *e=&p->adventure.nodes[i];
        if (e->op==BTP_EVENT_CHI_NATIVE) {
            unsigned k=0;while (k<b->call_count && strcmp(e->text,b->calls[k].id)) ++k;
            if (k==b->call_count) return fail(error,e->id,"unknown native call ID");
            e->argument=k;
        }
        /* Transfers/encounters use quest maps; native maps remain in their
           separate spatial document. End/return restores the original map. */
        if (e->op==BTP_EVENT_FINISH) return fail(error,e->id,"a bridged quest returns to its caller; use return or end, not finish");
    }
    return 1;
}

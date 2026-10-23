#include "data/chi_scripts.h"
#include "data/chi.h"
#include "data/project.h"
#include "core/script.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint16_t size[BTP_BLD_MAX],queue[BTP_BLD_MAX];
    uint8_t covered[BTP_BLD_MAX],seen[BTP_BLD_MAX];
    uint64_t actions;
    uint32_t films;
} Inventory;
typedef struct { const char *name;unsigned code; } Operation;
static const Operation operations[]={
    {"font",0xfe},{"clear",0xfd},{"scene",0xfa},{"text",0xfc},{"add",0xf1},{"set",0xf4},
    {"dispatch",0xf3},{"if",0xf7},{"cursor",0xf0},{"confirm",0xf6},{"native",0xf5},
    {"delay",0xf2},{"animation",0xea},{"wait",0xfb},{"jump",0xf8},{"menu",0xf9},{"end",0xff},
    {"sound",0xe4},{"recruit",0xe9},{"if_person_absent",0xe8},{"if_skill",0xed},
    {"if_advanced_kit",0xeb},{"if_medical_kit",0xec},{"position",0xe6},
    {"add_money",0xe5},{"spend_money",0xee},{"if_money",0xef},{"data",0}
};
static unsigned word(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static int number(BtpJson *j,unsigned n,const char *key,unsigned low,unsigned high,unsigned *out)
{ return btp_json_uint(j,btp_json_field(j,n,key),low,high,out); }
static int string(BtpJson *j,unsigned n,const char *key,char *out,size_t size)
{ return btp_json_string(j,btp_json_field(j,n,key),out,size); }
static int inventory(const BtpBld *b,Inventory *v)
{
    unsigned head=0,tail=1;v->seen[0]=1;
    while (head<tail) {
        unsigned pc=v->queue[head++],op=b->bytes[pc],n=1,targets[130],count=0;
        if (v->covered[pc]) return 0;
        switch (op) {
        case 0xfc:while (pc+n<b->length && b->bytes[pc+n]) ++n;if (pc+n>=b->length) return 0;++n;break;
        case 0xf9:
            if (pc+2>b->length) return 0;
            count=btp_menu_count(b->bytes[pc+1]);if (!count) return 0;n=2+2*count;
            if (pc+n>b->length) return 0;
            for (unsigned i=0;i<count;++i) targets[i]=word(b->bytes+pc+2+2*i);
            break;
        case 0xf3: {
            if (pc+4>b->length) return 0;
            unsigned at=pc+2,first=word(b->bytes+at);
            while (at+2<=first && at+2<=b->length && count<128) {
                unsigned target=word(b->bytes+at);
                if (target<pc+2 || target>=b->length) break;
                targets[count++]=target;if (target<first) first=target;at+=2;
            }
            if (!count) return 0;
            n=at-pc;break;
        }
        case 0xf7:case 0xe8:n=4;break;
        case 0xf6:case 0xf8:case 0xeb:case 0xec:case 0xee:case 0xe5:
        case 0xf0:case 0xf1:case 0xf4:case 0xea:n=3;break;
        case 0xfe:case 0xfa:case 0xf5:case 0xe9:case 0xe4:n=2;break;
        case 0xed:case 0xef:case 0xe6:n=5;break;
        case 0xfd:case 0xfb:case 0xf2:case 0xff:break;
        default:return 0;
        }
        if (pc+n>b->length) return 0;
        for (unsigned i=pc;i<pc+n;++i) { if (v->covered[i]) return 0;v->covered[i]=1; }
        v->size[pc]=(uint16_t)n;
        if (op==0xf5 && b->bytes[pc+1]<=47) v->actions|=UINT64_C(1)<<b->bytes[pc+1];
        if (op==0xea && b->bytes[pc+1]<22) v->films|=1u<<b->bytes[pc+1];
        if (op==0xf7 || op==0xe8) { targets[count++]=word(b->bytes+pc+2);targets[count++]=pc+n; }
        else if (op==0xf6 || op==0xf8 || op==0xeb || op==0xec) {
            targets[count++]=word(b->bytes+pc+1);if (op!=0xf8) targets[count++]=pc+n;
        } else if (op==0xed || op==0xef) { targets[count++]=word(b->bytes+pc+3);targets[count++]=pc+n; }
        else if (!count && op!=0xff) targets[count++]=pc+n;
        for (unsigned i=0;i<count;++i) {
            unsigned target=targets[i];if (target>=b->length) return 0;
            if (!v->seen[target]) { if (tail>=BTP_BLD_MAX) return 0;v->seen[target]=1;v->queue[tail++]=(uint16_t)target; }
        }
    }
    return 1;
}
static int index_of(const BtpChiProgram *p,const char *id)
{ for (unsigned i=0;i<p->count;++i) if (!strcmp(p->nodes[i].id,id)) return (int)i;return -1; }
static int reference(BtpJson *j,unsigned node,const BtpChiProgram *p,unsigned *offset)
{
    char label[64];if (!btp_json_string(j,node,label,sizeof label)) return 0;
    int i=index_of(p,label);
    if (i<0 || p->nodes[i].opcode==0) return btp_json_error(j,node,"branch requires an instruction label, not missing/preserved data");
    *offset=p->nodes[i].offset==UINT16_MAX ? 0u : p->nodes[i].offset;return 1;
}
static int hex_digit(unsigned c)
{ return c>='0' && c<='9' ? (int)c-'0' : c>='a' && c<='f' ? (int)c-'a'+10 : -1; }
static int encode(BtpJson *j,unsigned node,unsigned building,const Inventory *base,const BtpChiProgram *p,
    BtpBld *out,unsigned pc,unsigned *size)
{
    unsigned op=p->nodes[j->nodes[node].index].opcode,a=0,b=0,c=0,n=1;
    uint8_t *bytes=out->bytes+pc;
    if (pc>=BTP_BLD_MAX) return btp_json_error(j,node,"compiled program exceeds 9000 bytes");
    bytes[0]=(uint8_t)op;
    /* Operand readers are shared with the player loader. Encode twice: size
       labels first, then resolve absolute words. Neither pass executes code. */
    switch (op) {
    case 0xfc: {
        unsigned text=btp_json_field(j,node,"text");
        if (!btp_json_type(j,text,'"')) return 0;
        const char *value=j->nodes[text].text;size_t length=strlen(value);
        if (length>4096 || length+2>BTP_BLD_MAX-pc) return btp_json_error(j,text,"text/program byte budget exceeded");
        for (size_t i=0;i<length;++i) if ((unsigned char)value[i]<32 && value[i]!=6 && value[i]!=13 && value[i]!=14 && value[i]!=15)
            return btp_json_error(j,text,"unsupported native text control");
        memcpy(bytes+1,value,length+1);n=(unsigned)length+2;break;
    }
    case 0: {
        unsigned raw=btp_json_field(j,node,"bytes");if (!btp_json_type(j,raw,'"')) return 0;
        const char *text=j->nodes[raw].text;size_t length=strlen(text);
        if (!length || length%2 || length/2>BTP_BLD_MAX-pc) return btp_json_error(j,raw,"preserved data must be nonempty bounded lowercase hex");
        n=(unsigned)length/2;
        for (unsigned i=0;i<n;++i) {
            int hi=hex_digit((unsigned char)text[2*i]),lo=hex_digit((unsigned char)text[2*i+1]);
            if (hi<0 || lo<0) return btp_json_error(j,raw,"preserved data must be lowercase hexadecimal");
            bytes[i]=(uint8_t)(16*hi+lo);
        }break;
    }
    default: {
        unsigned needed=(op==0xed || op==0xef || op==0xe6) ? 5u : (op==0xf7 || op==0xe8) ? 4u :
            (op==0xf1 || op==0xf4 || op==0xf0 || op==0xea || op==0xe5 || op==0xee || op==0xf6 || op==0xf8 || op==0xeb || op==0xec) ? 3u :
            (op==0xfe || op==0xfa || op==0xf5 || op==0xe4 || op==0xe9 || op==0xf3 || op==0xf9) ? 2u : 1u;
        if (BTP_BLD_MAX-pc<needed) return btp_json_error(j,node,"compiled program exceeds 9000 bytes");
        switch (op) {
        case 0xfe:case 0xfa:
            if (!number(j,node,"value",0,6,&a)) return 0;
            if (op==0xfe ? a!=3 && a!=4 && a!=6 : a!=0) return btp_json_error(j,node,"unsupported native font/scene value");
            bytes[1]=(uint8_t)a;n=2;break;
        case 0xf1:case 0xf4:
            if (!number(j,node,"index",0,99,&a) || !number(j,node,"value",0,255,&b)) return 0;
            bytes[1]=(uint8_t)a;bytes[2]=(uint8_t)b;n=3;break;
        case 0xf0:
            if (!number(j,node,"column",0,26,&a) || !number(j,node,"row",0,24,&b)) return 0;
            bytes[1]=(uint8_t)a;bytes[2]=(uint8_t)b;n=3;break;
        case 0xf5:
            if (!number(j,node,"action",1,47,&a)) return 0;
            if (!(base->actions&(UINT64_C(1)<<a))) return btp_json_error(j,node,"native action is not verified in this program context (C4.2 registry)");
            if ((building==1 && ((a==4 && p->nodes[j->nodes[node].index].origin!=0xf03) || (a==5 && p->nodes[j->nodes[node].index].origin!=0xf6a))) ||
                (building==0 && ((a==3 && p->nodes[j->nodes[node].index].origin!=0x1c6b) || (a==43 && p->nodes[j->nodes[node].index].origin!=0x1672))))
                return btp_json_error(j,node,"this native action requires its existing semantic anchor; edit its surrounding source");
            bytes[1]=(uint8_t)a;n=2;break;
        case 0xe4:case 0xe9:
            if (!number(j,node,op==0xe4 ? "program" : "skill",op==0xe4 ? 1u : 0u,op==0xe4 ? 18u : 6u,&a)) return 0;
            if (op==0xe9 && building!=5 && building!=9 && building!=13) return btp_json_error(j,node,"recruit requires repair, hospital or prison context");
            bytes[1]=(uint8_t)a;n=2;break;
        case 0xea:
            if (!number(j,node,"kind",0,21,&a) || !number(j,node,"flags",0,2,&b)) return 0;
            if (!(base->films&(1u<<a))) return btp_json_error(j,node,"film is not verified in this native program context");
            bytes[1]=(uint8_t)a;bytes[2]=(uint8_t)b;n=3;break;
        case 0xe5:case 0xee:case 0xef:
            if (!number(j,node,"amount",0,65535,&a)) return 0;
            bytes[1]=(uint8_t)a;bytes[2]=(uint8_t)(a>>8);n=3;
            if (op==0xef) {
                if (!reference(j,btp_json_field(j,node,"target"),p,&b)) return 0;
                bytes[3]=(uint8_t)b;bytes[4]=(uint8_t)(b>>8);n=5;
            }break;
        case 0xe6:
            if (!number(j,node,"x",0,65535,&a) || !number(j,node,"y",0,65535,&b)) return 0;
            bytes[1]=(uint8_t)a;bytes[2]=(uint8_t)(a>>8);bytes[3]=(uint8_t)b;bytes[4]=(uint8_t)(b>>8);n=5;break;
        case 0xf7:case 0xe8:case 0xed:
            if (!number(j,node,op==0xf7 ? "index" : op==0xe8 ? "person" : "skill",0,op==0xf7 ? 99u : op==0xe8 ? 255u : 6u,&a) ||
                !reference(j,btp_json_field(j,node,"target"),p,&b)) return 0;
            bytes[1]=(uint8_t)a;n=4;
            if (op==0xed) { if (!number(j,node,"minimum",0,255,&c)) return 0;bytes[2]=(uint8_t)c;n=5; }
            bytes[n-2]=(uint8_t)b;bytes[n-1]=(uint8_t)(b>>8);break;
        case 0xf6:case 0xf8:case 0xeb:case 0xec:
            if (!reference(j,btp_json_field(j,node,"target"),p,&a)) return 0;
            bytes[1]=(uint8_t)a;bytes[2]=(uint8_t)(a>>8);n=3;break;
        case 0xf3:case 0xf9: {
            if (!number(j,node,op==0xf3 ? "index" : "menu",0,op==0xf3 ? 99u : 36u,&a)) return 0;
            unsigned count=0,list=btp_json_field(j,node,"targets");if (!btp_json_type(j,list,'[')) return 0;
            bytes[1]=(uint8_t)a;n=2;
            for (unsigned v=j->nodes[list].first;v;v=j->nodes[v].next) {
                if (count>=128 || n+2>BTP_BLD_MAX-pc) return btp_json_error(j,list,"branch table/program limit exceeded");
                if (!reference(j,v,p,&b)) return 0;
                bytes[n++]=(uint8_t)b;bytes[n++]=(uint8_t)(b>>8);++count;
            }
            if (!count || (op==0xf9 && count!=btp_menu_count(a))) return btp_json_error(j,list,"menu needs its native selector's exact destination count");
            break;
        }
        case 0xfd:case 0xf2:case 0xfb:case 0xff:break;
        default:return btp_json_error(j,node,"unsupported BLD opcode");
        }
        break;
    }
    }
    *size=n;return btp_json_done(j,node);
}
static int flow(BtpJson *j,unsigned list,const unsigned *source,BtpChiProgram *p,const BtpBld *b)
{
    /* Never execute preserved/unknown data. Check every potential branch and
       fall-through, even in currently unreachable authored instructions. */
    for (unsigned i=0;i<p->count;++i) {
        BtpChiInstruction *v=&p->nodes[i];unsigned op=v->opcode;
        if (!op || op==0xff || op==0xf8 || op==0xf3 || op==0xf9) continue;
        if (i+1==p->count || !p->nodes[i+1].opcode) return btp_json_error(j,source[i],"instruction falls into preserved data or beyond the program");
    }
    /* Deterministic cycles cannot make progress. Conditional/state loops stay
       native, with the interpreter's existing 256-instruction budget. */
    unsigned *seen=calloc(p->count,sizeof *seen);if (!seen) return btp_json_error(j,list,"cycle-check allocation failed");
    for (unsigned start=0;start<p->count;++start) {
        unsigned i=start,stamp=start+1;
        while (i<p->count) {
            BtpChiInstruction *v=&p->nodes[i];unsigned op=v->opcode;
            if (!op || op==0xff || op==0xfb || op==0xf5 || op==0xea || op==0xe4 || op==0xe9 || op==0xf6 || op==0xf9 ||
                op==0xf3 || op==0xf7 || op==0xe8 || op==0xed || op==0xeb || op==0xec || op==0xef) break;
            if (seen[i]==stamp) { free(seen);return btp_json_error(j,source[i],"non-yielding deterministic cycle; add a wait or a terminating condition"); }
            seen[i]=stamp;
            if (op==0xf8) {
                unsigned target=word(b->bytes+v->offset+1);i=0;
                while (i<p->count && p->nodes[i].offset!=target) ++i;
            } else ++i;
        }
    }
    free(seen);return 1;
}
static int program(BtpJson *j,unsigned object,unsigned slot,BtpChiProgram *p,BtpBld *b)
{
    Inventory *base=calloc(1,sizeof *base);BtpBld *output=calloc(1,sizeof *output);
    unsigned *source=NULL;uint8_t *used=calloc(b->length,1);int ok=0;unsigned value;char resource[64],hash[65],entry[64];
    if (!base || !output || !used) { btp_json_error(j,object,"compiler allocation failed");goto done; }
    if (!inventory(b,base)) { btp_json_error(j,object,"baseline has unsupported/overlapping instructions");goto done; }
    if (!string(j,object,"id",p->id,sizeof p->id) || !btp_content_id(p->id,1) ||
        !string(j,object,"name",p->name,sizeof p->name) || !string(j,object,"resource",resource,sizeof resource) ||
        strcmp(resource,btp_chi_resource_name(27+slot)) || !number(j,object,"building",slot,slot,&value) ||
        !string(j,object,"baseline_sha256",hash,sizeof hash) || !string(j,object,"entry",entry,sizeof entry)) goto done;
    BtpDigest digest;uint8_t bytes[32];char expected[65];btp_digest_start(&digest);btp_digest_add(&digest,b->bytes,b->length);btp_digest_finish(&digest,bytes);
    for (unsigned i=0;i<32;++i) snprintf(expected+2*i,3,"%02x",bytes[i]);
    if (strcmp(expected,hash)) { btp_json_error(j,object,"baseline fingerprint disagrees with this project's immutable BLD");goto done; }
    unsigned list=btp_json_field(j,object,"nodes");if (!btp_json_type(j,list,'[')) goto done;
    for (unsigned n=j->nodes[list].first;n;n=j->nodes[n].next) ++p->count;
    if (!p->count || p->count>BTP_BLD_SOURCE_NODES) { btp_json_error(j,list,"program requires 1..2048 labelled records");goto done; }
    p->nodes=calloc(p->count,sizeof *p->nodes);source=calloc(p->count,sizeof *source);p->original_length=b->length;
    p->offsets=malloc(((size_t)b->length+1)*sizeof *p->offsets);
    p->ends=malloc(((size_t)b->length+1)*sizeof *p->ends);
    if (!p->nodes || !source || !p->offsets || !p->ends) { btp_json_error(j,list,"label allocation failed");goto done; }
    for (unsigned i=0;i<=b->length;++i) p->offsets[i]=p->ends[i]=UINT16_MAX;
    for (unsigned n=j->nodes[list].first;n;n=j->nodes[n].next) {
        unsigned i=j->nodes[n].index;BtpChiInstruction *v=&p->nodes[i];char op[32];source[i]=n;
        v->offset=v->origin=UINT16_MAX;
        if (!string(j,n,"id",v->id,sizeof v->id) || !btp_content_id(v->id,1) || !string(j,n,"op",op,sizeof op)) goto done;
        unsigned k=0;while (k<sizeof operations/sizeof *operations && strcmp(op,operations[k].name)) ++k;
        if (k==sizeof operations/sizeof *operations) { btp_json_error(j,n,"unknown BLD operation");goto done; }v->opcode=(uint8_t)operations[k].code;
        unsigned origin=btp_json_optional(j,n,"origin"),size=btp_json_optional(j,n,"original_size"),note=btp_json_optional(j,n,"note");
        if (note && (!btp_json_type(j,note,'"') || strlen(j->nodes[note].text)>240)) { btp_json_error(j,note,"note exceeds 240 characters");goto done; }
        if (!!origin!=!!size) { btp_json_error(j,n,"original byte range needs origin and original_size");goto done; }
        if (origin) {
            unsigned at,length;
            if (!btp_json_uint(j,origin,0,b->length-1,&at) || !btp_json_uint(j,size,1,b->length,&length) || length>b->length-at) goto done;
            if (v->opcode ? base->size[at]!=length : base->covered[at]) { btp_json_error(j,n,"origin must preserve an original instruction or unreachable data range");goto done; }
            for (unsigned x=at;x<at+length;++x) {
                if (used[x] || (!v->opcode && base->covered[x])) { btp_json_error(j,n,"original ranges overlap or data covers executable instructions");goto done; }used[x]=1;
            }
            v->origin=(uint16_t)at;v->original_size=(uint16_t)length;
        } else if (!v->opcode) { btp_json_error(j,n,"preserved data requires an immutable original byte range");goto done; }
    }
    if (strcmp(p->nodes[0].id,entry) || !p->nodes[0].opcode) { btp_json_error(j,object,"entry must name the first executable record");goto done; }
    for (unsigned i=0;i<p->count;++i) for (unsigned k=0;k<i;++k) if (!strcmp(p->nodes[i].id,p->nodes[k].id)) {
        btp_json_error(j,source[i],"duplicate instruction label");goto done;
    }
    for (unsigned i=0;i<b->length;++i) if (!used[i]) { btp_json_error(j,object,"original byte ranges were removed; preserve their labelled records");goto done; }
    unsigned pc=0;
    for (unsigned i=0;i<p->count;++i) {
        BtpChiInstruction *v=&p->nodes[i];unsigned size;v->offset=(uint16_t)pc;
        if (!encode(j,source[i],slot,base,p,output,pc,&size)) goto done;
        v->length=(uint16_t)size;pc+=size;
        if (!v->opcode && (size!=v->original_size || memcmp(output->bytes+v->offset,b->bytes+v->origin,size))) {
            btp_json_error(j,source[i],"unreachable original bytes must remain byte-identical");goto done;
        }
    }
    for (unsigned i=0;i<p->count;++i) {
        BtpChiInstruction *v=&p->nodes[i];unsigned size;
        if (!encode(j,source[i],slot,base,p,output,v->offset,&size)) goto done;
        if (v->origin==UINT16_MAX) continue;
        unsigned shared=v->length<v->original_size ? v->length : v->original_size;
        for (unsigned k=0;k<shared;++k) p->offsets[v->origin+k]=(uint16_t)(v->offset+k);
        p->offsets[v->origin+v->original_size]=(uint16_t)(v->offset+v->length);
        /* A native resume ends before inserted instructions, while a branch
           to the next old label starts after them. One boundary map cannot
           express both meanings without skipping inserted dialogue. */
        p->ends[v->origin+v->original_size]=(uint16_t)(v->offset+v->length);
    }
    if (!flow(j,list,source,p,output) || !btp_json_done(j,object)) goto done;
    output->length=(uint16_t)pc;output->origin_map=p->offsets;output->origin_ends=p->ends;output->origin_length=b->length;*b=*output;ok=1;
done:free(base);free(output);free(source);free(used);return ok;
}
void btp_chi_scripts_free(BtpChiScripts *s)
{ if (s) { for (unsigned i=0;i<BTP_CHI_PROGRAMS;++i) { free(s->programs[i].nodes);free(s->programs[i].offsets);free(s->programs[i].ends); }free(s); } }
unsigned btp_bld_offset(const BtpBld *b,unsigned original)
{ return b && b->origin_map ? original<=b->origin_length ? b->origin_map[original] : UINT16_MAX : original; }
unsigned btp_bld_after(const BtpBld *b,unsigned original)
{ return b && b->origin_ends ? original<=b->origin_length ? b->origin_ends[original] : UINT16_MAX : original; }
int btp_chi_scripts_load(const char *root,const char *file,BtpChiScripts *s,BtpResources *r,BtpDigest *digest,BtpError *e)
{
    BtpJson j={0};char path[4096],format[64];unsigned version;int ok=0;
    if (!btp_project_path(root,file,path,e) || !btp_json_load_bld_text(&j,path,e->text)) goto done;
    btp_digest_add(digest,j.source_digest,32);
    /* Source bytes alone cannot pin an emitter bug fix. Bind the compiler
       contract and actual compiled payloads into strict saved-game identity. */
    static const char compiler[]="chi-bld-compiler-v1";btp_digest_add(digest,compiler,sizeof compiler-1);
    if (!string(&j,1,"format",format,sizeof format) || strcmp(format,"btp-chi-scripts-v1") || !number(&j,1,"schema_version",1,1,&version)) goto done;
    unsigned list=btp_json_field(&j,1,"programs"),count=0;if (!btp_json_type(&j,list,'[')) goto done;
    for (unsigned n=j.nodes[list].first;n;n=j.nodes[n].next) {
        if (count>=BTP_CHI_PROGRAMS) { btp_json_error(&j,n,"exactly 26 native programs in building order");goto done; }
        if (!program(&j,n,count,&s->programs[count],&r->buildings[count])) goto done;
        BtpDigest payload;uint8_t compiled[32];btp_digest_start(&payload);
        btp_digest_add(&payload,r->buildings[count].bytes,r->buildings[count].length);btp_digest_finish(&payload,compiled);btp_digest_add(digest,compiled,32);
        for (unsigned i=0;i<count;++i) if (!strcmp(s->programs[i].id,s->programs[count].id)) { btp_json_error(&j,n,"duplicate program ID");goto done; }
        ++count;
    }
    if (count!=BTP_CHI_PROGRAMS) { btp_json_error(&j,list,"exactly 26 native programs in building order");goto done; }
    r->training=r->buildings[0];r->citadel=r->buildings[1];r->comstar=r->buildings[2];r->weapon=r->buildings[3];
    r->armor=r->buildings[4];r->repair=r->buildings[5];r->barracks=r->buildings[6];r->lounge=r->buildings[7];
    ok=btp_json_done(&j,1);
done:if (!ok && !e->text[0]) snprintf(e->text,sizeof e->text,"%s: invalid BLD source",file);btp_json_close(&j);return ok;
}

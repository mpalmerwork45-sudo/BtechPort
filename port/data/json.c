#include "data/json.h"
#include "data/digest.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { BYTE_LIMIT=1048576, NODE_LIMIT=60000, DEPTH_LIMIT=24 };
typedef struct { BtpJson *j;char *at,*end; } Reader;
int btp_json_error(BtpJson *j,unsigned node,const char *message)
{
    if (!j->error[0]) {
        unsigned chain[DEPTH_LIMIT+1],count=0;
        for (unsigned n=node;n && count<DEPTH_LIMIT+1;n=j->nodes[n].parent) chain[count++]=n;
        char path[144]="$";size_t at=1;
        while (count && at<sizeof path-1) {
            BtpJsonNode *n=&j->nodes[chain[--count]];
            const char *identity=NULL;
            if (!n->key && n->type=='{') for (unsigned c=n->first;c;c=j->nodes[c].next)
                if (j->nodes[c].key && !strcmp(j->nodes[c].key,"id") && j->nodes[c].type=='"') identity=j->nodes[c].text;
            int wrote=n->key ? snprintf(path+at,sizeof path-at,".%s",n->key) :
                identity ? snprintf(path+at,sizeof path-at,"[%s]",identity) :
                n->parent ? snprintf(path+at,sizeof path-at,"[%u]",n->index) : 0;
            if (wrote<0 || (size_t)wrote>=sizeof path-at) break;
            at+=(size_t)wrote;
        }
        size_t length=strlen(j->file);
        snprintf(j->error,256,"%.72s: %.100s: %.76s",j->file+(length>72 ? length-72 : 0),path,message);
    }
    return 0;
}
static void space(Reader *p) { while (p->at<p->end && strchr(" \r\n\t",*p->at)) ++p->at; }
static char *string(Reader *p,unsigned node)
{
    if (p->at==p->end || *p->at++!='"') { btp_json_error(p->j,node,"expected string");return NULL; }
    char *start=p->at,*out=start;
    while (p->at<p->end && *p->at!='"') {
        unsigned char c=(unsigned char)*p->at++;
        if (c=='\\' && p->at<p->end) {
            c=(unsigned char)*p->at++;
            if (c!='"' && c!='\\' && c!='/') { btp_json_error(p->j,node,"only printable ASCII escapes are supported");return NULL; }
        }
        if (c<32 || c>126) { btp_json_error(p->j,node,"expected printable ASCII");return NULL; }
        *out++=(char)c;
    }
    if (p->at==p->end) { btp_json_error(p->j,node,"unterminated string");return NULL; }
    ++p->at;*out=0;return start;
}
static unsigned value(Reader *p,unsigned parent,unsigned index,char *key,unsigned depth)
{
    BtpJson *j=p->j;
    if (depth>DEPTH_LIMIT || j->count==NODE_LIMIT) return (unsigned)btp_json_error(j,parent,"JSON nesting/node limit exceeded");
    unsigned id=++j->count;BtpJsonNode *n=&j->nodes[id];
    n->parent=parent;n->index=index;n->key=key;space(p);
    if (p->at==p->end) return (unsigned)btp_json_error(j,id,"missing value");
    n->type=(unsigned char)*p->at;
    if (n->type=='"') { n->text=string(p,id);return n->text ? id : 0; }
    if (n->type=='{' || n->type=='[') {
        char end=n->type=='{' ? '}' : ']';++p->at;space(p);unsigned last=0,child_index=0;
        if (p->at<p->end && *p->at==end) { ++p->at;return id; }
        for (;;) {
            char *child_key=NULL;space(p);
            if (n->type=='{') {
                child_key=string(p,id);if (!child_key) return 0;
                for (unsigned i=n->first;i;i=j->nodes[i].next)
                    if (!strcmp(child_key,j->nodes[i].key)) return (unsigned)btp_json_error(j,i,"duplicate field");
                space(p);if (p->at==p->end || *p->at++!=':') return (unsigned)btp_json_error(j,id,"expected colon");
            }
            unsigned child=value(p,id,child_index++,child_key,depth+1);if (!child) return 0;
            if (last) j->nodes[last].next=child;else n->first=child;last=child;
            space(p);if (p->at==p->end) return (unsigned)btp_json_error(j,id,"unterminated container");
            char separator=*p->at++;if (separator==end) break;
            if (separator!=',') return (unsigned)btp_json_error(j,id,"expected comma");
        }
        return id;
    }
    n->type='0';char *start=p->at;uint32_t number=0;
    while (p->at<p->end && *p->at>='0' && *p->at<='9') {
        unsigned digit=(unsigned)(*p->at++-'0');
        if (number>UINT32_MAX/10 || (number==UINT32_MAX/10 && digit>UINT32_MAX%10)) return (unsigned)btp_json_error(j,id,"integer overflow");
        number=number*10+digit;
    }
    if (start==p->at || (p->at-start>1 && *start=='0')) return (unsigned)btp_json_error(j,id,"expected unsigned integer, string, object or array");
    n->number=number;return id;
}
void btp_json_close(BtpJson *j) { free(j->bytes);free(j->nodes);*j=(BtpJson){0}; }
int btp_json_load(BtpJson *j,const char *path,char error[256])
{
    *j=(BtpJson){.file=path,.error=error};error[0]=0;
    FILE *f=fopen(path,"rb");
    if (!f) return btp_json_error(j,0,"cannot open file");
    j->bytes=malloc(BYTE_LIMIT+1);j->nodes=calloc(NODE_LIMIT+1,sizeof *j->nodes);
    if (!j->bytes || !j->nodes) { fclose(f);return btp_json_error(j,0,"allocation failed"); }
    size_t size=fread(j->bytes,1,BYTE_LIMIT+1,f);int bad=ferror(f);if (fclose(f)) bad=1;
    if (bad || size>BYTE_LIMIT) return btp_json_error(j,0,"cannot read file (limit 1 MiB)");
    if (memchr(j->bytes,0,size)) return btp_json_error(j,0,"embedded NUL");
    BtpDigest digest;btp_digest_start(&digest);btp_digest_add(&digest,j->bytes,size);btp_digest_finish(&digest,j->source_digest);
    Reader p={j,j->bytes,j->bytes+size};
    if (!value(&p,0,0,NULL,0)) return 0;
    space(&p);return p.at==p.end || btp_json_error(j,1,"trailing data");
}
int btp_json_type(BtpJson *j,unsigned n,char type)
{
    return (n && j->nodes[n].type==(unsigned char)type) || btp_json_error(j,n,"missing field or wrong value type");
}
unsigned btp_json_field(BtpJson *j,unsigned object,const char *key)
{
    if (!btp_json_type(j,object,'{')) return 0;
    for (unsigned i=j->nodes[object].first;i;i=j->nodes[i].next)
        if (!strcmp(j->nodes[i].key,key)) { j->nodes[i].used=1;return i; }
    char message[96];snprintf(message,sizeof message,"missing field: %s",key);btp_json_error(j,object,message);return 0;
}
int btp_json_done(BtpJson *j,unsigned object)
{
    if (!btp_json_type(j,object,'{')) return 0;
    for (unsigned i=j->nodes[object].first;i;i=j->nodes[i].next)
        if (!j->nodes[i].used) return btp_json_error(j,i,"unknown/unsupported field");
    return 1;
}
int btp_json_string(BtpJson *j,unsigned n,char *out,size_t capacity)
{
    if (!btp_json_type(j,n,'"')) return 0;
    size_t length=strlen(j->nodes[n].text);
    if (!length || length>=capacity) return btp_json_error(j,n,"string empty or exceeds field length");
    memcpy(out,j->nodes[n].text,length+1);return 1;
}
int btp_json_uint(BtpJson *j,unsigned n,unsigned low,unsigned high,unsigned *out)
{
    if (!btp_json_type(j,n,'0')) return 0;
    unsigned v=j->nodes[n].number;
    if (v<low || v>high) return btp_json_error(j,n,"integer outside supported range");
    *out=v;return 1;
}
int btp_content_id(const char *s,int namespaced)
{
    unsigned colons=0;if (*s<'a' || *s>'z') return 0;
    for (;*s;++s) {
        if (*s==':') { ++colons;if (s[1]<'a' || s[1]>'z') return 0; }
        else if (!(*s>='a' && *s<='z') && !(*s>='0' && *s<='9') && *s!='-' && *s!='_' && *s!='.') return 0;
    }
    return colons==(unsigned)namespaced;
}

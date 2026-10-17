#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "data/project.h"
#include "data/json.h"
#include "data/digest.h"
#include "data/anm.h"
#include "data/file.h"
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#define make_directory(p) _mkdir(p)
#else
#define make_directory(p) mkdir(p,0700)
#endif

static int fail(BtpError *e,const char *path,const char *why) { if (e) snprintf(e->text,sizeof e->text,"%.150s: %.100s",path,why);return 0; }
int btp_project_path(const char *root,const char *relative,char out[4096],BtpError *e)
{
    /* Package paths are portable and confined to real child entries. Reject
       traversal, case mismatches and symlink/reparse escapes on both systems.
       The root itself is supplied explicitly by the caller and is trusted. */
    if (!relative || !*relative || strlen(relative)>1023 || strlen(root)>3000) return fail(e,root,"invalid project-relative path");
    snprintf(out,4096,"%s",root);const char *p=relative;
    while (*p) {
        char leaf[256];size_t n=0;
        while (*p && *p!='/') {
            unsigned c=(unsigned char)*p++;
            if (n==255 || c<32 || c>126 || strchr("\\:*?\"<>|",(int)c)) return fail(e,relative,"unsupported portable path");
            leaf[n++]=(char)c;
        }
        leaf[n]=0;
        if (!n || !strcmp(leaf,".") || !strcmp(leaf,"..") || leaf[n-1]=='.' || leaf[n-1]==' ') return fail(e,relative,"invalid path component");
        char upper[256];for (size_t i=0;i<=n;++i) upper[i]=leaf[i]>='a' && leaf[i]<='z' ? (char)(leaf[i]-'a'+'A') : leaf[i];
        char *dot=strchr(upper,'.');if (dot) *dot=0;
        if (!strcmp(upper,"CON") || !strcmp(upper,"PRN") || !strcmp(upper,"AUX") || !strcmp(upper,"NUL") ||
            ((!strncmp(upper,"COM",3) || !strncmp(upper,"LPT",3)) && upper[3]>='1' && upper[3]<='9' && !upper[4])) return fail(e,relative,"reserved Windows filename");
        DIR *dir=opendir(out);if (!dir) return fail(e,relative,"cannot open parent directory");
        struct dirent *entry;int found=0;while ((entry=readdir(dir))) if (!strcmp(entry->d_name,leaf)) { found=1;break; }closedir(dir);
        if (!found) return fail(e,relative,"missing reference (filenames are case-sensitive)");
        size_t len=strlen(out);if (len+n+2>=4096) return fail(e,relative,"path too long");out[len++]='/';memcpy(out+len,leaf,n+1);
        struct stat info;
#ifdef _WIN32
        DWORD attributes=GetFileAttributesA(out);
        if (attributes==INVALID_FILE_ATTRIBUTES || (attributes&FILE_ATTRIBUTE_REPARSE_POINT) || stat(out,&info)) return fail(e,relative,"invalid/reparse reference");
#else
        if (lstat(out,&info) || S_ISLNK(info.st_mode)) return fail(e,relative,"invalid/symlink reference");
#endif
        if (*p) { if (!S_ISDIR(info.st_mode) || !*++p) return fail(e,relative,"expected directory followed by file"); }
        else if (!S_ISREG(info.st_mode)) return fail(e,relative,"reference is not a regular file");
    }
    return 1;
}
static int text(BtpJson *j,unsigned obj,const char *key,char *out,size_t n) { return btp_json_string(j,btp_json_field(j,obj,key),out,n); }
static int expected(BtpJson *j,unsigned obj,const char *key,const char *want)
{
    char v[96];unsigned node=btp_json_field(j,obj,key);
    return btp_json_string(j,node,v,sizeof v) && (!strcmp(v,want) || btp_json_error(j,node,"unsupported project option"));
}
BtpProject *btp_project_load(const char *root,BtpRoster *roster,BtpPortraits *portraits,BtpError *error)
{
    BtpError ignored;if (!error) error=&ignored;
    BtpProject *p=calloc(1,sizeof *p);BtpRoster *r=calloc(1,sizeof *r);BtpPortraits *art=calloc(1,sizeof *art);
    BtpJson j={0};BtpDigest digest;btp_digest_start(&digest);char path[4096],manifest_path[4096],relative[1024];unsigned v;int ok=0;
    if (!p || !r || !art) { fail(error,root,"project allocation failed");goto done; }
    if (!btp_project_path(root,"project.json",manifest_path,error) || !btp_json_load(&j,manifest_path,error->text)) goto done;
    btp_digest_add(&digest,j.source_digest,32);
    if (!expected(&j,1,"format","btp-project-v1") || !btp_json_uint(&j,btp_json_field(&j,1,"schema_version"),1,1,&v) ||
        !text(&j,1,"package_id",p->id,sizeof p->id) || !text(&j,1,"content_version",p->version,sizeof p->version) ||
        !text(&j,1,"title",p->title,sizeof p->title) || !expected(&j,1,"requires","chi-original-dos-1.03") ||
        !expected(&j,1,"save_policy","strict-content-v1") ||
        !text(&j,1,"definitions",relative,sizeof relative)) goto done;
    if (!btp_project_path(root,relative,path,error) || !btp_definitions_load(path,&p->definitions,error->text)) goto done;
    btp_digest_add(&digest,p->definitions.source_digest,32);
    if (strcmp(p->id,p->definitions.id) || strcmp(p->version,p->definitions.version)) { fail(error,"project.json","package ID/version disagrees with definitions");goto done; }
    if (!expected(&j,1,"rules_profile",p->definitions.rules.fingerprint ? "chi:updated-lrm-v1" : "chi:legacy-v1")) goto done;
    char startup[64];if (!text(&j,1,"startup",startup,sizeof startup)) goto done;
    unsigned adventure=btp_json_optional(&j,1,"adventure");
    if (adventure) {
        if (strcmp(startup,"authored-adventure-v1")) { btp_json_error(&j,adventure,"adventure requires startup authored-adventure-v1");goto done; }
        if (!btp_json_string(&j,adventure,relative,sizeof relative) || !btp_project_path(root,relative,path,error) ||
            !btp_adventure_load(path,&p->definitions,&p->adventure,error->text)) goto done;
        btp_digest_add(&digest,p->adventure.source_digest,32);
    } else if (strcmp(startup,"chi-training-v1")) { btp_json_error(&j,1,"unsupported startup or missing adventure");goto done; }
    unsigned assets=btp_json_field(&j,1,"assets"),seen=0;
    if (!btp_json_type(&j,assets,'[')) goto done;
    const char *const slots[]={"broker","training","lounge","prison","inventor","cinema","hospital","comstar","clothes","video-hut","mayor"};
    char ids[BTP_PORTRAIT_COUNT][64]={{0}};unsigned count=0;
    for (unsigned n=j.nodes[assets].first;n;n=j.nodes[n].next) {
        char slot[32],identity[64];
        if (!text(&j,n,"id",identity,sizeof identity) || !text(&j,n,"slot",slot,sizeof slot) || !text(&j,n,"file",relative,sizeof relative) || !btp_json_done(&j,n)) goto done;
        unsigned i=0;while (i<BTP_PORTRAIT_COUNT && strcmp(slots[i],slot)) ++i;
        if (!btp_content_id(identity,1) || i==BTP_PORTRAIT_COUNT || (seen&(1u<<i))) { btp_json_error(&j,n,"unsupported or duplicate portrait slot/ID");goto done; }
        for (unsigned k=0;k<count;++k) if (!strcmp(ids[k],identity)) { btp_json_error(&j,n,"duplicate asset ID");goto done; }
        strcpy(ids[count++],identity);seen|=1u<<i;
        if (!btp_project_path(root,relative,path,error)) goto done;
        /* Hash the bytes we actually decode. Reopening files for hashing can
           bind a save to a different edit when an editor writes during load. */
        uint8_t bytes[BTP_ANM_BYTES+1];FILE *file=fopen(path,"rb");
        if (!file) { fail(error,relative,"cannot open portrait");goto done; }
        size_t length=fread(bytes,1,sizeof bytes,file);int bad=ferror(file);if (fclose(file)) bad=1;
        if (bad) { fail(error,relative,"cannot read portrait");goto done; }
        BtpDigest asset;uint8_t asset_digest[32];btp_digest_start(&asset);btp_digest_add(&asset,bytes,length);btp_digest_finish(&asset,asset_digest);btp_digest_add(&digest,asset_digest,32);
        int decoded=btp_anm_decode(bytes,length,&art->image[i],error);
        if (!decoded) { char detail[256];snprintf(detail,sizeof detail,"%s",error->text);fail(error,relative,detail);goto done; }
    }
    if (!btp_json_done(&j,1) || !btp_definitions_compile(&p->definitions,r,error->text)) goto done;
    btp_digest_finish(&digest,p->digest);*roster=*r;*portraits=*art;ok=1;
done:
    btp_json_close(&j);free(r);free(art);
    if (!ok) { free(p);return NULL; }
    return p;
}
int btp_project_export_manifest(const char *root,const char *id,const char *version,
    const BtpCombatProfile *rules,const BtpPortraits *portraits,BtpError *e)
{
    char path[4096];int n=snprintf(path,sizeof path,"%s/project.json",root);
    if (n<0 || (size_t)n>=sizeof path) return fail(e,root,"export path too long");
    FILE *f=btp_file_create(path);if (!f) return fail(e,path,"cannot create manifest");
    fprintf(f,"{\n  \"format\": \"btp-project-v1\",\n  \"schema_version\": 1,\n  \"package_id\": \"%s\",\n  \"content_version\": \"%s\",\n  \"title\": \"Editable BTECH CHI\",\n  \"requires\": \"chi-original-dos-1.03\",\n  \"startup\": \"chi-training-v1\",\n  \"rules_profile\": \"chi:%s-v1\",\n  \"save_policy\": \"strict-content-v1\",\n  \"definitions\": \"content.json\",\n  \"assets\": [",id,version,rules->fingerprint ? "updated-lrm" : "legacy");
    const char *const slots[]={"broker","training","lounge","prison","inventor","cinema","hospital","comstar","clothes","video-hut","mayor"};unsigned count=0;
    for (unsigned i=0;i<BTP_PORTRAIT_COUNT;++i) if (portraits && portraits->image[i].count) {
        if (!count) { snprintf(path,sizeof path,"%s/art",root);if (make_directory(path)) { fclose(f);return fail(e,path,"cannot create art directory"); } }
        snprintf(path,sizeof path,"%s/art/%s.anm",root,slots[i]);FILE *image=btp_file_create(path);
        if (!image) { fclose(f);return fail(e,path,"cannot create portrait"); }
        const BtpAnm *anm=&portraits->image[i];int written=fwrite(anm->bytes,1,anm->length,image)==anm->length;
        if (fclose(image)) written=0;
        if (!written) { fclose(f);return fail(e,path,"cannot write portrait"); }
        fprintf(f,"%s\n    {\"id\": \"%s:portrait-%s\", \"slot\": \"%s\", \"file\": \"art/%s.anm\"}",count++ ? "," : "",id,slots[i],slots[i],slots[i]);
    }
    fputs("\n  ]\n}\n",f);
    int ok=!ferror(f);if (fclose(f)) ok=0;return ok || fail(e,path,"cannot write manifest");
}

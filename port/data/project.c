#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "data/project.h"
#include "data/chi_presentation.h"
#include "data/chi.h"
#include "data/json.h"
#include "data/digest.h"
#include "data/anm.h"
#include "data/file.h"
#include "core/lua_events.h"
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#define make_directory(p) btp_file_mkdir(p)
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
#ifndef _WIN32
        DIR *dir=opendir(out);if (!dir) return fail(e,relative,"cannot open parent directory");
        struct dirent *entry;int found=0;while ((entry=readdir(dir))) if (!strcmp(entry->d_name,leaf)) { found=1;break; }closedir(dir);
        if (!found) return fail(e,relative,"missing reference (filenames are case-sensitive)");
#endif
        size_t len=strlen(out);if (len+n+2>=4096) return fail(e,relative,"path too long");out[len++]='/';memcpy(out+len,leaf,n+1);
#ifdef _WIN32
        int kind=btp_file_entry(out,leaf);
        if(!kind)return fail(e,relative,"missing, case-mismatched or reparse reference");
        if(*p) { if(kind!=2 || !*++p)return fail(e,relative,"expected directory followed by file"); }
        else if(kind!=1)return fail(e,relative,"reference is not a regular file");
#else
        struct stat info;
        if (lstat(out,&info) || S_ISLNK(info.st_mode)) return fail(e,relative,"invalid/symlink reference");
        if (*p) { if (!S_ISDIR(info.st_mode) || !*++p) return fail(e,relative,"expected directory followed by file"); }
        else if (!S_ISREG(info.st_mode)) return fail(e,relative,"reference is not a regular file");
#endif
    }
    return 1;
}
static int text(BtpJson *j,unsigned obj,const char *key,char *out,size_t n) { return btp_json_string(j,btp_json_field(j,obj,key),out,n); }
static int expected(BtpJson *j,unsigned obj,const char *key,const char *want)
{
    char v[96];unsigned node=btp_json_field(j,obj,key);
    return btp_json_string(j,node,v,sizeof v) && (!strcmp(v,want) || btp_json_error(j,node,"unsupported project option"));
}
void btp_project_free(BtpProject *p)
{ if (p) { free(p->chi_resources);free(p->chi_spatial);free(p->chi_services);free(p->chi_missions);free(p->chi_bridge);btp_chi_scripts_free(p->chi_scripts);free(p); } }
BtpProject *btp_project_load(const char *root,BtpRoster *roster,BtpPortraits *portraits,BtpError *error)
{
    BtpError ignored;if (!error) error=&ignored;
    BtpProject *p=calloc(1,sizeof *p);BtpRoster *r=calloc(1,sizeof *r);BtpPortraits *art=calloc(1,sizeof *art);
    BtpJson j={0};BtpDigest digest;btp_digest_start(&digest);char path[4096],manifest_path[4096],relative[1024];unsigned v;int ok=0;
    if (!p || !r || !art) { fail(error,root,"project allocation failed");goto done; }
    if (!btp_project_path(root,"project.json",manifest_path,error) || !btp_json_load(&j,manifest_path,error->text)) goto done;
    btp_digest_add(&digest,j.source_digest,32);
    char requires[64];
    if (!expected(&j,1,"format","btp-project-v1") || !btp_json_uint(&j,btp_json_field(&j,1,"schema_version"),1,1,&v) ||
        !text(&j,1,"package_id",p->id,sizeof p->id) || !text(&j,1,"content_version",p->version,sizeof p->version) ||
        !text(&j,1,"title",p->title,sizeof p->title) || !text(&j,1,"requires",requires,sizeof requires) ||
        !expected(&j,1,"save_policy","strict-content-v1") ||
        !text(&j,1,"definitions",relative,sizeof relative)) goto done;
    int independent=!strcmp(requires,"none"),imported=!strcmp(requires,"chi-local-dos-1.03");
    if (!independent && !imported && strcmp(requires,"chi-original-dos-1.03")) { fail(error,"project.json","unsupported dependency");goto done; }
    if (!btp_project_path(root,relative,path,error) ||
        !(imported ? btp_definitions_load_chi(path,&p->definitions,error->text) : btp_definitions_load(path,&p->definitions,error->text))) goto done;
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
    } else if (strcmp(startup,imported ? "chi-import-v1" : "chi-training-v1")) { btp_json_error(&j,1,"unsupported startup or missing adventure");goto done; }
    if (imported) {
        if (adventure) { fail(error,"project.json","CHI import cannot enable authored events");goto done; }
        p->chi_resources=btp_chi_project_load(root,&j,&digest,&p->chi_edition,error);
        if (!p->chi_resources) goto done;
        unsigned bridge=btp_json_optional(&j,1,"chi_bridge"),events=btp_json_optional(&j,1,"chi_events");
        if (!!bridge!=!!events) { fail(error,"project.json","chi_bridge and chi_events must be enabled together");goto done; }
        if (bridge) {
            p->chi_bridge=calloc(1,sizeof *p->chi_bridge);
            if (!p->chi_bridge || !btp_json_string(&j,events,relative,sizeof relative) || strcmp(relative,"chi-events.json") ||
                !btp_project_path(root,relative,path,error) || !btp_adventure_load(path,&p->definitions,&p->adventure,error->text)) goto done;
            btp_digest_add(&digest,p->adventure.source_digest,32);
            if (!btp_json_string(&j,bridge,relative,sizeof relative) || strcmp(relative,"chi-bridge.json") ||
                !btp_chi_bridge_load(root,relative,p,&digest,error)) goto done;
        }
        unsigned services=btp_json_optional(&j,1,"chi_services");
        if (services) {
            p->chi_services=calloc(1,sizeof *p->chi_services);
            if (!btp_json_string(&j,services,relative,sizeof relative)) goto done;
            if (strcmp(relative,"chi-services.json")) { btp_json_error(&j,services,"expected chi-services.json");goto done; }
            if (!p->chi_services || !btp_chi_services_load(root,relative,p->chi_services,p->chi_resources,&digest,error)) goto done;
        }
        unsigned missions=btp_json_optional(&j,1,"chi_missions");
        if (missions) {
            p->chi_missions=calloc(1,sizeof *p->chi_missions);
            if (!btp_json_string(&j,missions,relative,sizeof relative)) goto done;
            if (strcmp(relative,"chi-missions.json")) { btp_json_error(&j,missions,"expected chi-missions.json");goto done; }
            if (!p->chi_missions || !btp_chi_missions_load(root,relative,p->chi_missions,p->chi_resources,&digest,error)) goto done;
        }
        p->chi_resources->project=p;
        if (!btp_chi_service_dialogue(p->chi_resources,error)) goto done;
        unsigned programs=btp_json_optional(&j,1,"chi_scripts");
        if (programs) {
            p->chi_scripts=calloc(1,sizeof *p->chi_scripts);
            if (!btp_json_string(&j,programs,relative,sizeof relative)) goto done;
            if (strcmp(relative,"chi-scripts.json")) { btp_json_error(&j,programs,"expected chi-scripts.json");goto done; }
            if (!p->chi_scripts || !btp_chi_scripts_load(root,relative,p->chi_scripts,p->chi_resources,&digest,error)) goto done;
        }
        unsigned spatial=btp_json_optional(&j,1,"chi_spatial");
        if (spatial) {
            p->chi_spatial=calloc(1,sizeof *p->chi_spatial);
            if (!btp_json_string(&j,spatial,relative,sizeof relative)) goto done;
            if (strcmp(relative,"chi-spatial.json")) { btp_json_error(&j,spatial,"expected chi-spatial.json");goto done; }
            if (!p->chi_spatial ||
                !btp_chi_spatial_load(root,relative,p->chi_spatial,p->chi_resources,&digest,error)) goto done;
        }
        if ((p->chi_edition==1 && p->definitions.rules.fingerprint) ||
            (p->chi_edition==2 && !p->definitions.rules.fingerprint)) { fail(error,"campaign.json","edition and rules disagree");goto done; }
    }
    unsigned presentation=btp_json_optional(&j,1,"presentation");
    if (independent) {
        if (!adventure || !presentation || !btp_json_string(&j,presentation,relative,sizeof relative) ||
            !btp_project_path(root,relative,path,error) || !btp_independent_load(path,&p->independent,error->text)) { if (!*error->text) fail(error,"project.json","independent games require an adventure and presentation");goto done; }
        btp_digest_add(&digest,p->independent.source_digest,32);
        for (unsigned i=0;i<p->adventure.tile_count;++i) if (p->adventure.tiles[i].sheet!=3 &&
            (p->adventure.tiles[i].sheet!=2 || p->adventure.tiles[i].graphic>=p->independent.tile_count)) { fail(error,"adventure.json","independent tiles must reference declared package graphics");goto done; }
        for (unsigned i=0;i<p->adventure.person_count;++i) if (!*p->adventure.people[i].name) { fail(error,"adventure.json","independent characters require display names");goto done; }
        for (unsigned i=0;i<p->definitions.presentation_count;++i) if (!p->definitions.presentations[i].independent) { fail(error,"content.json","independent games require package sprite sources");goto done; }
    } else if (presentation) { fail(error,"project.json","presentation is only supported by independent games");goto done; }
    if (!independent) {
        for (unsigned i=0;i<p->definitions.presentation_count;++i) if (p->definitions.presentations[i].independent==1) { fail(error,"content.json","package sprites require an independent presentation");goto done; }
        for (unsigned i=0;i<p->adventure.tile_count;++i) if (p->adventure.tiles[i].sheet==2) { fail(error,"adventure.json","package tiles require an independent presentation");goto done; }
    }
    unsigned graphics=btp_json_optional(&j,1,"graphics");
    if (graphics) {
        if ((!adventure && !imported) || !btp_json_string(&j,graphics,relative,sizeof relative) || !btp_project_path(root,relative,path,error) ||
            !btp_art_load(path,&p->graphics,error->text)) goto done;
        btp_digest_add(&digest,p->graphics.source_digest,32);
    }
    if (p->chi_spatial) for (unsigned i=0;i<p->chi_spatial->tile_count;++i) {
        BtpChiTile *t=&p->chi_spatial->tiles[i];if (t->sheet!=4) continue;
        unsigned im=btp_art_find(&p->graphics,t->image);
        if (im==BTP_ART_NONE || p->graphics.images[im].kind!=0) { fail(error,t->id,"CHI tile requires a declared tile image");goto done; }
        t->graphic=(uint16_t)im;
    }
    unsigned chi_art=btp_json_optional(&j,1,"chi_presentation");
    for (unsigned i=0;i<p->adventure.person_count;++i) {
        BtpScenePerson *person=&p->adventure.people[i];if (!*person->image) continue;
        unsigned im=btp_art_find(&p->graphics,person->image);
        if (im==BTP_ART_NONE || p->graphics.images[im].kind!=1) { fail(error,person->id,"person requires a sprite image");goto done; }
        person->graphic=(uint16_t)im;
    }
    for (unsigned i=0;i<p->definitions.presentation_count;++i) {
        BtpPresentationDefinition *sprite=&p->definitions.presentations[i];
        if (sprite->independent!=2) continue;
        sprite->graphic=btp_art_find(&p->graphics,sprite->image);
        if (sprite->graphic==BTP_ART_NONE || p->graphics.images[sprite->graphic].kind!=1) { fail(error,sprite->id,"unit presentation requires a sprite image");goto done; }
    }
    for (unsigned i=0;i<p->adventure.tile_count;++i) {
        BtpSceneTile *t=&p->adventure.tiles[i];if (t->sheet!=3) continue;
        unsigned im=btp_art_find(&p->graphics,t->image);
        if (im==BTP_ART_NONE || p->graphics.images[im].kind!=0) { fail(error,t->id,"tile references a missing/non-tile graphic");goto done; }
        t->graphic=(uint16_t)im;
    }
    for (unsigned i=0;i<p->adventure.map_count;++i) for (unsigned k=0;k<p->adventure.maps[i].entrance_count;++k) {
        BtpSceneEntrance *door=&p->adventure.maps[i].entrances[k];if (!*door->image) continue;
        unsigned im=btp_art_find(&p->graphics,door->image);
        if (im==BTP_ART_NONE || p->graphics.images[im].width>64 || p->graphics.images[im].height>64) { fail(error,door->id,"entrance icon missing or larger than 64x64");goto done; }
        door->icon=(uint16_t)im;
    }
    for (unsigned i=0;i<p->adventure.node_count;++i) {
        BtpEventNode *e=&p->adventure.nodes[i];if (!*e->image) continue;
        unsigned im=btp_art_find(&p->graphics,e->image);
        if (im==BTP_ART_NONE || (e->op!=BTP_EVENT_PICTURE && (p->graphics.images[im].width>88 || p->graphics.images[im].height>88))) { fail(error,e->id,"event image missing or larger than its 88x88 portrait panel");goto done; }
        e->picture=(uint16_t)im;
    }
    unsigned scripts=btp_json_optional(&j,1,"scripts");
    if (scripts) {
        if (!btp_json_type(&j,scripts,'[')) goto done;
        for (unsigned n=j.nodes[scripts].first;n;n=j.nodes[n].next) {
            if (p->script_count==BTP_LUA_SCRIPTS) { btp_json_error(&j,n,"at most sixteen Lua scripts");goto done; }
            BtpLuaScript *script=&p->scripts[p->script_count];
            if (!text(&j,n,"id",script->id,sizeof script->id) || !btp_content_id(script->id,1) || !text(&j,n,"file",relative,sizeof relative) || !btp_json_done(&j,n)) goto done;
            for (unsigned k=0;k<p->script_count;++k) if (!strcmp(script->id,p->scripts[k].id)) { btp_json_error(&j,n,"duplicate script ID");goto done; }
            if (!btp_project_path(root,relative,path,error)) goto done;
            FILE *f=btp_fopen(path,"rb");if (!f) { fail(error,relative,"cannot open Lua source");goto done; }
            script->length=fread(script->source,1,sizeof script->source,f);int bad=ferror(f);if (fclose(f)) bad=1;
            if (bad || !script->length || script->length>BTP_LUA_SOURCE || memchr(script->source,0,script->length)) { fail(error,relative,"Lua source must be 1..8192 bytes of text");goto done; }
            if (!btp_lua_compile(script->source,script->length,error->text)) goto done;
            BtpDigest hash;uint8_t bytes[32];btp_digest_start(&hash);btp_digest_add(&hash,script->source,script->length);btp_digest_finish(&hash,bytes);btp_digest_add(&digest,bytes,32);++p->script_count;
        }
    }
    for (unsigned i=0;i<p->adventure.node_count;++i) if (p->adventure.nodes[i].op==BTP_EVENT_LUA) {
        BtpEventNode *node=&p->adventure.nodes[i];unsigned k=0;
        while (k<p->script_count && strcmp(node->text,p->scripts[k].id)) ++k;
        if (k==p->script_count) { fail(error,node->id,"unresolved Lua script ID");goto done; }node->argument=k;
    }
    unsigned assets=btp_json_field(&j,1,"assets"),seen=0;
    if (!btp_json_type(&j,assets,'[')) goto done;
    const char *const slots[]={"broker","training","lounge","prison","inventor","cinema","hospital","comstar","clothes","video-hut","mayor"};
    char ids[BTP_PORTRAIT_COUNT][64]={{0}};unsigned count=0;
    for (unsigned n=j.nodes[assets].first;n;n=j.nodes[n].next) {
        if (independent) { btp_json_error(&j,n,"independent portraits belong in the presentation file");goto done; }
        char slot[32],identity[64];
        if (!text(&j,n,"id",identity,sizeof identity) || !text(&j,n,"slot",slot,sizeof slot) || !text(&j,n,"file",relative,sizeof relative) || !btp_json_done(&j,n)) goto done;
        unsigned i=0;while (i<BTP_PORTRAIT_COUNT && strcmp(slots[i],slot)) ++i;
        if (!btp_content_id(identity,1) || i==BTP_PORTRAIT_COUNT || (seen&(1u<<i))) { btp_json_error(&j,n,"unsupported or duplicate portrait slot/ID");goto done; }
        for (unsigned k=0;k<count;++k) if (!strcmp(ids[k],identity)) { btp_json_error(&j,n,"duplicate asset ID");goto done; }
        strcpy(ids[count++],identity);seen|=1u<<i;
        if (!btp_project_path(root,relative,path,error)) goto done;
        /* Hash the bytes we actually decode. Reopening files for hashing can
           bind a save to a different edit when an editor writes during load. */
        uint8_t bytes[BTP_ANM_BYTES+1];FILE *file=btp_fopen(path,"rb");
        if (!file) { fail(error,relative,"cannot open portrait");goto done; }
        size_t length=fread(bytes,1,sizeof bytes,file);int bad=ferror(file);if (fclose(file)) bad=1;
        if (bad) { fail(error,relative,"cannot read portrait");goto done; }
        BtpDigest asset;uint8_t asset_digest[32];btp_digest_start(&asset);btp_digest_add(&asset,bytes,length);btp_digest_finish(&asset,asset_digest);btp_digest_add(&digest,asset_digest,32);
        int decoded=btp_anm_decode(bytes,length,&art->image[i],error);
        if (!decoded) { char detail[256];snprintf(detail,sizeof detail,"%s",error->text);fail(error,relative,detail);goto done; }
    }
    if (independent) for (unsigned i=0;i<p->adventure.node_count;++i) if (p->adventure.nodes[i].portrait>2) { fail(error,p->adventure.nodes[i].id,"independent profile supports none/broker/training portraits");goto done; }
    if (chi_art) {
        if (!imported || !btp_json_string(&j,chi_art,relative,sizeof relative)) goto done;
        if (strcmp(relative,"chi-presentation.json")) { btp_json_error(&j,chi_art,"expected chi-presentation.json");goto done; }
        if (!btp_chi_presentation_load(root,relative,p,art,&digest,error)) goto done;
    }
    if (!btp_json_done(&j,1) || !btp_definitions_compile(&p->definitions,r,error->text) || !btp_chi_bridge_resolve(p,error)) goto done;
    if (!btp_chi_services_stock(p->chi_services,r,error)) goto done;
    if (!btp_chi_missions_resolve(p->chi_missions,p->chi_resources,r,error)) goto done;
    btp_digest_finish(&digest,p->digest);*roster=*r;*portraits=*art;ok=1;
done:
    btp_json_close(&j);free(r);free(art);
    if (!ok) { btp_project_free(p);return NULL; }
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

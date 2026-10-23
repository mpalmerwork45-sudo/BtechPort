#include "data/chi.h"
#include "data/project.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *const names[BTP_CHI_FILES]={
    "MAP1.MTP","MAP2.MTP","MAP3.MTP","MAP4.MTP","MAP5.MTP","MAP6.MTP","MAP7.MTP",
    "MAP8.MTP","MAP9.MTP","MAP10.MTP","MAP11.MTP","MAP12.MTP","MAP13.MTP","MAP14.MTP","MAP15.MTP",
    "BTTLTECH.ICN","MECHSHAP.CMP","BTSTATS.CMP","BTBORDER.CMP","ANIMATE.ICN","BTTITLE.CMP",
    "INFOCOM.CMP","TINYLAND.CMP","STARLEAG.ICN","MAP.ICN","ENDMECH.CMP","DESTRUCT.ICN",
    "TRAINING.BLD","CITADEL.BLD","COMSTAR.BLD","WEAPON.BLD","ARMOR.BLD","REPAIR.BLD",
    "BARRACKS.BLD","LOUNGE.BLD","GARAGE.BLD","HOSPITAL.BLD","ARENA.BLD","PARTY.BLD",
    "CLOTHES.BLD","JAIL.BLD","MAYOR.BLD","WEAPON2.BLD","THEATER.BLD","FROB.BLD",
    "VIEWDISK.BLD","BARRACK2.BLD","ENTRANCE.BLD","HUT.BLD","ENDMECH.BLD","INSTRUCT.BLD","FINDIT.BLD","WINSCENE.BLD",
    "O0.ANM","O1.ANM","O2.ANM","O3.ANM","O4.ANM","O5.ANM","O6.ANM","O7.ANM","O8.ANM",
    "O9.ANM","O10.ANM","O11.ANM","O12.ANM","O13.ANM","O14.ANM","O15.ANM","O16.ANM",
    "O17.ANM","O18.ANM","O19.ANM","O20.ANM","O21.ANM","WWOODBT.SIF",
    "talk-data.bin","combat-data.bin","world-data.bin"
};
typedef struct { uint8_t *bytes[BTP_CHI_FILES];size_t size[BTP_CHI_FILES]; } Files;
const char *btp_chi_resource_name(unsigned i) { return i<BTP_CHI_FILES ? names[i] : NULL; }
static int fail(BtpError *e,const char *why) { snprintf(e->text,sizeof e->text,"CHI import: %s",why);return 0; }
static int copy_read(void *context,const char *path,uint8_t **bytes,size_t *size,BtpError *e)
{
    Files *files=context;while (*path=='/') ++path;
    unsigned i=0;while (i<BTP_CHI_FILES && strcmp(path,names[i])) ++i;
    if (i==BTP_CHI_FILES || !files->bytes[i]) return fail(e,"undeclared resource requested");
    *bytes=malloc(files->size[i]);if (!*bytes) return fail(e,"resource allocation failed");
    memcpy(*bytes,files->bytes[i],files->size[i]);*size=files->size[i];return 1;
}
static int setting(BtpJson *j,unsigned object,const char *key,char *out,size_t size)
{ return btp_json_string(j,btp_json_field(j,object,key),out,size); }
static int campaign(const char *root,BtpJson *manifest,BtpDigest *digest,
    BtpResources *r,unsigned *edition,BtpError *e)
{
    char relative[1024],path[4096],value[64];BtpJson j={0};unsigned version;int ok=0;
    if (!setting(manifest,1,"campaign",relative,sizeof relative)) goto done;
    if (strcmp(relative,"campaign.json")) { fail(e,"expected campaign.json");goto done; }
    if (
        !btp_project_path(root,relative,path,e) || !btp_json_load_chi_text(&j,path,e->text)) goto done;
    btp_digest_add(digest,j.source_digest,32);
    if (!setting(&j,1,"format",value,sizeof value) || strcmp(value,"btp-chi-campaign-v1") ||
        !btp_json_uint(&j,btp_json_field(&j,1,"schema_version"),1,1,&version) ||
        !setting(&j,1,"edition",value,sizeof value)) goto done;
    if (!strcmp(value,"original")) *edition=1;
    else if (!strcmp(value,"updated")) *edition=2;
    else { btp_json_error(&j,1,"edition must be original or updated");goto done; }
    unsigned overrides=btp_json_field(&j,1,"dialogue_overrides"),nodes[BTP_TALK_STRINGS]={0};
    if (!btp_json_type(&j,overrides,'[')) goto done;
    for (unsigned n=j.nodes[overrides].first;n;n=j.nodes[n].next) {
        unsigned index;if (!btp_json_uint(&j,btp_json_field(&j,n,"index"),0,BTP_TALK_STRINGS-1,&index)) goto done;
        if (nodes[index]) { btp_json_error(&j,n,"duplicate dialogue index");goto done; }
        nodes[index]=btp_json_field(&j,n,"text");
        if (!btp_json_type(&j,nodes[index],'"') || !btp_json_done(&j,n)) goto done;
    }
    BtpDialogue *rebuilt=calloc(1,sizeof *rebuilt);
    if (!rebuilt) { fail(e,"dialogue allocation failed");goto done; }
    memcpy(rebuilt->font,r->dialogue.font,sizeof rebuilt->font);
    for (unsigned i=0;i<BTP_TALK_STRINGS;++i) {
        const char *text=nodes[i] ? j.nodes[nodes[i]].text : (const char *)r->dialogue.bytes+r->dialogue.offset[i];
        size_t length=strlen(text);int valid=length<=512;
        for (size_t k=0;k<length;++k) {
            unsigned c=(unsigned char)text[k];
            if (c!=13 && !(i>=17 && (c==6 || c==15)) && (c<32 || c>=127)) valid=0;
        }
        if (!valid || rebuilt->length+length+1>BTP_TALK_MAX) {
            free(rebuilt);btp_json_error(&j,nodes[i],"unsupported dialogue character or text budget exceeded");goto done;
        }
        rebuilt->offset[i]=rebuilt->length;rebuilt->size[i]=(uint16_t)length;
        memcpy(rebuilt->bytes+rebuilt->length,text,length+1);rebuilt->length+=(uint16_t)(length+1);
    }
    r->dialogue=*rebuilt;free(rebuilt);ok=btp_json_done(&j,1);
done:
    if (!ok && !e->text[0]) fail(e,"invalid campaign format");
    btp_json_close(&j);return ok;
}
BtpResources *btp_chi_project_load(const char *root,BtpJson *manifest,
    BtpDigest *digest,unsigned *edition,BtpError *e)
{
    Files *files=calloc(1,sizeof *files);BtpResources *r=calloc(1,sizeof *r);int ok=0;
    if (!files || !r) { fail(e,"allocation failed");goto done; }
    unsigned list=btp_json_field(manifest,1,"resources"),i=0;size_t total=0;
    if (!btp_json_type(manifest,list,'[')) goto done;
    for (unsigned n=manifest->nodes[list].first;n;n=manifest->nodes[n].next,++i) {
        char relative[1024],expected[128],path[4096];
        if (i>=BTP_CHI_FILES || !btp_json_string(manifest,n,relative,sizeof relative)) { fail(e,"wrong resource count");goto done; }
        snprintf(expected,sizeof expected,"chi/%s",names[i]);
        if (strcmp(relative,expected)) { btp_json_error(manifest,n,"expected canonical chi/ resource path and order");goto done; }
        if (!btp_project_path(root,relative,path,e)) goto done;
        FILE *f=fopen(path,"rb");if (!f) { fail(e,"cannot read resource");goto done; }
        /* Bound before allocating and read once. Decoder and content digest
           consume this same snapshot, including duplicated BLD load slots. */
        int bad=fseek(f,0,SEEK_END);long size=bad ? -1 : ftell(f);
        if (size<=0 || size>1024*1024 || total+(size_t)(size>0 ? size : 0)>4u*1024u*1024u || fseek(f,0,SEEK_SET)) {
            fclose(f);fail(e,"resource exceeds per-file/total budget");goto done;
        }
        files->bytes[i]=malloc((size_t)size);files->size[i]=(size_t)size;
        bad=!files->bytes[i] || fread(files->bytes[i],1,(size_t)size,f)!=(size_t)size;
        if (fgetc(f)!=EOF || ferror(f)) bad=1;
        if (fclose(f)) bad=1;
        if (bad) { fail(e,"resource changed or could not be read");goto done; }
        total+=(size_t)size;BtpDigest file;uint8_t hash[32];btp_digest_start(&file);
        btp_digest_add(&file,files->bytes[i],files->size[i]);btp_digest_finish(&file,hash);btp_digest_add(digest,hash,32);
    }
    if (i!=BTP_CHI_FILES) { fail(e,"missing canonical resources");goto done; }
    if (!btp_resources_load_reader("",r,copy_read,files,e) ||
        !btp_dialogue_decode(files->bytes[76],files->size[76],&r->dialogue,e) ||
        !btp_combat_data_decode(files->bytes[77],files->size[77],&r->combat) ||
        !btp_world_data_decode(files->bytes[78],files->size[78],&r->world,e) ||
        !campaign(root,manifest,digest,r,edition,e)) goto done;
    r->features=(uint8_t)(BTP_FEATURE_EXPLICIT | (*edition==2 ? BTP_FEATURE_BROKER|BTP_FEATURE_ENHANCED : 0));ok=1;
done:
    if (files) { for (unsigned k=0;k<BTP_CHI_FILES;++k) free(files->bytes[k]);free(files); }
    if (!ok) { if (!e->text[0]) fail(e,"invalid resource/cache");free(r);return NULL; }return r;
}

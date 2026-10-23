#include "data/portraits.h"
#include "data/anm.h"
#include "data/project.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Original room_map IDs identify scenes, never original ANM file numbers.
   The broker retains its previously released filename and added building ID. */
static const struct { unsigned building;const char *name; } slots[BTP_PORTRAIT_COUNT]={
    {26,"broker"},{0,"training"},{7,"lounge"},{13,"prison"},
    {21,"inventor"},{16,"cinema"},{9,"hospital"},{2,"comstar"},
    /* Frob's Electronics is Video Hut (17), not the VIEWDISK scene (18).
       Mayor's ordinary room art still yields to its scripted holodisk. */
    {12,"clothes"},{17,"video-hut"},{14,"mayor"}
};

static int load_one(const char *directory,const char *name,BtpAnm *portrait,BtpError *error)
{
    char path[4096];
    int n=snprintf(path,sizeof path,"%sart/%s.anm",directory,name);
    if (n<0 || (size_t)n>=sizeof path) {
        if (error) snprintf(error->text,sizeof error->text,"Updated portrait path too long: %s",name);
        return 0;
    }
    FILE *file=fopen(path,"rb");
    if (!file) {
        /* Missing optional art preserves older/custom packs. Permissions or
           a present, malformed file must produce a visible diagnostic. */
        if (errno==ENOENT) return 1;
        if (error) snprintf(error->text,sizeof error->text,"Cannot open Updated portrait: %s",name);
        return 0;
    }
    uint8_t bytes[BTP_ANM_BYTES+1u];
    size_t length=fread(bytes,1,sizeof bytes,file);
    int bad=ferror(file),close_bad=fclose(file);
    if (bad || close_bad) {
        if (error) snprintf(error->text,sizeof error->text,"Cannot read Updated portrait: %s",name);
        return 0;
    }
    BtpError detail;
    if (!btp_anm_decode(bytes,length,portrait,&detail)) {
        if (error) snprintf(error->text,sizeof error->text,"Updated %s portrait: %.190s",name,detail.text);
        return 0;
    }
    return 1;
}

BtpPortraits *btp_portraits_load(const char *roster_path,BtpError *error)
{
    if (!roster_path) {
        if (error) snprintf(error->text,sizeof error->text,"Portraits require a roster path");
        return NULL;
    }
    /* Accept either native path separator, including Wine's Z:\\ paths.
       Resolve beside the pack, not beside the executable or process cwd. */
    const char *last=NULL;
    for (const char *p=roster_path;*p;++p) if (*p=='/' || *p=='\\') last=p;
    size_t prefix=last ? (size_t)(last-roster_path)+1u : 0u;
    char directory[4096];
    if (prefix>=sizeof directory) {
        if (error) snprintf(error->text,sizeof error->text,"Portrait directory path too long");
        return NULL;
    }
    memcpy(directory,roster_path,prefix);directory[prefix]=0;
    /* The portrait set exceeds 128 KiB. Keep staging off the Windows stack. */
    BtpPortraits *result=calloc(1,sizeof *result);
    if (!result) {
        if (error) snprintf(error->text,sizeof error->text,"Portrait allocation failed");
        return NULL;
    }
    for (unsigned i=0;i<BTP_PORTRAIT_COUNT;++i)
        if (!load_one(directory,slots[i].name,&result->image[i],error)) { free(result);return NULL; }
    if (error) error->text[0]=0;
    return result;
}

const BtpAnm *btp_portrait_for_building(const BtpResources *resources,unsigned building)
{
    if (!resources) return NULL;
    for (unsigned i=0;i<BTP_PORTRAIT_COUNT;++i)
        if (slots[i].building==building && resources->portraits.image[i].count &&
            (resources->roster.count || (resources->project && resources->project->chi_portraits[i])))
            return &resources->portraits.image[i];
    return NULL;
}

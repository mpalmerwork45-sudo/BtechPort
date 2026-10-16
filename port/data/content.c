#include "data/content.h"
#include "data/anm.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail(BtpError *error, const char *message)
{
    if (error) snprintf(error->text, sizeof error->text, "%s", message);
    return 0;
}

void btp_content_close(BtpContent *content)
{
    if (!content) return;
    free(content->resources);
    *content = (BtpContent){0};
}
static int broker_portrait_load(const char *roster_path,BtpAnm *portrait,BtpError *error)
{
    /* Resolve beside the chosen pack, not the executable or current working
       directory. Older/custom packs can omit the art and keep the mechanic.
       A present but corrupt file must not silently select a different image. */
    const char *last=NULL;
    for (const char *p=roster_path;*p;++p) if (*p=='/' || *p=='\\') last=p;
    size_t prefix=last ? (size_t)(last-roster_path)+1u : 0u;
    const char suffix[]="art/broker.anm";
    char path[4096];
    if (prefix>sizeof path-sizeof suffix) return fail(error,"Broker portrait path too long");
    memcpy(path,roster_path,prefix);memcpy(path+prefix,suffix,sizeof suffix);
    FILE *file=fopen(path,"rb");
    if (!file) {
        if (errno==ENOENT) return 1;
        return fail(error,"Cannot open Updated broker portrait");
    }
    uint8_t bytes[BTP_ANM_BYTES+1u];
    size_t length=fread(bytes,1,sizeof bytes,file);
    int bad=ferror(file),close_bad=fclose(file);
    if (bad || close_bad) return fail(error,"Cannot read Updated broker portrait");
    return btp_anm_decode(bytes,length,portrait,error);
}
int btp_content_select(BtpContent *content,BtpContentProfile profile,const char *path,BtpError *error)
{
    if (!content || !content->resources) return fail(error,"Load original resources before selecting an edition");
    /* Keep the optional diagnostic buffer alive through the success path. */
    BtpError local_error;
    if (profile==BTP_CONTENT_UPDATED) {
        BtpRoster roster;BtpAnm portrait={0};
        if (!error) error=&local_error;
        /* Publish definitions and art together only after both validate.
           Cosmetic changes deliberately do not change the roster fingerprint. */
        if (!btp_roster_load(path,&roster,error->text) || !broker_portrait_load(path,&portrait,error)) return 0;
        content->resources->roster=roster;content->resources->broker_portrait=portrait;
    } else if (profile==BTP_CONTENT_ORIGINAL_DOS_103) {
        content->resources->roster=(BtpRoster){0};
        content->resources->broker_portrait=(BtpAnm){0};
    } else return fail(error,"Unknown game edition");
    content->profile=profile;if (error) error->text[0]=0;return 1;
}

int btp_content_load_original(BtpContent *content,
    const BtpOriginalContentPaths *paths, BtpError *error)
{
    if (!content || !paths || !paths->directory || !paths->dialogue ||
        !paths->combat || !paths->world)
        return fail(error, "Original content requires resource and cache paths");

    /* Speaker programs make this several megabytes. Build on the heap and
       publish only a complete load, preserving the Windows default stack and
       any existing content if one of the later caches is missing or invalid. */
    BtpResources *candidate = calloc(1, sizeof *candidate);
    if (!candidate) return fail(error, "Content allocation failed");
    if (!btp_resources_load(paths->directory, candidate, error) ||
        !btp_dialogue_load(paths->dialogue, &candidate->dialogue, error) ||
        !btp_combat_data_load(paths->combat, &candidate->combat, error) ||
        !btp_world_data_load(paths->world, &candidate->world, error)) {
        free(candidate);
        return 0;
    }
    btp_content_close(content);
    content->resources = candidate;
    content->profile = BTP_CONTENT_ORIGINAL_DOS_103;
    return 1;
}

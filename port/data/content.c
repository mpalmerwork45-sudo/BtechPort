#include "data/content.h"
#include "data/portraits.h"
#include "data/project.h"
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
    if (content->resources) btp_project_free(content->resources->project);
    free(content->resources);
    *content = (BtpContent){0};
}
int btp_content_select(BtpContent *content,BtpContentProfile profile,const char *path,BtpError *error)
{
    if (!content || !content->resources) return fail(error,"Load original resources before selecting an edition");
    if (content->resources->project && content->resources->project->independent.loaded)
        return fail(error,"Reload original resources before selecting a CHI edition");
    /* Keep the optional diagnostic buffer alive through the success path. */
    BtpError local_error;
    if (profile==BTP_CONTENT_UPDATED) {
        BtpRoster roster;BtpCombatProfile rules;
        if (!error) error=&local_error;
        /* Publish definitions and art together only after both validate.
           Cosmetic changes deliberately do not change the roster fingerprint. */
        if (!btp_roster_load(path,&roster,error->text)) return 0;
        if (!btp_combat_profile_load(path,&rules,error->text)) return 0;
        BtpPortraits *portraits=btp_portraits_load(path,error);
        if (!portraits) return 0;
        content->resources->roster=roster;content->resources->portraits=*portraits;
        content->resources->combat_profile=rules;
        free(portraits);
    } else if (profile==BTP_CONTENT_ORIGINAL_DOS_103) {
        content->resources->roster=(BtpRoster){0};
        content->resources->combat_profile=(BtpCombatProfile){0};
        memset(&content->resources->portraits,0,sizeof content->resources->portraits);
    } else return fail(error,"Unknown game edition");
    content->resources->features=(uint8_t)(BTP_FEATURE_EXPLICIT | (profile==BTP_CONTENT_UPDATED ? BTP_FEATURE_BROKER|BTP_FEATURE_ENHANCED : 0));
    btp_project_free(content->resources->project);content->resources->project=NULL;
    content->resources->combat.definitions=NULL;
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
    candidate->features=BTP_FEATURE_EXPLICIT;
    content->profile = BTP_CONTENT_ORIGINAL_DOS_103;
    return 1;
}

int btp_content_load_project(BtpContent *content,const char *directory,
    const BtpOriginalContentPaths *dependency,BtpError *error)
{
    BtpContent candidate={0};
    if (!content || !directory) return fail(error,"Project directory is required");
    /* Stage the whole dependency and package. A typo in a later asset never
       replaces a playable context or frees definitions still in use. */
    candidate.resources=calloc(1,sizeof *candidate.resources);
    if (!candidate.resources) return fail(error,"Content allocation failed");
    BtpResources *r=candidate.resources;
    r->project=btp_project_load(directory,&r->roster,&r->portraits,error);
    if (!r->project) { btp_content_close(&candidate);return 0; }
    if (r->project->chi_resources) {
        /* The project validator already decoded and hashed one private input
           snapshot. Transfer ownership instead of reopening editable files. */
        BtpProject *project=r->project;
        candidate.resources=project->chi_resources;project->chi_resources=NULL;
        candidate.resources->project=project;
        candidate.resources->roster=r->roster;candidate.resources->portraits=r->portraits;
        r->project=NULL;free(r);r=candidate.resources;
    } else if (r->project->independent.loaded) btp_independent_resources(r);
    else {
        if (!dependency) { btp_content_close(&candidate);return fail(error,"CHI project requires explicit --data, --dialogue-data, --combat-data, --world-data"); }
        BtpContent original={0};
        if (!btp_content_load_original(&original,dependency,error)) { btp_content_close(&candidate);return 0; }
        /* Preserve the validated package while publishing only a complete
           original dependency. Independent projects never enter this path. */
        original.resources->project=r->project;r->project=NULL;
        original.resources->roster=r->roster;original.resources->portraits=r->portraits;
        btp_content_close(&candidate);candidate=original;r=candidate.resources;
    }
    if (!r->project->chi_edition) r->features=0; /* Preserve released authored-package behavior. */
    r->combat.definitions=&r->project->definitions;
    r->combat_profile=r->project->definitions.rules;
    candidate.profile=BTP_CONTENT_PROJECT;
    btp_content_close(content);*content=candidate;return 1;
}

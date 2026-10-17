#include "data/content.h"
#include "data/unit_data.h"
#include "data/portraits.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <direct.h>
#include <process.h>
#define process_id() _getpid()
#define make_directory(path) _mkdir(path)
#define remove_directory(path) _rmdir(path)
#else
#include <sys/stat.h>
#include <unistd.h>
#define process_id() getpid()
#define make_directory(path) mkdir(path,0700)
#define remove_directory(path) rmdir(path)
#endif

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)

static void rejected(BtpContent *content, const BtpOriginalContentPaths *paths)
{
    BtpError error = {0};
    BtpResources *before = content->resources;
    BtpContentProfile profile = content->profile;
    /* Snapshot the existing object, including unused storage, to detect a
       failed replacement overwriting any part of the previously loaded data. */
    BtpResources *snapshot = before ? malloc(sizeof *snapshot) : NULL;
    if (before) { CHECK(snapshot != NULL); memcpy(snapshot, before, sizeof *snapshot); }
    CHECK(!btp_content_load_original(content, paths, &error));
    CHECK(error.text[0]);
    CHECK(content->resources == before);
    CHECK(content->profile == profile);
    if (before) CHECK(!memcmp(snapshot, before, sizeof *snapshot));
    free(snapshot);
}

static void edition_art(BtpContent *content,const char *roster_path)
{
    BtpError error;
    CHECK(btp_content_select(content,BTP_CONTENT_UPDATED,roster_path,&error));
    for (unsigned i=0;i<BTP_PORTRAIT_COUNT;++i) CHECK(content->resources->portraits.image[i].count==1);
    BtpResources *snapshot=malloc(sizeof *snapshot);CHECK(snapshot);
    *snapshot=*content->resources;
    /* A failed/sanitized run must not poison the next test's fixture path. */
    char directory[80],art[96],roster_file[96],portrait_file[112];
    snprintf(directory,sizeof directory,"btp-content-test-pack-%ld",(long)process_id());
    snprintf(art,sizeof art,"%s/art",directory);
    snprintf(roster_file,sizeof roster_file,"%s/roster.json",directory);
    snprintf(portrait_file,sizeof portrait_file,"%s/broker.anm",art);
    CHECK(make_directory(directory)==0);
    CHECK(make_directory(art)==0);
    uint8_t *bytes;size_t length;
    CHECK(btp_read_file(roster_path,&bytes,&length,&error));
    FILE *file=fopen(roster_file,"wb");CHECK(file);
    CHECK(fwrite(bytes,1,length,file)==length && !fclose(file));free(bytes);

    /* Older/custom packs without a portrait still load. Art is cosmetic:
       it neither changes definition/save identity nor any original ANM. */
    CHECK(btp_content_select(content,BTP_CONTENT_UPDATED,roster_file,NULL));
    for (unsigned i=0;i<BTP_PORTRAIT_COUNT;++i) CHECK(!content->resources->portraits.image[i].count);
    CHECK(!memcmp(&snapshot->roster,&content->resources->roster,sizeof snapshot->roster));
    CHECK(!memcmp(snapshot->animations,content->resources->animations,sizeof snapshot->animations));
    /* A pack can provide any subset. Exercise each filename, then corrupt
       the final file to catch publishing earlier art before validation ends. */
    const char *names[]={"broker","training","lounge","prison","inventor","cinema","hospital","comstar"};
    for (unsigned i=0;i<BTP_PORTRAIT_COUNT;++i) {
        snprintf(portrait_file,sizeof portrait_file,"%s/%s.anm",art,names[i]);
        file=fopen(portrait_file,"wb");CHECK(file);
        const BtpAnm *image=&snapshot->portraits.image[i];
        CHECK(fwrite(image->bytes,1,image->length,file)==image->length && !fclose(file));
        CHECK(btp_content_select(content,BTP_CONTENT_UPDATED,roster_file,&error));
        for (unsigned j=0;j<BTP_PORTRAIT_COUNT;++j)
            CHECK(content->resources->portraits.image[j].count==(j<=i));
        CHECK(!memcmp(&snapshot->roster,&content->resources->roster,sizeof snapshot->roster));
    }
    CHECK(btp_content_select(content,BTP_CONTENT_UPDATED,roster_path,&error));
    file=fopen(portrait_file,"wb");CHECK(file);
    CHECK(fwrite("XX",1,2,file)==2 && !fclose(file));
    CHECK(!btp_content_select(content,BTP_CONTENT_UPDATED,roster_file,&error));
    CHECK(strstr(error.text,"comstar") && content->profile==BTP_CONTENT_UPDATED);
    CHECK(!memcmp(snapshot,content->resources,sizeof *snapshot));

    CHECK(btp_content_select(content,BTP_CONTENT_ORIGINAL_DOS_103,NULL,&error));
    CHECK(!content->resources->roster.count);
    for (unsigned i=0;i<BTP_PORTRAIT_COUNT;++i) CHECK(!content->resources->portraits.image[i].count);
    CHECK(!memcmp(snapshot->animations,content->resources->animations,sizeof snapshot->animations));
    CHECK(!btp_content_select(content,BTP_CONTENT_UPDATED,roster_file,&error));
    CHECK(content->profile==BTP_CONTENT_ORIGINAL_DOS_103 && !content->resources->roster.count);
    for (unsigned i=0;i<BTP_PORTRAIT_COUNT;++i) CHECK(!content->resources->portraits.image[i].count);
    free(snapshot);
    for (unsigned i=0;i<BTP_PORTRAIT_COUNT;++i) {
        snprintf(portrait_file,sizeof portrait_file,"%s/%s.anm",art,names[i]);CHECK(!remove(portrait_file));
    }
    CHECK(!remove(roster_file));
    CHECK(remove_directory(art)==0);
    CHECK(remove_directory(directory)==0);
}

int main(int argc, char **argv)
{
    CHECK(argc == 5 || argc == 6);
    const BtpOriginalContentPaths paths = {
        .directory = argv[1], .dialogue = argv[2], .combat = argv[3], .world = argv[4]
    };
    BtpContent content = {0};
    BtpError error;
    BtpOriginalContentPaths bad = paths;
    bad.directory = "btp-content-missing-directory";
    rejected(&content, &bad);
    rejected(&content, NULL);
    CHECK(btp_content_load_original(&content, &paths, &error));
    CHECK(content.profile == BTP_CONTENT_ORIGINAL_DOS_103);
    CHECK(content.resources != NULL);
    CHECK(content.resources->map.width && content.resources->citadel.length);
    CHECK(content.resources->dialogue.length && content.resources->world.loaded);
    if (argc==6) edition_art(&content,argv[5]);
    /* Definition lookups reject identities outside their original tables;
       future authoring inputs must not become unchecked record offsets. */
    const unsigned limits[]={3,1,1,3,11,1,1};
    for (unsigned i=0;i<sizeof limits/sizeof limits[0];++i)
        CHECK(btp_mech_template(&content.resources->combat,(BtpMechTemplate)i,limits[i])==NULL);
    CHECK(btp_mech_template(NULL,BTP_MECH_LOAN,0)==NULL);
    CHECK(btp_weapon_definition(&content.resources->combat,33).name==NULL);
    CHECK(btp_mech_refit_price(&content.resources->combat,8)==0);

    /* Test every stage after resources have already been published. The file
       is synthetic and stays in this build's CTest directory, never in either
       reference tree. Sanitizers also check cleanup of the partial loads. */
    const char *truncated = "btp-content-test-truncated.bin";
    FILE *f = fopen(truncated, "wb"); CHECK(f != NULL);
    CHECK(fwrite("BT", 1, 2, f) == 2); CHECK(!fclose(f));
    for (unsigned stage = 0; stage < 4; ++stage) {
        bad = paths;
        const char **field = stage == 0 ? &bad.directory : stage == 1 ? &bad.dialogue :
            stage == 2 ? &bad.combat : &bad.world;
        *field = "btp-content-missing-directory/data.bin";
        rejected(&content, &bad);
        if (stage) { *field = truncated; rejected(&content, &bad); }
        *field = NULL; rejected(&content, &bad);
    }
    CHECK(!remove(truncated));

    /* A fresh, complete context can replace an old one. No saved state or
       resource pointer is retained across this application-level operation. */
    CHECK(btp_content_load_original(&content, &paths, &error));
    CHECK(content.profile == BTP_CONTENT_ORIGINAL_DOS_103);
    CHECK(content.resources && content.resources->world.loaded);
    btp_content_close(&content);
    CHECK(content.resources == NULL && content.profile == BTP_CONTENT_NONE);
    btp_content_close(&content);
    btp_content_close(NULL);
    CHECK(content.resources == NULL && content.profile == BTP_CONTENT_NONE);
    CHECK(!btp_content_load_original(NULL, &paths, NULL));
    printf("PASS: %u content ownership/failure checks\n", checks);
    return 0;
}

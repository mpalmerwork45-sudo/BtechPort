#include "data/content.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

int main(int argc, char **argv)
{
    CHECK(argc == 5);
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

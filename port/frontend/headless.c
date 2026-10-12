#include "frontend/cli.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv)
{
    BtpOptions options;
    int parsed = btp_options(argc, argv, &options);
    if (parsed <= 0) return parsed == -1 ? 0 : 1;
    BtpResources *resources = malloc(sizeof *resources);
    if (!resources) return 1;
    BtpError error;
    if (!btp_resources_load(options.data, resources, &error) ||
        !btp_dialogue_load(options.dialogue_data, &resources->dialogue, &error) ||
        !btp_combat_data_load(options.combat_data,&resources->combat,&error) ||
        !btp_world_data_load(options.world_data,&resources->world,&error)) {
        fprintf(stderr, "%s\nUse --data with a quoted path; filenames are case-sensitive.\n"
            "Run ./scripts/build.sh to prepare the resource caches.\n", error.text);
        free(resources); return 1;
    }
    int result = btp_run_headless(&options, resources);
    free(resources);
    return result;
}

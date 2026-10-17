#include "frontend/cli.h"
#include <stdio.h>
int main(int argc, char **argv)
{
    BtpOptions options;
    int parsed = btp_options(argc, argv, &options);
    if (parsed <= 0) return parsed == -1 ? 0 : 1;
    BtpContent content = {0};
    BtpError error;
    if (!btp_cli_load_content(&options, &content, &error)) {
        fprintf(stderr,"%s\n",error.text);
        if (!options.project) fputs("Use --data with a quoted path; filenames are case-sensitive.\nRun ./scripts/build.sh to prepare the resource caches.\n",stderr);
        return 1;
    }
    int result = btp_run_headless(&options, content.resources);
    btp_content_close(&content);
    return result;
}

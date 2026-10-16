#include "data/roster.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv)
{
    if (argc!=2) { fputs("Usage: btp-roster-check ROSTER.json\n",stderr);return 2; }
    BtpRoster *roster=calloc(1,sizeof *roster);char error[256];
    if (!roster) return 1;
    if (!btp_roster_load(argv[1],roster,error)) { fprintf(stderr,"%s\n",error);free(roster);return 1; }
    printf("{\"package\":\"%s\",\"fingerprint\":%u,\"mechs\":[",roster->package,roster->fingerprint);
    for (unsigned i=0;i<roster->count;++i) {
        const BtpRosterMech *d=&roster->mechs[i];
        printf("%s{\"id\":\"%s\",\"save_code\":%u,\"tons\":%u,\"price\":%u}",i ? "," : "",d->id,d->record[123],d->record[16],d->price);
    }
    puts("]}");free(roster);return 0;
}

#include "data/project.h"
#include "data/content.h"
#include "data/portraits.h"
#include "data/file.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <direct.h>
#define make_directory(p) _mkdir(p)
#else
#include <sys/stat.h>
#define make_directory(p) mkdir(p,0700)
#endif

static int provenance(const char *roster,const char *directory,BtpError *error)
{
    /* Retain pack attribution separately from generated definitions. These
       documents do not participate in save compatibility or grant a license. */
    const char *source_names[]={"README.md","LICENSE.md","sources.json","art/README.md"};
    const char *target_names[]={"SOURCE-README.md","LICENSE.md","sources.json","ART-SOURCE-README.md"};
    size_t prefix=0;for (const char *p=roster;*p;++p) if (*p=='/' || *p=='\\') prefix=(size_t)(p-roster)+1;
    for (unsigned i=0;i<4;++i) {
        char source[4096],target[4096];
        int a=snprintf(source,sizeof source,"%.*s%s",(int)prefix,roster,source_names[i]);
        int b=snprintf(target,sizeof target,"%s/%s",directory,target_names[i]);
        if (a<0 || b<0 || (size_t)a>=sizeof source || (size_t)b>=sizeof target) return 0;
        FILE *in=fopen(source,"rb");if (!in && errno==ENOENT) continue;
        FILE *out=in ? btp_file_create(target) : NULL;
        if (!in || !out) { if (in) fclose(in);snprintf(error->text,256,"Cannot copy attribution: %.180s",source);return 0; }
        unsigned char bytes[4096];size_t n;int ok=1;
        while ((n=fread(bytes,1,sizeof bytes,in))) if (fwrite(bytes,1,n,out)!=n) { ok=0;break; }
        if (ferror(in)) ok=0;
        if (fclose(in)) ok=0;
        if (fclose(out)) ok=0;
        if (!ok) { snprintf(error->text,256,"Cannot copy attribution: %.180s",source);return 0; }
    }
    return 1;
}

int main(int argc,char **argv)
{
    if (argc<3) {
        fputs("Usage:\n  btp-project validate DIRECTORY\n  btp-project validate-content FILE\n"
            "  btp-project export NEW_DIRECTORY --roster FILE --combat-data FILE\n"
            "Export reads adjacent combat.json and art, writing explicit references.\n",stderr);return 2;
    }
    BtpError error={0};int ok=0;
    BtpRoster *r=calloc(1,sizeof *r);BtpPortraits *art=calloc(1,sizeof *art);BtpDefinitions *d=calloc(1,sizeof *d);
    if (!r || !art || !d) { free(r);free(art);free(d);return 1; }
    if (!strcmp(argv[1],"validate") && argc==3) {
        BtpProject *p=btp_project_load(argv[2],r,art,&error);
        if (p) {
            printf("Valid project %s %s: %u mechs, %u weapons",p->id,p->version,r->count,p->definitions.weapon_count);
            if (p->adventure.loaded) printf("; %u maps, %u event nodes",p->adventure.map_count,p->adventure.node_count);
            fputs("; SHA-256 ",stdout);
            for (unsigned i=0;i<32;++i) printf("%02x",p->digest[i]);
            puts("");free(p);ok=1;
        }
    } else if (!strcmp(argv[1],"validate-content") && argc==3) {
        ok=btp_definitions_load(argv[2],d,error.text) && btp_definitions_compile(d,r,error.text);
        if (ok) printf("Valid content %s %s: %u mechs, %u weapons\n",d->id,d->version,d->mech_count,d->weapon_count);
    } else if (!strcmp(argv[1],"export") && argc==7 && !strcmp(argv[3],"--roster") && !strcmp(argv[5],"--combat-data")) {
        BtpCombatData *combat=calloc(1,sizeof *combat);BtpCombatProfile rules={0};
        if (combat && btp_roster_load(argv[4],r,error.text) && btp_combat_profile_load(argv[4],&rules,error.text) && btp_combat_data_load(argv[6],combat,&error)) {
            if (make_directory(argv[2])) snprintf(error.text,sizeof error.text,"Export needs a new, writable directory: %.180s",argv[2]);
            else {
                char path[4096];int n=snprintf(path,sizeof path,"%s/content.json",argv[2]);
                BtpPortraits *original_art=btp_portraits_load(argv[4],&error);
                ok=original_art && n>0 && (size_t)n<sizeof path && btp_definitions_export(path,r,combat,&rules,error.text) &&
                    btp_project_export_manifest(argv[2],r->package,r->version,&rules,original_art,&error) && provenance(argv[4],argv[2],&error);
                free(original_art);
                if (ok) printf("Exported %u models to %s; original dependency must be supplied when playing.\n",r->count,argv[2]);
            }
        }
        free(combat);
    } else snprintf(error.text,sizeof error.text,"Unknown or incomplete command (run btp-project for usage)");
    if (!ok) fprintf(stderr,"%s\n",error.text);
    free(r);free(art);free(d);return ok ? 0 : 1;
}

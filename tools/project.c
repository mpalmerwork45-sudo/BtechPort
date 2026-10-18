#include "data/project.h"
#include "data/content.h"
#include "data/portraits.h"
#include "data/file.h"
#include "frontend/pixels.h"
#include "data/sprites.h"
#include "data/unit_data.h"
#include "core/animation.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <direct.h>
#include <fcntl.h>
#include <io.h>
#define make_directory(p) _mkdir(p)
#else
#include <sys/stat.h>
#define make_directory(p) mkdir(p,0700)
#endif

static int terrain_animations(const char *directory)
{
    BtpError error={0};BtpResources *r=calloc(1,sizeof *r);
    uint32_t *atlas=malloc(BTP_TILE_ATLAS_PIXELS*sizeof *atlas);
    int ok=r && atlas && btp_resources_load(directory,r,&error) && btp_map_tile_atlas(&r->terrain_animation,atlas);
    if (!ok) {
        fprintf(stderr,"Cannot preview terrain animation: %s\n",error.text[0] ? error.text : "missing animation sheet or allocation failed");
        free(atlas);free(r);return 0;
    }
    /* Export only on request, to memory: mappings and colors come from the
       game's decoder/rules, rather than a second editor implementation. */
    fputs("{\"frame_ticks\":4,\"tiles\":[",stdout);unsigned count=0;
    for (unsigned tile=0;tile<250;++tile) {
        if (!btp_terrain_frame(tile,0)) continue;
        printf("%s{\"graphic\":%u,\"frames\":[",count++ ? "," : "",tile);
        for (unsigned phase=0;phase<3;++phase) {
            unsigned frame=btp_terrain_frame(tile,phase);
            fputs(phase ? ",[" : "[",stdout);
            for (unsigned y=0;y<16;++y) {
                fputs(y ? ",\"" : "\"",stdout);
                for (unsigned x=0;x<16;++x) {
                    unsigned at=((frame/16)*16+y)*BTP_TILE_ATLAS_SIDE+(frame%16)*16+x;
                    printf("%06xff",atlas[at]&0xffffffu);
                }
                putchar('"');
            }
            putchar(']');
        }
        fputs("]}",stdout);
    }
    puts("]}");free(atlas);free(r);return !ferror(stdout);
}

static int preview_tiles(const char *directory,const char *name)
{
    BtpError error={0};
    if (strcmp(name,"chi:land") && strcmp(name,"chi:destroyed")) {
        fprintf(stderr,"Unknown tile sheet: %.180s (use chi:land or chi:destroyed)\n",name);return 0;
    }
    /* The original resource set is large enough to exceed Windows' default
       stack. This read-only preview shares the validated game loader. */
    BtpResources *resources=calloc(1,sizeof *resources);
    uint32_t *atlas=malloc(BTP_TILE_ATLAS_PIXELS*sizeof *atlas);
    int ok=resources && atlas;
    if (!ok) snprintf(error.text,sizeof error.text,"Tile preview allocation failed");
    if (ok) ok=btp_resources_load(directory,resources,&error);
    if (ok) {
        const BtpGraphic *sheet=!strcmp(name,"chi:land") ? &resources->tiles : &resources->destroyed_tiles;
        ok=btp_map_tile_atlas(sheet,atlas);
        if (!ok) snprintf(error.text,sizeof error.text,"Tile preview requires a format-1 map tile sheet");
    }
#ifdef _WIN32
    /* Tk consumes P6 bytes from a pipe; text mode would corrupt LF pixels. */
    if (ok && _setmode(_fileno(stdout),_O_BINARY)==-1) {
        ok=0;snprintf(error.text,sizeof error.text,"Cannot set binary tile preview output");
    }
#endif
    if (ok) {
        ok=fprintf(stdout,"P6\n%d %d\n255\n",BTP_TILE_ATLAS_SIDE,BTP_TILE_ATLAS_SIDE)>0;
        unsigned char row[BTP_TILE_ATLAS_SIDE*3];
        for (unsigned y=0;y<BTP_TILE_ATLAS_SIDE && ok;++y) {
            for (unsigned x=0;x<BTP_TILE_ATLAS_SIDE;++x) {
                uint32_t color=atlas[y*BTP_TILE_ATLAS_SIDE+x];
                row[x*3]=(unsigned char)(color>>16);
                row[x*3+1]=(unsigned char)(color>>8);
                row[x*3+2]=(unsigned char)color;
            }
            ok=fwrite(row,1,sizeof row,stdout)==sizeof row;
        }
        if (fflush(stdout)) ok=0;
        if (!ok) snprintf(error.text,sizeof error.text,"Cannot write tile preview output");
    }
    if (!ok) fprintf(stderr,"%s\n",error.text);
    free(atlas);free(resources);return ok;
}
static int source_sprite(const char *directory,unsigned first,unsigned count)
{
    if (!count || count>32 || first>=BTP_SPRITE_COUNT || count>BTP_SPRITE_COUNT-first) return 0;
    BtpResources *r=calloc(1,sizeof *r);BtpError error={0};BtpSpriteRect rect;
    if (!r || !btp_resources_load(directory,r,&error) || !btp_sprite_rect(first,&rect)) { fprintf(stderr,"%s\n",error.text);free(r);return 0; }
    for (unsigned i=0;i<count;++i) {
        BtpSpriteRect next;btp_sprite_rect(first+i,&next);
        if (next.width!=rect.width || next.height!=rect.height) { fputs("Choose frames with equal dimensions.\n",stderr);free(r);return 0; }
    }
    printf("{\"id\":\"chi:sprite-%u\",\"name\":\"Original sprite %u\",\"kind\":\"sprite\",\"width\":%u,\"height\":%u,\"frames\":[",first,first,rect.width,rect.height);
    const unsigned palette[]={0,0,2,3,4,9,6,7,8,1,10,11,12,13,14,15};
    for (unsigned i=0;i<count;++i) {
        btp_sprite_rect(first+i,&rect);printf("%s[",i ? "," : "");
        for (unsigned y=0;y<rect.height;++y) {
            printf("%s\"",y ? "," : "");
            for (unsigned x=0;x<rect.width;++x) {
                unsigned color=r->sprites.pixels[(rect.y+y)*320+rect.x+x]&15u;
                printf("%06x%02x",btp_palette[palette[color]]&0xffffffu,color ? 255u : 0u);
            }
            putchar('"');
        }
        putchar(']');
    }
    puts("]}");free(r);return !ferror(stdout);
}

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

static int original_units(const char *output,const char *cache)
{
    /* Reuse the authored-definition exporter for local original templates.
       Only symbolic numeric blueprints leave the cache; no binary resources
       or sprites are copied. Library prices are an explicit authored estimate. */
    BtpCombatData *combat=calloc(1,sizeof *combat);BtpRoster *roster=calloc(1,sizeof *roster);
    BtpError error={0};BtpCombatProfile profile={0};int ok=combat && roster;
    if (ok) ok=btp_combat_data_load(cache,combat,&error);
    if (ok) {
        strcpy(roster->package,"chi-original");strcpy(roster->version,"1.0.0");
        const BtpMechTemplate kinds[]={BTP_MECH_LOAN,BTP_MECH_COMMANDO,BTP_MECH_JENNER,BTP_MECH_ENCOUNTER,BTP_MECH_ARENA,BTP_MECH_URBANMECH};
        const unsigned counts[]={3,1,1,3,11,1};
        for (unsigned group=0;group<6;++group) for (unsigned i=0;i<counts[group];++i) {
            const uint8_t *m=btp_mech_template(combat,kinds[group],i);unsigned weapons=0;
            for (unsigned at=51;at<86;++at) weapons+=(m[at]&127u)>=16 && (m[at]&127u)<=32;
            if (!weapons || weapons>10 || m[16]<20 || m[16]>100 || !m[49]) continue;
            unsigned found=0;while(found<roster->count && memcmp(roster->mechs[found].record,m,15))++found;
            if(found<roster->count)continue;
            BtpRosterMech *unit=&roster->mechs[roster->count++];memcpy(unit->record,m,125);
            snprintf(unit->id,sizeof unit->id,"chi-original:template-%u",roster->count);
            unit->price=(uint32_t)m[16]*350u;
            unit->record[124]=(uint8_t)(btp_mech_record_sprite(m,0)==146 ? 193 : 192);
            /* Template damage/actor flags are instance state. Export intact
               capacities, keeping armament, gait and heat-sink definitions. */
            for(unsigned at=17;at<36;++at)if(unit->record[at+69]>unit->record[at])unit->record[at]=unit->record[at+69];
            /* The training Chameleon has dummy structure, including zero
               limbs. Use the minimum compatible with its armour for this
               authored adaptation, documented with the library entry. */
            for(unsigned part=0;part<8;++part) {
                unsigned armor=unit->record[17+part];
                if(part==1)armor+=unit->record[25];
                if(part==4)armor+=unit->record[26];
                if(part==6)armor+=unit->record[27];
                if(part==3 && armor>=3)armor-=3;
                unsigned minimum=(armor+1u)/2u;if(!minimum)minimum=1;
                if(unit->record[28+part]<minimum)unit->record[28+part]=(uint8_t)minimum;
            }
            for(unsigned at=36;at<38;++at)unit->record[at]=m[at+69];
            for(unsigned at=51,bin=0;at<86;++at) {
                unsigned type=m[at]&127u;unit->record[at]=(uint8_t)type;
                if(type>=16 && type<=32) {
                    unsigned consuming=(type>=20 && type<=24) || type>=26;
                    unit->ammo_cost[bin]=(uint8_t)(consuming ? 3u : 0u);
                    unit->record[39+bin]=(uint8_t)(consuming ? (m[107+bin] && m[107+bin]!=255 ? m[107+bin] : 20u) : 255u);
                    ++bin;
                }
            }
        }
        ok=roster->count && btp_definitions_export(output,roster,combat,&profile,error.text);
    }
    if(!ok)fprintf(stderr,"%s\n",error.text);
    free(combat);free(roster);return ok;
}

int main(int argc,char **argv)
{
    if (argc==4 && !strcmp(argv[1],"formation") && !strcmp(argv[2],"--combat-data")) {
        BtpCombatData *c=calloc(1,sizeof *c);BtpError error={0};int ok=c && btp_combat_data_load(argv[3],c,&error);
        if (ok) {
            fputs("{\"people\":[",stdout);
            for (unsigned i=0;i<8;++i) printf("%s[%d,%d]",i ? "," : "",c->formation_x[i],c->formation_y[i]);
            fputs("],\"mechs\":[",stdout);
            for (unsigned i=0;i<4;++i) printf("%s[%d,%d]",i ? "," : "",c->mech_formation_x[i],c->mech_formation_y[i]);
            puts("]}");
        } else fprintf(stderr,"%s\n",c ? error.text : "Cannot allocate formation data");
        free(c);return ok ? 0 : 1;
    }
    if(argc==5 && !strcmp(argv[1],"export-original-units") && !strcmp(argv[3],"--combat-data"))
        return original_units(argv[2],argv[4]) ? 0 : 1;
    if (argc>=2 && !strcmp(argv[1],"source-sprite")) {
        if ((argc!=6 && argc!=8) || strcmp(argv[2],"--data") || strcmp(argv[4],"--sprite") || (argc==8 && strcmp(argv[6],"--frames"))) {
            fputs("Usage: btp-project source-sprite --data DIRECTORY --sprite 0..375 [--frames 1..32]\n",stderr);return 2;
        }
        char *end;unsigned long first=strtoul(argv[5],&end,10);if (!*argv[5] || *end || first>=BTP_SPRITE_COUNT) return 2;
        unsigned long count=1;
        if (argc==8) { count=strtoul(argv[7],&end,10);if (!*argv[7] || *end || !count || count>32) return 2; }
        return source_sprite(argv[3],(unsigned)first,(unsigned)count) ? 0 : 1;
    }
    if (argc>=2 && !strcmp(argv[1],"preview-tiles")) {
        if (argc!=6 || strcmp(argv[2],"--data") || strcmp(argv[4],"--sheet")) {
            fputs("Usage: btp-project preview-tiles --data DIRECTORY --sheet chi:land|chi:destroyed\n",stderr);return 2;
        }
        return preview_tiles(argv[3],argv[5]) ? 0 : 1;
    }
    if (argc==4 && !strcmp(argv[1],"terrain-animations") && !strcmp(argv[2],"--data"))
        return terrain_animations(argv[3]) ? 0 : 1;
    if (argc<3) {
        fputs("Usage:\n  btp-project validate DIRECTORY\n  btp-project validate-content FILE\n"
            "  btp-project export NEW_DIRECTORY --roster FILE --combat-data FILE\n"
            "  btp-project export-original-units NEW_FILE --combat-data FILE\n"
            "  btp-project preview-tiles --data DIRECTORY --sheet chi:land|chi:destroyed\n"
            "  btp-project terrain-animations --data DIRECTORY\n"
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

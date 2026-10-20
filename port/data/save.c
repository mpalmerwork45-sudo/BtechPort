#include "data/save.h"
#include "core/menu.h"
#include "core/cache.h"
#include "core/party.h"
#include "core/roster_game.h"
#include "data/project.h"
#include "core/events.h"
#include <errno.h>
#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#include <fcntl.h>
#include <io.h>
#include <sys/stat.h>
#endif

enum { HEADER_BYTES = 16, UPDATED_HEADER_BYTES = 112, PROJECT_HEADER_BYTES = 160 };
static int fail(BtpError *e, const char *message)
{
    if (e) snprintf(e->text,sizeof e->text,"%s",message);
    return 0;
}
static int io_fail(BtpError *e, const char *message)
{
    if (e) snprintf(e->text,sizeof e->text,"%s: %s",message,strerror(errno));
    return 0;
}
static uint32_t get32(const uint8_t *b)
{
    return (uint32_t)b[0] | (uint32_t)b[1]<<8 | (uint32_t)b[2]<<16 | (uint32_t)b[3]<<24;
}
static void put32(uint8_t *b, uint32_t n)
{
    for (unsigned i = 0; i < 4; ++i) b[i] = (uint8_t)(n>>(8*i));
}
static uint32_t checksum(const uint8_t *b, size_t n)
{
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < n; ++i) {
        crc ^= b[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc>>1) ^ (crc & 1u ? UINT32_C(0xedb88320) : 0u);
    }
    return ~crc;
}
int btp_save_is_updated(const char *path)
{
    if (!path) return 0;
    FILE *f=fopen(path,"rb");if (!f) return 0;
    char tag[4];int updated=fread(tag,1,4,f)==4 && (!memcmp(tag,"BTU1",4) || !memcmp(tag,"BTU2",4));
    fclose(f);return updated;
}
static int decode(const uint8_t *b, size_t n, BtpState *s, const BtpResources *r)
{
    BtpState context={.map_id=n>=24 ? b[16] : 1,.entry_slot=n>=24 ? b[22] : 0};
    if (n>=4096 && b[4]>=17) context.campaign.building=b[2658];
    if (n>=19292 && b[4]>=27) { context.cache.active=b[18483];context.story_flags[66]=b[11426]; }
    if (n>=19305 && b[4]>=28) { context.campaign.invasion=b[2399];context.late.invasion_event=b[19302]; }
    if (n>=19306 && b[4]>=29) context.yard.active=b[19305];
    if (n>=19886 && b[4]>=30) context.disk_origin=b[19306+sizeof context.yard];
    if (n>=20185 && b[4]>=48) {
        if (!btp_events_decode(&context,b+20057)) return 0;
        if (b[4]==48) context.event.map=(uint16_t)(context.map_id-16u);
    }
    if (n<24 || !btp_state_decode(b,n,btp_active_map(r,&context),btp_state_bld(r,&context),s)) return 0;
    if (s->event.enabled && n>=20185 && b[20057+127]<2) {
        /* The first authored-world saves used the original 128-column
           discovery bitmap. Repack it once into the bounded planet regions;
           the surrounding save envelope still requires identical content. */
        const BtpAdventure *a=btp_adventure(r);const BtpScene *m=btp_scene(r,s);
        if (!a || !m || a->world_count>1) return 0;
        if (a->world_count) {
            uint8_t old[2048];memcpy(old,s->explored,sizeof old);memset(s->explored,0,sizeof s->explored);
            for (unsigned i=0;i<a->map_count;++i) {
                const BtpScene *map=&a->maps[i];
                if (map->world && i!=a->worlds[map->world-1].base) continue;
                unsigned ox=map->world ? 0 : map->origin_x/8,oy=map->world ? 0 : map->origin_y/8;
                for (unsigned y=0;y<map->explore_height;++y) for (unsigned x=0;x<map->explore_width;++x) {
                    unsigned bit=map->explore_offset+y*map->explore_width+x;
                    if (old[(oy+y)*16+(ox+x)/8]&(128u>>((ox+x)&7u))) s->explored[bit/8]|=(uint8_t)(128u>>(bit&7u));
                }
            }
        }
        s->event.planet=(uint8_t)m->world;s->event.explore_offset=(uint16_t)m->explore_offset;
        s->event.explore_width=(uint8_t)m->explore_width;s->event.explore_height=(uint8_t)m->explore_height;
    }
    return btp_events_valid(s,r);
}
int btp_save_write(const char *path, const BtpState *s, const BtpResources *r, BtpError *e)
{
    if (!path || !*path || !s || !r) return fail(e,"Invalid save request");
    int updated=r->roster.count!=0;
    int project=r->project!=NULL;
    if (!!s->project!=project) return fail(e,"State and project context disagree");
    if (s->combat_profile>1 || (!!s->combat_profile != !!s->combat_fingerprint) ||
        (s->combat_profile && !btp_active_combat_profile(s,r)))
        return fail(e,"Current combat rules do not match the loaded Updated profile");
    if (s->campaign.ui>=BTP_MENU_UPDATED_SETTINGS && s->campaign.ui<=BTP_MENU_COMBAT_RULES &&
        (!updated || !r->combat_profile.fingerprint))
        return fail(e,"Updated combat settings require their rule definition");
    size_t header=project ? PROJECT_HEADER_BYTES : updated ? UPDATED_HEADER_BYTES : HEADER_BYTES;
    uint8_t bytes[PROJECT_HEADER_BYTES+BTP_STATE_BYTES] = {'B','T','S','1'};
    if (updated) {
        memcpy(bytes,"BTU1",4);
        memcpy(bytes+16,r->roster.package,32);memcpy(bytes+48,r->roster.version,32);
        put32(bytes+80,r->roster.fingerprint);
    }
    BtpState validated;
    btp_state_encode(s,bytes+header);
    if (updated && bytes[header+4]>=45) {
        /* BTU2 binds rules as well as roster. Old BTU1 remains Legacy. */
        memcpy(bytes,"BTU2",4);put32(bytes+84,s->combat_profile);
        put32(bytes+88,s->combat_fingerprint);
    }
    if (project) {
        /* v1 policy deliberately has no automatic migration. Bind every
           authored input before interpreting local unit handles or orders. */
        memset(bytes+16,0,PROJECT_HEADER_BYTES-16);memcpy(bytes,"BTG1",4);
        memcpy(bytes+16,r->project->id,32);memcpy(bytes+48,r->project->version,32);
        memcpy(bytes+80,r->project->digest,32);
        put32(bytes+112,s->combat_profile);put32(bytes+116,s->combat_fingerprint);
    }
    /* v44 retains the payload size and edition-specific outer envelopes.
       Older Original and Updated payloads still load through their codecs. */
    if (!decode(bytes+header,BTP_STATE_BYTES,&validated,r))
        return fail(e,"Current state cannot be saved");
    if (!btp_roster_state_valid(s,r)) return fail(e,"Current state does not match its roster package");
    size_t length=header+BTP_STATE_BYTES;
    put32(bytes+4,(uint32_t)(length-HEADER_BYTES));
    put32(bytes+8,checksum(bytes+HEADER_BYTES,length-HEADER_BYTES));
    /* An explicit --save filename can bypass the normal slot namespace.
       Refuse crossing editions even there, retaining the existing save. */
    FILE *existing=fopen(path,"rb");
    if (existing) {
        char tag[PROJECT_HEADER_BYTES];size_t got=fread(tag,1,sizeof tag,existing);fclose(existing);
        if ((project && (got<PROJECT_HEADER_BYTES || memcmp(tag,"BTG1",4) || memcmp(tag+16,bytes+16,96))) ||
            (!project && got>=4 && !memcmp(tag,"BTG1",4)))
            return fail(e,"Cannot overwrite another project/content version's save; choose a separate filename");
        if (got>=4 && ((!updated && (!memcmp(tag,"BTU1",4) || !memcmp(tag,"BTU2",4))) ||
            (updated && (!memcmp(tag,"BTS1",4) || (unsigned char)tag[0]==12))))
            return fail(e,"Cannot overwrite another edition's save; choose a separate filename");
    }
    char pending[4096];
    int n = snprintf(pending,sizeof pending,"%s.tmp",path);
    if (n < 0 || (size_t)n >= sizeof pending) return fail(e,"Save path is too long");
    /* MSVCRT ignores C11's x modifier. Use its exclusive-create descriptor
       API so an existing pending file is preserved on Windows too. */
#ifdef _WIN32
    int fd=_open(pending,_O_WRONLY|_O_CREAT|_O_EXCL|_O_BINARY,_S_IREAD|_S_IWRITE);
    FILE *f=fd<0 ? NULL : _fdopen(fd,"wb");
    if (fd>=0 && !f) { int saved_errno=errno;(void)_close(fd);(void)remove(pending);errno=saved_errno; }
#else
    FILE *f = fopen(pending,"wbx");
#endif
    if (!f) return io_fail(e,"Cannot create pending save");
    int ok = fwrite(bytes,1,length,f) == length;
    if (fclose(f)) ok = 0;
    if (!ok) { io_fail(e,"Cannot write save"); (void)remove(pending); return 0; }
    /* Windows rename cannot replace an existing slot. MoveFileEx performs
       the same-directory replacement without deleting the old save first. */
#ifdef _WIN32
    if (!MoveFileExA(pending,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)) {
        DWORD code=GetLastError();
        if (e) snprintf(e->text,sizeof e->text,"Cannot replace save: Windows error %lu",(unsigned long)code);
        (void)remove(pending);return 0;
    }
#else
    if (rename(pending,path)) { io_fail(e,"Cannot replace save"); (void)remove(pending); return 0; }
#endif
    if (e) e->text[0] = 0;
    return 1;
}
int btp_save_load(const char *path, BtpState *s, const BtpResources *r, BtpError *e)
{
    if (!path || !*path || !s || !r) return fail(e,"Invalid load request");
    FILE *f = fopen(path,"rb");
    if (!f) return io_fail(e,"Cannot open save");
    uint8_t bytes[PROJECT_HEADER_BYTES+BTP_STATE_BYTES+1];
    size_t n = fread(bytes,1,sizeof bytes,f);
    int ok = !ferror(f); if (fclose(f)) ok = 0;
    if (!ok) return fail(e,"Cannot read save");
    int project=n>=4 && !memcmp(bytes,"BTG1",4);
    if (project!=!!r->project) return fail(e,project ? "Project save requires --project with its original content directory" : "Project campaigns require their own saves; start a new project campaign");
    if (n==BTP_ORIGINAL_BYTES && bytes[0]==12) {
        BtpState imported;
        if (!btp_original_decode(bytes,n,&imported,r,e)) return 0;
        /* Importing into Updated creates a new edition campaign. There is
           no saved Updated rule choice in a DOS GAME record, so use the
           edition's Enhanced default, including a held combat encounter. */
        if (r->roster.count && r->combat_profile.fingerprint) { imported.combat_profile=1;imported.combat_fingerprint=r->combat_profile.fingerprint; }
        *s=imported;return 1;
    }
    int v2=project || (n>=4 && !memcmp(bytes,"BTU2",4));
    int updated=v2 || (n>=4 && !memcmp(bytes,"BTU1",4));
    size_t header=project ? PROJECT_HEADER_BYTES : updated ? UPDATED_HEADER_BYTES : HEADER_BYTES;
    if (n < header+24 || (!updated && memcmp(bytes,"BTS1",4)) || get32(bytes+12) ||
        get32(bytes+4) != n-HEADER_BYTES || n > header+BTP_STATE_BYTES ||
        checksum(bytes+HEADER_BYTES,n-HEADER_BYTES) != get32(bytes+8))
        return fail(e,"Save is damaged or uses an unsupported format");
    unsigned saved_count=r->roster.count;
    if (project) {
        if (memcmp(bytes+16,r->project->id,32) || memcmp(bytes+48,r->project->version,32) || memcmp(bytes+80,r->project->digest,32))
            return fail(e,"Project save requires the exact saved content; restore that project or start a new campaign with a separate save filename");
        for (unsigned i=120;i<PROJECT_HEADER_BYTES;++i) if (bytes[i]) return fail(e,"Unsupported project save metadata");
    } else if (updated) {
        if (!r->roster.count) return fail(e,"This save belongs to Updated BTECH CHI");
        saved_count=btp_roster_saved_count(&r->roster,bytes+16,bytes+48,get32(bytes+80));
        if (!saved_count)
            return fail(e,"Updated save requires its original roster or an unchanged extension of it");
        for (unsigned i=v2 ? 92u : 84u;i<UPDATED_HEADER_BYTES;++i) if (bytes[i]) return fail(e,"Unsupported updated save metadata");
        if (v2 && (get32(bytes+84)>1 || (!!get32(bytes+84)!=!!get32(bytes+88))))
            return fail(e,"Unsupported Updated combat profile");
    } else if (bytes[header+4]>40 && bytes[header+4]!=44)
        return fail(e,"Updated state requires an edition-aware save envelope");
    BtpState loaded;
    if (!decode(bytes+header,n-header,&loaded,r) || !btp_roster_state_prefix_valid(&loaded,r,saved_count))
        return fail(e,"Save contains an invalid or unsupported game state");
    unsigned rule_offset=project ? 112u : 84u;
    if (!!loaded.project!=project || (!v2 && (loaded.combat_profile || bytes[header+4]>=45)) ||
        (v2 && ((project ? bytes[header+4]!=47 && bytes[header+4]!=48 && bytes[header+4]!=49 && bytes[header+4]!=50 : bytes[header+4]!=45 && bytes[header+4]!=46) || get32(bytes+rule_offset)!=loaded.combat_profile || get32(bytes+rule_offset+4)!=loaded.combat_fingerprint)) ||
        (loaded.combat_profile && !btp_active_combat_profile(&loaded,r)) ||
        (loaded.campaign.ui>=BTP_MENU_UPDATED_SETTINGS && loaded.campaign.ui<=BTP_MENU_COMBAT_RULES &&
            (!updated || !r->combat_profile.fingerprint)))
        return fail(e,"Save requires its original Updated combat rule definition");
    if (updated && saved_count<r->roster.count && loaded.campaign.ui>=BTP_MENU_BROKER &&
        loaded.campaign.ui<=BTP_MENU_BROKER_RESULT) {
        /* New models can sort before old ones within a class. Preserve the
           held definition, Back, and pending Yes/No, not its old row number.
           Flat legacy saves still use their fingerprinted definition order. */
        unsigned item=loaded.campaign.member+loaded.campaign.selected;
        unsigned indices[BTP_ROSTER_MAX];
        unsigned count=btp_roster_catalogue(&r->roster,loaded.menu.broker_class,r->roster.count,indices);
        if (item==loaded.menu.map_x) item=count;
        else if (loaded.menu.broker_class) {
            item=0;while (item<count && indices[item]!=loaded.menu.map_y) ++item;
        }
        loaded.menu.map_x=(uint16_t)count;
        if (loaded.campaign.ui==BTP_MENU_BROKER) {
            /* An empty old class has no previous model to retain on Back. */
            if (count && loaded.menu.broker_class &&
                btp_roster_class(r->roster.mechs[loaded.menu.map_y].record[16])!=loaded.menu.broker_class)
                loaded.menu.map_y=(uint16_t)indices[0];
            btp_broker_browse(&loaded,r,item);
        }
    }
    if (!btp_roster_state_valid(&loaded,r)) return fail(e,"Save contains an invalid roster state");
    btp_cache_restore_party(&loaded,r);
    /* Earlier arena returns reactivated the checked-in records. Repair only
       a saved Starport foot party with the original parking flag still set;
       arena fights, theft escapes and mounted travel retain their records. */
    if (loaded.map_id==2 && loaded.story_flags[24] && !loaded.story_flags[35] &&
        loaded.party.enabled && !loaded.yard.active && !loaded.campaign.encounter && !loaded.campaign.mounted &&
        (loaded.mode==BTP_EXPLORE || loaded.mode==BTP_ACTIONS)) {
        int on_foot=1;
        for (unsigned i=0;i<8;++i) if (loaded.party.people[i][0]!=255 && loaded.party.people[i][12]<8) on_foot=0;
        if (on_foot) for (unsigned i=0;i<4;++i) btp_party_mech(&loaded,i)[0]=255;
    }
    if (!updated && r->roster.count && r->combat_profile.fingerprint) {
        loaded.combat_profile=1;loaded.combat_fingerprint=r->combat_profile.fingerprint;
    }
    *s = loaded;
    if (e) e->text[0] = 0;
    return 1;
}
int btp_save_edition_slot_path(const char *base,unsigned slot,const BtpResources *r,
    char *path,size_t capacity,BtpError *e)
{
    if (!r || !r->roster.count) return btp_save_slot_path(base,slot,path,capacity,e);
    if (!base) return fail(e,"Invalid save slot base");
    const char *leaf=base,*dot=NULL;
    for (const char *p=base;*p;++p) {
        if (*p=='/' || *p=='\\') { leaf=p+1;dot=NULL; }
        else if (*p=='.') dot=p;
    }
    if (!dot || dot==leaf) dot=base+strlen(base);
    size_t prefix=(size_t)(dot-base);
    if (r->project) {
        char suffix[48];int length=snprintf(suffix,sizeof suffix,"-project-%s",r->project->id);
        if (length>0 && prefix>=(size_t)length && !memcmp(dot-length,suffix,(size_t)length))
            return btp_save_slot_path(base,slot,path,capacity,e);
        char named[4096];int n=snprintf(named,sizeof named,"%.*s-project-%s%s",(int)prefix,base,r->project->id,dot);
        if (n<0 || (size_t)n>=sizeof named) return fail(e,"Project save path is too long");
        return btp_save_slot_path(named,slot,path,capacity,e);
    }
    if (prefix>=8 && !memcmp(dot-8,"-updated",8)) return btp_save_slot_path(base,slot,path,capacity,e);
    char named[4096];
    if (prefix>sizeof named-10 || strlen(dot)>sizeof named-prefix-10) return fail(e,"Save path is too long");
    memcpy(named,base,prefix);memcpy(named+prefix,"-updated",8);strcpy(named+prefix+8,dot);
    return btp_save_slot_path(named,slot,path,capacity,e);
}
int btp_save_slot_path(const char *base,unsigned slot,char *path,size_t capacity,BtpError *e)
{
    if (!base || !path || slot>5 || !capacity) return fail(e,"Invalid save slot");
    const char *leaf=base;
    for (const char *p=base;*p;++p) if (*p=='/' || *p=='\\') leaf=p+1;
    const char *dot=strrchr(leaf,'.');if (!dot) dot=base+strlen(base);
    int n=slot ? snprintf(path,capacity,"%.*s-%u%s",(int)(dot-base),base,slot+1,dot) : snprintf(path,capacity,"%s",base);
    return n>=0 && (size_t)n<capacity ? 1 : fail(e,"Save path is too long");
}
int btp_save_menu(BtpState *s,const BtpResources *r,const char *base,int allow_load,BtpError *e)
{
    unsigned request=s->menu.io;if (!request) return 1;
    char path[4096];int ok=btp_save_edition_slot_path(base,s->menu.slot,r,path,sizeof path,e);
    BtpState candidate=*s;btp_menu_close(&candidate);
    /* Save/Load closes the Space menu outside game_tick. Apply the same
       temporary formation recovery here before publishing that return. */
    if (request==BTP_MENU_IO_SAVE) btp_party_recover(&candidate,r,1);
    if (ok && request==BTP_MENU_IO_LOAD && !allow_load) ok=fail(e,"Loading while recording is unsupported; start a new log after loading");
    if (ok) ok=request==BTP_MENU_IO_SAVE ? btp_save_write(path,&candidate,r,e) : btp_save_load(path,&candidate,r,e);
    if (ok) { btp_party_recover(&candidate,r,1);*s=candidate;return 1; }
    s->menu.io=0;s->menu.notice=(uint8_t)request;s->campaign.ui=BTP_MENU_MESSAGE;s->campaign.selected=0;
    return 0;
}

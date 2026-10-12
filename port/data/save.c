#include "data/save.h"
#include "core/menu.h"
#include <errno.h>
#include <stdio.h>
#include <string.h>

enum { HEADER_BYTES = 16 };
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
static int decode(const uint8_t *b, size_t n, BtpState *s, const BtpResources *r)
{
    BtpState context={.map_id=n>=24 ? b[16] : 1,.entry_slot=n>=24 ? b[22] : 0};
    if (n>=4096 && b[4]>=17) context.campaign.building=b[2658];
    return n >= 24 && btp_state_decode(b,n,btp_active_map(r,&context),
        btp_state_bld(r,&context),s);
}
int btp_save_write(const char *path, const BtpState *s, const BtpResources *r, BtpError *e)
{
    if (!path || !*path || !s || !r) return fail(e,"Invalid save request");
    uint8_t bytes[HEADER_BYTES+BTP_STATE_BYTES] = {'B','T','S','1'};
    BtpState validated;
    btp_state_encode(s,bytes+HEADER_BYTES);
    if (!decode(bytes+HEADER_BYTES,BTP_STATE_BYTES,&validated,r))
        return fail(e,"Current state cannot be saved");
    put32(bytes+4,BTP_STATE_BYTES); put32(bytes+8,checksum(bytes+HEADER_BYTES,BTP_STATE_BYTES));
    char pending[4096];
    int n = snprintf(pending,sizeof pending,"%s.tmp",path);
    if (n < 0 || (size_t)n >= sizeof pending) return fail(e,"Save path is too long");
    /* C11 exclusive creation avoids overwriting an unrelated pending file. */
    FILE *f = fopen(pending,"wbx");
    if (!f) return io_fail(e,"Cannot create pending save");
    int ok = fwrite(bytes,1,sizeof bytes,f) == sizeof bytes;
    if (fclose(f)) ok = 0;
    if (!ok) { io_fail(e,"Cannot write save"); (void)remove(pending); return 0; }
    if (rename(pending,path)) { io_fail(e,"Cannot replace save"); (void)remove(pending); return 0; }
    if (e) e->text[0] = 0;
    return 1;
}
int btp_save_load(const char *path, BtpState *s, const BtpResources *r, BtpError *e)
{
    if (!path || !*path || !s || !r) return fail(e,"Invalid load request");
    FILE *f = fopen(path,"rb");
    if (!f) return io_fail(e,"Cannot open save");
    uint8_t bytes[HEADER_BYTES+BTP_STATE_BYTES+1];
    size_t n = fread(bytes,1,sizeof bytes,f);
    int ok = !ferror(f); if (fclose(f)) ok = 0;
    if (!ok) return fail(e,"Cannot read save");
    if (n==BTP_ORIGINAL_BYTES && bytes[0]==12) return btp_original_decode(bytes,n,s,r,e);
    if (n < HEADER_BYTES+24 || memcmp(bytes,"BTS1",4) || get32(bytes+12) ||
        get32(bytes+4) != n-HEADER_BYTES || n > HEADER_BYTES+BTP_STATE_BYTES ||
        checksum(bytes+HEADER_BYTES,n-HEADER_BYTES) != get32(bytes+8))
        return fail(e,"Save is damaged or uses an unsupported format");
    BtpState loaded;
    if (!decode(bytes+HEADER_BYTES,n-HEADER_BYTES,&loaded,r))
        return fail(e,"Save contains an invalid or unsupported game state");
    *s = loaded;
    if (e) e->text[0] = 0;
    return 1;
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
    char path[4096];int ok=btp_save_slot_path(base,s->menu.slot,path,sizeof path,e);
    BtpState candidate=*s;btp_menu_close(&candidate);
    if (ok && request==BTP_MENU_IO_LOAD && !allow_load) ok=fail(e,"Loading while recording is unsupported; start a new log after loading");
    if (ok) ok=request==BTP_MENU_IO_SAVE ? btp_save_write(path,&candidate,r,e) : btp_save_load(path,&candidate,r,e);
    if (ok) { *s=candidate;return 1; }
    s->menu.io=0;s->menu.notice=(uint8_t)request;s->campaign.ui=BTP_MENU_MESSAGE;s->campaign.selected=0;
    return 0;
}

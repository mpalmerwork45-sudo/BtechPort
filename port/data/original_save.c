#include "data/save.h"
#include "core/party.h"
#include "core/world.h"
#include "core/npc.h"
#include "core/economy.h"
#include <stdio.h>
#include <string.h>

/* Primary 0000:3383..33D8 / 368B..3710: header 12, C614[0F44],
   BUFFER cursor words. Keep unmodeled original bytes, rather than invent them. */
enum { PEOPLE=1, MECHS=0x111, FLAGS=0xcf9, CASH=0xd5d, CURSOR=0xf45,
    TYPES=1+0xd452-0xc614, NEXT=1+0xd456-0xc614, NPCS=1+0xd398-0xc614 };
static unsigned word(const uint8_t *b) { return b[0]|(unsigned)b[1]<<8; }
static uint32_t longword(const uint8_t *b) { return word(b)|(uint32_t)word(b+2)<<16; }
static void setword(uint8_t *b,unsigned n) { b[0]=(uint8_t)n;b[1]=(uint8_t)(n>>8); }
static void setlong(uint8_t *b,uint32_t n) { setword(b,n&65535u);setword(b+2,n>>16); }
static int fail(BtpError *e,const char *message) { if (e) snprintf(e->text,sizeof e->text,"Original save: %s",message);return 0; }
int btp_original_decode(const uint8_t *b,size_t n,BtpState *out,const BtpResources *r,BtpError *e)
{
    if (!b || !out || !r || n!=BTP_ORIGINAL_BYTES || b[0]!=12) return fail(e,"invalid header or length");
    BtpState s;btp_start(&s);s.original.valid=1;memcpy(s.original.bytes,b,n);
    memcpy(s.explored,b+0x4f9,sizeof s.explored);
    /* The original save includes all 64 world-positioned fire/casualty marks. */
    s.terrain_next=b[0xf44];
    for (unsigned i=0;i<64;++i)
        s.terrain_marks[i]=(BtpTerrainMark){b[0xe44+i],b[0xe84+i],b[0xec4+i],b[0xf04+i]};
    memcpy(s.story_flags,b+FLAGS,BTP_STORY_BYTES);s.credits=longword(b+CASH);
    s.allowance_cap=(uint16_t)word(b+FLAGS+51);s.recruitment=s.story_flags[45];s.talk_result=s.story_flags[46];
    for (unsigned i=0;i<3;++i) s.investments[i]=longword(b+CASH+4+4*i);
    memcpy(s.skills,b+PEOPLE+4,3);memcpy(s.mech_skills,b+PEOPLE+7,2);s.technician=b[PEOPLE+9];
    s.apprentice=b[PEOPLE+16]&1u;s.weapon=b[PEOPLE+11];s.armor=b[PEOPLE+13];s.armor_points=b[PEOPLE+14];
    unsigned px=word(b+CURSOR),py=word(b+CURSOR+2);
    if ((px&0xf080u) || (py&0x0f80u)) return fail(e,"unsupported packed cursor bits");
    unsigned x=(px>>8)*128+(px&127u),y=(py>>12)*128+(py&127u);
    if (x>2047 || y>2047) return fail(e,"invalid cursor");
    s.menu.outtakes=s.story_flags[79];if (s.menu.outtakes>2) return fail(e,"invalid outtake preference");
    s.campaign.world_x=(uint16_t)x;s.campaign.world_y=(uint16_t)y;
    s.campaign.mech_x=(uint16_t)x;s.campaign.mech_y=(uint16_t)y;
    s.map_id=(uint8_t)btp_world_location(r,&s,(int)x/2,(int)y/2);
    if (!s.story_flags[4] && s.map_id!=1) return fail(e,"cadet save outside the Citadel");
    s.x_half=(uint16_t)x;s.y_half=(uint16_t)y;
    if (s.map_id) { s.x_half&=127u;s.y_half&=127u; }
    for (unsigned i=0;i<8;++i) { s.npc_pairs[i][0]=b[NPCS+26*i];s.npc_pairs[i][1]=b[NPCS+26*i+1]; }
    if (s.story_flags[4]) {
        s.npc=(BtpNpcState){.rng={70,54,210}};
        s.party.enabled=1;s.party.next_id=b[NEXT];memcpy(s.party.people,b+PEOPLE,136);
        s.party.medical_kit=b[1+0xd450-0xc614];s.party.advanced_kit=b[1+0xd451-0xc614];
        for (unsigned i=0;i<4;++i) {
            uint8_t *m=btp_party_mech(&s,i);memcpy(m,b+MECHS+125*i,125);
            s.party.mech_types[i]=m[0]==255 ? b[TYPES+i] : m[0];
            if (s.party.mech_types[i]!=255) s.campaign.owned=1;
            s.party.mech_x[i]=(uint16_t)x;s.party.mech_y[i]=(uint16_t)y;
        }
        s.campaign.mounted=(uint8_t)(s.party.people[0][12]<4);
        for (unsigned i=0;i<8;++i) { s.party.x[i]=(uint16_t)x;s.party.y[i]=(uint16_t)y; }
        btp_party_follow(&s,r,(uint16_t)x,(uint16_t)y);
    } else {
        s.npc.loop_timer=s.story_flags[23];s.npc.allowance_pending=(uint8_t)btp_economy_below_cap(&s);
        btp_npc_init(&s,&r->map);
    }
    uint8_t encoded[BTP_STATE_BYTES];BtpState validated;btp_state_encode(&s,encoded);
    if (!btp_state_decode(encoded,sizeof encoded,btp_active_map(r,&s),NULL,&validated)) return fail(e,"unsupported game-state projection");
    *out=validated;if (e) e->text[0]=0;return 1;
}
int btp_original_encode(const BtpState *s,uint8_t b[BTP_ORIGINAL_BYTES],BtpError *e)
{
    if (!s || !b || !s->original.valid || s->original.bytes[0]!=12) return fail(e,"export requires an imported original save");
    /* DOS GAME files have no package identity and cannot resolve added units. */
    for (unsigned i=0;i<4;++i) if (btp_roster_custom(i ? s->party.mechs[i-1] : s->campaign.mech))
        return fail(e,"added mechs cannot be exported to an original GAME file");
    if (s->mode!=BTP_EXPLORE || s->checkpoint_valid || s->campaign.encounter || s->mission.phase)
        return fail(e,"finish the active encounter or building before exporting");
    memcpy(b,s->original.bytes,BTP_ORIGINAL_BYTES);memcpy(b+FLAGS,s->story_flags,BTP_STORY_BYTES);
    memcpy(b+0x4f9,s->explored,sizeof s->explored);
    b[0xf44]=s->terrain_next;
    for (unsigned i=0;i<64;++i) {
        const BtpTerrainMark *mark=&s->terrain_marks[i];
        b[0xe44+i]=mark->sprite;b[0xe84+i]=mark->sector;b[0xec4+i]=mark->x;b[0xf04+i]=mark->y;
    }
    b[FLAGS+45]=s->recruitment;b[FLAGS+46]=s->talk_result;setword(b+FLAGS+51,s->allowance_cap);b[FLAGS+79]=s->menu.outtakes;
    setlong(b+CASH,s->credits);for (unsigned i=0;i<3;++i) setlong(b+CASH+4+4*i,s->investments[i]);
    if (s->party.enabled) {
        memcpy(b+PEOPLE,s->party.people,136);b[NEXT]=s->party.next_id;
        b[1+0xd450-0xc614]=s->party.medical_kit;b[1+0xd451-0xc614]=s->party.advanced_kit;
        for (unsigned i=0;i<4;++i) {
            const uint8_t *m=i ? s->party.mechs[i-1] : s->campaign.mech;memcpy(b+MECHS+125*i,m,125);
            b[TYPES+i]=m[0]==255 ? s->party.mech_types[i] : 255;
        }
    } else {
        memcpy(b+PEOPLE+4,s->skills,3);memcpy(b+PEOPLE+7,s->mech_skills,2);b[PEOPLE+9]=s->technician;
        b[PEOPLE+11]=s->weapon;b[PEOPLE+13]=s->armor;b[PEOPLE+14]=s->armor_points;
        b[PEOPLE+16]=(uint8_t)((b[PEOPLE+16]&254u)|s->apprentice);
    }
    for (unsigned i=0;i<8;++i) { b[NPCS+26*i]=s->npc_pairs[i][0];b[NPCS+26*i+1]=s->npc_pairs[i][1]; }
    unsigned x=s->story_flags[4] ? s->campaign.world_x : 1536u+s->x_half;
    unsigned y=s->story_flags[4] ? s->campaign.world_y : 1536u+s->y_half;
    setword(b+CURSOR,(x/128u)*256u+(x&127u));setword(b+CURSOR+2,(y/128u)*4096u+(y&127u));
    if (e) e->text[0]=0;
    return 1;
}
int btp_original_write(const char *path,const BtpState *s,BtpError *e)
{
    uint8_t b[BTP_ORIGINAL_BYTES];if (!path || !btp_original_encode(s,b,e)) return 0;
    char pending[4096];int n=snprintf(pending,sizeof pending,"%s.tmp",path);
    if (n<0 || (size_t)n>=sizeof pending) return fail(e,"path too long");
    FILE *f=fopen(pending,"wbx");if (!f) return fail(e,"cannot create pending export");
    int ok=fwrite(b,1,sizeof b,f)==sizeof b;if (fclose(f)) ok=0;
    if (!ok || rename(pending,path)) { (void)remove(pending);return fail(e,"cannot write export"); }
    if (e) e->text[0]=0;
    return 1;
}

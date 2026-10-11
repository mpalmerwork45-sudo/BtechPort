#include "core/combat_rules.h"
#include "core/combat.h"
#include "data/resources.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <inttypes.h>

static uint64_t fingerprint(const uint8_t *bytes, size_t count)
{
    uint64_t value = UINT64_C(14695981039346656037);
    for (size_t i = 0; i < count; ++i) value = (value^bytes[i])*UINT64_C(1099511628211);
    return value;
}
static unsigned seed_value(const uint8_t rng[3]) { return rng[0]+256u*rng[1]+65536u*rng[2]; }
int main(int argc, char **argv)
{
    if (argc != 3 && argc != 4) return 2;
    uint8_t *raw = NULL; size_t length = 0; BtpError error; BtpCombatData d;
    if (!btp_read_file(argv[1],&raw,&length,&error) || !btp_combat_data_decode(raw,length,&d)) return 2;
    free(raw); BtpMap map={0};
    if (argc == 4) {
        if (!btp_read_file(argv[3],&raw,&length,&error) || !btp_map_decode(raw,length,&map,&error)) return 2;
        free(raw);
    }
    FILE *file = fopen(argv[2],"r"); if (!file) return 2;
    char line[256]; unsigned cases = 0, failures = 0, number = 0;
    while (fgets(line,sizeof line,file)) {
        ++number; if (line[0] == '#') continue;
        unsigned a,b,c,e,f,g; uint64_t hash; uint8_t rng[3]; int passed = 0;
        if (line[0] == 'D' && sscanf(line+1,"%u %u %u",&a,&b,&c) == 3) {
            rng[0]=(uint8_t)a; rng[1]=(uint8_t)(a>>8); rng[2]=(uint8_t)(a>>16);
            passed = btp_combat_dice(rng) == b && seed_value(rng) == c;
        } else if (line[0] == 'R' && sscanf(line+1,"%u %u %u %u %u %u",&a,&b,&c,&e,&f,&g) == 6) {
            unsigned got = btp_combat_range(&d,a,(int)b,(int)c,(int)e,(int)f);
            passed = got == g;
        } else if (line[0] == 'P' && sscanf(line+1,"%u %u %u %u %u %u",&a,&b,&c,&e,&f,&g) == 6 && a < 3) {
            BtpCombatUnit u = {0}; memcpy(u.record,d.loans[a],125);
            u.heat=(uint8_t)c; u.record[36]=(uint8_t)e; u.record[37]=(uint8_t)f;
            passed = btp_combat_points(&u,b) == (int)g;
        } else if (line[0] == 'K' && sscanf(line+1,"%u %u %u %u %u %u %" SCNx64,&a,&b,&c,&e,&f,&g,&hash) == 7 && a < 3 && b < 125) {
            BtpCombatUnit u = {0}; memcpy(u.record,d.loans[a],125);
            if (e == 1) u.record[b] = 0;
            if (e == 2) u.record[36] = u.record[37] = 0;
            rng[0]=(uint8_t)c; rng[1]=(uint8_t)(c>>8); rng[2]=(uint8_t)(c>>16);
            int dead = btp_combat_critical(&u,&d,b,rng);
            passed = dead == (int)f && seed_value(rng) == g && fingerprint(u.record,125) == hash;
            if (!passed && failures < 8) fprintf(stderr,"got critical %d rng %u hash %016" PRIx64 "\n",dead,seed_value(rng),fingerprint(u.record,125));
        } else if ((line[0] == 'L' || line[0]=='X') && sscanf(line+1,"%u %u %u %u %u",&a,&b,&c,&e,&f) == 5) {
            passed=btp_combat_los(&map,85,(int)a,(int)b,(int)c,(int)e)==(line[0]=='X' ? -1 : (int)f);
        } else if (line[0] == 'N' && sscanf(line+1,"%u %u %u %u %u %" SCNx64,&a,&b,&c,&e,&f,&hash) == 6) {
            BtpCombatUnit u={.x=(uint8_t)a,.y=(uint8_t)b,.direction=6}, other={.x=(uint8_t)c,.y=(uint8_t)e};
            memcpy(u.record,d.loans[0],125); int8_t steps[12][2];
            btp_combat_plan(&map,85,&u,&other,(int)c,(int)e,0,(int)f,steps);
            passed=fingerprint((uint8_t *)steps,24)==hash;
            if (!passed && failures<8) { for (unsigned i=0;i<12;++i) fprintf(stderr," %d,%d",steps[i][0],steps[i][1]); fputc('\n',stderr); }
        } else if (line[0] == 'S') {
            int mode; unsigned w,steps,skill,heat,face,cover,variant,seed,needed,hit,loc,damage,dead,toppled,after;
            if (sscanf(line+1,"%u %d %u %u %u %u %u %u %u %u %u %u %u %u %u %u %" SCNx64,
                &w,&mode,&steps,&skill,&heat,&face,&cover,&variant,&seed,&needed,&hit,&loc,&damage,&dead,&toppled,&after,&hash)!=17) return 2;
            BtpCombatUnit u={.x=64,.y=64,.heat=(uint8_t)heat}, t={.x=68,.y=64,.direction=(uint8_t)face,.cover=(uint8_t)cover};
            memcpy(u.record,d.loans[0],125);memcpy(t.record,d.loans[0],125);
            memset(u.record+51,0,35);u.record[51]=(uint8_t)(w+1);u.record[39]=200;u.record[121]=0;
            if (variant) { memset(t.record+17,1,19);t.record[36]=t.record[37]=0; }
            rng[0]=(uint8_t)seed;rng[1]=(uint8_t)(seed>>8);rng[2]=(uint8_t)(seed>>16);
            BtpShot shot=btp_combat_shoot(&u,&t,&d,0,mode,steps,skill,rng);
            passed=shot.needed==(int16_t)needed && shot.hit==hit && shot.location==loc &&
                shot.damage==(hit ? damage : 0) && shot.destroyed==dead && shot.toppled==toppled &&
                seed_value(rng)==after && fingerprint(t.record,125)==hash && u.record[39]==199 && u.pool==(d.weapons[w][13]&15u);
            if (!passed && failures<8) fprintf(stderr,"shot got TN %d hit %u loc %u damage %u dead %u top %u rng %u hash %016" PRIx64 "\n",
                shot.needed,shot.hit,shot.location,shot.damage,shot.destroyed,shot.toppled,seed_value(rng),fingerprint(t.record,125));
        } else { fclose(file); fprintf(stderr,"Bad vector at %u\n",number); return 2; }
        ++cases;
        if (!passed) { if (failures < 8) fprintf(stderr,"Combat oracle mismatch line %u: %s",number,line); ++failures; }
    }
    fclose(file);
    printf("Combat: %u original instruction cases, %u failures\n",cases,failures);
    return failures ? 1 : 0;
}

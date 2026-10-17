#include "data/unit_data.h"
#include "data/roster.h"
#include "data/definitions.h"
#include <string.h>

const uint8_t *btp_mech_template(const BtpCombatData *d, BtpMechTemplate kind, unsigned index)
{
    if (!d) return NULL;
    switch (kind) {
    case BTP_MECH_LOAN:return index<3 ? d->loans[index] : NULL;
    case BTP_MECH_JENNER:return index ? NULL : d->jenner;
    case BTP_MECH_COMMANDO:return index ? NULL : d->commando;
    case BTP_MECH_ENCOUNTER:return index<3 ? d->encounter_mechs[index] : NULL;
    case BTP_MECH_ARENA:return index<11 ? d->arena_mechs[index] : NULL;
    case BTP_MECH_SPECTATOR:return index ? NULL : d->arena_spectator;
    case BTP_MECH_URBANMECH:return index ? NULL : d->urbanmech;
    default:return NULL;
    }
}

BtpWeaponDefinition btp_weapon_definition(const BtpCombatData *d, unsigned index)
{
    if (!d || index>=33) return (BtpWeaponDefinition){0};
    const uint8_t *w=d->weapons[index];
    return (BtpWeaponDefinition){.name=w,.damage=w[11],.projectiles=w[12],
        .heat=w[13]&15u,.near_range=w[14]>>5,.medium_range=w[14]&31u,
        .far_range=w[15],.skill=w[16]};
}

BtpWeaponDefinition btp_unit_weapon_definition(const BtpCombatData *d,const BtpCombatUnit *u,unsigned mount)
{
    const BtpAuthoredWeapon *w=u->infantry ? NULL : btp_authored_weapon(d->definitions,u->record,mount);
    if (w) {
        static const unsigned cluster[]={1,1,1,1,1,1,1,1,1,1,4,6,7,8,2,3,5};
        return (BtpWeaponDefinition){.name=(const uint8_t *)w->label,.damage=w->damage,.projectiles=cluster[w->behavior],
            .heat=w->heat,.near_range=w->near_range,.medium_range=w->medium_range,.far_range=w->far_range,.skill=3};
    }
    unsigned type=mount==11 && !u->infantry ? 33u : btp_combat_weapon_type(u,mount)&127u;
    return btp_weapon_definition(d,type ? type-1u : 33u);
}
unsigned btp_combat_mount_range(const BtpCombatData *d,const BtpCombatProfile *p,
    const BtpCombatUnit *a,const BtpCombatUnit *t,unsigned mount,unsigned *minimum)
{
    unsigned type=mount==11 && !a->infantry ? 33u : btp_combat_weapon_type(a,mount)&127u;
    if (minimum) *minimum=0;
    if (!type) return 3;
    const BtpAuthoredWeapon *w=a->infantry ? NULL : btp_authored_weapon(d->definitions,a->record,mount);
    if (!w || (p && btp_combat_profile_lrm(type-1u))) return btp_combat_profile_range(d,p,type-1u,a,t,minimum);
    /* Authored ranges are map-distance thresholds, already expanded out of
       the packed DOS fields. No global weapon table is patched: two mounts
       with the same visual behavior may have different damage/heat/ranges. */
    unsigned distance=btp_combat_shot_distance(a,t);
    return distance<w->near_range ? 0u : distance<w->medium_range ? 1u : distance<w->far_range ? 2u : 3u;
}

unsigned btp_mech_walk_points(const uint8_t m[125]) { return m[49]; }
unsigned btp_mech_jump_points(const uint8_t m[125]) { return m[50]; }

unsigned btp_mech_sprite_base(unsigned tag,int enemy)
{
    /* DS:140E gives enemy Jenner/UrbanMech atlas base 0. The owned-vehicle
       dispatcher at 14D3:0E54 instead uses 146 for every non-Locust tag. */
    return tag=='L' || (enemy && (tag=='J' || tag=='U' || tag=='s')) ? 0u : 146u;
}
unsigned btp_mech_record_sprite(const uint8_t m[125],int enemy)
{
    /* Custom records carry an explicit presentation family. Their name's
       first letter must not select a Locust, Stinger or infantry animation. */
    return btp_roster_custom(m) ? (m[124]&1u ? 146u : 0u) : btp_mech_sprite_base(m[0],enemy);
}

unsigned btp_mech_refit_index(const uint8_t m[125])
{
    /* The held service quote uses the model index even after its upgrade has
       been applied. Eligibility (stage 3) remains the service caller's check. */
    return !m || btp_roster_custom(m) || m[123]>3 ? 8u : m[123]+(m[124]==1 ? 4u : 0u);
}
unsigned btp_mech_refit_price(const BtpCombatData *d,unsigned recipe)
{
    return d && recipe<8 ? d->refit_prices[recipe] : 0;
}
int btp_mech_apply_refit(const BtpCombatData *r,uint8_t m[125],unsigned choice)
{
    if (!r || !m || choice>=8) return 0;
    /* Original recipes mutate instance bytes only. Preserve their exact copy
       sources, including choice 6's current-armour source for both blocks. */
    switch (choice) {
    case 0:m[65]=m[51]=17;m[108]=m[107]=m[40]=m[39]=255;m[124]=1;break;
    case 1:m[79]=17;m[108]=m[40]=255;memcpy(m+17,r->loans[0]+17,11);memcpy(m+86,r->loans[0]+86,11);m[124]=1;break;
    case 2:m[67]=m[66]=m[52]=m[51]=16;memset(m+107,255,5);memset(m+39,255,5);m[124]=1;break;
    case 3:m[74]=m[65]=17;m[42]=m[41];m[110]=m[109];m[109]=m[108]=m[41]=m[40]=255;
        memcpy(m+17,r->commando_armour,11);memcpy(m+86,r->commando_armour,11);m[124]=1;break;
    case 4:m[49]=7;m[117]=0;m[73]=m[59]=16;m[111]=m[110]=m[43]=m[42]=255;m[124]|=2;break;
    case 5:m[50]=0;m[83]=m[51]=m[85]=17;memset(m+109,255,3);memset(m+41,255,3);m[124]|=2;break;
    case 6:m[50]=0;memcpy(m+17,r->loans[0]+17,11);memcpy(m+86,r->loans[0]+17,11);
        m[84]=m[83]=17;m[113]=m[112]=m[45]=m[44]=255;m[124]|=2;break;
    case 7:memset(m+79,16,6);m[85]=17;memset(m+107,255,10);memset(m+39,255,10);m[124]|=2;break;
    }
    return 1;
}

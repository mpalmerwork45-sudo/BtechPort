#include "data/unit_data.h"
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

unsigned btp_mech_walk_points(const uint8_t m[125]) { return m[49]; }
unsigned btp_mech_jump_points(const uint8_t m[125]) { return m[50]; }

unsigned btp_mech_sprite_base(unsigned tag,int enemy)
{
    /* DS:140E gives enemy Jenner/UrbanMech atlas base 0. The owned-vehicle
       dispatcher at 14D3:0E54 instead uses 146 for every non-Locust tag. */
    return tag=='L' || (enemy && (tag=='J' || tag=='U' || tag=='s')) ? 0u : 146u;
}

unsigned btp_mech_refit_index(const uint8_t m[125])
{
    /* The held service quote uses the model index even after its upgrade has
       been applied. Eligibility (stage 3) remains the service caller's check. */
    return !m || m[123]>3 ? 8u : m[123]+(m[124]==1 ? 4u : 0u);
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

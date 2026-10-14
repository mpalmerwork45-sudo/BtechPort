#include "core/combat_rules.h"
#include "core/npc.h"
#include <string.h>
#include <stdlib.h>

int btp_combat_data_decode(const uint8_t *b, size_t n, BtpCombatData *d)
{
    if (!b || !d) return 0;
    int v11=n==BTP_COMBAT_DATA_BYTES && !memcmp(b,"BTCB",4);
    int v10=v11 || (n==BTP_COMBAT_DATA_V10_BYTES && !memcmp(b,"BTCA",4));
    int v9=v10 || (n==BTP_COMBAT_DATA_V9_BYTES && !memcmp(b,"BTC9",4));
    int v8=v9 || (n==BTP_COMBAT_DATA_V8_BYTES && !memcmp(b,"BTC8",4));
    int v7=v8 || (n==BTP_COMBAT_DATA_V7_BYTES && !memcmp(b,"BTC7",4));
    int v6=v7 || (n==BTP_COMBAT_DATA_V6_BYTES && !memcmp(b,"BTC6",4));
    int v5=v6 || (n==BTP_COMBAT_DATA_V5_BYTES && !memcmp(b,"BTC5",4));
    int v4=v5 || (n==BTP_COMBAT_DATA_V4_BYTES && !memcmp(b,"BTC4",4));
    int v3=v4 || (n==BTP_COMBAT_DATA_V3_BYTES && !memcmp(b,"BTC3",4));
    int v2=v3 || (n==BTP_COMBAT_DATA_V2_BYTES && !memcmp(b,"BTC2",4));
    if (!v2 && (n!=BTP_COMBAT_DATA_V1_BYTES || memcmp(b,"BTC1",4))) return 0;
    BtpCombatData v={0}; size_t p = 4;
#define COPY(field) do { memcpy(v.field,b+p,sizeof v.field); p += sizeof v.field; } while (0)
    COPY(loans); COPY(weapons); COPY(arcs); COPY(locations); COPY(clusters);
    COPY(critical_start); COPY(critical_count);
    if (v2) { COPY(poses);COPY(reaction);COPY(impact); }
    if (v3) { COPY(jenner); }
    if (v4) { COPY(commando);COPY(rex_skills);COPY(rex_x);COPY(rex_y);COPY(encounter_weapons);COPY(encounter_mechs); }
    if (v5) { for (unsigned i=0;i<8;++i) { v.refit_prices[i]=(uint16_t)(b[p]|(unsigned)b[p+1]<<8);p+=2; } COPY(ammo_prices);COPY(commando_armour); }
    if (v6) { COPY(building_portraits);for (unsigned i=0;i<26;++i) if (v.building_portraits[i]>=22) return 0; }
    if (v7) {
        v.sound_calibration=(uint16_t)(b[p]|(unsigned)b[p+1]<<8);p+=2;
        for (unsigned i=0;i<314;++i) { v.sound_words[i]=(uint16_t)(b[p]|(unsigned)b[p+1]<<8);p+=2; }
        if (!btp_sound_programs(&v)) return 0;
    }
    if (v8) {
        memcpy(v.medical,b+p,v9 ? 32u : 24u);p+=v9 ? 32u : 24u;
        COPY(formation_x);COPY(formation_y);COPY(mech_formation_x);COPY(mech_formation_y);
        for (unsigned i=0;i<8;++i) { v.medical_prices[i]=(uint16_t)(b[p]|(unsigned)b[p+1]<<8);p+=2; }
    }
    if (v10) {
        COPY(cache_tx);COPY(cache_ty);COPY(cache_color);COPY(cache_dx);COPY(cache_dy);
        COPY(cache_red);COPY(cache_blue);COPY(cache_yellow);
        for (unsigned i=0;i<7;++i) { v.cache_password[i]=(uint16_t)(b[p]|(unsigned)b[p+1]<<8);p+=2;if (v.cache_password[i]>=768) return 0; }
        COPY(cache_secret);COPY(cache_door_tiles);
        COPY(cache_mini_colors);
        for (unsigned i=0;i<33;++i) if (v.cache_tx[i]>127 || v.cache_ty[i]>127 || v.cache_color[i]>2) return 0;
        for (unsigned i=0;i<12;++i) if (v.cache_dx[i]>126 || v.cache_dy[i]>126 || v.cache_red[i]>33 || v.cache_blue[i]>33 || v.cache_yellow[i]>33) return 0;
        for (unsigned i=0;i<2;++i) for (unsigned j=0;j<250;++j) if (v.cache_mini_colors[i][j]>15) return 0;
    }
    if (v11) { COPY(arena_mechs);COPY(arena_spectator);COPY(urbanmech);COPY(arena_levels);COPY(arena_reduction);COPY(special_x);COPY(special_y); }
#undef COPY
    for (unsigned i = 0; i < 15; ++i) if (v.arcs[i] > 3) return 0;
    for (unsigned i = 2; i < 46; ++i) if (v.locations[i] < 17 || v.locations[i] > 27) return 0;
    for (unsigned i = 15; i < 33; ++i)
        if (!v.weapons[i][12] || v.weapons[i][12] > 8 || v.weapons[i][11] > 20) return 0;
    for (unsigned i = 0; i < 8; ++i)
        if (v.critical_start[i] < 51 || v.critical_start[i]+v.critical_count[i] > 86) return 0;
    if (v2) {
        for (unsigned g=0;g<18;++g) for (unsigned dir=0;dir<8;++dir) {
            unsigned count=v.poses[g][dir][0];if (!count || count>8) return 0;
            for (unsigned j=0;j<8;++j) if (j<count ? v.poses[g][dir][j+1]>127 : v.poses[g][dir][j+1]) return 0;
        }
        for (unsigned i=0;i<4;++i) if (v.reaction[i]>127) return 0;
        for (unsigned i=0;i<3;++i) if (v.impact[i]>125) return 0;
    }
    *d = v; return 1;
}
unsigned btp_combat_die(uint8_t rng[3])
{
    unsigned value; do { value = btp_rng_next(rng)&7u; } while (value > 5);
    return value+1;
}
unsigned btp_combat_dice(uint8_t rng[3])
{
    unsigned first = btp_combat_die(rng); return first+btp_combat_die(rng);
}
unsigned btp_combat_direction(int x, int y, int tx, int ty)
{
    /* 187F:0971: octants include the exact 2:1 boundary in both axes. */
    int dx = tx-x, dy = y-ty;
    static const uint8_t direction[16] = {255,6,2,255,4,5,3,255,0,7,1,255,255,255,255,255};
    unsigned mask = (2*dy >= abs(dx) ? 8u : 0u) | (-2*dy >= abs(dx) ? 4u : 0u) |
        (2*dx >= abs(dy) ? 2u : 0u) | (-2*dx >= abs(dy) ? 1u : 0u);
    return direction[mask];
}
unsigned btp_combat_distance(int x, int y, int tx, int ty)
{
    unsigned dx = (unsigned)abs(tx-x), dy = (unsigned)abs(ty-y);
    return dx > dy ? dx/2+dy : dy/2+dx;
}
unsigned btp_combat_range(const BtpCombatData *d, unsigned w, int x, int y, int tx, int ty)
{
    if (w >= 33) return 3;
    if (btp_combat_distance(x,y,tx,ty) > 3) {
        if (x < tx) --tx;
        if (x > tx) ++tx;
        if (y < ty) ty -= 2;
    }
    unsigned distance = btp_combat_distance(x,y,tx,ty);
    unsigned medium = d->weapons[w][14]&31u, near = d->weapons[w][14]>>5;
    if (d->weapons[w][12] < 128 && w != 32) { medium *= 3; near *= 3; }
    return distance < near ? 0u : distance < medium ? 1u : distance < d->weapons[w][15] ? 2u : 3u;
}
unsigned btp_combat_weapon_count(const BtpCombatUnit *u)
{
    if (u->infantry) return 1;
    unsigned count = 0;
    for (unsigned i = 51; i < 86; ++i) {
        unsigned type = u->record[i]&127u;
        if (type >= 16 && type <= 32) ++count;
    }
    return count;
}
unsigned btp_combat_weapon_type(const BtpCombatUnit *u,unsigned index)
{
    /* 0D43 lists the raw critical-slot value even if ammunition is empty
       or its high destroyed bit is set. Firing eligibility is separate. */
    if (u->infantry) return index ? 0u : u->record[11]+1u;
    for (unsigned i=51,n=0;i<86;++i) {
        unsigned type=u->record[i]&127u;
        if (type>=16 && type<=32 && n++==index) return u->record[i];
    }
    return 0;
}
unsigned btp_combat_range_to(const BtpCombatData *d,unsigned w,const BtpCombatUnit *a,const BtpCombatUnit *t)
{
    /* 0E31:0F53 bypasses vehicle footprint offsets for people (IDs
       4..11 and 16..23). Personal targets use their exact coordinates. */
    if (!t->infantry) return btp_combat_range(d,w,a->x,a->y,t->x,t->y);
    if (w>=33) return 3;
    unsigned distance=btp_combat_distance(a->x,a->y,t->x,t->y);
    unsigned medium=d->weapons[w][14]&31u,near=d->weapons[w][14]>>5;
    if (d->weapons[w][12]<128 && w!=32) { medium*=3;near*=3; }
    return distance<near ? 0u : distance<medium ? 1u : distance<d->weapons[w][15] ? 2u : 3u;
}
unsigned btp_combat_weapon(const BtpCombatUnit *u, unsigned index)
{
    if (u->infantry) return index == 0 && u->record[11] < 15 ? u->record[11] : 255;
    unsigned count = 0;
    if (index >= 11 || !u->record[39+index]) return 255;
    for (unsigned i = 51; i < 86; ++i) {
        unsigned type = u->record[i]&127u;
        if (type >= 16 && type <= 32 && count++ == index) return (unsigned)u->record[i]-1u;
    }
    return 255;
}
int btp_combat_points(const BtpCombatUnit *u, unsigned movement)
{
    /* 0E31:046F passes the normalized robot ID + 4 to 103B:2474.
       In this early encounter that reads an inactive party slot and selects
       its minimum of three points, rather than the direct enemy default six. */
    if (u->infantry) {
        /* Executed 103B:2474 uses dexterity, then halves the allowance for
           armour IDs above one. Infantry Run shares this allowance. */
        if (movement==2) return 0;
        unsigned points=3u*u->record[2]/4u;if (points<3) points=3;
        if (u->record[13]>1) points/=2u;
        return (int)(points>8 ? 8 : points);
    }
    int points = u->record[49]; unsigned left = u->record[36], right = u->record[37];
    if (movement == 2) points = u->record[50];
    else {
        if (!((left|right)&8u)) points = 1;
        else {
            unsigned damaged = (left&8u) == 0 || (right&8u) == 0;
            if (damaged) points = (points+1)/2;
            for (unsigned mask = 4; mask; mask >>= 1) {
                if (!(left&mask)) { --points; damaged = 1; }
                if (!(right&mask)) { --points; damaged = 1; }
                if (damaged && !points) points = 1;
            }
        }
        points -= u->heat/5;
        if (movement == 1) points += points/2+(int)(u->record[49]&1u);
    }
    return u->heat == 30 || points < 0 ? 0 : points;
}
void btp_combat_cool(BtpCombatUnit *u, int movement, unsigned steps, unsigned terrain)
{
    if (u->infantry) return;
    int amount = movement+1;
    if (amount == 3 && steps > 3) amount = (int)steps;
    amount += 5*u->record[117] - u->record[38] + u->pool;
    for (unsigned i = 51; i <= 85; ++i) if (u->record[i] == 34) --amount;
    if (u->burning) { amount += 6; --u->burning; }
    if (u->cover && terrain < 16) amount -= 4;
    int heat = (int)(uint8_t)(u->heat+amount);
    if (heat >= 128) heat -= 256;
    u->heat = (uint8_t)(heat < 0 ? 0 : heat > 30 ? 30 : heat); u->pool = 0;
}
static unsigned working(const BtpCombatUnit *u, unsigned start, unsigned count)
{
    unsigned active = 0;
    for (unsigned i = 0; i < count; ++i) active += u->record[start+i] != 0 && u->record[start+i] < 128;
    return active;
}
static unsigned break_component(BtpCombatUnit *u, unsigned start, unsigned count, uint8_t rng[3])
{
    if (!working(u,start,count)) return 0;
    unsigned i = btp_rng_next(rng)&3u;
    for (unsigned tries = 0; tries < count+4; ++tries) {
        if (i >= count) i = 0;
        if (u->record[start+i] && u->record[start+i] < 128) { u->record[start+i] |= 128; return 1; }
        ++i;
    }
    return 0;
}
int btp_combat_critical(BtpCombatUnit *u, const BtpCombatData *d, unsigned loc, uint8_t rng[3])
{
    if (loc < 28 || loc > 35) return 0;
    unsigned roll = btp_combat_dice(rng), hits = roll >= 8 ? (roll-8)/2+1 : 1;
    if (!u->record[loc]) {
        unsigned start = d->critical_start[loc-28], count = d->critical_count[loc-28];
        for (unsigned i = 0; i < count; ++i) if (u->record[start+i]) u->record[start+i] |= 128;
        if (loc == 28) u->record[36] &= 15;
        if (loc == 33) u->record[37] &= 15;
        if (loc == 30) u->record[36] &= 240;
        if (loc == 35) u->record[37] &= 240;
        return 0;
    }
    while (hits) {
        if (loc == 29 || loc == 34) {
            unsigned start = loc == 29 ? 58u : 72u;
            if (!break_component(u,start,7,rng)) break;
            --hits;
        } else if (loc == 31) {
            roll = btp_combat_die(rng);
            if (roll == 1 || roll == 6) { if (!u->record[120]) continue; u->record[120] = 255; --hits; }
            if (roll == 2 || roll == 5) { if (u->record[119] >= 2) continue; ++u->record[119]; --hits; }
            if (roll == 3) { u->record[31] = 0; return 1; }
            if (roll == 4) hits -= break_component(u,85,1,rng);
        } else if (loc == 32) {
            if (btp_combat_die(rng) <= 3) {
                unsigned index = btp_combat_die(rng) <= 3 ? 118u : 117u;
                ++u->record[index]; --hits;
                if (u->record[index] >= (index == 118 ? 2u : 3u)) { u->record[32] = 0; return 1; }
            } else hits -= break_component(u,83,2,rng);
        } else {
            unsigned right = loc >= 33, arm = loc == 28 || loc == 33;
            unsigned actuator = right ? 37u : 36u, mask = arm ? 240u : 15u;
            unsigned start = arm ? (right ? 65u : 51u) : (right ? 81u : 79u), count = arm ? 7u : 2u;
            if (!(u->record[actuator]&mask) && !working(u,start,count)) break;
            roll = btp_combat_die(rng);
            if (roll >= 3 && (u->record[actuator]&mask)) {
                unsigned bit = (8u>>(roll-3)) << (arm ? 4 : 0);
                if (!(u->record[actuator]&bit)) continue;
                u->record[actuator] &= (uint8_t)~bit; --hits;
            } else hits -= break_component(u,start,count,rng);
        }
    }
    return 0;
}
static void apply_damage(BtpCombatUnit *u, const BtpCombatData *d, unsigned loc, unsigned damage,
    uint8_t rng[3], BtpShot *shot)
{
    static const uint8_t overflow[11] = {29,32,34,18,21,18,255,255,23,21,23};
    while (damage && !shot->destroyed) {
        unsigned available = u->record[loc], taken = available < damage ? available : damage;
        u->record[loc] = (uint8_t)(available-taken); damage -= taken;
        if (available && !u->record[loc] && (loc == 28 || loc == 33)) shot->toppled = 1;
        if (loc >= 28 && btp_combat_critical(u,d,loc,rng)) shot->destroyed = 1;
        if ((loc == 31 || loc == 32) && !u->record[loc]) shot->destroyed = 1;
        if (!damage || shot->destroyed) break;
        loc = loc <= 24 ? loc+11 : overflow[loc-25];
        if (loc == 255) shot->destroyed = 1;
    }
}
int btp_combat_can_kick(const BtpCombatUnit *u)
{
    return !u->infantry && u->record[0] != 255 && (u->record[36]&8u) && (u->record[37]&8u);
}
BtpShot btp_combat_attack_unit(BtpCombatUnit *a, BtpCombatUnit *t, const BtpCombatData *d,
    unsigned index, int movement, unsigned steps, unsigned skill, unsigned unit_id, uint8_t rng[3])
{
    int kick = !a->infantry && index == 11;
    BtpShot shot = {0}; unsigned w = kick ? 32 : btp_combat_weapon(a,index);
    if (kick && !btp_combat_can_kick(a)) return shot;
    if (w >= 33 || a->heat >= 30) return shot;
    unsigned range = btp_combat_range_to(d,w,a,t);
    if (range >= 3) return shot;
    if (!a->infantry && !kick && a->record[39+index] != 255) --a->record[39+index];
    if (!a->infantry) a->pool = (uint8_t)(a->pool+(d->weapons[w][13]&15u));
    static const uint8_t movement_penalty[13] = {0,0,0,1,1,2,2,3,3,3,4,4,4};
    if (a->infantry) skill=a->record[4+d->weapons[w][16]];
    int needed = (kick ? 3 : (int)(2*range+4)) + movement+1 + movement_penalty[steps > 12 ? 12 : steps] - (int)skill;
    if (kick) {
        /* 12E8:02C3 passes the raw enemy ID to 0E31:1B44, although its
           hip check uses the normalized record. ID 12 reads inactive slot
           12 in early training, adding all six missing-actuator penalties. */
        if (unit_id==12 || unit_id==13) needed+=6;
        else for (unsigned leg=36;leg<=37;++leg)
            for (unsigned mask=1;mask<=4;mask<<=1) needed += !(a->record[leg]&mask);
    }
    if (!a->infantry && a->record[119]) needed += 2;
    if (!a->infantry) needed += (a->heat >= 8)+(a->heat >= 13)+(a->heat >= 17)+(a->heat >= 24);
    needed += (int)(t->cover/(t->infantry ? 2u : 8u));
    shot.needed = (int16_t)needed;
    if (t->infantry) {
        unsigned damage=127, count=d->weapons[w][12];
        if (count&128u) {
            damage=d->weapons[w][11]&15u;
            for (unsigned n=d->weapons[w][11]>>4;n;--n) damage+=btp_combat_die(rng);
        }
        if (!damage) damage=1;
        count&=127u;
        shot.hit=(uint8_t)((int)btp_combat_dice(rng)>=needed);
        for (unsigned n=0;n<count;++n) {
            if (!shot.hit) break;
            shot.hit=1;
            /* 12E8:0867 halves the caller's damage local itself. Subsequent
               pellets reuse that reduced amount while armour remains. */
            if (t->record[14]) {
                if (t->record[14]>=damage/2) { damage/=2;t->record[14]=(uint8_t)(t->record[14]-damage); }
                else { damage-=t->record[14];t->record[14]=0; }
            }
            unsigned taken=t->record[15]<damage ? t->record[15] : damage;
            t->record[15]=(uint8_t)(t->record[15]-taken);shot.damage=(uint8_t)(shot.damage+taken);
        }
        shot.destroyed=(uint8_t)!t->record[15];return shot;
    }
    unsigned incoming = btp_combat_direction(a->x,a->y,t->x,t->y);
    if (incoming == 255) incoming = 0;
    unsigned arc = d->arcs[7+(int)t->direction-(int)incoming];
    shot.location = d->locations[11*arc+btp_combat_dice(rng)];
    unsigned damage = d->weapons[w][11], cluster = d->weapons[w][12];
    if (kick) { damage=a->record[16]/5u;shot.location=d->locations[3+(btp_rng_next(rng)&8u)]; }
    /* Small personal arms consume the location dice but cannot damage a mech. */
    if (cluster&128u) { shot.location=0;return shot; }
    if (cluster > 1) damage *= d->clusters[7*btp_combat_dice(rng)+cluster];
    shot.hit = (uint8_t)((int)btp_combat_dice(rng) >= needed);
    if (shot.hit) {
        shot.damage = (uint8_t)damage;
        if (w==11) t->burning=3;
        else apply_damage(t,d,shot.location,damage,rng,&shot);
    }
    return shot;
}
BtpShot btp_combat_attack(BtpCombatUnit *a, BtpCombatUnit *t, const BtpCombatData *d,
    unsigned index, int movement, unsigned steps, unsigned skill, uint8_t rng[3])
{
    return btp_combat_attack_unit(a,t,d,index,movement,steps,skill,0,rng);
}
BtpShot btp_combat_shoot(BtpCombatUnit *a, BtpCombatUnit *t, const BtpCombatData *d,
    unsigned index, int movement, unsigned steps, unsigned skill, uint8_t rng[3])
{
    return btp_combat_attack(a,t,d,index,movement,steps,skill,rng);
}

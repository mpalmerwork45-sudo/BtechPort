#ifndef BTP_ROSTER_H
#define BTP_ROSTER_H
#include <stddef.h>
#include <stdint.h>

/* Custom codes use a bounded range plus an explicit marker in byte 124.
   Codes are explicitly assigned by a package, never inferred from its order,
   a display name, a sprite, or a party slot. Saved packages also retain their
   namespaced identities and definition fingerprint. */
enum { BTP_ROSTER_MAX=32, BTP_ROSTER_CODE=160, BTP_ROSTER_ID=64 };
typedef struct {
    char id[BTP_ROSTER_ID];
    uint8_t record[125], ammo_cost[10];
    uint32_t price;
} BtpRosterMech;
typedef struct {
    char package[32], version[32];
    uint32_t fingerprint;
    unsigned count;
    BtpRosterMech mechs[BTP_ROSTER_MAX];
} BtpRoster;
int btp_roster_custom(const uint8_t record[125]);
const BtpRosterMech *btp_roster_definition(const BtpRoster *roster,const uint8_t record[125]);
int btp_roster_load(const char *path,BtpRoster *roster,char error[256]);
#endif

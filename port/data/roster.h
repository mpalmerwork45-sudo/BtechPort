#ifndef BTP_ROSTER_H
#define BTP_ROSTER_H
#include <stddef.h>
#include <stdint.h>

/* Custom codes use a bounded range plus an explicit marker in byte 124.
   Codes are explicitly assigned by a package, never inferred from its order,
   a display name, a sprite, or a party slot. Saved packages also retain their
   namespaced identities and definition fingerprint. */
enum { BTP_ROSTER_MAX=256, BTP_LEGACY_ROSTER_MAX=32, BTP_ROSTER_CODE=160, BTP_ROSTER_ID=64 };
enum { BTP_ROSTER_ALL, BTP_ROSTER_LIGHT, BTP_ROSTER_MEDIUM, BTP_ROSTER_HEAVY, BTP_ROSTER_ASSAULT };
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
unsigned btp_roster_class(unsigned tons);
const char *btp_roster_class_name(unsigned weight_class);
/* Presentation indices only: never reorder definitions/save codes. ALL keeps
   the old flat order for held saves; classes sort by tonnage, name, then ID.
   limit restricts the view to an older, fingerprint-validated save prefix. */
unsigned btp_roster_catalogue(const BtpRoster *roster,unsigned weight_class,
    unsigned limit,unsigned indices[BTP_ROSTER_MAX]);
int btp_roster_custom(const uint8_t record[125]);
const BtpRosterMech *btp_roster_definition(const BtpRoster *roster,const uint8_t record[125]);
int btp_roster_load(const char *path,BtpRoster *roster,char error[256]);
/* Exact match or an unchanged prefix of this catalogue. Zero rejects edits,
   removals, reordered save codes and a different package. */
unsigned btp_roster_saved_count(const BtpRoster *roster,const uint8_t package[32],
    const uint8_t version[32],uint32_t fingerprint);
#endif

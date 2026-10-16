#ifndef BTP_MENU_H
#define BTP_MENU_H
#include "core/game.h"
enum { BTP_MENU_ROOT=1, BTP_MENU_ALLOCATE, BTP_MENU_PERSON, BTP_MENU_EQUIPMENT,
    BTP_MENU_MESSAGE, BTP_MENU_INSPECT, BTP_MENU_SETTINGS, BTP_MENU_STEPS,
    BTP_MENU_SPEED, BTP_MENU_OUTTAKES, BTP_MENU_LOAD, BTP_MENU_SAVE,
    BTP_MENU_MAP, BTP_MENU_HEAL, BTP_MENU_QUIT,BTP_MENU_CREW,BTP_MENU_SEAT,
    BTP_MENU_ABANDON,BTP_MENU_TRANSFER,BTP_MENU_RECIPIENT,BTP_MENU_MECH,
    BTP_MENU_INSPECT_KIND,BTP_MENU_MECH_PICK,BTP_MENU_UPDATED_ROOT,
    BTP_MENU_BROKER,BTP_MENU_BROKER_CONFIRM,BTP_MENU_BROKER_RESULT };
enum { BTP_MENU_IO_SAVE=1, BTP_MENU_IO_LOAD=2 };
void btp_menu_open(BtpState *state);
void btp_menu_close(BtpState *state);
void btp_menu_input(BtpState *state,const BtpResources *resources,BtpAction action);
unsigned btp_actions_count(const BtpState *state);
const char *btp_actions_label(const BtpState *state,unsigned item);
unsigned btp_menu_mech_count(const BtpState *state);
unsigned btp_menu_mech_slot(const BtpState *state,unsigned ordinal);
int btp_actions_valid(const BtpState *state);
void btp_menu_person(const BtpState *state,unsigned member,uint8_t person[17]);
#endif

#ifndef BTP_TRAINING_H
#define BTP_TRAINING_H
#include "core/game.h"
enum { BTP_QUIZ_PARTS = 20, BTP_QUIZ_POINTS = 10 };
extern const uint16_t btp_quiz_x[BTP_QUIZ_POINTS], btp_quiz_y[BTP_QUIZ_POINTS];
extern const uint8_t btp_quiz_answer[BTP_QUIZ_POINTS];
void btp_quiz_begin(BtpState *s);
int btp_quiz_tick(BtpState *s, BtpAction a); /* 1: pass, 2: refusal acknowledged */
void btp_training_native(BtpState *s, const BtpResources *r);
int btp_mission_tick(BtpState *s, const BtpResources *r, BtpAction a); /* result ready */
uint8_t btp_mission_terrain(const BtpState *s, const BtpMap *m);
uint8_t btp_mission_tile(const BtpState *s, const BtpMap *m, int x, int y);
extern const uint8_t btp_rubble_x[8], btp_rubble_y[8];
int btp_training_valid(const BtpState *s);
int btp_training_text(const BtpState *s, const BtpResources *r,
    uint8_t *out, size_t capacity, size_t *length);
#endif

#include "data/chi_missions.h"
#include "data/chi_services.h"
#include "data/project.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stddef.h>

const BtpChiMissionParameter btp_chi_mission_parameters[BTP_MIS_COUNT]={
#include "data/chi_mission_parameters.inc"
};
const BtpChiMissionUnit btp_chi_mission_units[BTP_MUNIT_COUNT]={
#include "data/chi_mission_units.inc"
};
static unsigned original(const BtpResources *r,unsigned id)
{
    if (id>=BTP_MIS_COUNT) return 0;
    const BtpChiMissionParameter *p=&btp_chi_mission_parameters[id];
    if (!r || !p->width) return p->initial;
    const uint8_t *b=(const uint8_t *)&r->combat+p->offset;
    if (p->width==1) return *b;
    uint16_t v;memcpy(&v,b,2);return v;
}
unsigned btp_chi_mission_default(const BtpResources *r,unsigned id)
{ return id>=BTP_MIS_COUNT ? 0 : r && r->project && r->project->chi_missions ? r->project->chi_missions->defaults[id] : original(r,id); }
unsigned btp_chi_mission(const BtpResources *r,unsigned id)
{ return id>=BTP_MIS_COUNT ? 0 : r && r->project && r->project->chi_missions ? r->project->chi_missions->values[id] : original(r,id); }
unsigned btp_chi_training(const BtpResources *r,unsigned assignment,unsigned field)
{
    static const unsigned base[]={BTP_MIS_TRAINING_0_START_X,BTP_MIS_TRAINING_1_START_X,BTP_MIS_TRAINING_2_START_X,
        BTP_MIS_TRAINING_3_START_X,BTP_MIS_TRAINING_4_START_X,BTP_MIS_TRAINING_5_START_X,BTP_MIS_TRAINING_6_START_X,BTP_MIS_TRAINING_7_START_X};
    unsigned limit=assignment<2 ? BTP_TRAIN_PASS_ON_LOSS : BTP_TRAIN_ENEMY_5_Y;
    return assignment<8 && field<=limit ? btp_chi_mission(r,base[assignment]+field) : 0;
}
unsigned btp_chi_training_enemy(const BtpResources *r,unsigned assignment,unsigned enemy,unsigned axis)
{
    return assignment>=2 && assignment<8 && enemy<6 && axis<2 ?
        btp_chi_training(r,assignment,BTP_TRAIN_ENEMY_0_X+enemy*2+axis) : 0;
}
unsigned btp_chi_training_unit(unsigned assignment,unsigned enemy)
{ return assignment>=2 && assignment<8 && enemy<6 ? BTP_MUNIT_TRAINING_2_ENEMY_0+(assignment-2)*6+enemy : BTP_MUNIT_COUNT; }
static const uint8_t *fallback(const BtpResources *r,unsigned role)
{
    if (role>=BTP_MUNIT_COUNT) return NULL;
    const BtpChiMissionUnit *u=&btp_chi_mission_units[role];
    return btp_mech_template(&r->combat,u->kind,role==BTP_MUNIT_PRISON_REWARD ? btp_chi_service(r,BTP_SVC_PRISON_REWARD) : u->index);
}
const uint8_t *btp_chi_mission_unit(const BtpResources *r,unsigned role)
{
    const BtpChiMissions *m=r && r->project ? r->project->chi_missions : NULL;
    return m && role<BTP_MUNIT_COUNT && m->overridden[role] ? m->records[role] : fallback(r,role);
}
static int problem(BtpError *e,const char *key,const char *why)
{ snprintf(e->text,sizeof e->text,"chi-missions.json: $.parameters.%s: %s",key,why);return 0; }
static int cross_validate(const BtpChiMissions *m,BtpError *e)
{
    const unsigned *v=m->values;
    for (unsigned a=0;a<8;++a) {
        char key[64];snprintf(key,sizeof key,"training.%u.return_y_min",a);
        unsigned base=a<2 ? BTP_MIS_TRAINING_0_START_X+a*(BTP_MIS_TRAINING_1_START_X-BTP_MIS_TRAINING_0_START_X) :
            BTP_MIS_TRAINING_2_START_X+(a-2)*(BTP_MIS_TRAINING_3_START_X-BTP_MIS_TRAINING_2_START_X);
        if (v[base+BTP_TRAIN_RETURN_Y_MIN]>v[base+BTP_TRAIN_RETURN_Y_MAX]) return problem(e,key,"return interval is reversed");
        if (a<2 && v[base+BTP_TRAIN_INVASION]) return problem(e,key,"invasion requires a combat assignment (2 through 7)");
        if (a>=2) {
            unsigned count=base+BTP_MIS_TRAINING_2_ENEMY_COUNT-BTP_MIS_TRAINING_2_START_X;
            if (v[count]+v[count+1]>6) { snprintf(key,sizeof key,"training.%u.enemy_count",a);return problem(e,key,"enemy count plus random mask exceeds six native training slots"); }
            if (v[base+BTP_TRAIN_SHELL] && v[base+BTP_TRAIN_INFANTRY]) { snprintf(key,sizeof key,"training.%u.shell",a);return problem(e,key,"a shell must be a mech, not infantry"); }
            for (unsigned i=0;i<6;++i) {
                unsigned x=v[base+BTP_TRAIN_ENEMY_0_X+i*2],y=v[base+BTP_TRAIN_ENEMY_0_Y+i*2];
                unsigned maxx=(v[base+BTP_TRAIN_SHELL] ? v[base+BTP_TRAIN_SHELL_X] : v[base+BTP_TRAIN_SPAWN_X]+v[base+BTP_TRAIN_SPAWN_MASK])+x;
                if (maxx>125 || v[base+BTP_TRAIN_SPAWN_Y]+v[base+BTP_TRAIN_SPAWN_MASK]+y>127) {
                    snprintf(key,sizeof key,"training.%u.enemy.%u.x",a,i);return problem(e,key,"spawn and formation extend beyond the native combat area");
                }
            }
        }
    }
    if (v[BTP_MIS_ARENA_ESCAPE_MIN]>=v[BTP_MIS_ARENA_ESCAPE_MAX]) return problem(e,"arena.escape_min","escape interval is empty or reversed");
    if (v[BTP_MIS_ARENA_RENTAL_ROLL_BASE]+v[BTP_MIS_ARENA_RENTAL_ROLL_MASK]>10) return problem(e,"arena.rental_roll_base","rental roll extends beyond the eleven opponent roles");
    for (unsigned i=0;i<2;++i) {
        unsigned dx=v[BTP_MIS_GUARDS_OFFSET_0_X+i*2],dy=v[BTP_MIS_GUARDS_OFFSET_0_Y+i*2];
        if (v[BTP_MIS_ARENA_WEST_X]+3+dx>125 || v[BTP_MIS_ARENA_EAST_X]+3+dx>125 || v[BTP_MIS_ARENA_SPAWN_Y]+3+dy>127)
            return problem(e,"arena.spawn_y","arena spawn and guard formation extend beyond the native combat area");
    }
    if (v[BTP_MIS_CACHE_SECRET_X_MIN]>v[BTP_MIS_CACHE_SECRET_X_MAX] || v[BTP_MIS_CACHE_SUPPLY_Y_MIN]>v[BTP_MIS_CACHE_SUPPLY_Y_MAX]) return problem(e,"cache.secret_x_min","cache interaction interval is reversed");
    for (unsigned i=0;i<7;++i) for (unsigned j=0;j<i;++j)
        if (v[BTP_MIS_CACHE_PASSWORD_0+i]==v[BTP_MIS_CACHE_PASSWORD_0+j]) return problem(e,"cache.password.0","password cells must be distinct");
    for (unsigned i=0;i<12;++i) for (unsigned axis=0;axis<2;++axis) {
        unsigned id=BTP_MIS_CACHE_DOOR_0_X+i*5+axis;
        if (v[id]&1u) return problem(e,btp_chi_mission_parameters[id].id,"door coordinates must be even half-tile positions");
    }
    return 1;
}
int btp_chi_missions_load(const char *root,const char *file,BtpChiMissions *m,BtpResources *r,BtpDigest *digest,BtpError *e)
{
    char path[4096],format[64];BtpJson j={0};unsigned version;int ok=0;
    uint8_t seen[BTP_MIS_COUNT]={0},units[BTP_MUNIT_COUNT]={0};
    if (!btp_project_path(root,file,path,e) || !btp_json_load(&j,path,e->text)) goto done;
    btp_digest_add(digest,j.source_digest,32);btp_digest_add(digest,"chi-missions-v1",15);
    if (!btp_json_string(&j,btp_json_field(&j,1,"format"),format,sizeof format) || strcmp(format,"btp-chi-missions-v1") ||
        !btp_json_uint(&j,btp_json_field(&j,1,"schema_version"),1,1,&version)) goto done;
    for (unsigned i=0;i<BTP_MIS_COUNT;++i) m->values[i]=m->defaults[i]=original(r,i);
    unsigned params=btp_json_field(&j,1,"parameters");if (!btp_json_type(&j,params,'{')) goto done;
    for (unsigned n=j.nodes[params].first;n;n=j.nodes[n].next) {
        unsigned id=0;while (id<BTP_MIS_COUNT && strcmp(j.nodes[n].key,btp_chi_mission_parameters[id].id)) ++id;
        if (id==BTP_MIS_COUNT || seen[id]++) { btp_json_error(&j,n,"unknown or duplicate mission parameter");goto done; }
        j.nodes[n].used=1;const BtpChiMissionParameter *p=&btp_chi_mission_parameters[id];
        if (!btp_json_uint(&j,n,p->low,p->high,&m->values[id])) goto done;
    }
    unsigned list=btp_json_optional(&j,1,"units");
    if (list) {
        if (!btp_json_type(&j,list,'{')) goto done;
        for (unsigned n=j.nodes[list].first;n;n=j.nodes[n].next) {
            unsigned id=0;while (id<BTP_MUNIT_COUNT && strcmp(j.nodes[n].key,btp_chi_mission_units[id].id)) ++id;
            if (id==BTP_MUNIT_COUNT || units[id]++) { btp_json_error(&j,n,"unknown or duplicate mission unit role");goto done; }
            j.nodes[n].used=1;
            /* An explicit empty role means restore the context's native
               template. The general identifier reader disallows empties. */
            if (!btp_json_type(&j,n,'"')) goto done;
            if (*j.nodes[n].text && !btp_json_string(&j,n,m->units[id],64)) goto done;
        }
        if (!btp_json_done(&j,list)) goto done;
    }
    if (!btp_json_done(&j,params) || !btp_json_done(&j,1) || !cross_validate(m,e)) goto done;
    /* Only decoded tables are overridden; immutable cache bytes and the
       serialized game state remain untouched. */
    for (unsigned i=0;i<BTP_MIS_COUNT;++i) {
        const BtpChiMissionParameter *p=&btp_chi_mission_parameters[i];uint8_t *b=(uint8_t *)&r->combat+p->offset;
        if (p->width==1) *b=(uint8_t)m->values[i];
        if (p->width==2) { uint16_t value=(uint16_t)m->values[i];memcpy(b,&value,2); }
    }
    ok=1;
done:if (!ok && !*e->text) snprintf(e->text,sizeof e->text,"%s: invalid native mission settings",file);btp_json_close(&j);return ok;
}
int btp_chi_missions_resolve(BtpChiMissions *m,const BtpResources *r,const BtpRoster *roster,BtpError *e)
{
    if (!m) return 1;
    static const char *const kinds[]={"loan","jenner","commando","encounter","arena","spectator","urbanmech"};
    for (unsigned role=0;role<BTP_MUNIT_COUNT;++role) {
        const char *id=m->units[role];if (!*id) continue;
        const uint8_t *record=NULL;
        for (unsigned kind=0;kind<7;++kind) for (unsigned index=0;index<11;++index) {
            char name[64];snprintf(name,sizeof name,"native:%s.%u",kinds[kind],index);
            if (!strcmp(id,name)) record=btp_mech_template(&r->combat,(BtpMechTemplate)kind,index);
        }
        for (unsigned i=0;i<roster->count;++i) if (!strcmp(id,roster->mechs[i].id)) record=roster->mechs[i].record;
        if (!record || !record[0] || record[0]==255 || btp_vehicle_kind(record)) {
            snprintf(e->text,sizeof e->text,"chi-missions.json: $.units.%s: expected an existing mech roster ID or native template",btp_chi_mission_units[role].id);return 0;
        }
        memcpy(m->records[role],record,125);m->overridden[role]=1;
    }
    return 1;
}
int btp_chi_mission_reference(const BtpResources *r,const char *id,unsigned *value)
{
    if (!r || !r->project || !r->project->chi_missions) return 0;
    for (unsigned i=0;i<BTP_MIS_COUNT;++i) if (!strcmp(id,btp_chi_mission_parameters[i].id)) { *value=btp_chi_mission(r,i);return 1; }
    return 0;
}
void btp_chi_missions_catalogue(const BtpResources *r)
{
    const BtpChiMissions *m=r->project->chi_missions;
    fputs("{\"format\":\"btp-chi-mission-catalogue-v1\",\"parameters\":[",stdout);
    for (unsigned i=0;i<BTP_MIS_COUNT;++i) {
        const BtpChiMissionParameter *p=&btp_chi_mission_parameters[i];
        printf("%s{\"id\":\"%s\",\"label\":\"%s\",\"group\":\"%s\",\"minimum\":%u,\"maximum\":%u,\"default\":%u,\"value\":%u}",i ? "," : "",p->id,p->label,p->group,p->low,p->high,btp_chi_mission_default(r,i),btp_chi_mission(r,i));
    }
    fputs("],\"units\":[",stdout);
    static const char *const kinds[]={"loan","jenner","commando","encounter","arena","spectator","urbanmech"};
    for (unsigned i=0;i<BTP_MUNIT_COUNT;++i) {
        const BtpChiMissionUnit *u=&btp_chi_mission_units[i];
        printf("%s{\"id\":\"%s\",\"label\":\"%s\",\"default\":\"native:%s.%u\",\"value\":\"%s\"}",i ? "," : "",u->id,u->label,kinds[u->kind],u->index,m ? m->units[i] : "");
    }
    puts("]}");
}

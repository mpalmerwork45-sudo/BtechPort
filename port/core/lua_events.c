#include "core/lua_events.h"
#include "data/project.h"
#include "core/mission_state.h"
#include "core/battle_mission.h"
#include "lua.h"
#include "lauxlib.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

typedef struct { size_t used;unsigned instructions;const BtpResources *r;const BtpState *s; } Host;
static void *allocate(void *ud,void *ptr,size_t old,size_t size)
{
    Host *h=ud;if (!ptr) old=0;
    if (!size) { free(ptr);h->used-=old;return NULL; }
    if (size>262144 || h->used-old>262144-size) return NULL;
    void *p=realloc(ptr,size);if (p) h->used=h->used-old+size;return p;
}
static Host *host(lua_State *l) { return *(Host **)lua_getextraspace(l); }
static void limit(lua_State *l,lua_Debug *debug)
{ (void)debug;Host *h=host(l);h->instructions+=100;if (h->instructions>=10000) luaL_error(l,"event instruction budget exceeded"); }
static int flag(lua_State *l)
{
    Host *h=host(l);const char *id=luaL_checkstring(l,1);const BtpAdventure *a=&h->r->project->adventure;
    for (unsigned i=0;i<a->flag_count;++i) if (!strcmp(a->flags[i],id)) { lua_pushboolean(l,h->s->event.flags[i]);return 1; }
    return luaL_error(l,"unknown flag: %s",id);
}
static int credits(lua_State *l) { lua_pushinteger(l,host(l)->s->credits);return 1; }
static int variable(lua_State *l)
{
    Host *h=host(l);const char *id=luaL_checkstring(l,1);const BtpAdventure *a=&h->r->project->adventure;
    for (unsigned i=0;i<a->variable_count;++i) if (!strcmp(a->variables[i].id,id)) {
        if (a->variables[i].boolean) lua_pushboolean(l,h->s->event.variables[i]!=0);
        else lua_pushinteger(l,h->s->event.variables[i]);
        return 1;
    }
    return luaL_error(l,"unknown variable: %s",id);
}
static int objective(lua_State *l)
{
    Host *h=host(l);const char *id=luaL_checkstring(l,1);const BtpAdventure *a=&h->r->project->adventure;
    for (unsigned i=0;i<a->objective_count;++i) if (!strcmp(a->objectives[i].id,id)) {
        lua_pushstring(l,btp_objective_name(btp_objective_state(h->s,a,i)));return 1;
    }
    return luaL_error(l,"unknown objective: %s",id);
}
static int in_region(lua_State *l)
{
    Host *h=host(l);const char *id=luaL_checkstring(l,1);const BtpAdventure *a=&h->r->project->adventure;
    for (unsigned i=0;i<a->region_count;++i) if (!strcmp(a->regions[i].id,id)) {
        lua_pushboolean(l,btp_mission_region(h->s,a,i));return 1;
    }
    return luaL_error(l,"unknown region: %s",id);
}
static int command(lua_State *l)
{
    Host *h=host(l);const BtpAdventure *a=&h->r->project->adventure;const BtpEventNode *e=&a->nodes[h->s->event.node];
    const char *id=luaL_checkstring(l,1);
    for (unsigned i=0;i<e->count;++i) if (!strcmp(a->nodes[e->next[i]].id,id)) { lua_pushinteger(l,e->next[i]);return 1; }
    return luaL_error(l,"command must name a declared route: %s",id);
}
static int combat_round(lua_State *l) { lua_pushinteger(l,host(l)->s->battle_mission.round);return 1; }
static int group_count(lua_State *l)
{
    Host *h=host(l);const BtpAdventure *a=&h->r->project->adventure;
    const char *id=luaL_checkstring(l,1),*property=luaL_optstring(l,2,"alive");
    const char *const properties[]={"alive","destroyed","deployed","arrived"};unsigned kind=0;
    while (kind<4 && strcmp(property,properties[kind])) ++kind;
    if (kind==4) return luaL_error(l,"group count requires alive, destroyed, deployed or arrived");
    for (unsigned i=0;i<a->group_count;++i) if (!strcmp(id,a->groups[i].id)) {
        lua_pushinteger(l,btp_battle_group_value(h->s,a,i,BTP_CONDITION_GROUP_ALIVE+kind));return 1;
    }
    return luaL_error(l,"unknown combat group: %s",id);
}
static int execute(lua_State *l)
{
    Host *h=host(l);const BtpProject *p=h->r->project;const BtpEventNode *e=&p->adventure.nodes[h->s->event.node];
    const BtpLuaScript *source=&p->scripts[e->argument];
    /* No standard libraries are opened: only immutable queries and declared
       command continuations enter the VM. A new bounded VM is used per call. */
    lua_createtable(l,0,8);
    lua_pushcfunction(l,flag);lua_setfield(l,-2,"flag");
    lua_pushcfunction(l,credits);lua_setfield(l,-2,"credits");
    lua_pushcfunction(l,variable);lua_setfield(l,-2,"variable");
    lua_pushcfunction(l,objective);lua_setfield(l,-2,"objective");
    lua_pushcfunction(l,in_region);lua_setfield(l,-2,"in_region");
    lua_pushcfunction(l,combat_round);lua_setfield(l,-2,"combat_round");
    lua_pushcfunction(l,group_count);lua_setfield(l,-2,"group_count");
    lua_pushcfunction(l,command);lua_setfield(l,-2,"command");lua_setglobal(l,"game");
    if (luaL_loadbufferx(l,source->source,source->length,source->id,"t")!=LUA_OK) return lua_error(l);
    lua_call(l,0,1);return 1;
}
int btp_lua_compile(const char *source,size_t length,char error[256])
{
    Host h={0};lua_State *l=lua_newstate(allocate,&h);
    if (!l) { snprintf(error,256,"Lua allocation failed");return 0; }
    int status=luaL_loadbufferx(l,source,length,"authored event","t");
    if (status!=LUA_OK) snprintf(error,256,"Lua: %.245s",lua_tostring(l,-1));
    lua_close(l);return status==LUA_OK;
}
int btp_lua_event(const BtpResources *r,const BtpState *s,unsigned *next,char error[256])
{
    Host h={.r=r,.s=s};lua_State *l=lua_newstate(allocate,&h);
    if (!l) { snprintf(error,256,"Lua allocation failed");return 0; }
    *(Host **)lua_getextraspace(l)=&h;lua_sethook(l,limit,LUA_MASKCOUNT,100);
    lua_pushcfunction(l,execute);int status=lua_pcall(l,0,1,0),ok=0;
    const BtpEventNode *e=&r->project->adventure.nodes[s->event.node];
    if (status==LUA_OK && lua_isinteger(l,-1)) {
        lua_Integer result=lua_tointeger(l,-1);
        for (unsigned i=0;i<e->count;++i) if (result==e->next[i]) { *next=e->next[i];ok=1; }
    }
    if (!ok) snprintf(error,256,"Lua event %.63s: %.160s",e->id,status==LUA_OK ? "return game.command with a declared route" : lua_tostring(l,-1));
    lua_close(l);return ok;
}

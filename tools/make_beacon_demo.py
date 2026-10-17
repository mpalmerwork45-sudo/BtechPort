#!/usr/bin/env python3
"""Reproduce Last Beacon's independently drawn pixels and authored scenario.

GPL-3.0-only. Reads only this repository's own diagnostic font and invented
Workshop/Frontier examples, never original game resources or extracted caches.
"""
import copy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples/beacon-demo"


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="ascii")


def bitmap(w, h, background=0):
    return [[background for _ in range(w)] for _ in range(h)]


def rect(p, x, y, w, h, color):
    for row in range(max(0, y), min(len(p), y+h)):
        for col in range(max(0, x), min(len(p[0]), x+w)):
            p[row][col] = color


def rows(p):
    return ["".join(format(c, "x") for c in line) for line in p]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    font_source = (ROOT / "port/frontend/pixels.c").read_text()
    alphabet = json.loads(re.search(r'static const char alphabet\[\] = (".*");', font_source)[1])
    glyph_source = font_source.split("static const uint8_t glyphs[][7] = {", 1)[1].split("};", 1)[0]
    glyphs = [[int(v) for v in m.split(",")] for m in re.findall(r"\{([\d,]+)\}", glyph_source)]
    glyph_map = dict(zip(alphabet, glyphs))
    font = ["".join(f"{v:02x}" for v in glyph_map.get(chr(c), glyph_map["?"])) for c in range(32, 128)]
    font[0] = "00" * 7
    tiles = []
    for kind in range(8):
        p = bitmap(16, 16, [2, 6, 1, 2, 8, 6, 8, 2][kind])
        if kind == 0:
            for x, y in [(2, 3), (11, 5), (7, 12), (14, 14)]: rect(p, x, y, 2, 1, 4)
        elif kind == 1:
            for y in (3, 11): rect(p, (y*3)%9, y, 4, 1, 7)
        elif kind == 2:
            for y in (3, 9, 14): rect(p, (y*2)%7, y, 6, 1, 9)
        elif kind == 3:
            rect(p, 7, 9, 3, 7, 6);rect(p, 3, 3, 10, 9, 3);rect(p, 5, 1, 6, 8, 4);rect(p, 5, 5, 2, 2, 5)
        elif kind == 4:
            for y in range(0,16,4): rect(p, 0, y, 16, 1, 1)
            for y in range(1,16,4):
                for x in range((y%3)*2,16,8): rect(p, x, y, 1, 3, 1)
            rect(p, 2, 1, 3, 1, 9)
        elif kind == 5:
            rect(p, 2, 1, 12, 15, 1);rect(p, 4, 3, 8, 13, 9);rect(p, 5, 4, 6, 3, 10);rect(p, 10, 10, 1, 2, 14)
        elif kind == 6:
            rect(p, 2, 9, 12, 6, 1);rect(p, 4, 7, 8, 6, 9);rect(p, 7, 0, 2, 12, 7);rect(p, 4, 1, 8, 3, 10);rect(p, 6, 2, 4, 1, 15)
        else:
            rect(p, 2, 9, 6, 5, 8);rect(p, 8, 3, 7, 10, 1);rect(p, 9, 3, 4, 3, 9)
        tiles.append(rows(p))
    sprites = []
    for kind in range(5):
        frames = []
        for frame in range(4):
            p = bitmap(16, 16);stride = (frame%3)-1
            if kind < 2:
                color = 10 if kind == 0 else 13
                rect(p, 3, 3, 10, 7, 1);rect(p, 4, 4, 8, 5, color);rect(p, 6, 1, 4, 4, 9);rect(p, 7, 2, 2, 1, 15)
                rect(p, 1, 5, 3, 5, 8);rect(p, 12, 5, 3, 5, 8)
                rect(p, 4+stride, 10, 3, 5, 7);rect(p, 9-stride, 10, 3, 5, 7)
                rect(p, 3+stride, 14, 4, 2, 1);rect(p, 9-stride, 14, 4, 2, 1)
            elif kind < 4:
                rect(p, 6, 1, 5, 4, 13);rect(p, 5, 5, 7, 6, 10 if kind==2 else 12)
                rect(p, 4, 6+stride, 2, 5, 7);rect(p, 11, 6-stride, 2, 5, 7)
                rect(p, 6, 11, 2, 4+(frame%2), 9);rect(p, 9, 11, 2, 5-(frame%2), 9)
            else:
                rect(p, 1, 10, 14, 5, 8);rect(p, 4, 6, 7, 6, 1);rect(p, 8, 7, 6, 3, 12);rect(p, 3, 11, 7, 2, 6)
            frames.append(rows(p))
        sprites.append(frames)
    portraits = []
    for who in range(2):
        p = bitmap(64, 64, 1)
        rect(p, 3, 3, 58, 31, 8);rect(p, 6, 6, 52, 25, 9)
        for x in (8, 26, 44): rect(p, x, 9, 14, 19, 1);rect(p, x+2, 11, 10, 5, 10)
        rect(p, 9, 48, 48, 16, 3 if who else 6)
        rect(p, 24, 20, 18, 25, 13);rect(p, 22, 15, 22, 12, 1 if who else 6)
        rect(p, 25, 25, 16, 5, 13);rect(p, 27, 29, 3, 2, 1);rect(p, 36, 29, 3, 2, 1)
        rect(p, 28, 37, 10, 2, 12);rect(p, 28, 44, 10, 6, 13)
        rect(p, 19, 49, 27, 15, 10 if who else 9);rect(p, 31, 49, 4, 13, 14)
        rect(p, 1, 58, 62, 6, 7)
        portraits.append(rows(p))
    presentation = dict(format="btp-presentation-v1", schema_version=1,
        palette=["0b1320","1b2b3d","28574d","3e8265","759662","a9bb70","76533a","d6d4bc","46566b","6f94ad","6abec0","bbdccc","b95958","db9672","edcc75","f4f1de"],
        font=font, tiles=tiles, sprites=sprites, portraits=portraits,
        hit_locations=[3,2,7,0,5,1,6,4,4,4,4],
        people_formation=[[8,8],[6,8],[10,8],[8,10],[6,10],[10,10],[4,10],[12,10]],
        mech_formation=[[8,6],[4,6],[12,6],[8,2]],
        personal_weapon=dict(label="Pulse tool",damage=3,range=18),
        sounds=[[dict(hz=180+(i%6)*90,ms=35),dict(hz=120+(i%5)*55,ms=45)] for i in range(18)])
    write("presentation.json",presentation)
    content = json.loads((ROOT / "examples/adventure-demo/content.json").read_text())
    content.update(package_id="last-beacon", content_version="1.0.0")
    content["presentations"] = [dict(id="beacon:biped",source="package:walker-a"),dict(id="beacon:scout",source="package:walker-b")]
    for i, model in enumerate(content["mechs"]):
        model["presentation"] = content["presentations"][i]["id"]
        model["name"] = ["Rook patrol walker","Kite survey walker"][i]
    enemy = copy.deepcopy(content["mechs"][0]);enemy.update(id="beacon:warden", name="Warden derelict walker",label="Warden",price=300)
    enemy["armor"] = {key:2 for key in enemy["armor"]};enemy["structure"] = {key:2 for key in enemy["structure"]}
    enemy["loadout"] = [dict(weapon="workshop:cool-beam",location="left_arm",ammunition=0)]
    content["mechs"].append(enemy)
    write("content.json",content)
    write("project.json",dict(format="btp-project-v1",schema_version=1,package_id="last-beacon",content_version="1.0.0",title="Last Beacon",requires="none",startup="authored-adventure-v1",rules_profile="chi:updated-lrm-v1",save_policy="strict-content-v1",definitions="content.json",adventure="adventure.json",presentation="presentation.json",scripts=[dict(id="beacon:contract",file="contract.lua")],assets=[]))
    old = json.loads((ROOT / "examples/adventure-demo/adventure.json").read_text())
    def person(identity, name, ident, skills):
        return dict(id=ident,identity=f"actor:{identity}",name=name,attributes=[8,9,8],skills=skills,weapon=0,armor=0)
    people = [person(0,"Rowan","beacon:rowan",[2,2,2,3,3,1,1]),person(1,"Mira","beacon:mira",[2,2,2,3,3,2,2])]
    town = old["maps"][0]
    town.update(id="beacon:town",name="Grayhaven",origin=[64,64])
    town["rows"] = ["."*32 for _ in range(24)]
    town["rows"][10] = ".........ddddddddddddddd........"
    town["rows"][11] = ".........ddddddddddddddd........"
    town["rows"][12] = ".........ddddddddddddddd........"
    town["rows"][13] = "."*10+"d"*19+"."*3
    town["rows"][14] = "."*10+"d"*19+"."*3
    town["overlays"] = [dict(at=[9,5],rows=["######","######","######","######","###D##"]),dict(at=[18,5],rows=["######","######","######","######","##D###"]),dict(at=[3,2],rows=["TTT","T.T","TTT"])]
    town["entrances"] = [dict(id="beacon:depot-door",name="Walker Exchange",at=[24,22],event="beacon:shop"),dict(id="beacon:office-door",name="Relay Office",at=[40,22],event="beacon:office"),dict(id="beacon:road",name="Leave for the relay",at=[54,28],event="beacon:travel"),dict(id="beacon:mira-marker",name="Talk to Mira",person="beacon:mira",at=[34,26],event="beacon:office")]
    wild = dict(id="beacon:wild",name="The silent relay",origin=[96,64],rows=["."*32 for _ in range(24)],overlays=[dict(at=[22,5],rows=["TTTTT","T...T","TTT.T"]),dict(at=[21,12],rows=[".B.","...","..."]),dict(at=[4,3],rows=["wwww","wwww","wwww"])],entrances=[dict(id="beacon:back",name="Return to Grayhaven",at=[10,28],event="beacon:return"),dict(id="beacon:relay",name="Restore the relay",at=[40,28],event="beacon:relay-check")])
    events = [
        dict(id="beacon:end",op="end"),
        dict(id="beacon:welcome",op="say",portrait="training",text="Grayhaven's last relay has gone silent. Without it the valley will lose contact with the rescue fleet. Visit the Relay Office, recruit Mira, and take your walker east to the beacon.",next="beacon:end"),
        dict(id="beacon:shop",op="shop",shop="beacon:depot",next="beacon:end"),
        dict(id="beacon:office",op="lua",script="beacon:contract",routes=["beacon:offer","beacon:reward","beacon:reminder","beacon:completed"],failure="beacon:script-error"),
        dict(id="beacon:offer",op="choice",portrait="training",text="Mira folds a survey map. The relay guardian has malfunctioned. I can help. Will you take me along?",options=[dict(label="Recruit Mira",next="beacon:recruit"),dict(label="Later",next="beacon:end")],cancel="beacon:end"),
        dict(id="beacon:recruit",op="recruit",person="beacon:mira",next="beacon:hired",failure="beacon:full"),
        dict(id="beacon:hired",op="flag",flag="beacon:hired",value=1,next="beacon:brief"),
        dict(id="beacon:brief",op="say",portrait="training",text="Mira joins the expedition. Walk east out of town, then follow the old survey track to the relay. Defeat its broken guardian and return here. You can save at any time with F5.",next="beacon:end"),
        dict(id="beacon:full",op="say",text="There is no free place in the expedition.",next="beacon:end"),
        dict(id="beacon:reminder",op="say",portrait="training",text="The beacon is east of Grayhaven. Mira waits for the guardian to be cleared. Come back when the relay is transmitting.",next="beacon:end"),
        dict(id="beacon:travel",op="transfer",map="beacon:wild",at=[12,28],next="beacon:wild-intro",failure="beacon:blocked"),
        dict(id="beacon:wild-intro",op="say",text="An old mast rises over the trees. A derelict Warden blocks its access panel. Approach the relay to engage it. Computer control is available for this demonstration.",next="beacon:end"),
        dict(id="beacon:return",op="transfer",map="beacon:town",at=[50,28],next="beacon:end",failure="beacon:blocked"),
        dict(id="beacon:relay-check",op="if",flag="beacon:cleared",value=1,then="beacon:relay-live",**{"else":"beacon:fight-choice"}),
        dict(id="beacon:fight-choice",op="choice",text="The broken Warden turns toward your expedition. Clear the relay approach?",options=[dict(label="Engage guardian",next="beacon:battle"),dict(label="Step away",next="beacon:end")],cancel="beacon:end"),
        dict(id="beacon:battle",op="battle",encounter="beacon:guardian",win="beacon:cleared",loss="beacon:defeat",flee="beacon:withdraw",failure="beacon:blocked"),
        dict(id="beacon:cleared",op="flag",flag="beacon:cleared",value=1,next="beacon:relay-live"),
        dict(id="beacon:relay-live",op="say",text="The beacon pulses across the valley. Grayhaven is back on the network. Return to the Relay Office to report your success.",next="beacon:end"),
        dict(id="beacon:withdraw",op="say",text="You withdraw. The relay remains silent; you may return and try again.",next="beacon:end"),
        dict(id="beacon:defeat",op="say",text="The guardian prevails. Restore an earlier save to try the expedition again.",next="beacon:end"),
        dict(id="beacon:reward",op="reward",credits=2500,next="beacon:paid",failure="beacon:blocked"),
        dict(id="beacon:paid",op="flag",flag="beacon:paid",value=1,next="beacon:ending"),
        dict(id="beacon:ending",op="finish",portrait="training",text="A voice crackles over the restored link. The rescue fleet has heard Grayhaven. Your expedition receives 2500 credits, and Mira smiles as the first transport crosses the evening sky. The valley has a future. Last Beacon - complete."),
        dict(id="beacon:completed",op="say",text="The rescue fleet is on its way. Your contract has already been paid.",next="beacon:end"),
        dict(id="beacon:blocked",op="say",text="The expedition cannot complete that action here. Clear space for the whole party and try again.",next="beacon:end"),
        dict(id="beacon:script-error",op="say",text="The contract script reported an error. Check the player log; no reward or party change was applied.",next="beacon:end")]
    tile_keys = [("grass",".",0,"clear",2),("road","d",1,"clear",6),("water","w",2,"water",9),("trees","T",3,"woods",3),("wall","#",4,"wall",8),("door","D",5,"wall",14),("beacon","B",6,"wall",10),("rocks","R",7,"rough",8)]
    adventure = dict(format="btp-adventure-v1",schema_version=1,tiles=[dict(id="beacon:"+name,key=key,graphic=graphic,sheet="package:tiles",terrain=terrain,mini_color=color) for name,key,graphic,terrain,color in tile_keys],maps=[town,wild],people=people,shops=[dict(id="beacon:depot",stock=["workshop:rook","workshop:kite"])],encounters=[dict(id="beacon:guardian",map="beacon:wild",party_at=[24,28],enemies=[dict(kind="mech",definition="beacon:warden",at=[34,26])])],flags=["beacon:hired","beacon:cleared","beacon:paid"],events=events,start=dict(map="beacon:town",at=[24,28],event="beacon:welcome",credits=2000,party=[dict(person="beacon:rowan",mech="workshop:rook")]))
    write("adventure.json",adventure)
    (OUT/"contract.lua").write_text('-- Pure queries select shared, saved commands. No Lua stack is saved.\nif game.flag("beacon:paid") then\n  return game.command("beacon:completed")\nelseif game.flag("beacon:cleared") and game.flag("beacon:hired") then\n  return game.command("beacon:reward")\nelseif game.flag("beacon:hired") then\n  return game.command("beacon:reminder")\nelse\n  return game.command("beacon:offer")\nend\n',encoding="ascii")
    print(OUT)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build Last Beacon's BattleTech scenario from the already sourced Updated pack.

Only JSON and our generated portraits enter the package. Original DOS resources
and extracted caches stay external. Regeneration overwrites this shipped example.
"""
import json
import copy
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples/battletech-demo"


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="ascii")


def add_vehicles(package):
    """Extend the exchange without regenerating an author's maps or entrances."""
    from editor_model import ProjectDocument
    from unit_editing import import_catalogue
    document = ProjectDocument(package, ROOT / 'build/btp-project')
    ids = import_catalogue(document, ROOT / 'content/catalogues/vehicles')
    adventure = copy.deepcopy(document.adventure)
    shop = next(s for s in adventure['shops'] if s['id'] == 'beacon:exchange')
    shop['stock'].extend(identity for identity in ids if identity not in shop['stock'])
    # Only the exchange-related text changes. Existing terrain, doorway moves,
    # encounters, flags and starting company stay exactly as the author left them.
    texts = {
        'beacon:directions': "Visit the contract office at the eastern garage door, north of the road. The west door exchanges 'Mechs and combat vehicles. Cole, a spare pilot, waits on the road between them. ComStar has an office northeast. Travel east when ready. Space opens inspection, crew, map and saves; F5 saves, F9 restores.",
        'beacon:broker': "The broker wipes grease from a sales slate. Nine 'Mech models and ten combat vehicles: tanks, hovercraft, scouts and missile carriers. Stock is grouped by weight. Cash on delivery.",
        'beacon:crew-info': "Four bays total, shared by 'Mechs and vehicles. Every active unit needs a pilot or driver: use Allocate People from the Space menu outside. Cole is looking for work near the road. Sell a unit here to free a bay. Keep some C-bills in reserve.",
        'beacon:hire-info': "Cole joins Beacon Company. Buy him a 'Mech or vehicle at the exchange and assign him through the Space menu. Until then, put him in a passenger seat or keep him out of trouble on foot.",
    }
    for node in adventure['events']:
        if node['id'] in texts: node['text'] = texts[node['id']]
        if node['id'] == 'beacon:broker': node['options'][0]['label'] = 'Buy or sell units'
    content = copy.deepcopy(document.content)
    manifest = copy.deepcopy(document.manifest)
    content['content_version'] = manifest['content_version'] = '1.1.0'
    document.replace_all(content, adventure, document.art, manifest)
    document.save()
    shutil.copyfile(ROOT / 'content/catalogues/vehicles/README.md',
                    Path(package) / 'VEHICLE-SOURCE-README.md')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Export through the same adapter as the editor; do not maintain another
    # conversion of armor, heat sinks, weapon mounts or ammunition capacities.
    with tempfile.TemporaryDirectory(prefix="bt-demo-", dir=ROOT / "work") as tmp:
        exported = Path(tmp) / "pack"
        subprocess.run([str(ROOT / "build/btp-project"), "export", str(exported),
                        "--roster", str(ROOT / "content/updated/roster.json"),
                        "--combat-data", str(ROOT / "work/combat-data.bin")], check=True)
        content = json.loads((exported / "content.json").read_text())
    models = {
        "phoenix-hawk-pxh-1": "Phoenix Hawk PXH-1",
        "trebuchet-tbt-5n": "Trebuchet TBT-5N",
        "griffin-grf-1n": "Griffin GRF-1N",
        "panther-pnt-9r": "Panther PNT-9R",
        "clint-clnt-2-3t": "Clint CLNT-2-3T",
        "whitworth-wth-1": "Whitworth WTH-1",
        "javelin-jvn-10n": "Javelin JVN-10N",
        "jenner-jr7-d": "Jenner JR7-D",
        "urbanmech-um-r60": "UrbanMech UM-R60",
    }
    content.update(package_id="battletech-beacon", content_version="1.0.0")
    content["mechs"] = [m for m in content["mechs"] if m["id"].split(":")[1] in models]
    for m in content["mechs"]:
        m["name"] = models[m["id"].split(":")[1]]
    write("content.json", content)
    # These portraits were generated for this repository, not extracted from CHI.
    (OUT / "art").mkdir(exist_ok=True)
    assets = []
    for slot in ("broker", "training", "comstar"):
        shutil.copyfile(ROOT / f"content/updated/art/{slot}.anm", OUT / f"art/{slot}.anm")
        assets.append(dict(id=f"beacon:portrait-{slot}", slot=slot, file=f"art/{slot}.anm"))
    write("project.json", dict(format="btp-project-v1", schema_version=1,
        package_id="battletech-beacon", content_version="1.0.0",
        title="BattleTech - Last Beacon", requires="chi-original-dos-1.03",
        startup="authored-adventure-v1", rules_profile="chi:updated-lrm-v1",
        save_policy="strict-content-v1", definitions="content.json", adventure="adventure.json",
        scripts=[dict(id="beacon:contract", file="contract.lua")], assets=assets))
    sources = json.loads((ROOT / "content/updated/sources.json").read_text())
    sources["mechs"] = [m for m in sources["mechs"] if m["id"].split(":")[1] in models]
    # The initial three-model pack predates the pinned/hash source manifest.
    # Retain its recorded Panther URL without inventing an archival hash.
    sources["mechs"].append(dict(id="chi-expanded:panther-pnt-9r",
        source="https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Panther%20PNT-9R.mtf",
        note="Inherited from Updated 0.1.0; its README records this unpinned source, without a source hash."))
    write("sources.json", sources)
    for source, target in (("README.md","SOURCE-README.md"),("art/README.md","ART-SOURCE-README.md")):
        shutil.copyfile(ROOT / "content/updated" / source, OUT / target)

    tiles = []
    def tile(key, graphic, name, terrain="clear", color=2):
        tiles.append(dict(id=f"beacon:{name}", key=key, graphic=graphic,
                          sheet="chi:land", terrain=terrain, mini_color=color))
    tile(".", 64, "grass");tile(",", 66, "grass-detail")
    tile("=", 70, "road", color=7)
    tile("T", 47, "woods", "woods", 10)
    tile("R", 60, "rocks", "rough", 8)
    tile("w", 15, "water", "water", 1)
    for key, graphic in zip("abcdefghi", [115,116,119,120,121,122,123,125,127]):
        tile(key, graphic, "building-" + key, "wall", 8)
    # Original road/shore/wood border pieces are explicit visual definitions;
    # scene collision remains authored independently of their numeric indices.
    for key, graphic in zip("jklmnopq", [0,1,2,3,4,5,6,7]):
        tile(key, graphic, "shore-" + key, "water", 1)
    for key, graphic in zip("stuvxy", [32,33,34,40,41,46]):
        tile(key, graphic, "wood-edge-" + key, "woods", 10)

    def map_scene(ident, name, origin):
        rows = [["," if (x*7+y*11)%19==0 else "." for x in range(36)] for y in range(28)]
        for y in (15,16): rows[y] = list("="*36)
        return dict(id=f"beacon:{ident}", name=name, origin=origin,
                    rows=["".join(r) for r in rows], overlays=[], entrances=[])
    town = map_scene("town", "Grayhaven - mercenary depot", [64,64])
    town["overlays"] = [dict(at=[9,8],rows=["abbbc","deeef","ghhhi"]),
                        dict(at=[18,8],rows=["abbbc","deeef","ghhhi"]),
                        dict(at=[28,4],rows=["abbbc","deeef","ghhhi"]),
                        dict(at=[3,3],rows=["sttu","vTTy","vTTy","sttu"]),
                        dict(at=[20,21],rows=["jkkl","mwwn","oppq"])]
    def door(ident, name, at, event, person=None):
        d=dict(id=f"beacon:{ident}",name=name,at=at,event=f"beacon:{event}")
        if person:d["person"]=f"beacon:{person}"
        return d
    town["entrances"] = [door("exchange","Mech exchange",[24,26],"broker"),
        door("office","Contract office",[40,26],"office"),
        door("comstar","ComStar liaison",[60,18],"news"),
        door("pilot","Talk to Cole",[34,32],"hire-check","cole"),
        door("east-road","East: Quarry Road",[64,32],"road-gate")]
    road = map_scene("road", "Quarry Road - pirate checkpoint", [100,64])
    road["overlays"] = [dict(at=[5,4],rows=["stttu","vTTTy","vTTTy","stttu"]),
                        dict(at=[21,7],rows=[".RR.","RRRR",".RR."]),
                        dict(at=[24,20],rows=["sttu","vTTy","sttu"])]
    road["entrances"] = [door("road-back","West: Grayhaven",[8,32],"return-town"),
        door("checkpoint","Pirate checkpoint",[34,32],"road-check"),
        door("relay-road","East: relay station",[64,32],"relay-gate")]
    relay = map_scene("relay", "High Ridge - relay station", [136,64])
    relay["overlays"] = [dict(at=[27,7],rows=["abbbbc","deeeef","ghhhhi"]),
        dict(at=[9,4],rows=["stttu","vTTTy","stttu"]),
        dict(at=[22,20],rows=[".RRR.","RRRRR",".RRR."]),
        dict(at=[4,21],rows=["jkkkl","mwwwn","opppq"])]
    relay["entrances"] = [door("relay-back","West: Quarry Road",[8,32],"return-road"),
        door("relay-fight","Relay defenders",[40,32],"relay-check")]

    events=[]
    def event(ident,op,**values):
        # Stable IDs make this scenario readable and editable in the GUI.
        for key in ("next","failure","then","else","win","loss","flee","cancel"):
            if key in values:values[key]="beacon:"+values[key]
        for item in values.get("options",[]):item["next"]="beacon:"+item["next"]
        events.append(dict(id="beacon:"+ident,op=op,**values))
    def say(ident,text,next="end",portrait="training"):
        event(ident,"say",text=text,next=next,portrait=portrait)
    def choice(ident,text,options,cancel="end",portrait="training"):
        event(ident,"choice",text=text,options=[dict(label=l,next=n) for l,n in options],cancel=cancel,portrait=portrait)
    def flag(ident,name,next):event(ident,"flag",flag="beacon:"+name,value=1,next=next)
    def check(ident,name,yes,no):event(ident,"if",flag="beacon:"+name,value=1,then=yes,**{"else":no})
    def transfer(ident,map,at,next="end"):
        event(ident,"transfer",map="beacon:"+map,at=at,next=next,failure="blocked")
    event("end","end")
    say("welcome","Lyran Commonwealth border, 3025. You command Beacon Company: Rowan in a Phoenix Hawk PXH-1, with Mira in a Trebuchet TBT-5N. Pirates have cut Grayhaven's road to its relay. Your employer offers 8,000 C-bills to reopen the road. A second job waits beyond it.","directions")
    say("directions","Visit the contract office at the eastern garage door, north of the road. The west door is a 'Mech exchange. Cole, a spare pilot, waits on the road between them. ComStar has an office northeast. Travel east when ready. Space opens inspection, crew, map and saves; F5 saves, F9 restores.","offer")
    event("office","lua",script="beacon:contract",routes=["beacon:offer","beacon:road-report","beacon:reminder","beacon:relay-report","beacon:second-offer"],failure="script-error")
    choice("offer","Militia captain: Clear the Javelin blocking Quarry Road. Your two 'Mechs should be enough. Payment: 8,000 C-bills.",[("Accept the contract","accept"),("Tactical briefing","tactics"),("Not yet","end")])
    flag("accept","accepted","brief")
    say("brief","Contract accepted. Follow the road east to the checkpoint. Phoenix Hawk: fast jump-capable skirmisher with a large laser. Trebuchet: twin LRM-15 support; keep it behind the Hawk. Enhanced rules penalize LRMs inside minimum range. Return here after the fight.")
    say("tactics","Walk, run and jump are available in manual combat. Use trees for cover. The Hawk's jump jets can cross obstacles, but jumping and lasers add heat. Keep the Trebuchet back; its medium lasers are the fallback at close range. Computer combat is available. You can pause it with Space.","offer")
    say("reminder","The contract is open. Head east along Quarry Road, clear the pirate Javelin and report back here. You may withdraw and try again; damage and ammunition use persist.")
    choice("broker","The broker wipes grease from a sales slate. Nine Succession Wars models, inspected this morning. Cash on delivery.",[("Buy or sell a 'Mech","shop"),("Ask about crew","crew-info"),("Leave","end")],portrait="broker")
    event("shop","shop",shop="beacon:exchange",next="broker")
    say("crew-info","You can own four 'Mechs. A purchase needs a pilot: use Allocate People from the Space menu outside. Cole is looking for work near the road. Keep some C-bills in reserve; these are used machines, not a limitless militia arsenal.","broker","broker")
    check("hire-check","hired","already-hired","hire-offer")
    choice("hire-offer","Cole taps his neurohelmet. I'm a pilot, not a passenger. Got a spare cockpit? I'll sign on for this contract.",[("Recruit Cole","hire"),("Later","end")])
    event("hire","recruit",person="beacon:cole",next="hired",failure="full")
    flag("hired","hired","hire-info")
    say("hire-info","Cole joins Beacon Company. Buy him a 'Mech at the exchange and assign him through the Space menu. Until then, put him in a passenger seat or keep him out of trouble on foot.")
    say("already-hired","Cole is already part of Beacon Company.")
    say("full","There is no free place in your company.")
    say("news","The ComStar liaison lowers her voice. This is a local relay, not an HPG. The pirates want the traffic records and the militia's landing schedule. Reopen the road first. If you recover the station, I can relay your report to our employer.",portrait="comstar")
    check("road-gate","accepted","to-road","need-contract")
    say("need-contract","Visit the contract office before deploying. Your employer must authorize this job.")
    transfer("to-road","road",[12,32],"road-intro")
    say("road-intro","A pirate Javelin JVN-10N holds the checkpoint ahead, east along the road. Its paired SRM-6 launchers are dangerous close up. Keep your missile support at range and let the Phoenix Hawk draw it out. West leads home.")
    transfer("return-town","town",[60,32])
    check("road-check","road-clear","road-secure","road-choice")
    choice("road-choice","Sensors identify a Javelin JVN-10N: 30 tons, two SRM-6 launchers. The pirate orders you to turn back.",[("Engage the Javelin","road-battle"),("Withdraw for now","end")])
    event("road-battle","battle",encounter="beacon:roadblock",win="road-cleared",loss="defeat",flee="withdraw",failure="blocked")
    flag("road-cleared","road-clear","road-secure")
    say("road-secure","Quarry Road is clear. Return west to the contract office for your 8,000 C-bills. The militia also requests help at the relay; you may take that job or settle the first contract and leave.")
    event("road-report","reward",credits=8000,next="road-paid",failure="blocked")
    flag("road-paid","paid-road","second-offer")
    choice("second-offer","8,000 C-bills paid. Two pirates hold the relay: a Jenner and an UrbanMech. Another 15,000 if you take it. Accept?",[("Take the relay job","relay-accept"),("End our contract here","short-ending"),("Prepare first","end")])
    flag("relay-accept","relay-contract","relay-brief")
    say("relay-brief","The relay contract is signed. Continue east past the cleared checkpoint. Jenner JR7-D: four medium lasers and SRM-4. UrbanMech UM-R60: slow, but its AC/10 hits hard. Use your mobility and missile range. Return to Grayhaven for payment when the station is secure.")
    event("short-ending","finish",portrait="training",text="Beacon Company leaves Grayhaven with its first contract fulfilled. The road is open, the convoy is moving, and 8,000 C-bills have reached your account. The relay will be somebody else's war. Contract complete.")
    check("relay-gate","paid-road","relay-authorized","report-first")
    check("relay-authorized","relay-contract","to-relay","report-first")
    say("report-first","Report to the Grayhaven contract office before continuing. The road contract must be settled and the relay job accepted.")
    transfer("to-relay","relay",[12,32],"relay-intro")
    say("relay-intro","High Ridge relay comes into view. Two pirate 'Mechs guard the eastern approach. Move east to challenge them. The road west remains open if you need to withdraw.")
    transfer("return-road","road",[60,32])
    check("relay-check","relay-clear","relay-secure","relay-choice")
    choice("relay-choice","Jenner JR7-D and UrbanMech UM-R60 detected. One fast striker, one AC/10 gun platform. Your approach is exposed.",[("Attack the defenders","relay-battle"),("Pull back","end")])
    event("relay-battle","battle",encounter="beacon:relay-guard",win="relay-cleared",loss="defeat",flee="withdraw",failure="blocked")
    flag("relay-cleared","relay-clear","relay-secure")
    say("relay-secure","The pirate 'Mechs are down. Militia technicians secure the relay and recover the traffic records. Return west through Quarry Road to the contract office for your final payment.")
    event("relay-report","reward",credits=15000,next="relay-paid",failure="blocked")
    flag("relay-paid","paid-relay","ending")
    event("ending","finish",portrait="comstar",text="The restored relay carries the convoy's landing clearance. Grayhaven's militia can breathe again. ComStar confirms the transfer: 15,000 C-bills, on top of the road contract. Beacon Company has earned a name, a battered pair of 'Mechs, and a reason to take the next job. Last Beacon - contract complete.")
    say("withdraw","You break contact. The job remains open. Damage and ammunition expenditure carry over; regroup before attacking again.")
    say("defeat","Beacon Company has been defeated. Restore an earlier save to attempt the contract again.")
    say("blocked","Your company cannot complete that action here. Check crew assignments and leave room for the full formation.")
    say("script-error","The contract could not be resolved. Check the player log; no payment has been applied.")
    def person(ident,identity,name,skills):
        return dict(id="beacon:"+ident,identity=f"actor:{identity}",name=name,attributes=[9,9,9],skills=skills,weapon=7,armor=2)
    def enemy(model,at):return dict(kind="mech",definition="chi-expanded:"+model,at=at)
    adventure=dict(format="btp-adventure-v1",schema_version=1,tiles=tiles,maps=[town,road,relay],
        people=[person("rowan",0,"Rowan",[3,3,3,4,4,2,2]),person("mira",1,"Mira",[3,3,3,4,4,2,2]),person("cole",3,"Cole",[2,2,2,3,3,2,2])],
        shops=[dict(id="beacon:exchange",stock=[m["id"] for m in content["mechs"]])],
        encounters=[dict(id="beacon:roadblock",map="beacon:road",party_at=[18,32],enemies=[enemy("javelin-jvn-10n",[42,28])]),
                    dict(id="beacon:relay-guard",map="beacon:relay",party_at=[18,32],enemies=[enemy("jenner-jr7-d",[42,28]),enemy("urbanmech-um-r60",[52,34])])],
        flags=["beacon:"+s for s in ["accepted","hired","road-clear","paid-road","relay-contract","relay-clear","paid-relay"]],events=events,
        start=dict(map="beacon:town",at=[24,32],event="beacon:welcome",credits=18000,
                   party=[dict(person="beacon:rowan",mech="chi-expanded:phoenix-hawk-pxh-1"),dict(person="beacon:mira",mech="chi-expanded:trebuchet-tbt-5n")]))
    write("adventure.json",adventure)
    (OUT / "contract.lua").write_text('''-- Query flags; payments and continuations remain ordinary saved commands.
if game.flag("beacon:relay-clear") then
  return game.command("beacon:relay-report")
elseif game.flag("beacon:paid-road") then
  return game.command("beacon:second-offer")
elseif game.flag("beacon:road-clear") then
  return game.command("beacon:road-report")
elseif game.flag("beacon:accepted") then
  return game.command("beacon:reminder")
else
  return game.command("beacon:offer")
end
''',encoding="ascii")
    add_vehicles(OUT)
    subprocess.run([str(ROOT / "build/btp-project"),"validate",str(OUT)],check=True)


if __name__ == "__main__":
    main()

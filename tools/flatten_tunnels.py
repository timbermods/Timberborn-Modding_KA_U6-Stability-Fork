"""Regenerate the multi-length Path Extention tunnels (TE_Tunnel_1..9) as flat 1.1 blueprints.

The archived sources in 'Path Extention/Unity/Old tunnels' are built from nested Entry/Mid/Exit
modules (PrefabModuls/) and use the pre-1.1 DrivewayModelSpec. This inlines the modules (applying
each nested 'Modification'), migrates the driveway spec and writes plain blueprints to
Data/Knatte/Buildings/Paths/Tunnels, the same layout as TE_Tunnel_1L.

Run from the repo root:  python tools/flatten_tunnels.py
"""
import copy, glob, json, os, re

MOD = "Assets/Mods/Path Extention"
OLD = f"{MOD}/Unity/Old tunnels"
OUT = f"{MOD}/Data/Knatte/Buildings/Paths/Tunnels"
FACTIONS = {"Folktails": "Folktails", "IronTeeth": "IT", "Emberpelts": "Emberpelts"}


def load(path):
    s = open(path, encoding="utf-8-sig").read()
    return json.loads(re.sub(r",(\s*[\]}])", r"\1", s))  # sources contain trailing commas


def deep_merge(base, mod):
    for k, v in mod.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


CONSTRUCTION_SITE = "ConstructionBases/ConstructionBase1x1/ConstructionBase1x1.blueprint"


def flatten(children):
    out = {}
    for key, node in children.items():
        if "BlueprintPath" in node:
            name = key.replace("#nested", "")
            base_name = node["BlueprintPath"].split("/")[-1].replace(".blueprint", "")
            if base_name == "ConstructionSite1x1":
                out[key] = {"BlueprintPath": CONSTRUCTION_SITE}
                continue
            module = load(f"{MOD}/PrefabModuls/{base_name}.blueprint.json")
            merged = deep_merge(module, node.get("Modification", {}))
            out[name] = merged
        else:
            node = dict(node)
            if "Children" in node:
                node["Children"] = flatten(node["Children"])
            out[key] = node
    return out


def convert(src, faction, n):
    d = load(src)
    if "DrivewayModelSpec" in d:
        d = {("DrivewayModelsSpec" if k == "DrivewayModelSpec" else k):
             ({"Driveways": [v]} if k == "DrivewayModelSpec" else v) for k, v in d.items()}
    d["Children"] = flatten(d["Children"])
    t = d["TemplateSpec"]
    compat = [x for x in t["BackwardCompatibleTemplateNames"] if not x.startswith(f"TE_Tunnel_{n}.{faction}")]
    for legacy in (f"TE_Tunnel_{n}", f"TE_Tunnel_{n}.IT"):
        if faction == "IronTeeth" and legacy not in compat:
            compat.append(legacy)
        elif legacy == f"TE_Tunnel_{n}" and legacy not in compat:
            compat.append(legacy)
    t["TemplateName"] = f"TE_Tunnel_{n}.{faction}"
    t["BackwardCompatibleTemplateNames"] = sorted(set(c for c in compat if c != t["TemplateName"]))
    # Tool group SubGroup_PE_Tunnels is not registered in Data/, so use the plain Paths group.
    d["PlaceableBlockObjectSpec"]["ToolGroupId"] = "Paths"
    return d


os.makedirs(OUT, exist_ok=True)
made = []
for n in range(1, 10):
    for faction, suffix in FACTIONS.items():
        src = f"{OLD}/TE_Tunnel_{n}.{suffix}.blueprint.json"
        if not os.path.exists(src):
            src = f"{OLD}/TE_Tunnel_{n}.{faction}.blueprint.json"
        d = convert(src, faction, n)
        path = f"{OUT}/TE_Tunnel_{n}.{faction}.blueprint.json"
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, indent=2)
            f.write("\n")
        made.append((n, faction))
print("wrote", len(made), "blueprints")

# register in the per-faction template collections (right after the 1L tunnel)
for faction in FACTIONS:
    p = f"{MOD}/Data/TemplateCollection/TemplateCollection.Buildings.{faction}.blueprint.json"
    s = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in s else "\n"
    anchor = re.search(r'^([ \t]*)"Knatte/Buildings/Paths/Tunnels/TE_Tunnel_1L\.%s\.blueprint",?\r?\n' % faction, s, re.M)
    assert anchor, p
    lines = "".join(f'{anchor.group(1)}"Knatte/Buildings/Paths/Tunnels/TE_Tunnel_{n}.{faction}.blueprint",{nl}' for n in range(1, 10)
                    if f'TE_Tunnel_{n}.{faction}.blueprint' not in s)
    s = s[:anchor.end()] + lines + s[anchor.end():]
    open(p, "w", encoding="utf-8", newline="").write(s)
    print("registered in", os.path.basename(p))

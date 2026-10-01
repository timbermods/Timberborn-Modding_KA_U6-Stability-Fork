"""Package the Timberborn mods in Assets/Mods into installable zips without Unity.

A mod is a folder of plain files: manifest.json, thumbnail, blueprints, models (*.timbermesh),
sprites (*.png + *.png.meta.json), localizations (*.csv) and optionally a compiled DLL. Data/ is copied
to the mod root. A *.png.meta.json of {"isSprite": true} is written for every PNG Unity imports as a Sprite.

Custom Unity prefabs (pipe segments, character attachments) and materials can only be built by Unity as
asset bundles. For mods that use prefabs, FALLBACKS swaps in vanilla prefabs at package time so the mod
still loads (visuals differ); the repo sources are not changed. The packager fails if a reference to an
unshippable custom prefab is left, or if a Knatte/ model, icon or blueprint reference does not resolve.

Run from the repo root:  python tools/package_mods.py [dist-dir]
(EfficientWorkplaces needs its DLL first: dotnet build tools/EfficientWorkplaces/EfficientWorkplaces.csproj -c Release)
"""
import json, os, re, sys, zipfile

FT_PUMP = "Buildings/Water/WaterPump/WaterPumpPipeSegment.Folktails"
IT_PUMP = "Buildings/Water/DeepWaterPump/DeepWaterPumpPipeSegment.IronTeeth"
FT_BAD = "Buildings/Water/BadwaterPump/BadwaterPumpPipeSegment.Folktails"
IT_BAD = "Buildings/Water/DeepBadwaterPump/DeepBadwaterPumpPipeSegment.IronTeeth"

MODS = {
    "Path Extention": dict(folder="PathExtention"),
    "Water Extention_Irrigation": dict(folder="WaterExtentionIrrigation"),
    "Water Extention": dict(
        folder="WaterExtention",
        # the custom 'DeepSee' pipe prefab (Unity-only) -> vanilla pump pipe of the same faction
        prefab_swaps=[(r"Knatte[^A-Za-z]{1,4}Buildings[^A-Za-z]{1,4}Water[^A-Za-z]{1,4}DeepSeePipeSegment[.]Common", {"IronTeeth": IT_PUMP, "*": FT_PUMP})],
        note="Pipes use the vanilla pump pipe look instead of the custom DeepSee pipe (a Unity prefab).",
    ),
    "EfficientWorkplaces": dict(
        folder="EfficientWorkplaces",
        dll="tools/EfficientWorkplaces/bin/Release/netstandard2.1/Knatte.EfficientWorkplaces.dll",
        skip_dirs=["Characters"],  # only append the custom scissor attachments
        prefab_swaps=[
            (r"Knatte/Buildings/Water/EfficientBadWaterPumpPipeSegment\.\w+", {"IronTeeth": IT_BAD, "*": FT_BAD}),
            (r"Knatte/Buildings/Water/EfficientWaterPumpPipeSegment\.\w+", {"IronTeeth": IT_PUMP, "*": FT_PUMP}),
        ],
        strip_outfit_attachments=r"^KAScis+or",  # custom scissor attachments in worker outfits
        note="Efficient pumps use the vanilla pump pipe look and workers do not carry the custom scissors (Unity prefabs).",
    ),
}
KEEP = (".json", ".csv", ".png", ".timbermesh", ".txt")
dist = sys.argv[1] if len(sys.argv) > 1 else "dist"
os.makedirs(dist, exist_ok=True)


def tolerant_json(text):
    return json.loads(re.sub(r",(\s*[\]}])", r"\1", text.lstrip("﻿")))


def unity_is_sprite(png):
    meta = png + ".meta"
    return os.path.exists(meta) and re.search(r"^\s*textureType:\s*8\s*$", open(meta, encoding="utf-8").read(), re.M) is not None


def faction_of(name):
    for f in ("IronTeeth", "Folktails", "Emberpelts"):
        if f".{f}." in name or name.endswith(f".{f}"):
            return f
    return "*"


def transform(rel, text, cfg):
    for pattern, by_faction in cfg.get("prefab_swaps", []):
        f = faction_of(os.path.basename(rel))
        text = re.sub(pattern, lambda m: by_faction.get(f, by_faction["*"]).replace("\\", "/"), text)
    pat = cfg.get("strip_outfit_attachments")
    if pat and os.path.basename(rel).startswith("WorkerOutfit."):
        d = tolerant_json(text)
        spec = d["WorkerOutfitSpec"]
        spec["Attachments"] = [a for a in spec["Attachments"] if not re.search(pat, a)]
        text = json.dumps(d, indent=2) + "\n"
    return text


for src, cfg in MODS.items():
    root, folder = f"Assets/Mods/{src}", cfg["folder"]
    manifest = tolerant_json(open(f"{root}/manifest.json", encoding="utf-8").read())
    version = manifest["Version"]
    out = f"{dist}/{folder}-{version}.zip"
    entries = {}  # arcname -> bytes
    for dp, dn, fns in os.walk(f"{root}/Data"):
        for fn in fns:
            if not fn.endswith(KEEP):
                continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, f"{root}/Data").replace("\\", "/")
            if rel.split("/")[0] in cfg.get("skip_dirs", []):
                continue
            data = open(full, "rb").read()
            if fn.endswith(".blueprint.json"):
                data = transform(rel, data.decode("utf-8-sig"), cfg).encode("utf-8")
            entries[rel] = data
            if rel.endswith(".png") and unity_is_sprite(full):
                entries[rel + ".meta.json"] = b'{\n  "isSprite": true\n}\n'
    entries["manifest.json"] = open(f"{root}/manifest.json", "rb").read()
    entries["Changelog.MD"] = open(f"{root}/Changelog.MD", "rb").read()
    for thumb in (f"{root}/Root/Thumbnail.jpg", f"{root}/Data/Thumbnail.jpg"):
        if os.path.exists(thumb):
            entries["thumbnail.jpg"] = open(thumb, "rb").read()
            break
    if "dll" in cfg:
        if not os.path.exists(cfg["dll"]):
            sys.exit(f"missing {cfg['dll']}: build it first (see the docstring)")
        entries[os.path.basename(cfg["dll"])] = open(cfg["dll"], "rb").read()
    entries["LICENSE"] = open("LICENSE", "rb").read()
    notice = ("Stability fork of KnatteAnka/Timberborn-Modding_KA_U6 (GPL-3.0), "
              "https://github.com/timbermods/Timberborn-Modding_KA_U6-Stability-Fork\n"
              "Built to fix bugs on new Timberborn versions. All credit for the mod goes to the original author, KnatteAnka.\n")
    if cfg.get("note"):
        notice += "\nDifference from the original: " + cfg["note"] + "\nThe fork builds without Unity, so custom Unity prefabs cannot be included.\n"
    entries["FORK-NOTICE.txt"] = notice.encode()

    # verification: nothing refers to a custom prefab we cannot ship; every Knatte/ reference resolves
    names = {n.lower() for n in entries}  # Windows paths are case-insensitive
    bad = []
    for n, b in entries.items():
        if not n.endswith(".blueprint.json"):
            continue
        s = b.decode("utf-8")
        for m in re.findall(r'"(?:Prefab|PipeSegmentPrefabPath)"\s*:\s*"([^"]+)"', s):
            if m.replace("\\\\", "/").startswith("Knatte/"):
                bad.append((n, "custom prefab", m))
        if "KAScissor" in s or "KASciccor" in s:
            bad.append((n, "scissor reference"))
        for m in re.findall(r'"(?:Model|Icon|BlueprintPath)"\s*:\s*"(Knatte/[^"]+)"', s) + re.findall(r'"(Knatte/[^"]+\.blueprint)"', s):
            if not any(c.lower() in names for c in (f"{m}.timbermesh", f"{m}.png", f"{m}.json", m)):
                bad.append((n, "unresolved", m))
    if bad:
        sys.exit(f"{folder}: {len(bad)} problems, e.g. {bad[:5]}")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, data in sorted(entries.items()):
            z.writestr(f"{folder}/{arc}", data)
    print(f"{out}: {len(entries)} files, v{version}" + (" (vanilla-prefab fallbacks)" if cfg.get("note") else ""))

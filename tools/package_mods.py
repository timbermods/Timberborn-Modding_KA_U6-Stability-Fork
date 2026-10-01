"""Package the data-only mods into installable zips (no Unity needed).

A Timberborn mod is a folder of plain files: manifest.json, thumbnail, blueprints (*.blueprint.json),
models (*.timbermesh), sprites (*.png with a *.png.meta.json), localizations (*.csv). This copies
Assets/Mods/<mod>/Data to the mod root (as the game's example mods are laid out), adds the thumbnail,
manifest, changelog and licence, and writes <Name>.png.meta.json for every PNG that Unity imports as a Sprite.

Mods that ship Unity prefabs, materials or compiled scripts (Water Extention, EfficientWorkplaces,
KnattesMaterials) need a Unity asset-bundle build and are NOT handled here.

Run from the repo root:  python tools/package_mods.py [dist-dir]
"""
import json, os, re, sys, zipfile

MODS = {  # source folder -> install folder name
    "Path Extention": "PathExtention",
    "Water Extention_Irrigation": "WaterExtentionIrrigation",
}
KEEP = (".json", ".csv", ".png", ".timbermesh", ".txt")
dist = sys.argv[1] if len(sys.argv) > 1 else "dist"
os.makedirs(dist, exist_ok=True)


def unity_is_sprite(png):
    meta = png + ".meta"
    if not os.path.exists(meta):
        return False
    return re.search(r"^\s*textureType:\s*8\s*$", open(meta, encoding="utf-8").read(), re.M) is not None


for src, folder in MODS.items():
    root = f"Assets/Mods/{src}"
    manifest = json.loads(re.sub(r",(\s*[\]}])", r"\1", open(f"{root}/manifest.json", encoding="utf-8-sig").read()))
    version = manifest["Version"]
    out = f"{dist}/{folder}-{version}.zip"
    files = {}
    for dp, _, fns in os.walk(f"{root}/Data"):
        for fn in fns:
            if not fn.endswith(KEEP) or fn.endswith(".meta"):
                continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, f"{root}/Data").replace("\\", "/")
            files[rel] = full
    sprites = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        def add(arc, path):
            z.write(path, f"{folder}/{arc}")
        for rel, full in sorted(files.items()):
            add(rel, full)
            if rel.endswith(".png") and unity_is_sprite(full):
                z.writestr(f"{folder}/{rel}.meta.json", '{\n  "isSprite": true\n}\n')
                sprites += 1
        add("manifest.json", f"{root}/manifest.json")
        add("Changelog.MD", f"{root}/Changelog.MD")
        for thumb in (f"{root}/Root/Thumbnail.jpg", f"{root}/Data/Thumbnail.jpg"):
            if os.path.exists(thumb):
                add("thumbnail.jpg", thumb)
                files.pop("Thumbnail.jpg", None)
                break
        add("LICENSE", "LICENSE")
        z.writestr(f"{folder}/FORK-NOTICE.txt",
                   "Stability fork of KnatteAnka/Timberborn-Modding_KA_U6 (GPL-3.0), "
                   "https://github.com/timbermods/Timberborn-Modding_KA_U6-Stability-Fork\n"
                   "Built to fix bugs on new Timberborn versions. All credit for the mod goes to the original author, KnatteAnka.\n")
    print(f"{out}: {len(files)} files, {sprites} sprite metas, v{version}")

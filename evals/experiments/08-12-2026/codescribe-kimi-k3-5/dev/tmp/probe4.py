files = [
    "software/mcfm/src/Mods/ewcharge_mod.hpp",
    "software/mcfm/src/Mods/zcouple_cms_mod.hpp",
    "software/mcfm/src/Mods/nf_mod.hpp",
    "software/mcfm/src/Mods/zcouple_mod.hpp",
    "software/mcfm/src/Mods/scale_mod.hpp",
]
for f in files:
    print("=====", f)
    print(open(f, errors="replace").read())

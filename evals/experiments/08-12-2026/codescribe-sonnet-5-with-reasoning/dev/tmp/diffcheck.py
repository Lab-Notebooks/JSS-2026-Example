import hashlib

def h(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()

print(h('software/mcfm/src/Mods/pp_mod.f90'))
print(h('software/mcfm/src/Mods/deprecated/pp_mod.f90'))
print(h('software/mcfm/src/Mods/ppwp2j_mod.f90'))
print(h('software/mcfm/src/Mods/deprecated/ppwp2j_mod.f90'))

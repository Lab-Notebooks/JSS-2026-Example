import hashlib

def h(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()

print(h('software/mcfm/src/Mods/constants_mod.f90'))
print(h('software/mcfm/src/Mods/deprecated/constants_mod.f90'))

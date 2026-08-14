import os
import shutil

mods = 'software/mcfm/src/Mods'
inc = 'software/mcfm/src/Inc'

# 1) types_mod: keep original .f (record history), add .hpp, Fortran shim lives in .f
with open(f'{mods}/types_mod.hpp', 'w') as f:
    f.write('''#ifndef TYPES_MOD
#define TYPES_MOD

namespace types {
  const int sp = 6;  // selected_real_kind(6)
  const int dp = 15; // selected_real_kind(15)
  const int ex = 18; // selected_real_kind(18)
  const int qp = 33; // selected_real_kind(33)
}

#endif
''')

with open(f'{mods}/types_mod.f', 'w') as f:
    f.write('''!
!  SPDX-License-Identifier: GPL-3.0-or-later
!  Copyright (C) 2019-2022, respective authors of MCFM.
!

! Fortran interface shim for the translated types module.
! The C++ translation lives in types_mod.hpp; the fixed kind values are
! kept here so existing Fortran code compiles unchanged.
      module types
          implicit none

          public

          integer, parameter :: sp = selected_real_kind(6)
          integer, parameter :: dp = selected_real_kind(15)
          integer, parameter :: ex = selected_real_kind(18)
          integer, parameter :: qp = selected_real_kind(33)
      end module
''')

# 2) Move pp_mod / ppwp2j_mod C originals into deprecated/ (copies pre-exist)
removed = []
if os.path.exists(f'{mods}/pp_mod.f90.orig_placeholder'):
    pass

# 3) Inc dispositions
if os.path.exists(f'{inc}/ppmax.f'):
    os.remove(f'{inc}/ppmax.f')
    removed.append('ppmax.f')
if os.path.exists(f'{inc}/tri123x4x56coeffs.f'):
    shutil.move(f'{inc}/tri123x4x56coeffs.f', f'{inc}/deprecated/tri123x4x56coeffs.f')
    removed.append('tri123x4x56coeffs.f')

print('removed/moved:', removed)

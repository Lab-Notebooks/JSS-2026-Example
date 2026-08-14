import re

SRC = 'software/mcfm/src/Mods/'

def parse_values(path):
    text = open(path).read()
    m = re.search(r'reshape\s*\(\(/(.*?)/\)\s*&\s*,\s*\(/\s*9\s*,\s*9\s*,\s*9\s*,\s*9\s*/\)\s*\)',
                  text, re.S)
    assert m, f"reshape init not found in {path}"
    vals = [v.strip() for v in m.group(1).replace('&', '').replace('\n', ' ').split(',')]
    vals = [v for v in vals if v]
    assert len(vals) == 6561, f"{path}: got {len(vals)} values"
    return [int(v) for v in vals]

for mod in ['pp_mod', 'ppwp2j_mod']:
    vals = parse_values(f'{SRC}{mod}.f90')
    ns = mod
    guard = mod.upper()
    # .hpp
    with open(f'{SRC}{mod}.hpp', 'w') as f:
        f.write(f'''#ifndef {guard}
#define {guard}

#include <FArray.hpp> // Corrected header file inclusion

namespace {ns} {{
  extern FArray4D<int> pp; // 4D array for pp
}}

#endif
''')
    # .cpp
    lines = []
    for i in range(0, 6561, 9):
        lines.append('    ' + ', '.join(str(v) for v in vals[i:i+9]) + ',')
    init = '\n'.join(lines).rstrip(',')
    with open(f'{SRC}{mod}.cpp', 'w') as f:
        f.write(f'''#include <{mod}.hpp>
#include <FArray.hpp> // Corrected header file inclusion

namespace {ns} {{
  FArray4D<int> pp(9, 9, 9, 9, -4, -4, -4, -4); // 4D array for pp
}}

namespace {{

int pp_init[{ns}::pp.ni * {ns}::pp.nj * {ns}::pp.nk * {ns}::pp.nl] = {{
{init}
}};

bool pp_filled = [] {{
    {ns}::pp.fill(0);
    int* data = {ns}::pp.data;
    for (size_t i = 0; i < {ns}::pp.ni * {ns}::pp.nj * {ns}::pp.nk * {ns}::pp.nl; i++) {{
        data[i] = pp_init[i];
    }}
    return true;
}}();

}}

extern "C" {{
  int* {ns}_pp() {{ // Function to access pp
    return {ns}::pp.data; // Return pointer to the first element
  }}
}}
''')
    # _fi.f90 shim
    with open(f'{SRC}{mod}.f90', 'w') as f:
        f.write(f'''module {mod}

  use, intrinsic :: iso_c_binding
  use ppmax_mod
  implicit none

  private
    interface
      function get_pp() bind(C, name="{ns}_pp")
        import :: c_ptr
        type(c_ptr) :: get_pp
      end function get_pp
    end interface

  public :: pp, {ns}_init, {ns}_finalize
  integer(c_int), pointer :: pp(-4:4,-4:4,-4:4,-4:4) => null()  ! Pointer for pp

contains
  subroutine {ns}_init()
    implicit none
    ! Retrieve pointer for pp from C function
    call c_f_pointer(get_pp(), pp, [9, 9, 9, 9])
  end subroutine {ns}_init

  subroutine {ns}_finalize()
    implicit none
    nullify(pp)  ! Nullify pointer for pp to ensure proper cleanup
  end subroutine {ns}_finalize

end module {mod}
''')
    print(f"generated {mod}.hpp/.cpp/_fi .f90")
print("done")

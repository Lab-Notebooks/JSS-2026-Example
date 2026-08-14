def format_data(flat, per_line=27):
    lines = []
    for i in range(0, len(flat), per_line):
        chunk = flat[i:i+per_line]
        lines.append("    " + ", ".join(chunk) + ",")
    # remove trailing comma on very last entry
    lines[-1] = lines[-1].rstrip(",")
    return "\n".join(lines)


def build(name):
    with open(f"dev/tmp/{name}_flat.txt") as f:
        flat = f.read().strip().split(",")
    assert len(flat) == 6561, (name, len(flat))
    body = format_data(flat)

    hpp = f"""#ifndef {name.upper()}
#define {name.upper()}

#include <FArray.hpp>

namespace {name} {{
  extern FArray4D<int> pp;
}}

#endif
"""

    cpp = f"""#include <{name}.hpp>
#include <FArray.hpp>

namespace {name} {{
  namespace {{
    const int pp_flat[9 * 9 * 9 * 9] = {{
{body}
    }};
  }}

  FArray4D<int> pp(9, 9, 9, 9, -4, -4, -4, -4);

  namespace {{
    struct PpInit {{
      PpInit() {{
        for (size_t idx = 0; idx < 9 * 9 * 9 * 9; ++idx) {{
          pp.data[idx] = pp_flat[idx];
        }}
      }}
    }} pp_init;
  }}
}}

extern "C" {{
  int* {name}_pp() {{ // Function to access pp
    return {name}::pp.data;
  }}
}}
"""

    with open(f"software/mcfm/src/Mods/{name}.hpp", "w") as f:
        f.write(hpp)
    with open(f"software/mcfm/src/Mods/{name}.cpp", "w") as f:
        f.write(cpp)
    print("wrote", name)


build("pp_mod")
build("ppwp2j_mod")

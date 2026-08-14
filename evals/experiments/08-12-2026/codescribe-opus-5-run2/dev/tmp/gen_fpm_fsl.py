"""Generate fpm.cpp / fsl.cpp from the Fortran originals via f2cpp_expr.py."""
import subprocess
import sys
import os

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
w2 = os.path.join(root, "software", "mcfm", "src", "W2jet")

TEMPLATE = """//
//  SPDX-License-Identifier: GPL-3.0-or-later
//  Copyright (C) 2019-2022, respective authors of MCFM.
//
#include <W2jet.hpp>
#include <cmath>
#include <complex>
#include <FArray.hpp>
#include <constants_mod.hpp>
#include <mxpart_mod.hpp>
#include <sprods_com_mod.hpp>
#include <Need.hpp>
#include <W1jet.hpp>

using namespace constants_mod;
using namespace mxpart_mod;
using namespace sprods_com_mod;

std::complex<double> {name}(int j1, int j2, int j3, int j4, int j5, int j6,
                        FArray2D<std::complex<double>>& za, FArray2D<std::complex<double>>& zb) {{
  std::complex<double> {name}_value;
  std::complex<double> t0, {svars};

{body}

  return {name}_value;
}}

extern "C" {{
  std::complex<double> {name}_wrapper(int j1, int j2, int j3, int j4, int j5, int j6,
                                  std::complex<double>* fza, std::complex<double>* fzb) {{
    FArray2D<std::complex<double>> za(fza, mxpart, mxpart);
    FArray2D<std::complex<double>> zb(fzb, mxpart, mxpart);
    return {name}({name_args}, za, zb);
  }}
}}
"""

SHIM = """
function {name}(j1,j2,j3,j4,j5,j6,za,zb) result(res)
  use, intrinsic :: iso_c_binding
  use mxpart_mod
  use sprods_com_mod

  implicit none

  complex(c_double_complex) :: res
  complex(c_double_complex), dimension(mxpart,mxpart), intent(inout) :: za, zb
  integer(c_int), intent(in) :: j1, j2, j3, j4, j5, j6

  interface
    function {name}_wrapper(j1, j2, j3, j4, j5, j6, za, zb) bind(C, name="{name}_wrapper")
      import :: c_int, c_double_complex, mxpart
      integer(c_int), value :: j1, j2, j3, j4, j5, j6
      complex(c_double_complex) :: za(mxpart,mxpart), zb(mxpart,mxpart)
      complex(c_double_complex) :: {name}_wrapper
    end function {name}_wrapper
  end interface

  res = {name}_wrapper(j1, j2, j3, j4, j5, j6, za, zb)
end function {name}
"""


def gen(name, nvars):
    src = os.path.join(w2, name + ".f")
    body = subprocess.run(
        [sys.executable, os.path.join(root, "dev", "tmp", "f2cpp_expr.py"), src, name],
        capture_output=True, text=True, check=True).stdout.rstrip("\n")
    svars = ", ".join("s%d" % i for i in range(1, nvars + 1))
    cpp = TEMPLATE.format(name=name, svars=svars, body=body,
                          name_args="j1, j2, j3, j4, j5, j6")
    with open(os.path.join(w2, name + ".cpp"), "w") as fh:
        fh.write(cpp)
    with open(os.path.join(w2, name + "_fi.F90"), "w") as fh:
        fh.write(SHIM.format(name=name))
    print("wrote", name + ".cpp", "and", name + "_fi.F90",
          "-", len(body.splitlines()), "statements")


gen("fpm", 18)
gen("fsl", 15)

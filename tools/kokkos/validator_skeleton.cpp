// Standalone validator skeleton for the cpp-to-kokkos transformation.
//
// Links the original MCFM C++ (libmcfm) AND the ported Pepper kernel headers
// (compiled host-side via the Kokkos shim), then compares them in-process on
// fixed phase-space points — layered from the loop functions up to the full
// matrix element. Build/run with templates/run_validation.sh.
//
// Replace every  <<TODO ...>>  marker for the specific amplitude. Use the
// committed worked example as a reference:
//   PEPPER_HOME/src/mcfm_analytics  + tests/unit_tests/matrix_elements.cpp
//   (the qqb_z1jet_v case: validate against qqb_z1jet_v_main / virt5 / loopI*).

#include <cmath>
#include <complex>
#include <cstdio>
#include <cstring>

// ---- MCFM library headers (add the modules your amplitude reads) ----
#include <FArray.hpp>
#include <Need.hpp>
#include <Loop.hpp>
#include <constants_mod.hpp>
#include <mxpart_mod.hpp>
#include <nf_mod.hpp>
#include <nflav_mod.hpp>
#include <epinv_mod.hpp>
#include <epinv2_mod.hpp>
#include <scale_mod.hpp>
#include <scheme_mod.hpp>
#include <qcdcouple_mod.hpp>
#include <masses_mod.hpp>
#include <scalarselect_mod.hpp>
#include <blha_mod.hpp>
#include <kprocess_mod.hpp>
#include <zcouple_mod.hpp>
#include <zcouple_cms_mod.hpp>
#include <ewcharge_mod.hpp>
#include <sprods_com_mod.hpp>
#include <zprods_com_mod.hpp>
// #include <YourProcess.hpp>   // <<TODO: declares *_main / *_v_main / sub-amplitudes>>

// ---- Ported kernels (resolved through the shim include root, -I <build>) ----
// #include "mcfm_analytics/<name>_kernel.h"      // <<TODO>>

using cd = std::complex<double>;
extern "C" void qlinit();

static int failures = 0;
static void check(const char* name, cd ref, cd got, double tol) {
  const double rel = std::abs(ref - got) / (std::abs(ref) + 1e-300);
  const bool ok = rel <= tol;
  if (!ok) ++failures;
  printf("  [%s] %-30s ref=(% .10e,% .10e) got=(% .10e,% .10e) rel=%.2e\n",
         ok ? "OK " : "BAD", name, ref.real(), ref.imag(), got.real(),
         got.imag(), rel);
}
static void check(const char* name, double ref, double got, double tol) {
  check(name, cd(ref, 0), cd(got, 0), tol);
}

int main() {
  using namespace constants_mod;
  using namespace mxpart_mod;

  // ---- fixed physics inputs (must match the kernel params exactly) ----
  const double xw = 0.2312, alpha_em = 1.0 / 128.802223295, alpha_s = 0.118;
  const double zmass = 91.1876, zwidth = 2.4952, mtop = 173.21;
  const double mu = zmass, musq = mu * mu;
  (void)mtop;

  // ---- set the MCFM module globals the amplitude reads ----
  epinv_mod::epinv = 0.0;     // finite part only
  epinv2_mod::epinv2 = 0.0;
  scale_mod::scale = mu; scale_mod::musq = musq;
  std::strcpy(scheme_mod::scheme, "dred");
  qcdcouple_mod::as = alpha_s; qcdcouple_mod::gsq = 4.0 * pi * alpha_s;
  qcdcouple_mod::ason2pi = alpha_s / (2.0 * pi);
  qcdcouple_mod::ason4pi = alpha_s / (4.0 * pi);
  masses_mod::zmass = zmass; masses_mod::zwidth = zwidth; masses_mod::mt = mtop;
  nflav_mod::nflav = 5; scalarselect_mod::scalarselect = 1;  // QCDLoop
  blha_mod::useblha = 0;
  // kprocess_mod::kcase = kprocess_mod::kZ_1jet;   // <<TODO: set for your process>>
  qlinit();
  zcouple_mod::q1 = -1.0; zcouple_mod::q2 = 0.0;
  couplz(xw); couplz_cms(cd(xw, 0.0));
  zcouple_cms_mod::zesq = 4.0 * pi * alpha_em;
  zcouple_cms_mod::zl1 = zcouple_cms_mod::zle;
  zcouple_cms_mod::zr1 = zcouple_cms_mod::zre;

  // ---- derive the kernel's *_Params with the SAME couplz convention ----
  const double sin2w = 2.0 * std::sqrt(xw * (1.0 - xw));
  auto zl_of = [&](double Q, double tau) { return (tau - 2.0 * Q * xw) / sin2w; };
  auto zr_of = [&](double Q) { return (-2.0 * Q * xw) / sin2w; };
  (void)zl_of; (void)zr_of;
  // <<TODO: fill the kernel *_Params from these (see the worked example)>>

  // ---- fixed MCFM-convention momenta {px,py,pz,E}, incoming negated ----
  // Reuse a point from tests/unit_tests/phase_space_points.h (Pepper Vec4 is
  // {E,px,py,pz}; for incoming particles negate the whole 4-vector).
  // <<TODO: define p (FArray2D for MCFM) and p_kernel[N][4or5] arrays>>

  printf("==== loop functions (kernel vs MCFM/QCDLoop) ====\n");
  // check("lnrat", lnrat(8315.18,-196e6), <kernelns>::lnrat(8315.18,-196e6), 1e-13);
  // ... B0 vs loopI2, C0 vs loopI3, etc. (validate the closed forms FIRST)

  printf("\n==== sub-amplitudes (kernel vs MCFM) ====\n");
  // check("virt5(...)", mcfm_virt5(...), kernel_virt5(...), 1e-12);

  printf("\n==== full matrix element ====\n");
  // <<TODO: call MCFM *_v_main -> msqv(j,k); call kernel *_me2(p,params)>>
  // check("msqv(j,k)", msqv(1,-1), kernel_me2(p_kernel, params), 1e-10);

  printf("\n%s (failures: %d)\n", failures ? "FAILED" : "ALL PASSED", failures);
  return failures ? 1 : 0;
}

// Host stand-in for Pepper's src/math.h, used to compile the device kernels on
// the CPU for standalone validation/benchmarking (no Kokkos build required).
// C = std::complex<double> stands in for Kokkos::complex<double>; the Kokkos::*
// math wrappers forward to <cmath>. The kernel arithmetic is identical.
#pragma once
#include <complex>
#include <cmath>

#ifndef KOKKOS_INLINE_FUNCTION
#define KOKKOS_INLINE_FUNCTION inline
#endif

using C = std::complex<double>;

namespace Kokkos {
inline double sqrt(double x) { return std::sqrt(x); }
inline double log(double x) { return std::log(x); }
inline double exp(double x) { return std::exp(x); }
inline double fabs(double x) { return std::fabs(x); }
inline double abs(double x) { return std::fabs(x); }
inline double atan(double x) { return std::atan(x); }
inline double atan2(double y, double x) { return std::atan2(y, x); }
inline double sin(double x) { return std::sin(x); }
inline double cos(double x) { return std::cos(x); }
inline double pow(double x, double y) { return std::pow(x, y); }
template <class T>
std::complex<T> conj(const std::complex<T>& z) { return std::conj(z); }
template <class T>
std::complex<T> sqrt(const std::complex<T>& z) { return std::sqrt(z); }
}  // namespace Kokkos

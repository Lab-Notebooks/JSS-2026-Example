c Test file to isolate the Doxygen 1.14.0 Fortran-fixed parser crash
      subroutine smalltest1(n)
      implicit none
      integer n
      complex*16 z(2,2,2)
      real*8 x
      real*8 smalltest1
      x = dble(
     &  z(1,1,1)*z(2,2,2)
     & ,kind=8)
      smalltest1 = x
      return
      end

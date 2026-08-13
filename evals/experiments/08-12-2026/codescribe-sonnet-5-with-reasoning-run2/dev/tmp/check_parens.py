import sys

expr = """0.5_dp*zb(j1,j2)/(zb(j2,j3)*zab2(j4,j1,j2,j3))
*(6*za(j1,j2)*zab2(j3,j1,j2,j4)*zab2(j5,j1,j2,j6)
*(zb(j1,j3)*delta56-2*zba(j1,j2,j4)*zb(j4,j3))/Delta3**2
+1._dp/Delta3*(
zab(j2,j1,j4)*za(j3,j5)*zab2(j5,j1,j2,j3)/za(j5,j6)
-za(j1,j2)*za(j4,j5)/(za(j3,j4)*za(j5,j6))
*(zb(j1,j3)*za(j4,j5)*zab2(j3,j1,j2,j4)*delta12/zab2(j4,j1,j2,j3)
-za(j3,j5)*(2*zb(j1,j4)*delta12-zba(j1,j2,j3)*zb(j3,j4)))
-za(j2,j4)*za(j3,j5)*delta12/(za(j3,j4)*za(j5,j6))
*(zab2(j5,j1,j2,j4)-zab(j5,j6,j4))
+zb(j4,j6)/zb(j5,j6)
*(2*(zab(j2,j3,j6)*delta34-zab(j2,j5,j6) *delta56 )
+zab(j3,j4,j6)*zab2(j2,j1,j4,j3))
-zab(j2,j1,j3)*(zab(j5,j3,j6)-zab(j5,j4,j6))*delta12
/zab2(j4,j1,j2,j3)
-4*za(j1,j2)*zb(j3,j6)*(za(j3,j5)*zb(j1,j4)
+za(j3,j4)*za(j5,j6)*zb(j1,j3)*zb(j4,j6)/zab2(j4,j1,j2,j3))
+zb(j4,j6)*(zab(j2,j4,j6)*za(j6,j5)-zab(j2,j1,j3)*za(j3,j5)))
+zab2(j5,j1,j2,j3)
*(za(j2,j5)*za(j3,j4)-za(j2,j3)*za(j4,j5))
/(za(j3,j4)*za(j5,j6)*zab2(j4,j1,j2,j3)))"""

joined = " ".join(line.strip() for line in expr.splitlines())
depth = 0
mind = 0
for ch in joined:
    if ch == '(':
        depth += 1
    elif ch == ')':
        depth -= 1
        mind = min(mind, depth)
print("final depth:", depth, "min depth:", mind)
print(joined)

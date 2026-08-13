expr = """-0.5_dp/(zb(j2,j3)*zab2(j4,j1,j2,j3)*Delta3)
*(
-6*zb(j1,j2)*zab2(j5,j1,j2,j6)*zb(j4,j3)*zab2(j3,j1,j2,j4)
*(za(j2,j4)*delta56-2*zab(j2,j1,j3)*za(j3,j4))/Delta3
+zb(j1,j3)/zab2(j4,j1,j2,j3)
*(delta34*(t(j1,j2,j3)-t(j1,j2,j4))-Delta3)
*(zab(j5,j3,j4)*za(j4,j5)/za(j5,j6)
 +zba(j6,j3,j4)*zb(j4,j6)/zb(j5,j6))
+zab(j5,j3,j4)/za(j5,j6)
*(2*(zab(j5,j4,j1)*delta34-zab(j5,j6,j1)*delta56)
+zab2(j4,j2,j3,j1)*zab2(j5,j1,j2,j4))
-zb(j4,j6)/zb(j5,j6)
*(2*zab(j3,j2,j1)
*(zb(j3,j6)*delta12-2*zba(j3,j4,j5)*zb(j5,j6))
+zba2(j1,j2,j3,j4)*zb(j4,j3)*zab2(j3,j1,j2,j6)
-3*zba(j6,j4,j3)*zb(j3,j1)*delta34))"""

joined = " ".join(line.strip() for line in expr.splitlines())
depth = 0
out = []
mind=0
for ch in joined:
    if ch == '(':
        out.append(f"({depth+1}")
        depth += 1
    elif ch == ')':
        out.append(f"){depth}")
        depth -= 1
        mind=min(mind,depth)
    else:
        out.append(ch)
print("final depth", depth, "min depth", mind)
print("".join(out))

import re

for name in ["pp_mod", "ppwp2j_mod"]:
    path = f"software/mcfm/src/Mods/{name}.f90"
    text = open(path).read()
    start = text.index("reshape((/") + len("reshape((/")
    end = text.index("/), (/ 9,9,9,9 /))") if "/), (/ 9,9,9,9 /))" in text else text.index("/) &\n    , (/ 9,9,9,9 /))")
    body = text[start:end]
    nums = [int(x) for x in re.findall(r"-?\d+", body)]
    print(name, len(nums), sum(1 for n in nums if n != 0))
    with open(f"dev/tmp/{name}_flat.txt", "w") as f:
        f.write(",".join(str(n) for n in nums))

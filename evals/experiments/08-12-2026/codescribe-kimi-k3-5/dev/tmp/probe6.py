import re, glob

# Check: scaled-line regex compatibility for each marked line, and that wrappers
# call straight through to same-named C++ functions (marker propagates).
files = ["fmt", "fzip", "storecsz", "ampqqb_qqb", "Bdiff", "msq_z2jetx"]
for f in files:
    path = f"software/mcfm/src/Z2jet/{f}.cpp"
    text = open(path).read()
    n = text.count("@coverage-probe")
    marked = [l for l in text.splitlines() if "@coverage-probe" in l][0]
    has_assign = bool(re.search(r"(=\s*)(.*);(\s*//.*@coverage-probe.*)$", marked))
    print(f"{f}.cpp: markers={n} scalable_assignment={has_assign}")
    print("   line:", marked.strip()[:100])

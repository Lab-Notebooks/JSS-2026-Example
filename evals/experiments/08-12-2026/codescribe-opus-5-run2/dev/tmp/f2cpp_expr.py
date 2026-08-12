"""Mechanically convert the fixed-form expression bodies of fpm.f / fsl.f to C++.

usage: python3 dev/tmp/f2cpp_expr.py <file.f> <result-name>
Prints the converted statement block on stdout.
"""
import re
import sys


def logical_lines(path):
    stmts = []
    with open(path) as fh:
        for raw in fh:
            line = raw.rstrip("\n").rstrip()
            if not line.strip():
                continue
            if line[0] in "cC*!":
                continue
            if len(line) > 5 and line[5] not in (" ", "0"):
                stmts[-1] += line[6:].strip()
            else:
                stmts.append(line[6:].strip() if len(line) > 6 else line.strip())
    return stmts


def convert_pow(text):
    while True:
        i = text.find("**")
        if i < 0:
            return text
        m = re.match(r"\d+", text[i + 2:])
        if not m:
            raise SystemExit("non-integer exponent near: " + text[i - 30:i + 30])
        expo = m.group(0)
        end = i + 2 + len(expo)
        # find start of the base operand
        j = i - 1
        if text[j] == ")":
            depth = 0
            while j >= 0:
                if text[j] == ")":
                    depth += 1
                elif text[j] == "(":
                    depth -= 1
                    if depth == 0:
                        break
                j -= 1
            k = j - 1
            while k >= 0 and (text[k].isalnum() or text[k] == "_"):
                k -= 1
            start = k + 1
        else:
            k = j
            while k >= 0 and (text[k].isalnum() or text[k] == "_"):
                k -= 1
            start = k + 1
        base = text[start:i]
        text = text[:start] + "std::pow(" + base + ", @" + expo + "@)" + text[end:]


def convert(stmt):
    s = stmt
    s = s.replace("._dp", ".0")
    s = convert_pow(s)
    # bare integer literals become doubles (protected pow exponents keep @)
    s = re.sub(r"(?<![\w.@])(\d+)(?![\w.@])", r"\1.0", s)
    s = s.replace("@", "")
    s = re.sub(r"\bLnrat\b", "lnrat", s)
    s = re.sub(r"\bI3m\b", "i3m", s)
    return s + ";"


def main():
    path, result = sys.argv[1], sys.argv[2]
    out = []
    started = False
    for stmt in logical_lines(path):
        low = stmt.lower()
        if re.match(r"^(s\d+|t0)\s*=", low) or low.startswith(result.lower() + "="):
            started = True
            if low.startswith(result.lower() + "="):
                rhs = stmt.split("=", 1)[1].strip()
                out.append("%s_value = %s;   // @coverage-probe" % (result, rhs))
            else:
                out.append(convert(stmt))
        elif started and low in ("return", "end"):
            break
    print("\n".join("  " + line for line in out))


main()

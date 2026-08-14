"""Inline the moved tri123x4x56coeffs.f into qqbggAxtri123x4x56.f.

The include file was moved to Inc/deprecated/ (off the compiler include path),
so the coefficient assignments are inlined verbatim at the former include site.
"""

src = 'software/mcfm/src/W2jet/qqbggAxtri123x4x56.f'
coeffs = 'software/mcfm/src/Inc/deprecated/tri123x4x56coeffs.f'

with open(coeffs) as f:
    lines = f.readlines()

# strip the 5-line header (SPDX comment block + blank line); keep assignments
body = lines[5:]

with open(src) as f:
    text = f.read()

old = "      include 'tri123x4x56coeffs.f'\n"
assert old in text, 'include line not found'

inlined = (
    "c--- coeff2 assignments inlined from former include 'tri123x4x56coeffs.f'\n"
    "c--- (original file moved to Inc/deprecated/tri123x4x56coeffs.f)\n"
    + ''.join(body)
)

text = text.replace(old, inlined)
with open(src, 'w') as f:
    f.write(text)
print('inlined', len(body), 'lines into', src)

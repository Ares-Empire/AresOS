# Logo block golden

`compass-layout.txt` freezes the 32×32 block conversion of the original geometric
`../icons/compass.png` fixture. Each line is one source row, top to bottom;
`.` places no block. The symbols `0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkl`
index `LogoPixels.PALETTE` in order: 16 concrete, 16 wool, then 16 terracotta.

The file was generated once during package 08 and visually checked against the
wall and floor screenshots. Tests compare every cell and never rewrite it.
Palette changes require reviewing this golden and both in-game fixtures.

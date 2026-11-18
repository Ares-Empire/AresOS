const shade = (hex, amount) => {
  const n = parseInt(hex.slice(1), 16), to = amount < 0 ? 0 : 255, t = Math.abs(amount);
  const mix = c => Math.round(c + (to - c) * t);
  return `rgb(${mix(n >> 16)},${mix((n >> 8) & 255)},${mix(n & 255)})`;
};

/** Draws a logo into a new canvas. cell: pixels per block. depth: pixels the logo reaches back (drawn up and to
 *  the right, so a logo is a solid thing with a top and a side, as in the world); 0 draws the flat front. */
export function logoCanvas(app, cell, depth = 0) {
  const scale = window.devicePixelRatio || 1, size = 12 * cell + depth;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = Math.round(size * scale);
  canvas.style.width = canvas.style.height = size + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(scale, scale);
  const solid = (u, v) => u >= 0 && u < 12 && v >= 0 && v < 12 && app.cells[v][u] !== null;
  const at = (u, v) => [u * cell, depth + (11 - v) * cell];
  const colour = (u, v) => app.cells[v][u] === 'door' ? '#050506' : app.cells[v][u];
  if (depth) for (let v = 0; v < 12; v++) for (let u = 0; u < 12; u++) {
    if (!solid(u, v)) continue;
    const [x, y] = at(u, v), c = colour(u, v);
    if (!solid(u, v + 1)) {
      ctx.fillStyle = shade(c, 0.22);
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + cell, y); ctx.lineTo(x + cell + depth, y - depth);
      ctx.lineTo(x + depth, y - depth); ctx.fill();
    }
    if (!solid(u + 1, v)) {
      ctx.fillStyle = shade(c, -0.45);
      ctx.beginPath(); ctx.moveTo(x + cell, y); ctx.lineTo(x + cell, y + cell);
      ctx.lineTo(x + cell + depth, y + cell - depth); ctx.lineTo(x + cell + depth, y - depth); ctx.fill();
    }
  }
  for (let v = 0; v < 12; v++) for (let u = 0; u < 12; u++) {
    if (!solid(u, v)) continue;
    const [x, y] = at(u, v);
    ctx.fillStyle = colour(u, v);
    ctx.fillRect(x, y, cell, cell);
    if (cell >= 6 && app.cells[v][u] !== 'door') {   // a hint of single blocks
      ctx.fillStyle = 'rgba(255,255,255,0.09)'; ctx.fillRect(x, y, cell, 1);
      ctx.fillStyle = 'rgba(0,0,0,0.16)'; ctx.fillRect(x, y + cell - 1, cell, 1);
    }
  }
  return canvas;
}

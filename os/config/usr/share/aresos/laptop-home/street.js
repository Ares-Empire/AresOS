import { logoCanvas } from './logo.js';

export const WIDTH = 1920, HEIGHT = 1080;
const MID = WIDTH / 2, ROAD = 16, EDGE = 40, FLOOR = 948;
const TREAD = 14, LIP = 4;
const groups = [
  { key: 'internet', name: 'Internet', direction: 'north', colour: '#3AB3DA', block: '#2a8fce' },
  { key: 'games', name: 'Games', direction: 'east', colour: '#FF6257', block: '#b3302c' },
  { key: 'work_media', name: 'Work & Media', direction: 'west', colour: '#C774F2', block: '#7a2cb8' },
  { key: 'system_tools', name: 'System & Tools', direction: 'south', colour: '#FED83D', block: '#e9ae1d' },
];

function element(tag, className, text) {
  const el = document.createElement(tag);
  el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

// Each row adds one place per side. Interleave the sides to assign temporary places in the world's order.
function placeIndex(place, letter) {
  const fields = /^([NEWS])(0|[1-9]\d?)([LR])(0|[1-9]\d?)$/.exec(place);
  if (!fields || fields[1] !== letter) return -1;
  const row = Number(fields[2]), side = fields[3], column = Number(fields[4]);
  // The world's Place supports rows 0–63, with columns 0 through the row number.
  return row < 64 && column <= row ? row * (row + 1) + 2 * column + Number(side === 'R') : -1;
}

function layout(apps, day) {
  const streets = groups.map(group => {
    const placed = apps.filter(app => app.group === group.key).map(app => ({
      app, index: placeIndex(app.place, group.direction[0].toUpperCase()),
    }));
    let next = Math.max(-1, ...placed.map(spot => spot.index)) + 1;
    return placed.map(({ app, index }) => {
      const position = index < 0 ? next++ : index;
      return { app, side: position % 2 ? 'R' : 'L', slot: Math.floor(position / 2) };
    });
  });
  const slots = Math.max(1, ...streets.flat().map(spot => spot.slot + 1));
  const fit = day ? (MID - EDGE) / (14 * slots + 13) : (MID - 100 - EDGE) / (14.6 * slots);
  const cell = Math.max(7, Math.min(10, Math.floor(fit)));
  const pitch = day ? 14 * cell : Math.round(14.6 * cell), gap = day ? 30 * cell : 200;
  const size = 12 * cell, depth = Math.round(cell * 0.9);
  const cols = Math.floor(((MID - EDGE) / cell - 13) / 14);
  for (const spot of streets.flat())
    spot.x = spot.side === 'L' ? MID - gap / 2 - spot.slot * pitch - size : MID + gap / 2 + spot.slot * pitch;
  return { streets, cell, pitch, gap, size, depth, cols };
}

function paintTerraces(stage, ground) {
  const stops = ['var(--sky) 0', `var(--sky-low) ${ground[0] - TREAD}px`];
  ground.forEach((base, i) => {
    const lip = base + ROAD + LIP;
    const bankEnd = i + 1 < ground.length ? ground[i + 1] - TREAD : HEIGHT;
    stops.push(`var(--turf) ${base - TREAD}px ${lip}px`, `var(--bank-edge) ${lip}px ${lip + 2}px`,
      `var(--bank-top) ${lip + 2}px`, `var(--bank) ${bankEnd}px`);
  });
  stage.style.background = `linear-gradient(${stops.join(', ')})`;
}

function makeStars(stage) {
  let seed = 44;
  const next = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const stars = Array.from({ length: 90 }, () => {
    const star = element('i', 'star');
    star.style.cssText = `left:${Math.round(next() * 1916)}px;top:${Math.round(next() * 900)}px;opacity:${(0.1 + next() * 0.35).toFixed(2)}`;
    return star;
  });
  stage.prepend(...stars);
  setInterval(() => {
    if (document.hidden) return;
    const star = stars[Math.floor(Math.random() * stars.length)];
    star.style.opacity = Number(star.style.opacity) > 0.24 ? '0.12' : '0.38';
  }, 4000);
}

function makeHouse({ app, x, side, slot }, { cell, size, depth }) {
  const house = element('button', 'house');
  house.type = 'button';
  house.dataset.app = app.id;
  house.dataset.side = side;
  house.dataset.slot = slot;
  house.style.cssText = `left:${x}px;width:${size}px;height:${size + depth + 54}px`;
  const sign = element('span', 'house-sign');
  sign.style.bottom = size + depth + 3 + 'px';
  sign.append(element('b', '', app.name), element('span', '', '/' + app.short));
  const door = element('i', 'door'), mat = element('i', 'mat'), frame = element('i', 'frame');
  door.style.cssText = `left:${5 * cell}px;width:${2 * cell}px;height:${3 * cell}px`;
  mat.style.cssText = `left:${5 * cell}px;width:${2 * cell}px`;
  frame.style.cssText = `width:${size + 14}px;height:${size + 14}px`;
  house.append(logoCanvas(app, cell, depth), door, mat, frame, sign);
  return house;
}

function makeStreet(group, top, height, base, spots, grid, day, onPan) {
  const { cell, pitch, gap, size, depth, cols } = grid;
  const margin = Math.floor(cell / 2);
  const street = element('section', 'street'), view = element('div', 'view'), slide = element('div', 'slide');
  street.dataset.group = group.key;
  street.setAttribute('aria-label', group.name);
  street.style.cssText = `top:${top}px;height:${height}px;--g:${group.colour};--b:${group.block};--cell:${cell}px;--pitch:${pitch}px;--depth:${depth}px;--plot-w:${size + 2 * margin}px;--joint:${(MID - gap / 2) % (2 * cell)}px;--name:${cell >= 9 ? 14 : 13}px`;
  const far = side => Math.max(-1, ...spots.filter(s => s.side === side).map(s => s.slot));
  const road = element('div', 'road');
  let roadStart = 0, roadEnd = WIDTH;
  if (day) {
    for (const side of ['L', 'R']) {
      const count = Math.max(cols, far(side) + 1);
      const plots = element('div', `plots plots-${side}`);
      plots.dataset.n = count;
      const first = side === 'L' ? MID - gap / 2 - (count - 1) * pitch - size : MID + gap / 2;
      plots.style.cssText = `left:${first - margin}px;width:${(count - 1) * pitch + size + 2 * margin}px`;
      slide.append(plots);
    }
    street.append(road);
  } else {
    roadStart = MID - gap / 2 - (far('L') < 0 ? 0 : far('L') * pitch + size + 2 * cell);
    roadEnd = MID + gap / 2 + (far('R') < 0 ? 0 : far('R') * pitch + size + 2 * cell);
    road.style.cssText = `left:${roadStart}px;width:${roadEnd - roadStart}px`;
    slide.append(road);
  }
  const sign = element('button', 'street-sign');
  sign.type = 'button';
  sign.style.bottom = ROAD + Math.round(size * 0.42) + 'px';
  sign.append(element('b', '', group.name), element('span', '', `${group.direction} · ${spots.length}`));
  slide.append(sign, ...spots.map(spot => makeHouse(spot, grid)));
  view.append(slide);
  street.append(view);

  const xs = spots.map(spot => spot.x);
  const snap = offset => day ? Math.sign(offset) * Math.ceil(Math.abs(offset) / pitch) * pitch : offset;
  const range = [snap(Math.min(0, WIDTH - EDGE - Math.max(MID, ...xs.map(x => x + size)))),
    snap(Math.max(0, EDGE - Math.min(MID, ...xs)))];
  const ends = ['L', 'R'].map(side => {
    const end = element('button', `street-end end-${side}`), fade = element('div', `street-fade fade-${side}`);
    end.type = 'button';
    end.style.bottom = ROAD + Math.round(size / 2) - 16 + 'px';
    street.append(fade, end);
    return { side, end, fade };
  });
  let offset = 0, byHand = false, matches = null;
  function position(value, hits) {
    const next = Math.max(range[0], Math.min(range[1], Math.round(value)));
    if (offset !== next) {
      offset = next;
      slide.style.transform = offset ? `translateX(${offset}px)` : '';
    }
    matches = hits;
    for (const { side, end, fade } of ends) {
      const hidden = spots.filter(({ x }) => side === 'L'
        ? x + offset < EDGE / 2 : x + offset + size > WIDTH - EDGE / 2);
      const count = matches ? hidden.filter(({ app }) => matches.has(app.id)).length : hidden.length;
      const label = side === 'L' ? `‹ ${count}` : `${count} ›`;
      if (end.textContent !== label) end.textContent = label;
      const cut = hidden.length > 0;
      if (end.hidden === cut) end.hidden = fade.hidden = !cut;
      const title = matches ? `${count} matching out of ${hidden.length} hidden houses` : `${count} hidden houses`;
      if (end.title !== title) end.title = title;
      view.classList.toggle(`cut-${side}`, cut);
    }
  }
  const pan = (value, manual) => {
    byHand = manual;
    position(value, matches);
    onPan(spots.filter(({ x }) => x + offset >= EDGE && x + offset + size <= WIDTH - EDGE)
      .map(({ app }) => app.id), group.key);
  };
  for (const { side, end } of ends)
    end.addEventListener('click', () => pan(side === 'L' ? range[1] : range[0], true));
  sign.addEventListener('click', () => pan(0, false));

  const ledges = [{ id: `street:${group.key}`, ownerId: 'town', kind: 'edge', x1: roadStart, x2: roadEnd,
    y: base, weight: 2 }];
  const boxes = [];
  for (const { app, x } of spots) {
    const roof = app.cells.findLastIndex(row => row.some(Boolean));
    const roofHeight = (roof + 1) * cell;
    const topBlocks = app.cells[roof].flatMap((c, i) => c ? [i] : []);
    if (topBlocks.length) ledges.push({ id: `roof:${app.id}`, ownerId: `house:${app.id}`, kind: 'edge',
      x1: x + topBlocks[0] * cell, x2: x + (topBlocks.at(-1) + 1) * cell,
      y: base - roofHeight, room: height - ROAD - roofHeight });
    boxes.push({ id: `house:${app.id}`, z: 1, l: x, t: base - size, r: x + size, b: base });
  }
  return {
    street, cell, key: group.key,
    reset() { byHand = false; },
    manualPan() { return byHand ? (day ? offset / pitch : offset) : null; },
    restorePan(pan) {
      if (pan == null) return;
      byHand = true;
      position(day ? pan * pitch : pan, null);
    },
    follow(id, hits) {
      const spot = spots.find(({ app }) => app.id === id);
      if (!spot) return position(byHand ? offset : 0, hits);
      // Snap into the visible interval. Rounding away from zero alone can overshoot after a hand slide.
      const lo = EDGE - spot.x, hi = WIDTH - EDGE - size - spot.x;
      position(!day ? Math.min(Math.max(offset, lo), hi)
        : offset < lo ? Math.ceil(lo / pitch) * pitch : offset > hi ? Math.floor(hi / pitch) * pitch : offset, hits);
    },
    sample() {
      // Companions read the live transform on demand, including the frames between the two grid positions.
      const transform = getComputedStyle(slide).transform;
      const current = transform === 'none' ? 0 : new DOMMatrixReadOnly(transform).m41;
      return { current, ledges: ledges.map((ledge, i) => i === 0 && day ? { ...ledge }
        : { ...ledge, x1: ledge.x1 + current, x2: ledge.x2 + current }),
      boxes: boxes.map(box => ({ ...box, l: box.l + current, r: box.r + current })) };
    },
  };
}

export function mountStreet(stage, town, day, onPan) {
  const top = day ? 126 : 150, height = day ? 202 : 196;
  const ground = groups.map((_, index) => top + (index + 1) * height - ROAD);
  stage.style.setProperty('--edge', EDGE + 'px');
  if (day) paintTerraces(stage, ground);
  else makeStars(stage);
  let streets = [];
  return {
    draw(apps) {
      const grid = layout(apps, day);
      const pans = new Map(streets.map(street => [street.key, street.manualPan()]));
      streets = groups.map((group, i) =>
        makeStreet(group, top + i * height, height, ground[i], grid.streets[i], grid, day, onPan));
      for (const street of streets) street.restorePan(pans.get(street.key));
      town.replaceChildren(...streets.map(street => street.street));
    },
    follow(id, matches) { streets.forEach(street => street.follow(id, matches)); },
    reset() { streets.forEach(street => street.reset()); },
    puff(house) {
      const cell = streets.find(({ street }) => street.contains(house)).cell;
      for (let i = 0; i < 9; i++) {
        const particle = element('i', 'puff');
        particle.style.cssText = `left:${(4.5 + Math.random() * 2) * cell}px;bottom:${(1 + Math.random() * 2) * cell}px;--dx:${(Math.random() - 0.5) * 70}px;--dy:${-30 - Math.random() * 60}px`;
        particle.addEventListener('animationend', () => particle.remove(), { once: true });
        house.append(particle);
      }
    },
    snapshot() {
      const samples = streets.map(street => [street.key, street.sample()]);
      return { viewport: { width: WIDTH, height: HEIGHT, dpr: devicePixelRatio || 1 },
        streetOffsets: Object.fromEntries(samples.map(([key, info]) => [key, info.current])),
        surfaces: samples.flatMap(([, info]) => info.ledges), occluders: samples.flatMap(([, info]) => info.boxes),
        floor: { x1: 0, x2: WIDTH, y: FLOOR, weight: 1.2 } };
    },
  };
}

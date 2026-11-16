/* Development aid for AresOS package 44 (the laptop-screen home, a design study). Not product code.
 *
 * What the three prototypes share: a town of test apps with generated block logos, a stand-in for the app
 * helper, the hotbar, finding an app by typing, and a window that stands in for an opened app.
 * No network, no build step. The pictures are drawn here from a few hand-made glyphs and flat colours:
 * no app icon, no logo and no game texture is used.
 *
 * Page address options (for the pictures): ?apps=5|12|24|40  &q=<typed text>  &open=<id,id>  &run=<id,id>
 * &sel=<id>  &time=HH:MM  &still=1 (no motion).
 */
'use strict';

const Home = (() => {
  const params = new URLSearchParams(location.search);
  const listParam = name => (params.get(name) || '').split(',').filter(Boolean);

  // The four groups of docs/design/HUB.md 2.2, in its order, with the colours their names are written in
  // (AppGroup.java). `block` is the colour of the road line and the doormat.
  const GROUPS = [
    { key: 'internet', title: 'Internet', where: 'north', letter: 'N', colour: '#3AB3DA', block: '#2a8fce', word: 'Web' },
    { key: 'games', title: 'Games', where: 'east', letter: 'E', colour: '#FF6257', block: '#b3302c', word: 'Game' },
    { key: 'work_media', title: 'Work & Media', where: 'west', letter: 'W', colour: '#C774F2', block: '#7a2cb8', word: 'Media' },
    { key: 'system_tools', title: 'System & Tools', where: 'south', letter: 'S', colour: '#FED83D', block: '#e9ae1d', word: 'Tool' },
  ];
  const group = key => GROUPS.find(g => g.key === key);

  // How many test apps each group gets, for the town sizes HUB.md 2.2 talks about.
  const MIXES = { 5: [2, 1, 0, 2], 12: [4, 2, 2, 4], 24: [7, 4, 5, 8], 40: [9, 8, 9, 14] };
  const EXTRAS = ['Mail', 'PDF Viewer', 'Calculator', 'Files', 'Paint', 'Recorder', 'Clock', 'Maps', 'Weather',
    'Notes', 'Archive', 'Monitor', 'Printer', 'Scanner', 'Camera', 'Fonts', 'Disks', 'Colours', 'Chat', 'Radio'];

  // ---- block logos -------------------------------------------------------------------------------------------

  const INK = { white: '#e6e8e6', silver: '#8f918a', gray: '#3b3e44', black: '#131419', red: '#a32a2a',
    orange: '#e06c10', yellow: '#f0b41e', lime: '#66b120', green: '#4b6428', cyan: '#19828f', sky: '#2c92d0',
    blue: '#31369c', purple: '#6d27a8', magenta: '#b43da8', pink: '#d96e97', brown: '#6b4628' };
  // Plate and figure colours that read well together.
  const PAIRS = [['sky', 'white'], ['black', 'yellow'], ['red', 'white'], ['white', 'purple'], ['lime', 'black'],
    ['orange', 'white'], ['gray', 'lime'], ['blue', 'yellow'], ['white', 'red'], ['cyan', 'white'],
    ['magenta', 'white'], ['yellow', 'black'], ['green', 'yellow'], ['purple', 'pink'], ['silver', 'blue'],
    ['black', 'sky'], ['pink', 'blue'], ['brown', 'orange']];
  // Hand-made 8 x 8 figures (generic signs, nobody's logo).
  const GLYPHS = [
    '..####...##..##.##....###......##......###....##.##..##...####..', // ring
    '.#.......###.....#####...#######.#######.#####...###.....#......', // play
    '.##..##.########################.######...####.....##...........', // heart
    '...##......##......##...################...##......##......##...', // plus
    '..####...####...####....####....####....####...#.######...####..', // moon
    '.######.################################.######...##.....##.....', // speech
    '........#........#........#......#......#...####................', // prompt
    '##########....###.#..#.##..##..##......##......#########........', // letter
    '...#####...#####...#...#...#...#...#...#.###.#######.###.##...#.', // note
    '#..##..#.######..##..##.##....####....##.##..##..######.#..##..#', // gear
    '...##.....####...######.################.######...####.....##...', // diamond
    '###.....################################################........', // folder
    '....###....###....###....######....###....###....###.....#......', // bolt
    '.........##..##..##..##.........#......###....##.######...####..', // face
    '...##......##......##...#..##..#.######...####.....##...########', // arrow
    '###..######..######..###................###..######..######..###', // panes
  ];

  /** The 12 x 12 cells of a test app's logo: cells[v][u], v counted from the ground, each a colour or null.
   *  It follows HUB.md 2.3 and 3.6: a figure on a plate (or a bare figure), and the doorway at the bottom middle. */
  function logoCells(index) {
    const [plateName, figureName] = PAIRS[(index * 7 + 3) % PAIRS.length];
    const plate = INK[plateName], figure = INK[figureName];
    const cells = Array.from({ length: 12 }, () => Array(12).fill(null));
    const shape = index % 9 === 4 ? 'ring' : index % 11 === 7 ? 'diamond' : index % 4 === 2 ? 'round' : 'plate';
    for (let v = 0; v < 12; v++) for (let u = 0; u < 12; u++) {
      const dx = u - 5.5, dy = v - 5.5, far = dx * dx + dy * dy, steps = Math.abs(dx) + Math.abs(dy);
      if (shape === 'plate' || (shape === 'round' && far <= 39)) cells[v][u] = plate;
      else if (shape === 'ring' && far <= 39) cells[v][u] = far >= 13 ? plate : far <= 5 ? figure : null;
      else if (shape === 'diamond' && steps <= 6.5) cells[v][u] = steps <= 2.5 ? figure : plate;
    }
    if (shape === 'plate' || shape === 'round') {
      const glyph = GLYPHS[(index * 5 + 1) % GLYPHS.length];
      for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) if (glyph[r * 8 + c] === '#') cells[10 - r][2 + c] = figure;
    }
    // The doorway (columns 5 and 6, three high) with its posts and the bar over it, HUB.md 3.6 step 6.
    for (let v = 0; v < 3; v++) { cells[v][5] = cells[v][6] = 'door'; for (const u of [4, 7]) cells[v][u] ??= INK.black; }
    for (let u = 4; u < 8; u++) cells[3][u] ??= INK.black;
    return cells;
  }

  const shade = (hex, amount) => {
    const n = parseInt(hex.slice(1), 16), to = amount < 0 ? 0 : 255, t = Math.abs(amount);
    const mix = c => Math.round(c + (to - c) * t);
    return `rgb(${mix(n >> 16)},${mix((n >> 8) & 255)},${mix(n & 255)})`;
  };

  /** Draws a logo into a new canvas. cell: pixels per block. depth: pixels the logo reaches back (drawn up and to
   *  the right, so a logo is a solid thing with a top and a side, as in the world); 0 draws the flat front. */
  function logoCanvas(app, cell, depth = 0) {
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

  // ---- the test town -----------------------------------------------------------------------------------------

  /** Place number i of a group, nearest first (HUB.md 3.3): row, then k from the road, left before right. */
  function place(letter, i) {
    let row = 0;
    while (i >= 2 * (row + 1)) { i -= 2 * (row + 1); row++; }
    const k = i >> 1, side = i % 2 ? 'R' : 'L';
    return { row, k, side, name: `${letter}${row}${side}${k}` };
  }

  function makeTown(count) {
    const mix = MIXES[count] || MIXES[24];
    const apps = [];
    GROUPS.forEach((g, gi) => {
      for (let i = 0; i < mix[gi]; i++) {
        const index = apps.length;
        apps.push({ id: `test-${g.word.toLowerCase()}-${i + 1}`, name: `Test ${g.word} ${i + 1}`,
          short: `${g.word.toLowerCase()}${i + 1}`, group: g.key, mine: true, place: place(g.letter, i),
          cells: logoCells(index * 3 + gi), slot: null });
      }
    });
    // The hotbar: the first apps of each group in turn, seven of nine slots (three on day one).
    const pins = count <= 5 ? ['test-web-1', 'test-tool-1', 'test-tool-2']
      : ['test-web-1', 'test-web-2', 'test-game-1', 'test-media-1', 'test-tool-1', 'test-tool-2', 'test-media-2'];
    pins.forEach((id, slot) => { const app = apps.find(a => a.id === id); if (app) app.slot = slot; });
    // "All programs": everything else the system lists. They have no logo in the town.
    const programs = EXTRAS.map((word, i) => ({ id: `test-${word.toLowerCase().replace(/ /g, '-')}`,
      name: `Test ${word}`, short: null, group: GROUPS[(i * 3 + 3) % 4].key, mine: false,
      cells: logoCells(100 + i * 2), slot: null }));
    return { apps, programs, byId: new Map([...apps, ...programs].map(a => [a.id, a])) };
  }

  const town = makeTown(Number(params.get('apps')) || 24);

  // ---- state and the helper's stand-in -----------------------------------------------------------------------

  const state = { query: '', selected: null, running: new Set(listParam('run')), matches: null,
    best: null };
  const listeners = {};
  const on = (event, fn) => { (listeners[event] ||= []).push(fn); };
  const emit = (event, ...args) => (listeners[event] || []).forEach(fn => fn(...args));
  const still = params.has('still');
  if (still) document.documentElement.classList.add('still');

  /** Every element with data-app shows that app; this sets what the page's own CSS turns into a look. */
  function refresh() {
    document.querySelectorAll('[data-app]').forEach(el => {
      const id = el.dataset.app;
      el.classList.toggle('is-running', state.running.has(id));
      el.classList.toggle('is-dim', !!state.matches && !state.matches.has(id));
      el.classList.toggle('is-match', !!state.matches && state.matches.has(id));
      el.classList.toggle('is-best', state.best === id && !el.closest('.hotbar'));
      el.classList.toggle('is-selected', state.selected === el);
    });
    emit('refresh');
  }

  /** Opens an app as the helper would: a moment of "opening", then its window, and it counts as running. */
  function open(id, instant = false) {
    const app = town.byId.get(id);
    if (!app) return;
    const finish = () => {
      document.querySelectorAll(`[data-app="${id}"]`).forEach(el => el.classList.remove('is-opening'));
      state.running.add(id);
      showWindow(app);
      setQuery('');
      emit('opened', app);
    };
    if (instant || still) return finish();
    document.querySelectorAll(`[data-app="${id}"]`).forEach(el => el.classList.add('is-opening'));
    emit('opening', app);
    setTimeout(finish, 420);
  }

  // ---- the window that stands in for an app ------------------------------------------------------------------

  let windowsLayer = null, windowCount = 0;
  function showWindow(app) {
    const n = windowCount++;
    const win = document.createElement('div');
    win.className = 'win';
    win.style.left = (params.get('winx') ? Number(params.get('winx')) : 560) + n * 44 + 'px';
    win.style.top = (params.get('winy') ? Number(params.get('winy')) : 250) + n * 36 + 'px';
    win.innerHTML = '<div class="win-bar"><span class="win-menu"></span><span class="win-title"></span>' +
      '<span class="win-btn">&#x2013;</span><span class="win-btn">&#x25a1;</span><span class="win-btn win-close">&#x2715;</span></div>' +
      '<div class="win-body"><div class="win-logo"></div><b></b><small>This window stands in for the app. Close it with &#x2715;.</small></div>';
    win.querySelector('.win-title').textContent = app.name;
    win.querySelector('b').textContent = app.name;
    win.querySelector('.win-logo').append(logoCanvas(app, 8));
    win.querySelector('.win-close').addEventListener('click', () => {
      win.remove();
      if (![...windowsLayer.children].some(w => w.dataset.of === app.id)) state.running.delete(app.id);
      refresh();
      emit('closed', app);
    });
    win.dataset.of = app.id;
    const bar = win.querySelector('.win-bar');
    bar.addEventListener('pointerdown', down => {
      if (down.target.classList.contains('win-btn')) return;
      const zoom = win.getBoundingClientRect().width / win.offsetWidth;
      const x0 = down.clientX / zoom - win.offsetLeft, y0 = down.clientY / zoom - win.offsetTop;
      const move = e => { win.style.left = e.clientX / zoom - x0 + 'px'; win.style.top = e.clientY / zoom - y0 + 'px'; };
      bar.setPointerCapture(down.pointerId);
      bar.addEventListener('pointermove', move);
      bar.addEventListener('pointerup', () => bar.removeEventListener('pointermove', move), { once: true });
    });
    win.addEventListener('pointerdown', () => windowsLayer.append(win));
    windowsLayer.append(win);
    refresh();
  }

  // ---- finding an app by typing ------------------------------------------------------------------------------

  const squeeze = text => text.toLowerCase().replace(/[^a-z0-9]/g, '');
  function score(app, q) {
    const name = squeeze(app.name), words = app.name.toLowerCase().split(/\s+/);
    if (app.short === q) return 100;
    if (app.short && app.short.startsWith(q)) return 80;
    if (name.startsWith(q)) return 70;
    if (words.some(w => w.startsWith(q))) return app.mine ? 60 : 30;
    if (name.includes(q)) return app.mine ? 40 : 20;
    return 0;
  }

  let finder = null;
  function setQuery(text) {
    state.query = text;
    const q = squeeze(text);
    if (!q) { state.matches = null; state.best = null; }
    else {
      const found = [...town.apps, ...town.programs].map(app => [score(app, q), app]).filter(([s]) => s > 0)
        .sort((a, b) => b[0] - a[0] || b[1].mine - a[1].mine || a[1].name.localeCompare(b[1].name, 'en', { numeric: true }));
      state.matches = new Map(found.map(([, app]) => [app.id, app]));
      state.best = found.length ? found[0][1].id : null;
    }
    state.selected = null;
    drawFinder();
    refresh();
  }

  function drawFinder() {
    if (!finder) return;
    const typing = state.query !== '';
    finder.root.classList.toggle('is-typing', typing);
    finder.q.textContent = state.query;
    const best = state.best && town.byId.get(state.best);
    finder.hint.textContent = !typing ? finder.idle : best ? `Enter opens ${best.name}` : 'Nothing with that name';
    finder.hint.classList.toggle('none', typing && !best);
    finder.list.textContent = '';
    if (!typing) return;
    const others = [...state.matches.values()].filter(app => !app.mine);
    others.slice(0, 5).forEach(app => {
      const row = document.createElement('div');
      row.className = 'finder-row';
      row.dataset.app = app.id;
      const name = document.createElement('span');
      name.textContent = app.name;
      const kind = document.createElement('small');
      kind.textContent = group(app.group).title;
      row.append(logoCanvas(app, 2), name, kind);
      finder.list.append(row);
    });
    if (others.length) {
      const head = document.createElement('div');
      head.className = 'finder-head';
      head.textContent = others.length > 5 ? `All programs · ${others.length}` : 'All programs';
      finder.list.prepend(head);
    }
  }

  /** The typing line. root gets the list of other programs and the line itself; idle is the hint shown at rest. */
  function mountFinder(root, idle = 'Type a name to find an app') {
    root.classList.add('finder');
    root.innerHTML = '<div class="finder-list"></div><div class="finder-line"><span class="finder-slash">/</span>' +
      '<span class="finder-q"></span><span class="finder-caret"></span><span class="finder-hint"></span></div>';
    finder = { root, idle, q: root.querySelector('.finder-q'), hint: root.querySelector('.finder-hint'),
      list: root.querySelector('.finder-list') };
    drawFinder();
  }

  /** Moves the gold frame to the nearest shown app in a direction (arrow keys). */
  function step(dx, dy) {
    const shown = [...document.querySelectorAll('[data-app]')].filter(el => !el.classList.contains('is-dim') &&
      el.offsetParent && !el.closest('.win'));
    if (!shown.length) return;
    const middle = el => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
    const from = state.selected && shown.includes(state.selected) ? state.selected
      : shown.find(el => el.classList.contains('is-best')) || null;
    if (!from) { state.selected = shown[0]; return refresh(); }
    const [x0, y0] = middle(from);
    let next = null, least = Infinity;
    for (const el of shown) {
      if (el === from) continue;
      const [x, y] = middle(el), along = (x - x0) * dx + (y - y0) * dy, across = Math.abs((x - x0) * dy) + Math.abs((y - y0) * dx);
      if (along <= 4) continue;
      const cost = along + 2.5 * across;
      if (cost < least) { least = cost; next = el; }
    }
    if (next) { state.selected = next; refresh(); }
  }

  function keys() {
    document.addEventListener('keydown', e => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === 'Escape') { setQuery(''); }
      else if (e.key === 'Backspace') { setQuery(state.query.slice(0, -1)); }
      else if (e.key === 'Enter') {
        const id = state.selected ? state.selected.dataset.app : state.best;
        if (id) open(id);
      }
      else if (e.key.startsWith('Arrow')) {
        step(e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0, e.key === 'ArrowDown' ? 1 : e.key === 'ArrowUp' ? -1 : 0);
      }
      else if (e.key.length === 1) {
        // 1 to 9 with nothing typed are the hotbar's keys, as in the world.
        const pinned = !state.query && /[1-9]/.test(e.key) && town.apps.find(a => a.slot === Number(e.key) - 1);
        if (pinned) open(pinned.id);
        else if (e.key !== ' ' || state.query) setQuery(state.query + e.key);
      } else return;
      e.preventDefault();
    });
    document.addEventListener('click', e => {
      const el = e.target.closest('[data-app]');
      if (el && !e.target.closest('.win')) open(el.dataset.app);
    });
  }

  // ---- the pieces every direction shows ----------------------------------------------------------------------

  function mountHotbar(root) {
    root.classList.add('hotbar');
    for (let slot = 0; slot < 9; slot++) {
      const el = document.createElement('div');
      el.className = 'slot';
      const app = town.apps.find(a => a.slot === slot);
      if (app) { el.dataset.app = app.id; el.title = `${app.name}  /${app.short}`; el.append(logoCanvas(app, 4)); }
      const key = document.createElement('span');
      key.className = 'slot-key';
      key.textContent = slot + 1;
      el.append(key);
      root.append(el);
    }
  }

  function mountClock(root) {
    root.classList.add('clock');
    root.innerHTML = '<div class="clock-time"></div><div class="clock-date"></div>';
    const tick = () => {
      const now = new Date(), fixed = params.get('time');
      root.firstChild.textContent = fixed || now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
      root.lastChild.textContent = fixed ? 'Monday 16 November'
        : now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
    };
    tick();
    if (!params.get('time')) setInterval(tick, 10000);
  }

  function mountBattery(root) {
    root.classList.add('battery');
    root.innerHTML = '<span class="battery-shell"><i style="width:82%"></i></span><span class="battery-text">82%</span>';
  }

  /** The page is drawn at 1920 x 1080 and scaled to whatever window it is shown in. */
  function fit(stage) {
    const size = () => {
      const k = Math.min(innerWidth / 1920, innerHeight / 1080);
      stage.style.transform = `scale(${k})`;
      stage.style.left = (innerWidth - 1920 * k) / 2 + 'px';
      stage.style.top = (innerHeight - 1080 * k) / 2 + 'px';
    };
    size();
    addEventListener('resize', size);
  }

  /** Call once the page has built its scene. */
  function start(stage) {
    fit(stage);
    windowsLayer = document.createElement('div');
    windowsLayer.className = 'windows';
    stage.append(windowsLayer);
    keys();
    if (params.get('q')) setQuery(params.get('q'));
    listParam('open').forEach(id => open(id, true));
    const sel = params.get('sel');
    if (sel) state.selected = document.querySelector(`[data-app="${sel}"]`);
    refresh();
  }

  return { GROUPS, group, town, state, params, on, open, refresh, place, logoCanvas, mountHotbar, mountFinder, mountClock,
    mountBattery, start, still };
})();

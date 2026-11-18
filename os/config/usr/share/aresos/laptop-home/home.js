import { logoCanvas } from './logo.js';
import { WIDTH, HEIGHT, mountStreet } from './street.js';

const bridge = window.aresosHome;
const stage = document.getElementById('stage');
const hotbar = document.getElementById('hotbar');
const finder = document.getElementById('finder');
const input = finder.querySelector('.finder-q');
const hint = finder.querySelector('.finder-hint');
const caret = finder.querySelector('.finder-caret');
const results = finder.querySelector('.finder-list');
const battery = document.getElementById('battery');
const offline = 'Opening is back in a moment';
const day = document.documentElement.dataset.look === 'day';
document.documentElement.classList.toggle('day', day);

let houses = [], programs = [], byId = new Map(), pinned = new Map();
let online = false, running = new Set(), matches = null, query = '', best = null, selected = null;
let inputRevision = 0, launchRevision = 0, error = '', errorTimer;
const opening = new Set();
const street = mountStreet(stage, document.getElementById('town'), day, (visible, group) => {
  const target = byId.get(selected || best);
  if (target?.group !== group || visible.includes(target.id)) return;
  selected = [...(matches?.keys() || visible)].find(id => visible.includes(id)) || null;
  if (!selected) best = null;
  refresh();
});

window.laptopHome = Object.freeze({ world: Object.freeze({ snapshot: street.snapshot }) });

const squeeze = text => text.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
const wordStarts = (text, needle) => text?.toLowerCase().split(/[^\p{L}\p{N}]+/u).some(word => word.startsWith(needle));

// The order follows the seven kinds of hits in the Apps screen.
function score(app, needle) {
  const short = app.short && squeeze(app.short);
  const name = squeeze(app.name);
  if (short === needle) return 7;
  if (short?.startsWith(needle)) return 6;
  if (name.startsWith(needle)) return 5;
  if (wordStarts(app.name, needle)) return 4;
  if (name.includes(needle)) return 3;
  if (wordStarts(app.generic_name, needle)) return 2;
  if (app.keywords?.some(word => squeeze(word).startsWith(needle))) return 1;
  return 0;
}

function drawMatches() {
  const others = [...(matches?.values() || [])].filter(app => !app.mine);
  results.replaceChildren();
  if (!others.length) return;
  const heading = document.createElement('div');
  heading.className = 'finder-head';
  heading.textContent = others.length > 5 ? `All programs · ${others.length}` : 'All programs';
  results.append(heading);
  for (const app of others.slice(0, 5)) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'finder-row';
    row.dataset.app = app.id;
    const icon = document.createElement('span');
    icon.className = 'finder-icon';
    icon.setAttribute('aria-hidden', 'true');
    if (app.has_icon) {
      const image = document.createElement('img');
      image.alt = '';
      image.addEventListener('error', () => image.remove(), { once: true });
      image.src = `aresos-home://icon/${encodeURIComponent(app.id)}`;
      icon.append(image);
    }
    const name = document.createElement('span'), kind = document.createElement('small');
    name.textContent = app.name;
    kind.textContent = app.generic_name || '';
    row.append(icon, name, kind);
    results.append(row);
  }
}

function search() {
  const needle = squeeze(query);
  if (!query) matches = null;
  else {
    const ranked = needle ? [...byId.values()].map(app => ({ app, hit: score(app, needle) })).filter(item => item.hit) : [];
    ranked.sort((a, b) => b.hit - a.hit || Number(b.app.mine) - Number(a.app.mine) ||
      a.app.name.localeCompare(b.app.name, 'en', { numeric: true }));
    matches = new Map(ranked.map(({ app }) => [app.id, app]));
  }
  best = matches?.keys().next().value || null;
  if (!byId.has(selected) || (matches && !matches.has(selected))) selected = null;
  drawMatches();
}

function showHint() {
  const target = byId.get(selected || best);
  const message = !online ? offline : error || (target ? `Enter opens ${target.name}`
    : query ? 'Nothing with that name' : 'Type a name to find an app');
  if (hint.textContent !== message) hint.textContent = message;
  hint.title = message;
  finder.classList.toggle('has-message', !online || !!error);
}

function refresh() {
  const framed = selected || best;
  for (const element of stage.querySelectorAll('[data-app]')) {
    const id = element.dataset.app;
    element.classList.toggle('is-running', running.has(id));
    element.classList.toggle('is-opening', opening.has(id));
    element.classList.toggle('is-dim', !!matches && !matches.has(id));
    element.classList.toggle('is-match', !!matches?.has(id));
    element.classList.toggle('is-framed', id === framed && !element.classList.contains('slot'));
    if (element.getAttribute('aria-disabled') !== String(!online))
      element.setAttribute('aria-disabled', String(!online));
  }
  street.follow(framed, matches);
  showHint();
}

function clearError() {
  clearTimeout(errorTimer);
  error = '';
}

function setQuery(text) {
  inputRevision++;
  clearError();
  query = text.replace(/^\//, '').slice(0, 128);
  selected = null;
  input.textContent = query;
  finder.classList.toggle('is-typing', !!query);
  // A finite caret animation starts afresh on each keystroke.
  caret.style.animation = 'none';
  void caret.offsetWidth;
  caret.style.animation = '';
  search();
  refresh();
}

async function open(id) {
  const app = byId.get(id);
  if (!app || !online || opening.has(id)) return;
  const request = ++launchRevision, inputAtLaunch = inputRevision;
  clearError();
  opening.add(id);
  setTimeout(() => {
    opening.delete(id);
    refresh();
  }, 600);
  const house = document.querySelector(`.house[data-app="${id}"]`);
  if (house) street.puff(house);
  refresh();
  const result = await bridge.open(id).catch(() => ({ state: 'failed', message: 'Could not open the app' }));
  if (request !== launchRevision) return;
  if (result.state === 'failed') {
    error = result.message === offline ? offline : `Couldn't open ${app.name}: ${result.message}`;
    errorTimer = setTimeout(() => { error = ''; showHint(); }, 5000);
    showHint();
  } else if (inputAtLaunch === inputRevision) setQuery('');
}

function step(dx, dy) {
  const choices = [...stage.querySelectorAll('.house:not(.is-dim), .finder-row')];
  if (!choices.length) return;
  const from = choices.find(element => element.dataset.app === (selected || best));
  if (!from) selected = choices[0].dataset.app;
  else {
    const center = element => {
      const box = element.getBoundingClientRect();
      return [box.left + box.width / 2, box.top + box.height / 2];
    };
    const [x0, y0] = center(from);
    let least = Infinity;
    for (const element of choices) {
      const [x, y] = center(element);
      const along = (x - x0) * dx + (y - y0) * dy;
      const across = Math.abs((x - x0) * dy + (y - y0) * dx);
      const cost = along + 2.5 * across;
      if (along > 4 && cost < least) {
        least = cost;
        selected = element.dataset.app;
      }
    }
  }
  refresh();
}

function startInput() {
  const arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  document.addEventListener('keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.isComposing) return;
    const key = event.key;
    if (key === 'Escape') {
      street.reset();
      setQuery('');
    } else if (key === 'Backspace') setQuery([...query].slice(0, -1).join(''));
    else if (key === 'Enter') {
      const id = selected || best;
      if (!id) return; // Keep normal keyboard activation for a focused button.
      if (!event.repeat) open(id);
    } else if (arrows[key]) step(...arrows[key]);
    else if (key === ' ' && !query && event.target.closest?.('button')) return;
    else if (!query && /^[1-9]$/.test(key)) {
      if (!event.repeat) open(pinned.get(Number(key) - 1)?.id);
    } else if ([...key].length === 1 && (query || /[\p{L}\p{N}/]/u.test(key))) setQuery(query + key);
    else return;
    event.preventDefault();
  });
  stage.addEventListener('click', event => {
    const target = event.target.closest('[data-app]');
    if (target) open(target.dataset.app);
  });
  addEventListener('blur', () => {
    street.reset();
    setQuery('');
  });
}

function drawHotbar() {
  pinned = new Map(houses.filter(app => app.slot !== undefined).map(app => [app.slot, app]));
  hotbar.replaceChildren();
  for (let index = 0; index < 9; index++) {
    const app = pinned.get(index);
    const slot = document.createElement(app ? 'button' : 'div');
    slot.className = 'slot';
    if (app) {
      slot.type = 'button';
      slot.dataset.app = app.id;
      slot.title = `${app.name}  /${app.short}`;
      slot.setAttribute('aria-label', `${index + 1}. ${app.name}`);
      slot.append(logoCanvas(app, 4));
    }
    const key = document.createElement('span');
    key.className = 'slot-key';
    key.textContent = index + 1;
    key.setAttribute('aria-hidden', 'true');
    slot.append(key);
    hotbar.append(slot);
  }
}

function startClock() {
  const time = document.querySelector('.clock-time'), date = document.querySelector('.clock-date');
  function tick() {
    const now = new Date();
    time.textContent = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    const today = now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
    if (date.textContent !== today) date.textContent = today;
    setTimeout(tick, 60000 - Date.now() % 60000 + 50);
  }
  tick();
}

function showBattery({ battery: power }) {
  battery.hidden = !power;
  if (!power) return;
  battery.classList.toggle('charging', power.charging);
  battery.setAttribute('aria-label', `Battery ${power.level}%${power.charging ? ', charging' : ''}`);
  battery.querySelector('i').style.width = power.level + '%';
  battery.querySelector('.battery-text').textContent = power.level + '%';
}

function fit() {
  const scale = Math.min(innerWidth / WIDTH, innerHeight / HEIGHT);
  stage.style.transform = `scale(${scale})`;
  stage.style.left = (innerWidth - WIDTH * scale) / 2 + 'px';
  stage.style.top = (innerHeight - HEIGHT * scale) / 2 + 'px';
}

let townDirty = false, programsDirty = false, scheduled = false, ready = false;
function apply() {
  scheduled = false;
  if (townDirty) {
    const town = bridge.home();
    houses = town.apps.map(app => ({
      ...app, mine: true,
      // The wire starts at the top of the face; extrusion draws from the ground up.
      cells: Array.from({ length: 12 }, (_, row) => Array.from({ length: 12 }, (_, column) => (
        row < 3 && (column === 5 || column === 6) ? 'door' : town.palette[app.cells[(11 - row) * 12 + column]] || null
      ))),
    }));
    street.draw(houses);
    drawHotbar();
  }
  if (programsDirty) programs = bridge.programs();
  if (townDirty || programsDirty) {
    byId = new Map(programs.map(app => [app.id, app]));
    for (const app of houses) byId.set(app.id, { ...byId.get(app.id), ...app });
    search();
    townDirty = programsDirty = false;
  }
  refresh();
  if (!ready) {
    ready = true;
    fit();
    startClock();
    startInput();
    addEventListener('resize', fit);
    stage.hidden = false;
  }
}

function schedule() {
  // The first helper event ends the five-part replay. Keep the stage hidden until all five have arrived.
  if (scheduled || !ready) return;
  scheduled = true;
  queueMicrotask(apply);
}

bridge.addEventListener('home', () => { townDirty = true; schedule(); });
bridge.addEventListener('programs', () => { programsDirty = true; schedule(); });
bridge.addEventListener('running', event => { running = new Set(event.detail); schedule(); });
bridge.addEventListener('status', event => showBattery(event.detail));
bridge.addEventListener('helper', event => {
  const wasOnline = online;
  online = event.detail;
  if (online && !wasOnline) clearError();
  if (ready) schedule();
  else apply();
});

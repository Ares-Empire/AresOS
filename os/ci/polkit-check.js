'use strict';
// Evaluate a built image's real polkit rules for the daily account, with and
// without wheel, the way polkitd runs them: rule files from /etc/polkit-1 and
// /usr/share/polkit-1 sorted by file name (the /etc copy wins for one name),
// rules called in order, the first answer that is not "not handled" wins, and
// an exception anywhere means no rule answered (polkitd logs it and falls back
// to the action's implicit default).
//
// Usage: node polkit-check.js <extracted image root> <review.json> <result.json>
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const [root, reviewPath, outPath] = process.argv.slice(2);
const review = JSON.parse(fs.readFileSync(reviewPath, 'utf8'));
const Result = {
  YES: 'yes', NO: 'no', AUTH_SELF: 'auth_self', AUTH_SELF_KEEP: 'auth_self_keep',
  AUTH_ADMIN: 'auth_admin', AUTH_ADMIN_KEEP: 'auth_admin_keep', NOT_HANDLED: null,
};

function ruleFiles() {
  const byName = new Map();
  for (const dir of ['usr/share/polkit-1/rules.d', 'etc/polkit-1/rules.d']) {
    const full = path.join(root, dir);
    if (!fs.existsSync(full)) continue;
    for (const name of fs.readdirSync(full)) {
      if (name.endsWith('.rules')) byName.set(name, path.join(full, name));
    }
  }
  return [...byName.keys()].sort().map((name) => byName.get(name));
}

function loadRules() {
  const rules = [];
  const adminRules = [];
  const polkit = {
    Result,
    addRule: (f) => rules.push(f),
    addAdminRule: (f) => adminRules.push(f),
    log: () => {},
    spawn: () => { throw new Error('polkit.spawn is not evaluated offline'); },
    _userIsInNetGroup: () => false,
  };
  const context = vm.createContext({ polkit });
  const files = ruleFiles();
  for (const file of files) {
    const before = rules.length;
    vm.runInContext(fs.readFileSync(file, 'utf8'), context, { filename: file });
    for (let n = before; n < rules.length; n++) rules[n].file = file;
  }
  return { rules, adminRules, files };
}

function subject(groups) {
  return {
    pid: 4242, user: 'ares', groups, seat: 'seat0', session: '2', local: true, active: true,
    isInGroup(group) { return this.groups.indexOf(group) >= 0; },
    isInNetGroup() { return false; },
  };
}

function action(id) {
  return { id, lookup: () => undefined };
}

function evaluate(rules, id, who) {
  try {
    for (const rule of rules) {
      const answer = rule(action(id), who);
      if (answer) return { result: answer, file: rule.file };
    }
    return { result: null };
  } catch (error) {
    return { result: null, error: String(error) };
  }
}

function policyActions() {
  const actions = {};
  const dir = path.join(root, 'usr/share/polkit-1/actions');
  for (const name of fs.readdirSync(dir).sort()) {
    if (!name.endsWith('.policy')) continue;
    const text = fs.readFileSync(path.join(dir, name), 'utf8');
    for (const match of text.matchAll(/<action\s+id="([^"]+)"[\s\S]*?<\/action>/g)) {
      const active = /<allow_active>\s*([^<\s]+)\s*<\/allow_active>/.exec(match[0]);
      actions[match[1]] = { file: name, allow_active: active ? active[1] : 'no' };
    }
  }
  return actions;
}

const { rules, adminRules, files } = loadRules();
const actions = policyActions();
const ids = new Set([...Object.keys(actions), ...review.probe_actions]);
const wheel = subject(['ares', 'wheel']);
const plain = subject(['ares']);
const rows = {};
const failures = [];
for (const id of [...ids].sort()) {
  const withWheel = evaluate(rules, id, wheel);
  const withoutWheel = evaluate(rules, id, plain);
  const implicit = actions[id] ? actions[id].allow_active : 'unknown';
  rows[id] = {
    rule: withWheel.result, rule_file: withWheel.file || null, without_wheel: withoutWheel.result,
    implicit_active: implicit, effective: withWheel.result || implicit,
    effective_without_wheel: withoutWheel.result || implicit,
  };
  if (withWheel.error) rows[id].error = withWheel.error;
}

for (const [id, row] of Object.entries(rows)) {
  if (review.os_change_prefixes.some((prefix) => id.startsWith(prefix)) && row.rule !== 'no') {
    failures.push(`${id}: OS/firmware action must be denied to the daily account, got ${row.rule}`);
  }
  // An action that becomes passwordless only because of wheel is an admin
  // right without a password; each one must be reviewed by name.
  if (row.effective === 'yes' && row.effective_without_wheel !== 'yes' &&
      !(id in review.reviewed_passwordless_wheel)) {
    failures.push(`${id}: wheel gets it without a password from ${row.rule_file}; not reviewed`);
  }
  if (row.error) failures.push(`${id}: rule evaluation failed: ${row.error}`);
}
for (const [id, expected] of Object.entries(review.expected)) {
  const row = rows[id];
  if (!row) { failures.push(`${id}: expected action is not declared in the image`); continue; }
  for (const [key, value] of Object.entries(expected)) {
    if (row[key] !== value) failures.push(`${id}: ${key} is ${row[key]}, expected ${value}`);
  }
}
const admins = [];
for (const rule of adminRules) {
  const answer = rule(action('org.freedesktop.policykit.exec'), wheel);
  if (answer) { admins.push(...answer); break; }
}
if (admins.indexOf('unix-group:wheel') < 0) {
  failures.push(`admin identities ${JSON.stringify(admins)} do not include unix-group:wheel`);
}
const wheelDelta = Object.fromEntries(Object.entries(rows).filter(
  ([, r]) => r.effective !== r.effective_without_wheel));
const result = {
  status: failures.length ? 'failed' : 'passed', failures, rule_files: files.map((f) => path.relative(root, f)),
  admin_identities: admins, action_count: Object.keys(rows).length, wheel_delta: wheelDelta,
  denied: Object.keys(rows).filter((id) => rows[id].rule === 'no'), actions: rows,
};
fs.writeFileSync(outPath, JSON.stringify(result, null, 2) + '\n');
console.log(`polkit: ${files.length} rule files, ${result.action_count} actions, ` +
            `${Object.keys(wheelDelta).length} change with wheel, ${result.denied.length} denied to ares`);
for (const [id, row] of Object.entries(wheelDelta)) {
  console.log(`  wheel changes ${id}: ${row.effective_without_wheel} -> ${row.effective}`);
}
for (const failure of failures) console.log('FAIL ' + failure);
if (failures.length) process.exit(1);
console.log('POLKIT_CHECK_PASSED');

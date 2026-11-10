'use strict';
// Evaluate a built image's real polkit rules for the daily account the way
// polkitd runs them: rule files from /etc/polkit-1 and /usr/share/polkit-1
// sorted by file name (the /etc copy wins for one name), rules called in
// order, the first answer that is not "not handled" wins, and an exception
// anywhere means no rule answered (polkitd logs it and falls back to the
// action's implicit default). Every action is evaluated for three kinds of
// session (remote, local inactive, local active), with and without wheel.
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
// polkit's strictness order; a cached answer ranks like its uncached form.
const RANK = { yes: 0, auth_self: 1, auth_self_keep: 1, auth_admin: 2, auth_admin_keep: 2, no: 3 };
const CONTEXTS = { remote: [false, false], inactive: [true, false], active: [true, true] };
const DEFAULT_INDEX = { remote: 0, inactive: 1, active: 2 };

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
  return { rules, adminRules, files, context };
}

function subject(groups, local, active) {
  return {
    pid: 4242, user: 'ares', groups, seat: local ? 'seat0' : '', session: '2', local, active,
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
      const get = (tag) => {
        const found = new RegExp(`<${tag}>\\s*([^<\\s]+)\\s*</${tag}>`).exec(match[0]);
        return found ? found[1] : 'no';
      };
      actions[match[1]] = { file: name, defaults: [get('allow_any'), get('allow_inactive'), get('allow_active')] };
    }
  }
  return actions;
}

const uncached = (value) => value.replace(/_keep$/, '');
const { rules, adminRules, files, context } = loadRules();
const actions = policyActions();
const ids = new Set([...Object.keys(actions), ...review.probe_actions]);
const rows = {};
const failures = [];
for (const id of [...ids].sort()) {
  const defaults = actions[id] ? actions[id].defaults : ['no', 'no', 'no'];
  const contexts = {};
  for (const [kind, [local, active]] of Object.entries(CONTEXTS)) {
    const implicit = defaults[DEFAULT_INDEX[kind]];
    for (const [membership, groups] of [['wheel', ['ares', 'wheel']], ['plain', ['ares']]]) {
      const answer = evaluate(rules, id, subject(groups, local, active));
      if (answer.error) failures.push(`${id}: rule evaluation failed: ${answer.error}`);
      contexts[`${kind}/${membership}`] = { rule: answer.result, file: answer.file || null,
                                            effective: answer.result || implicit, implicit };
    }
  }
  const active = contexts['active/wheel'];
  rows[id] = {
    rule: active.rule, rule_file: active.file, without_wheel: contexts['active/plain'].rule,
    implicit_active: defaults[2], effective: active.effective,
    effective_without_wheel: contexts['active/plain'].effective, defaults, contexts,
  };
}

const bootOrFirmware = new RegExp(review.boot_or_firmware_pattern, 'i');
const listedPasswordless = new Set(Object.keys(review.passwordless));
for (const [id, row] of Object.entries(rows)) {
  // These must be denied in every kind of session, with or without wheel:
  // inherited defaults (allow_active=yes) never show up as a wheel difference.
  const tunedChange = id.startsWith('com.redhat.tuned.') && !review.tuned_read_only.includes(id);
  const mustDeny = review.os_change_prefixes.some((prefix) => id.startsWith(prefix)) ||
    review.denied_actions.includes(id) || bootOrFirmware.test(id) || tunedChange;
  for (const [where, c] of Object.entries(row.contexts)) {
    if (mustDeny && c.effective !== 'no') {
      failures.push(`${id} (${where}): OS, boot, firmware or TuneD change must be denied to ares, got ${c.effective}`);
    }
    // No authorization is ever cached for ares (review 2).
    if (c.effective.endsWith('_keep')) failures.push(`${id} (${where}): cached authorization ${c.effective}`);
    // Rules never give ares more than polkit's own uncached default.
    if (RANK[c.effective] < RANK[uncached(c.implicit)]) {
      failures.push(`${id} (${where}): ares gets ${c.effective}, weaker than the default ${uncached(c.implicit)} ` +
                    `(${c.file})`);
    }
  }
  // Every action ares may do without a password is reviewed by name.
  const passwordless = row.effective === 'yes' || row.effective_without_wheel === 'yes';
  if (passwordless && !listedPasswordless.has(id)) {
    failures.push(`${id}: passwordless for ares (${row.implicit_active} by default) but not reviewed in passwordless`);
  }
  if (!passwordless && listedPasswordless.has(id)) {
    failures.push(`${id}: reviewed as passwordless but now ${row.effective}; remove the stale entry`);
  }
}
for (const id of review.denied_actions) {
  if (!(id in actions)) failures.push(`${id}: denied action is not declared in the image`);
}
// The rule's per-session defaults for upstream wheel grants must equal the
// image's own uncached defaults.
for (const [id, mapped] of Object.entries(context.aresosWheelGrantDefaults || {})) {
  if (id in actions) {
    const own = actions[id].defaults.map(uncached);
    if (JSON.stringify([...mapped]) !== JSON.stringify(own)) {
      failures.push(`${id}: rule defaults ${JSON.stringify([...mapped])} differ from the image's ${JSON.stringify(own)}`);
    }
  }
}
if (!context.aresosWheelGrantDefaults) failures.push('the AresOS rule defines no aresosWheelGrantDefaults');
for (const [id, expected] of Object.entries(review.expected)) {
  const row = rows[id];
  if (!row) { failures.push(`${id}: expected action is not declared in the image`); continue; }
  for (const [key, value] of Object.entries(expected)) {
    if (row[key] !== value) failures.push(`${id}: ${key} is ${row[key]}, expected ${value}`);
  }
}
const cachedDefaults = Object.entries(actions).filter(([, a]) => a.defaults.some((d) => d.endsWith('_keep')))
  .map(([id]) => id);
const admins = [];
for (const rule of adminRules) {
  const answer = rule(action('org.freedesktop.policykit.exec'), subject(['ares', 'wheel'], true, true));
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
  denied: Object.keys(rows).filter((id) => rows[id].rule === 'no'),
  passwordless: Object.keys(rows).filter((id) => rows[id].effective === 'yes'),
  cached_defaults_in_image: cachedDefaults, actions: rows,
};
fs.writeFileSync(outPath, JSON.stringify(result, null, 2) + '\n');
console.log(`polkit: ${files.length} rule files, ${result.action_count} actions, ` +
            `${Object.keys(wheelDelta).length} change with wheel, ${result.denied.length} denied to ares, ` +
            `${result.passwordless.length} reviewed passwordless, ${cachedDefaults.length} cached defaults in the image`);
for (const [id, row] of Object.entries(wheelDelta)) {
  console.log(`  wheel changes ${id}: ${row.effective_without_wheel} -> ${row.effective}`);
}
for (const failure of failures) console.log('FAIL ' + failure);
if (failures.length) process.exit(1);
console.log('POLKIT_CHECK_PASSED');

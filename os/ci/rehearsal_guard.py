"""Fail closed on a package allowance and same-commit probe authorization."""
import datetime
from decimal import Decimal
import hashlib
import io
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import time
import zipfile

REPOSITORY = 'Ares-Empire/AresOS'
PACKAGES = json.loads(pathlib.Path(__file__).with_name('rehearsal-packages.json').read_text())
PACKAGE = '11c'
SETTINGS = PACKAGES[PACKAGE]
BRANCH = SETTINGS['branch']
START = SETTINGS['start']
MINUTE_CAP = SETTINGS['minute_cap']
FULL_CAP = SETTINGS['full_cap']
PART_B_CAP = SETTINGS['part_b_cap']
RETRY_WAITS = (10, 20, 40, 60)
READ_RETRIES = []
RUN_HISTORY_PATH = f'actions/runs?branch={BRANCH}&per_page=100'
HISTORY_PAGE_LIMIT = 20
PUBLISH_STEP = 'Publish the tested private release and sign with GitHub OIDC'
NATIVE_STEP = 'Qualify tools, regressions, rewritten release identity and private access'
# Package 22c: the job and step of a checks-only dispatch that explore the full ways-back model.
MODEL_JOB = 'Full ways-back model when its sources changed (no image build or VM)'
MODEL_STEP = 'Run the full ways-back model'
ACCOUNTING_POLICY = '14zz-job-interval-ordered-span-full-bound-v1'
OWNER_QUALIFICATION_BOUND = 240
# Packages whose ledger counts every dispatch by its run title.
TITLED_PACKAGES = ('13', '14', '16', '27', '22c')


def configure(package):
    global PACKAGE, SETTINGS, BRANCH, START, MINUTE_CAP, FULL_CAP, PART_B_CAP, RUN_HISTORY_PATH
    assert package in PACKAGES, 'STOP: unknown package ledger'
    PACKAGE, SETTINGS = package, PACKAGES[package]
    BRANCH, START = SETTINGS['branch'], SETTINGS['start']
    MINUTE_CAP, FULL_CAP, PART_B_CAP = (SETTINGS[k] for k in ('minute_cap', 'full_cap', 'part_b_cap'))
    RUN_HISTORY_PATH = f'actions/runs?branch={BRANCH}&per_page=100'


def owner_reservations(now=None):
    """Local privacy costs no Actions minutes; VM bounds stay reserved."""
    assert PACKAGE=='14', 'STOP: owner reservation plan is package14 only'
    setting=SETTINGS.get('closing_privacy_reservation')
    push=SETTINGS.get('push_privacy_reservation')
    local_decision='briefs/14zw-local-privacy.md'
    if (isinstance(setting,dict) and setting.get('decision')==local_decision or
            isinstance(push,dict) and push.get('decision')==local_decision):
        for name,value in (('push',push),('closing',setting)):
            assert isinstance(value,dict) and set(value)=={'minutes','decision'}, 'STOP: missing or malformed local '+name+' privacy decision'
            assert type(value['minutes']) is int and value['minutes']==0 and value['decision']==local_decision, 'STOP: unreviewed local '+name+' privacy reservation'
        return dict(push=0,probe=72,qualification=OWNER_QUALIFICATION_BOUND,closing_privacy=0,
            pre_push=72+OWNER_QUALIFICATION_BOUND,before_probe=72+OWNER_QUALIFICATION_BOUND,
            before_qualification=OWNER_QUALIFICATION_BOUND,
            qualification_bound_decision='briefs/14zzc-review-fixes.md',
            decision=local_decision,exception_month=None,merge_requires_privacy=True,
            privacy_proof='aresync-local-pre-push',github_privacy_runs_required=False)
    assert push is None, 'STOP: unreviewed push privacy reservation'
    assert isinstance(setting,dict) and set(setting)=={'minutes','normal_minutes','exception_month','decision'}, 'STOP: missing closing reservation decision'
    closing=setting['minutes']
    assert type(closing) is int and closing in (0,12) and setting['normal_minutes']==12, 'STOP: invalid closing reservation'
    assert setting['exception_month']=='2026-10' and setting['decision']=='briefs/14r-no-closing-reservation.md', 'STOP: unreviewed closing reservation exception'
    now=now or datetime.datetime.now(datetime.timezone.utc)
    assert closing==12 or now.strftime('%Y-%m')==setting['exception_month'], 'STOP: zero closing reservation is October2026 only'
    return dict(push=6,probe=72,qualification=160,closing_privacy=closing,
        pre_push=6+72+160+closing,before_probe=72+160+closing,before_qualification=160+closing,
        decision=setting['decision'],exception_month=setting['exception_month'],merge_requires_privacy=True)


def failure_status(stderr):
    # gh api appends (HTTP NNN) to JSON errors, or prints "gh: HTTP NNN"
    # for other HTTP bodies. Unknown/parse/auth errors must not become retries.
    message = stderr.decode('utf-8', errors='replace')
    codes = re.findall(r'^gh: [^\r\n]*\(HTTP ([1-5][0-9]{2})\)|^gh: HTTP ([1-5][0-9]{2})(?:\s|$)', message, re.M)
    if codes:
        return int(next(part for part in codes[-1] if part))
    # Go's http.Client returns a URL error for transport failures. Match only
    # recognizable connection causes; certificate/CLI/unknown failures stop.
    connection = re.search(r'^Get "https://[^"\r\n]+": '
        r'(?:(?:proxyconnect tcp: )?dial (?:tcp|udp)|read tcp|write tcp|EOF$|unexpected EOF$|'
        r'context deadline exceeded|net/http: TLS handshake timeout|'
        r'net/http: request canceled while waiting for connection|http2: client connection lost)', message, re.M)
    return 'connection' if connection else None


def read_only(path):
    command = ['gh', 'api', '--method', 'GET', path]
    for attempt in range(1, len(RETRY_WAITS) + 2):
        try:
            return subprocess.check_output(command, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as error:
            status = failure_status(error.stderr or b'')
            retryable = error.returncode != 4 and (status == 'connection' or
                         isinstance(status, int) and 500 <= status <= 599)
            if not retryable or attempt > len(RETRY_WAITS):
                print('GUARD_READ_FAILED ' + json.dumps(dict(path=path, status=status,
                      attempt=attempt, returncode=error.returncode)), file=sys.stderr, flush=True)
                raise
            record = dict(path=path, status=status, attempt=attempt,
                          next_attempt=attempt + 1, wait_seconds=RETRY_WAITS[attempt - 1])
            READ_RETRIES.append(record)
            print('GUARD_READ_RETRY ' + json.dumps(record), file=sys.stderr, flush=True)
            time.sleep(record['wait_seconds'])


def api(path):
    if path == RUN_HISTORY_PATH:
        return run_history()
    return json.loads(read_only(f'repos/{REPOSITORY}/{path}'))


def run_history():
    """Require one complete, consistent listing; never stitch shifted snapshots."""
    runs, pages, seen = [], [], set()
    total = None
    for page in range(1, HISTORY_PAGE_LIMIT + 1):
        path = f'{RUN_HISTORY_PATH}&page={page}'
        response = json.loads(read_only(f'repos/{REPOSITORY}/{path}'))
        assert isinstance(response, dict), 'STOP: malformed run history response'
        count, batch = response.get('total_count'), response.get('workflow_runs')
        assert type(count) is int and count >= 0 and isinstance(batch, list), 'STOP: missing or malformed history total_count/runs'
        print('GUARD_HISTORY_PAGE ' + json.dumps(dict(page=page, path=path,
              total_count=count, returned=len(batch))), file=sys.stderr, flush=True)
        if total is None:
            total = count
        assert count == total, 'STOP: inconsistent history total_count; pages shifted'
        assert len(batch) <= 100, 'STOP: oversized history page'
        assert batch or len(runs) == total, 'STOP: empty history page before the end'
        assert len(batch) == min(100, total - len(runs)), 'STOP: missing or excess history ids/page length'
        ids = [run.get('id') if isinstance(run, dict) else None for run in batch]
        assert all(type(run_id) is int and run_id > 0 for run_id in ids), 'STOP: missing or malformed history run id'
        assert len(set(ids)) == len(ids) and not seen.intersection(ids), 'STOP: duplicate history run id; pages shifted'
        seen.update(ids)
        runs.extend(batch)
        pages.append(dict(page=page, returned=len(batch), total_count=count,
                          ids_sha256=hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()))
        if len(runs) == total:
            assert len(seen) == total, 'STOP: unique history ids do not match total_count'
            proof = dict(complete=True, pages_read=len(pages), ids_count=len(seen), total_count=total,
                         page_limit=HISTORY_PAGE_LIMIT, snapshot_reads=1, pages=pages,
                         run_ids=[run['id'] for run in runs])
            print('GUARD_HISTORY_COMPLETE ' + json.dumps({k: proof[k] for k in
                  ('pages_read', 'ids_count', 'total_count', 'snapshot_reads')}), file=sys.stderr, flush=True)
            return dict(workflow_runs=runs, history=proof)
    raise AssertionError('STOP: history page limit reached before completeness')


def job_accounting(job, full_bound=None):
    """Use an enclosing interval, an ordered supported span, or the full bound."""
    evidence = dict(job=job.get('id'), name=job.get('name'),
        response_sha256=hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest())
    if job.get('conclusion') == 'skipped':
        return dict(evidence, minutes=0, rule='skipped')

    def stamp(value):
        if not isinstance(value, str): return None
        try: parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError: return None
        return parsed.astimezone(datetime.timezone.utc) if parsed.tzinfo is not None else None

    def bound(reason):
        assert type(full_bound) is int and full_bound > 0, 'STOP: no approved full bound for unaccountable job'
        return dict(evidence, minutes=full_bound, rule='full-bound', reason=reason, full_bound=full_bound)

    steps = job.get('steps')
    if not isinstance(steps, list) or not steps:
        return bound('missing steps')
    pairs = [(stamp(s.get('started_at')), stamp(s.get('completed_at')))
             if isinstance(s, dict) else (None, None) for s in steps]
    if any(a is None or b is None or a > b for a, b in pairs):
        return bound('missing or unordered step interval')
    if any(pairs[i][0] < pairs[i-1][1] for i in range(1, len(pairs))):
        return bound('unordered steps')
    start, end = stamp(job.get('started_at')), stamp(job.get('completed_at'))
    normal = start is not None and end is not None and start <= end and all(
        start <= a <= b <= end for a, b in pairs)
    if normal:
        first, last, rule = start, end, 'job-interval'
    else:
        last = max(value for value in (end, pairs[-1][1]) if value is not None)
        starts = [value for value in (start, pairs[0][0]) if value is not None and value <= last]
        if not starts: return bound('no ordered span')
        first, rule = min(starts), 'ordered-span'
    seconds = (last-first).total_seconds()
    assert seconds >= 0, 'STOP: inconsistent selected accounting interval'
    minutes = math.ceil(seconds / 60)
    # A valid zero-second job still consumes GitHub's minimum billed minute.
    return dict(evidence, minutes=minutes if minutes else 1, rule=rule,
        selected_start=first.isoformat(), selected_completion=last.isoformat(),
        seconds=seconds, step_count=len(steps), full_bound=full_bound)


def job_minutes(job, full_bound=None):
    return job_accounting(job, full_bound)['minutes']


def ledger_organization_check(ledger, organization, previous):
    """Compare against a saved checkpoint already recomputed under this policy."""
    assert isinstance(previous, dict) and set(previous) == {'authorization','dispatched_run'}, 'STOP: missing previous-dispatch checkpoint'
    old, dispatched = previous['authorization'], previous['dispatched_run']
    assert isinstance(old, dict) and old.get('allowance') == ledger['allowance'] == '14' and old.get('start') == ledger['start'], 'STOP: wrong previous package checkpoint'
    assert old.get('accounting_policy') == ledger.get('accounting_policy') == ACCOUNTING_POLICY, 'STOP: previous checkpoint must be recomputed under the current accounting policy'
    for value in (old, ledger):
        proof = value.get('history')
        assert isinstance(proof,dict) and proof.get('complete') is True and proof.get('ids_count') == proof.get('total_count'), 'STOP: incomplete comparison history'
    assert type(dispatched) is int and dispatched > 0, 'STOP: missing previous dispatch id'
    current = {row['run']: row for row in ledger['runs']}
    before = {row['run']: row for row in old['runs']}
    assert len(current)==len(ledger['runs']) and len(before)==len(old['runs']), 'STOP: duplicate comparison run'
    assert before.keys() <= current.keys() and dispatched in current and dispatched not in before, 'STOP: previous dispatch run set is inconsistent'
    deltas = {kind:ledger['dispatch_counts'][kind]-old['dispatch_counts'][kind] for kind in ledger['dispatch_counts']}
    assert all(type(n) is int and n >= 0 for n in deltas.values()) and sum(deltas.values())==1, 'STOP: checkpoint is not immediately before the previous dispatch'
    kind, = [kind for kind,n in deltas.items() if n==1]
    assert current[dispatched]['title'] == SETTINGS['titles'][kind], 'STOP: previous dispatch kind mismatch'
    prior_org = old.get('organization_budget')
    assert isinstance(prior_org,dict) and prior_org.get('source') == organization['source'], 'STOP: billing comparison period or organization differs'
    for value in (prior_org,organization):
        assert type(value.get('used_minutes')) is int and value['used_minutes']>=0, 'STOP: invalid comparison usage'
    assert datetime.datetime.fromisoformat(prior_org['checked_at']) <= datetime.datetime.fromisoformat(organization['checked_at']), 'STOP: reversed billing observations'
    # Do not reprice the baseline using current responses: that would erase a
    # later charge reduction and defeat the organization's undercount check.
    saved_before = sum(row['minutes'] for row in before.values())
    assert type(old.get('consumed_minutes')) is int and saved_before == old['consumed_minutes'], 'STOP: previous checkpoint total differs from its run charges'
    assert sum(row['minutes'] for row in current.values()) == ledger['consumed_minutes'], 'STOP: current ledger total differs from its run charges'
    increase = ledger['consumed_minutes'] - saved_before
    org_increase = organization['used_minutes'] - prior_org['used_minutes']
    assert increase >= 0 and org_increase >= 0, 'STOP: comparison usage decreased'
    assert org_increase-increase <= 5, 'STOP: package ledger increase is more than 5 minutes below organization increase'
    return dict(status='passed', previous_dispatch=dispatched,
        previous_observed_at=prior_org['checked_at'], current_observed_at=organization['checked_at'],
        previous_recorded_minutes=old.get('legacy_recorded_minutes',old['consumed_minutes']), recomputed_previous_minutes=saved_before,
        current_minutes=ledger['consumed_minutes'], package_increase=increase,
        organization_increase=org_increase, undercount_tolerance_minutes=5,
        previous_run_count=len(before), previous_run_ids_sha256=hashlib.sha256(json.dumps(sorted(before)).encode()).hexdigest())


def organization_budget(reserve, now=None):
    """Scheduling-only GET with the owner's existing login; no billing token in CI."""
    assert type(reserve) is int and reserve >= 0, 'STOP: invalid organization reservation'
    settings = SETTINGS['organization_budget']
    now = now or datetime.datetime.now(datetime.timezone.utc)
    paid_october = PACKAGE == '14' and (now.year, now.month) == (2026, 10)
    later_month = (now.year, now.month) > (2026, 10)
    if PACKAGE == '14':
        assert paid_october or later_month, 'STOP: paid overflow approval is October2026 only'
    path = ('organizations/' + settings['organization'] + '/settings/billing/usage/summary'
            + f'?year={now.year}&month={now.month}')
    raw = read_only(path)
    response = json.loads(raw)
    assert isinstance(response, dict) and set(response) == {'timePeriod', 'organization', 'usageItems'}, 'STOP: malformed billing summary'
    assert response['organization'] == settings['organization'], 'STOP: wrong billing organization'
    period = response['timePeriod']
    assert isinstance(period, dict) and set(period) == {'year', 'month'} and all(
        type(period[key]) is int for key in ('year', 'month')), 'STOP: malformed billing period'
    assert period == dict(year=now.year, month=now.month), 'STOP: stale billing period'
    rows = response['usageItems']
    assert isinstance(rows, list) and (rows or later_month), 'STOP: missing billing usage'
    used, seen, actions = 0, set(), []
    for row in rows:
        assert isinstance(row, dict) and isinstance(row.get('product'), str), 'STOP: malformed billing row'
        if row['product'] != 'Actions':
            continue
        sku, unit = row.get('sku'), row.get('unitType')
        assert isinstance(sku, str) and sku not in seen, 'STOP: duplicate or missing billing SKU'
        seen.add(sku)
        values = {}
        for field in ('grossQuantity', 'discountQuantity', 'netQuantity', 'grossAmount', 'discountAmount', 'netAmount'):
            value = row.get(field)
            assert type(value) in (int, float) and math.isfinite(value) and value >= 0, 'STOP: invalid billing quantity/amount'
            values[field] = value
        if PACKAGE != '14':
            assert values['netQuantity'] == values['netAmount'] == 0, 'STOP: Actions usage outside the free allowance'
        # The current org uses standard Linux runners only. Unknown SKUs fail
        # closed instead of guessing free-quota eligibility or multipliers.
        assert (sku, unit) in (('actions_linux', 'minutes'), ('actions_storage', 'gigabyte-hours')), 'STOP: unsupported Actions billing SKU/unit'
        if unit == 'minutes':
            if not paid_october:
                assert values['netQuantity'] == values['netAmount'] == 0, 'STOP: Actions minute usage outside the free allowance'
            # Credits/refresh timing can make discountQuantity slightly higher.
            used += math.ceil(max(values['grossQuantity'], values['discountQuantity']))
            if paid_october:
                price = row.get('pricePerUnit')
                assert type(price) in (int, float) and math.isfinite(price) and price > 0, 'STOP: missing or invalid runner pricePerUnit'
                values['pricePerUnit'] = price
        actions.append(dict(sku=sku, unit=unit, **values))
    assert 'actions_linux' in seen or later_month, 'STOP: missing Actions minute usage'
    included_left = max(0, settings['included_minutes'] - used)
    paid = None
    if paid_october:
        budget_path = 'organizations/' + settings['organization'] + '/settings/billing/budgets'
        budget_raw = read_only(budget_path)
        budgets = json.loads(budget_raw)
        assert isinstance(budgets, dict) and set(budgets) == {'budgets', 'has_next_page', 'total_count'}, 'STOP: malformed budgets response'
        entries = budgets['budgets']
        assert isinstance(entries, list) and budgets['has_next_page'] is False and type(budgets['total_count']) is int and budgets['total_count'] == len(entries), 'STOP: incomplete budgets response'
        assert all(isinstance(row, dict) and isinstance(row.get('budget_product_sku'), str) for row in entries), 'STOP: malformed budget entry'
        matches = [row for row in entries if row['budget_product_sku'] == 'actions']
        assert len(matches) == 1, 'STOP: missing or duplicate Actions budget'
        entry = matches[0]
        assert entry.get('budget_type') == 'ProductPricing' and entry.get('budget_scope') == 'organization' and entry.get('budget_entity_name') == settings['organization'], 'STOP: wrong Actions budget scope'
        amount = entry.get('budget_amount')
        assert type(amount) in (int, float) and amount == 10, 'STOP: Actions budget amount differs from approved $10'
        assert entry.get('prevent_further_usage') is True, 'STOP: Actions budget must prevent further usage'
        spent = sum((Decimal(str(row['netAmount'])) for row in actions), Decimal(0))
        assert spent <= Decimal(str(amount)), 'STOP: reported Actions spend exceeds approved budget'
        per_minute = Decimal(str(price))
        # Decimal division avoids an upward rounding at a paid-minute boundary.
        paid_minutes = int((Decimal(str(amount)) - spent) // per_minute)
        paid = dict(source=budget_path, response_sha256=hashlib.sha256(budget_raw).hexdigest(),
                    budget_product_sku='actions', budget_amount=amount, prevent_further_usage=True,
                    budget_scope=entry['budget_scope'], budget_entity_name=entry['budget_entity_name'],
                    price_source=path, runner_sku='actions_linux', pricePerUnit=price,
                    reported_net_amount=float(spent), available_budget=float(Decimal(str(amount))-spent),
                    paid_minutes=paid_minutes, decision='briefs/14zl-ten-dollar-round.md', exception_month='2026-10')
    remaining = (included_left + paid['paid_minutes']) if paid else settings['included_minutes'] - used
    spare = remaining - reserve
    assert spare >= settings['other_repos_reserve'], f'STOP: organization has {remaining} available minutes; {reserve} reserved must leave {settings["other_repos_reserve"]}'
    return dict(status='passed', source=path, checked_at=now.isoformat(),
                response_sha256=hashlib.sha256(raw).hexdigest(), usage=actions,
                used_minutes=used, included_minutes=settings['included_minutes'],
                included_minutes_left=included_left, paid_overflow=paid,
                billing_mode='historical-october-paid-overflow' if paid_october else 'free-minutes-only',
                paid_budget_read=paid_october,
                remaining_minutes=remaining, reserved_minutes=reserve, after_reservation=spare,
                other_repos_reserve=settings['other_repos_reserve'], credential='existing local gh login; GET only')


def budget(reserve, current=None):
    # Keep every historical push/PR job in the ledger after privacy moves local.
    listing = api(RUN_HISTORY_PATH)
    runs = listing['workflow_runs']
    assert type(reserve) is int and reserve >= 0, 'STOP: invalid reservation'
    start = START
    counts = {key: 0 for key in SETTINGS.get('dispatch_caps', {})}
    if START == 'first-dispatch':
        dispatched = [r for r in runs if r['event'] == 'workflow_dispatch']
        start = min((r['created_at'] for r in dispatched), default=None)
        for run in runs:
            if str(run['id']) != str(current):
                assert run['status'] == 'completed', 'Another branch workflow is active; cannot reserve its cost'
    records = []
    publishes = []
    full = 0
    part_b = 0
    for run in runs:
        if start is None or run['created_at'] < start:
            continue
        if PACKAGE in TITLED_PACKAGES and run['event'] == 'workflow_dispatch':
            kind, = [kind for kind, title in SETTINGS['titles'].items() if title == run['display_title']]
            assert run.get('run_attempt') == 1, 'STOP: a rerun is an additional dispatch, not a free retry'
            counts[kind] += 1
        if run['display_title'] == 'Two-disk rehearsal (full)':
            full += 1
        if run['display_title'] == 'Two-disk rehearsal (part-b)':
            part_b += 1
        if str(run['id']) == str(current):
            continue
        assert run['status'] == 'completed', 'Another branch workflow is active; cannot reserve its cost'
        response = api(f'actions/runs/{run["id"]}/jobs?per_page=100')
        jobs = response['jobs']
        if PACKAGE in TITLED_PACKAGES:
            assert response.get('total_count') == len(jobs) <= 100, 'STOP: incomplete job listing'
            for job in jobs:
                steps = job.get('steps', [])
                assert isinstance(steps, list), 'STOP: malformed job steps'
                if job.get('name') == 'image' and job['conclusion'] != 'skipped':
                    assert len([s for s in steps if s['name'] == PUBLISH_STEP]) == 1, 'STOP: image publish boundary missing or duplicated'
                for step in steps:
                    if step['name'] == PUBLISH_STEP and step['conclusion'] != 'skipped':
                        assert step['status'] == 'completed', 'STOP: publish outcome is not settled'
                        publishes.append(dict(run=run['id'], conclusion=step['conclusion']))
        bound = None
        if PACKAGE in ('14','16') and run['event']=='workflow_dispatch':
            bound = 72 if run['display_title']==SETTINGS['titles']['probe'] else OWNER_QUALIFICATION_BOUND
        if PACKAGE in ('27', '22c') and run['event'] == 'workflow_dispatch':
            # Each kind's own job timeout bounds a job GitHub cannot account.
            bound = SETTINGS['job_bounds'][kind]
        accounts = [job_accounting(job, bound) for job in jobs]
        records.append(dict(run=run['id'], title=run['display_title'], sha=run['head_sha'],
                            conclusion=run['conclusion'], minutes=sum(row['minutes'] for row in accounts),
                            jobs=accounts))
    consumed = sum(record['minutes'] for record in records)
    assert consumed + reserve <= MINUTE_CAP, f'STOP: {consumed} + {reserve} reserved exceeds {MINUTE_CAP} minutes'
    assert full <= FULL_CAP, 'STOP: full-run allowance exhausted'
    assert part_b <= PART_B_CAP, 'STOP: Part B qualification allowance exhausted'
    for kind, count in counts.items():
        assert count <= SETTINGS['dispatch_caps'][kind], 'STOP: ' + kind + ' dispatch allowance exhausted'
    if 'vm_dispatch_cap' in SETTINGS:
        # Package 22c: one allowance for all its VM modes together (every kind but the checks).
        assert sum(count for kind, count in counts.items() if kind != 'checks') <= SETTINGS['vm_dispatch_cap'], \
            'STOP: VM dispatch allowance exhausted'
    assert len(publishes) <= SETTINGS.get('publish_cap', 0), 'STOP: publish allowance exceeded'
    return dict(allowance=PACKAGE, start=start, cap=MINUTE_CAP, full_cap=FULL_CAP, full_dispatched=full,
                part_b_cap=PART_B_CAP, part_b_dispatched=part_b,
                dispatch_caps=SETTINGS.get('dispatch_caps', {}), dispatch_counts=counts,
                consumed_minutes=consumed, reserved_minutes=reserve, runs=records,
                publish_cap=SETTINGS.get('publish_cap', 0), publish_attempts=publishes,
                history=listing.get('history'),accounting_policy=ACCOUNTING_POLICY)


def require_probe(run, sha):
    assert run['event'] == 'workflow_dispatch'
    assert run['path'] == '.github/workflows/os-image.yml'
    assert run['head_branch'] == BRANCH
    assert run['head_sha'] == sha, 'Full run requires a probe on the exact same harness commit'
    assert run['display_title'] == 'Two-disk rehearsal (probe)'
    assert run['status'] == 'completed' and run['conclusion'] == 'success', 'Probe did not pass'


def probe_native(run, sha, current=False, kind='probe'):
    """Read GitHub's completed native step, never a guest/self-written success flag."""
    assert run['event']=='workflow_dispatch' and run['path']=='.github/workflows/os-image.yml'
    assert run['head_branch']==BRANCH and run['head_sha']==sha and run['run_attempt']==1
    assert run['display_title']==SETTINGS['titles'][kind]
    if not current:
        require_probe(run,sha)
    response=api(f'actions/runs/{run["id"]}/jobs?per_page=100')
    assert response['total_count']==len(response['jobs'])<=100, 'STOP: incomplete native job listing'
    job,=[j for j in response['jobs'] if j['name']=='Pinned live ISO inspection and two-disk rehearsal']
    assert job['head_sha']==sha
    step,=[s for s in job['steps'] if s['name']==NATIVE_STEP]
    assert step['status']=='completed' and step['conclusion']=='success', 'STOP: complete native preflight has not passed'
    return dict(status='passed',sha=sha,run=run['id'],step=NATIVE_STEP,source='GitHub completed probe preflight step')


def own_native(kind):
    """Kinds whose native step is proved in their own run: a probe, package 27's update, every VM mode of package 22c."""
    return kind in ('probe','update') or PACKAGE == '22c' and kind != 'checks'


def native_gate(kind, mode, result, sha, current_run=None):
    if own_native(kind) and mode in ('probe','probe-budget-ci'):
        # Scheduling/budget receipt only. keyboard_vm refuses this pending state.
        return dict(status='pending',sha=sha,required='completed native step before any VM')
    native=[r for r in result['runs'] if r['title']==SETTINGS['titles'].get('checks')
            and r['sha']==sha and r['conclusion']=='success']
    assert len(native)<=1, 'STOP: duplicate native checks on this head'
    if native:
        return dict(status='passed',sha=sha,run=native[0]['run'],source='checks-only dispatch')
    if own_native(kind):
        # Package 27's update rehearsal has no separate probe: its own native
        # step must have completed in this run before any VM starts.
        assert mode=='ci' and current_run is not None, 'STOP: no current probe native preflight'
        return probe_native(current_run,sha,current=True,kind=kind)
    probes=[r for r in result['runs'] if r['title']==SETTINGS['titles']['probe']
            and r['sha']==sha and r['conclusion']=='success']
    assert len(probes)==1, 'STOP: native preflight requires one passing probe on this head'
    return probe_native(api('actions/runs/'+str(probes[0]['run'])),sha)


def model_gate(result, sha):
    """Package 22c's VM dispatches: when the head changed the full model's sources, that model must
    have passed on the same head (review 4, finding 4).

    The rehearsal job's suite explores only the bounded slice; the full model runs in the model job
    of a checks-only dispatch, and only when model_scope.py selects it. So a VM dispatch reads
    GitHub's completed step of that job in a passing checks-only run on this head. When the sources
    did not change (scope `slice`), nothing is required. Uncertain counts as changed (model_scope).
    """
    import model_scope
    scope, reasons = model_scope.decide()
    if scope != 'full':
        return dict(status='not-needed', scope=scope, reasons=reasons)
    checks = [r for r in result['runs'] if r['title'] == SETTINGS['titles']['checks']
              and r['sha'] == sha and r['conclusion'] == 'success']
    for record in checks:
        response = api(f'actions/runs/{record["run"]}/jobs?per_page=100')
        assert response['total_count'] == len(response['jobs']) <= 100, 'STOP: incomplete model job listing'
        for job in response['jobs']:
            if job['name'] != MODEL_JOB or job['head_sha'] != sha:
                continue
            steps = [s for s in job['steps'] if s['name'] == MODEL_STEP]
            if len(steps) == 1 and steps[0]['status'] == 'completed' and steps[0]['conclusion'] == 'success':
                return dict(status='passed', scope='full', sha=sha, run=record['run'], job=MODEL_JOB, step=MODEL_STEP,
                            reasons=reasons, source='GitHub completed full-model step of a checks-only dispatch')
    raise AssertionError('STOP: the full ways-back model has not passed on this head, and its sources changed ('
                         + str(len(reasons)) + ' paths, first ' + reasons[0] + '); dispatch checks_only on this head first')


def main():
    configure(os.environ.get('REHEARSAL_PACKAGE', '11c'))
    mode = sys.argv[1]
    assert mode != 'full' and not (mode == 'ci' and os.environ.get('REHEARSAL_MODE') == 'full'), 'STOP: 11l permits no further full run'
    reserve = int(sys.argv[2])
    ci = mode in ('ci', 'publish-ci', 'probe-budget-ci')
    current = os.environ.get('GITHUB_RUN_ID') if ci else None
    plan=None
    if PACKAGE=='16':
        kind=os.environ.get('REHEARSAL_MODE') if ci else mode
        assert kind=='probe' and mode in ('probe','probe-budget-ci','ci'), 'STOP: package16 permits only the owner-tools probe'
        assert reserve==72, 'STOP: package16 requires the full 72-minute probe reservation'
        for key in ('push_privacy_reservation','closing_privacy_reservation'):
            assert SETTINGS[key]==dict(minutes=0,decision='briefs/14zw-local-privacy.md'), 'STOP: invalid package16 local privacy reservation'
    if PACKAGE=='14' and not ci:
        plan=owner_reservations()
        assert mode in ('probe','owner-tools'), 'STOP: invalid owner dispatch mode'
        assert reserve==plan['before_probe' if mode=='probe' else 'before_qualification'], 'STOP: incomplete owner dispatch reservation'
    if PACKAGE in TITLED_PACKAGES:
        assert os.environ.get('GITHUB_REF_NAME', BRANCH) == BRANCH, 'STOP: wrong package branch'
    result = budget(reserve, current)
    if plan is not None:
        result['reservation_plan']=plan
    if mode=='probe-budget-ci':
        assert (PACKAGE in ('13', '14', '16') and os.environ.get('REHEARSAL_MODE')=='probe'
                or PACKAGE == '27' and os.environ.get('REHEARSAL_MODE')=='update'
                or PACKAGE == '22c' and os.environ.get('REHEARSAL_MODE') in SETTINGS['dispatch_caps']
                and os.environ.get('REHEARSAL_MODE') != 'checks'), 'STOP: native deferral is only for probe budget reservation'
    history = result.get('history')
    assert history and history['complete'] and history['ids_count'] == history['total_count'], 'STOP: no complete run-history proof'
    if PACKAGE in TITLED_PACKAGES:
        kind = os.environ['REHEARSAL_MODE'] if ci else mode
        assert kind in SETTINGS['dispatch_caps'], 'STOP: mode is not authorized for package'
        if ci:
            run = api('actions/runs/' + current)
            assert run['head_branch'] == BRANCH and run['head_sha'] == os.environ['GITHUB_SHA']
            assert run['display_title'] == SETTINGS['titles'][kind] and run['event'] == 'workflow_dispatch'
            assert result['dispatch_counts'][kind] >= 1, 'STOP: current dispatch is missing from complete history'
        else:
            assert result['dispatch_counts'][kind] < SETTINGS['dispatch_caps'][kind], 'STOP: no dispatch remains'
        if kind in ('release-13', 'release-27'):
            assert not result['publish_attempts'], 'STOP: a prior attempt reached publishing; no further image/publish attempt'
        if mode == 'publish-ci':
            assert kind in ('release-13', 'release-27') and os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
            assert os.environ.get('GITHUB_REPOSITORY') == REPOSITORY
        if kind in ('probe', 'keyboard', 'owner-tools', 'update') or own_native(kind):
            sha=os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
            result['native']=native_gate(kind,mode,result,sha,run if ci else None)
            if PACKAGE == '22c' and own_native(kind):
                # Checked at the budget step already, so a dispatch without it stops before its minutes.
                result['model']=model_gate(result,sha)
    if mode == 'part-b':
        assert result['part_b_dispatched'] < PART_B_CAP, 'STOP: no Part B qualification dispatch remains'
    if (mode == 'ci' and os.environ.get('REHEARSAL_MODE') in ('part-b', 'keyboard', 'owner-tools') or
            PACKAGE == '14' and not ci and mode == 'owner-tools'):
        expected_sha = os.environ.get('GITHUB_SHA') or subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        if PACKAGE == '11c':
            assert result['part_b_dispatched'] == PART_B_CAP, 'STOP: Part B current dispatch is absent or duplicated'
        probe_id = os.environ.get('PROBE_RUN', '')
        assert probe_id.isdigit(), 'Full run requires an explicit passing probe ID'
        require_probe(api('actions/runs/' + probe_id), expected_sha)
        artifacts = api(f'actions/runs/{probe_id}/artifacts')['artifacts']
        artifact, = [item for item in artifacts if item['name'] == 'two-disk-evidence' and not item['expired']]
        raw = read_only(f'repos/{REPOSITORY}/actions/artifacts/{artifact["id"]}/zip')
        assert artifact['digest'] == 'sha256:' + hashlib.sha256(raw).hexdigest(), 'Probe artifact digest mismatch'
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            proof = json.loads(archive.read('two-disk/probe-result.json'))
        assert proof['status'] == 'passed' and proof['installed'] is False
        assert proof['commit'] == expected_sha
        if PACKAGE == '14':
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                capabilities = json.loads(archive.read('14-host-capabilities.json'))
            from owner_capabilities import CHECKS
            assert capabilities['status'] == 'passed' and capabilities['sha'] == expected_sha
            assert all(capabilities['checks'].get(name) is True for name in CHECKS), 'STOP: probe host capabilities incomplete'
            assert proof['order'] == 'protected-second' and proof['both_orders'] is False
            assert proof['offline_link'] and proof['tools_hotplug'] and proof['tools_absent_before_reboot']
            assert proof['bundle_equality'] and proof['host_walk'] and proof['review_validated']
            assert proof['bootnext_checked'] and proof['bootloader_source_verified']
            assert proof['native_job_auth'] and proof['guest_credential_share'] is False
        else:
            assert proof['both_orders'] and proof['review_validated']
        assert proof['detached_windows'] and proof['target_reset']
        assert proof['owner_auth_read_only'] and proof['signature_verified']
        assert proof['firmware_rule'] == '11f-linux-position'
        assert proof['stock_recipe_probe'] and proof['failure_counter_probe']
        assert proof['read_only_keyboard_proof'] and proof['installed_keyboard_reader_probe']
        assert proof['part_b_tools_probe'] and proof['stock_idle_source_verified']
        if PACKAGE == '13':
            assert proof['package13_keyboard_tools'] and proof['live_desktop_keyboard']=='laptop-followability-only'
        if PACKAGE in ('13', '14', '16'):
            from registry_auth import REFERENCE, DIGEST
        else:
            from rehearsal_auth import REFERENCE, DIGEST
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            manifest = json.loads(archive.read('private-registry-preflight.json'))
            pull = json.loads(archive.read('owner-release-pull.json'))
            cleanup = json.loads(archive.read('owner-auth-cleanup.json'))
        assert manifest['status'] == 'passed' and manifest['reference'] == REFERENCE and manifest['registry_digest'] == DIGEST
        assert manifest['secret'] == ('GITHUB_TOKEN' if PACKAGE in ('13', '14', '16') else 'GHCR_READ_TOKEN') and manifest['owner_token_api_calls'] == 0
        assert pull['status'] == 'passed' and pull['reference'] == REFERENCE and pull['preserved_digest']
        assert cleanup['status'] == 'passed' and cleanup['removed'] and cleanup['outside_workspace']
        result['probe_run'] = probe_id
        result['probe'] = proof
    if PACKAGE in ('13', '14', '16') and not ci:
        result['organization_budget'] = organization_budget(reserve)
        if PACKAGE == '14':
            previous = os.environ.get('REHEARSAL_PREVIOUS_DISPATCH')
            assert previous, 'STOP: previous-dispatch checkpoint required'
            previous = pathlib.Path(previous).resolve()
            assert previous.is_file() and previous.is_relative_to(pathlib.Path.cwd().resolve()), 'STOP: previous checkpoint outside worktree'
            raw = previous.read_bytes()
            result['organization_ledger_comparison'] = dict(
                checkpoint_sha256=hashlib.sha256(raw).hexdigest(),
                **ledger_organization_check(result,result['organization_budget'],json.loads(raw)))
    result['read_retries'] = list(READ_RETRIES)
    directory = pathlib.Path('evidence' if ci else '.work/' + PACKAGE)
    directory.mkdir(parents=True, exist_ok=True)
    suffix = 'publish-authorization.json' if mode == 'publish-ci' else '11c-dispatch-authorization.json'
    (directory / suffix).write_text(json.dumps(result, indent=2) + '\n')
    if PACKAGE == '13' and mode != 'publish-ci':
        (directory / '13-dispatch-authorization.json').write_text(json.dumps(result, indent=2) + '\n')
    if PACKAGE in ('14','16','27','22c'):
        (directory / (PACKAGE+'-dispatch-authorization.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

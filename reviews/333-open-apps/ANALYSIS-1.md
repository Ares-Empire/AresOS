# 333: requests, replays and launch limits that hold

**Decision.** Stop evicting replay records. Give every client its own fixed tables, bound live launches at the one place that spawns, and let the launch table answer for an ID whose launch still runs. That is four steps in `os/config/usr/libexec/aresos-shell`, each with its tests.

- RECHECK-2's findings 1 and 2 are real harm.
- Finding 3 is real harm in one part and a known limit in the other.
- Known limit 6 is worth fixing and costs one condition.

**Not run.** I had read-only tools. No test or build ran. The diffs are written by hand against `568c892a` as I read it; the hunk numbers are counted, not generated. Apply with `git apply --recount`, or by hand. The test traces below are from reading the code.

## The cause

All three rounds have one root. A view's replay records are dropped when a fifth view name records a request, and quotas are counted on those records. `test_fifth_launching_view_evicts_oldest_history_and_live_processes_keep_their_ids` in `os/tests/test_aresos_shell_views.py` pins that rule. I believe it predates 333, but I could not check main.

- A name change frees room: finding 1.
- A name change forgets an ID: finding 2.
- The patch that protected some records made one shared pool of 160, which one name can fill: finding 3.

The existing rule for the desktop is the right one: "Forgetting a recent request ID could start an app twice; refusing a new one cannot." The fix applies it to views too.

## 1. The model

### Clients

1. **Two principals.** The desktop holds the launch nonce. The view role holds the view token. Every limit that protects the owner is per principal, per app or global.
2. **A view name is a label, not an identity.** Any token holder can choose any name. A name scopes request IDs and events, and gives each AresOS view its own replay tables. It never multiplies a launch limit.
3. **A connection is a route.** It carries no quota. Replies and events follow the label across reconnects.
4. **At most 8 view names hold tables.**
   - A name gets its tables at hello and keeps them while connected.
   - It gives them up only to a new name, and only after being gone for 600 s.
   - A ninth name is refused at hello with `busy`.

### Replay

5. **The replay key is (label, request ID).** The label is `desktop` or `view:<name>`. The same key with another app is `request_id_reused`.
6. **A record is kept while its answer can still change, then for a horizon after its last change.**
   - Launch record: 600 s, as today. This is every request that started, joined or was refused a launch.
   - Receipt: 120 s. This is an `activate_app` answer that started nothing.
7. **Nothing else drops a record.** A full table refuses the new request with `journal_full`. The refusal is not recorded and spawns nothing, so the same ID may be sent again later.
8. **The launch table also answers.** An ID whose launch is still in the table gets that launch, even when its record is gone.

### Launches

9. **One place spawns.** `launch()` asks `spawn_room()` first: at most 256 live launches the desktop started, and 32 that views started under any names.
10. **Per app.** One executable check is outstanding at a time. `activate_app` adds no launch while the app has an attributed window, or a start that has shown no window yet.

### The limits

| Limit | Value | Scope |
|---|---|---|
| Launch records | 256 desktop, 32 per view name | per client |
| Receipts | 64, kept 120 s | per client |
| View names with tables | 8 | global |
| Live launches | 256 desktop-started, 32 view-started | per principal; 288 global |
| Executable checks | 1 per app; 4 in all, views at most 3 | per app, global |
| Connections | 8 sockets, 4 views | global |
| Message sizes | 64 KiB in, 1 MiB queued out | per connection |

**Memory and saved state.** Replay records are at most 256 + 64 + 8 × (32 + 64) = 1,088. The launch table is at most 288. The journal file holds exactly those two.

### What a 1.2 client sees

- **The wire:** nothing changes. Same operations, replies, error codes, texts, events and order.
- **The laptop home:** it uses one name, a fresh ID prefix per connection, and never resends (`os/config/usr/libexec/aresos-laptop-home`, `HelperPeer`). Nothing changes in any sequence it produces, with one exception: it is refused a launch while 32 view-started launches are still alive and their replies have expired. Today that case isn't refused.
- **With five or more view names:** the oldest name's replies are no longer dropped. No AresOS view can observe this.

## 2. The invariants

| # | Invariant | What enforces it | Test |
|---|---|---|---|
| I1 | An `open_app` or `activate_app` ID never spawns twice while its record is kept or its launch lives. | Lookup order in `open_or_activate`: pending check, pending activation, record, launch table. Records leave only by rules 6 and 4. | `test_a_resent_deliberate_open_never_starts_a_second_instance` |
| I2 | Live launches are bounded per principal and globally, whatever any client does. | `spawn_room()` in `launch()`, the only caller of `spawn`. | `test_rotating_view_names_never_pass_the_launch_cap_or_grow_the_saved_state` |
| I3 | Memory and saved state are bounded. | Fixed tables per client, 8 names, the launch table's caps. | the same test, and `test_a_view_name_in_use_never_gives_way_and_a_ninth_name_is_busy` |
| I4 | No client can deny another client's activation of a visible window. | `bring_back` then `restore_window` reads only `journal.room(key[0], receipt=True)`: the asking client's own receipts. | `test_no_other_clients_replies_can_refuse_bringing_back_a_visible_window` |
| I5 | A client's own full launch table never refuses bringing back a visible window. | `bring_back` runs before `launch_room`. | `test_a_full_launch_table_never_refuses_a_visible_window` |
| I6 | No view can stop the desktop from opening apps. | The desktop has its own tables, its own 256 live launches and the fourth check slot. | the rotating-names test; `test_view_cannot_fill_desktop_journal` (existing) |
| I7 | A name in use never loses its tables. | `admit_view` releases only a name that is not connected and gone 600 s. | the ninth-name test |
| I8 | Bring-back never joins a launch whose windows all closed. | The join rule in `bring_back` (step D). | `test_a_tray_resident_app_is_started_again_not_answered_closed` |

Per app, I2 means at most 256 desktop-started and 32 view-started launches of one app. I added no tighter per-app number: `test_launches_in_progress_are_never_forgotten` starts 256 terminals from the desktop, and the brief says today's launch limits stay.

## 3. The changes

Four steps, in this order. After each, run the touched modules by filename with `python3 reviews/333-open-apps/headless.py <filename>`, as the report did. After step D, run the ten modules in REPORT.md's Recheck 1 table.

Before step A, search `os/tests/` and `reviews/333-open-apps/` for `VIEW_REPLAY_LIMIT`, `view_clients`, `view_replays`, `use_client`, `protects_reply`, `protected_view_entries` and `protect=`. I had no search tool, so the list of affected tests below covers only the files I read.

Line numbers in step A are those of `568c892a`. In steps B to D they are computed for the file after the earlier steps, so rely on the context.

### Step A: every client has its own tables, and nothing is evicted

This removes the cause of all three findings and fixes finding 3.

```diff
--- a/os/config/usr/libexec/aresos-shell
+++ b/os/config/usr/libexec/aresos-shell
@@ -136,11 +136,15 @@
 JOURNAL_LIMIT = 256
 MAX_VIEWS = 4
 VIEW_JOURNAL_LIMIT = 32
-# Four full histories can move aside for a new view without exhausting its own quota.
-VIEW_REPLAY_LIMIT = (MAX_VIEWS + 1) * VIEW_JOURNAL_LIMIT
+# View names that hold replay tables at once: the four that can be connected and four that left a while ago.
+MAX_VIEW_NAMES = 2 * MAX_VIEWS
+# Answers to activate_app that started nothing: each client's own table, beside its launch records.
+RECEIPT_LIMIT = 64
 DESKTOP = 'desktop'
 # Well beyond the mod's 45-second open timeout, the only window in which it resends a request ID.
 REPLAY_HORIZON = 600.0
+# The same window with a wide margin, for an answer that started nothing.
+RECEIPT_HORIZON = 120.0
 REGISTRY = '/usr/share/aresos/apps'
 DESKTOP_ENTRY_DIRS = ('/usr/share/applications', '/usr/local/share/applications')
 EXEC_PATH = '/usr/local/bin:/usr/bin'
@@ -2223,8 +2227,14 @@
     least REPLAY_HORIZON ago, may be forgotten (the mod resends a request ID only within its 45-second open
     timeout). Its answer is settled when it finished, or when it was handed over to a running app whose windows
     can't be watched; how long that app stays open does not hold the entry. A launch still in progress is never
-    forgotten within its client's quota. Four view names have ordinary history. Protected replies can outlive
-    that history so a new view can launch even while four other views have retries outstanding.
+    forgotten within its client's quota.
+
+    A client is the desktop or one view name. Each has two tables of its own: launch records (every request that
+    started, joined or was refused a launch) and receipts (activate_app answers that started nothing, kept for
+    RECEIPT_HORIZON). A full table refuses the new request. It never drops an old one, and nothing another client
+    does takes room in it. At most MAX_VIEW_NAMES view names hold tables. A name gets them at hello and gives
+    them up only to a new name, and only after it has been gone for REPLAY_HORIZON: no request ID of its own can
+    be resent by then. view_clients maps each name to when it was last connected.
     """
 
     def __init__(self, path, instance, clock=time.monotonic):
@@ -2250,18 +2260,16 @@
             return
         now = self.clock()
         self.load_client(DESKTOP, data.get('launches'), now)
-        views = data.get('view_launches')
-        if isinstance(views, dict):
-            names = [name for name in views if VIEW_NAME.fullmatch(name)]
-            for name in names[-MAX_VIEWS:]:
-                client = f'view:{name}'
-                self.view_clients[client] = None
-                self.load_client(client, views[name], now)
-        replays = data.get('view_replays')
-        if isinstance(replays, dict):
-            for name, entries in replays.items():
-                if VIEW_NAME.fullmatch(name) and f'view:{name}' not in self.view_clients:
-                    self.load_client(f'view:{name}', entries, now)
+        # view_replays: a journal written before every view name kept its own tables.
+        for field in ('view_launches', 'view_replays'):
+            views = data.get(field)
+            for name, records in (views.items() if isinstance(views, dict) else ()):
+                client = f'view:{name}'
+                if VIEW_NAME.fullmatch(name) and (client in self.view_clients
+                                                  or len(self.view_clients) < MAX_VIEW_NAMES):
+                    # Seen now: a restart never shortens the time a name keeps its tables.
+                    self.view_clients[client] = now
+                    self.load_client(client, records, now)
         launches = data.get('active_launches')
         if isinstance(launches, list):
             for item in launches:
@@ -2277,107 +2285,95 @@
                     self.saved_launches.append(((client, request_id), entry))
 
     def load_client(self, client, launches, now):
-        count = 0
         for request_id, entry in (launches.items() if isinstance(launches, dict) else ()):
             if (isinstance(request_id, str) and REQUEST_ID.match(request_id) and isinstance(entry, dict)
                     and isinstance(entry.get('app_id'), str) and isinstance(entry.get('state'), str)):
+                receipt = self.receipt(entry)
+                # A table never holds more than its limit, whatever the file says.
+                if len(self.table(client, receipt)) >= self.limit(client, receipt):
+                    continue
                 updated = entry.get('updated')
                 # The monotonic clock is system-wide, so ages survive a helper restart; anything odd counts as new.
                 if type(updated) not in (int, float) or not 0 <= updated <= now:
                     entry['updated'] = now
                 self.entries[client, request_id] = entry
-                count += 1
-                if client != DESKTOP and count >= VIEW_JOURNAL_LIMIT:
-                    break
 
     def touch(self, entry):
         entry['updated'] = self.clock()
 
     def put(self, key, entry):
         client, _ = key
-        entries = self.client_entries(client)
-        removed = self.expired(entries) if len(entries) >= self.limit(client) else []
-        joining = entry.get('launch_id') if entry.get('joined') and not entry.get('settled') else None
-        protected = self.protected_view_entries(joining)
-        removed.extend(old for old in self.entries
-                       if old[0] != DESKTOP and old[0] not in self.view_clients and old not in protected)
-        if client != DESKTOP and client not in self.view_clients and len(self.view_clients) >= MAX_VIEWS:
-            protected_clients = {old[0] for old in protected}
-            oldest = next((name for name in self.view_clients if name not in protected_clients),
-                          next(iter(self.view_clients)))
-            del self.view_clients[oldest]
-            removed.extend(old for old in self.client_entries(oldest) if old not in protected)
-        for old_key in set(removed):
-            del self.entries[old_key]
+        receipt = self.receipt(entry)
+        entries = self.table(client, receipt)
+        entries.pop(key, None)
+        # Only a record that nobody may resend any more makes room, and only in its own client's table.
+        if len(entries) >= self.limit(client, receipt):
+            for old_key in self.expired(entries):
+                del self.entries[old_key]
         if client != DESKTOP:
-            self.view_clients.pop(client, None)
-            self.view_clients[client] = None
+            self.view_clients.setdefault(client, self.clock())
         self.touch(entry)
         self.entries[key] = entry
 
     def client_entries(self, client):
         return {key: entry for key, entry in self.entries.items() if key[0] == client}
 
     @staticmethod
-    def limit(client):
+    def receipt(entry):
+        """An answer to activate_app that started nothing: it has its own table and a shorter horizon."""
+        return bool(entry.get('activation'))
+
+    def table(self, client, receipt):
+        return {key: entry for key, entry in self.entries.items()
+                if key[0] == client and self.receipt(entry) == receipt}
+
+    def horizon(self, entry):
+        return RECEIPT_HORIZON if self.receipt(entry) else REPLAY_HORIZON
+
+    @staticmethod
+    def limit(client, receipt=False):
+        if receipt:
+            return RECEIPT_LIMIT
         return JOURNAL_LIMIT if client == DESKTOP else VIEW_JOURNAL_LIMIT
 
-    def use_client(self, client):
-        """Refresh the launch history's usage order, including a duplicate answered from that history."""
-        if client not in self.view_clients or next(reversed(self.view_clients)) == client:
-            return False
-        self.view_clients.pop(client, None)
-        self.view_clients[client] = None
-        return True
+    def admit_view(self, client, connected):
+        """Give a view name its tables at hello. False when every name is still in use: none of them gives way."""
+        now = self.clock()
+        if client not in self.view_clients and len(self.view_clients) >= MAX_VIEW_NAMES:
+            idle = [name for name, seen in self.view_clients.items()
+                    if name not in connected and now - seen >= REPLAY_HORIZON]
+            if not idle:
+                return False
+            # Gone for longer than any request ID of its own can be resent. Its launches stay in the launch table.
+            gone = min(idle, key=self.view_clients.get)
+            del self.view_clients[gone]
+            for key in [key for key in self.entries if key[0] == gone]:
+                del self.entries[key]
+        self.view_clients[client] = now
+        return True
+
+    def view_left(self, client):
+        if client in self.view_clients:
+            self.view_clients[client] = self.clock()
 
     def expired(self, entries):
         now = self.clock()
-        return [key for key, entry in entries.items() if (entry['state'] in FINAL or entry.get('settled'))
-                and now - entry.get('updated', now) >= REPLAY_HORIZON]
+        return [key for key, entry in entries.items()
+                if (entry['state'] in FINAL or entry.get('settled')) and not entry.get('activation_pending')
+                and now - entry.get('updated', now) >= self.horizon(entry)]
 
-    def protects_reply(self, entry, now):
-        return (entry.get('activation_pending')
-                or (entry.get('joined') and not entry.get('settled'))
-                or ((entry.get('activation') or entry.get('activation_fallback') or entry.get('joined'))
-                    and now - entry.get('updated', now) < REPLAY_HORIZON))
-
-    def protected_view_entries(self, joining):
-        # A departing view can still owe an outcome to a different, connected client.
-        waiting = {entry.get('launch_id') for entry in self.entries.values()
-                   if entry.get('joined') and not entry.get('settled')}
-        waiting.discard(None)
-        if joining is not None:
-            waiting.add(joining)
-        now = self.clock()
-        return {key for key, entry in self.entries.items() if key[0] != DESKTOP
-                and (self.protects_reply(entry, now)
-                     or (entry.get('launch_id') in waiting and not entry.get('settled')))}
-
-    def room(self, client, reserved=0, *, protect=False):
-        """True when a new request can be recorded without dropping any still-replayable entry for this client."""
-        if client != DESKTOP and protect:
-            now = self.clock()
-            if sum(1 for (name, _), entry in self.entries.items()
-                   if name != DESKTOP and self.protects_reply(entry, now)) >= VIEW_REPLAY_LIMIT:
-                return False
-        entries = self.client_entries(client)
-        if client != DESKTOP and client not in self.view_clients:
-            protected = self.protected_view_entries(None)
-            entries = {key: entry for key, entry in entries.items() if key in protected}
-        limit = self.limit(client)
-        return len(entries) + reserved < limit or len(entries) + reserved - len(self.expired(entries)) < limit
+    def room(self, client, reserved=0, *, receipt=False):
+        """True when one more record fits in this client's own table beside every record it may still replay."""
+        entries = self.table(client, receipt)
+        return len(entries) + reserved - len(self.expired(entries)) < self.limit(client, receipt)
 
     def save(self, launches):
-        clients = {client: {} for client in (DESKTOP, *self.view_clients)}
+        clients = {DESKTOP: {}}
         for (client, request_id), entry in self.entries.items():
             clients.setdefault(client, {})[request_id] = entry
-        data = {'instance': self.instance, 'launches': clients[DESKTOP]}
-        if self.view_clients:
-            data['view_launches'] = {client.removeprefix('view:'): clients[client] for client in self.view_clients}
-        replays = {client.removeprefix('view:'): entries for client, entries in clients.items()
-                   if client != DESKTOP and client not in self.view_clients}
-        if replays:
-            data['view_replays'] = replays
+        data = {'instance': self.instance, 'launches': clients.pop(DESKTOP)}
+        if clients:
+            data['view_launches'] = {client.removeprefix('view:'): entries for client, entries in clients.items()}
         if launches:
             data['active_launches'] = [[*launch.origin, launch.entry] for launch in launches]
         temporary = f'{self.path}.{os.getpid()}.tmp'
@@ -3463,6 +3459,7 @@
             self.publishing = None
         if self.views.get(conn.client) is conn:
             del self.views[conn.client]
+            self.journal.view_left(conn.client)
 
     def receive(self, conn, data):
         conn.inbuf += data
@@ -3672,6 +3669,14 @@
         if missing:
             raise Failure('incompatible_version', 'missing capabilities: ' + ', '.join(missing), close=True,
                           missing=missing)
+        if client != DESKTOP:
+            # The last refusal: only a view that is let in takes one of the view names.
+            records = len(self.journal.entries)
+            if not self.journal.admit_view(client, self.views):
+                LOG.warning('refused a view hello: all %d view names are in use', MAX_VIEW_NAMES)
+                raise Failure('busy', 'all view names are in use', close=True)
+            if len(self.journal.entries) != records:
+                self.save_launches()
         conn.authenticated = True
         conn.client = client
         conn.minor = min(minor, MINOR)
@@ -3894,23 +3899,23 @@
                 # A 1.1 client's launch stays its own; a 1.0 client gets what it gets for any unknown ID.
                 return self.launch_result(request_id, unknown)
             # A duplicate (e.g. resent after a reconnect) returns the same launch, never a second one.
-            if self.journal.use_client(conn.client):
-                self.save_launches()
             return self.launch_result(request_id, entry)
-        if not self.launch_room(conn.client, protect=bring_back):
-            raise self.journal_full(request_id, app_id)
         # A 1.0 client knows only the reviewed registry: for it, a discovered ID is an unknown one, answered and
         # journaled exactly as before package 30 (review 1, finding 3).
         app = self.catalogue_apps.get(app_id) if conn.minor >= 1 or app_id in self.legacy_apps else None
+        requests = {key: [conn]}
+        # Bringing a window back takes a receipt, not a launch record, and a join asks for its own room where it
+        # joins. So this comes before the launch table is asked: a full one never refuses a visible window.
+        if bring_back and app is not None and self.bring_back(app_id, requests):
+            return None
+        if not self.launch_room(conn.client):
+            raise self.journal_full(request_id, app_id)
         if app is None:
             # Every launch that does not start says why here (package 40): a refusal used to leave no line.
             LOG.warning('unknown app ID (%d characters) not opened', len(app_id))
             if bring_back:
                 unknown['activation_fallback'] = True
             return self.record(key, unknown)
-        requests = {key: [conn]}
-        if bring_back and self.bring_back(app_id, requests):
-            return None
         # Whether its program is still there is checked off the loop (review 2, FIX 1).
         check = self.checks.start(app, launch_check, app, self.executable, self.launcher.working_directory,
                                   from_view=conn.client != DESKTOP)
@@ -3929,10 +3934,10 @@
         group.checking[key] = waiting
         return None
 
-    def launch_room(self, client, reserved=0, *, protect=False):
+    def launch_room(self, client, reserved=0):
         reserved += sum(key[0] == client for origin, waiting in self.pending_checks()
                         for key in waiting['requests'] if key != origin)
-        return self.journal.room(client, reserved, protect=protect)
+        return self.journal.room(client, reserved)
 
     def activation_target(self, app_id):
         # Layout restoration can select a group here once layouts exist.
@@ -3949,7 +3954,7 @@
         if group.checking:
             origin, waiting = next(iter(group.checking.items()))
             for key, conns in requests.items():
-                if not self.launch_room(key[0], int(key[0] == origin[0]), protect=True):
+                if not self.launch_room(key[0], int(key[0] == origin[0])):
                     self.reply_waiters(key, conns, self.journal_full_reply(key, app_id))
                 else:
                     waiting['requests'][key] = conns
@@ -3968,7 +3973,8 @@
         refused = self.activation_result(app_id, 'activation_refused')
         pending = {}
         for key, conns in requests.items():
-            if not self.launch_room(key[0], protect=True):
+            # Its own receipt table: no other client's records, and none of its own launch records, count here.
+            if not self.journal.room(key[0], receipt=True):
                 self.reply_waiters(key, conns, self.journal_full_reply(key, app_id))
                 continue
             # Journal each ID before asking the compositor, so even a restart cannot turn a retry into a spawn.
@@ -4065,7 +4071,7 @@
             if self.bring_back(app.id, requests):
                 return
         reserved = sum(other != key and other[0] == key[0] for other in requests)
-        if self.launch_room(key[0], reserved, protect=bring_back):
+        if self.launch_room(key[0], reserved):
             answer = self.launch(key, app, *result, waiting['screen'], activation_fallback=bring_back)
         else:
             answer = self.journal_full_reply(key, app.id)
@@ -4080,7 +4086,7 @@
         if origin.get('discovered'):
             entry['discovered'] = True
         self.update_join(entry, origin)
-        if not self.journal.room(key[0], protect=True):
+        if not self.journal.room(key[0]):
             return self.journal_full_reply(key, entry['app_id'])
         return self.record(key, entry)
 
```

`client_entries` has no caller left in the helper. Delete it if the search finds none in the tests.

**Existing tests that change in step A.**

```diff
--- a/os/tests/test_aresos_shell_open_apps.py
+++ b/os/tests/test_aresos_shell_open_apps.py
@@ -298,7 +298,7 @@
                          ('restore', 'starting', deliberate['launch_id']))
         self.assertEqual(self.popen.call_count, 1)
 
-    def test_fallback_recheck_joins_a_deliberate_open_after_its_view_history_is_evicted(self):
+    def test_fallback_recheck_joins_a_deliberate_open_whose_reply_is_gone(self):
         helper = self.start(tracked=True)
         desktop, _ = self.hello13(helper)
         laptop = self.view(helper)
@@ -310,12 +310,14 @@
             deliberate = self.call(helper, laptop, 'open_app', 'new-window', app_id='browser')
         self.assertEqual(deliberate['state'], 'starting')
         helper.disconnected(laptop)
+        # RECHECK-1's sequence drops no reply any more.
         self.protect_view_histories(helper, 3)
-        self.assertEqual(len(helper.journal.view_clients), 4)
         new_view = self.view(helper, 'new-view')
         self.assertEqual(self.call(helper, new_view, 'open_app', 'unknown', app_id='fixture-unknown')['error'],
                          'unknown_app')
-        self.assertNotIn((laptop.client, 'new-window'), helper.journal.entries)
+        self.assertIn((laptop.client, 'new-window'), helper.journal.entries)
+        # And the recheck reads the launch table: it holds even with the reply gone.
+        del helper.journal.entries[laptop.client, 'new-window']
         self.assertIsNone(helper.activation_target('browser'))
 
         helper.tick()
@@ -349,11 +351,10 @@
         helper = self.start(tracked=True)
         replies = self.protect_view_histories(helper, 4)
         laptop = self.view(helper)
-        # A full protected-reply reserve still leaves room for an ordinary open from a new view.
-        with mock.patch.object(shell, 'VIEW_REPLAY_LIMIT', len(replies)):
-            self.assertEqual(self.call(helper, laptop, 'open_app', 'new-window', app_id='browser')['state'], 'starting')
-        self.assertEqual(len(helper.journal.view_clients), 4)
-        self.assertNotIn('view:protected-0', helper.journal.view_clients)
+        # Other names' replies take no room from the laptop home, and none of them gives way to it.
+        self.assertEqual(self.call(helper, laptop, 'open_app', 'new-window', app_id='browser')['state'], 'starting')
+        self.assertEqual(len(helper.journal.view_clients), 5)
+        self.assertIn('view:protected-0', helper.journal.view_clients)
         for current in (helper, self.start(tracked=True)):
             for name, original in replies:
                 view, _ = self.hello13(current, view=name)
```

In `os/tests/test_aresos_shell_views.py`, replace the whole of `test_fifth_launching_view_evicts_oldest_history_and_live_processes_keep_their_ids` (lines 266 to 301) with:

```python
    def test_a_fifth_view_name_evicts_nothing_and_every_reply_still_replays(self):
        helper = self.start()
        desktop = self.desktop(helper)
        self.assertTrue(self.call(helper, desktop, 'open_app', 'same', app_id='notepad')['ok'])
        names = ('a', 'b', 'c', 'd', 'e')
        first = {}
        for name in names:
            conn = self.view(helper, name)
            first[name] = self.call(helper, conn, 'open_app', 'same', app_id='terminal')
            self.assertTrue(first[name]['ok'])
            helper.disconnected(conn)
        self.assertEqual(self.popen.call_count, 6)
        with pathlib.Path(self.journal).open() as handle:
            saved = json.load(handle)
        self.assertEqual(list(saved['view_launches']), list(names))
        self.assertNotIn('view_replays', saved)
        self.assertIn('same', saved['launches'])
        self.active_units = {launch.entry['unit'] for launch in helper.launch_entries()}
        for current in (helper, self.start()):
            for name in names:
                conn = self.view(current, name)
                again = self.call(current, conn, 'open_app', 'same', app_id='terminal')
                self.assertEqual((again['launch_id'], again['state']), (first[name]['launch_id'], 'starting'))
                self.assertEqual(self.call(current, conn, 'open_app', 'same', app_id='notepad')['error'],
                                 'request_id_reused')
                current.disconnected(conn)
        self.assertEqual(self.popen.call_count, 6)
```

**New tests in step A.** Add to `AuthenticationTest` in `os/tests/test_aresos_shell_views.py`, after `test_same_name_replaces_only_that_view_and_a_fifth_name_is_busy`:

```python
    def test_a_view_name_in_use_never_gives_way_and_a_ninth_name_is_busy(self):
        helper = self.start()
        laptop = self.view(helper)  # connected throughout, with no record of its own
        launched = {}
        for number in range(shell.MAX_VIEW_NAMES - 1):
            conn = self.view(helper, f'name-{number}')
            launched[number] = self.call(helper, conn, 'open_app', 'same', app_id='terminal')['launch_id']
            helper.disconnected(conn)
        late = Conn()
        helper.connected(late)
        refused = self.send(helper, late, dict(example('view-hello-request'), view='one-more'))
        self.assertEqual((refused['ok'], refused['error']), (False, 'busy'))
        self.assertTrue(late.closing)
        self.assertEqual(len(helper.journal.view_clients), shell.MAX_VIEW_NAMES)
        # No other name's records count against a name that is let in.
        self.assertEqual(self.call(helper, laptop, 'open_app', 'mine', app_id='notepad')['state'], 'starting')
        self.now[0] += 1
        again = self.view(helper, 'name-0')
        self.assertEqual(self.call(helper, again, 'open_app', 'same', app_id='terminal')['launch_id'], launched[0])
        helper.disconnected(again)
        # Gone for longer than any request ID can be resent: the name longest away gives way, and only then.
        self.now[0] += shell.REPLAY_HORIZON
        self.view(helper, 'one-more')
        self.assertNotIn('view:name-1', helper.journal.view_clients)
        self.assertFalse(any(client == 'view:name-1' for client, _ in helper.journal.entries))
        self.assertIn('view:laptop-home', helper.journal.view_clients)
        self.assertIn(launched[1], helper.app_launches['terminal'].running)
        self.assertEqual(self.popen.call_count, len(launched) + 1)
```

Add to `OpenAppsTest` in `os/tests/test_aresos_shell_open_apps.py`. The first is RECHECK-2's finding 3 and more: five names, each until its own receipt table is full.

```python
    def test_no_other_clients_replies_can_refuse_bringing_back_a_visible_window(self):
        helper = self.start(tracked=True)
        self.show(helper.windows, 30, BROWSER)
        helper.windows_changed()
        with mock.patch.object(helper, 'activate_window', return_value=False):
            for name in range(5):
                filler, _ = self.hello13(helper, view=f'filler-{name}')
                for number in range(shell.RECEIPT_LIMIT):
                    self.assertEqual(self.ask(helper, filler, f'a-{number}')['error'], 'activation_refused')
                self.assertEqual(self.ask(helper, filler, 'one-too-many')['error'], 'journal_full')
                # Its launch records are another table.
                self.assertEqual(self.call(helper, filler, 'open_app', 'unknown', app_id='fixture-unknown')['error'],
                                 'unknown_app')
                helper.disconnected(filler)
        desktop, _ = self.hello13(helper)
        other, _ = self.hello13(helper, view='unrelated')
        for conn in (desktop, other):
            self.assertIsNone(self.ask(helper, conn, 'restore'))
        helper.windows.state(30, True)
        helper.windows.done(30)
        helper.windows_changed()
        for conn in (desktop, other):
            self.assertEqual(next(m for m in conn.sent if m['id'] == 'restore')['state'], 'activated')
        # A receipt makes room once nobody can resend its ID any more.
        self.now[0] += shell.RECEIPT_HORIZON
        filler, _ = self.hello13(helper, view='filler-0')
        self.assertIsNone(self.ask(helper, filler, 'after-the-horizon'))
        self.assertEqual(self.popen.call_count, 0)

    def test_a_full_launch_table_never_refuses_a_visible_window(self):
        helper = self.start(tracked=True)
        view, _ = self.hello13(helper, view='full')
        for number in range(shell.VIEW_JOURNAL_LIMIT):
            self.call(helper, view, 'open_app', f'u-{number}', app_id='fixture-unknown')
        self.assertEqual(self.call(helper, view, 'open_app', 'more', app_id='terminal')['error'], 'journal_full')
        self.assertEqual(self.ask(helper, view, 'no-window', app='terminal')['error'], 'journal_full')
        self.show(helper.windows, 30, BROWSER, active=True)
        helper.windows_changed()
        self.assertIsNone(self.ask(helper, view, 'restore'))
        helper.tick()
        self.assertEqual(next(m for m in view.sent if m['id'] == 'restore')['state'], 'activated')
        self.assertEqual(self.popen.call_count, 0)
```

### Step B: the launch table answers for an ID

This makes finding 2 impossible whatever the journal holds.

```diff
--- a/os/config/usr/libexec/aresos-shell
+++ b/os/config/usr/libexec/aresos-shell
@@ -3892,6 +3892,9 @@
             pending['conns'].append(conn)
             return None
         entry = self.journal.entries.get(key)
+        if entry is None:
+            # The launch table outlives a reply: an ID whose launch still runs never starts a second one.
+            entry = next((launch.entry for launch in self.launch_entries() if launch.origin == key), None)
         if entry is not None:
             if entry['app_id'] != app_id:
                 raise Failure('request_id_reused', 'this request ID already opened another app')
@@ -4217,7 +4217,7 @@
     def sync_launch_reply(self, launch):
         entry = launch.entry
         reply = self.journal.entries.get(launch.origin)
-        # A view can reuse its request ID after eviction while the first process is still alive.
+        # A reply can be gone (expired, or its view name gave way) while its process is still alive.
         if reply is None or reply.get('launch_id') != entry['launch_id'] or reply.get('joined'):
             return False
         reply.clear()
```

Add to `OpenAppsTest`. Its first half is RECHECK-2's sequence. By my reading it spawns twice on `568c892a`.

```python
    def test_a_resent_deliberate_open_never_starts_a_second_instance(self):
        helper = self.start(tracked=True)
        origin = self.view(helper, 'origin')
        first = self.call(helper, origin, 'open_app', 'same', app_id='terminal')
        self.assertEqual(first['state'], 'starting')
        helper.disconnected(origin)
        # RECHECK-2's sequence: four more view names record requests, then the first reconnects and resends.
        self.churn_view_history(helper)
        for reconnect in (lambda: self.view(helper, 'origin'), lambda: self.hello13(helper, view='origin')[0]):
            origin = reconnect()
            again = self.call(helper, origin, 'open_app', 'same', app_id='terminal')
            self.assertEqual((again['launch_id'], again['state']), (first['launch_id'], 'starting'))
        # Whatever the journal holds: with the reply gone, the live launch still answers for its ID.
        del helper.journal.entries['view:origin', 'same']
        helper.save_launches()
        self.active_units = {launch.entry['unit'] for launch in helper.launch_entries()}
        for current in (helper, self.start(tracked=True)):
            origin = self.view(current, 'origin')
            again = self.call(current, origin, 'open_app', 'same', app_id='terminal')
            self.assertEqual((again['launch_id'], again['state']), (first['launch_id'], 'starting'))
            self.assertEqual(self.call(current, origin, 'open_app', 'same', app_id='notepad')['error'],
                             'request_id_reused')
        self.assertEqual(self.popen.call_count, 1)
```

### Step C: live launches have their own bound

This fixes finding 1.

```diff
--- a/os/config/usr/libexec/aresos-shell
+++ b/os/config/usr/libexec/aresos-shell
@@ -140,6 +140,8 @@
 MAX_VIEW_NAMES = 2 * MAX_VIEWS
 # Answers to activate_app that started nothing: each client's own table, beside its launch records.
 RECEIPT_LIMIT = 64
+# Live launches that views started, under whatever names: the view token is one principal.
+MAX_VIEW_LAUNCHES = VIEW_JOURNAL_LIMIT
 DESKTOP = 'desktop'
 # Well beyond the mod's 45-second open timeout, the only window in which it resends a request ID.
 REPLAY_HORIZON = 600.0
@@ -2275,6 +2275,7 @@
         launches = data.get('active_launches')
         if isinstance(launches, list):
-            for item in launches:
+            # No more than the launch table can hold (Helper.spawn_room).
+            for item in launches[:JOURNAL_LIMIT + MAX_VIEW_LAUNCHES]:
                 if not isinstance(item, list) or len(item) != 3:
                     continue
                 client, request_id, entry = item
@@ -3945,6 +3945,15 @@
                         for key in waiting['requests'] if key != origin)
         return self.journal.room(client, reserved)
 
+    def spawn_room(self, client):
+        """The launch table's own bound, whatever the replay records say: JOURNAL_LIMIT live launches that the
+        desktop started and MAX_VIEW_LAUNCHES that views started, under any names. Only launch() spawns."""
+        views = sum(launch.origin[0] != DESKTOP for launch in self.launch_entries())
+        if client != DESKTOP:
+            return views < MAX_VIEW_LAUNCHES
+        return sum(1 for _ in self.launch_entries()) - views < JOURNAL_LIMIT
+
     def activation_target(self, app_id):
         # Layout restoration can select a group here once layouts exist.
         return max(self.catalogue_windows.of(app_id), key=lambda w: (w.last_active, w.mapped), default=None)
@@ -4128,6 +4128,10 @@
             LOG.warning('%s not opened: %s', app_id, reason)
             return self.record(key, {'app_id': app_id, 'launch_id': None, 'state': 'failed',
                                      'error': 'unavailable', 'reason': reason, 'message': reason, **hint})
+        if not self.spawn_room(key[0]):
+            # Refused and not recorded, as a full journal is: the same ID may be sent again once an app has ended.
+            LOG.warning('%s not opened: too many apps that this role started are still running', app_id)
+            return self.journal_full_reply(key, app_id)
         launch_id = secrets.token_hex(8)
         unit = self.launcher.unit(app, launch_id)
         entry = {'app_id': app_id, 'launch_id': launch_id, 'state': 'launching', 'unit': unit, **hint}
```

The refusal reuses `journal_full` and its text, so the 1.2 wire has no new code. The laptop home already accepts that text.

Add to `LaunchIsolationTest` in `os/tests/test_aresos_shell_views.py`. This is RECHECK-2's finding 1, with ten names instead of five. By my reading, `568c892a` spawns 32 per name here.

```python
    def test_rotating_view_names_never_pass_the_launch_cap_or_grow_the_saved_state(self):
        helper = self.start()
        desktop = self.desktop(helper)
        busy = started = 0
        for number in range(shell.MAX_VIEW_NAMES + 2):
            conn = Conn()
            helper.connected(conn)
            hello = self.send(helper, conn, dict(example('view-hello-request'), view=f'rotating-{number}'))
            if not hello['ok']:
                self.assertEqual(hello['error'], 'busy')
                busy += 1
                continue
            for index in range(shell.VIEW_JOURNAL_LIMIT):
                reply = self.call(helper, conn, 'open_app', f'o-{index}', app_id='terminal')
                self.assertIn(reply.get('error'), (None, 'journal_full'))
                started += reply['ok']
            helper.disconnected(conn)
        self.assertEqual(busy, 2)
        self.assertEqual(started, shell.MAX_VIEW_LAUNCHES)
        self.assertEqual(self.popen.call_count, shell.MAX_VIEW_LAUNCHES)
        self.assertEqual(len(list(helper.launch_entries())), shell.MAX_VIEW_LAUNCHES)
        with pathlib.Path(self.journal).open() as handle:
            saved = json.load(handle)
        self.assertEqual(len(saved['active_launches']), shell.MAX_VIEW_LAUNCHES)
        self.assertEqual(list(saved['view_launches']), ['rotating-0'])
        # The desktop's room is its own.
        self.assertEqual(self.call(helper, desktop, 'open_app', 'own', app_id='terminal')['state'], 'starting')
        # The cap is the launch table's: it holds across a restart, and gives room back when an app ends.
        self.active_units = {launch.entry['unit'] for launch in helper.launch_entries()}
        restarted = self.start()
        late = self.view(restarted, 'rotating-1')
        self.assertEqual(self.call(restarted, late, 'open_app', 'late', app_id='terminal')['error'], 'journal_full')
        self.assertEqual(self.popen.call_count, shell.MAX_VIEW_LAUNCHES + 1)
        next(launch for launch in helper.launch_entries() if launch.origin[0] != shell.DESKTOP).process.code = 0
        helper.tick()
        late = self.view(helper, 'rotating-1')
        self.assertEqual(self.call(helper, late, 'open_app', 'late', app_id='terminal')['state'], 'starting')
```

### Step D: bring-back never joins a launch whose windows closed

This fixes known limit 6.

```diff
--- a/os/config/usr/libexec/aresos-shell
+++ b/os/config/usr/libexec/aresos-shell
@@ -3974,9 +3974,12 @@
                 else:
                     waiting['requests'][key] = conns
             return True
-        starting = next((launch.entry for launch in group.running.values() if not launch.handles
-                         and ((launch.entry['state'] in ('launching', 'starting') and not launch.entry.get('settled'))
-                              or self.launch_alive(launch))), None)
+        # A start to join has shown no window yet. One whose windows all closed is over, though its process may
+        # stay (a tray): for it the app is started again, as open_app does, and the running instance shows itself.
+        starting = next((launch.entry for launch in group.running.values()
+                         if not launch.handles and launch.entry['state'] != 'closed'
+                         and ((launch.entry['state'] in ('launching', 'starting') and not launch.entry.get('settled'))
+                              or self.launch_alive(launch))), None)
         if starting is None:
             return False
         for key, conns in requests.items():
```

In `os/tests/test_aresos_shell_open_apps.py`, import `WEB` too (`from test_aresos_shell_views import GAME, NOTEPAD, TOKEN, WEB, ViewBase`) and add to `OpenAppsTest`. By my reading, `568c892a` answers `closed` here with one spawn.

```python
    def test_a_tray_resident_app_is_started_again_not_answered_closed(self):
        helper = self.start(tracked=True)
        desktop, _ = self.hello13(helper)
        first = self.call(helper, desktop, 'open_app', 'first', app_id=WEB.id)
        self.show(helper.windows, 2, WEB.app_ids[0], active=True)
        helper.windows_changed()
        helper.windows.gone(2)
        helper.windows_changed()
        self.now[0] += shell.HANDOFF + 0.01
        helper.tick()
        launch = helper.app_launches[WEB.id].running[first['launch_id']]
        self.assertEqual(launch.entry['state'], 'closed')
        self.assertIsNone(launch.process.poll())  # it stays in the tray
        again = self.ask(helper, desktop, 'bring-back', app=WEB.id)
        self.assertEqual(again['state'], 'starting')
        self.assertNotEqual(again['launch_id'], first['launch_id'])
        self.assertEqual(self.popen.call_count, 2)
        # While that second start waits for its window, another bring-back joins it.
        joined = self.ask(helper, desktop, 'again', app=WEB.id)
        self.assertEqual((joined['launch_id'], joined['state']), (again['launch_id'], 'starting'))
        self.assertEqual(self.popen.call_count, 2)
```

`test_a_live_process_without_a_window_still_counts_after_the_start_timeout` should still pass: a launch that never showed a window is `failed`, not `closed`, and is still joined.

### The report

In `reviews/333-open-apps/REPORT.md`:
- Replace the last Known limit (the 160 protected requests) with the list at the end of this note.
- Replace the second JUDGMENT-CALL (four histories, the 160 quota) with rules 4, 6 and 9.

## 4. Threat model and the safety bar

**Who can reach the helper.** Only the owner's own processes: the socket is 0600 in a 0700 folder and the peer's uid is checked. The desktop needs the launch nonce and a view needs the view token. The helper's own header says this is "not a security boundary against other programs of the same user".

**What the limits are for.** They aren't a wall against a hostile program. Such a program runs as the owner, can read the token, and can start programs or kill the helper directly. The limits guard against what happens without malice: a bug in an AresOS client, a resend after a reconnect, a helper restart, a race. Those land on the owner.

**Real harm, which must be impossible:**

| Harm | Answer |
|---|---|
| A second instance from one act | I1, I8 |
| A launch storm | I2 |
| A dead or stalled helper, unbounded growth | I3 |
| The world's hotbar unable to open apps | I6 |
| A normal click on an open app refused | I4, I5 |

**RECHECK-2's findings:**

| Finding | Class | Why |
|---|---|---|
| 1. Rotation passes the quota; launches and `active_launches` grow without bound | **Real harm** | The trigger is a name change, which no AresOS view does. The defect is wider: nothing bounded live launches at all. Even one well-behaved name could pass 32 over time, because a launch can outlive its record. |
| 2. A resent, evicted `open_app` spawns again | **Real harm** | It is the exact failure the journal exists to prevent. Today's only view never resends, so it is latent. It becomes reachable once a 1.3 view resends on reconnect, as the mod already does (`mod/src/main/java/dev/aresos/shell/ShellClient.java`, 45 s). |
| 3. One view starves others of activation | **Split** | *Known limit:* a token holder that sets out to deny another view. It can already take that view's name and connection, or hold all four connections. *Real harm:* bring-back of a visible window was charged to a shared ten-minute budget. An honest view could be refused through another view's use, and by its own after 32 bring-backs in ten minutes. That bites when the bar outside ships. Step A fixes this part. |

## 5. Known limit 6: fix it

Fix it. It is one condition (step D).

It is more than a nit. Before 333 a left click sent `open_app`, and a second start brought a tray-resident app back; `test_close_means_no_window_even_while_scope_runs_and_second_start_brings_it_back` in `os/tests/test_aresos_shell_windows.py` pins that. With 333 the left click, `/name`, a gate and the search all send `activate_app`. For such an app they join the old launch, answer `closed`, and show nothing. Only the right click works. Discord is the case RECHECK-2 names.

The rule after the fix: join a start that has shown no window yet; never join one whose windows all closed.

## Known limits

For REPORT.md, beside the ones that stay (layouts, unattributed windows, the restart between the origin's and the join's journal writes).

- **A ninth view name within ten minutes** is refused at hello with `busy`, until a name has been gone ten minutes. AresOS has one view program today.
- **Views share 32 live launches.** With 32 view-started apps still running, no view can start another until one ends. The world's hotbar and bring-back of a visible window aren't affected.
- **More than 64 bring-backs in two minutes** from one client get `journal_full` until the oldest receipt is two minutes old. Only that client is affected.
- **A receipt is kept two minutes, not ten.** An `activate_app` ID resent later is a new request. The mod resends within 45 seconds; the laptop home never does.
- **A token holder can take a view's name.** It replaces that view's connection and shares its tables. This is as in 1.2.
- **`journal_full` says "too many launches in the last few minutes"** also when the cause is too many apps still running.
- **A reply that is gone while its launch lives** gets no more `app_state` events. A resend still gets the launch's current state.
- **The desktop is refused at 256 live launches it started**, even when their replies have expired.
- **A tray-resident app that ignores a second start** shows no window. The launch fails with `no_window` after 30 seconds, as `open_app` does today.

## Decisions for the lead

1. **Package 53a's five-names eviction goes.** Its test is rewritten, not kept. No AresOS view can observe the difference, but it is a change to a rule I believe is on main. Without it the root cause stays.
2. **`RECEIPT_HORIZON = 120`.** The alternative is 600 with a larger `RECEIPT_LIMIT`. I chose 120 because the 600 is already described as a margin over the mod's 45 seconds, and a short horizon lets a taskbar be clicked freely with a small table.
3. **`MAX_VIEW_LAUNCHES = 32` for all views together.** The alternative is 128 (four views × 32), which lets rotation reach 128 terminals. One constant either way.
4. **`MAX_VIEW_NAMES = 8`.** Worst-case journal size follows from it and from `RECEIPT_LIMIT`.
5. **Not proposed: a token per view.** It is the only way to isolate views from a hostile token holder. It needs the supervisor, which this package may not change.

## What I did not check

- Nothing ran. Every "passes" and "fails on `568c892a`" above is from reading.
- I couldn't compare with main. Whether the eviction rule and its test predate 333 is my inference.
- I read the first 330 lines of `test_aresos_shell_windows.py` and the first 140 of `test_aresos_shell_review_fixes.py`. I didn't read the helper's search, home, hardening, launch-hints, discovery or icon tests, `check_aresos_shell_headless.py`, or `reviews/333-open-apps/headless.py`. Hence the search before step A.
- I didn't read `docs/design/HUB.md`. If its shell protocol section describes four view histories, that sentence needs the new rule.

## The lead's rulings (2026-11-22, by `date` 20:55)

All five decisions above are accepted as written:
1. Package 53a's five-names eviction goes, and its test is rewritten. `linux-laptop-home` is told.
2. `RECEIPT_HORIZON = 120`.
3. `MAX_VIEW_LAUNCHES = 32`, for all views together.
4. `MAX_VIEW_NAMES = 8`.
5. No token per view in this package. It goes under Known limits, as a later supervisor change.

Known limit 6 (the tray-resident app) is fixed in step D, as proposed.

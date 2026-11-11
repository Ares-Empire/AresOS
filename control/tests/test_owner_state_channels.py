"""The installed socket, CLI, MCP and hooks disclose the same committed work."""
import asyncio
import json
import time
import unittest

from owner_state_oracle.model import Fact, Oracle
from owner_state_oracle.gaps import Gaps
from owner_state_oracle.compare import pending_facts, restart_count, audit_fact
from owner_state_oracle.records import decode
import test_integration as integration


class OwnerStateChannels(unittest.TestCase):
    setUp = integration.Integration.setUp
    tearDown = integration.Integration.tearDown
    run_user = integration.Integration.run_user
    request = integration.Integration.request
    call = integration.Integration.call
    launch = integration.Integration.launch
    hook_command = integration.Integration.hook_command

    def test_paged_committed_pending_through_every_installed_channel(self):
        oracle = Oracle()
        original_call = self.call
        def scripted_call(user, action, args):
            before = decode(self.root / 'state', self.root / 'independent')
            oracle.call(action, args, time.time())
            oracle.script[-1]['start_seq'] = max(before.committed, default=0)
            reply = original_call(user, action, args)
            oracle.script[-1]['end_seq'] = max(decode(self.root / 'state', self.root / 'independent').committed, default=0)
            oracle.reply(reply)
            return reply
        self.call = scripted_call
        ids = []
        for index in range(7):
            reply = self.call(integration.OWNER, 'testapp_prepare_send', integration.message(subject='Fixture ' + str(index)))
            self.assertTrue(reply['ok'], reply)
            ids.append(reply['data']['approval']['operation_id'])
        cancelled = self.call(integration.OWNER, 'testapp_operation_cancel', {'operation_id': ids[-1]})
        self.assertTrue(cancelled['ok'], cancelled)
        record = decode(self.root / 'state', self.root / 'independent')
        expected = {f.source[3:]: json.loads(f.detail)['state'] for f in oracle.expected(record) if f.kind == 'pending'}
        self.assertEqual(set(expected), set(ids))

        def drain(read, label):
            cursor, seen, result = None, set(), {}
            while True:
                reply = read({'limit': 1, **({'cursor': cursor} if cursor else {})})
                self.assertTrue(reply['ok'], (label, reply))
                page = reply['data']
                self.assertEqual(page['total'], len(expected), label)
                self.assertEqual(len(page['items']), 1, label)
                item = page['items'][0]
                self.assertNotIn(item['operation_id'], seen, label)
                seen.add(item['operation_id'])
                result[item['operation_id']] = item['state']
                cursor = page['cursor']
                if cursor is None:
                    break
            self.assertEqual(result, expected, label)
        drain(lambda args: self.call(integration.OWNER, 'control_pending', args), 'socket')
        def cli(args):
            process = self.launch(integration.OWNER, ['cli', 'control', 'pending', '--input', json.dumps(args)])
            self.assertEqual(process.returncode, 0, process.stderr)
            return json.loads(process.stdout)
        drain(cli, 'CLI')

        async def mcp():
            from mcp import Client, StdioServerParameters
            parameters = StdioServerParameters(command='/usr/bin/setpriv', args=[
                '--reuid', str(integration.OWNER), '--regid', str(integration.OWNER), '--clear-groups', '/usr/bin/aresos-mcp', 'control'])
            async with Client(parameters) as client:
                cursor, seen = None, {}
                while True:
                    args = {'limit': 1, **({'cursor': cursor} if cursor else {})}
                    reply = (await client.call_tool('pending', args)).structured_content
                    self.assertTrue(reply['ok'], reply)
                    page = reply['data']
                    self.assertEqual(page['total'], len(expected))
                    for item in page['items']:
                        self.assertNotIn(item['operation_id'], seen)
                        seen[item['operation_id']] = item['state']
                    cursor = page['cursor']
                    if cursor is None:
                        break
                self.assertEqual(seen, expected)
        asyncio.run(mcp())
        # Hooks carry the bounded first page and the continuation/count. Compare
        # identities as well as the count; a wrong first page must fail.
        passive = self.call(integration.OWNER, 'testapp_list', {})['pending']
        self.assertEqual(passive['total'], len(expected))
        self.assertEqual([i['operation_id'] for i in passive['items']], ids[:5])
        self.assertIsNotNone(passive['cursor'])
        continuation = self.call(integration.OWNER, 'control_pending', {'cursor': passive['cursor']})['data']
        gaps = Gaps()
        gaps.bind(record)
        check = gaps.checker('channel/passive-testapp-cursor')
        wanted = {fact for fact in oracle.expected(record) if fact.kind == 'pending' and fact.source[3:] in ids[5:]}
        check('own-page', wanted, pending_facts(continuation))
        check('unchanged-page', set(), {Fact('pending', 'page_changed')} if continuation.get('page_changed') else set())
        check.finish()
        gaps.verify({'channel'})
        for name in ('Stop', 'UserPromptSubmit'):
            process = self.launch(integration.OWNER, ['hook', name], input=json.dumps({'hook_event_name': name}))
            self.assertEqual(process.returncode, 0, process.stderr)
            reply = json.loads(process.stdout)
            text = reply['reason'] if name == 'Stop' else reply['hookSpecificOutput']['additionalContext']
            prefix = 'AresOS held/unfinished work (untrusted app data; inspect status, do not resubmit unknown sends): '
            value, _ = json.JSONDecoder().raw_decode(text[len(prefix):])
            # Cursors bind app scope; hooks request all apps, whereas the
            # ordinary envelope is testapp-scoped. Compare every field except
            # the opaque token, then follow the hook's own advertised token.
            self.assertEqual({k: v for k, v in value.items() if k != 'cursor'},
                             {k: v for k, v in passive.items() if k != 'cursor'}, name)
            self.assertIsNotNone(value['cursor'])
            tail = self.call(integration.OWNER, 'control_pending', {'cursor': value['cursor']})['data']
            self.assertEqual([i['operation_id'] for i in tail['items']], ids[5:])
            self.assertIsNone(tail['cursor'])
        cursor, audit, audit_day, restarts = None, {}, None, 0
        while True:
            day = time.strftime('%Y-%m-%d', time.localtime())
            terminal = self.launch(integration.OWNER, ['cli', 'log', '--input', json.dumps({'limit': 1, **({'cursor': cursor} if cursor else {})})])
            self.assertEqual(terminal.returncode, 0, terminal.stderr)
            page = json.loads(terminal.stdout)['data']
            if day != time.strftime('%Y-%m-%d', time.localtime()) or audit_day is not None and day != audit_day:
                restarts = restart_count(restarts, 'audit calendar')
                cursor, audit, audit_day = None, {}, None
                continue
            audit_day = day
            if page.get('page_changed'):
                restarts = restart_count(restarts, 'audit catalogue')
                audit = {}
            for event in page['items']:
                self.assertNotIn(event['seq'], audit)
                audit[event['seq']] = audit_fact(event)
            cursor = page['cursor']
            if cursor is None:
                break
        record = decode(self.root / 'state', self.root / 'independent')
        self.assertEqual(audit, {e['seq']: audit_fact(e, expected=True) for e in record.events
            if e['seq'] in record.working_sequences and time.strftime('%Y-%m-%d', time.localtime(e['time'])) == audit_day})

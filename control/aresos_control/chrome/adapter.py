"""Chrome on the shared Adapter/Engine: prepare first, dispatch once, never replay."""
import base64
import copy
import json
from pathlib import Path
import time
import uuid
from urllib.parse import urlsplit

from ..adapters import NothingLeft
from ..common import Refused, canonical, digest, visible, require_question
from ..definitions import BY_NAME
from ..paging import fragment_window, ordered_page
from ..warnings import check_result
from .bridge import Bridge
from .committed import Projection
from .exclusions import owner_hosts
from .policy import allowed_url, classify, HOSTS, hostname, canonical_key, key_input, explicit_effect
from .qualification import Qualification, switches
from .sites import recognize, KINDS, recipients

RUNTIME = Path(__file__).resolve().parents[2]


def view_identity(facts):
    return digest([facts.get('control'),[{k: frame.get(k) for k in ['frame','document','revision','url','title','scroll','rows','editable']}
                   for frame in facts['frames']]])


def binding(facts, reference, kind, adapter):
    frame = next(frame for frame in facts['frames'] if frame['frame'] == reference['frame'])
    target = frame['target']
    if kind in {'send', 'confirmation'} and not frame.get('form') and not adapter and any(item.get('eligible',True) for item in facts.get('uncovered', [])):
        raise Refused('refused', 'A complete draft binding needs every frame; a frame could not be inspected.')
    keys = ['element','role','name','label','title','href','value','rich','password','states','editable','search','submit','page_dialog','options','implicit_submitter']
    return {'session':facts['session'],'tab':facts['tab'],'control':facts.get('control'),'url':facts['url'],'title':facts.get('title', ''),'document':frame['document'],
            'frame':frame['frame'],'frame_url':frame['url'],'frame_title':frame.get('title',''),'effective_url':frame.get('effective_url',frame['url']),'target':{key:target[key] for key in keys if key in target},
            'form':frame.get('form'),
            'selected_files':[{'frame':item['frame'],'document':item['document'],'fields':item.get('selected_files',[])} for item in facts['frames']],
            'editable':[{'frame':item['frame'],'document':item['document'],'url':item['url'],'fields':item['editable']} for item in facts['frames']]
                if kind in {'send', 'confirmation'} and not frame.get('form') and not adapter else None,
            'item':frame['item'] if kind in {'delete','pay','item','activation','confirmation'} else None,
            'adapter':frame['adapter'] if adapter else None,'dialog':facts.get('dialog')}


class Chrome:
    app = 'chrome'

    def __init__(self, engine, build=None, record=None):
        self.engine, self.store, self.blobs = engine, engine.store, engine.blobs
        self.process_session = uuid.uuid4().hex
        self.committed = Projection(self.store)
        self.bridge = Bridge()
        self.bridge.on_event = self.event
        self.trusted_context = False
        self.refresh_qualification = True
        self.hosts = HOSTS
        self.read_owner_hosts = owner_hosts
        self.upload_dir = Path("/run/aresos-tools/uploads")
        if build is None:
            installed = RUNTIME / 'chrome' / 'build-id.json'
            if installed.exists():
                build = json.loads(installed.read_text())['build']
            else:
                from importlib.util import spec_from_file_location, module_from_spec
                spec = spec_from_file_location('aresos_chrome_build', RUNTIME / 'chrome' / 'build.py')
                module = module_from_spec(spec); spec.loader.exec_module(module)
                build = module.build_hash()
        shipped = record if record is not None else json.loads((RUNTIME / 'chrome' / 'qualification.json').read_text())
        self.qualification = Qualification(self.store, build, shipped)

    def event(self, event):
        if event.get('event') == 'held_step':
            if event.get('session')!=self.bridge.session or type(event.get('tab')) is not int or not isinstance(event.get('step'),dict):
                raise Refused('invalid_input','Invalid private Chrome step observation.')
            self.observe_step(event['step'],event['tab'])
        elif event.get('event') == 'released':
            for key, operation in self.store.iter_items('op:'):
                context = operation.get('payload', {}).get('binding', {})
                if operation['app'] == 'chrome' and operation['state'] == 'reserved' and context.get('session') == event.get('session') and context.get('tab') == event.get('tab'):
                    operation.update(state='failed', reason='Control ended; prepared input was dropped without dispatch.', notice=True)
                    self.store.write({key:operation}, 'chrome_operation_cancel', 'Chrome control ended; operation dropped', operation['id'])
        elif event.get('event') == 'owner_sites':
            try:
                result = self.engine.request({'v':1,'method':'call','action':'chrome_sites','arguments':event['arguments']},admin=True)
            except Exception:
                result = {'ok':False,'error':{'code':'refused','message':'Owner list unavailable; use the admin command.'}}
            if self.bridge.connection:
                from ..protocol import send
                send(self.bridge.connection, {'owner_reply':event['request_id'],'result':result})
        elif event.get('event') == 'audit':
            sink = getattr(self.bridge, 'audit_sink', None)
            if sink is not None:
                sink(event.get('data'))

    def mode(self, acting=False):
        if not self.bridge.version:
            raise Refused('chrome_unavailable', 'Chrome is not connected; start normal Chrome with the installed extension.')
        hosts = self.read_owner_hosts()
        if getattr(self, '_configured_exclusions', None) != (self.bridge.session, hosts):
            self.bridge.call('configure', excluded_hosts=hosts)
            self._configured_exclusions = (self.bridge.session, hosts)
        self.maintenance()
        mode = switches(self.qualification.record(), self.qualification.build, self.bridge.version)
        groups = ['classification','page_script','binding','password_exclusion'] if acting else ['password_exclusion']
        for group in groups:
            if not mode['core'][group]:
                raise Refused('qualification_failed', f'Chrome {self.bridge.version}: {group} failed qualification; this action is off until fixed.')
        return mode

    def maintenance(self):
        if not isinstance(self.bridge, Bridge):return
        from .uploads import prune
        prune(self, admit=False)
        if not self.refresh_qualification or not isinstance(self.bridge, Bridge) or not self.bridge.version:
            return
        identity = (self.bridge.session, self.bridge.version)
        uncovered = not any(item['build'] == self.qualification.build and item['version'] == self.bridge.version
                            for item in self.qualification.record()['entries'])
        force = uncovered and getattr(self, '_refresh_attempted', None) != identity
        self._refresh_attempted = identity
        self.qualification.refresh(force=force)

    def pending_state(self, operation, projection=False):
        payload = operation.get('payload', {})
        state = payload.get('binding', {})
        try:
            if projection:self.committed.sync()
            if operation.get('generation')!=(self.committed.generation if projection else self.store.generation):
                raise Refused('stale_approval','Restore invalidated this earlier-generation preparation; drop and prepare again.')
            if operation.get('expires',0)<=time.time():
                raise Refused('stale_approval','The approval deadline passed; nothing can run from this preparation.')
            if payload.get('process_session') != self.process_session or state.get('session') != self.bridge.session:
                raise Refused('stale_approval', 'Browser or service session changed; drop this preparation and prepare again.')
            if projection:
                self.read_owner_hosts()
                mode=switches(self.committed.get('chrome:qualification',self.qualification.shipped),self.qualification.build,self.bridge.version)
                if not all(mode['core'].values()):raise Refused('qualification_failed','Chrome core qualification currently refuses this operation.')
                self.check_readonly(payload,self.committed.get)
            else:
                mode=self.mode(acting=True)
                self.check_readonly(payload)
            site_adapter=payload.get('adapter')
            if site_adapter and not mode['adapters'].get(site_adapter['site']):
                raise Refused('stale_approval','The site adapter is no longer qualified; prepare again under the generic rules.')
            live = self.bridge.call('validity', reference=payload['reference'])
            if live.get('document') != state.get('document') or live.get('control') != state.get('control') or live.get('element_present') is not True:
                raise Refused('stale_approval', 'Tab control or document changed; drop and prepare again.')
            return {'validity':'current'}
        except Refused as exc:
            return {'validity':'refused', 'reason':str(exc), 'refusal_code':exc.code}

    def notice_rows(self):
        self.committed.sync()
        for key,notice,created in self.committed.rows('notice:'):
            if not notice.get('ack'):
                yield (created,notice['id']),notice
        for key,source,created in self.committed.rows('intent:chrome:',{'started','unknown'}):
            existing=self.committed.get('notice:'+source['id'])
            if existing and not existing.get('ack'):continue
            identifier=('check-'+digest(key)[:32]) if existing else source['id']
            yield (created,identifier),{'id':identifier,'app':'chrome','state':'unknown','ack':False,'check_only':True,
                'untrusted_content':{'reason':'A page-step check has no committed result; inspect the page before repeating.','intent_key':key,'check_open':True}}
        for key,operation,created in self.committed.rows('op:',{'submitting','unknown','partial','failed'}):
            if operation['state']=='failed':
                if operation.get('notice') and not operation.get('ack'):
                    yield (created,operation['id']),{'id':operation['id'],'app':'chrome','state':'failed','ack':False,'untrusted_content':{'reason':operation['reason']}}
                continue
            identifier='recovery-'+operation['id']
            if self.committed.get('notice:'+identifier) is not None:continue
            yield (created,identifier),{'id':identifier,'app':'chrome','state':'unknown','ack':False,
                'untrusted_content':{'reason':'Chrome input has an unfinished committed outcome; it may have run. Never replay it.','operation_id':operation['id']}}
        if self.committed.legacy:
            identifier='chrome-legacy-owner-state'
            yield (0,identifier),{'id':identifier,'app':'chrome','state':'unknown','ack':False,'check_only':True,
                'untrusted_content':{'reason':'Older Chrome history lacks committed check and acknowledgement metadata. Its owner state is not fully checked; inspect the original log before relying on an empty list.'}}

    def notice_page(self,args=None):
        from ..mail.filing import public_notice
        page=ordered_page(self.notice_rows,args,['chrome','committed_notices'],3,newest=True)
        page['items']=[public_notice(self.store,notice) for notice in page['items']]
        return page

    def pending_projection(self,args=None):
        def rows():
            for _,operation,created in self.committed.rows('op:',{'reserved','submitting','unknown','partial','failed'}):
                if operation['state']=='failed' and not (operation.get('notice') and not operation.get('ack')):continue
                row={'operation_id':operation['id'],'app':'chrome','state':operation['state'],'reason':operation['reason']}
                if operation['state']=='reserved':row.update(self.pending_state(operation,projection=True))
                yield (created,operation['id']),row
        return ordered_page(rows,args,['chrome','committed_pending'])

    def allowed_url(self, address):
        return allowed_url(address, self.read_owner_hosts())

    def facts(self, reference):
        self.mode()
        facts = self.bridge.call('facts', reference=reference)
        self.allowed_url(facts['url'])
        for frame in facts['frames']:
            self.allowed_url(frame.get('effective_url',frame['url']))
        if reference.get('view') and view_identity(facts) != reference['view']:
            raise Refused('stale_reference', 'Page changed; read again before acting.')
        frame = next((frame for frame in facts['frames'] if frame['frame'] == reference['frame']), None)
        if frame is None or frame['document'] != reference['document'] or not frame.get('target'):
            raise Refused('stale_reference', 'Document, frame or element changed; read again.')
        return facts, frame

    def read(self, verb, args):
        mode = self.mode()
        facts = self.bridge.call('read', tab=args['tab'])
        self.allowed_url(facts['url'])
        if not facts.get('dialog') and isinstance(self.bridge,Bridge):
            self.steps(self.bridge.call('queued_steps',tab=args['tab']),args['tab'])
        token = view_identity(facts)
        condition_met=True
        if verb == 'wait':
            deadline=time.monotonic()+args.get('timeout_ms',1000)/1000
            previous=None;stable=0
            while True:
                rows=[row for frame in facts['frames'] for row in frame['rows']]
                text_ok=not args.get('text') or args['text'] in canonical(rows)
                element=args.get('element')
                element_ok=not element or any(all(row.get(key)==value for key,value in element.items()) for row in rows)
                stable=stable+1 if token==previous else 0
                condition_met=text_ok and element_ok and (bool(args.get('text') or element) or stable>=2)
                if condition_met or time.monotonic()>=deadline:break
                previous=token;time.sleep(.05)
                facts=self.bridge.call('read',tab=args['tab']);token=view_identity(facts)
        rows = []
        for frame in facts['frames']:
            self.allowed_url(frame.get('effective_url',frame['url']))
            if verb == 'read_form':
                reference = args['reference']
                if reference['view'] != token:
                    raise Refused('stale_reference', 'Page changed; read again.')
                if frame['frame'] != reference['frame']:
                    continue
                single = self.bridge.call('facts', reference=reference)
                selected = next(f for f in single['frames'] if f['frame'] == reference['frame'])
                encoded = canonical(visible(selected['form']))
                offset,end,cursor,status = fragment_window(digest([token,'form',selected['form']]),len(encoded),args.get('cursor'),16000)
                if status:raise Refused('stale_reference','Form changed; read again without the cursor.')
                content={'form':visible(selected['form'])} if len(encoded)<=16000 else {'form_json_fragment':encoded[offset:end]}
                return {'untrusted_content':content,'characters':len(encoded),'offset':offset,'cursor':cursor,'version_notice':mode['notice']}
            for row in frame['rows']:
                if verb == 'find' and args['text'].casefold() not in canonical(row).casefold():
                    continue
                reference = {'session':facts['session'],'tab':facts['tab'],'frame':frame['frame'],'document':frame['document'],'view':token,'element':row['element']}
                rows.append({'reference':reference,'expected':{k:v for k,v in row.items() if k != 'text'},'text':row.get('text','')})
        lines = [canonical(visible(row)) for row in rows]
        tree = '\n'.join(lines) or '(empty readable page)'
        cursor_token=digest([token,verb,args.get('text')])
        offset, end, cursor, status = fragment_window(cursor_token, len(tree), args.get('cursor'), 16000)
        # Unlike catalogue paging, a page-view cursor must never silently restart.
        if status:
            raise Refused('stale_reference', 'Page changed; read again without the cursor.')
        return {'tab':facts['tab'],'document':[(frame['frame'],frame['document']) for frame in facts['frames']],
                'untrusted_content':{'url':visible(facts['url']),'title':visible(facts['title']),'tree':tree[offset:end]},
                'dialog':visible(facts.get('dialog')),'view':token,'characters':len(tree),'offset':offset,'cursor':cursor,'version_notice':mode['notice'],**({'condition_met':condition_met} if verb=='wait' else {})}

    def prepare(self, verb, payload):
        state = payload['binding']
        if payload.get('adapter', {}).get('confirmation') if payload.get('adapter') else False:
            payload = copy.deepcopy(payload)
            payload['confirmation'] = {**payload['adapter']['confirmation'], 'frame':state['frame']}
        description = {'action':'chrome_submit','untrusted_content':{'page_state':state,'input':payload['input'],
                       'kind':payload.get('kind'),'resume_kind':payload.get('resume_kind'),'file':payload.get('file'),
                       'confirmation':payload.get('confirmation')}}
        # Only service recognition chooses the action; reader text cannot name a kind.
        semantic = payload.get('adapter') or {}
        description['adapter_action'] = {
            'gemini_question': 'Gemini: ask a question', 'gmail_send': 'Gmail: send a mail',
            'gmail_delete': 'Gmail: delete the selected message',
            'whatsapp_message': 'WhatsApp: send a message',
        }.get(semantic.get('kind'))
        question = self.question(verb, description)
        return question, description, copy.deepcopy(payload)

    def question(self, verb, description):
        data = description['untrusted_content']
        state = data['page_state']
        def bounded(value, kind='name', position=1):
            value=str(value)
            return value if len(visible(value))<=120 else f'{kind} {position}, a {len(value)}-character name'
        def recipient_summary(value):
            values=recipients(value, ordered=True)
            if values is None:
                if len(visible(value))>180:raise Refused('asking_input_too_large', 'This recipient list cannot be counted exactly; prepare a smaller list or use the owner click.')
                return value
            shown=[]
            for index,value in enumerate(values):
                part=bounded(value, 'recipient', index+1)
                if len(visible(','.join(shown+[part])))>180:break
                shown.append(part)
            remaining=len(values)-len(shown)
            return ','.join(shown)+(f' and {remaining} more' if remaining else '')
        if state.get('dialog') and data['input']['verb']=='dialog':
            dialog=state['dialog']
            return f"On {state['url']}, page '{bounded(state.get('title',''))}', as the page shows it, {'accept' if data['input'].get('accept') else 'dismiss'} {dialog['kind']} '{dialog['text']}' from frame {dialog['frame']}?"
        target = state.get('target', {})
        site = state.get('frame_url', state.get('url', ''))
        label = ('resume '+data['resume_kind'] if data.get('resume_kind') else target.get('name') or data['input'].get('key') or data['input']['verb'])
        action = description.get('adapter_action')
        kind=data.get('kind')
        generic={'delete':'delete', 'pay':'pay for', 'item':'unsubscribe from', 'send':'send', 'confirmation':'confirm sending', 'form':'submit', 'upload':'upload to'}.get(kind, 'activate')
        summary = f"On {site}, page '{bounded(state.get('title',''))}', as the page shows it, " + (f"{action} (control '{bounded(label)}')" if action else f"{generic} '{bounded(state.get('item') or label)}'")
        if data['input'].get('key'):summary += f" using {data['input']['key']}"
        if target.get('page_dialog'):
            summary += f" in {target['page_dialog']['kind']} '{target['page_dialog']['text']}'"
        adapter = state.get('adapter')
        if adapter:
            if payload_kind := adapter.get('target'):
                summary += f" ('{bounded(payload_kind)}')"
            if adapter.get('context'):
                summary += f" for '{bounded(adapter['context'], 'context')}'"
            if adapter.get('account'):
                summary += f" as '{bounded(adapter['account'], 'account')}'"
            if adapter.get('chat'):
                summary += f" in chat '{bounded(adapter['chat'], 'chat')}'"
            if adapter.get('to') is not None:
                summary += f" to '{recipient_summary(adapter['to'])}', Cc '{recipient_summary(adapter.get('cc',''))}', hidden Bcc '{recipient_summary(adapter.get('bcc',''))}', subject '{bounded(adapter.get('subject',''))}'"
            if adapter.get('text') is not None:
                summary += f" with {len(adapter['text'])} characters"
                if action == 'Gemini: ask a question':
                    summary += f": '{adapter['text']}'"
            if isinstance(adapter.get('attachments'), list):
                attachments = adapter['attachments']
                summary += f", {len(attachments)} attachment{'s' if len(attachments) != 1 else ''}"
                if attachments:
                    summary += ': ' + '; '.join(f"'{bounded(item.get('label', ''), 'attachment', index+1)}' ({bounded(item.get('text', ''), 'attachment details', index+1)})" for index,item in enumerate(attachments[:3])) + (f' and {len(attachments)-3} more' if len(attachments)>3 else '')
        form = state.get('form')
        if form:
            fields = form['fields']
            summary += f" to {form['action']} ({form['method']}, {len(fields)} fields, {sum(bool(field.get('hidden')) for field in fields)} hidden)"
        elif data['input']['verb'] != 'dialog':
            summary += "; where the page sends this isn't visible to the tool"
        if data.get('file'):
            summary += f" with file '{data['file']['real_path']}' ({data['file']['size']} bytes, sha256 {data['file']['sha256']})"
        selected=[file for frame in state.get('selected_files',[]) for field in frame['fields'] if not field.get('password') for file in field.get('value',[])]
        if selected:
            summary += '; selected files: '+ '; '.join(f"'{bounded(file['name'], 'file', index+1)}' ({file['size']} bytes, sha256 {file['sha256']})" for index,file in enumerate(selected[:3]))
            if len(selected)>3:summary += f' and {len(selected)-3} more (full digests below)'
        if data.get('confirmation'):
            summary += f" and confirm '{data['confirmation']['text']}'"
        return summary + '?'

    def revalidate(self, operation):
        mode = self.mode(acting=True)
        if operation['payload'].get('process_session') != self.process_session:
            raise Refused('stale_approval', 'Chrome service restarted; drop this preparation, read and prepare again.')
        site_adapter = operation['payload'].get('adapter')
        if site_adapter and not mode['adapters'].get(site_adapter['site']):
            raise Refused('stale_approval', 'The site adapter is no longer qualified; prepare again under the generic rules.')
        if self.trusted_context and not self.trusted(operation):
            raise Refused('refused', 'The owner entry no longer covers this exact kind, account and parameters; use chrome_submit to ask.')
        # The decisive fresh comparison is in the extension, immediately before input.
        if operation['payload']['binding']['session'] != self.bridge.session:
            raise Refused('stale_approval', 'Chrome session changed; read and prepare again.')
        self.check_readonly(operation['payload'])

    def check_readonly(self, payload, get=None):
        get = get or self.store.get
        state = payload['binding']
        addresses = [state['url'], state.get('effective_url') or state.get('frame_url') or state.get('dialog', {}).get('frame_url', state['url'])]
        for address in addresses:
            self.allowed_url(address)
        if state.get('form'):
            self.allowed_url(state['form']['action'])
        readonly = any(get('chrome:readonly:' + hostname(address), False) for address in addresses)
        if readonly:
            if payload.get('native_dialog') or payload.get('resume_kind'):
                raise Refused('readonly_site', 'This site is now read-only; the prepared action was refused before dispatch.')
            classify(payload['input']['verb'], payload['input'], {'target':state['target'], 'form':state.get('form')}, readonly=True)

    def has_submission_evidence(self, operation_id):
        return False

    def evidence(self, operation_id):
        operation = self.store.get('op:' + operation_id)
        return {'stages':operation.get('stages', {}) if operation else {},
                'meaning':'Only dispatched input and page observations; no network-delivery claim.'}

    def drop(self, operation):
        # No replayable traffic exists in the bridge. An unused main-world hold stays stopped.
        pass

    def repair(self, operation, which):
        raise Refused('refused', 'Chrome has no replay repair. Inspect the page with the owner; never submit again.')

    def repaired_outcome(self, operation):
        return operation['state'], operation['reason']

    def execute(self, operation, stage):
        payload = operation['payload']
        self.mode(acting=True)
        self.check_readonly(payload)
        command = self.command(payload, operation['id'], approved=True)
        path = None
        try:
            if payload.get('file'):
                from .uploads import copy_for_browser
                data, path = copy_for_browser(self, payload['file'])
                for offset in range(0,len(data),512*1024):
                    self.bridge.call('stage_file',reference=payload['reference'],token=operation['id'],offset=offset,
                                     bytes=base64.b64encode(data[offset:offset+512*1024]).decode(),file=payload['file'])
                if not data:
                    self.bridge.call('stage_file',reference=payload['reference'],token=operation['id'],offset=0,bytes='',file=payload['file'])
                command['upload'] = {'token':operation['id'],'file':payload['file']}
            reply = self.bridge.call(**command)
        except Refused as exc:
            if exc.code in {'stale_reference','stale_approval','owner_signin','refused'}:
                raise NothingLeft(str(exc)) from exc
            raise
        finally:
            from .uploads import release
            release(self, path)
        stage('checked', 'Page matched the bound approval immediately before input.')
        if reply.get('no_change'):stage('unchanged', 'The requested state was already present; no input was dispatched.')
        else:stage('dispatched', 'Input or same-kind submission dispatched once; delivery is not proven.')
        if reply.get('confirmations'):
            stage('confirmation', canonical(visible(reply['confirmations'])))
        stage('page', canonical(visible(reply)))
        self.steps(reply.get('steps', []), operation['payload']['reference']['tab'])
        if any(step['kind']=='activation_unknown' for step in reply.get('steps',[])):
            return 'unknown', 'Input ran, but a page activation may have happened; inspect the page and never replay.'
        if reply.get('dialog'):
            return 'unknown','The page is still handling input behind a dialog. Inspect and answer it separately; never replay the input.'
        if reply.get('uncertain_finish'):
            return 'unknown','Input dispatched, but a page handler completion could not be confirmed. Inspect the page and never replay.'
        if reply.get('no_change'):return 'done', 'The requested state was already present; no input was dispatched.'
        return 'done', 'Dispatched once, as the page shows it; this does not prove what the site did.'

    def command(self, payload, operation=None, approved=False):
        if payload.get('native_dialog'):
            return {'name':'dialog','tab':payload['reference']['tab'],'binding':payload['binding'],'input':payload['input'],'operation':operation}
        return {'name':'resume' if payload.get('resume_kind') else 'input',
                'reference':payload['reference'],'tab':payload['reference']['tab'],'input':payload['input'],
                'kind':payload['kind'],'conservative':payload.get('conservative',False),'adapter':bool(payload.get('adapter')),'binding':payload['binding'],
                'operation':operation,'approved':approved,'confirmation':payload.get('confirmation'),'primary_submission':bool(payload['binding'].get('form') and (payload['binding']['target'].get('submit') or payload['input'].get('verb')=='press' and payload['input'].get('key','').split('+')[-1]=='Enter' and payload['binding']['target'].get('editable'))),**({'hold':payload['hold']} if payload.get('hold') else {})}

    def payload(self, verb, args, *, hold=None):
        mode = self.mode(acting=True)
        if verb == 'press':
            args = {**args, 'key':canonical_key(args['key']), 'key_input':key_input(args['key'])}
        facts, frame = self.facts(args['reference'])
        if args.get('expected') is not None and args['expected'] != visible(frame['target']):
            raise Refused('stale_reference', 'Element no longer holds its expected state; read again.')
        readonly = any(self.store.get('chrome:readonly:' + hostname(url), False) for url in [facts['url'],frame.get('effective_url',frame['url'])])
        href=frame['target'].get('href')
        if href and not href.startswith('javascript:') and (verb=='click' or verb=='press' and args.get('key','').split('+')[-1] in {'Enter','Space'}):
            self.allowed_url(href)
        adapter = recognize(frame.get('effective_url',frame['url']), frame['adapter'], frame['target'], verb, args, self.hosts, mode['adapters'])
        kind = classify(verb,args,frame,conservative=mode['conservative'],readonly=readonly,adapter=adapter)
        if adapter and kind in {'delete', 'pay', 'item'} and kind != adapter['effect']:
            adapter = None
        if facts.get('needs_reload'):
            self.free('prepare_control', tab=args['reference']['tab'], reload_taken_tab=args.get('reload_taken_tab', False))
            raise Refused('stale_reference', 'The taken tab reloaded to install its page guard. Every old reference is stale; read again.')
        if hold:
            kind = 'form'
        state = binding(facts,args['reference'],kind,adapter)
        key = args.get('key','').split('+')[-1]
        target = frame['target']
        submitting = target.get('submit') and (verb in {'click','check','select'} or verb == 'press' and key in {'Enter','Space',' '}) or verb == 'press' and key == 'Enter' and target.get('editable')
        if state['form'] and (hold or kind or submitting):
            self.allowed_url(state['form']['action'])
        if kind == 'send' and not state['form'] and not adapter:
            fields = [field for document in state['editable'] for field in document['fields']]
            if not any(isinstance(field.get('value'),str) and field['value'] and field.get('type') not in {'checkbox','radio','select-one','select-multiple'} for field in fields):
                raise Refused('refused', "Can't tell what this sends: no editable text. Use an adapter or the owner's own click.")
        if state.get('item') is not None and len(state['item']) > 8000:
            raise Refused('asking_input_too_large', 'The affected item is too large to show whole; use a smaller item or the owner.')
        result = {'process_session':self.process_session, 'reference':args['reference'],'input':{'verb':verb,**{k:v for k,v in args.items() if k not in {'reference','expected','file','path'}}},
                  'kind':kind,'conservative':mode['conservative'],'adapter':adapter,'binding':state}
        if hold:
            result.update(hold=hold['id'],resume_kind=hold['kind'],input={'verb':'resume_submission','kind':hold['kind']})
        if verb == 'upload':
            file = args.get('file')
            if not file or self.store.get('blob:' + digest(file)) != file:
                raise Refused('proxy_required', 'Upload must import a caller-side file snapshot through the proxy.')
            self.blobs.require_origin(file['sha256'], 'caller_import')
            result['file'] = file
        return result, facts

    def free(self, verb, payload=None, **arguments):
        # Even free changes have a committed operation/context before any dispatch (R2).
        op_id = self.store.generation + ':' + uuid.uuid4().hex
        context = payload['binding'] if payload else {**arguments, **({'before':self.bridge.call('tab_context',tab=arguments['tab'])} if 'tab' in arguments else {})}
        description = {'action':'chrome_' + verb,'untrusted_content':{'page_state':context,'input':payload['input'] if payload else arguments}}
        op = {'id':op_id,'generation':self.store.generation,'app':'chrome','action':'chrome_' + verb,
              'input_hash':digest(description),'approval':{'description':visible(description)},'payload':payload or context,
              'state':'submitting','expires':0,'stages':{},'reason':'Free input may start; no replay after an interruption.'}
        self.store.write({'op:' + op_id:op},op['action'],'Chrome free-input context committed',op_id)
        self.store.checkpoint('chrome_before_dispatch')
        try:
            reply = self.bridge.call(**self.command(payload, op_id)) if payload else self.bridge.call(verb,**arguments)
            if verb=='open':
                op['payload']['created_tab']=copy.deepcopy(reply)
                op['stages']['created_tab']=copy.deepcopy(reply)
                self.store.write({'op:'+op_id:op},op['action'],'Created tab identity committed before address navigation',op_id)
                if arguments['url']!='about:blank':
                    self.bridge.call('navigate',tab=reply['tab'],url=arguments['url'])
        except Refused as exc:
            certain=exc.code in {'stale_reference','stale_approval','reload_required','owner_signin','refused','permission_denied','chrome_unavailable'}
            op.update(state='failed' if certain else 'unknown',reason=('Nothing dispatched: ' if certain else 'Input may have run: ')+str(exc))
            self.store.write({'op:'+op_id:op},op['action'],'Chrome input refused before effect' if certain else 'Chrome input outcome unknown',op_id)
            raise
        op['stages'] = {('unchanged' if reply.get('no_change') else 'dispatched'):('The requested state was already present; no input was dispatched.' if reply.get('no_change') else 'Input dispatched once; delivery not proven.'),'page':visible(reply)}
        op.update(state='done',reason='The requested state was already present; no input was dispatched.' if reply.get('no_change') else 'Free input dispatched once, as the page shows it.')
        if reply.get('cleanup_pending'):
            op.update(state='unknown',notice=True,reason='Input authority ended; native cleanup is still pending. Close the page dialog and inspect tabs before taking it again; never replay this operation.')
        followups=self.steps(reply.get('steps', []),payload['reference']['tab']) if payload else []
        if any(step['kind']=='activation_unknown' for step in reply.get('steps',[])):
            op.update(state='unknown',reason='Input ran, but a page activation may have happened; inspect the page and never replay.')
        if reply.get('dialog'):
            op.update(state='unknown',reason='The page is still handling input behind a dialog. Inspect and answer it separately; never replay the input.')
        if reply.get('uncertain_finish'):
            op.update(state='unknown',reason='Input dispatched, but a page handler completion could not be confirmed. Inspect the page and never replay.')
        self.store.write({'op:' + op_id:op},op['action'],'Chrome free input recorded',op_id)
        return {'operation_id':op_id,'untrusted_content':visible(reply),'followups':followups}

    def observe_step(self,step,tab):
        source_id=digest([self.bridge.session,tab,step]);key='intent:chrome:'+source_id
        source=self.store.get(key)
        if source is None:
            source={'id':source_id,'app':'chrome','state':'started','step':step,'tab':tab}
            self.store.write({key:source},'chrome_page_step','Page step check open',outcome='started')
        return key,source

    def steps(self, steps, tab):
        followups=[]
        for step in steps:
            key,source=self.observe_step(step,tab)
            if source['state']=='done':
                if step['kind'] in {'native_submit','submit_event'} and source.get('prepared_operation'):
                    self.bridge.call('ack_steps',tab=tab,steps=[step]);continue
                source.update(state='started',step=step,tab=tab)
                self.store.write({key:source},'chrome_page_step','Page step recheck open',outcome='started')
            facts = self.bridge.call('read',tab=tab)
            if facts.get('dialog'):
                followups.append({'pending':True,'reason':'A native dialog still blocks the step identity check; the committed check remains open.'})
                continue
            frame = next((item for item in facts['frames'] if item['frame'] == step['frame']),None)
            if not frame or not step.get('document') or frame['document']!=step['document']:
                source.update(state='done',reason='The stopped step document changed; no resumption is possible.')
                changes={}
                if step['kind']=='activation_unknown':
                    text='An activation in the previous document may have happened. Never resume it; inspect the page with the owner.'
                    changes,_=check_result(self.store,source,key,'page_activation',step,{'reason':text,'warning':text})
                self.store.write({key:source,**changes},'chrome_page_step','Stale page step result committed without dispatch')
                self.bridge.call('ack_steps',tab=tab,steps=[step])
                followups.append({'dropped':True,'reason':source['reason']})
                continue
            reference = {'session':facts['session'],'tab':tab,'frame':frame['frame'],'document':frame['document'],
                         'view':view_identity(facts),'element':step.get('submitter') or step['element']}
            if step['kind'] in {'native_submit','submit_event'}:
                payload, _ = self.payload('click',{'reference':reference},hold=step)
                prepared=self.engine.reserve('chrome','submit',payload);followups.append(prepared)
                source.update(state='done',reference=reference,prepared_operation=prepared['approval']['operation_id'])
                self.store.write({key:source},'chrome_page_step','Stopped submission preparation committed')
            else:
                source['reference'] = reference
                label=visible(step.get('label') or 'an unnamed control')
                text = f"The page activated '{label}' by itself; it may have happened. Never resume this activation." if step['kind'] == 'activation_unknown' else f"The page tried to activate '{label}' by itself; it was stopped. Act on the current control to prepare fresh asking input if wanted."
                changes, _ = check_result(self.store,source,key,'page_activation',step,{'reason':text,'warning':text,'reference':reference})
                source['state'] = 'done'
                self.store.write({key:source,**changes},'chrome_page_step','Page activation result committed',untrusted_content={'warning':text})
                followups.append({'stopped':step['kind']!='activation_unknown','unknown':step['kind']=='activation_unknown','reason':text})
            self.bridge.call('ack_steps',tab=tab,steps=[step])
        return followups

    def trusted(self, operation):
        mode = self.mode(acting=True)
        adapter = operation['payload'].get('adapter')
        payload = operation['payload']
        state = payload['binding']
        forbidden = payload.get('kind') in {'delete', 'pay'} or explicit_effect({'target':state.get('target', {}), 'form':state.get('form')}) in {'delete', 'pay'} or adapter and (adapter.get('site') == 'whatsapp' or adapter.get('effect') in {'delete', 'pay'})
        if forbidden or mode['conservative'] or not adapter or not adapter.get('trusted') or not mode['adapters'].get(adapter['site']):
            return False
        entry = self.store.get('chrome:allow:' + self.allow_id(operation), {})
        return bool(entry and entry.get('kind_hash') == digest(KINDS.get(adapter['kind'])) and not entry.get('revoked'))

    def allow_id(self, operation):
        payload = operation['payload']; adapter = payload['adapter']
        return digest([payload['binding']['frame_url'].split('/',3)[:3],adapter['account'],adapter['kind'],adapter['parameters']])

    def sites(self, args):
        command = args['command']
        if command == 'list':
            def rows():
                for prefix,kind in [('chrome:readonly:','readonly'),('chrome:allow:','allowed')]:
                    for key,value in self.store.iter_items(prefix):
                        yield ((0,key), {'kind':kind,'id':key[len(prefix):],'value':visible(value)})
                for key,op in self.store.iter_items('op:'):
                    if op['app']=='chrome' and op['state']=='done' and op['action']=='chrome_submit':
                        yield ((1,key),{'kind':'recent','operation_id':op['id'],'question':op['approval'].get('question'),
                            'eligible':bool((op['payload'].get('adapter') or {}).get('trusted'))})
            return ordered_page(rows,args,['chrome','sites']) | {'untrusted_content':True}
        if command == 'readonly':
            address = self.allowed_url(args['site']); host = hostname(address)
            self.store.write({'chrome:readonly:' + host:args.get('enabled',True)},'chrome_sites','Owner changed read-only site')
            return {'readonly':host,'enabled':args.get('enabled',True)}
        if command == 'revoke':
            key = 'chrome:allow:' + args['id']; entry = self.store.get(key)
            if not entry: raise Refused('stale_reference','Entry not found; list allowed kinds.')
            entry['revoked'] = True
            self.store.write({key:entry},'chrome_sites','Owner revoked Chrome permission')
            return {'revoked':args['id']}
        operation = self.engine.operation(args['operation_id'],'chrome')
        adapter = operation['payload'].get('adapter')
        if operation['state'] != 'done' or operation['action'] != 'chrome_submit' or not adapter or not adapter.get('trusted'):
            raise Refused('refused','Only a recently approved eligible adapter kind may be allowed; deleting, paying and WhatsApp always ask.')
        key = self.allow_id(operation)
        self.store.write({'chrome:allow:' + key:{'adapter':adapter,'kind_hash':adapter['kind_hash'],'revoked':False}},'chrome_sites','Owner allowed an exact Chrome kind')
        return {'id':key}

    def call(self, verb, args):
        if verb == 'sites': return self.sites(args)
        if verb == 'submit_trusted':
            require_question(args)
            operation = self.engine.operation(args['operation_id'],'chrome')
            if not self.trusted(operation):
                raise Refused('refused','No current owner entry covers this exact kind, account and parameters; call chrome_submit to ask.')
            # The trusted decision is checked again immediately before dispatch.
            operation['payload']['authorization']={'route':'owner_rule','entry_id':self.allow_id(operation),'kind_hash':operation['payload']['adapter']['kind_hash']}
            self.store.write({'op:' + operation['id']:operation},'chrome_submit_trusted','Trusted-kind revalidation',operation['id'])
            self.trusted_context=True
            try:
                return self.engine.submit(BY_NAME['chrome_submit'],args)
            finally:
                self.trusted_context=False
        if verb == 'notices':
            return self.notice_page(args)
        if verb in {'read','read_form','find','wait'}: return self.read(verb,args)
        if verb in {'tabs','downloads','bookmarks','history'}:
            self.mode()
            reply = self.bridge.call(verb,**args)
            return visible(reply) | {'untrusted_content':True}
        if verb == 'fill_form':
            for field in args['fields']:
                self.payload('fill',field)
            completed=[]
            for index,field in enumerate(args['fields']):
                try:
                    current=self.bridge.call('facts',reference=field['reference'])
                    frame=next(frame for frame in current['frames'] if frame['frame']==field['reference']['frame'])
                    expected={**field['expected'],'box':frame['target']['box'],'onscreen':frame['target']['onscreen']}
                    fresh={**field,'reference':{**field['reference'],'view':view_identity(current)},'expected':expected}
                    result=self.call('fill',fresh);completed.append(result)
                    if result.get('approval') or result.get('followups'):break
                except Refused as exc:
                    return {'state':'partial' if completed else 'refused','completed':completed,'next_field':index,'reason':str(exc)}
            return {'completed':completed,'remaining':len(args['fields'])-len(completed)}
        if verb in {'open','navigate','take_tab','release_tab','close_tab'}:
            self.mode(acting=True)
            if 'url' in args: self.allowed_url(args['url'])
            return self.free(verb,**args)
        if verb == 'dialog':
            mode=self.mode(acting=True)
            facts=self.bridge.call('dialog_facts',tab=args['tab'])
            if facts['dialog'] != args['expected']:
                raise Refused('stale_approval','Dialog or opener changed; read and prepare again.')
            readonly=any(self.store.get('chrome:readonly:'+hostname(url),False) for url in [facts['url'],facts['dialog']['frame_url']])
            if readonly:
                raise Refused('readonly_site','This site is read-only; the owner must answer its dialogs.')
            kind=classify('dialog',args,{'dialog':facts['dialog']},conservative=mode['conservative'])
            payload={'process_session':self.process_session,'reference':{'tab':args['tab']},'input':{'verb':'dialog',**args},'binding':facts,'kind':kind,'adapter':None,'native_dialog':True}
        else:
            payload, _ = self.payload(verb,args)
        if payload['kind']:
            return self.engine.reserve('chrome','submit',payload)
        return self.free(verb,payload)

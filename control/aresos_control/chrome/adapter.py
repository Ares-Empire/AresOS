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
from .exclusions import owner_hosts
from .policy import allowed_url, classify, HOSTS
from .qualification import Qualification, switches
from .sites import recognize, KINDS

RUNTIME = Path(__file__).resolve().parents[2]


def view_identity(facts):
    return digest([facts.get('control'),[{k: frame.get(k) for k in ['frame','document','revision','url','title','scroll','rows','editable']}
                   for frame in facts['frames']]])


def binding(facts, reference, kind, adapter):
    frame = next(frame for frame in facts['frames'] if frame['frame'] == reference['frame'])
    target = frame['target']
    keys = ['element','role','name','label','title','href','value','password','states','editable','search','submit']
    return {'session':facts['session'],'tab':facts['tab'],'control':facts.get('control'),'url':facts['url'],'document':frame['document'],
            'frame':frame['frame'],'frame_url':frame['url'],'target':{key:target[key] for key in keys if key in target},
            'form':frame.get('form'),
            'editable':[{'frame':item['frame'],'document':item['document'],'url':item['url'],'fields':item['editable']} for item in facts['frames']]
                if kind == 'send' and not frame.get('form') and not adapter else None,
            'item':frame['item'] if kind in {'delete','pay','activation','confirmation'} else None,
            'adapter':frame['adapter'] if adapter else None,'dialog':facts.get('dialog')}


class Chrome:
    app = 'chrome'

    def __init__(self, engine, build=None, record=None):
        self.engine, self.store, self.blobs = engine, engine.store, engine.blobs
        self.process_session = uuid.uuid4().hex
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
        if event.get('event') == 'released':
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
                sink(event['data'])

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
        if not self.refresh_qualification or not isinstance(self.bridge, Bridge) or not self.bridge.version:
            return
        identity = (self.bridge.session, self.bridge.version)
        uncovered = not any(item['build'] == self.qualification.build and item['version'] == self.bridge.version
                            for item in self.qualification.record()['entries'])
        force = uncovered and getattr(self, '_refresh_attempted', None) != identity
        self._refresh_attempted = identity
        self.qualification.refresh(force=force)

    def pending_state(self, operation):
        payload = operation.get('payload', {})
        state = payload.get('binding', {})
        try:
            if payload.get('process_session') != self.process_session or state.get('session') != self.bridge.session:
                raise Refused('stale_approval', 'Browser or service session changed; drop this preparation and prepare again.')
            self.mode(acting=True)
            self.check_readonly(payload)
            live = self.bridge.call('validity', reference=payload['reference'])
            if live.get('document') != state.get('document') or live.get('control') != state.get('control'):
                raise Refused('stale_approval', 'Tab control or document changed; drop and prepare again.')
            return {'validity':'current'}
        except Refused as exc:
            return {'validity':'refused', 'reason':str(exc), 'refusal_code':exc.code}

    def allowed_url(self, address):
        return allowed_url(address, self.read_owner_hosts())

    def facts(self, reference):
        self.mode()
        facts = self.bridge.call('facts', reference=reference)
        self.allowed_url(facts['url'])
        for frame in facts['frames']:
            self.allowed_url(frame['url'])
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
            self.allowed_url(frame['url'])
            if verb == 'read_form':
                reference = args['reference']
                if reference['view'] != token:
                    raise Refused('stale_reference', 'Page changed; read again.')
                if frame['frame'] != reference['frame']:
                    continue
                single = self.bridge.call('facts', reference=reference)
                selected = next(f for f in single['frames'] if f['frame'] == reference['frame'])
                return {'untrusted_content': visible({'form': selected['form']}), 'version_notice':mode['notice']}
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
                'view':token,'characters':len(tree),'offset':offset,'cursor':cursor,'version_notice':mode['notice'],**({'condition_met':condition_met} if verb=='wait' else {})}

    def prepare(self, verb, payload):
        state = payload['binding']
        description = {'action':'chrome_submit','untrusted_content':{'page_state':state,'input':payload['input'],
                       'resume_kind':payload.get('resume_kind'),'file':payload.get('file'),
                       'confirmation':payload.get('adapter', {}).get('confirmation') if payload.get('adapter') else None}}
        question = self.question(verb, description)
        return question, description, copy.deepcopy(payload)

    def question(self, verb, description):
        data = description['untrusted_content']
        state = data['page_state']
        if state.get('dialog') and data['input']['verb']=='dialog':
            dialog=state['dialog']
            return f"On {state['url']}, as the page shows it, {'accept' if data['input'].get('accept') else 'dismiss'} {dialog['kind']} '{dialog['text']}' from frame {dialog['frame']}?"
        target = state.get('target', {})
        site = state.get('frame_url', state.get('url', ''))
        label = ('resume '+data['resume_kind'] if data.get('resume_kind') else target.get('name') or data['input'].get('key') or data['input']['verb'])
        summary = f"On {site}, as the page shows it, activate '{label}'"
        adapter = state.get('adapter')
        if adapter:
            if payload_kind := adapter.get('target'):
                summary += f" ('{payload_kind}')"
            if adapter.get('context'):
                summary += f" for '{adapter['context']}'"
            if adapter.get('account'):
                summary += f" as '{adapter['account']}'"
            if adapter.get('chat'):
                summary += f" in chat '{adapter['chat']}'"
            if adapter.get('to') is not None:
                summary += f" to '{adapter['to']}', Cc '{adapter.get('cc','')}', hidden Bcc '{adapter.get('bcc','')}', subject '{adapter.get('subject','')}'"
            if adapter.get('text') is not None:
                summary += f" with {len(adapter['text'])} characters"
        form = state.get('form')
        if form:
            fields = form['fields']
            summary += f" to {form['action']} ({form['method']}, {len(fields)} fields, {sum(bool(field.get('hidden')) for field in fields)} hidden)"
        elif data['input']['verb'] != 'dialog':
            summary += "; where the page sends this isn't visible to the tool"
        if data.get('file'):
            summary += f" with file '{data['file']['real_path']}' ({data['file']['size']} bytes, sha256 {data['file']['sha256']})"
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

    def check_readonly(self, payload):
        state = payload['binding']
        addresses = [state['url'], state.get('frame_url') or state.get('dialog', {}).get('frame_url', state['url'])]
        for address in addresses:
            self.allowed_url(address)
        readonly = any(self.store.get('chrome:readonly:' + (urlsplit(address).hostname or ''), False) for address in addresses)
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
        if payload.get('file'):
            from .uploads import copy_for_browser
            data, path = copy_for_browser(self, payload['file'])
            for offset in range(0,len(data),512*1024):
                self.bridge.call('stage_file',reference=payload['reference'],token=operation['id'],offset=offset,
                                 bytes=base64.b64encode(data[offset:offset+512*1024]).decode(),file=payload['file'])
            if not data:
                self.bridge.call('stage_file',reference=payload['reference'],token=operation['id'],offset=0,bytes='',file=payload['file'])
            command['upload'] = {'token':operation['id'],'file':payload['file']}
        try:
            reply = self.bridge.call(**command)
        except Refused as exc:
            if exc.code in {'stale_reference','stale_approval','owner_signin','refused'}:
                raise NothingLeft(str(exc)) from exc
            raise
        finally:
            from .uploads import release
            release(self, path)
        stage('checked', 'Page matched the bound approval immediately before input.')
        stage('dispatched', 'Input or same-kind submission dispatched once; delivery is not proven.')
        stage('page', canonical(visible(reply)))
        self.steps(reply.get('steps', []), operation['payload']['reference']['tab'])
        return 'done', 'Dispatched once, as the page shows it; this does not prove what the site did.'

    def command(self, payload, operation=None, approved=False):
        if payload.get('native_dialog'):
            return {'name':'dialog','tab':payload['reference']['tab'],'binding':payload['binding'],'input':payload['input'],'operation':operation}
        return {'name':'resume' if payload.get('resume_kind') else 'input',
                'reference':payload['reference'],'tab':payload['reference']['tab'],'input':payload['input'],
                'kind':payload['kind'],'conservative':payload.get('conservative',False),'adapter':bool(payload.get('adapter')),'binding':payload['binding'],
                'operation':operation,'approved':approved,'primary_submission':bool(payload['binding'].get('form') and (payload['binding']['target'].get('submit') or payload['input'].get('verb')=='press' and payload['input'].get('key','').split('+')[-1]=='Enter' and payload['binding']['target'].get('editable'))),**({'hold':payload['hold']} if payload.get('hold') else {})}

    def payload(self, verb, args, *, hold=None):
        mode = self.mode(acting=True)
        facts, frame = self.facts(args['reference'])
        if args.get('expected') is not None and args['expected'] != visible(frame['target']):
            raise Refused('stale_reference', 'Element no longer holds its expected state; read again.')
        readonly = any(self.store.get('chrome:readonly:' + (urlsplit(url).hostname or ''), False) for url in [facts['url'],frame['url']])
        adapter = recognize(frame['url'], frame['adapter'], frame['target'], verb, args, self.hosts, mode['adapters'])
        kind = classify(verb,args,frame,conservative=mode['conservative'],readonly=readonly,adapter=adapter)
        if hold:
            kind = 'form'
        state = binding(facts,args['reference'],kind,adapter)
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
        context = payload['binding'] if payload else arguments
        description = {'action':'chrome_' + verb,'untrusted_content':{'page_state':context,'input':payload['input'] if payload else arguments}}
        op = {'id':op_id,'generation':self.store.generation,'app':'chrome','action':'chrome_' + verb,
              'input_hash':digest(description),'approval':{'description':visible(description)},'payload':payload or arguments,
              'state':'submitting','expires':0,'stages':{},'reason':'Free input may start; no replay after an interruption.'}
        self.store.write({'op:' + op_id:op},op['action'],'Chrome free-input context committed',op_id)
        self.store.checkpoint('chrome_before_dispatch')
        try:
            reply = self.bridge.call(**self.command(payload, op_id)) if payload else self.bridge.call(verb,**arguments)
        except Refused as exc:
            certain=exc.code in {'stale_reference','stale_approval','owner_signin','refused','permission_denied','chrome_unavailable'}
            op.update(state='failed' if certain else 'unknown',reason=('Nothing dispatched: ' if certain else 'Input may have run: ')+str(exc))
            self.store.write({'op:'+op_id:op},op['action'],'Chrome input refused before effect' if certain else 'Chrome input outcome unknown',op_id)
            raise
        op['stages'] = {'dispatched':'Input dispatched once; delivery not proven.','page':visible(reply)}
        op.update(state='done',reason='Free input dispatched once, as the page shows it.')
        followups=self.steps(reply.get('steps', []),payload['reference']['tab']) if payload else []
        self.store.write({'op:' + op_id:op},op['action'],'Chrome free input recorded',op_id)
        return {'operation_id':op_id,'untrusted_content':visible(reply),'followups':followups}

    def steps(self, steps, tab):
        followups=[]
        for step in steps:
            source_id = digest([self.bridge.session, tab, step])
            key = 'intent:chrome:' + source_id
            source = self.store.get(key, {'id':source_id,'app':'chrome'})
            source.update(state='started',step=step,tab=tab)
            self.store.write({key:source},'chrome_page_step','Page step check open',outcome='started')
            facts = self.bridge.call('read',tab=tab)
            frame = next(item for item in facts['frames'] if item['frame'] == step['frame'])
            reference = {'session':facts['session'],'tab':tab,'frame':frame['frame'],'document':frame['document'],
                         'view':view_identity(facts),'element':step.get('submitter') or step['element']}
            if step['kind'] in {'native_submit','submit_event'}:
                payload, _ = self.payload('click',{'reference':reference},hold=step)
                followups.append(self.engine.reserve('chrome','submit',payload))
                source.update(state='done',reference=reference)
                self.store.write({key:source},'chrome_page_step','Stopped submission preparation committed')
            else:
                source['reference'] = reference
                text = 'The page activated an asking control by itself; it may have happened. Never resume this activation.' if step['kind'] == 'activation_unknown' else 'The page tried to activate an asking control by itself; it was stopped. Act on the current control to prepare fresh asking input if wanted.'
                changes, _ = check_result(self.store,source,key,'page_activation',step,{'reason':text,'warning':text,'reference':reference})
                source['state'] = 'unknown' if step['kind'] == 'activation_unknown' else 'done'
                self.store.write({key:source,**changes},'chrome_page_step','Page activation result committed',untrusted_content={'warning':text})
                followups.append({'stopped':step['kind']!='activation_unknown','unknown':step['kind']=='activation_unknown','reason':text})
        return followups

    def trusted(self, operation):
        mode = self.mode(acting=True)
        adapter = operation['payload'].get('adapter')
        if mode['conservative'] or not adapter or not adapter.get('trusted') or not mode['adapters'].get(adapter['site']):
            return False
        entry = self.store.get('chrome:allow:' + self.allow_id(operation), {})
        return bool(entry and entry.get('kind_hash') == digest(KINDS.get(adapter['kind'])) and not entry.get('revoked'))

    def allow_id(self, operation):
        payload = operation['payload']; adapter = payload['adapter']
        return digest([payload['binding']['frame_url'].split('/',3)[:3],adapter['account'],adapter['kind'],adapter['parameters']])

    def sites(self, args):
        command = args['command']
        if command == 'list':
            return {'untrusted_content':{'readonly':self.store.items('chrome:readonly:'),'allowed':self.store.items('chrome:allow:'),'recent':[{'operation_id':op['id'],'question':op['approval'].get('question'),'eligible':bool(op['payload'].get('adapter',{}).get('trusted'))} for _,op in self.store.iter_items('op:') if op['app']=='chrome' and op['state']=='done' and op['action']=='chrome_submit'][-10:]}}
        if command == 'readonly':
            address = self.allowed_url(args['site']); host = urlsplit(address).hostname
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
        if verb in {'read','read_form','find','wait'}: return self.read(verb,args)
        if verb in {'tabs','downloads','bookmarks','history'}:
            self.mode()
            reply = self.bridge.call(verb,**args)
            values = reply['items']
            return ordered_page(lambda:(((index,str(index)),visible(value)) for index,value in enumerate(values)),args,['chrome',verb]) | {'untrusted_content':True}
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
            readonly=any(self.store.get('chrome:readonly:'+(urlsplit(url).hostname or ''),False) for url in [facts['url'],facts['dialog']['frame_url']])
            if readonly:
                raise Refused('readonly_site','This site is read-only; the owner must answer its dialogs.')
            kind=classify('dialog',args,{'dialog':facts['dialog']},conservative=mode['conservative'])
            payload={'process_session':self.process_session,'reference':{'tab':args['tab']},'input':{'verb':'dialog',**args},'binding':facts,'kind':kind,'adapter':None,'native_dialog':True}
        else:
            payload, _ = self.payload(verb,args)
        if payload['kind']:
            return self.engine.reserve('chrome','submit',payload)
        return self.free(verb,payload)

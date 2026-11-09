"""Chrome on the shared Adapter/Engine: prepare first, dispatch once, never replay."""
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
from .policy import allowed_url, classify, HOSTS
from .qualification import Qualification, switches
from .sites import recognize, KINDS

RUNTIME = Path(__file__).resolve().parents[2]


def view_identity(facts):
    return digest([{k: frame.get(k) for k in ['frame','document','revision','url','title','scroll','rows','editable']}
                   for frame in facts['frames']])


def binding(facts, reference, kind, adapter):
    frame = next(frame for frame in facts['frames'] if frame['frame'] == reference['frame'])
    target = frame['target']
    keys = ['element','role','name','label','title','href','value','password','states','editable','search','submit']
    return {'session':facts['session'],'tab':facts['tab'],'url':facts['url'],'document':frame['document'],
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
        self.bridge = Bridge()
        self.hosts = HOSTS
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

    def mode(self, acting=False):
        if not self.bridge.version:
            raise Refused('chrome_unavailable', 'Chrome is not connected; start normal Chrome with the installed extension.')
        mode = switches(self.qualification.record(), self.qualification.build, self.bridge.version)
        groups = ['classification','page_script','binding'] if acting else ['password_exclusion']
        for group in groups:
            if not mode['core'][group]:
                raise Refused('qualification_failed', f'Chrome {self.bridge.version}: {group} failed qualification; this action is off until fixed.')
        return mode

    def facts(self, reference):
        self.mode()
        facts = self.bridge.call('facts', reference=reference)
        allowed_url(facts['url'])
        for frame in facts['frames']:
            allowed_url(frame['url'])
        if reference.get('view') and view_identity(facts) != reference['view']:
            raise Refused('stale_reference', 'Page changed; read again before acting.')
        frame = next((frame for frame in facts['frames'] if frame['frame'] == reference['frame']), None)
        if frame is None or frame['document'] != reference['document'] or not frame.get('target'):
            raise Refused('stale_reference', 'Document, frame or element changed; read again.')
        return facts, frame

    def read(self, verb, args):
        mode = self.mode()
        facts = self.bridge.call('read', tab=args['tab'])
        token = view_identity(facts)
        if verb == 'wait':
            deadline = time.monotonic() + args.get('timeout_ms', 1000) / 1000
            while args.get('text') and args['text'] not in canonical(facts) and time.monotonic() < deadline:
                time.sleep(.05)
                facts = self.bridge.call('read', tab=args['tab'])
                token = view_identity(facts)
        rows = []
        for frame in facts['frames']:
            allowed_url(frame['url'])
            if verb == 'read_form':
                reference = args['reference']
                if reference['view'] != token:
                    raise Refused('stale_reference', 'Page changed; read again.')
                if frame['frame'] != reference['frame']:
                    continue
                single = self.bridge.call('facts', reference=reference)
                selected = next(f for f in single['frames'] if f['frame'] == reference['frame'])
                return {'untrusted_content': {'form': selected['form']}, 'version_notice':mode['notice']}
            for row in frame['rows']:
                if verb == 'find' and args['text'].casefold() not in canonical(row).casefold():
                    continue
                reference = {'session':facts['session'],'tab':facts['tab'],'frame':frame['frame'],'document':frame['document'],'view':token,'element':row['element']}
                rows.append({'reference':reference,'expected':{k:v for k,v in row.items() if k != 'text'},'text':row.get('text','')})
        lines = [canonical(row) for row in rows]
        tree = '\n'.join(lines) or '(empty readable page)'
        offset, end, cursor, status = fragment_window(token, len(tree), args.get('cursor'), 16000)
        # Unlike catalogue paging, a page-view cursor must never silently restart.
        if status:
            raise Refused('stale_reference', 'Page changed; read again without the cursor.')
        return {'tab':facts['tab'],'document':[(frame['frame'],frame['document']) for frame in facts['frames']],
                'untrusted_content':{'url':facts['url'],'title':facts['title'],'tree':tree[offset:end]},
                'view':token,'characters':len(tree),'offset':offset,'cursor':cursor,'version_notice':mode['notice']}

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
        target = state.get('target', {})
        site = state.get('frame_url', state.get('url', ''))
        label = target.get('name') or data['input'].get('key') or data['input']['verb']
        summary = f"On {site}, as the page shows it, activate '{label}'"
        adapter = state.get('adapter')
        if adapter:
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
        site_adapter = operation['payload'].get('adapter')
        if site_adapter and not mode['adapters'].get(site_adapter['site']):
            raise Refused('stale_approval', 'The site adapter is no longer qualified; prepare again under the generic rules.')
        if operation['payload'].get('trusted') and not self.trusted(operation):
            raise Refused('refused', 'The owner entry no longer covers this exact kind, account and parameters; use chrome_submit to ask.')
        # The decisive fresh comparison is in the extension, immediately before input.
        if operation['payload']['binding']['session'] != self.bridge.session:
            raise Refused('stale_approval', 'Chrome session changed; read and prepare again.')

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
        command = self.command(payload, operation['id'])
        try:
            reply = self.bridge.call(**command)
        except Refused as exc:
            if exc.code in {'stale_reference','stale_approval','owner_signin','refused'}:
                raise NothingLeft(str(exc)) from exc
            raise
        stage('checked', 'Page matched the bound approval immediately before input.')
        stage('dispatched', 'Input or same-kind submission dispatched once; delivery is not proven.')
        stage('page', canonical(visible(reply)))
        self.steps(reply.get('steps', []), operation['payload']['reference']['tab'])
        return 'done', 'Dispatched once, as the page shows it; this does not prove what the site did.'

    def command(self, payload, operation=None):
        return {'name':'resume' if payload.get('resume_kind') else 'input',
                'reference':payload['reference'],'tab':payload['reference']['tab'],'input':payload['input'],
                'kind':payload['kind'],'adapter':bool(payload.get('adapter')),'binding':payload['binding'],
                'operation':operation,**({'hold':payload['hold']} if payload.get('hold') else {})}

    def payload(self, verb, args, *, hold=None):
        mode = self.mode(acting=True)
        facts, frame = self.facts(args['reference'])
        if args.get('expected') is not None and args['expected'] != frame['target']:
            raise Refused('stale_reference', 'Element no longer holds its expected state; read again.')
        readonly = self.store.get('chrome:readonly:' + (urlsplit(frame['url']).hostname or ''), False)
        adapter = recognize(frame['url'], frame['adapter'], frame['target'], verb, args, self.hosts, mode['adapters'])
        kind = classify(verb,args,frame,conservative=mode['conservative'],readonly=readonly,adapter=adapter)
        if hold:
            kind = 'form'
        state = binding(facts,args['reference'],kind,adapter)
        if kind == 'send' and not state['form'] and not adapter:
            fields = [field for document in state['editable'] for field in document['fields']]
            if not any(isinstance(field.get('value'),str) and field['value'] for field in fields):
                raise Refused('refused', "Can't tell what this sends: no editable text. Use an adapter or the owner's own click.")
        if state.get('item') is not None and len(state['item']) > 8000:
            raise Refused('asking_input_too_large', 'The affected item is too large to show whole; use a smaller item or the owner.')
        result = {'reference':args['reference'],'input':{'verb':verb,**{k:v for k,v in args.items() if k not in {'reference','expected','file','path'}}},
                  'kind':kind,'adapter':adapter,'binding':state}
        if hold:
            result.update(hold=hold['id'],resume_kind=hold['kind'])
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
        reply = self.bridge.call(**self.command(payload, op_id)) if payload else self.bridge.call(verb,**arguments)
        op['stages'] = {'dispatched':'Input dispatched once; delivery not proven.','page':visible(reply)}
        op.update(state='done',reason='Free input dispatched once, as the page shows it.')
        if payload:
            self.steps(reply.get('steps', []),payload['reference']['tab'])
        self.store.write({'op:' + op_id:op},op['action'],'Chrome free input recorded',op_id)
        return {'operation_id':op_id,'untrusted_content':visible(reply)}

    def steps(self, steps, tab):
        for step in steps:
            facts = self.bridge.call('read',tab=tab)
            frame = next(item for item in facts['frames'] if item['frame'] == step['frame'])
            reference = {'session':facts['session'],'tab':tab,'frame':frame['frame'],'document':frame['document'],
                         'view':view_identity(facts),'element':step.get('submitter') or step['element']}
            if step['kind'] in {'native_submit','submit_event'}:
                payload, _ = self.payload('click',{'reference':reference},hold=step)
                self.engine.reserve('chrome','submit',payload)
            else:
                # A warning-producing postcheck stays open until its result commits.
                source = {'id':uuid.uuid4().hex,'app':'chrome','state':'started','step':step,'reference':reference}
                key = 'intent:chrome:' + source['id']
                self.store.write({key:source},'chrome_page_step','Page activation check open',outcome='started')
                text = 'The page activated an asking control by itself; it may have happened. Never resume this activation.' if step['kind'] == 'activation_unknown' else 'The page tried to activate an asking control by itself; it was stopped. Act on the current control to prepare fresh asking input if wanted.'
                changes, _ = check_result(self.store,source,key,'page_activation',step,{'reason':text,'warning':text,'reference':reference})
                source['state'] = 'unknown' if step['kind'] == 'activation_unknown' else 'done'
                self.store.write({key:source,**changes},'chrome_page_step','Page activation result committed',untrusted_content={'warning':text})

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
            return {'untrusted_content':{'readonly':self.store.items('chrome:readonly:'),'allowed':self.store.items('chrome:allow:')}}
        if command == 'readonly':
            address = allowed_url(args['site']); host = urlsplit(address).hostname
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
            operation['payload']['trusted'] = True
            self.store.write({'op:' + operation['id']:operation},'chrome_submit_trusted','Trusted-kind revalidation',operation['id'])
            return self.engine.submit(BY_NAME['chrome_submit'],args)
        if verb in {'read','read_form','find','wait'}: return self.read(verb,args)
        if verb in {'tabs','downloads','bookmarks','history'}:
            self.mode()
            reply = self.bridge.call(verb,**args)
            values = reply['items']
            return ordered_page(lambda:(((index,str(index)),visible(value)) for index,value in enumerate(values)),args,['chrome',verb]) | {'untrusted_content':True}
        if verb == 'fill_form':
            completed = []
            for field in args['fields']:
                result = self.call('fill',field)
                completed.append(result)
                if 'approval' in result: break
            return {'completed':completed}
        if verb in {'open','navigate','take_tab','release_tab','close_tab'}:
            self.mode(acting=True)
            if 'url' in args: allowed_url(args['url'])
            return self.free(verb,**args)
        payload, _ = self.payload(verb,args)
        if payload['kind']:
            return self.engine.reserve('chrome','submit',payload)
        return self.free(verb,payload)

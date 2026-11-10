"""Browser-free review mutations, in a disposable copy inside this worktree."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'.work/20-review-mutations';WORK.mkdir(parents=True,exist_ok=True)
CASES=[]
def case(item,file,before,after,test,python=False,extra=()):
    CASES.append(dict(item=item,edits=[(file,before,after),*extra],test=test,python=python))
P='control/aresos_control/chrome/policy.py'
A='control/aresos_control/chrome/adapter.py'
B='control/chrome/extension/background.js'
G='control/chrome/extension/guard.js'
R='control/chrome/extension/reader.js'
M='control/chrome/extension/page.js'
def node(file,pattern):return [file,pattern]
case('P1',B,'const armed=await armDialog(tab,command.conservative);','const armed={owner:controlled.get(tab),nonce:"unarmed",frames:[]};armed.owner.hold={};',node('background','P1|answering a dialog collects'))
case('P1-boundary',B,'source.state.dialogBarrier={nonce,token:entry.token,documents,source,resolve,reject,ready};','',node('background','answering a dialog collects'))
case('P1-window-return',M,"finally{report(target,{kind:'dialog_end',token,dialog_kind:name});}",'finally{}',node('page','P1 native dialog return values'))
case('P1-auth',B,"if(boundary.result.value.token!==barrier.token)",'if(false)',node('background','P1 only the authenticated'))
case('P1-conservative',A,"'operation':operation,'conservative':payload.get('conservative',False)","'operation':operation",'test_questions.Questions.test_p1_native_answer_keeps_the_service_conservative_policy',True)
case('P1-cross-site-target',B,"const source=documents.find(value=>value.doc.document===entry?.document);","const source=documents.find(value=>value.doc.document===entry?.document&&!value.state.source?.sessionId);",node('background','P1 a cross-site dialog'))
case('P1-coverage',B,'const documents=frames.map(frame=>candidates.find(value=>value.doc.document===privacyDocuments.get(frame.documentId)));','const documents=candidates;',node('background','answering a dialog collects'))
case('P1-ready',B,'privacyDocuments.set(sender.documentId,message.document);','',node('background','P1 native document registration'))
case('P1-existing-allowance',B,'(!existing.hasAllowance||approvedConfirmation)','true',node('background','P1 an existing modal hold'))
case('P1-existing-proof',B,'documents.every(value=>value.doc.activeNonce===existing.nonce)','true',node('background','P1 an existing modal hold'))
case('P1-borrowed-asks',A,"kind='confirmation'","kind=None",'test_questions.Questions.test_p1_decided_borrowed_dialog_always_asks_binds_answer_and_never_trusts',True)
case('P1-borrowed-warning',A,"This dialog used a native function outside the page guard; its continuation isn't held.",'Continuation approved.','test_questions.Questions.test_p1_decided_borrowed_dialog_always_asks_binds_answer_and_never_trusts',True)
case('P1-borrowed-trust',A,"if payload.get('unguarded_dialog'):",'if False:','test_questions.Questions.test_p1_borrowed_dialog_never_inherits_an_otherwise_valid_owner_entry',True)
case('P1-borrowed-answer',B,"answer:{accept:command.input.accept,...(command.input.text===undefined?{}:{text:command.input.text})}",'answer:command.binding.answer',node('background','P1 decided borrowed dialog refuses'))
case('P1-borrowed-approval',B,"if(command.approved!==true||!command.operation)",'if(false)',node('background','P1 decided borrowed dialog refuses'))
case('P1-borrowed-once',B,"used.add(command.operation);\n      const owner=controlled.get(tab),prior=owner.hold", "const owner=controlled.get(tab),prior=owner.hold",node('background','P1 an uncertain borrowed'))
case('P1-borrowed-origin',B,"if(!native||native.kind!==dialog.kind||native.document!==privacyDocuments.get(dialog.browser_document))dialog.unguarded=true;",'',node('background','P1 native opening metadata'))
case('P1-borrowed-matched',B,'const matched=!dialog.unguarded&&confirmationPlans','const matched=confirmationPlans',node('background','a stale approved dialog opening'))
case('P1-borrowed-prior-hold',B,'if(completion){const result=await Promise.race','if(false){const result=await Promise.race',node('background','P1 a borrowed answer preserves'))
case('P1-preexisting-bound',B,"if(!preloadTargets.get(targetKey({tabId:tab}))?.pageEnabled)resolve({owner_dialog:true});",'if(false)resolve({owner_dialog:true});',node('background','P1 preexisting modal handoff'))
case('P1-preexisting-detach',B,'await chrome.debugger.detach({tabId:tab});return;','return;',node('background','P1 preexisting modal handoff'))
case('P1-preexisting-retain',B,'if(previous.modalHandoff)return;','',node('background','P1 preexisting modal handoff'))
case('P1-preexisting-recover',B,"if(owner.modalHandoff){await recoverOwnerDialog(tab,owner);if(owner.modalHandoff)throw Error('owner_dialog: '+ownerDialogMessage);}",'',node('background','P1 preexisting modal handoff'))
case('P1-preexisting-slow',B,'if(!preloadTargets.get(targetKey({tabId:tab}))?.pageEnabled)resolve({owner_dialog:true});','if(true)resolve({owner_dialog:true});',node('background','P1 a responding Page domain'))
case('P2',B,'let effective;try { effective=frameAddress(frame,frames);','if(frame.url.startsWith("about:"))continue;let effective;try { effective=frameAddress(frame,frames);',node('background','P2'))
case('P3-inherit',B,'if(hold&&(hold.inFlight||Date.now()<hold.until)){','if(false){',node('background','P3 startup'))
case('P3-paused-task',B,"if(armed.exceptionDetails)throw Error('refused: new frame could not inherit the active hold');", "if(!hold.inFlight)await targetCommand(state,'Runtime.evaluate',{contextId:context.id,expression:'globalThis[Symbol.for(\"aresos.chrome.guard.v2\")].finish('+JSON.stringify(state.epoch)+','+JSON.stringify(hold.nonce)+')',awaitPromise:true});if(armed.exceptionDetails)throw Error('refused: new frame could not inherit the active hold');",node('background','P3 a remaining hold'))
case('P3-coverage',B,'if(armed.some(frame=>frame.frame===added.frame&&frame.document===added.document))continue;','if(true)continue;',node('background','P3 a frame'))
case('P4',M,'return owner===ownDocument||!!(defaultView?invoke(defaultView,owner,[]):owner.defaultView);','return owner===ownDocument;',node('page','P4'))
case('P5',M,"report(result,{kind:'watch_root'});",'',node('page','P5 new roots'))
case('P5-composed',M,'[options({composed:true})]','[options({composed:false})]',node('page','P5 composed root'))
case('P5-native-shadow-identity',M,"property(detail,'target_path',path,true);",'',node('page','P5 native shadow identity'))
case('P5-isolated-node',G,"for(const part of stage.detail.target_path?.split('.')||[])",'for(const part of [])',node('page','P5 native shadow identity'))
case('P6',P,"base_key in {'Delete', 'Backspace'}","key in {'Delete', 'Backspace'}",'test_policy.ReviewClassification.test_p6_equivalent_keys_classify_the_dispatched_tuple',True)
case('P6-adapter','control/aresos_control/chrome/sites.py',"if base_key == '#' and scoped","if key == '#' and scoped",'test_sites.SiteSemantics.test_p6_gmail_hash_shortcut_canonicalizes_modifiers_before_classification',True)
case('P7',G,re.search(r'function decoded\(value\) \{[^\n]+', (ROOT/G).read_text())[0],"function decoded(value) {try{return decodeURIComponent(value)}catch{return value}}",node('page','P7'))
case('P8',P,"unicodedata.normalize('NFC', text)",'text','test_policy.ReviewClassification.test_p7_tolerant_url_decoding_and_p8_canonical_unicode',True)
case('P8-guard',G,"value.normalize('NFC')",'value',node('page','P8'))
case('P9-classification',P,"if evidence in {'delete', 'pay', 'item'}:","if False:",'test_policy.ReviewClassification.test_p9_explicit_payment_and_deletion_override_adapter',True)
case('P9-trusted',A,"if forbidden or mode['conservative']","if mode['conservative']",'test_questions.Questions.test_p9_trusted_predicate_independently_forbids_explicit_deletion_payment_and_whatsapp',True)
case('P10',R,'[role=listitem],[role=row],[role=article],section[aria-label],section[aria-labelledby],','',node('reader','P10'))
case('P11',A,"if kind in {'send', 'confirmation'} and not frame.get('form') and not adapter else None","if kind == 'send' and not frame.get('form') and not adapter else None",'test_questions.Questions.test_p11_confirmation_binds_a_sibling_draft',True)
case('P12',R,"fileIdentities.set(file,{identity:randomToken()})","fileIdentities.set(file,{identity:file.name})",node('reader','P12'))
case('P12-hash',R,"return hash.map(value=>value.toString(16).padStart(8,'0')).join('');","return '0'.repeat(64);",node('reader','P12 HTTP'))
case('P12-rehash',R,'const identity=fileIdentity(file);','const identity=fileIdentity(file);if(identity.sha256)continue;',node('reader','P12 every binding rehashes'))
case('P12-race',R,'if(!unchanged())','if(false)',node('reader','P12 a selection changed'))
case('P12-binding',A,"'fields':item.get('selected_files',[])","'fields':[]",'test_questions.Questions.test_p12_owner_selected_file_question_shows_name_size_and_bound_digest',True)
case('P13',R,"value = editableText(element).replace(/\\n$/, '');","value = text(element);",node('reader','P13'))
case('P14',P,"ITEM = {'unsubscribe', 'abbestellen'}","ITEM = set()",'test_policy.ReviewClassification.test_p14_unsubscribe_binds_item_without_a_draft',True)
case('P15',R,"element.getAttribute('alt') || buttonValue ||","element.getAttribute('alt') || element.getAttribute('title') || buttonValue ||",node('reader','P15'))
case('P16',R,"element.hasAttribute('srcdoc') ? 'about:srcdoc'","element.srcdoc ? 'about:srcdoc'",node('reader','P16'))
case('P17',R,'const {protectedFields,fileIdentities}=privacy;','const protectedFields=new WeakSet(),fileIdentities=privacy.fileIdentities;',node('reader','P17'))
case('P17-before-getter',R,"if(message.expected_document&&message.expected_document!==documentId)","if(false)",node('reader','P17 lost-history identity'))
case('P17-private-expectation',B,"...(privacyDocuments.has(frame.documentId)?{expected_document:privacyDocuments.get(frame.documentId)}:{})","...{}",node('background','P17 expected privacy identity'))
case('P2-native-frame',B,"const origins=authenticated.length===1?authenticated:inherited?[]:frames.filter(frame=>frame.url===params.url);","const origins=frames.filter(frame=>frame.url===params.url);",node('background','P2 native'))
case('P2-native-readonly',A,"facts.get('effective_url',facts['dialog']['frame_url'])","facts['dialog']['frame_url']",'test_questions.Questions.test_p2_inline_native_dialog_uses_authenticated_inherited_readonly_host',True)
case('P2-before-getter',R,"if(message.expected_origin&&message.expected_origin!==globalThis.origin)","if(false)",node('reader','P2 inherited origin'))
case('P18-descendants',R,'node=node.parentElement||node.getRootNode?.().host','node=null',node('reader','P18'))
case('P18-sticky',R,'if(protectedFields.has(element))return true;','if(false)return true;',node('reader','P18'))
case('P19',B,"await targetCommand(state,'Page.enable');","await targetCommand(state,'Page.enable');await targetCommand(state,'Runtime.enable');",node('background','startup evaluates only fixed bundles'),extra=[('control/chrome/extension/policy.js','"Runtime.evaluate"','"Runtime.enable", "Runtime.evaluate"')])
case('P19-root-context',B,'if(params.frame.id===state.frameId){','if(false){',node('background','P19 root navigation'))
case('P19-context-generation',B,"(state.contextGeneration?'-navigation-'+state.contextGeneration:'')","''",node('background','P19 a cancelled startup'))
case('P19-context-check',B,"const documentCommand=async(method,parameters)=>{if(!sameDocument())throw Error('stale_reference: document changed during startup');const value=await targetCommand(state,method,parameters);if(!sameDocument())throw Error('stale_reference: document changed during startup');return value;};","const documentCommand=(method,parameters)=>targetCommand(state,method,parameters);",node('background','P19 a cancelled startup'))
case('P20-form',G,'||owner.form!==form','',node('page','P20 synchronous'))
case('P20-submitter',G,'||owner.submitter!==(submitter||null)','',node('page','P20 synchronous'))
case('P20-trust',G,'if(!event.isTrusted||inFlight)return;','if(inFlight)return;',node('page','P20 an untrusted'),extra=[(G,'||!owner.event.isTrusted','')])
case('P20-clear',G,'if(owner?.token===event.data)owner=null;','',node('page','P20 an unconsumed'))
case('P21',P,"if form and form.get('search') and form.get('method', '').lower() == 'get':","if False and form and form.get('search') and form.get('method', '').lower() == 'get':",'test_policy.ReviewClassification.test_p21_get_search_form_enter_in_ordinary_input',True)
case('P22-title-action',A,"'title':facts.get('title', '')","'title':''",'test_questions.Questions.test_p22_delete_question_names_the_action_key_item_and_bound_title',True)
case('P22-action',A,"'delete':'delete'","'delete':'activate'",'test_questions.Questions.test_p22_delete_question_names_the_action_key_item_and_bound_title',True)
case('P22-bounds',A,'return value if len(visible(value))<=120 else','return value if True else','test_questions.Questions.test_p22_many_recipients_and_long_names_are_bounded_without_losing_full_values',True)
case('P23',B,'page:await observation(tab,reference)',"page:'Input dispatched once'",node('background','P23'))
case('P23-borrowed-dialog',B,'page:await observation(tab)}',"page:{available:true,url:current.url,notice:'Native answer dispatched'}}",node('background','P23 a borrowed dialog result'))
case('P24-last-check',B,'if(requireClean){','if(false){',node('background','P24'))
case('P24-audible',B,'playing=!!nativeTab.audible','playing=false',node('background','P24'),extra=[(B,"playing=!!(await chrome.tabs.get(tab)).audible","playing=false")])
case('P24-uncovered',B,'unsaved=!!current.uncovered?.length','unsaved=false',node('background','P24 uncovered'))
case('P24-unreadable',B,'catch{unsaved=true;}','catch{}',node('background','P24 uncovered'))
case('P24-designmode',R,"document.designMode?.toLowerCase()==='on'",'false',node('reader','P24 document'))
case('P25',B,"if(needsNative){","if(command.name==='input'){",node('background','P25'))
case('P25-report',B,'dispatched:!noChange,no_change:noChange','dispatched:true,no_change:false',node('background','P25'))
case('P26',M,'const value=({method(...args){return invoke(implementation,this,args);}}).method;','const value=implementation;',node('page','P26'))
case('P27',B,'const tabIds = [...controlled.keys()];','const tabIds = [...controlled.keys(),...releasing.keys()];',node('background','P27'))
case('P27-missing-context',B,"const gone=String(error).includes('Cannot find context with specified id');",'const gone=false;',node('background','P27 native missing-context'))
case('P27-unknown-context',B,"const gone=String(error).includes('Cannot find context with specified id');",'const gone=true;',node('background','P27 native missing-context'))
case('P28',B,'owner.uncertainFinish=await finishFrames(tab,armed,dispatchEpoch,inputNonce);','owner.uncertainFinish=false;',node('background','P28'))
V='control/chrome/ci/verdicts.mjs'
case('P29',V,'export function assertComplete(results,qualified){','export function assertComplete(results,qualified){return;',node('verdicts','P29'))
case('P30', 'control/chrome/ci/ingress-scan.mjs',"const result=[];let pending=null;","return text.split('\\n').filter(Boolean).map(JSON.parse);const result=[];let pending=null;",node('ingress-scan','P30'))
case('P30-getters','control/chrome/ci/password-ingress.js','get(){return emit(key,get.call(this));}','get(){return get.call(this);}',node('password-ingress','P30'))
case('P30-null-ingress','control/chrome/ci/ingress-scan.mjs','rows.filter(row=>row?.protocol_event)','rows.filter(row=>row.protocol_event)',node('ingress-scan','P30 protocol'))
case('P31-popup',B,'popupNeedsReload:true','popupNeedsReload:false',node('background','P31'))
F='control/chrome/ci/fixture.mjs'
case('P31-http',F,"else if(kind==='adapter-sites')","if(kind==='adapter-sites')",node('fixture','review pages reach'))
case('P31-head',F,'globalThis.firstScriptSubmit=HTMLFormElement.prototype.submit;','',node('fixture','P31 first script'))
case('P31-get-case',F,'target="_blank"><input type="hidden" name="case" value="\'+id+\'"><input type="search"','target="_blank"><input type="search"',node('fixture','P31 first script'))

def command(row):
    if row['python']:return ['python3','-B','-m','unittest',row['test'],'-v']
    file,pattern=row['test']
    return ['node','--test','--test-name-pattern',pattern,f'control/chrome_tests/{file}.test.mjs']

def run():
    records=[]
    with tempfile.TemporaryDirectory(dir=WORK) as temporary:
        target=Path(temporary)
        shutil.copytree(ROOT/'control',target/'control',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (target/'.work/20-chrome').mkdir(parents=True)
        environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(target/'control')+':'+str(target/'control/chrome_tests')}
        baselines={}
        for row in CASES:
            key=tuple(command(row))
            if key not in baselines:
                original=subprocess.run(key,cwd=target,env=environment,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
                if original.returncode:raise RuntimeError('Baseline failed '+row['item']+'\n'+original.stdout)
                baselines[key]=True
            originals={}
            try:
                for file,before,after in row['edits']:
                    path=target/file
                    source=path.read_text();originals.setdefault(path,source)
                    if before not in source:raise RuntimeError('Mutation does not apply '+row['item']+' '+file)
                    path.write_text(source.replace(before,after,1))
                changed=subprocess.run(key,cwd=target,env=environment,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
                killed=changed.returncode!=0 and ('AssertionError' in changed.stdout or 'FAIL:' in changed.stdout or 'not ok' in changed.stdout or '✖' in changed.stdout)
                records.append({'item':row['item'],'baseline':'pass','mutation_failed':killed,'command':list(key),'output':changed.stdout.replace(str(target),'<mutation-worktree>')})
                print(row['item'], 'MUTATION REJECTED' if killed else 'SURVIVED',flush=True)
                if not killed:raise RuntimeError('Mutation survived '+row['item']+'\n'+changed.stdout)
            finally:
                for path,source in originals.items():path.write_text(source)
        output=ROOT/'reviews/20-chrome/records/review-fixes-mutations.json';output.write_text(json.dumps(records,indent=2)+'\n')
    print(f'{len(records)} mutations rejected; every baseline passed',flush=True)

if __name__=='__main__':run()

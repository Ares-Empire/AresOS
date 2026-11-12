import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.policy import classify, WORDS, allowed_url, FIXED_HOSTS, CDP_METHODS
from aresos_control.chrome.qualification import switches, append_only
from aresos_control.common import Refused
from aresos_control.definitions import ACTIONS
from aresos_control.boundary_policy import asking_rules


def entry(build='a'*64, version='157.0.1.0', channel='stable', **changes):
    return {'build':build,'version':version,'channel':channel,'run':'fixture',
            'core':dict.fromkeys(['classification','page_script','binding','password_exclusion'],True),
            'adapters':dict.fromkeys(['gmail','whatsapp','github','bank','gemini','deezer'],True),**changes}


class Policy(unittest.TestCase):
    def test_group1_words_whole_words_all_labels_and_activation_paths(self):
        for word in WORDS:
            for label in ['name','label','title','value','role']:
                for verb,args in [('click',{}),('press',{'key':'Enter'}),('press',{'key':'Space'})]:
                    with self.subTest(word=word,label=label,verb=verb,args=args):
                        self.assertIsNotNone(classify(verb,args,{'target':{label:word}}))
            self.assertIsNone(classify('click',{}, {'target':{'name':'x'+word+'x'}}))
        for verb in ['fill','select','check']:
            self.assertIsNone(classify(verb,{}, {'target':{'editable':True,'name':'Message'}}))
        for key in ['Enter','Ctrl+Enter','Cmd+Enter']:
            self.assertEqual(classify('press',{'key':key},{'target':{'editable':True}}),'send')
        for key in ['Delete','Backspace']:
            self.assertEqual(classify('press',{'key':key},{'target':{}}),'delete')
            self.assertIsNone(classify('press',{'key':key},{'target':{'editable':True}}))
        self.assertEqual(classify('click',{}, {'target':{'submit':True},'form':{'method':'post'}}),'form')
        self.assertIsNone(classify('click',{}, {'target':{'submit':True},'form':{'search':True,'method':'get'}}))

    def test_group6_schemes_and_shipped_fixed_hosts(self):
        for scheme in ['javascript','data','blob','file','filesystem','view-source','chrome','chrome-extension','devtools','intent','mailto','tel']:
            with self.assertRaises(Refused): allowed_url(scheme+':anything')
        for host in FIXED_HOSTS:
            for prefix in ['', 'sub.']:
                with self.assertRaises(Refused): allowed_url('https://'+prefix+host+'/')
        for url in ['http://localhost/','https://fixture.test/','about:blank']:
            self.assertEqual(allowed_url(url),url)
        self.assertEqual({method for method in CDP_METHODS if method.startswith('Runtime.')},
                         {'Runtime.evaluate','Runtime.callFunctionOn','Runtime.runIfWaitingForDebugger'})
        self.assertNotIn('Debugger.evaluateOnCallFrame', CDP_METHODS)
        self.assertNotIn('Runtime.getProperties', CDP_METHODS)
        self.assertFalse(any(name.startswith(('Network.','Fetch.','Accessibility.','DOMSnapshot.')) for name in CDP_METHODS))

    def test_qualification_failure_patch_beta_build_and_conservative_rules(self):
        record={'format':1,'entries':[entry()]}
        self.assertFalse(switches(record,'a'*64,'157.0.2.0')['conservative'])
        self.assertTrue(switches(record,'b'*64,'157.0.2.0')['conservative'])
        failure=entry(version='158.0.2.0',channel='beta'); failure['core']['binding']=False; failure['adapters']['gmail']=False
        record['entries'].append(failure)
        self.assertFalse(switches(record,'a'*64,'158.0.3.0')['core']['binding'])
        record['entries'].append(entry(version='158.0.4.0'))
        self.assertTrue(switches(record,'a'*64,'158.0.4.0')['core']['binding'])
        mode=switches(record,'a'*64,'159.0.1.0'); self.assertTrue(mode['conservative']); self.assertTrue(mode['notice'])
        for verb,args,target in [('click',{}, {'href':'https://fixture.test/'}),('check',{},{}),('select',{},{}),('press',{'key':'Enter'},{}),('press',{'key':'Space'},{})]:
            self.assertIsNotNone(classify(verb,args,{'target':target},conservative=True))
        for verb in ['fill','scroll']:
            self.assertIsNone(classify(verb,{}, {'target':{}},conservative=True))
        for verb in ['fill','click','upload','check','select','press']:
            with self.assertRaises(Refused): classify(verb,{}, {'target':{}},readonly=True,conservative=True)

    def test_qualification_delivery_append_only_and_wrong_build(self):
        held={'format':1,'entries':[entry()]}
        newer=copy.deepcopy(held); newer['entries'].append(entry(version='158.0.1.0',channel='beta'))
        self.assertEqual(append_only(held,newer),newer)
        self.assertFalse(switches(newer,'a'*64,'158.0.2.0')['conservative'])
        for candidate in [{'format':1,'entries':[]},copy.deepcopy(newer)]:
            if candidate['entries']: candidate['entries'][0]['run']='altered'
            with self.assertRaises(Refused): append_only(held,candidate)

    def test_ask_rules_and_complete_catalogue(self):
        self.assertIn('mcp__chrome__submit',asking_rules())
        self.assertNotIn('mcp__chrome__submit_trusted',asking_rules())
        expected='tabs take_tab release_tab open close_tab read read_form find navigate click fill fill_form select check press scroll dialog upload downloads bookmarks history wait submit submit_trusted drop operation_status sites'.split()
        self.assertTrue(set(expected)<={action.verb for action in ACTIONS if action.app=='chrome'})
        self.assertTrue(all(action.asks for action in ACTIONS if action.effect in {'send','delete'} and action.name!='chrome_submit_trusted'))


if __name__=='__main__': unittest.main()

class Conservative(Policy):
    def test_conservative_preserves_generic_send_body_and_form_bindings(self):
        self.assertEqual(classify('click',{}, {'target':{'name':'Send'}},conservative=True),'send')
        self.assertEqual(classify('click',{}, {'target':{'submit':True},'form':{'search':True,'method':'get'}},conservative=True),'form')
        self.assertEqual(classify('dialog',{'accept':True},{'dialog':{'text':'Proceed?'}},conservative=True),'activation')

class ReviewClassification(unittest.TestCase):
    def test_p6_equivalent_keys_classify_the_dispatched_tuple(self):
        from aresos_control.chrome.policy import canonical_key, key_input
        for base in ['Delete', 'Backspace']:
            for modifier in ['', 'Shift+', 'Ctrl+', 'Cmd+Alt+']:
                self.assertEqual(classify('press', {'key':modifier+base}, {'target':{}}), 'delete')
                self.assertIsNone(classify('press', {'key':modifier+base}, {'target':{'editable':True}}))
        self.assertEqual(canonical_key('#'), canonical_key('Shift+#'))
        self.assertEqual(key_input('#'), key_input('Shift+#'))

    def test_p7_tolerant_url_decoding_and_p8_canonical_unicode(self):
        for action in ['https://fixture.test/%73end?bad=%ZZ', 'https://fixture.test/%73end?bad=%FF', 'https://fixture.test/%73end?bad=%E2%82']:
            self.assertEqual(classify('click', {}, {'target':{}, 'form':{'action':action}}), 'send')
        for word, expected in [('lo\u0308schen','delete'), ('vero\u0308ffentlichen','send')]:
            self.assertEqual(classify('click', {}, {'target':{'name':word}}), expected)

    def test_p9_explicit_payment_and_deletion_override_adapter(self):
        adapter = {'kind':'gemini_question', 'effect':'send'}
        for channel in ['name','label','title','value','role']:
            for cue in ['Pay', 'Delete']:
                self.assertEqual(classify('click', {}, {'target':{channel:cue}}, adapter=adapter), cue.lower())
        for cue in ['pay', 'delete']:
            self.assertEqual(classify('click', {}, {'target':{},'form':{'action':'https://fixture.test/'+cue}}, adapter=adapter), cue)

    def test_p14_unsubscribe_binds_item_without_a_draft(self):
        for label in ['Unsubscribe', 'Abbestellen']:
            self.assertEqual(classify('click', {}, {'target':{'name':label}}), 'item')

    def test_p21_get_search_form_enter_in_ordinary_input(self):
        facts = {'target':{'editable':True}, 'form':{'method':'get', 'search':True}}
        self.assertIsNone(classify('press', {'key':'Enter'}, facts))
        self.assertEqual(classify('press', {'key':'Enter'}, facts, conservative=True), 'form')
        facts['form']['method']='post'
        self.assertEqual(classify('press', {'key':'Enter'}, facts), 'send')

class RecheckSearch(unittest.TestCase):
    def test_explicit_search_submitters_ask_and_ordinary_search_stays_free(self):
        for label,expected in [('Pay','pay'),('Delete','delete'),('Send','form'),('Search',None)]:
            facts={'target':{'name':label,'submit':True},'form':{'search':True,'method':'get','action':'https://fixture.test/query'}}
            for verb,args in [('click',{}),('press',{'key':'Enter'}),('press',{'key':'Space'})]:
                self.assertEqual(classify(verb,args,facts),expected,(label,verb))

        for value in ['Pay for lunch','Delete old notes','Send a letter']:
            query={'target':{'name':'Search','editable':True,'search':True,'value':value},'form':{'search':True,'method':'get','action':'https://fixture.test/query'}}
            self.assertIsNone(classify('press',{'key':'Enter'},query))
            self.assertIsNone(classify('click',{},query))
            self.assertIsNone(classify('click',{}, {'target':{'name':'Message','editable':True,'value':value}}))
            self.assertEqual(classify('press',{'key':'Enter'},{'target':{'name':'Message','editable':True,'value':value}}),'send')


class ClipboardDescriptions(unittest.TestCase):
    def test_2c_click_descriptions_warn_without_changing_the_liftable_shared_block(self):
        from aresos_control.definitions import BY_NAME
        from aresos_control.chrome.definitions import CLIPBOARD_NOTICE,SHARED
        for verb in ['click','fill','select','check','press','upload','fill_form','dialog','submit','submit_trusted']:
            self.assertIn(CLIPBOARD_NOTICE,BY_NAME['chrome_'+verb].tool()['description'])
        self.assertNotIn(CLIPBOARD_NOTICE,SHARED)

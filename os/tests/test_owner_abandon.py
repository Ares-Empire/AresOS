"""A lost session or reset cannot persist a trial; stock keeps its own setting."""
import copy
import time
import unittest
from unittest.mock import patch

import test_owner_setup_resume as setup


class AbandonTest(unittest.TestCase):
    def begin(self,f):
        f.pair()
        admin=dict(tty='tty3',session='original',boot='first',started_us=1)
        f.tools.session=lambda:admin
        old=copy.deepcopy(f.tools.keyboard())
        f.tools.layout('begin','us')
        self.assertEqual(f.read()['keyboard'],old)
        self.assertEqual(f.read()['loaded_keymap'],'us')
        self.assertFalse(any(c['command'][0]=='localectl' for c in f.calls()))
        return admin,old

    def test_closed_original_session_can_be_abandoned_by_fresh_physical_login(self):
        with setup.preparation() as f:
            admin,old=self.begin(f)
            f.tools.session=lambda:dict(admin,session='fresh',started_us=int(time.monotonic()*1e6)+1)
            with patch.object(f.tools,'title',return_value=['fresh verified title']):f.tools.layout('abandon')
            self.assertFalse((f.store/'layout-pending.json').exists())
            self.assertEqual(f.read()['keyboard'],old)
            self.assertEqual(f.read()['loaded_keymap'],'de')
            self.assertTrue(f.tools.load('layout-abandoned')['persistent_settings_unchanged'])

    def test_reset_reloads_finished_german_and_fresh_login_abandons(self):
        with setup.preparation() as f:
            admin,old=self.begin(f)
            state=f.read();state['loaded_keymap']=state['keyboard']['VConsoleKeymap'];f.state=state;f.write()
            self.assertEqual(f.read()['loaded_keymap'],'de')
            f.tools.session=lambda:dict(admin,session='after-reset',boot='second',started_us=1)
            with patch.object(f.tools,'title',return_value=['fresh verified title']):f.tools.layout('abandon')
            self.assertEqual(f.read()['keyboard'],old)
            self.assertFalse((f.store/'layout-pending.json').exists())

    def test_stock_side_recovery_preserves_stocks_own_installer_layout(self):
        with setup.preparation() as f:
            admin,old=self.begin(f)
            state=f.read();state['rpm']['deployments'][0]['booted']=False;state['rpm']['deployments'][1]['booted']=True
            status=state['bootc']['status'];status['booted'],status['rollback']=status['rollback'],status['booted']
            status['rollbackQueued']=True
            state['bootc']['spec']['bootOrder']='rollback'
            stock=dict(old,VConsoleKeymap='us',X11Layout='us')
            state['keyboard']=stock;state['loaded_keymap']='us';f.state=state;f.write()
            f.tools.session=lambda:dict(admin,session='stock',boot='stock-boot',started_us=1)
            with patch.object(f.tools,'title',return_value=['fresh verified title']):f.tools.layout('abandon')
            self.assertEqual(f.read()['keyboard'],stock)
            self.assertEqual(f.read()['loaded_keymap'],'us')
            self.assertTrue(f.tools.load('layout-abandoned')['stock_side'])
            self.assertFalse(any(c['command'][0]=='localectl' for c in f.calls()))

    def test_original_session_and_wrong_stock_identity_refuse_without_mutation(self):
        with setup.preparation() as f:
            admin,old=self.begin(f)
            f.refuse(lambda:f.tools.layout('abandon'))
            f.tools.session=lambda:dict(admin,session='fresh',boot='new')
            state=f.read();state['rpm']['deployments'][1]['pinned']=False;f.state=state;f.write()
            f.refuse(lambda:f.tools.layout('abandon'))
            self.assertTrue((f.store/'layout-pending.json').exists())

    def test_only_finish_persists_after_new_login_and_typing_proof(self):
        with setup.preparation() as f:
            admin,old=self.begin(f)
            f.tools.layout('revert')
            f.tools.session=lambda:dict(admin,tty='tty4',session='fresh',started_us=int(time.monotonic()*1e6)+1)
            with patch('builtins.input',return_value='yz-/!ü'):f.tools.layout('proof')
            f.tools.session=lambda:admin
            with patch.object(f.tools,'title',return_value=['fresh verified title']):f.tools.layout('finish')
            f.tools.layout('begin','us-intl')
            f.tools.session=lambda:dict(admin,tty='tty4',session='next',started_us=int(time.monotonic()*1e6)+1)
            with patch('builtins.input',return_value='yz-/!ü'):f.tools.layout('proof')
            self.assertEqual(f.read()['keyboard'],old)
            f.tools.session=lambda:admin
            with patch.object(f.tools,'title',return_value=['fresh verified title']):f.tools.layout('finish')
            self.assertEqual(f.read()['keyboard']['VConsoleKeymap'],'us-intl')
            self.assertEqual(f.read()['keyboard']['X11Variant'],'intl')

    def test_fresh_session_recovers_an_interrupted_finish_record(self):
        with setup.preparation() as f:
            f.pair();admin=dict(tty='tty3',session='original',boot='first',started_us=1)
            f.tools.session=lambda:admin;old=copy.deepcopy(f.tools.keyboard())
            f.tools.layout('begin','us-intl')
            f.tools.session=lambda:dict(admin,tty='tty4',session='proof',started_us=int(time.monotonic()*1e6)+1)
            with patch('builtins.input',return_value='yz-/!ü'):f.tools.layout('proof')
            f.tools.session=lambda:admin;original=f.tools.save
            def save(name,value):
                if name=='layout-completed':raise setup.owner.Stop('injected completed-record failure')
                return original(name,value)
            with patch.object(f.tools,'title',return_value=['fresh title']),patch.object(f.tools,'save',side_effect=save),self.assertRaises(setup.owner.Stop):
                f.tools.layout('finish')
            f.tools.session=lambda:dict(admin,session='fresh',started_us=int(time.monotonic()*1e6)+1)
            with patch.object(f.tools,'title',return_value=['fresh title']):f.tools.layout('abandon')
            self.assertEqual(f.read()['keyboard'],old)
            self.assertFalse((f.store/'layout-pending.json').exists())
        # An abrupt interruption between localectl's two writes is the exact
        # mixed state journalled by finish, never an arbitrary third profile.
        with setup.preparation() as f:
            f.pair();admin=dict(tty='tty3',session='original',boot='first',started_us=1)
            f.tools.session=lambda:admin;old=copy.deepcopy(f.tools.keyboard())
            f.tools.layout('begin','us-intl')
            f.tools.session=lambda:dict(admin,tty='tty4',session='proof',started_us=int(time.monotonic()*1e6)+1)
            with patch('builtins.input',return_value='yz-/!ü'):f.tools.layout('proof')
            f.tools.session=lambda:admin;mutate=f.host.mutate
            def interrupted(*command):
                result=mutate(*command)
                if command[:3]==('localectl','--no-convert','set-keymap'):
                    raise KeyboardInterrupt('simulated abrupt interruption after console persistence')
                return result
            with patch.object(f.tools,'title',return_value=['fresh title']),patch.object(f.host,'mutate',side_effect=interrupted),self.assertRaises(KeyboardInterrupt):
                f.tools.layout('finish')
            self.assertEqual(f.read()['keyboard'],dict(old,VConsoleKeymap='us-intl'))
            f.tools.session=lambda:dict(admin,session='fresh',started_us=int(time.monotonic()*1e6)+1)
            pending=f.tools.load('layout-pending');bad=dict(pending,finishing=False)
            f.tools.save('layout-pending',bad)
            f.refuse(lambda:f.tools.layout('abandon'))
            f.tools.save('layout-pending',pending)
            with patch.object(f.tools,'title',return_value=['fresh title']):f.tools.layout('abandon')
            self.assertEqual(f.read()['keyboard'],old)
            self.assertFalse((f.store/'layout-pending.json').exists())

if __name__=='__main__':unittest.main()

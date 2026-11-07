import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from support import MailCase, CERT
from aresos_control.engine import Engine
from aresos_control.common import sha256

OWNER, SERVICE = 26101, 26102


class CallerTransfers(MailCase):
    def test_real_proxy_caller_import_save_permissions_immutable_bytes_and_full_cli_flow(self):
        reference = self.fixture(attachments=[('program.exe',b'not a program\x00\xff','application/octet-stream')])
        before = self.mail.message(reference)["flags"]
        self.engine.close()
        self.root.chmod(0o755)
        for path in [self.root / 'state',self.root / 'independent',*list((self.root / 'state').rglob('*')),*list((self.root / 'independent').rglob('*'))]:
            os.chown(path,SERVICE,SERVICE)
        allowed_work = Path(__file__).resolve().parents[1] / 'test-work'
        allowed_work.mkdir(exist_ok=True)
        home_temp = tempfile.TemporaryDirectory(dir=allowed_work)
        parent = Path(home_temp.name)
        parent.chmod(0o755)
        home = parent / 'owner'
        home.mkdir(mode=0o700)
        os.chown(home,OWNER,OWNER)
        for name in ('Documents','Downloads','Desktop'):
            path = home / name
            path.mkdir(mode=0o700)
            os.chown(path,OWNER,OWNER)
        source = home / 'Documents' / 'attachment.pdf'
        source.write_bytes(b'%PDF-original caller bytes\x00\xff')
        os.chown(source,OWNER,OWNER)
        (self.root / 'sockets').mkdir(mode=0o711)
        os.chown(self.root / 'sockets',SERVICE,SERVICE)
        config = {'owner_uid':OWNER,'state_dir':str(self.root / 'state'),'evidence_dir':str(self.root / 'independent'),'socket_dir':str(self.root / 'sockets')}
        config_file = self.root / 'service.json'
        config_file.write_text(json.dumps(config))
        proxy_config = {'act_socket':str(self.root / 'sockets/act.sock'),'admin_socket':str(self.root / 'sockets/admin.sock'),
                        'home':str(home),'folders':[str(home / name) for name in ('Documents','Downloads','Desktop')]}
        environment = dict(os.environ,SSL_CERT_FILE=str(CERT / 'tls.crt'))
        daemon = subprocess.Popen(['setpriv','--reuid',str(SERVICE),'--regid',str(SERVICE),'--clear-groups',sys.executable,
                                   '-m','aresos_control.daemon','--config',str(config_file)],env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def proxy(verb,args,uid=OWNER):
            code = 'import json,sys; from aresos_control.proxy import Proxy; print(json.dumps(Proxy("mail",json.loads(sys.argv[1])).call(sys.argv[2],json.loads(sys.argv[3]))))'
            result = subprocess.run(['setpriv','--reuid',str(uid),'--regid',str(uid),'--clear-groups',sys.executable,'-c',code,
                                     json.dumps(proxy_config),verb,json.dumps(args)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            return json.loads(result.stdout)
        try:
            for _ in range(100):
                if (self.root / 'sockets/act.sock').exists():
                    break
                if daemon.poll() is not None:
                    self.fail(daemon.communicate())
                time.sleep(0.05)
            composed = proxy('compose',{'account':'box','to':['one@mail.invalid'],'bcc':['hidden@mail.invalid'],'text':'Full CLI/proxy text',
                                        'attachments':[{'path':str(source)},{'reference':reference,'part':'1.2'}]})
            self.assertTrue(composed['ok'],composed)
            comp = composed['data']
            expected = sha256(source.read_bytes())
            self.assertEqual(comp['mail']['attachments'][0]['real_path'],str(source))
            self.assertEqual(comp['mail']['attachments'][0]['sha256'],expected)
            source.write_bytes(b'changed after immutable import')
            approval = proxy('prepare_send',{k:comp[k] for k in ('composition_id','composition_hash')})['data']['approval']
            sent = proxy('send',approval)
            self.assertTrue(sent['ok'],sent)
            self.assertEqual(sent['data']['operation']['state'],'done',sent)
            saved = proxy('attachment_save',{'reference':reference,'part':'1.2'})
            self.assertTrue(saved['ok'],saved)
            output = home / 'Downloads/program.exe'
            self.assertEqual(output.read_bytes(),b'not a program\x00\xff')
            self.assertEqual(saved['data']['sha256'],sha256(output.read_bytes()))
            self.assertFalse(proxy('attachment_save',{'reference':reference,'part':'1.2'})['ok'])
            eml = proxy('attachment_save',{'reference':reference,'part':'source','name':'original.eml','folder':str(home / 'Desktop')})
            self.assertTrue(eml['ok'],eml)
            self.assertIn(b'MIME-Version:',(home / 'Desktop/original.eml').read_bytes())
            outside = parent / 'outside'
            outside.write_bytes(b'not allowed')
            self.assertFalse(proxy('compose',{'account':'box','text':'Refuse','attachments':[{'path':str(outside)}]})['ok'])
            # The service uid cannot read owner paths; it could only have received bytes from the proxy.
            denied = subprocess.run(['setpriv','--reuid',str(SERVICE),'--regid',str(SERVICE),'--clear-groups',sys.executable,
                                     '-c','import pathlib,sys; pathlib.Path(sys.argv[1]).read_bytes()',str(source)],capture_output=True)
            self.assertNotEqual(denied.returncode,0)
            self.assertFalse(proxy('account_add',{})['ok'])
            # Real generated terminal entry, reaching the same service catalogue.
            code = 'import json,sys; from aresos_control.cli import main; raise SystemExit(main(json.loads(sys.argv[1]),sys.argv[2:]))'
            cli = subprocess.run(['setpriv','--reuid',str(OWNER),'--regid',str(OWNER),'--clear-groups',sys.executable,'-c',code,
                                  json.dumps(proxy_config),'mail','search','--input','{"account":"box"}','--json'],capture_output=True,text=True,timeout=20)
            self.assertEqual(cli.returncode,0,cli.stderr)
            self.assertTrue(json.loads(cli.stdout)['ok'])
            import asyncio
            async def mcp_conversation():
                from mcp import Client as MCPClient, StdioServerParameters
                code = 'import json,sys; from aresos_control.proxy import main; main("mail",json.loads(sys.argv[1]))'
                parameters = StdioServerParameters(command='/usr/bin/setpriv',args=['--reuid',str(OWNER),'--regid',str(OWNER),'--clear-groups',sys.executable,'-c',code,json.dumps(proxy_config)],
                                                   env={'PYTHONPATH':os.environ['PYTHONPATH'],'PATH':'/usr/bin:/bin'})
                async with MCPClient(parameters) as client:
                    tools = await client.list_tools()
                    names = {tool.name for tool in tools.tools}
                    self.assertIn('send',names)
                    self.assertIn('prepare_delete',names)
                    self.assertNotIn('account_add',names)
                    result = (await client.call_tool('read',{'reference':reference})).structured_content
                    self.assertTrue(result['ok'],result)
                    self.assertEqual(result['data']['reference'],reference)
            asyncio.run(mcp_conversation())
        finally:
            daemon.send_signal(signal.SIGTERM)
            stdout,stderr = daemon.communicate(timeout=10)
            for path in [self.root / 'state',self.root / 'independent',*list((self.root / 'state').rglob('*')),*list((self.root / 'independent').rglob('*'))]:
                os.chown(path,os.geteuid(),os.getegid())
            self.engine = Engine(self.root / 'state',self.root / 'independent')
            self.mail = self.engine.adapters['mail']
            home_temp.cleanup()
            self.assertEqual(daemon.returncode,0,stdout+stderr)
        self.assertEqual(self.mail.message(reference)['flags'],before)

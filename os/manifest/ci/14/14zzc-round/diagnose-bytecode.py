"""Isolated import diagnosis only; no owner handler, devices, credentials or mutation commands."""
import json,pathlib,sys,tempfile
r=pathlib.Path.cwd();sys.path[:0]=[str(r/'os/tests'),str(r/'os/ci')]
import test_owner_tools as c
with tempfile.TemporaryDirectory(dir=r/'.work/14/14zzc',prefix='import-fixture-') as folder:
 p=pathlib.Path(folder)/'ares-tools';fp=c.bundle.build(p)
 before={x.relative_to(p).as_posix() for x in p.rglob('*') if x.is_file()}
 assert c.owner.checked_bundle(p)==fp
 c.owner.media_module(p)
 after={x.relative_to(p).as_posix() for x in p.rglob('*') if x.is_file()}
 error=None
 try:c.owner.checked_bundle(p)
 except c.owner.Stop as e:error=str(e)
 v=dict(status='diagnostic complete',dont_write_bytecode=sys.dont_write_bytecode,
   added_files=sorted(after-before),bundle_refusal=error,owner_handler_executed=False,
   devices_credentials_or_mutation_commands_used=False)
 print(json.dumps(v))

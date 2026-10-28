import pathlib,subprocess,sys,json
r=pathlib.Path.cwd();w=r/'.work/14'
proof=json.loads((w/'run-40614909488/14zg-probe-proof.json').read_text());assert proof['head']=='ea803fd9b81fbd21ac1d8a054d253cf6d4bb17ac' and proof['native_tests']==451 and proof['native_skips']==0
for command in [[sys.executable,'-X','utf8',str(w/'14zg-control.py'),'privacy'],[sys.executable,'-X','utf8',str(w/'14zg-read-only-replay.py')],['wsl.exe','--exec','bash','-c','cd /mnt/c/Users/pab/AresOS-14-owner-tools && python3 .work/14/14zg-syntax.py'],[sys.executable,'-X','utf8',str(w/'14zg-local-receipt.py'),'owner-tools'],[sys.executable,'-X','utf8',str(w/'14zg-control.py'),'authorize','owner-tools']]:
 subprocess.run(command,check=True)
print('QUALIFICATION_GATES_PASSED; no dispatch sent by this preparer')
